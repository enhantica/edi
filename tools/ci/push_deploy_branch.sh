#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copy a built folder onto a branch of enhantica/edi-sites, which the web host behind easydiffraction.org pulls
# through a webhook (one branch per domain). Each update is one commit on top of the last, so git sends only the
# files that changed. SITES_TOKEN is a short-lived GitHub App token that may write to edi-sites.
#   SITES_TOKEN=... bash tools/ci/push_deploy_branch.sh <folder> <branch>
set -euo pipefail
folder="$(cd "${1:?the built folder}" && pwd)"
branch="${2:?the deploy branch}"
remote="https://x-access-token:${SITES_TOKEN:?a token that may write to edi-sites}@github.com/enhantica/edi-sites.git"
work="$(mktemp -d)"
git -C "$work" init -q
if git -C "$work" fetch -q --depth 1 "$remote" "refs/heads/$branch" 2>/dev/null; then
  git -C "$work" checkout -q --detach FETCH_HEAD
else
  git -C "$work" checkout -q --orphan "$branch"
fi
rsync -a --delete --exclude .git "$folder"/ "$work"/
# The host serves .wasm as text by default; browsers need this type to start the web app.
printf 'AddType application/wasm .wasm\n' > "$work/.htaccess"
cd "$work"
git add -A
if git diff --cached --quiet 2>/dev/null && git rev-parse -q --verify HEAD >/dev/null; then
  echo "push_deploy_branch: $branch is already up to date"
  exit 0
fi
git -c user.name='github-actions[bot]' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit -q -m "Update the site"
git push -q "$remote" "HEAD:refs/heads/$branch"
echo "push_deploy_branch: $branch updated"
