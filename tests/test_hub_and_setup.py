"""The hub no longer serves/links the two files; missions 02/03 point at the
site; and ctfd-setup gives 02/03 a connection link with no download links."""
import glob
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_hub_no_longer_serves_the_two_files(hub):
    assert hub.get("/fichiers/decaflop_poster.png").status_code == 404
    assert hub.get("/fichiers/transition_shot.jpg").status_code == 404


def test_hub_files_whitelist_excludes_them(hub_module):
    assert "decaflop_poster.png" not in hub_module.FILES
    assert "transition_shot.jpg" not in hub_module.FILES


def test_missions_02_03_are_live_site(hub_module):
    missions = {m[0]: m for m in hub_module.MISSIONS}
    for num in ("02", "03"):
        _, _, _, _, _, _, live, files = missions[num]
        assert live == "site"
        assert files == []


def test_hub_home_links_missions_to_site(hub):
    home = hub.get("/").data.decode()
    for num in ("02", "03"):
        start = home.find(f'id="mission-{num}"')
        end = home.find("mission-", start + 10)
        row = home[start:end if end != -1 else None]
        assert ":8001" in row
        assert "/fichiers/" not in row


def _load_ctfd_setup():
    spec = importlib.util.spec_from_file_location("ctfd_setup", ROOT / "scripts" / "ctfd-setup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("num", ["02", "03"])
def test_readme_connect_no_download(num):
    mod = _load_ctfd_setup()
    path = glob.glob(str(ROOT / "challenges" / f"{num}-*" / "README.md"))[0]
    ch = mod.parse_readme(path, "192.168.8.2")
    assert ch["connection_info"] == "http://192.168.8.2:8001"
    assert "**Download:**" not in ch["description"]


def test_ctfd_setup_dry_run_shows_connect_for_02_03():
    env = dict(os.environ)
    env.pop("HANDOUT_DIR", None)
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ctfd-setup.py"),
         "--dry-run", "--env", str(ROOT / ".env.example")],
        capture_output=True, text=True, check=True, env=env).stdout
    lines = {ln[:2]: ln for ln in out.splitlines() if ln[:2] in ("02", "03")}
    assert "connect=http://<CTF-HOST>:8001" in lines["02"]
    assert "connect=http://<CTF-HOST>:8001" in lines["03"]
    assert "Download" not in out            # dry-run prints no download links at all
