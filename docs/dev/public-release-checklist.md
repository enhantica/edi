# Public release: the cut and the publish checklist

edi is cut once into a new private repository that later goes public. In the cut window,
`enhantica/edi` is renamed `edi-archive-<date>` and keeps its history; a new private `enhantica/edi`
takes the reviewed snapshot as its only commit. Development continues there under the public rules,
and publishing means making that same repository public. The steps below are in order; each names
who does it and how it is checked.

The scripts are in `tools/public-release/`: `scrub.py` (the content scrub), `scan.py` (the secrets
scan and the residue counts), `spdx.py` (the licence identifiers), `snapshot.py` (one fresh commit of
a scrubbed `main`), `content_check.py` (every change's files, commit messages and pull request) and
`cutover.py` (the rehearsal, the settings inventory and the cut).

## 1. Before the cut

- [ ] edi is frozen: every open pull request of `edi` is merged or closed, and no new one opens
      until the cut is done.
- [ ] Rehearse on the newest `main` of `edi`:
      `python tools/public-release/cutover.py rehearse --source <edi> --previous <last snapshot> --output <new dir>`.
      Read every line of its delta. A change the scrub rewrote that it should not have is reverted
      in `edi`, and the scrub learns it; a new private path, citation or process reference in the
      delta is edited in `edi` first.
- [ ] The snapshot's own checks pass on the new tree: `scan.py` reports no credential and no
      archive-member finding, gitleaks reports no leak (`gitleaks detect --source <new dir>`, with
      the reviewed `.gitleaksignore`), the content check passes from the root
      (`content_check.py --base root`), and the public-release gates pass
      (`tests/system/py/test_e04_t12_public_release.py`).
- [ ] Redistribution rights are recorded for every bundled dataset: the facility data and the
      FullProf example files.
- [ ] The crysta SDK pin names a build published from crysta `main` (its `build-<sha>` release
      tag) that is built against the locked Eigen 3.4.0. Its `lib/cmake/crysta/crystaConfig.cmake`
      requires `Eigen3 3.4.0 EXACT`, and its fingerprint names eigen 3.4.0. Pin it with
      `pixi run crysta-sdk-pin <sha>`. The hosted `pin currency` job fails while the pin names a
      pull-request head's build, which is published only when that pull request ships. Never publish
      a pull-request build to make it pass.
- [ ] The re-anchoring changes for the development hub and crysta are reviewed and ready to merge:
      commits of the old `edi` resolve in `edi-archive-<date>` (the archive name is set to the cut's
      date), and the hub's mount of `edi` and its records point at the new repository.

## 2. The cut window

Run by the maintainer the owner authorized for the cut.

- [ ] Check first: `python tools/public-release/cutover.py cut --date <date> --snapshot <snapshot>`.
      It reads only: the snapshot is one clean commit with no finding, the repository is private,
      has no open pull request and the archive name is free; it prints every change it would make
      and the organization's runner groups, secrets and variables with their visibility.
- [ ] Cut: the same command with `--apply`. In order, and stopping at the first failure, it renames
      `edi` to `edi-archive-<date>`, creates the private `edi` with the old settings, pushes the
      snapshot as its only commit, and recreates:
  - **Labels**, with their colours and descriptions. GitHub's default labels that share a name are
    updated, and the others are removed.
  - **Rulesets**: the main-branch protection (pull requests only, squash merges, no force push, no
    deletion, the hosted CI's job names and the content check required).
  - **Environments**: `crysta-sdk`, deployment from `main` and from pull requests (their
    `refs/pull/*/merge` refs), so pull-request CI runs. A fork's pull request is admitted as well: it
    gets no secrets, and its jobs skip every step that needs the token. `github-pages` is created by
    Pages.
  - **Actions**: approval required for workflows from outside contributors' forks.
  - **Secrets and variables**: the crysta SDK token comes from the organization's app
    (`ENHANTICA_APP_KEY`, an organization secret, read only inside the `crysta-sdk` environment)
    and `ENHANTICA_APP_ID` (an organization variable). Granted repository by repository when their
    visibility is `selected`; nothing to do when it is `all`.
  - **Runners**: the self-hosted runner groups admit the new private repository; a group granted
    repository by repository is given it.
- [ ] Read the settings back: `python tools/public-release/cutover.py settings --repo enhantica/edi`
      matches the archive's (names only, never values), with the ruleset renamed and the content
      check added.
- [ ] Merge the re-anchoring changes. crysta's edi verification runs once against the new
      repository and is green; the hub's checks are green against it.
- [ ] Every local checkout of `edi` is cloned again from the new repository.

## 3. Developing in the private repository

- [ ] The content check (`content.yml`) runs on every push and pull request and is required by the
      ruleset. Commit messages, pull-request titles and bodies, branch names, review comments and CI
      logs are written for the public from the cut onward.
- [ ] The public workflows are installed in `.github/workflows` and run on GitHub-hosted runners;
      the content check (`content.yml`) is one of them. The latency bank (`bank-latency.yml`) runs on
      the self-hosted fleet by dispatch only, so no pull request reaches a self-hosted runner.
- [ ] **Pages** is on: `pages.yml` builds the docs and the web app from main and deploys them while
      the repository is public.
- [ ] The scheduled and writing workflows run only in the repository named `enhantica/edi`: the
      crysta SDK update (`crysta-sdk-update.yml`) and the latency bank (`bank-latency.yml`).

## 4. Publish — the owner's step

The owner makes the repository public personally; no script and no session does.

- [ ] Before: the self-hosted runners leave the repository. A runner group that does not allow
      public repositories stops serving it by itself at the visibility change; confirm every group
      the repository uses is such a group, or that fork pull requests require approval.
- [ ] Before the visibility change, by pull request: the public workflows replace the private ones in
      `.github/workflows`, on GitHub-hosted runners. GitHub-hosted runners then run every job a pull
      request reaches, with no self-hosted job reachable from a fork's pull request.
- [ ] Before: the logs of runs on self-hosted runners are deleted or have expired
      (`gh run list --repo enhantica/edi`, then `gh run delete <id>` for each run a self-hosted
      runner served), so no runner's machine paths or names are published with them.
- [ ] The owner changes the visibility to public.
- [ ] **Pages** is enabled, with GitHub Actions (`pages.yml`) as its source. The site URL is the one
      `mkdocs.yml` declares, and the web app is at `/webapp/`, linked from the docs.
- [ ] Hosted CI is green on the public `edi`.
- [ ] The scheduled crysta SDK update workflow is enabled again (GitHub disables a schedule after 60
      days without activity).
- [ ] A fresh re-snapshot is only the fallback if the repository cannot be made public as it is.
