#!/usr/bin/env bash
# Blacktop Police Chase — launcher offline
# First run (with WiFi): loads game, patches save, caches assets.
# Subsequent runs (no WiFi): launches from cache, fully offline.

EXT_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME_URL="https://poki.com/en/g/blacktop-police-chase"
PROFILE="$EXT_DIR/profile"

# Check connectivity to poki.com
if timeout 4 bash -c 'cat < /dev/null > /dev/tcp/poki.com/443' 2>/dev/null; then
  ONLINE=1
else
  ONLINE=0
fi

if [ "$ONLINE" = "1" ]; then
  echo "[launcher] WiFi detectado — cargando juego y cacheando assets..."
  exec chromium \
    --user-data-dir="$PROFILE" \
    --load-extension="$EXT_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-session-crashed-bubble \
    "$GAME_URL"
else
  echo "[launcher] Sin WiFi — cargando desde cache local..."
  exec chromium \
    --user-data-dir="$PROFILE" \
    --load-extension="$EXT_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-session-crashed-bubble \
    --offline \
    "https://poki.com/en/g/blacktop-police-chase"
fi