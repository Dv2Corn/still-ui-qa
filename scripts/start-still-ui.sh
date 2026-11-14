#!/bin/sh
# Starts a throwaway still-ui panel from a release tarball in a Debian container.
# Env: STILL_UI_VERSION (default v1.8.0), DOCKER_NET_ARGS (default: publish 2053 and 2096 on 127.0.0.1),
#      QA_USER / QA_PASSWORD (test-only credentials for this disposable panel).
set -eu
VERSION="${STILL_UI_VERSION:-v1.8.0}"
NET_ARGS="${DOCKER_NET_ARGS:--p 127.0.0.1:2053:2053 -p 127.0.0.1:2096:2096}"
QA_USER="${QA_USER:-qa-admin}"
QA_PASSWORD="${QA_PASSWORD:-qa-pass-123}"
WORK="${WORK_DIR:-$PWD/.still-ui}"
BASE="https://github.com/Dv2Corn/still-ui/releases/download/$VERSION"

mkdir -p "$WORK"
cd "$WORK"
if [ ! -f still-ui-linux-amd64.tar.gz ]; then
  curl -fsSLO "$BASE/still-ui-linux-amd64.tar.gz"
  curl -fsSLO "$BASE/still-ui-linux-amd64.tar.gz.sha256"
fi
sha256sum -c still-ui-linux-amd64.tar.gz.sha256
rm -rf still-ui && tar xzf still-ui-linux-amd64.tar.gz

docker rm -f qa-still-ui >/dev/null 2>&1 || true
# shellcheck disable=SC2086
# Runs as the calling user: no root and no capabilities are needed for these tests.
docker run -d --name qa-still-ui --cap-drop ALL --security-opt no-new-privileges $NET_ARGS \
  --user "$(id -u):$(id -g)" -e HOME=/data \
  -v "$WORK/still-ui:/app" --tmpfs "/data:uid=$(id -u),gid=$(id -g)" -w /app \
  -e XUI_DB_FOLDER=/data -e XUI_LOG_FOLDER=/data -e XUI_BIN_FOLDER=/app/bin \
  debian:12-slim sh -c "/app/x-ui setting -username '$QA_USER' -password '$QA_PASSWORD' -port 2053 -webBasePath / >/dev/null && exec /app/x-ui run"
echo "still-ui $VERSION started in container qa-still-ui"
