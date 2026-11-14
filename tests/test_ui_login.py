"""Login page in a real browser (Playwright)."""
import re

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import Page, expect  # noqa: E402

from conftest import PANEL, PASSWORD, USER  # noqa: E402

pytestmark = pytest.mark.ui


def fill_login(page: Page, username: str, password: str):
    page.goto(PANEL + "/")
    page.locator("input").nth(0).fill(username)
    page.locator("input[type=password]").fill(password)
    page.get_by_role("button", name=re.compile("log ?in|sign ?in", re.I)).click()


def test_login_page_renders(page: Page):
    page.goto(PANEL + "/")
    expect(page.locator("input[type=password]")).to_be_visible()
    expect(page.locator('meta[name="csrf-token"]')).to_have_count(1)


def test_wrong_password_shows_an_error_and_stays_on_login(page: Page):
    fill_login(page, USER, "wrong-password")
    expect(page.get_by_text(re.compile("invalid", re.I))).to_be_visible()
    expect(page).not_to_have_url(re.compile("/panel/"))


def test_correct_password_opens_the_panel(page: Page):
    fill_login(page, USER, PASSWORD)
    expect(page).to_have_url(re.compile("/panel/"), timeout=15000)
