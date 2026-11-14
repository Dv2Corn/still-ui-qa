# BR-001: `XRead` with a block time under 1 ms hangs until the read timeout

| Field | Value |
|---|---|
| Component | go-redis — stream and `WAIT` command builders |
| Version | `master` at 73d0e4c (go-redis v9), Redis 8.10.3 |
| Severity | Major — the call blocks ~10 s and fails instead of returning at once |
| Priority | Medium — needs a sub-millisecond value, which a deadline-based block time produces |
| Status | Fixed in [redis/go-redis#4292](https://github.com/redis/go-redis/pull/4292) |

## Steps to reproduce

1. Start Redis 8.10.3 locally.
2. Run:
   ```go
   _, err := rdb.XRead(ctx, &redis.XReadArgs{
   	Streams: []string{"stream", "$"},
   	Block:   500 * time.Microsecond,
   }).Result()
   ```

## Expected result

`err == redis.Nil` after about 1 ms (no new entries in the stream).

## Actual result

After 10.0 s: `read tcp 127.0.0.1:41666->127.0.0.1:6379: i/o timeout`.

## Also affected

`XReadGroup` (`BLOCK`, `CLAIM`), `XClaim` / `XClaimJustID` (min idle time), `Wait`, `WaitAOF`.

## Analysis

The duration is sent as `duration / time.Millisecond`, so 500 µs becomes `0`. For `BLOCK` and `WAIT`, `0` means "no timeout". The client already has `formatMs`, which rounds positive sub-millisecond values up to 1 ms; these six call sites did not use it.

## Evidence

| | XRead(Block: 500µs) | Wait(1, 500µs) |
|---|---|---|
| before | i/o timeout after 10.01 s | i/o timeout after 10.01 s |
| after | `redis: nil` after 20 ms | `0` after 100 ms |

## Regression tests added

`TestSubMillisecondDurationArgs` checks the boundary values 500 µs, 0 and 2500 µs; two integration specs run against a real server.
