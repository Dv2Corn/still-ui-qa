# BR-002: An HTTP proxy URL ending in "/" makes every request fail

| Field | Value |
|---|---|
| Component | fasthttp — `fasthttpproxy` dialer |
| Version | v1.56.0 and later (regression; v1.55.0 works) |
| Severity | Major — no request goes through the proxy at all |
| Priority | High — `http://host:port/` is a common way to write `HTTP_PROXY` |
| Status | Fixed in [valyala/fasthttp#2548](https://github.com/valyala/fasthttp/pull/2548) |

## Steps to reproduce

1. Set `HTTP_PROXY=http://127.0.0.1:3128/` (note the trailing slash), or pass that URL to `FasthttpHTTPDialer`.
2. Dial any address:
   ```go
   dial := fasthttpproxy.FasthttpHTTPDialer("http://127.0.0.1:3128/")
   _, err := dial("example.com:443")
   ```

## Expected result

The connection is made through the proxy, as with `net/http` and the same URL.

## Actual result

`strconv.Atoi: parsing "3128/": invalid syntax`. No connection is attempted.

## Analysis

The address to dial is built as `pu.Host + pu.Path`, so the path ends up in the port. This came in with the `Dialer` refactoring in v1.56.0; earlier versions dialed only the host.

## Test matrix used to confirm the fix

| URL | proxy chosen once | proxy chosen per dial |
|---|---|---|
| `http://host:port/` | fail → pass | fail → pass |
| `http://user:pass@host:port/` | fail → pass | fail → pass |

## Known limitation (separate issue)

A proxy URL without a port (`http://proxy.local`) still fails with `missing port in address`; choosing a default port is a separate decision.
