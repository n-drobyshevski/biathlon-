"""scripts/check-consistency.py: the evidence in the missions == what the War Room accepts.
Also proves the checks can FAIL: each one must notice when its side drifts."""
import importlib.util
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cc():
    """build_world() sets flags in os.environ and loads apps under cc_* names; put both back
    afterwards so later tests (which read FLAG_14 / FLAG_FINALE) never see throwaway values."""
    saved_env, saved_mods = dict(os.environ), set(sys.modules)
    spec = importlib.util.spec_from_file_location("check_consistency", ROOT / "scripts" / "check-consistency.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_consistency"] = mod
    spec.loader.exec_module(mod)
    mod.world = mod.build_world()
    yield mod
    os.environ.clear()
    os.environ.update(saved_env)
    for name in set(sys.modules) - saved_mods:
        del sys.modules[name]


def test_no_check_fails(cc):
    for label, fn in cc.CHECKS:
        status, detail = fn(cc.world)
        assert status != "FAIL", f"{label}: {detail}"


def test_unseen_vector_answers_are_reported_not_hidden(cc):
    status, detail = cc.check_gateway_theme(cc.world)
    assert status == "WARN" and "OData" in detail and "SAP Gateway" in detail   # no 'odata' inside 'horodatages'


def test_rogue_device_drift_is_detected(cc, monkeypatch):
    monkeypatch.setattr(cc.world["war"], "ROGUE_IP", "10.10.0.43")
    assert cc.check_rogue_device(cc.world)[0] == "FAIL"


def test_incident_time_drift_is_detected(cc, monkeypatch):
    monkeypatch.setattr(cc.world["war"], "INCIDENT_TIME", "19:00")
    assert cc.check_exif_time(cc.world)[0] == "FAIL"


def test_saboteur_drift_is_detected(cc, monkeypatch):
    monkeypatch.setattr(cc.world["war"], "SABOTEUR_ANSWERS", ["SOMEONE ELSE"])
    assert cc.check_saboteur(cc.world)[0] == "FAIL"


def test_gateway_vector_drift_is_detected(cc, monkeypatch):
    monkeypatch.setattr(cc.world["war"], "VECTOR_ANSWERS", ["Wi-Fi", "reginfo", "USR02", "RFC"])
    assert cc.check_gateway_theme(cc.world)[0] == "FAIL"          # "Passerelle SAP" no longer accepted... and Wi-Fi unseen


def test_a_leaky_war_room_is_detected(cc, monkeypatch):
    war = cc.world["war"]                                         # FIELDS holds the checker functions
    leaky = [(k, label, (lambda value: True) if k == "device" else fn) for k, label, fn in war.FIELDS]
    monkeypatch.setattr(war, "FIELDS", leaky)                     # the device field now accepts anything
    assert cc.check_finale_gating(cc.world)[0] == "FAIL"
