# Test plan: still-ui panel — login and subscription

## 1. Scope

**System under test:** [still-ui](https://github.com/Dv2Corn/still-ui) v1.8.0, an open-source web panel for proxy servers (a fork of 3x-ui). It has two HTTP listeners:

- the **admin panel** (port 2053);
- the **subscription server** (port 2096), where end-user apps download their connection links.

**In scope**

| Area | What is checked |
|---|---|
| Authentication | login with valid / invalid / empty credentials, error message wording |
| CSRF protection | state-changing requests need the per-session token |
| Brute-force protection | lockout after repeated failures, existing sessions unaffected |
| Access control | admin API refuses anonymous requests |
| Subscription | links by subscription id, metadata headers, unknown id, disabled client, HTML view |
| Login UI | page renders, error shown, successful login navigates to the panel |

**Out of scope (this iteration):** proxy traffic itself (Xray), Telegram bot, multi-node sync, two-factor authentication, PostgreSQL backend, performance and load.

## 2. Approach

- **Black-box API tests** (pytest + requests) against a real panel built from the published release, not a mock.
- **UI tests** (Playwright, Chromium) for the user-visible login flow only. The API layer is covered by the faster tests, so UI tests stay few.
- **Test design techniques:**
  - equivalence classes (valid / wrong / empty credentials);
  - negative testing (missing or foreign CSRF token, unknown subscription id);
  - state transition (enabled → disabled client; open → locked login);
  - error guessing (the same error for a wrong user and a wrong password; subscription ids not leaking through the panel port).
- **Isolation:** each subscription test creates its own inbound and client and deletes it afterwards. The lockout test runs last because it locks the admin login for 15 minutes.

## 3. Environment

- still-ui v1.8.0 release tarball, SHA-256 verified against the published checksum, started in a `debian:12-slim` container with all Linux capabilities dropped.
- Fresh SQLite database on every run (tmpfs), test-only credentials.
- CI: GitHub Actions, `ubuntu-24.04`, Python 3.12, Playwright 1.48.

## 4. Entry and exit criteria

- **Entry:** the panel answers `GET /csrf-token` within 60 s.
- **Exit:** all tests pass. A failure blocks the run, and the workflow prints the panel log.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Lockout test locks out later tests | file order puts it last; the session-scoped admin login happens earlier |
| Random subscription path on fresh panels | read `subPath` from the settings API instead of hard-coding it |
| Port clash between test inbounds | the port is derived from a random id; inbounds are deleted after each test |
| UI text changes between releases | locators use roles and input types, with case-insensitive text matching |

## 6. Traceability

See the coverage matrix in [README.md](README.md#coverage-matrix).
