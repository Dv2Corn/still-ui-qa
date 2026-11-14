import os
import time
import uuid

import pytest
import requests

PANEL = os.environ.get("PANEL_URL", "http://127.0.0.1:2053")
SUB = os.environ.get("SUB_URL", "http://127.0.0.1:2096")
USER = os.environ.get("QA_USER", "qa-admin")
PASSWORD = os.environ.get("QA_PASSWORD", "qa-pass-123")


def csrf_token(session):
    r = session.get(f"{PANEL}/csrf-token", timeout=5)
    r.raise_for_status()
    return r.json()["obj"]


def login(session, username, password, with_csrf=True):
    headers = {"X-CSRF-Token": csrf_token(session)} if with_csrf else {}
    return session.post(
        f"{PANEL}/login",
        data={"username": username, "password": password},
        headers=headers,
        timeout=10,
    )


@pytest.fixture(scope="session", autouse=True)
def panel_ready():
    deadline = time.monotonic() + 60
    while True:
        try:
            if requests.get(f"{PANEL}/csrf-token", timeout=2).ok:
                return
        except requests.ConnectionError:
            pass
        if time.monotonic() > deadline:
            pytest.fail(f"panel did not come up at {PANEL}")
        time.sleep(1)


@pytest.fixture(scope="session")
def admin():
    """A logged-in session that sends the CSRF token on every request."""
    s = requests.Session()
    r = login(s, USER, PASSWORD)
    assert r.json()["success"], r.text
    s.headers["X-CSRF-Token"] = csrf_token(s)
    return s


@pytest.fixture(scope="session")
def sub_path(admin):
    r = admin.post(f"{PANEL}/panel/api/setting/all", timeout=10)
    return r.json()["obj"]["subPath"]


@pytest.fixture
def client_with_sub(admin):
    """A VLESS inbound with one client; removed after the test."""
    sub_id = "qa" + uuid.uuid4().hex[:12]
    client_id = str(uuid.uuid4())
    email = f"qa-{sub_id}"
    r = admin.post(
        f"{PANEL}/panel/api/inbounds/add",
        json={
            "enable": True,
            "remark": "qa",
            "listen": "",
            "port": 20000 + int(sub_id[-4:], 16) % 20000,
            "protocol": "vless",
            "settings": {
                "clients": [{"id": client_id, "email": email, "subId": sub_id, "enable": True}],
                "decryption": "none",
            },
            "streamSettings": {"network": "tcp", "security": "none"},
            "sniffing": {"enabled": False},
        },
        timeout=10,
    )
    body = r.json()
    assert body["success"], body
    inbound_id = body["obj"]["id"]
    yield {"sub_id": sub_id, "client_id": client_id, "email": email, "inbound_id": inbound_id}
    admin.post(f"{PANEL}/panel/api/inbounds/del/{inbound_id}", timeout=10)
