# Contributing to EasyDiffraction

Thank you for helping. Bug reports, questions and ideas are welcome through the **Feedback** menu in the
app or the form on [easydiffraction.org](https://easydiffraction.org).

## Setting up

Everything is built through [pixi](https://pixi.sh); see [BUILD.md](BUILD.md) for the core, the app and
the Python package.

```bash
pixi install
git config core.hooksPath .githooks   # run the lint checks before every push
```

## Before you push

- `pixi run lint` runs the same checks as the CI lint job: Ruff, formatting and the repository's policy
  checks. The pre-push hook above runs it for you; `git push --no-verify` skips it once.
- `pixi run test` runs the Python tests; `pixi run verify` runs the full local gate.
- New behaviour comes with tests. Values that claim correctness come from an independent reference (a
  published result, another program or a closed form), not from the code under test.

## Pull requests

- Keep a pull request to one change, with a title that reads as a release note.
- Add one `[scope]` label and one or more `[interface]` labels; the release notes are made from them and
  the label check refuses a pull request without them.
- Design decisions are recorded as ADRs in [docs/dev/adrs](docs/dev/adrs). A change to a recorded decision
  updates its ADR in the same pull request.
- Commit subjects are short (at most 72 characters) and say what the change does.

## Licence

By contributing you agree that your work is released under the project's licences: the source code under
the [BSD 3-Clause License](LICENSE), and the application built from it under the
[GNU General Public License version 3](COPYING).
