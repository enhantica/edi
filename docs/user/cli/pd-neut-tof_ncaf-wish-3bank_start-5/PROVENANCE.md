# pd-neut-tof_ncaf-wish-3bank_start-5 — provenance

crysta fitting case `ncaf-wish-3bank-s5` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/ncaf-wish-3bank-s5/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/ncaf-wish-3bank-s5` (tree) | `601eb125715722d9efcbc2a54dfe3e8e00c019b5` |
| `tests/fitting/ncaf-wish-3bank-s5/project` (tree) | `c03a7e73566b44e925867507bb7490131e7e2c59` |
| `tests/fitting/ncaf-wish-3bank-s5/expected.json` (blob) | `8844e493fd370128f8c163f0c95751fd03f49783` |

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.
