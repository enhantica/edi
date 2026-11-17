#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copy a branch of enhantica/edi-sites (the site the host behind easydiffraction.org serves) into a folder, so a
# publish keeps the part it does not rebuild: the docs keep the deployed web app and the web app the deployed docs.
# A branch that does not exist yet gives an empty folder; any other failure stops, so an unreachable edi-sites never
# publishes a site without its other half.
#   SITES_TOKEN=... bash tools/ci/fetch_deploy_branch.sh <branch> <folder>
set -euo pipefail
branch="${1:?the deploy branch}"
folder="${2:?the destination folder}"
remote="https://x-access-token:${SITES_TOKEN:?a token that may read edi-sites}@github.com/enhantica/edi-sites.git"
mkdir -p "$folder"
status=0
git ls-remote --exit-code --heads "$remote" "refs/heads/$branch" >/dev/null || status=$?
if [ "$status" -eq 2 ]; then
  echo "fetch_deploy_branch: $branch does not exist yet; starting from an empty site"
  exit 0
fi
[ "$status" -eq 0 ] || { echo "fetch_deploy_branch: edi-sites could not be read (git exit $status)" >&2; exit 1; }
git -C "$folder" init -q
git -C "$folder" fetch -q --depth 1 "$remote" "refs/heads/$branch"
git -C "$folder" checkout -q --detach FETCH_HEAD
rm -rf "$folder/.git"
echo "fetch_deploy_branch: $branch copied into $folder"
