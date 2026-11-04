"""
Check a player's scoreboard (CTFd) credentials from the hub, server to server.

The hub signs players in with their CTFd account: one name and password for
the scoreboard, the Bloc-notes and the mission statuses. It does what CTFd's
own login page does, on the Pi's internal Docker network (CTFD_INTERNAL_URL,
http://ctfd:8000 offline), checked against CTFd 3.8.8 (CTFd/auth.py login(),
CTFd/utils/initialization csrf check):

1. GET /login       -> a session cookie and the form's CSRF "nonce"
2. POST /login      name (or e-mail), password, nonce
                    -> 302 on success, 200 with "incorrect" on a wrong password,
                       403 on a bad nonce, 429 when rate-limited (10 per 5 s)
3. GET /api/v1/users/me -> the account's exact name (the player may have typed
                       the e-mail, or other capitals)
4. GET /logout      -> drop that CTFd session again

Standard library only (urllib), short timeouts. The player's browser is never
involved, and nothing is stored here: notes.py keeps a hash of the password so
players can still sign in while CTFd is down.
"""
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 4
NONCE_RE = re.compile(r'name="nonce"[^>]*value="([^"]+)"|value="([^"]+)"[^>]*name="nonce"')
OK, BAD, DOWN, BUSY = "ok", "bad", "down", "busy"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):   # keep the 302 so success can be told apart
        return None


def _opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), _NoRedirect())


def _open(opener, url, data=None):
    """(status, headers, body text); HTTP errors are answers too."""
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": "decaflop-hub"})
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            return r.status, r.headers, r.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read(200_000).decode("utf-8", "replace") if e.fp else ""


def check(base, name, password):
    """(OK, exact CTFd name) | (BAD, None) | (DOWN, None) | (BUSY, None)."""
    base = base.rstrip("/")
    op = _opener()
    try:
        status, headers, page = _open(op, base + "/login")
        if status in (301, 302, 303, 307, 308):           # /setup not finished yet
            return DOWN, None
        m = NONCE_RE.search(page) if status == 200 else None
        if not m:
            return DOWN, None
        nonce = m.group(1) or m.group(2)
        status, headers, page = _open(op, base + "/login", {"name": name, "password": password, "nonce": nonce})
        if status == 429:
            return BUSY, None
        if status in (302, 303):
            loc = headers.get("Location", "")
            if "/login" in urllib.parse.urlsplit(loc).path:
                return BAD, None
            exact = name
            st, _h, me = _open(op, base + "/api/v1/users/me")
            if st == 200:
                try:
                    exact = json.loads(me)["data"]["name"] or name
                except (ValueError, KeyError, TypeError):
                    pass
            _open(op, base + "/logout")
            return OK, exact
        if status == 200:
            return BAD, None
        return DOWN, None
    except (urllib.error.URLError, OSError, ValueError):
        return DOWN, None
