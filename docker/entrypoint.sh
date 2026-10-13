#!/usr/bin/env bash

set -Eeuo pipefail

cd /workspace

VENV_PATH="${UV_PROJECT_ENVIRONMENT:-/workspace/.venv}"
UV_CACHE_PATH="${UV_CACHE_DIR:-/home/django/.cache/uv}"
UV_VENV_CLEAR=1

mkdir -p "${UV_CACHE_PATH}"

# A directory without pyvenv.cfg is not a valid virtual environment.
if [[ -d "${VENV_PATH}" && ! -f "${VENV_PATH}/pyvenv.cfg" ]]; then
    echo "Removing incomplete virtual environment..."
    rm -rf "${VENV_PATH:?}"/*
    rm -rf "${VENV_PATH}"/.[!.]* "${VENV_PATH}"/..?* 2>/dev/null || true
fi

if [[ ! -f "${VENV_PATH}/pyvenv.cfg" ]]; then
    echo "Creating container development environment..."
    uv venv "${VENV_PATH}"
fi

# uv skips packages that already satisfy the requirements, while this also
# repairs persistent environments that are incomplete or out of date.
echo "Ensuring Django and test dependencies are installed..."

uv pip install --python "${VENV_PATH}/bin/python" --editable .
uv pip install \
    --python "${VENV_PATH}/bin/python" \
    --requirements tests/requirements/py3.txt
uv pip install \
    --python "${VENV_PATH}/bin/python" \
    --requirements tests/requirements/postgres.txt
uv pip install \
    --python "${VENV_PATH}/bin/python" \
    tox \
    pre-commit


exec "$@"
