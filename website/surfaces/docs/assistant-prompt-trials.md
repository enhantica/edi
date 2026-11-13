# Assistant prompt trials

These records describe attempts to use the published Python and command-line assistant prompts.
They are historical failures, and do not establish that an assistant-generated fit works.

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

## Recorded provenance

The original trial records name prompt commit `557d6e703`. Their prompt SHA-256 digests are:

- Python: `a5d78847928809368f87ed8260439bc4218fd1837248fc678b03dbac0eb84e1c`.
- Command line: `e958568b03ff3447ab6ed7394fc6cfb5544ddcdd08dde7555f63b56cd18c521c`.

The captured summary is identified by source commit
`37e53a6cf1e38b88549a241717f1eb49d57499bb` and SHA-256
`85b40bef0e02d3b13b077e5d056c3d51cfc6f70f88072f8d1dec96a48a5da0ff`.
These identify the historical source; this page does not claim a new trial or publication.
