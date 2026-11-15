#!/bin/bash
set -euo pipefail

HOST_UID="$(stat -c %u /home/user/hostcwd)"
HOST_GID="$(stat -c %g /home/user/hostcwd)"

# Получаем текущие UID и GID пользователя user
CURRENT_UID="$(id -u user)"
CURRENT_GID="$(id -g user)"

# Если UID на хосте отличается, меняем UID пользователя user
if [ "$HOST_UID" != "$CURRENT_UID" ]; then
    usermod -u "$HOST_UID" user
fi

# Если GID на хосте отличается, меняем GID группы user
if [ "$HOST_GID" != "$CURRENT_GID" ]; then
    groupmod -g "$HOST_GID" user
fi

# Меняем владельца домашней директории и проекта на актуальные UID/GID
chown -R "$HOST_UID:$HOST_GID" /home/user

# Запускаем buildozer от имени пользователя user
exec sudo -u user -E HOME=/home/user \
    PATH=/home/user/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    buildozer "$@"
