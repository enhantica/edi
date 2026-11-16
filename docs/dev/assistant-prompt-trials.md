# Assistant prompt trials

These records say which assistant was given the published
[Python](https://easydiffraction.org/python/tutorials/assistant/) and
[command-line](https://easydiffraction.org/cli/tutorials/assistant/) prompts, whether its generated
artifact ran, and how its results compared with the La₀.₅Ba₀.₅CoO₃ on HRPT tutorial. The user docs only
say when the prompts were last checked; the evidence lives here and in
`tests/fixtures/tutorial_cases/published_assistant_trials.json` (SHA-256
`f9d892f37e88d7db1a10e7a095130c7de377595e8e84185d0eb53bfcba015ebe`), which keeps the fetched prompts,
input identities, execution captures, artifact hashes and comparisons. CI checks that record; it does not
run an online assistant ([ADR-0065](adrs/0065-public-site-and-contributor-docs.md)).

## Published prompts, 2026-11-13

A Codex assistant (backend model not exposed) read both published prompts, the linked worked references
and the two input downloads, and produced a notebook and a native CLI project. Both ran all five
cumulative fit stages.

| Artifact | Completed fits | Final reduced χ² | Final Rwp |
| --- | --- | --- | --- |
| Python notebook | 5 | 1.30 | 7.23% |
| Native CLI project | 5 | 1.30 | 7.23% |

Both match the published staged notebook and all six FullProf reference rows within their original
tolerances. The single-fit regression fixture's χ² and iteration count do not match this five-fit path;
the record keeps those mismatches with the original values and tolerances. The La/Ba displacement
correlation was −1.00, so "move together" in the prompt means strong correlation in magnitude; both
artifacts then applied the equal-displacement constraint.

The runs used Linux diagnostic builds of edi `80dc974c431aceee6f1dd4f3468847466b56d27a` and SDK
`2b6b981e21194f9a76074742dd0e148736ca4d9b`, with documentation from
`b16f9867ef1de464dfed731796848eb5ba60e739` on the published-release route. They do not qualify a
release binary, the current SDK candidate or Windows.

## Earlier attempts, 2026-11-09

| Interface | Model | Outcome |
| --- | --- | --- |
| Python notebook | GPT-6 (Codex) | Failed: required tutorial pages returned HTTP 404 |
| Command line | GPT-6 (Codex) | Failed: required tutorial pages returned HTTP 404 |

No generated artifact ran and nothing was compared. These attempts used prompt commit `557d6e703`;
their record is `tests/fixtures/tutorial_cases/assistant_trials.json`.
