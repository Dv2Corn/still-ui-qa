"""Brute-force protection. Runs last (file order): it locks the admin login
from this address for 15 minutes, so every other test logs in before it."""
import requests

from conftest import PANEL, PASSWORD, USER, login

MAX_FAILURES = 5  # still-ui: 5 failures per (address, username) in 5 minutes


def test_correct_password_is_refused_after_too_many_failures():
    for _ in range(MAX_FAILURES):
        assert login(requests.Session(), USER, "wrong-password").json()["success"] is False
    body = login(requests.Session(), USER, PASSWORD).json()
    assert body["success"] is False, "login still open after repeated failures"


def test_existing_session_keeps_working_during_the_lockout(admin):
    r = admin.get(f"{PANEL}/panel/api/inbounds/list", timeout=10)
    assert r.status_code == 200
