"""Sucht auf GitHub nach einer neuen Version und startet deren Installer."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass

from . import __version__

REPO = "phillhf/mp3-organizer"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET_PATTERN = re.compile(r"^MP3-Organizer-Setup-[\d.]+\.exe$")


@dataclass
class Release:
    version: str
    page: str
    asset_url: str
    asset_name: str
    digest: str


def parse_version(text):
    numbers = re.findall(r"\d+", text)
    return tuple(int(n) for n in numbers[:3]) + (0,) * (3 - len(numbers[:3]))


def _request(url):
    return urllib.request.Request(url, headers={
        "User-Agent": f"MP3Organizer/{__version__}", "Accept": "application/vnd.github+json"})


def parse_release(data, current=__version__):
    """Liefert das Release, falls es neuer ist als current und einen Installer hat."""
    tag = data.get("tag_name", "")
    if parse_version(tag) <= parse_version(current):
        return None
    for asset in data.get("assets", []):
        if ASSET_PATTERN.match(asset.get("name", "")):
            return Release(tag.lstrip("v"), data.get("html_url", ""),
                           asset["browser_download_url"], asset["name"], asset.get("digest") or "")
    return None


def check_latest(current=__version__):
    with urllib.request.urlopen(_request(API_URL), timeout=15) as response:
        return parse_release(json.load(response), current)


def download(release, progress=lambda percent: None):
    target = os.path.join(tempfile.mkdtemp(prefix="mp3org-update-"), release.asset_name)
    digest = hashlib.sha256()
    with urllib.request.urlopen(_request(release.asset_url), timeout=60) as response, \
            open(target, "wb") as f:
        total = int(response.headers.get("Content-Length") or 0)
        loaded = 0
        while chunk := response.read(256 * 1024):
            f.write(chunk)
            digest.update(chunk)
            loaded += len(chunk)
            if total:
                progress(loaded * 100 // total)
    if release.digest and release.digest != f"sha256:{digest.hexdigest()}":
        os.remove(target)
        raise ValueError("Prüfsumme des Downloads stimmt nicht")
    return target


def can_self_update():
    return bool(getattr(sys, "frozen", False))


def start_installer(path):
    """Startet das Setup still; es beendet die App und startet sie danach neu."""
    subprocess.Popen([path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/RESTARTAPP=1"],
                     close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
