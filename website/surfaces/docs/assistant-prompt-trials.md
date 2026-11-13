---
icon: fa5/clipboard-check
---

# Assistant prompt trials

These records say which assistant was tried, whether its generated artifact ran, and how its
results compared with the [La₀.₅Ba₀.₅CoO₃ on HRPT](python/tutorials/cases/pd-neut-cwl_lbco-hrpt.md)
tutorial. Another assistant run can take different steps; check the generated work and its results.

## Published prompts, 2026-11-13

Codex assistant (exact backend model not exposed) read the actual published
[Python](python/tutorials/assistant.md) and [command-line](cli/tutorials/assistant.md) prompts,
the linked worked references and the two input downloads. It produced a notebook and a native
CLI project. Both executed all five cumulative fit stages and completed with findings.

| Artifact | Completed fits | Final reduced χ² | Final Rwp |
| --- | --- | --- | --- |
| Python notebook | 5 | 1.30 | 7.23% |
| Native CLI project | 5 | 1.30 | 7.23% |

Both results match the published staged notebook's displayed results and all six unchanged
FullProf scientific-reference rows within their original tolerances. The separate single-fit
regression fixture's precise χ² and iteration count do **not** match this five-fit trajectory.
The recorded comparisons retain those mismatches and every original reference value and tolerance;
this is not an all-regression-pins pass. Display rounding is not a scientific tolerance.

The La/Ba displacement correlation was −1.00. The worked tutorial describes their opposite signs:
“move together” in the prompt should be read as strong correlation in magnitude. Both artifacts
then applied the requested equal-displacement constraint.

These executions used Linux diagnostic artifacts from Edi
`80dc974c431aceee6f1dd4f3468847466b56d27a` and SDK
`2b6b981e21194f9a76074742dd0e148736ca4d9b`. They do not qualify a published release binary,
the current SDK candidate, or Windows. The documentation source was
`b16f9867ef1de464dfed731796848eb5ba60e739`; the route was `published-release`, not a prerelease preview.

### Trial provenance

Recorded evidence: `tests/fixtures/tutorial_cases/published_assistant_trials.json`, SHA-256
`f9d892f37e88d7db1a10e7a095130c7de377595e8e84185d0eb53bfcba015ebe`.
It retains exact fetched prompts, documentation/input identities, execution captures and comparisons.
The generated artifacts are retained as authoring evidence; no public download is claimed here.

- Ready notebook `lbco_hrpt_prompt.ipynb`: SHA-256
  `d5f516b4e96086f3c37ebc9e21d4e145f74558fad4b4a5417e7cd2f9f535e960`.
- Ready project `cli-ready-project.zip`: SHA-256
  `4d89fd52f404b0b29cc92d8d709c503b6d0f96419a612cf265e7856f6d67caa7`.
- Python final raw result: SHA-256
  `8c3c606b017f59754f5530af4921e07388bb8ebf8bdc8be4d13e2ac88e75d1ac`.
- Native final machine report: SHA-256
  `c57958c6014291afe3a092c4de27ae6b9f70c37f24894e100a5ddb074dacd6bf`.

## Earlier attempts, 2026-11-09

These historical prerequisite failures did not execute a generated fit. They remain part of the record.

| Interface | Date | Model | Outcome | Scientific comparison |
| --- | --- | --- | --- | --- |
| Python notebook | 2026-11-09 | GPT-6 (Codex; exact backend variant not exposed) | Failed: required tutorial pages returned HTTP 404 | Not reached |
| Command line | 2026-11-09 | GPT-6 (Codex; exact backend variant not exposed) | Failed: required tutorial pages returned HTTP 404 | Not reached |

In both attempts, the documentation root, assistant index and collection downloads were reachable.
The required tutorial index and worked LBCO reference were unavailable. The attempts stopped there:
no substitute checkout was used, no generated artifact was executed, and no fitted values were
compared with the regression references. No preview trial is recorded by this evidence.

The prompts remain available for [Python](python/tutorials/assistant.md) and
[the command line](cli/tutorials/assistant.md). A successful trial requires fetching the actual
published references, executing the generated notebook or project, and comparing its scientific
results with the tutorial references. A documentation build alone does not supply that evidence.

### Historical provenance

The original trial records name prompt commit `557d6e703`. Their prompt SHA-256 digests are:

- Python: `a5d78847928809368f87ed8260439bc4218fd1837248fc678b03dbac0eb84e1c`.
- Command line: `e958568b03ff3447ab6ed7394fc6cfb5544ddcdd08dde7555f63b56cd18c521c`.

The captured summary is identified by source commit
`37e53a6cf1e38b88549a241717f1eb49d57499bb` and SHA-256
`85b40bef0e02d3b13b077e5d056c3d51cfc6f70f88072f8d1dec96a48a5da0ff`.
These identify the historical source; they do not identify the later trials above.
