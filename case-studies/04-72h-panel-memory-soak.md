# 72-hour memory soak: a VPN panel fork against its upstream

**Type:** long-run reliability test (soak) with a control group · **Found by:** a planned measurement, not a bug report · **Outcome:** no memory leak in 72 h under load, in either panel; one remaining memory risk narrowed to a specific mechanism for a follow-up test

## Context

[3x-ui](https://github.com/MHSanaei/3x-ui) is a popular web panel for Xray-core (about 50k stars).
[still-ui](https://github.com/Dv2Corn/still-ui) is a fork of it I maintain, aimed at small servers that run for
months without attention. Earlier I had found and fixed one source of panel memory growth (the embedded
AmneziaWG relay allocated two fresh 32 KiB buffers per connection; the fix and a short benchmark cut panel
memory under that load from about 400 to about 180 MiB). The fork's README still listed one open item:
*"a multi-day measurement under load to confirm there is no other source of growth"*. This case is that
measurement.

## Problem / risk

A panel process that slowly grows is the typical way such a server dies: after days or weeks the host runs
out of memory, swaps, freezes and drops every VPN user. A short benchmark cannot rule this out; it needs
hours or days of realistic, mixed load. And a number from one panel alone says little: the useful question is
"does the fork behave at least as well as upstream under the same load".

## Test design

**Two identical environments, one variable.** Two containers with the same image and limits (≤ 1 CPU,
2 GiB RAM, no swap). One ran the upstream release 3x-ui v3.11.0, the other still-ui v1.6.0. Both releases
were installed from their published archives, verified against the published checksums. To keep only the
code as the difference, still-ui's own protections were switched off: no memory cap on the service, and Xray
as a child process of the panel, as in upstream.

**The same data.** One database built through the panel API (200 users on VLESS + REALITY, 100 of them also on
VMess and 50 also on AmneziaWG) was copied to both panels.

**The same load, from a third container, all the time:**

- every 5 s a client change in turn: update, disable, enable, reset traffic, add and delete trial users;
- every 10–60 s the API calls the web UI makes (inbound list, online clients, traffic, status, paged client
  list, the UI page itself), and a new login session every 10 minutes;
- every 15 s a subscription download in plain, JSON or Clash format;
- real traffic: VLESS and VMess downloads through the proxies, two long slow downloads, and through
  AmneziaWG 10 new short TCP connections per second plus periodic downloads.

About 860,000 operations per panel per day.

**Sampling.** Every 60 s for each panel: process RSS/PSS/anonymous memory, Go runtime statistics (heap,
objects, goroutines, GC count, from the panel's own pprof endpoint), threads, file descriptors, the Xray
child's memory, database file size, the service cgroup (anonymous vs page cache), OOM kills and restarts.
A report script prints current, peak and the linear trend in MB/h over the whole run and over the last 24 h.

**Isolation.** The lab network had no internet access, and the load generator talked only to the two
panels and a local target server.

## Results (72 h, 4,321 samples per panel)

| Metric | 3x-ui 3.11.0 start → end (peak) | still-ui 1.6.0 start → end (peak) |
|---|---|---|
| Panel RSS, MB | 134 → 152 (178) | 133 → 162 (186) |
| Trend over the last 24 h, MB/h | +0.1 | +0.1 |
| Go heap in use, MB | 79 → 93 (119) | 76 → 108 (121) |
| Goroutines | 141 → 139 | 143 → 142 |
| File descriptors | 26 → 30 | 25 → 29 |
| Xray RSS, MB | 37 → 38 | 35 → 35 |
| Restarts / OOM kills | 0 / 0 | 0 / 0 |

- **No leak in either panel.** After the first hours of warm-up, memory, goroutines and descriptors stayed
  flat; a trend of +0.1 MB/h is within the noise of a garbage-collected process.
- **The cgroup grew, but not from a leak.** The service cgroup went from about 100 to 210 MB in both. Split
  by type: anonymous memory +50–60 MB, almost all in the first hours (warm-up), and page cache +55 MB (log
  files and the database, which grew from 2 to 5 MB). Page cache can be reclaimed by the kernel, so it is not
  a risk.
- **The fork is not worse than upstream.** Both panels ended within 10 MB of each other on every metric.
- **One background failure rate, equal in both.** About 11–12% of the short AmneziaWG connections timed out,
  the same in both panels and steady over the three days. Because it was the same with the same load
  generator, it points at the lab client side, not at either panel; it did not change the memory result.

## What the soak did *not* cover, and the follow-up

In the soak, AmneziaWG clients read their data quickly. A separate short test (H1) looked at a case the soak cannot show: many
**slow** clients through the embedded AmneziaWG. There, memory is not in the Go heap at all: the kernel
buffers of the relay's local TCP connections grow while data waits for a slow client, and that memory is
charged to the panel's cgroup.

**H1 test design.** A fresh upstream panel (3x-ui v3.11.0, 2 CPUs, 2 GiB) and 16 AmneziaWG clients. Phases:
idle; 28 slow streams at 50 KB/s for 5 minutes; idle; 56 slow streams; idle; then full-speed downloads
(1 and 4 streams) to see whether any change costs throughput. The same sampler as above, plus the kernel
socket memory of the cgroup and the queued bytes per socket group: loopback receive/send queues (relay ↔ Xray)
and the external receive queue (Xray ↔ the target). Three runs:

1. the official release binary;
2. the same version built from source (to prove the build is equivalent);
3. that build with one experimental change: the relay's loopback socket receive buffer capped at 256 KiB.

(The first scheduled pass of run 3 silently used the stock binary: copying the patched build over a
root-owned file had failed. The pass was kept as an extra baseline and run 3 was repeated with the real
build. A check that the binary under test is the one you built belongs in every A/B script.)

| 56 slow streams, peak | cgroup | kernel socket memory | relay's loopback receive buffers |
|---|---|---|---|
| stock (release binary and source build, four runs) | 890–1,059 MB | 652–755 MB | 169–240 MB |
| same source build, no cap | 891 MB | 652 MB | 169 MB |
| same source build, relay buffer capped | 732 MB | 508 MB | 23 MB |

- **The memory is real but not a leak.** With 56 slow clients the panel's cgroup reached about 1 GB, while the
  Go heap stayed near 250 MB. Each slow stream pins about 12–13 MB of kernel socket buffers along the chain:
  about 3–4 MB in the relay's receive buffer, about 3.5 MB queued on Xray's sending side of the same loopback
  hop, and about 5 MB in Xray's receive buffer from the target. TCP auto-tuning grows each buffer while the slow
  client holds the data back. It scales with the number of slow connections (half of it at 28 streams) and
  drops to zero within seconds after they close.
- **The hypothesis was only partly right.** Capping the relay's receive buffer shrank that queue from 169 to
  23 MB, but total socket memory fell only 22%: Xray's own buffers stayed the same, and memory still grows with
  every slow connection. A relay-only change saves about 4 MB per slow client; it does not bound the total.
- **No throughput cost was visible** (about 258 MB/s for one stream and 284 MB/s for four, with and without the
  cap).
- The source build matched the release binary closely enough to trust experiments on it.

Practical conclusion: on a 2 GB server, many slow AmneziaWG clients through the embedded relay can take
hundreds of megabytes of kernel memory charged to the panel. The levers are system-wide (the `tcp_rmem` and
`tcp_wmem` limits) or a cgroup memory cap on the service, under which the kernel applies TCP memory pressure
instead of letting the host swap. still-ui already sets such a cap by default.

## Lessons

- A soak test needs a control group. "Our panel used 160 MB after three days" means nothing; "the same as
  upstream under the same load, with a flat trend" is a result.
- Separate anonymous memory from page cache before calling growth a leak. Half of the cgroup growth here was
  cache.
- Watch more than RSS: goroutines and file descriptors catch leaks that memory alone hides, and Go runtime
  statistics tell heap growth from fragmentation.
- Switch off the system-under-test's own protections when comparing code, or the protection becomes the
  difference you measure.
- Note what the test does not cover. The fast-client soak was clean, and the slow-client case needed its own
  test.
