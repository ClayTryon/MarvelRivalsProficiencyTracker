"""Query engine factory — wraps the retriever and Groq LLM."""
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import get_response_synthesizer

from rag.ingest import get_index


def get_engine(top_k: int = 3) -> RetrieverQueryEngine:
    index = get_index()
    retriever = VectorIndexRetriever(index=index, similarity_top_k=top_k)
    synthesizer = get_response_synthesizer(response_mode="compact")
    return RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
    )
