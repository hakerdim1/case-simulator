#!/bin/bash
set -euo pipefail

HOST_UID="$(stat -c %u /home/user/hostcwd)"
HOST_GID="$(stat -c %g /home/user/hostcwd)"

CURRENT_UID="$(id -u user)"
CURRENT_GID="$(id -g user)"

if [ "$HOST_UID" != "$CURRENT_UID" ]; then
    usermod -u "$HOST_UID" user
fi

if [ "$HOST_GID" != "$CURRENT_GID" ]; then
    groupmod -g "$HOST_GID" user
fi

chown -R "$HOST_UID:$HOST_GID" /home/user

# 👇 Используем абсолютный путь к buildozer в виртуальном окружении 👇
exec sudo -u user -E HOME=/home/user \
    PATH=/home/user/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    /home/user/.venv/bin/buildozer "$@"
