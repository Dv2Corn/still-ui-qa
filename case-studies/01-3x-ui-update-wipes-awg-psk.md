# 3x-ui partial update silently wipes the AmneziaWG pre-shared key

**Type:** integration defect in a third-party API (3x-ui 3.7.0) · **Found in:** a staging rehearsal · **Severity:** high (client credentials silently changed, the API reports success)

## Context

An application manages VPN clients in a self-hosted 3x-ui panel (Xray-core plus AmneziaWG) through the
panel's HTTP API. A new feature attached one more protocol entry (Hysteria) to existing clients by
rewriting the client record through the API.

## Problem / risk

To attach the new entry, the application sent `POST /panel/api/clients/update/<email>` with the fields as
it read them plus the new value. The body did not include the AmneziaWG `preSharedKey`.

3x-ui 3.7.0 treats a missing `preSharedKey` as "set it to empty", and still answers success. So:

- the client's AmneziaWG key in the panel no longer matched the copy the application held;
- the new protocol entry was not attached when the feature was on.

An earlier test had concluded that the panel "keeps the AmneziaWG keys on update". That was true only for
the private and public keys: the test clients in that run had no pre-shared key, so the difference never
showed.

## How it was found

The application verifies every write: after an update it reads the client back and compares the identity
fields with what it expects, and refuses to continue on any difference.

During a staging rehearsal (a separate stand with a real 3x-ui 3.7.0, 40 clients, 7 of them with a
pre-shared key):

1. Attaching the entry for a new test client logged a conflict; the client's main access was fine.
2. Tracing the call chain showed the read-after-write check reporting that 3x-ui had changed the
   client's `preSharedKey`.
3. A comparison script (printing only booleans, never key values) showed the panel and the application
   disagreeing on the key for the affected clients.
4. A controlled experiment isolated the cause (below).

## Reproduction steps

Environment: 3x-ui 3.7.0, an AmneziaWG inbound, a client that **has** a pre-shared key.

1. Read the client through the API and save all fields.
2. `POST /panel/api/clients/update/<email>` with every field exactly as read, **except** `preSharedKey`.
3. Read the client again and diff all 32 fields.
   - **Actual:** `preSharedKey` and `updatedAt` changed; `preSharedKey` is now empty.
   - **Expected:** only `updatedAt` changes (a partial update should not clear a field it does not mention).
4. Control: repeat step 2 on another client with `preSharedKey` included as read → only `updatedAt` changes.
5. A second update without the field on the same client changes nothing — the key is already empty, so a
   repeated run hides the bug.

## Root cause

- **Upstream behaviour:** the update endpoint is not a true partial update for `preSharedKey`: an absent
  field is written as empty, while the other AmneziaWG keys are kept.
- **Integration side:** the write path built its body from the fields it "needed", assuming the panel keeps
  the rest. The assumption came from a test whose data did not cover "client has a PSK".

## Fix and regression test

- **Fix (same day):** the write now copies `preSharedKey` exactly as read when the client has one, and adds
  nothing when it does not. Re-checked on the same stand with two new clients: key equal on both sides,
  read-after-write check green.
- **Regression test:** the in-memory fake of the panel used by unit tests now behaves like the real 3x-ui
  (an update without `preSharedKey` clears it). The test covers a client with a PSK (the body carries it, the
  stored key is unchanged) and a client without one (the body does not invent it). On the old code it fails
  with the same error seen on staging.
- **Follow-up:** an audit of other partial-update call sites found one more (renewing or disabling a client
  whose key the application does not store). It was not failing yet and was fixed with its own test.

## Result

- Caught by an automatic read-after-write check on staging, root-caused with a controlled experiment, fixed
  with a test the same day. 2 call sites fixed, 2 regression tests added; the test double now models the
  real API.

## Lessons

- **Cover "field present / absent / empty" in test data.** The earlier "keys are kept" conclusion was correct
  for its data and wrong in general.
- **Fakes must copy the real system's quirks.** A fake that "keeps fields" passed while the real panel wiped
  them. Every new external call is now checked once against the real service, not only the fake.
- **Read-after-write verification pays off.** The API said "success"; only the read-back caught it.
- **Next:** a contract test suite against a real panel container for each new panel version, so upstream
  behaviour changes show up before an upgrade.
