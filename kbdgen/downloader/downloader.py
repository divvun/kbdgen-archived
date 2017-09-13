import sys
import os
import hashlib
from urllib.parse import urlparse
from pathlib import Path, PosixPath
from homura import download

from .. import get_logger

logger = get_logger(__file__)

if sys.platform.startswith("win"):
    default_cache_dir = Path(os.getenv("LOCALAPPDATA")) / "kbdgen" / "cache"
elif sys.platform.startswith("darwin"):
    default_cache_dir = Path(os.getenv("HOME")) / "Library" / "Caches" / "kbdgen"
else:
    default_cache_dir = Path(os.getenv("HOME")) / ".cache" / "kbdgen"

class Downloader:
    def __init__(self, cache_dir=default_cache_dir):
        self.cache_dir = Path(cache_dir)
        self.ensure_cache_exists()

    def ensure_cache_exists(self):
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(exist_ok=True)

    def is_cached_valid(self, filename: str, sha256sum: str) -> bool:
        candidate = self.cache_dir / filename
        if not candidate.exists():
            return False
        m = hashlib.sha256()
        with candidate.open('rb') as f:
            m.update(f.read())
        new_sum = m.hexdigest()
        logger.debug("SHA256: %s", new_sum)
        return new_sum == sha256sum

    def download(self, raw_url: str, sha256sum: str) -> str:
        url = urlparse(raw_url)
        filename = PosixPath(url.path).name
        candidate = self.cache_dir / filename
        if self.is_cached_valid(filename, sha256sum):
            return candidate
        logger.info("Downloading '%s'…" % filename)
        download(url=raw_url, path=str(candidate))
        if not self.is_cached_valid(filename, sha256sum):
            raise Exception("Cached file '%s' has failed integrity checks." % filename)
        return candidate