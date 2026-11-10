# SPDX-License-Identifier: BSD-3-Clause
# Sourced, never run: hold edi's producer lock for this script's lifetime. Every writer of a crysta prefix, the
# SDK cache or build/crysta-src holds the lock core-build.sh takes. A script core-build runs inherits that
# acquisition, proven by EDI_PRODUCER_LOCK_HELD equalling the token core-build wrote into the lock. Every other
# caller, including one naming another holder's lock or token, takes the lock here, waiting at most
# EDI_CORE_BUILD_LOCK_WAIT_S seconds as core-build does.
edi_producer_lock() {  # $1 = the edi root
  local lock="$1/build/.core-build.lock.d" waited=0
  [ -z "${EDI_PRODUCER_LOCK_HELD:-}" ] || [ "$(cat "$lock/owner" 2>/dev/null)" != "$EDI_PRODUCER_LOCK_HELD" ] || return 0
  mkdir -p "$1/build"
  until mkdir "$lock" 2>/dev/null; do
    [ "$waited" -lt "${EDI_CORE_BUILD_LOCK_WAIT_S:-1800}" ] || { echo "REFUSING: $lock has been held for ${waited}s; if no build runs, remove it" >&2; exit 1; }
    sleep 1; waited=$((waited + 1))
  done
  EDI_PRODUCER_LOCK_RELEASE="$lock"; trap 'rmdir "$EDI_PRODUCER_LOCK_RELEASE" 2>/dev/null || true' EXIT
}
