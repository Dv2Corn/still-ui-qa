"""Subscription server: a client fetches its links by subscription id."""
import base64
from urllib.parse import urlparse

import requests

from conftest import PANEL, SUB


def fetch(sub_path, sub_id, **kw):
    return requests.get(f"{SUB}{sub_path}{sub_id}", timeout=10, **kw)


def test_subscription_returns_the_clients_link(sub_path, client_with_sub):
    r = fetch(sub_path, client_with_sub["sub_id"])
    assert r.status_code == 200
    links = base64.b64decode(r.text).decode().split()
    assert len(links) == 1
    link = urlparse(links[0])
    assert link.scheme == "vless"
    assert link.username == client_with_sub["client_id"]


def test_subscription_sends_usage_headers(sub_path, client_with_sub):
    r = fetch(sub_path, client_with_sub["sub_id"])
    info = dict(p.strip().split("=") for p in r.headers["Subscription-Userinfo"].split(";"))
    assert set(info) == {"upload", "download", "total", "expire"}
    assert int(r.headers["Profile-Update-Interval"]) > 0


def test_unknown_subscription_id_is_not_found(sub_path):
    assert fetch(sub_path, "no-such-subscription").status_code == 404


def test_subscription_ids_are_not_served_on_the_panel_port(sub_path, client_with_sub):
    r = requests.get(f"{PANEL}{sub_path}{client_with_sub['sub_id']}", timeout=10)
    assert "vless://" not in r.text
    assert client_with_sub["client_id"] not in r.text


def test_disabled_client_is_reported_as_disabled(admin, sub_path, client_with_sub):
    info = fetch(sub_path, client_with_sub["sub_id"], params={"format": "info"}).json()
    assert info["enabled"] is True
    r = admin.post(
        f"{PANEL}/panel/api/clients/update/{client_with_sub['email']}",
        json={"email": client_with_sub["email"], "enable": False},
        timeout=10,
    )
    assert r.json()["success"], r.text
    # By design the link list stays the same (the proxy core refuses the client);
    # the status page and the info endpoint must show the change.
    info = fetch(sub_path, client_with_sub["sub_id"], params={"format": "info"}).json()
    assert info["enabled"] is False
    assert info["emails"] == [client_with_sub["email"]]


def test_html_page_for_browsers(sub_path, client_with_sub):
    r = fetch(sub_path, client_with_sub["sub_id"], headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("text/html")
