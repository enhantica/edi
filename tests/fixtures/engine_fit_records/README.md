# Engine fit records

Run `python -m tests.fixtures.engine_fit_records.generate` in the pinned default
environment. The generator invokes the SDK's independent crysta CLI on its pristine
source corpus, with `--dry`; it never fits through edi or changes a project.

`joint-tail-default.json` is a parity regression pin for the TOF model that includes tails of
reflections outside the measured range. Before writing it, the generator checks every independently valued
FullProf reference in the corpus at its original bound. The receipt hashes the
complete external artifacts, expected table, historical transcript and input files.
The historical transcript remains unchanged for codec consumers. Live fit values,
uncertainties, bank metrics and persisted metrics use the current model's record;
their comparison tolerances are unchanged.

`cosio-ladder.json` records the resumed ladder finding no accepted step. Its status is `no_step` and convergence is false. The prior compact
record's iterations, metrics and diagnostic counters remain byte-identical. Other
registered descents retain their original corpus pins and successful status.
Only elapsed-time fields are omitted from these records.
