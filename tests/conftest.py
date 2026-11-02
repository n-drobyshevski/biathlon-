"""Shared fixtures for the DécaFlop CTF tests.

The poster (02) and the race photo (03) are built into a throwaway dist dir
with test flags, then the shop (challenge 01) and the hub are imported with
HANDOUT_DIR pointed at it. Both apps define a module called ``app``, so each is
loaded under a unique name with importlib to avoid a clash.
"""
import importlib.util
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAFF_APP = ROOT / "challenges" / "01-web-staff" / "app"
HUB_APP = ROOT / "hub" / "app"
SHARE_APP = ROOT / "share" / "app"
GEN_DIR = ROOT / "handouts"

TEST_FLAGS = {
    "FLAG_02_STEGO": "TRIATHLON{poster_zip_test}",
    "FLAG_03_EXIF": "TRIATHLON{exif_meta_test}",
    "FLAG_05_PCAP": "TRIATHLON{pcap_creds_test}",
    "FLAG_07_USB": "TRIATHLON{usb_carve_test}",
    "FLAG_09_SAP_USR02": "TRIATHLON{sap_usr02_test}",
    "SABOTEUR_NAME": "viktor_lindqvist",
    "FLAG_13_SAP_SHORTCUT": "TRIATHLON{sap_shortcut_test}",
    "FLAG_15_SAP_ABAP": "TRIATHLON{sap_abap_test}",
}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def dist(tmp_path_factory):
    """Build every handout file from the test flags into a throwaway dir."""
    out = tmp_path_factory.mktemp("dist")
    os.environ.update(TEST_FLAGS)
    gen = _load("gen_handouts", GEN_DIR / "generate.py")
    gen.OUT = str(out)
    gen.gen_stego()
    gen.gen_exif()
    gen.gen_pcap()
    gen.gen_usb()
    gen.gen_sap()
    gen.gen_sap_shortcut()
    gen.gen_sap_abap()
    os.environ["HANDOUT_DIR"] = str(out)
    return out


@pytest.fixture(scope="session")
def shop_module(dist):
    os.environ["HANDOUT_DIR"] = str(dist)
    os.environ.setdefault("FLAG", "TRIATHLON{staff_test}")
    if str(STAFF_APP) not in sys.path:
        sys.path.insert(0, str(STAFF_APP))
    return _load("staff_app", STAFF_APP / "app.py")


@pytest.fixture()
def shop(shop_module):
    return shop_module.app.test_client()


@pytest.fixture(scope="session")
def hub_module(dist):
    os.environ["HANDOUT_DIR"] = str(dist)
    return _load("hub_app", HUB_APP / "app.py")


@pytest.fixture()
def hub(hub_module):
    return hub_module.app.test_client()


SHARE_PASSWORD = "transition2026"


@pytest.fixture(scope="session")
def share_module(dist):
    os.environ["HANDOUT_DIR"] = str(dist)
    os.environ["SHARE_PASSWORD"] = SHARE_PASSWORD
    os.environ["SHARE_SECRET_KEY"] = "test-secret-key"
    return _load("share_app", SHARE_APP / "app.py")


@pytest.fixture()
def share_anon(share_module):
    """A share client that is NOT logged in."""
    return share_module.app.test_client()


@pytest.fixture()
def share(share_module):
    """A share client that is logged in as the crew account."""
    share_module._FAILS.clear()                      # not tripped by a prior test
    c = share_module.app.test_client()
    r = c.post("/login", data={"identifiant": "equipe-it", "motdepasse": SHARE_PASSWORD})
    assert r.status_code == 302
    return c
