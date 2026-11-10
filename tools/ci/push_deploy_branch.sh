#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copy a built folder onto a branch that a web host pulls through a webhook (easydiffraction.org and app.).
# Each update is one commit on top of the last, so git sends only the files that changed.
#   bash tools/ci/push_deploy_branch.sh <folder> <branch>
set -euo pipefail
folder="$(cd "${1:?the built folder}" && pwd)"
branch="${2:?the deploy branch}"
work="$(mktemp -d)"
if git fetch --depth 1 origin "refs/heads/$branch" 2>/dev/null; then
  git worktree add --detach "$work" FETCH_HEAD
else
  git worktree add --detach "$work" HEAD
  (cd "$work" && git checkout -q --orphan deploy && git rm -rqf --ignore-unmatch .)
fi
rsync -a --delete --exclude .git "$folder"/ "$work"/
cd "$work"
git add -A
if git diff --cached --quiet; then
  echo "push_deploy_branch: $branch is already up to date"
  exit 0
fi
git -c user.name='github-actions[bot]' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit -q -m "Update the site"
git push -q origin "HEAD:refs/heads/$branch"
echo "push_deploy_branch: $branch updated"
