#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

URL="http://127.0.0.1:8000"
VENV_DIR="$ROOT_DIR/.venv"
BREW_BIN=""

log() {
  printf '\n[%s] %s\n' "doc-toolkit" "$1"
}

fail() {
  printf '\n[%s] %s\n' "doc-toolkit" "$1" >&2
  exit 1
}

detect_brew() {
  if command -v brew >/dev/null 2>&1; then
    BREW_BIN="$(command -v brew)"
    return 0
  fi
  if [ -x /opt/homebrew/bin/brew ]; then
    BREW_BIN="/opt/homebrew/bin/brew"
    return 0
  fi
  if [ -x /usr/local/bin/brew ]; then
    BREW_BIN="/usr/local/bin/brew"
    return 0
  fi
  return 1
}

ensure_brew() {
  if detect_brew; then
    return 0
  fi

  log "Homebrew not found. Installing Homebrew."
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  detect_brew || fail "Homebrew installation completed, but brew was not found in expected locations."
}

brew_prefix_for() {
  "$BREW_BIN" --prefix "$1" 2>/dev/null || true
}

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    local py_major py_minor
    py_major="$(python3 -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)"
    py_minor="$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)"
    if [ "$py_major" -gt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -ge 11 ]; }; then
      return 0
    fi
  fi

  ensure_brew
  log "Python 3.11+ not found. Installing with Homebrew."
  "$BREW_BIN" install python@3.11

  local py_prefix
  py_prefix="$(brew_prefix_for python@3.11)"
  if [ -n "$py_prefix" ]; then
    export PATH="$py_prefix/bin:$PATH"
  fi

  command -v python3 >/dev/null 2>&1 || fail "Python 3.11 installation failed."
}

ensure_node() {
  local install_node=0

  if ! command -v node >/dev/null 2>&1; then
    install_node=1
  else
    local major
    major="$(node -v | sed 's/^v//' | cut -d. -f1)"
    if [ "${major:-0}" -lt 20 ]; then
      install_node=1
    fi
  fi

  if [ "$install_node" -eq 0 ] && command -v npm >/dev/null 2>&1; then
    return 0
  fi

  ensure_brew
  log "Installing Node.js 22 with Homebrew."
  "$BREW_BIN" install node@22

  local node_prefix
  node_prefix="$(brew_prefix_for node@22)"
  if [ -n "$node_prefix" ]; then
    export PATH="$node_prefix/bin:$PATH"
  fi

  command -v node >/dev/null 2>&1 || fail "Node.js installation failed."
  command -v npm >/dev/null 2>&1 || fail "npm installation failed."
}

ensure_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    log "Creating Python virtual environment."
    python3 -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

install_backend_deps() {
  log "Installing backend dependencies."
  python -m pip install --upgrade pip
  pip install -r backend/requirements.txt
}

install_frontend_deps() {
  log "Installing frontend dependencies."
  cd "$ROOT_DIR/frontend"
  npm install
  cd "$ROOT_DIR"
}

build_frontend() {
  log "Building frontend."
  cd "$ROOT_DIR/frontend"
  npm run build
  cd "$ROOT_DIR"
}

open_when_ready() {
  (
    local attempt
    for attempt in $(seq 1 60); do
      if curl -fsS "$URL" >/dev/null 2>&1; then
        open "$URL" >/dev/null 2>&1 || true
        exit 0
      fi
      sleep 1
    done
  ) &
}

main() {
  log "Checking system requirements."
  ensure_python
  ensure_node
  ensure_venv
  install_backend_deps
  install_frontend_deps
  build_frontend

  log "Starting local server at $URL"
  open_when_ready
  exec "$VENV_DIR/bin/uvicorn" backend.app.main:app --host 127.0.0.1 --port 8000
}

main "$@"
