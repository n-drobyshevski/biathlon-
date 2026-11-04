"""scripts/ctfd-users.py: pre-made CTFd accounts (no e-mail form for players)."""
import importlib.util
import os
import pathlib
import random
import re
import stat

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def mod():
    spec = importlib.util.spec_from_file_location("ctfd_users", ROOT / "scripts" / "ctfd-users.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeCTFd:
    """Just enough of CTFd's admin API: users list/search, create, patch, configs."""
    def __init__(self, existing=()):
        self.users = [{"id": i + 1, "name": n} for i, n in enumerate(existing)]
        self.calls = []

    def call(self, method, path, data=None):
        self.calls.append((method, path, data))
        if method == "GET" and path.startswith("/users?"):
            q = re.search(r"q=([^&]*)", path).group(1)
            return [u for u in self.users if q.lower() in u["name"].lower()]
        if method == "POST" and path.startswith("/users"):
            u = {"id": len(self.users) + 1, **data}
            self.users.append(u)
            return u
        return {}


class Rng:                                   # secrets-like, but seeded
    def __init__(self, seed=1):
        self.r = random.Random(seed)

    def choice(self, seq):
        return self.r.choice(seq)

    def randbelow(self, n):
        return self.r.randrange(n)


def test_passwords_are_easy_words_and_a_number(mod):
    rng = Rng()
    for _ in range(200):
        pw = mod.make_password(rng)
        a, b, n = pw.split("-")
        assert a in mod.WORDS and b in mod.WORDS and a != b
        assert n.isdigit() and 10 <= int(n) <= 99
        assert pw.isascii() and pw == pw.lower()


def test_plan_names_count_test_and_unique_emails(mod):
    rows = mod.plan(["Élodie", "ÉLODIE", "Jean Luc", " "], 2, test=True)     # same pseudo twice: kept once
    assert [r[0] for r in rows] == ["Élodie", "Jean Luc", "player01", "player02", "test"]
    emails = [r[1] for r in rows]
    assert emails[0] == "elodie@ctf.lan" and emails[1] == "jean-luc@ctf.lan"
    assert all(e.endswith("@ctf.lan") for e in emails)
    assert [r[2] for r in rows] == [False, False, False, False, True]   # only test is hidden
    # different pseudos that fold to the same e-mail still get distinct e-mails
    assert [r[1] for r in mod.plan(["Élodie", "elodie"], 0, test=False)] == ["elodie@ctf.lan", "elodie2@ctf.lan"]


def test_apply_creates_verified_accounts_hidden_test(mod):
    api = FakeCTFd()
    res = mod.apply(api, mod.plan([], 2, test=True), rng=Rng())
    posts = [d for m, p, d in api.calls if m == "POST"]
    assert [d["name"] for d in posts] == ["player01", "player02", "test"]
    assert all(d["verified"] and d["email"].endswith("@ctf.lan") and d["password"] for d in posts)
    assert [d["hidden"] for d in posts] == [False, False, True]
    assert all(p for _n, p, _s in res)


def test_existing_accounts_kept_unless_reset(mod):
    api = FakeCTFd(existing=["player01"])
    res = mod.apply(api, mod.plan([], 2, test=False), rng=Rng())
    assert res[0][1] is None and "existe" in res[0][2]                 # left untouched
    assert not any(m == "PATCH" for m, _p, _d in api.calls)
    api = FakeCTFd(existing=["player01"])
    res = mod.apply(api, mod.plan([], 1, test=False), reset=True, rng=Rng())
    patch = [(p, d) for m, p, d in api.calls if m == "PATCH"]
    assert patch and patch[0][0] == "/users/1" and patch[0][1]["password"] == res[0][1]


def test_main_writes_private_list_and_can_close_signup(mod, tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("CTFD_TOKEN=ctfd_x\nCTF_HOST=ctf.lan\n")
    api = FakeCTFd()
    monkeypatch.setattr(mod, "CTFd", lambda url, token: api)
    out = tmp_path / "comptes.txt"
    assert mod.main(["--count", "2", "--test", "--close-registration",
                     "--env", str(env), "--out", str(out)]) == 0
    text = out.read_text()
    assert "player01" in text and "test" in text and "http://ctf.lan:8000" in text
    assert stat.S_IMODE(os.stat(out).st_mode) == 0o600
    assert ("PATCH", "/configs", {"registration_visibility": "private"}) in api.calls


def test_dry_run_needs_no_token(mod, tmp_path, capsys):
    assert mod.main(["--count", "1", "--dry-run", "--env", str(tmp_path / "none")]) == 0
    assert "player01@ctf.lan" in capsys.readouterr().out


def test_rerun_without_reset_keeps_noted_passwords(mod, tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text("CTFD_TOKEN=ctfd_x\n")
    out = tmp_path / "comptes.txt"
    api = FakeCTFd()
    monkeypatch.setattr(mod, "CTFd", lambda url, token: api)
    mod.main(["--count", "2", "--env", str(env), "--out", str(out)])
    first = mod.read_list(str(out))
    assert set(first) == {"player01", "player02"}
    mod.main(["--count", "3", "--env", str(env), "--out", str(out)])       # 01, 02 exist; 03 is new
    second = mod.read_list(str(out))
    assert second["player01"] == first["player01"] and second["player02"] == first["player02"]
    assert "player03" in second
    assert "--reset" in capsys.readouterr().out                          # tells how to change them
    mod.main(["--count", "1", "--reset", "--env", str(env), "--out", str(out)])
    assert mod.read_list(str(out))["player01"] != first["player01"]       # reset: new one noted
