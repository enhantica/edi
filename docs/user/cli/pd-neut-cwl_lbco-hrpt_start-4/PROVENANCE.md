# pd-neut-cwl_lbco-hrpt_start-4 — provenance

crysta fitting case `lbco-hrpt-s4` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/lbco-hrpt-s4/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/lbco-hrpt-s4` (tree) | `a6c1dfe105a6f53a4951916aefd525be2bf0837a` |
| `tests/fitting/lbco-hrpt-s4/project` (tree) | `6b2f38daf8efdcccc79488d694e94fd9e84068be` |
| `tests/fitting/lbco-hrpt-s4/expected.json` (blob) | `b72cce960a0e49bdf80b1c715f08de366bfae447` |

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The copy stays byte-identical to its source, whose
new content ids are `tests/fitting/lbco-hrpt-s4` (tree) `13faadd66ec255fa30ebb611dcb63546720bf905` and `tests/fitting/lbco-hrpt-s4/project` (tree)
`25f762a7cf74aaecd5aa912b0fa963364e9020cd`; `expected.json` did not change.
