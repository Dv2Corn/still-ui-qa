# still-ui QA

[![tests](https://github.com/Dv2Corn/still-ui-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/Dv2Corn/still-ui-qa/actions/workflows/tests.yml)

Test artifacts and an automated test suite for [still-ui](https://github.com/Dv2Corn/still-ui), an open-source web panel for proxy servers. The suite runs against the real published release in a container, not against mocks.

| Artifact | What it shows |
|---|---|
| [TEST-PLAN.md](TEST-PLAN.md) | scope, approach, test design techniques, environment, exit criteria, risks |
| [case-studies/](case-studies) | four in-depth investigations (below) |
| [bug-reports/](bug-reports) | two bug reports for real bugs I found and fixed upstream (go-redis, fasthttp) |
| [tests/](tests) | API tests (pytest + requests) and UI tests (Playwright) |
| [.github/workflows/tests.yml](.github/workflows/tests.yml) | CI: download the release, verify its checksum, start it, run all tests |

## Case studies

| # | Case | QA technique |
|---|---|---|
| 1 | [3x-ui partial update silently wipes the AmneziaWG pre-shared key](case-studies/01-3x-ui-update-wipes-awg-psk.md) | API integration testing, test-data equivalence classes (present / absent / empty), read-after-write checks, fakes that match reality |
| 2 | [Xray ≥ 26.9 silently rejects common client profiles](case-studies/02-xray-26-9-rejects-fp-ios.md) | compatibility matrix as a release gate, silent-failure detection from the client side |
| 3 | [sing-tun: synthesized UDP replies echo the client's congestion marks](case-studies/03-sing-tun-udp-replies-echo-ecn.md) | protocol compliance (RFC 3168), failing unit test first, upstream fix merged |
| 4 | [72-hour memory soak: a panel fork against its upstream](case-studies/04-72h-panel-memory-soak.md) | soak testing with a control group, telemetry design, A/B experiment, a hypothesis that was only partly right |

## Coverage matrix

| Requirement | Test | Technique | Level |
|---|---|---|---|
| CSRF token issued per session, stable within it | `test_csrf_token_is_issued_per_session` | positive | API |
| Login without a CSRF token is refused | `test_login_without_csrf_token_is_rejected` | negative | API |
| A token from another session is refused | `test_login_with_a_foreign_csrf_token_is_rejected` | negative | API |
| Wrong password fails; same message as for a wrong user | `test_login_with_wrong_password_fails_without_hinting_which_field` | equivalence classes, error guessing | API |
| Empty password is refused | `test_login_with_empty_password_is_refused` | boundary value | API |
| Valid login opens the admin API | `test_successful_login_opens_the_api` | positive | API |
| Admin API refuses anonymous requests | `test_api_without_login_is_not_served` | negative, access control | API |
| Subscription returns the client's link | `test_subscription_returns_the_clients_link` | positive | API |
| Subscription carries usage headers | `test_subscription_sends_usage_headers` | contract | API |
| Unknown subscription id → 404 | `test_unknown_subscription_id_is_not_found` | negative | API |
| Links are not served on the panel port | `test_subscription_ids_are_not_served_on_the_panel_port` | error guessing | API |
| Disabling a client shows on its subscription status | `test_disabled_client_is_reported_as_disabled` | state transition | API |
| Browsers get an HTML page | `test_html_page_for_browsers` | content negotiation | API |
| Login is locked after 5 failures, even with the right password | `test_correct_password_is_refused_after_too_many_failures` | state transition | API |
| Existing session survives the lockout | `test_existing_session_keeps_working_during_the_lockout` | state transition | API |
| Traffic limit: 0, 1 byte, 10 GiB saved as is | `test_traffic_limit_valid_values_are_saved_as_is` | boundary values | API |
| Traffic limit: 1.5 and "10" refused, no half-created client | `test_traffic_limit_not_an_integer_is_rejected` | equivalence classes | API |
| Traffic limit: -1 refused (**known finding**, strict xfail: the API stores it) | `test_traffic_limit_negative_is_rejected` | boundary values | API |
| A client created via the API shows in the UI | `test_client_added_via_api_is_visible_in_ui` | API/UI consistency | UI |
| The traffic-limit field in the UI does not go below 0 | `test_traffic_limit_field_in_ui_does_not_go_below_zero` | boundary values | UI |
| Login page renders with a CSRF meta tag | `test_login_page_renders` | smoke | UI |
| Wrong password shows an error, no navigation | `test_wrong_password_shows_an_error_and_stays_on_login` | negative | UI |
| Correct password opens the panel | `test_correct_password_opens_the_panel` | positive, end to end | UI |

## Run locally

Requires Docker, Python 3.12 and Linux on amd64.

```bash
pip install -r requirements.txt
python -m playwright install chromium
scripts/start-still-ui.sh          # downloads v1.8.0, verifies SHA-256, starts the panel
pytest                             # all tests
pytest -m "not ui"                 # API tests only
docker rm -f qa-still-ui           # clean up
```

`STILL_UI_VERSION` picks another release. The credentials are test-only values for a throwaway panel (`QA_USER`, `QA_PASSWORD`).

## Notes

- `test_traffic_limit_negative_is_rejected` is a documented finding, marked strict xfail: when the panel starts refusing -1, the run turns red and asks to drop the marker.
- `test_zz_login_rate_limit.py` runs last on purpose: it locks the admin login from this address for 15 minutes.
- Each subscription test creates its own inbound and client and deletes them afterwards, so tests do not depend on each other.

## License

MIT
