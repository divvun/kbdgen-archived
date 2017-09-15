import sys
import os
import hashlib
import requests
import tempfile
import shutil
import humanize
from urllib.parse import urlparse
from pathlib import Path, PosixPath

from .. import get_logger

logger = get_logger(__file__)

if sys.platform.startswith("win"):
    default_cache_dir = Path(os.getenv("LOCALAPPDATA")) / "kbdgen" / "cache"
elif sys.platform.startswith("darwin"):
    default_cache_dir = Path(os.getenv("HOME")) / "Library" / "Caches" / "kbdgen"
else:
    default_cache_dir = Path(os.getenv("HOME")) / ".cache" / "kbdgen"

def stream_download(url: str, fn: str, output_file: str):
    r = requests.get(url, stream=True)

    with open(output_file, 'wb') as f:
        max_size_raw = int(r.headers['content-length'])
        max_size = humanize.naturalsize(max_size_raw)
        i = 0
        block_size = 1024

        for block in r.iter_content(block_size):
            if not block:
                continue
            f.write(block)
            i = min(max_size_raw, i + block_size)
            cur_size = humanize.naturalsize(i)
            percent = "%.0f" % min(i / max_size_raw * 100.0, 100.0)
            sys.stdout.write("%c[2K\r{}: {}/{} {}%%".format(fn, cur_size, max_size, percent) % 27)
            sys.stdout.flush()
        print()

class FileCache:
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
        if sha256sum is None:
            return True
        m = hashlib.sha256()
        with candidate.open('rb') as f:
            m.update(f.read())
        new_sum = m.hexdigest()
        logger.debug("SHA256: %s", new_sum)
        return new_sum == sha256sum

    def save_directory_tree(self, id: str, basepath: str, tree: str):
        src = Path(basepath) / tree
        target = self.cache_dir / id / tree
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir()
        shutil.copytree(src, target)

    def inject_directory_tree(self, id: str, tree: str, base_target: str) -> bool:
        src = self.cache_dir / id / tree
        if not src.exists():
            return False
        target = Path(base_target) / Path(tree).parent
        os.makedirs(str(target), exist_ok=True)
        shutil.rmtree(target, ignore_errors=True)
        logger.debug("Copying '%s' to '%s'" % (src, target))
        
        shutil.copytree(src, target)
        return True

    def download(self, raw_url: str, sha256sum: str) -> str:
        url = urlparse(raw_url)
        filename = PosixPath(url.path).name
        candidate = self.cache_dir / filename
        if self.is_cached_valid(filename, sha256sum):
            return candidate
        logger.info("Downloading '%s'…" % filename)
        stream_download(raw_url, filename, str(candidate))
        if not self.is_cached_valid(filename, sha256sum):
            raise Exception("Cached file '%s' has failed integrity checks." % filename)
        return candidate

    def download_latest_from_github(self, repo: str, branch: str="master") -> str:
        repo_meta = requests.get("https://api.github.com/repos/{repo}/commits/HEAD?branch={branch}".format(
            repo=repo,
            branch=branch
        )).json()

        sha = repo_meta["sha"]
        filename = "%s-%s.tgz" % (repo.replace("/", "-"), sha)
        candidate = self.cache_dir / filename
        if self.is_cached_valid(filename, None):
            return candidate
        download_url = "https://api.github.com/repos/{repo}/tarball/{branch}".format(repo=repo, branch=branch)
        logger.debug("Download URL: %s" % download_url)
        with tempfile.TemporaryDirectory() as tmpdir:
            fp = os.path.join(tmpdir, filename)
            stream_download(download_url, filename, fp)
            Path(fp).rename(candidate)
        return candidate
