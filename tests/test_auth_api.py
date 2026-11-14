"""Login and CSRF checks on the panel's HTTP API."""
import requests

from conftest import PANEL, PASSWORD, USER, csrf_token, login


def test_csrf_token_is_issued_per_session():
    a, b = requests.Session(), requests.Session()
    ta, tb = csrf_token(a), csrf_token(b)
    assert len(ta) >= 32
    assert ta != tb
    assert csrf_token(a) == ta  # stable within one session


def test_login_without_csrf_token_is_rejected():
    r = login(requests.Session(), USER, PASSWORD, with_csrf=False)
    assert r.status_code == 403


def test_login_with_a_foreign_csrf_token_is_rejected():
    other = requests.Session()
    token = csrf_token(other)
    s = requests.Session()
    csrf_token(s)  # s has its own token; sending another session's token must fail
    r = s.post(f"{PANEL}/login", data={"username": USER, "password": PASSWORD},
               headers={"X-CSRF-Token": token}, timeout=10)
    assert r.status_code == 403


def test_login_with_wrong_password_fails_without_hinting_which_field():
    r = login(requests.Session(), USER, "definitely-wrong")
    body = r.json()
    assert body["success"] is False
    # same message for a wrong user and a wrong password: no account enumeration
    r2 = login(requests.Session(), "no-such-user", "definitely-wrong")
    assert r2.json()["msg"] == body["msg"]


def test_login_with_empty_password_is_refused():
    body = login(requests.Session(), USER, "").json()
    assert body["success"] is False


def test_successful_login_opens_the_api():
    s = requests.Session()
    assert login(s, USER, PASSWORD).json()["success"] is True
    r = s.get(f"{PANEL}/panel/api/inbounds/list", timeout=10)
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_api_without_login_is_not_served():
    r = requests.get(f"{PANEL}/panel/api/inbounds/list", timeout=10, allow_redirects=False)
    assert r.status_code in (401, 404)
