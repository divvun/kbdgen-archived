import sys
import os
import hashlib
import requests
from requests.auth import HTTPBasicAuth
import tempfile
import shutil
from urllib.parse import urlparse
from pathlib import Path

from ..base import get_logger
from .downloader import stream_download

logger = get_logger(__file__)

if sys.platform.startswith("win"):
    default_cache_dir = Path(os.getenv("LOCALAPPDATA")) / "kbdgen" / "cache"
elif sys.platform.startswith("darwin"):
    default_cache_dir = Path(os.getenv("HOME")) / "Library" / "Caches" / "kbdgen"
else:
    default_cache_dir = Path(os.getenv("HOME")) / ".cache" / "kbdgen"


class FileCache:
    def __init__(self, cache_dir=default_cache_dir):
        self.cache_dir = Path(cache_dir)
        self.ensure_cache_exists()

    def ensure_cache_exists(self):
        if not self.cache_dir.exists():
            os.makedirs(str(self.cache_dir), exist_ok=True)

    def is_cached_valid(self, filename: str, sha256sum: str) -> bool:
        candidate = self.cache_dir / filename
        if not candidate.exists():
            return False
        if sha256sum is None:
            return True
        m = hashlib.sha256()
        with candidate.open("rb") as f:
            m.update(f.read())
        new_sum = m.hexdigest()
        logger.debug("SHA256: %s", new_sum)
        return new_sum == sha256sum

    def save_directory_tree(self, id: str, basepath: str, tree: str):
        logger.debug(
            "Inject directory tree - id: %s, base: %s, tree: %s" % (id, basepath, tree)
        )
        target = self.cache_dir / id / os.path.relpath(tree, basepath)
        logger.debug("src: %s, dst: %s" % (tree, target))
        target.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(tree, target)

    def inject_directory_tree(self, id: str, tree: str, base_target: str) -> bool:
        logger.debug(
            "Inject directory tree: id: %s, tree: %s, base_target: %s"
            % (id, tree, base_target)
        )
        tree_path = os.path.relpath(tree, base_target)
        src = self.cache_dir / id / tree_path
        target = Path(base_target) / Path(tree_path)
        logger.debug("src: %s, target: %s" % (src, target))
        # TODO: this does not check if the directory has even a single file in it...
        if not src.exists():
            return False
        os.makedirs(str(target), exist_ok=True)
        shutil.rmtree(str(target), ignore_errors=True)
        logger.debug("Copying '%s' to '%s'" % (src, target))

        shutil.copytree(str(src), str(target))
        return True

    def download(self, raw_url: str, sha256sum: str) -> str:
        url = urlparse(raw_url)
        filename = Path(url.path).name
        candidate = str(self.cache_dir / filename)
        if self.is_cached_valid(filename, sha256sum):
            return candidate
        logger.info("Downloading '%s'…" % filename)
        stream_download(raw_url, filename, candidate)
        if not self.is_cached_valid(filename, sha256sum):
            raise Exception("Cached file '%s' has failed integrity checks." % filename)
        return candidate

    def download_latest_from_github(
        self,
        repo: str,
        branch: str = "master",
        username: str = None,
        password: str = None,
    ) -> str:
        url = "https://api.github.com/repos/{repo}/commits/{branch}".format(
            repo=repo, branch=branch
        )

        if username is not None and password is not None:
            repo_meta = requests.get(url, auth=HTTPBasicAuth(username, password)).json()
        else:
            repo_meta = requests.get(url).json()

        sha = repo_meta.get("sha", None)
        if sha is None:
            raise Exception("No sha found in response: %r" % repo_meta)
        filename = "%s-%s.tgz" % (repo.replace("/", "-"), sha)
        candidate = str(self.cache_dir / filename)
        if self.is_cached_valid(filename, None):
            return candidate
        download_url = "https://api.github.com/repos/{repo}/tarball/{branch}".format(
            repo=repo, branch=branch
        )
        logger.debug("Download URL: %s" % download_url)
        with tempfile.TemporaryDirectory() as tmpdir:
            fp = os.path.join(tmpdir, filename)
            stream_download(download_url, filename, fp)
            shutil.move(fp, candidate)
        return candidate
