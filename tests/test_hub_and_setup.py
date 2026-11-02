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


def test_hub_contexte_links_share_without_creds(hub):
    ctx = hub.get("/contexte").data.decode()
    assert ":8020" in ctx                       # still names/links the share
    assert "portail staff" in ctx               # points players at challenge 01
    assert "transition2026" not in ctx          # no longer prints the credentials
    assert "equipe-it" not in ctx


# ---------------------------------------------------------------- locked missions
def _row(home, num):
    i = home.find(f'id="mission-{num}"')
    j = home.find("mission-", i + 10)
    return home[i:j if j != -1 else None]


def test_requires_matches_the_share_gated_set(hub_module):
    # the lock prerequisites are exactly the share-gated missions
    share_gated = {m[0] for m in hub_module.MISSIONS if m[6] == "share"}
    assert set(hub_module.REQUIRES) == share_gated == {"05", "07", "09", "13", "15"}
    assert all(reqs == ["01"] for reqs in hub_module.REQUIRES.values())
    # soft feeders are deliberately NOT locked
    for soft in ("03", "04", "06"):
        assert soft not in hub_module.REQUIRES


def test_gated_rows_render_locked_affordances(hub):
    home = hub.get("/").data.decode()
    for num in ("05", "07", "09", "13", "15"):
        row = _row(home, num)
        assert 'data-requires="01"' in row                      # JS targets this
        assert 'class="lock" hidden' in row                     # note hidden by default
        assert "Déverrouillé en résolvant la mission 01" in row  # real text reason
        assert 'class="open"' in row                            # link wrapper to toggle


def test_non_gated_rows_have_no_lock(hub):
    home = hub.get("/").data.decode()
    for num in ("01", "02", "03", "04", "06", "10", "11", "12", "14"):
        row = _row(home, num)
        assert "data-requires" not in row
        assert 'class="lock"' not in row


def test_lock_rule_locks_until_prereq_solved(hub_module):
    # mirror the client rule: locked iff not every prerequisite is solved
    def locked(solved):
        return {num for num, reqs in hub_module.REQUIRES.items()
                if any(r not in solved for r in reqs)}
    assert locked(set()) == {"05", "07", "09", "13", "15"}       # fresh browser
    assert locked({"01"}) == set()                               # 01 solved -> all unlock
    assert locked({"01", "05"}) == set()                         # staying unlocked
    assert locked({"02", "03"}) == {"05", "07", "09", "13", "15"}  # wrong prereq solved


def test_lock_script_guards_and_wiring(hub):
    home = hub.get("/").data.decode()
    assert "if(!store)return" in home                            # no storage -> unlocked
    assert "store.setItem(probe" in home                         # probes storage is writable
    assert "applyLocks" in home and "tr[data-requires]" in home  # the lock pass is wired
    assert "sel.value==='Résolu'" in home                        # reads the same Statut state


def test_page_notes_the_lock_is_only_a_guide(hub):
    home = hub.get("/").data.decode()
    assert "repère" in home
    assert "rien n'est bloqué" in home


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
