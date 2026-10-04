#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# edi's crysta pin reader, its currency check and their remote helpers (edi ADR-0017). Run directly, it reads
# the committed pin and outputs the pinned sha: the
# `changes` job runs it once per workflow run, for the record the CI evidence reads. The
# `pin currency` job runs it with --currency (crysta_currency, below), the one required check on the pin itself
# (owner, 2026-10-01): it reports a stale pin, and fails only when the pin or the answer cannot be read. edi
# never compiles crysta: build-crysta.sh takes a prebuilt SDK, the pinned one or, in a paired run whose pin is
# stale, the paired crysta branch head's (crysta_paired_head, below), and crysta-src.sh sources the remote
# helpers to fetch that build's source.
#
# Branch lookups use `git ls-remote` over the authenticated URL (the self-hosted runners have no
# `gh`), so a successful answer also proves the token reads crysta. A branch proven ABSENT, or one whose head
# has landed on crysta main, leaves the PR unpaired (a branch that merely exists pairs nothing); a lookup
# ERROR refuses by name, since a branch that could not be resolved is never read as absent.
#
# Remote steps: an auth or `Repository not found` failure is retried, 3 attempts with 5 s and 15 s
# backoff, each failure logging the repositories the token grants; any other failure is final.
#
#   bash tools/ci/crysta-source.sh                -> prints the pinned sha; in CI also `sha=<sha>` to $GITHUB_OUTPUT
#   bash tools/ci/crysta-source.sh --currency     -> reports whether the pin is current; exit 1 only when the
#                                                    pin or the answer cannot be read
#   bash tools/ci/crysta-source.sh --paired-head  -> prints the paired crysta branch's head, or an empty line
#   bash tools/ci/crysta-source.sh --paired-commit <sha>  -> exit 0 when <sha> is a commit of the paired crysta
#                                                    branch that crysta main lacks; 1 when it is not; 2 unread

CRYSTA_REPO="enhantica/crysta"
CRYSTA_PUBLIC_URL="https://github.com/$CRYSTA_REPO"
: "${CRYSTA_SRC:=$HOME/Development/github.com/enhantica/crysta}"

# The URL every remote step uses: the public URL, authenticated with the CI token when one is passed
# (named in the log, never echoed by value — see _crysta_redact).
crysta_url() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    printf 'https://x-access-token:%s@github.com/%s' "$GITHUB_TOKEN" "$CRYSTA_REPO"
  else
    printf '%s' "$CRYSTA_PUBLIC_URL"
  fi
}

_crysta_redact() {  # never a token by value, even in git's own words
  local text="$1"
  [ -z "${GITHUB_TOKEN:-}" ] || text="${text//${GITHUB_TOKEN}/***}"
  printf '%s' "$text"
}

_crysta_granted() {  # the repositories the minted token reads, listed with curl
  local out rc=0
  out="$(curl -fsS -H "Authorization: Bearer ${GITHUB_TOKEN:-}" -H 'Accept: application/vnd.github+json' \
    https://api.github.com/installation/repositories 2>&1)" || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "build-crysta: the token's grants could not be listed (curl exit $rc): $(_crysta_redact "$out")" >&2
  else
    echo "build-crysta: the token grants: $(printf '%s' "$out" | sed -n 's/.*"full_name": *"\([^"]*\)".*/\1/p' | tr '\n' ' ')" >&2
  fi
}

# crysta_remote <step> <git args...>: run one remote git step with the bounded auth retry. The output
# lands in CRYSTA_REMOTE_OUT; the return code is git's last. `.extraheader` is cleared because
# actions/checkout's persisted repo-scoped header would override the URL credential (PR54 run 3).
crysta_remote() {
  local step="$1" attempt=1 rc
  shift
  while :; do
    rc=0
    CRYSTA_REMOTE_OUT="$(git -c http.https://github.com/.extraheader= "$@" 2>&1)" || rc=$?
    [ "$rc" -eq 0 ] && return 0
    case "$CRYSTA_REMOTE_OUT" in
      *"Repository not found"* | *"Authentication failed"* | *"could not read Username"* | \
        *"Invalid username or password"* | *"returned error: 401"* | *"returned error: 403"*) ;;
      *) return "$rc" ;;
    esac
    echo "build-crysta: $step attempt $attempt/3 failed (rc=$rc): $(_crysta_redact "$CRYSTA_REMOTE_OUT")" >&2
    _crysta_granted
    [ "$attempt" -lt 3 ] || return "$rc"
    if [ "$attempt" -eq 1 ]; then sleep 5; else sleep 15; fi
    attempt=$((attempt + 1))
  done
}

