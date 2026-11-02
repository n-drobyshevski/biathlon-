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


def test_hub_serves_no_files(hub):
    # the /fichiers route and the FILES whitelist are gone entirely
    for name in ("decaflop_poster.png", "transition_shot.jpg", "timing_booth.pcap",
                 "referee_usb.img", "case_file.zip"):
        assert hub.get("/fichiers/" + name).status_code == 404


def test_hub_has_no_files_whitelist(hub_module):
    assert not hasattr(hub_module, "FILES")


def test_missions_02_03_are_live_site(hub_module):
    missions = {m[0]: m for m in hub_module.MISSIONS}
    for num in ("02", "03"):
        _, _, _, _, _, _, live, files = missions[num]
        assert live == "site"
        assert files == []


def test_missions_evidence_are_live_share(hub_module):
    missions = {m[0]: m for m in hub_module.MISSIONS}
    for num in ("05", "07", "09", "13", "15"):
        _, _, _, _, _, _, live, files = missions[num]
        assert live == "share", num
        assert files == []


def test_every_mission_has_a_live_service(hub_module):
    # the hub serves no files, so every mission must be reached through a service
    for m in hub_module.MISSIONS:
        assert m[6], f"mission {m[0]} has no live service"


def test_hub_home_links_missions_to_service(hub):
    home = hub.get("/").data.decode()
    expect = {"02": ":8001", "03": ":8001", "05": ":8020", "07": ":8020",
              "09": ":8020", "13": ":8020", "15": ":8020"}
    for num, port in expect.items():
        start = home.find(f'id="mission-{num}"')
        end = home.find("mission-", start + 10)
        row = home[start:end if end != -1 else None]
        assert port in row, num
        assert "/fichiers/" not in row


def test_hub_contexte_shows_share_login(hub):
    ctx = hub.get("/contexte").data.decode()
    assert "equipe-it" in ctx
    assert "transition2026" in ctx
    assert ":8020" in ctx


def _load_ctfd_setup():
    spec = importlib.util.spec_from_file_location("ctfd_setup", ROOT / "scripts" / "ctfd-setup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CONNECT_PORT = {"02": "8001", "03": "8001",
                "05": "8020", "07": "8020", "09": "8020", "13": "8020", "15": "8020"}


@pytest.mark.parametrize("num,port", sorted(CONNECT_PORT.items()))
def test_readme_connect_and_no_hub_links(num, port):
    mod = _load_ctfd_setup()
    path = glob.glob(str(ROOT / "challenges" / f"{num}-*" / "README.md"))[0]
    ch = mod.parse_readme(path, "192.168.8.2")
    assert ch["connection_info"] == f"http://192.168.8.2:{port}"
    assert "/fichiers/" not in ch["description"]
    assert "**Download:**" not in ch["description"]


def test_ctfd_setup_dry_run_links_share_not_hub():
    env = dict(os.environ)
    env.pop("HANDOUT_DIR", None)
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ctfd-setup.py"),
         "--dry-run", "--env", str(ROOT / ".env.example")],
        capture_output=True, text=True, check=True, env=env).stdout
    lines = {ln[:2]: ln for ln in out.splitlines() if ln[:2].isdigit()}
    for num in ("02", "03"):
        assert "connect=http://<CTF-HOST>:8001" in lines[num]
    for num in ("05", "07", "09", "13", "15"):
        assert "connect=http://<CTF-HOST>:8020" in lines[num], num
    assert "Download" not in out            # dry-run prints no download links at all
    assert "/fichiers/" not in out
