#!/bin/bash
# Map container user to host UID/GID (from /home/user/hostcwd) so writes to the
# bind-mounted project work. Then exec Buildozer from the venv as that user.
set -euo pipefail
DEFAULT_USER_NAME="user"
DEFAULT_USER_HOME="/home/$DEFAULT_USER_NAME"

# Read UID/GID from bind mount; default to 1000:1000 if absent
HOST_UID="$(stat -c %u "$DEFAULT_USER_HOME/hostcwd" 2>/dev/null || echo 1000)"
HOST_GID="$(stat -c %g "$DEFAULT_USER_HOME/hostcwd" 2>/dev/null || echo 1000)"

# Create group with host GID if it doesn't exist (используем sudo)
if ! getent group $HOST_GID > /dev/null 2>&1; then
    sudo groupadd --gid $HOST_GID hostgroup
fi

# Check if UID already exists
if getent passwd $HOST_UID > /dev/null 2>&1; then
    USER_NAME="$(getent passwd $HOST_UID | cut -d: -f1)"
else
    USER_NAME="$DEFAULT_USER_NAME"
    # Используем sudo для создания пользователя
    sudo useradd --uid $HOST_UID --gid $HOST_GID --home "$DEFAULT_USER_HOME" --shell /bin/bash --no-create-home "$DEFAULT_USER_NAME"
fi

# Ensure home directory and venv ownership (используем sudo)
sudo chown --recursive $HOST_UID:$HOST_GID "$DEFAULT_USER_HOME"

# Switch to the user and execute buildozer
BUILDOZER="$DEFAULT_USER_HOME/.venv/bin/buildozer"
# Запускаем buildozer от имени найденного пользователя
exec sudo --preserve-env --user "$USER_NAME" HOME="$DEFAULT_USER_HOME" PATH="$DEFAULT_USER_HOME/.venv/bin:$PATH" -- "$BUILDOZER" "$@"