# crysta_branch_head <branch>: the same-named crysta branch's head in CRYSTA_BRANCH_HEAD, or empty when the
# branch is proven ABSENT; returns 1 (the cause printed) on a lookup error. Read with
# `git ls-remote` over the authenticated URL (no `gh`): success proves crysta is readable. The
# answer is accepted only as exactly one line `<40-hex sha><TAB>refs/heads/<branch>`, or as no line at all
# (absent). Anything else — a failure, a second line, a line naming any other ref (a tag or another branch
# with that name included), or a malformed line — is a lookup error, never read as absence.
crysta_branch_head() {
  CRYSTA_BRANCH_HEAD=""
  local want="refs/heads/$1" lines="" found="" count=0 line bad=0
  if ! crysta_remote "branch lookup" ls-remote "$(crysta_url)" "$want"; then
    echo "crysta-resolution: the crysta branch lookup for '$1' failed: $(_crysta_redact "$CRYSTA_REMOTE_OUT") — refusing: a branch that cannot be resolved is never replaced by crysta main" >&2
    return 1
  fi
  lines="$CRYSTA_REMOTE_OUT"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    if [[ "$line" =~ ^([0-9a-f]{40})$'\t'(.+)$ ]] && [ "${BASH_REMATCH[2]}" = "$want" ]; then
      count=$((count + 1))
      found="${BASH_REMATCH[1]}"
    else
      bad=1
    fi
  done <<<"$lines"
  if [ "$bad" -ne 0 ] || [ "$count" -gt 1 ]; then
    echo "crysta-resolution: the crysta branch lookup for '$1' gave an answer other than exactly $want: $(_crysta_redact "$lines") — refusing" >&2
    return 1
  fi
  CRYSTA_BRANCH_HEAD="$found"
}

# crysta_pin <pixi.toml> <label>: prints the one build that file pins (THE pin contract,
# tools/ci/crysta_sdk.py, decides it; nothing here reads pixi.toml). Returns 1, the cause printed, unless every
# platform pins one build.
crysta_pin() {
  local root shas
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  shas="$(python3 "$root/tools/ci/crysta_sdk.py" pins "$1" | sort -u | grep .)" || shas=""
  if [ -z "$shas" ] || [ "$(printf '%s\n' "$shas" | wc -l)" -ne 1 ]; then
    echo "crysta-pin: $2 pins ${shas:-no} crysta build(s); every platform pins one build" >&2
    return 1
  fi
  printf '%s\n' "$shas"
}

# crysta_landed <sha> [ref]: 0 when <sha> has landed on crysta main — a main commit, or a paired PR head squashed
# onto main, whose tree a main commit carries. The commit is read through [ref]: its retained build-<sha> tag by
# default, or the branch ref whose head it is. 1 when it has not landed; 2, the cause printed, when crysta, that
# ref or the commit through it could not be read. The clone fetches commits only (no trees, no blobs).
crysta_landed() {
  local clone rc=2 anc=0 tree trees ref="${2:-refs/tags/build-$1}" what="${2:-build-$1}"  # review-18 F03: only a history read in full answers 1
  clone="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/crysta-currency.XXXXXX")"  # the job's temp: a cancel cannot strand it
  if ! crysta_remote "main clone" clone -q --bare --filter=tree:0 --single-branch --branch main "$(crysta_url)" "$clone/c"; then
    echo "crysta-currency: crysta main could not be read: $(_crysta_redact "$CRYSTA_REMOTE_OUT")" >&2
  else
    git -C "$clone/c" merge-base --is-ancestor "$1" main 2>/dev/null || anc=$?
    if [ "$anc" -eq 0 ]; then
      rc=0  # ancestry, never presence: a partial clone fetches any missing commit on demand
    elif [ "$anc" -ne 1 ]; then  # review-20 F02: any lookup error is red (gate 9), whatever a later lookup finds
      echo "crysta-currency: the ancestry of $1 could not be read (merge-base exit $anc)" >&2
    elif ! crysta_remote "${2:+branch }${2:-build tag}" -C "$clone/c" fetch -q origin "$ref:$ref"; then
      echo "crysta-currency: $what could not be read: $(_crysta_redact "$CRYSTA_REMOTE_OUT")" >&2
    elif ! tree="$(git -C "$clone/c" rev-parse "$1^{tree}")" || ! trees="$(git -C "$clone/c" log --format=%T main)"; then
      echo "crysta-currency: $what's tree or crysta main's history could not be read" >&2
    elif grep -qxF "$tree" <<<"$trees"; then
      rc=0  # a paired head squashed onto main: main carries its tree
    else
      rc=1  # read in full: neither an ancestor of main nor a tree main carries
    fi
  fi
  rm -rf "$clone"
  return "$rc"
}

