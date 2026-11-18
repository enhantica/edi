## What this changes

<!-- One or two sentences for the release notes: what a user notices. -->

## Labels

The release notes are made from the labels, and the label check refuses a pull request without them:

- one scope: `[scope] significant`, `[scope] enhancement`, `[scope] bug`, `[scope] maintenance` or
  `[scope] documentation`;
- one or more interfaces: `[interface] desktop`, `[interface] web`, `[interface] py`, `[interface] cli`,
  `[interface] cli-py`;
- or only `[bot] release` for a release pull request.

## Checks

- [ ] `pixi run lint` passes (the pre-push hook runs it: `git config core.hooksPath .githooks`).
- [ ] New behaviour has tests.
