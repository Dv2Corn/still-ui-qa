"""Boundary values of the client "traffic limit" field (totalGB) and API/UI consistency.

The API field is called totalGB but stores BYTES; 0 means "no limit".
Equivalence classes: negative | 0 | positive | not an integer. Boundaries: -1, 0, 1.
"""
import re
import uuid

import pytest

from conftest import PANEL


@pytest.fixture
def inbound_id(client_with_sub):
    return client_with_sub["inbound_id"]


@pytest.fixture
def email(admin):
    name = f"qa-{uuid.uuid4().hex[:8]}"
    yield name
    admin.post(f"{PANEL}/panel/api/clients/del/{name}", timeout=10)


def add_client(admin, email, inbound_id, total_bytes=0):
    return admin.post(
        f"{PANEL}/panel/api/clients/add",
        json={"client": {"email": email, "enable": True, "totalGB": total_bytes}, "inboundIds": [inbound_id]},
        timeout=10,
    ).json()


def get_client(admin, email):
    return admin.get(f"{PANEL}/panel/api/clients/get/{email}", timeout=10).json()


@pytest.mark.parametrize("value", [0, 1, 10 * 1024**3])
def test_traffic_limit_valid_values_are_saved_as_is(admin, inbound_id, email, value):
    assert add_client(admin, email, inbound_id, value)["success"]
    assert get_client(admin, email)["obj"]["client"]["totalGB"] == value


@pytest.mark.parametrize("value", [1.5, "10"])
def test_traffic_limit_not_an_integer_is_rejected(admin, inbound_id, email, value):
    assert add_client(admin, email, inbound_id, value)["success"] is False
    # and the client must not be half-created
    assert get_client(admin, email)["success"] is False


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "Known finding: the UI form clamps the field at 0, but the API accepts and stores -1. "
    "When it is fixed this test passes unexpectedly and strict xfail asks to remove the marker."
))
def test_traffic_limit_negative_is_rejected(admin, inbound_id, email):
    assert add_client(admin, email, inbound_id, -1)["success"] is False


# --- UI: the same field and the same data, seen through the browser ---

def _logged_in(page):
    from test_ui_login import fill_login
    from conftest import PASSWORD, USER
    fill_login(page, USER, PASSWORD)
    page.wait_for_url(re.compile("/panel/"), timeout=15000)
    return page


@pytest.mark.ui
def test_client_added_via_api_is_visible_in_ui(admin, inbound_id, email, page):
    from playwright.sync_api import expect
    assert add_client(admin, email, inbound_id)["success"]
    _logged_in(page).goto(PANEL + "/panel/clients")
    expect(page.get_by_text(email)).to_be_visible(timeout=15000)


@pytest.mark.ui
def test_traffic_limit_field_in_ui_does_not_go_below_zero(page):
    _logged_in(page).goto(PANEL + "/panel/clients")
    page.get_by_role("button", name=re.compile("add client", re.I)).first.click()
    field = page.get_by_label(re.compile("traffic limit", re.I))
    field.fill("-5")
    field.blur()
    # Ant Design InputNumber with min=0 corrects the value itself
    assert field.input_value() == "0"
