# sing-tun: synthesized UDP replies echo the client's congestion marks

**Type:** protocol-compliance defect (RFC 3168) in an open-source networking library · **Found by:** code review + a failing unit test · **Outcome:** fix merged by the project's author ([SagerNet/sing-tun#106](https://github.com/SagerNet/sing-tun/pull/106))

## Context

[sing-tun](https://github.com/SagerNet/sing-tun) is the TUN layer of sing-box: the part that captures all
traffic of a device when a VPN app runs in "TUN mode". It is used by sing-box and by client apps built on it.
The project rarely merges outside pull requests: of 56 from outside contributors in its whole history
(checked 2026-11-08), 14 were merged, 20 closed without merging and 22 are still open.

## Problem / risk

In the "system" stack, sing-tun builds UDP replies itself. It made each reply from a copy of the client's IP
header, swapping addresses and ports and fixing lengths and checksums, but it kept the TOS byte (IPv4) and
traffic class (IPv6) exactly as the client sent them.

Two bits of that byte are ECN (Explicit Congestion Notification). So if a client marked its packets ECT(0),
ECT(1) or CE, every reply carried the same mark back:

- RFC 3168 only allows ECT marks on packets from a transport that actually does ECN. Nothing on this side
  does ECN for these flows.
- A copied CE mark is a false "the network is congested" signal. Congestion-aware traffic (for example QUIC
  or real-time media over UDP) may slow down for no reason.

The project already had an open issue about it (#92).

## How it was found

Starting from the open issue, I read the reply path in `stack_system.go` (the functions that save and
rewrite the client header) and compared what is rewritten with what RFC 3168 requires. Addresses, ports,
lengths and checksums were rewritten; the ECN field was not. That made the expected result easy to state
and to test.

## Reproduction (as a unit test)

1. Build a client UDP packet with DSCP EF and each ECN codepoint: Not-ECT, ECT(1), ECT(0), CE.
2. Do it for IPv4 and for IPv6: 8 cases.
3. Run it through the same functions the stack uses to build a reply.
4. Check the reply: ECN must be Not-ECT; DSCP, the IPv6 flow label, addresses and payload must stay as
   expected; the IPv4 header checksum must be valid.

Before the fix the ECT(1), ECT(0) and CE cases failed for both IP versions (for example TOS `0xb9` instead of
`0xb8`). After it, all 8 passed. Linters and builds for Linux, Windows and macOS were clean.

## Proposed fix

A minimal change, as an outside contributor should make: clear the two ECN bits once, when the header copy is
made. DSCP and the flow label were kept on purpose. In the pull request I also pointed to a similar spot
(ICMP echo replies) that I left out to keep the change small.

## What the maintainer did

The author of sing-box merged it the same day, with no review questions, but reworked it into a broader fix:

- replies are now built from a fresh header instead of a copy of the client's one, so no stray client flag
  can leak into a reply, not only ECN;
- the same problem was fixed in synthesized DNS replies, which I had not found;
- IPv4 replies now get a proper incrementing Identification field.

The commit kept me as its author. My unit test was not kept: it targeted the "copy the header" step, which
no longer exists in the new design.

## Result

- A real standards violation, open as an issue, was closed.
- The defect was found, proven with a failing test and explained precisely enough that the maintainer could
  fix its root cause wider than the report itself.

## Lessons

- For a defect report, a failing test plus the exact lines and the standard it breaks is the most convincing
  form. It needed no discussion.
- An outside contributor should keep the change narrow; the owner can then decide how deep to go.
- Checking "what does this code copy that it should not" is a cheap, effective review technique for code that
  builds packets or messages from a template.
