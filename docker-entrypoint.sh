#!/bin/sh
set -e
# Bind-mount ./logs с хоста часто root:root — appuser (uid 1000) не может писать.
mkdir -p /app/logs
chown -R appuser:appuser /app/logs 2>/dev/null || true
exec runuser -u appuser -- "$@"
