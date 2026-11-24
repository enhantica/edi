## What this changes

<!-- One or two sentences for the release notes: what a user notices. -->

## Labels

The release notes are made from the labels, and the label check refuses a pull request without them:

- one scope (red): `💥 significant`, `✨ enhancement`, `🐞 bug`, `🧹 maintenance` or `📘 documentation`;
- one or more interfaces (blue): `🖥️ desktop`, `🌐 web`, `🐍 py`, `⌨️ cli`, `📦 cli-py`, or `🪟 app` for desktop and
  web together and `🌍 all` for every one;
- or only `🚀 release` for a release pull request.

## Checks

- [ ] `pixi run lint` passes (the pre-push hook runs it: `git config core.hooksPath .githooks`).
- [ ] New behaviour has tests.
