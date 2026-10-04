#  omitted-selector record regression pin

`default-record-no-elapsed.txt` is an implementation-produced regression pin, not an independent
correctness oracle. It was first captured from the real edi CLI at pre-selector commit `60302545`,
fitting crysta's committed `cosio-d20-s1/project` with `--dry` and no descent option:

```text
python -m edi fit build/crysta-src/tests/fitting/cosio-d20-s1/project --dry --report machine --verbosity compact
```

The sole `elapsed_ms` line is excluded because wall-clock duration is nondeterministic; every other
byte and line order is retained. Per-strategy numerical pins remain sourced independently from the
crysta corpus case's committed `expected.json` and `PROVENANCE.md`.

 refreshed this labelled pin after the origin correction and again after `adb3b700` froze
the generation limit per fit. The latter measurement uses edi `af22657` linked to crysta
`190129d6`, through `tests/fixtures/c11_t62/repin.py`; its exact source commits and output hash are
in `tests/fixtures/c11_t62/repin-provenance.json`. Before/after: iterations 14 to 13, reduced
chi-square 75.61907118 to 75.61970582, Rwp 0.1634551479 to 0.1634558338. Every other deterministic
record byte remains unchanged. This adapts an exact historical record to the corrected engine;
it makes no claim that this default fit reaches the independent reference basin.