# crysta_paired_head: is this run paired? A pull request, or a dispatched run, is paired when its
# branch has a same-named crysta branch whose head has NOT landed on crysta main. Sets CRYSTA_PAIRED_BRANCH to the
# run's branch when that crysta branch exists, and CRYSTA_PAIRED_HEAD to its head when the run is paired; both
# are empty otherwise. Returns 1, the cause printed, on any lookup error: an unread answer is never "unpaired".
# One rule answers the currency check below and the build (crysta_sdk.py fetch, through --paired-head).
crysta_paired_head() {
  local branch="" landed=0
  CRYSTA_PAIRED_BRANCH="" CRYSTA_PAIRED_HEAD=""
  case "${GITHUB_EVENT_NAME:-}" in
    pull_request) branch="${GITHUB_HEAD_REF:-}" ;;
    workflow_dispatch) branch="${GITHUB_REF_NAME:-}" ;;
  esac
  [ -n "$branch" ] || return 0
  crysta_branch_head "$branch" || return 1
  [ -n "$CRYSTA_BRANCH_HEAD" ] || return 0
  CRYSTA_PAIRED_BRANCH="$branch"
  crysta_landed "$CRYSTA_BRANCH_HEAD" "refs/heads/$branch" || landed=$?
  [ "$landed" -le 1 ] || return 1
  [ "$landed" -eq 0 ] || CRYSTA_PAIRED_HEAD="$CRYSTA_BRANCH_HEAD"
}

# crysta_paired_commit <sha>: is <sha> a commit this paired run may have built? That is the paired crysta
# branch's head, or an earlier commit of that branch that crysta main lacks: the head a job of the same run found
# before the branch moved on. 0 when it is; 1 when the run is unpaired or the commit is not on the branch or has
# landed; 2, the cause printed, when the answer cannot be read. The clone fetches commits only.
crysta_paired_commit() {
  local clone rc=2 on_branch=0 on_main=0 ref
  crysta_paired_head || return 2
  [ -n "$CRYSTA_PAIRED_HEAD" ] || return 1
  [ "$1" != "$CRYSTA_PAIRED_HEAD" ] || return 0
  ref="refs/heads/$CRYSTA_PAIRED_BRANCH"
  clone="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/crysta-paired.XXXXXX")"
  if ! crysta_remote "main clone" clone -q --bare --filter=tree:0 --single-branch --branch main "$(crysta_url)" "$clone/c"; then
    echo "crysta-paired: crysta main could not be read: $(_crysta_redact "$CRYSTA_REMOTE_OUT")" >&2
  elif ! crysta_remote "branch" -C "$clone/c" fetch -q origin "$ref:$ref"; then
    echo "crysta-paired: crysta branch '$CRYSTA_PAIRED_BRANCH' could not be read: $(_crysta_redact "$CRYSTA_REMOTE_OUT")" >&2
  else
    git -C "$clone/c" merge-base --is-ancestor "$1" "$ref" 2>/dev/null || on_branch=$?
    git -C "$clone/c" merge-base --is-ancestor "$1" main 2>/dev/null || on_main=$?
    if [ "$on_branch" -gt 1 ] || [ "$on_main" -gt 1 ]; then
      rc=1  # the commit is not in crysta at all: not a commit of the branch
    elif [ "$on_branch" -eq 0 ] && [ "$on_main" -eq 1 ]; then
      rc=0
    else
      rc=1
    fi
  fi
  rm -rf "$clone"
  return "$rc"
}

