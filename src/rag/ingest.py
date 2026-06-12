"""
URL -> LlamaIndex vector index.

Manages a persistent index stored at <project_root>/rag_index/.
Call add_urls() to scrape and index one or more Fandom wiki pages.
The index survives app restarts; call clear_index() to wipe and start over.
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

# In a frozen exe the app dir is next to the executable; in dev it's the project root.
_APP_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=_APP_DIR / ".env")

_INDEX_DIR = _APP_DIR / "rag_index"
_GROQ_MODEL = "llama-3.3-70b-versatile"
_EMBED_MODEL = "BAAI/bge-small-en-v1.5"

_index = None  # cached VectorStoreIndex
_stats_collector: list[dict] = []  # populated by _extract_infobox during add_urls


def rag_enabled() -> bool:
    """Return False when PROFTRACKER_DISABLE_RAG is set (any non-empty value)."""
    return not os.environ.get("PROFTRACKER_DISABLE_RAG")


def _setup_settings() -> None:
    from llama_index.core import Settings
    from llama_index.llms.groq import Groq
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    Settings.llm = Groq(
        model=_GROQ_MODEL,
        api_key=os.environ.get("GROQ_API_KEY", ""),
        temperature=0.1,
    )
    Settings.embed_model = HuggingFaceEmbedding(model_name=_EMBED_MODEL)
    Settings.chunk_size = 512
    Settings.chunk_overlap = 64


def get_index():
    """Return the active VectorStoreIndex, loading from disk if needed."""
    global _index
    if _index is not None:
        return _index

    from llama_index.core import (
        VectorStoreIndex, StorageContext, load_index_from_storage,
    )

    _setup_settings()

    if _INDEX_DIR.exists() and any(_INDEX_DIR.iterdir()):
        storage_context = StorageContext.from_defaults(persist_dir=str(_INDEX_DIR))
        _index = load_index_from_storage(storage_context)
    else:
        _index = VectorStoreIndex.from_documents([])
        _INDEX_DIR.mkdir(parents=True, exist_ok=True)
        _index.storage_context.persist(persist_dir=str(_INDEX_DIR))

    return _index


def _extract_infobox(html: str, title: str, url: str) -> "Document | None":
    """Extract only game-relevant stats from the wikitext infobox into a focused chunk.
    Keeping this chunk tiny ensures its embedding strongly represents game stats, not biography."""
    import re
    import json as _json
    import urllib.parse
    import urllib.request
    from llama_index.core.schema import Document

    # Use the revisions API to get raw wikitext — field values are unambiguous there
    m = re.match(r"(https?://[^/]+)", url)
    if not m:
        return None
    base = m.group(1)
    page_title = urllib.parse.unquote(url.split("/wiki/")[-1]).replace("_", " ")
    api = (
        f"{base}/api.php?action=query&titles={urllib.parse.quote(page_title)}"
        f"&prop=revisions&rvprop=content&rvslots=main&format=json&formatversion=2"
    )
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "ProfTracker/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = _json.loads(resp.read())
        wikitext = (
            data.get("query", {}).get("pages", [{}])[0]
            .get("revisions", [{}])[0]
            .get("slots", {}).get("main", {}).get("content", "")
        )
    except Exception:
        return None

    if not wikitext:
        return None

    # Pull only the game-stat fields by name
    stat_fields = {
        "role": "Role",
        "health": "Health / HP",
        "difficulty": "Difficulty",
        "realname": "Real Name",
    }
    parsed: dict[str, str] = {}
    lines = [f"{title} game stats:"]
    for field, label in stat_fields.items():
        m2 = re.search(rf"^\|\s*{field}\s*=\s*(.+)$", wikitext, re.MULTILINE | re.IGNORECASE)
        if m2:
            val = m2.group(1).strip()
            val = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", val)
            val = re.sub(r"\{\{[^}]+\}\}", "", val).strip()
            if val:
                parsed[label] = val
                lines.append(f"{label}: {val}")

    if len(lines) < 2:
        return None

    # Side-effect: feed the aggregate stats table built in rebuild_index
    _stats_collector.append({"name": title, **parsed})

    return Document(
        text="\n".join(lines),
        metadata={"url": url, "title": title, "chunk_type": "stats"},
    )


def _fetch_mediawiki(url: str) -> "list | None":
    """Use the MediaWiki parse API to get plain text for /wiki/ URLs.
    Returns a list of Documents on success, None if the URL pattern doesn't match."""
    import re
    import json as _json
    import urllib.parse
    import urllib.request
    from llama_index.core.schema import Document

    m = re.match(r"(https?://[^/]+)/wiki/(.+)", url)
    if not m:
        return None

    base = m.group(1)
    title = urllib.parse.unquote(m.group(2)).replace("_", " ")
    api = (
        f"{base}/api.php?action=parse"
        f"&page={urllib.parse.quote(title)}"
        f"&prop=text&format=json&formatversion=2"
    )
    req = urllib.request.Request(api, headers={"User-Agent": "ProfTracker/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = _json.loads(resp.read())

    html = data.get("parse", {}).get("text", "")
    if not html:
        return None

    docs = []

    # Dedicated infobox chunk so stats (HP, role, difficulty) retrieve reliably
    infobox_doc = _extract_infobox(html, title, url)
    if infobox_doc:
        docs.append(infobox_doc)

    # Full page as plain text for ability descriptions, lore, etc.
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        docs.append(Document(text=text, metadata={"url": url, "title": title}))

    return docs if docs else None


def add_urls(
    urls: list[str],
    progress_cb: Callable[[str], None] | None = None,
) -> int:
    """Scrape URLs, embed, and insert into the persistent index. Returns doc count."""
    global _index
    from llama_index.readers.web import BeautifulSoupWebReader

    _setup_settings()

    if progress_cb:
        progress_cb(f"Fetching {len(urls)} page(s)...")

    reader = BeautifulSoupWebReader()
    docs = []
    for url in urls:
        try:
            if progress_cb:
                progress_cb(f"  Fetching: {url}")
            # Try MediaWiki API first (works for Fandom without JS)
            page_docs = _fetch_mediawiki(url)
            if page_docs is None:
                # Fall back to HTML scraping for non-wiki URLs
                page_docs = reader.load_data(urls=[url])
                for doc in page_docs:
                    doc.metadata["url"] = url
            docs.extend(page_docs)
        except Exception as exc:
            if progress_cb:
                progress_cb(f"  Error ({url}): {exc}")

    if not docs:
        return 0

    if progress_cb:
        progress_cb("Building embeddings and inserting...")

    idx = get_index()
    for doc in docs:
        idx.insert(doc)

    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    idx.storage_context.persist(persist_dir=str(_INDEX_DIR))

    if progress_cb:
        progress_cb(f"Done — {len(docs)} chunk(s) added.")

    return len(docs)


def index_chunk_count() -> int:
    try:
        return len(get_index().docstore.docs)
    except Exception:
        return 0


def clear_index() -> None:
    global _index
    from llama_index.core import VectorStoreIndex
    _setup_settings()
    if _INDEX_DIR.exists():
        shutil.rmtree(_INDEX_DIR)
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    _index = VectorStoreIndex.from_documents([])
    _index.storage_context.persist(persist_dir=str(_INDEX_DIR))


def rebuild_index(
    urls: list[str],
    progress_cb: Callable[[str], None] | None = None,
) -> int:
    """Clear the index, then index all given URLs from scratch. Returns chunk count."""
    global _stats_collector
    _stats_collector = []

    if progress_cb:
        progress_cb("Clearing existing RAG index...")
    clear_index()
    count = add_urls(urls, progress_cb=progress_cb)

    # Insert one aggregated stats document so comparison queries
    # ("which tank has the most HP?") see all heroes at once.
    if _stats_collector:
        if progress_cb:
            progress_cb("Building hero stats comparison table...")
        _insert_stats_aggregate(_stats_collector)

    return count


def _insert_stats_aggregate(stats: list[dict]) -> None:
    from llama_index.core.schema import Document
    ordered = sorted(stats, key=lambda h: h.get("name", ""))
    rows = ["Marvel Rivals hero base stats (all heroes, for comparison queries):"]
    for h in ordered:
        parts = []
        for key in ("Role", "Health / HP", "Difficulty", "Real Name"):
            if key in h:
                parts.append(f"{key}: {h[key]}")
        rows.append(f"  {h['name']} — " + ", ".join(parts))
    doc = Document(
        text="\n".join(rows),
        metadata={"chunk_type": "stats_aggregate", "title": "Hero Stats Table"},
    )
    idx = get_index()
    idx.insert(doc)
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    idx.storage_context.persist(persist_dir=str(_INDEX_DIR))
