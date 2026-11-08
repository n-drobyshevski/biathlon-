"""War Room finale: all four fields must be right, the flag is never leaked,
failures only say HOW MANY fields are right, and submissions are rate limited."""
import importlib.util
import itertools
import pathlib
import sys
from html import unescape

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLAG = "TRIATHLON{grand_maitre_test}"
RIGHT = {"saboteur": "VLINDQVIST", "vector": "Passerelle SAP", "time": "18:42",
         "device": "aa:bb:cc:dd:ee:42"}
ENV_NAMES = ("FLAG_FINALE", "ROGUE_MAC", "ROGUE_IP", "WARROOM_SABOTEUR", "WARROOM_VECTOR",
             "WARROOM_INCIDENT_DATE", "WARROOM_INCIDENT_TIME", "WARROOM_RATE_LIMIT",
             "WARROOM_RATE_WINDOW", "WARROOM_TRUST_PROXY")


def load(monkeypatch, name="warroom_app", path=None, **env):
    """A fresh copy of the module (its rate-limit state starts empty) under a clean env."""
    for k in ENV_NAMES:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location(name, path or ROOT / "warroom" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def wr(monkeypatch):
    return load(monkeypatch, FLAG_FINALE=FLAG)


@pytest.fixture()
def client(wr):
    return wr.app.test_client()


def post(client, ip="10.0.0.9", **fields):
    data = {**RIGHT, **fields}
    return client.post("/submit", data=data, environ_overrides={"REMOTE_ADDR": ip})


# ---------------------------------------------------------------- the form
def test_form_is_french_and_has_no_flag(client):
    r = client.get("/")
    page = unescape(r.data.decode())                                  # the template escapes the apostrophe
    assert r.status_code == 200 and r.headers["Cache-Control"] == "no-store"
    for label in ("Identité du saboteur", "Vecteur d'attaque", "Heure de l'incident",
                  "Équipement fantôme (MAC ou IP)"):
        assert label in page
    assert page.count("<input") == 4 and "TRIATHLON{" not in page


# ---------------------------------------------------------------- success and failure
def test_all_correct_reveals_the_flag(client):
    r = post(client)
    page = r.data.decode()
    assert r.status_code == 200 and FLAG in page and r.headers["Cache-Control"] == "no-store"
    assert "Erreur de corrélation" not in page


def test_all_wrong_says_zero_of_four_and_no_flag(client):
    r = post(client, saboteur="x", vector="y", time="z", device="w")
    page = r.data.decode()
    assert "Erreur de corrélation : 0 champ(s) correct(s) sur 4. Vérifiez vos preuves avec les autres équipes." in page
    assert "TRIATHLON{" not in page


@pytest.mark.parametrize("k", range(0, 4))
def test_count_matches_number_of_correct_fields_but_never_which(client, k):
    fresh_ip = (f"10.1.0.{n}" for n in itertools.count(1))           # one budget per submission
    for keep in itertools.combinations(RIGHT, k):
        wrong = {f: "nope" for f in RIGHT if f not in keep}
        page = post(client, ip=next(fresh_ip), **wrong).data.decode()
        assert f"{k} champ(s) correct(s) sur 4" in page
        assert 'class="ok"' not in page and page.count('class="err"') == 1   # no per-field marker
        assert "TRIATHLON{" not in page


def test_flag_never_appears_on_a_failure_even_when_configured(client):
    assert FLAG not in post(client, device="10.10.0.43").data.decode()


def test_missing_flag_config_fails_loudly_instead_of_a_placeholder(monkeypatch):
    wr = load(monkeypatch)                                           # FLAG_FINALE not set
    r = post(wr.app.test_client())
    assert r.status_code == 500 and "TRIATHLON{" not in r.data.decode()
    assert "pas configuré" in r.data.decode()


# ---------------------------------------------------------------- what counts as right
@pytest.mark.parametrize("field,value", [
    ("saboteur", "VLINDQVIST"), ("saboteur", "vlindqvist"), ("saboteur", "  Viktor   Lindqvist "),
    ("saboteur", "V.LINDQVIST"), ("saboteur", "v.lindqvist"),
    *[("vector", v) for v in ("SAP Gateway", "passerelle sap", "REGINFO", "usr02", "OData", "rfc")],
    ("time", "18:42"), ("time", "18:42:00"), ("time", "2026-11-01 18:42"), ("time", "18h42"),
    ("time", "2026:11:01 18:42:11"), ("time", "01/11/2026 18:42"), ("time", " 18:42:59 "),
    ("device", "aa:bb:cc:dd:ee:42"), ("device", "AA-BB-CC-DD-EE-42"), ("device", "aabbccddee42"),
    ("device", "10.10.0.42"), ("device", " 10.10.0.42 "),
])
def test_accepted_variants(client, field, value):
    wrong = {f: "nope" for f in RIGHT if f != field}
    assert "1 champ(s) correct(s) sur 4" in post(client, **{**wrong, field: value}).data.decode()
    assert FLAG in post(client, ip="10.2.0.1", **{field: value}).data.decode()


@pytest.mark.parametrize("field,value", [
    ("saboteur", "Lindqvist"), ("saboteur", "VLINDQVIST2"), ("saboteur", ""), ("saboteur", "MSORENSEN"),
    ("vector", "gateway"), ("vector", "SAP Gateway reginfo"), ("vector", ""),
    ("vector", "sap gateway, passerelle sap, reginfo, usr02, odata, rfc"),   # keyword stuffing
    ("time", "18:43"), ("time", "19:42"), ("time", "2026-11-02 18:42"), ("time", "18:4"),
    ("time", "6:42pm"), ("time", "2026-11-01 18:42 18:42"), ("time", ""),
    ("device", "10.10.0.43"), ("device", "10.10.0.4"), ("device", "aa:bb:cc:dd:ee:43"),
    ("device", "aabbccddee4"), ("device", "10.10.0.42x"), ("device", ""),
])
def test_rejected_variants(client, field, value):
    assert FLAG not in post(client, **{field: value}).data.decode()
    wrong = {f: "nope" for f in RIGHT if f != field}
    assert "0 champ(s) correct(s) sur 4" in post(client, ip="10.3.0.1", **{**wrong, field: value}).data.decode()


def test_answers_can_be_overridden_by_env(monkeypatch):
    wr = load(monkeypatch, FLAG_FINALE=FLAG, WARROOM_SABOTEUR="Autre Nom, A.NOM",
              ROGUE_IP="10.10.0.99", ROGUE_MAC="02:00:00:00:00:99", WARROOM_INCIDENT_TIME="19:05")
    c = wr.app.test_client()
    page = post(c, saboteur="a.nom", vector="nope", device="02-00-00-00-00-99", time="19:05:30").data.decode()
    assert "3 champ(s) correct(s) sur 4" in page
    assert FLAG in post(c, ip="10.4.0.1", saboteur="Autre Nom", device="10.10.0.99",
                        time="2026-11-01 19:05").data.decode()
    assert "0 champ(s)" in post(c, ip="10.4.0.2", saboteur="VLINDQVIST", vector="x",
                                device="10.10.0.42", time="18:42").data.decode()


# ---------------------------------------------------------------- the rogue device never drifts from generate.py
def test_rogue_device_matches_the_handout_generator(monkeypatch, dist):
    wr = load(monkeypatch)
    gen = load(monkeypatch, name="gen_for_warroom", path=ROOT / "handouts" / "generate.py")
    assert (wr.ROGUE_MAC, wr.ROGUE_IP) == (gen.ROGUE_MAC, gen.ROGUE_IP) == ("aa:bb:cc:dd:ee:42", "10.10.0.42")
    raw = (dist / "phantom_signal.pcap").read_bytes()                # what players actually analyse
    assert bytes.fromhex(wr.ROGUE_MAC.replace(":", "")) in raw
    assert f"host={wr.ROGUE_IP}".encode() in raw
    assert wr.check_device(wr.ROGUE_MAC) and wr.check_device(wr.ROGUE_IP)


# ---------------------------------------------------------------- rate limit
def test_sixth_submission_in_a_minute_is_refused(client):
    for _ in range(5):
        assert post(client, device="nope").status_code == 200
    r = post(client)                                                 # even a CORRECT report is refused
    assert r.status_code == 429 and 1 <= int(r.headers["Retry-After"]) <= 60
    assert "Trop de tentatives" in r.data.decode() and FLAG not in r.data.decode()


def test_limit_is_per_ip(client):
    for _ in range(5):
        post(client, ip="10.5.0.1", device="nope")
    assert post(client, ip="10.5.0.1").status_code == 429
    assert FLAG in post(client, ip="10.5.0.2").data.decode()


def test_window_slides_and_blocked_attempts_do_not_extend_it(wr, client):
    t = [1000.0]
    wr._now = lambda: t[0]
    for _ in range(5):
        post(client, device="nope")
        t[0] += 1
    t[0] = 1010.0
    first = post(client)
    assert first.status_code == 429
    t[0] = 1030.0
    later = post(client)
    assert later.status_code == 429 and int(later.headers["Retry-After"]) < int(first.headers["Retry-After"])
    t[0] = 1000.0 + 60.5                                              # the first hit has aged out
    assert FLAG in post(client).data.decode()


def test_forwarded_header_is_ignored_unless_proxy_is_trusted(monkeypatch):
    plain = load(monkeypatch, FLAG_FINALE=FLAG)
    c = plain.app.test_client()
    for i in range(5):
        c.post("/submit", data={**RIGHT, "device": "nope"}, headers={"X-Forwarded-For": f"1.1.1.{i}"},
               environ_overrides={"REMOTE_ADDR": "10.6.0.1"})
    r = c.post("/submit", data=RIGHT, headers={"X-Forwarded-For": "9.9.9.9"},
               environ_overrides={"REMOTE_ADDR": "10.6.0.1"})
    assert r.status_code == 429                                       # spoofing the header does not help
    proxied = load(monkeypatch, FLAG_FINALE=FLAG, WARROOM_TRUST_PROXY="1")
    c = proxied.app.test_client()
    for _ in range(5):
        c.post("/submit", data={**RIGHT, "device": "nope"}, headers={"X-Forwarded-For": "1.1.1.1"},
               environ_overrides={"REMOTE_ADDR": "10.6.0.1"})
    assert c.post("/submit", data=RIGHT, headers={"X-Forwarded-For": "1.1.1.1"},
                  environ_overrides={"REMOTE_ADDR": "10.6.0.1"}).status_code == 429
    assert FLAG in c.post("/submit", data=RIGHT, headers={"X-Forwarded-For": "2.2.2.2"},
                          environ_overrides={"REMOTE_ADDR": "10.6.0.1"}).data.decode()


def test_oversized_and_missing_fields_are_handled(client):
    assert client.post("/submit", data={}).status_code == 200        # missing fields count as wrong
    assert client.post("/submit", data={"saboteur": "x" * 20000}).status_code == 413