# _crysta_stale <what>: report a stale pin and the fix; in CI the same report is a warning on the run.
_crysta_stale() {
  echo "crysta-currency: $1" >&2
  echo "crysta-currency: the stale pin is reported, not refused: the final CI evidence and the merge refuse it" >&2
  [ "${GITHUB_ACTIONS:-}" != true ] || echo "::warning title=stale crysta pin::$1"
}

# crysta_currency (I10; edi ADR-0017): is
# the committed pin current? Paired (crysta_paired_head), the current pin is that crysta branch's head. Unpaired,
# it has landed on crysta main (crysta_landed) or is the pin on edi main. A pin that is not current is STALE: it
# is reported, with the fix, and the answer is still 0. A task's crysta branch moves with every crysta commit, so
# a job that failed on each of those rows said nothing new; a paired run builds the branch head whatever the pin
# says (crysta_sdk.py fetch); the final CI evidence counts an edi run only when the SDK it built is its pin and the
# paired crysta pull request's head; and the merge guard refuses a pin that has not landed. Returns 1, the cause
# printed, on a pin that cannot be read and on any lookup error: an unread answer is never current.
crysta_currency() {
  local root pin main_pin landed=0
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  pin="$(crysta_pin "$root/pixi.toml" pixi.toml)" || return 1
  crysta_paired_head || return 1
  if [ -n "$CRYSTA_PAIRED_HEAD" ] && [ "$CRYSTA_PAIRED_HEAD" = "$pin" ]; then
    echo "crysta-currency: paired with crysta branch '$CRYSTA_PAIRED_BRANCH', whose head build-$pin is the pin"
    return 0
  elif [ -n "$CRYSTA_PAIRED_HEAD" ]; then
    _crysta_stale "crysta branch '$CRYSTA_PAIRED_BRANCH' is at $CRYSTA_PAIRED_HEAD but edi pins build-$pin — re-pin: pixi run crysta-sdk-pin $CRYSTA_PAIRED_HEAD"
    return 0
  elif [ -n "$CRYSTA_PAIRED_BRANCH" ]; then
    echo "crysta-currency: crysta branch '$CRYSTA_PAIRED_BRANCH' carries nothing crysta main lacks, so this pull request is unpaired"
  fi
  crysta_landed "$pin" || landed=$?
  if [ "$landed" -eq 0 ]; then
    echo "crysta-currency: unpaired; the pin build-$pin has landed on crysta main"
    return 0
  elif [ "$landed" -ne 1 ]; then
    return 1
  fi
  if ! git -C "$root" fetch -q --depth=1 origin main; then
    echo "crysta-currency: edi main could not be read — refusing" >&2
    return 1
  fi
  main_pin="$(crysta_pin <(git -C "$root" show FETCH_HEAD:pixi.toml) "edi main's pixi.toml" 2>/dev/null)" || main_pin=""
  if [ "$main_pin" = "$pin" ]; then
    echo "crysta-currency: unpaired; the pin build-$pin is edi main's"
    return 0
  fi
  _crysta_stale "unpaired, and build-$pin has neither landed on crysta main nor is edi main's pin (${main_pin:+build-}${main_pin:-none}) — re-pin: pixi run crysta-sdk-pin <a crysta main sha>"
  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  set -euo pipefail
  if [ "${1:-}" = --currency ]; then
    crysta_currency
    exit 0
  fi
  if [ "${1:-}" = --paired-head ]; then
    crysta_paired_head
    echo "$CRYSTA_PAIRED_HEAD"
    exit 0
  fi
  if [ "${1:-}" = --paired-commit ]; then
    crysta_paired_commit "${2:?a crysta sha}" && exit 0 || exit $?
  fi
  CRYSTA_PIN="$(crysta_pin "$(cd "$(dirname "$0")/../.." && pwd)/pixi.toml" pixi.toml)"
  echo "crysta: pinned SDK build-$CRYSTA_PIN" >&2   # The effective pin the CI evidence reads
  echo "$CRYSTA_PIN"
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'sha=%s\n' "$CRYSTA_PIN" >>"$GITHUB_OUTPUT"
  fi
fi
