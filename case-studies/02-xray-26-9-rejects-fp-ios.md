# Xray ≥ 26.9 silently rejects common client profiles: a compatibility matrix before an upgrade

**Type:** upstream compatibility regression · **Found in:** pre-upgrade lab testing · **Severity:** critical if shipped (users of the affected client profiles lose the connection; the server shows no error)

## Context

Xray-core with VLESS + REALITY is served to many different client apps: some built on Xray-core itself,
others on sing-box or mihomo (Hiddify, Karing, Clash-based apps). Clients pick a uTLS fingerprint
(`chrome`, `firefox`, `safari`, `ios`, …) that shapes their TLS ClientHello. Before upgrading the server
core, the question was simple: will every client in use still connect?

## Problem / risk

Starting with the first published release that includes it (26.9.9), the REALITY server in Xray-core
rejects any ClientHello without an X25519MLKEM768 (post-quantum) key share. The uTLS `ios` profile has none,
and sing-box and mihomo send none by default with any fingerprint.

A rejected hello is not logged as an error. REALITY treats it as an ordinary visitor and forwards it to the
decoy site, so the client gets the decoy's real certificate and fails. A routine upgrade would have cut off
those clients while every server-side health check stayed green.

## How it was found

A compatibility matrix on a lab machine, everything on loopback, fresh keys per run:

- **Servers:** Xray 26.6.27 (the current version), 26.7.28, 26.9.9, 26.10.31.
- **Clients:** Xray 26.6.27 and 26.10.31 with fingerprints ios, chrome, firefox, safari (plus edge, qq);
  sing-box 1.12.12 and 1.14.4; mihomo 1.19.33.
- **Cell result:** successful HTTPS requests through the client's SOCKS port out of N tries.

| Server | Xray client chrome / firefox / safari | Xray client ios / edge / qq | sing-box, any fp | mihomo | mihomo with `support-x25519mlkem768: true` |
|---|---|---|---|---|---|
| 26.6.27 | ok | ok | ok | ok | ok |
| 26.7.28 | ok | ok | refused | refused | refused |
| 26.9.9 | ok | **refused** | **refused** | **refused** | ok |
| 26.10.31 | ok | **refused** | **refused** | **refused** | ok |

Side finding: 26.7.11–26.7.28 refuse sing-box and mihomo for a different reason (a default minimum client
version), so those releases were never an upgrade option either.

## Reproduction steps

1. Start an Xray 26.10.31 server with a VLESS + REALITY inbound on loopback.
2. Start an Xray client with `fingerprint: ios`; request `https://www.gstatic.com/generate_204` through its
   SOCKS port. **Actual:** no response (curl code `000`); the client sees the decoy's real certificate.
3. Same client with `fingerprint: chrome` → `204`.
4. Replace the server with 26.6.27 → both fingerprints `204`.
5. sing-box 1.12.12 with any fingerprint → refused by 26.10.31, accepted by 26.6.27.

## Root cause

A hardening change in the REALITY library (rejecting "outdated/strange" ClientHello messages) requires an
X25519MLKEM768 key share before the optional X25519 one. Clients that send only X25519 are treated as
non-REALITY traffic. It is a deliberate upstream decision, not a bug — but it breaks clients that are
widely used.

## Decision

The upgrade was stopped and the current version pinned, with a written "do not upgrade until the matrix is
green" rule. Options for moving forward were listed and weighed: wait for client apps to send the
post-quantum key share by default, change client fingerprints, or carry a minimal upstream patch. Each new
Xray release goes through the same matrix before it reaches a server.

## Lessons

- **Test the clients you actually have.** The reference client with `chrome` works on every version; the
  breakage was visible only with `ios`, sing-box and mihomo.
- **Silent failures need client-side checks.** The server cannot see this failure; only a real client can.
- **A compatibility matrix is a release gate** for core upgrades, not a one-off experiment.
- **Next:** run the matrix automatically in CI for each upstream release.

---
The fingerprint compatibility table is maintained in [xui-doctor](https://github.com/Dv2Corn/xui-doctor), a read-only health checker for 3x-ui and still-ui panels.
