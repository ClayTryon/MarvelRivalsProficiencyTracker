import json
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

from version import __version__

_API_URL = (
    "https://api.github.com/repos/ClayTryon/"
    "MarvelRivalsProficiencyTracker/releases/latest"
)


def _parse(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in tag.lstrip("v").split("."))


class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # (new_version, release_url)

    def run(self):
        try:
            req = urllib.request.Request(
                _API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ProfTracker",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            url = data.get("html_url", "")
            if tag and _parse(tag) > _parse(__version__):
                self.update_available.emit(tag.lstrip("v"), url)
        except Exception:
            pass  # no network / private repo / rate limit — silently ignore
