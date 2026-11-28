#!/usr/bin/env bash
# Runs the pixi a manifest pins. It finds the manifest the way pixi does, reads its exact
# requires-pixi, fetches that release once (checked against its published sha256) and runs it.
# With no manifest it runs the newest version already fetched. It never runs another version:
# a range, a failed download or a wrong checksum stops it.
#
#   pixi-launcher.sh <pixi arguments>          run the pinned pixi
#   pixi-launcher.sh --launcher-pin <manifest> print the exact version a manifest pins
#
# Two repositories carry this file; their copies stay byte-identical.
set -euo pipefail

RELEASES="${PIXI_LAUNCHER_RELEASES:-https://github.com/prefix-dev/pixi/releases/download}"
VERSIONS="${PIXI_LAUNCHER_VERSIONS:-${HOME:?}/.pixi/versions}"
LOCK="" TMP=""

refuse() { echo "pixi-launcher: $*" >&2; exit 1; }
cleanup() { [ -z "$TMP" ] || rm -rf "$TMP"; [ -z "$LOCK" ] || rm -rf "$LOCK"; TMP="" LOCK=""; }
trap cleanup EXIT

# pixi skips a pyproject.toml without a [tool.pixi...] table and keeps looking upwards.
has_pixi_table() { grep -Eq '^[[:space:]]*\[tool\.pixi([].]|$)' "$1"; }

manifest_in() { # the manifest pixi takes from a directory: pixi.toml before pyproject.toml
  if [ -f "$1/pixi.toml" ]; then
    printf '%s\n' "$1/pixi.toml"
  elif [ -f "$1/pyproject.toml" ] && has_pixi_table "$1/pyproject.toml"; then
    printf '%s\n' "$1/pyproject.toml"
  else
    return 1
  fi
}

# The options before a command that take a value, so their value is not read as the command.
takes_value() {
  case "$1" in
    -e | --environment | -p | --platform | -s | --spec | --shell | --script | -c | --channel | -f | --feature | \
      -g | --git | -w | --workspace | --with | --color | --concurrent-solves | --concurrent-downloads | \
      --config-file | --auth-file | --tls-root-certs | --pypi-keyring-provider | --pinning-strategy | --skip | \
      --skip-with-deps | --branch | --tag | --rev | --subdirectory | --index | --only) return 0 ;;
  esac
  return 1
}

# Sets MANIFEST_ARG and SUBCOMMAND from pixi's arguments. Everything after the command of
# `run`/`exec` belongs to that command (`pixi run python -m pytest` names no manifest).
# A manifest chosen by an option this misses still meets pixi's own requires-pixi check.
MANIFEST_ARG="" SUBCOMMAND=""
read_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --) return 0 ;;
      --manifest-path=*) MANIFEST_ARG="${1#*=}" ;;
      -m | --manifest-path)
        [ "$#" -ge 2 ] || return 0
        MANIFEST_ARG="$2"
        shift
        ;;
      -m?*) MANIFEST_ARG="${1#-m}" ;;
      -*=*) ;;
      -*) if takes_value "$1" && [ "$#" -ge 2 ]; then shift; fi ;;
      *)
        if [ -z "$SUBCOMMAND" ]; then
          SUBCOMMAND="$1"
        else
          case "$SUBCOMMAND" in run | exec | x) return 0 ;; esac
        fi
        ;;
    esac
    shift
  done
}

find_manifest() { # the manifest pixi would use: --manifest-path, else upwards, else PIXI_PROJECT_MANIFEST
  local dir
  if [ -n "$MANIFEST_ARG" ]; then
    if [ -d "$MANIFEST_ARG" ]; then
      manifest_in "$MANIFEST_ARG" || refuse "no pixi manifest in $MANIFEST_ARG"
    elif [ -f "$MANIFEST_ARG" ]; then
      printf '%s\n' "$MANIFEST_ARG"
    else
      refuse "no manifest at $MANIFEST_ARG"
    fi
    return 0
  fi
  dir="$PWD"
  while :; do
    manifest_in "$dir" && return 0
    [ "$dir" != / ] || break
    dir="$(dirname "$dir")"
  done
  # pixi measured: a manifest found from the working directory wins over the variable
  if [ -n "${PIXI_PROJECT_MANIFEST:-}" ] && [ -f "$PIXI_PROJECT_MANIFEST" ]; then
    printf '%s\n' "$PIXI_PROJECT_MANIFEST"
  fi
}

pin_of() { # the exact version a manifest pins, or nothing when it pins none
  local count line value
  count="$(grep -cE '^[[:space:]]*requires-pixi[[:space:]]*=' "$1" || true)"
  [ "$count" != 0 ] || return 0
  [ "$count" = 1 ] || refuse "$1 declares requires-pixi $count times"
  line="$(grep -E '^[[:space:]]*requires-pixi[[:space:]]*=' "$1")"
  value="$(printf '%s\n' "$line" | sed -E "s/^[^=]*=[[:space:]]*['\"]([^'\"]*)['\"][[:space:]]*(#.*)?\$/\\1/")"
  [[ "$value" =~ ^==[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
    refuse "$1 requires pixi '${value}', not one exact version (==x.y.z): no version is run"
  printf '%s\n' "${value#==}"
}

newest() { # the newest version already fetched
  [ -d "$VERSIONS" ] || return 0
  local v
  for v in "$VERSIONS"/*; do
    v="${v##*/}"
    if [[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && [ -x "$VERSIONS/$v/pixi" ]; then printf '%s\n' "$v"; fi
  done | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1
}

target() {
  local os arch
  case "$(uname -s)" in
    Linux) os=unknown-linux-musl ;;
    Darwin) os=apple-darwin ;;
    *) refuse "no pixi release is fetched for $(uname -s)" ;;
  esac
  case "$(uname -m)" in
    x86_64 | amd64) arch=x86_64 ;;
    aarch64 | arm64) arch=aarch64 ;;
    *) refuse "no pixi release is fetched for $(uname -m)" ;;
  esac
  printf '%s-%s\n' "$arch" "$os"
}

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi | awk '{print $1}'
}

take_lock() { # one fetch of a version at a time; a lock left by a dead launcher is taken over
  local waited=0 holder
  until mkdir "$1" 2>/dev/null; do
    holder="$(cat "$1/pid" 2>/dev/null || true)"
    if { [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; } ||
      { [ -z "$holder" ] && [ -n "$(find "$1" -maxdepth 0 -mmin +2 2>/dev/null)" ]; }; then
      rm -rf "$1"
      continue
    fi
    [ "$waited" -lt 600 ] || refuse "another launcher has held $1 for ${waited}s"
    sleep 1
    waited=$((waited + 1))
  done
  LOCK="$1"
  echo "$$" >"$1/pid"
}

fetch() { # download, check and rename one version into place
  local v="$1" name want got
  name="pixi-$(target).tar.gz"
  mkdir -p "$VERSIONS"
  take_lock "$VERSIONS/.$v.lock"
  if [ ! -x "$VERSIONS/$v/pixi" ]; then # another launcher may have fetched it while this one waited
    TMP="$(mktemp -d "$VERSIONS/.$v.XXXXXX")"
    echo "pixi-launcher: fetching pixi $v" >&2
    curl -fsSL --retry 2 --connect-timeout 30 --speed-limit 1024 --speed-time 60 -o "$TMP/$name" "$RELEASES/v$v/$name" ||
      refuse "cannot download pixi $v ($RELEASES/v$v/$name): no version is run"
    curl -fsSL --retry 2 --connect-timeout 30 --speed-limit 1024 --speed-time 60 -o "$TMP/$name.sha256" "$RELEASES/v$v/$name.sha256" ||
      refuse "cannot download the published sha256 of pixi $v: no version is run"
    want="$(awk '{print $1; exit}' "$TMP/$name.sha256")"
    got="$(sha256 "$TMP/$name")"
    [[ "$want" =~ ^[0-9a-f]{64}$ ]] && [ "$got" = "$want" ] ||
      refuse "pixi $v: the download's sha256 $got is not the published '$want': no version is run"
    mkdir "$TMP/x"
    tar -xzf "$TMP/$name" -C "$TMP/x" && [ -f "$TMP/x/pixi" ] || refuse "pixi $v: the release archive holds no pixi"
    chmod +x "$TMP/x/pixi"
    [ "$("$TMP/x/pixi" --version 2>/dev/null)" = "pixi $v" ] ||
      refuse "pixi $v: the downloaded binary does not report version $v"
    mkdir -p "$VERSIONS/$v"
    mv -f "$TMP/x/pixi" "$VERSIONS/$v/pixi"
  fi
  cleanup
}

if [ "${1:-}" = --launcher-pin ]; then
  [ "$#" -eq 2 ] && [ -f "$2" ] || refuse "usage: pixi-launcher.sh --launcher-pin <manifest>"
  version="$(pin_of "$2")"
  [ -n "$version" ] || refuse "$2 pins no pixi version"
  printf '%s\n' "$version"
  exit 0
fi

read_args "$@"
[ "$SUBCOMMAND" != self-update ] ||
  refuse "self-update would replace a pinned version; change requires-pixi in the manifest instead"
manifest="$(find_manifest)"
version=""
[ -z "$manifest" ] || version="$(pin_of "$manifest")"
if [ -z "$version" ]; then
  version="$(newest)"
  [ -n "$version" ] || refuse "${manifest:-no manifest here} pins no pixi version and none is fetched in $VERSIONS"
fi
[ -x "$VERSIONS/$version/pixi" ] || fetch "$version"
cleanup
trap - EXIT
exec "$VERSIONS/$version/pixi" "$@"
