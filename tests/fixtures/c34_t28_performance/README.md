#  independent  timing procedure

The reference is development hub's closed edi  record, as named in
`project-provenance.json`: the five-bank TOF project, a three-uncertainty starting
perturbation, three alternating crysta CLI / edi CLI repetitions on one machine,
and a bound of 1.3 on the ratio of median engine times.

Run `generate_project.py` to reconstruct the committed project from edi main
`f3ea7afea400639f2a66d6acb8d922163f1ef128`. It verifies main reachability and reads
Git blobs, then adds three uncertainties to each numeric uncertainty-bearing
input token, preserving the uncertainty and exponent. The provenance file names
every source and generated file hash and each transformed-token count. This is
an explicit reconstruction of the issue's perturbation recipe, not a claim of
byte identity with the old uncommitted benchmark directory. It is not a physics
oracle; the timing compares two executions of identical input bytes.

Invoke `measure.py --crysta-bin <executable> --edi-python <python> --output <new-directory>`
from edi's configured environment. Launch it detached with a persistent log. Each
execution gets its own identical project copy and uses `--dry`; a write to that
copy refuses. Only a completed, converged fit with positive finite engine time
can count. The two CLIs must agree on iterations, free and fitted-point counts,
and the fit objective. Every stdout/stderr is saved. The report records machine,
commands, executable hashes, the individual engine observations and medians.
The 1.3 endpoint admits; larger ratios return nonzero.

The script measures the executables selected by the caller. It does not certify
that a checkout built those executables, that both contain the same engine, or
that a final CI head is proven. The implement lane must provide that build
provenance alongside the final measurement; an older SDK diagnostic is not gate
7 at the final head. The counterexamples exercise separate processes, all six alternating launches,
identical input hashes, nonzero/empty/mutating middle executions, diagnostic
retention, work comparison and the bound. These controls do not prove the live
timing result. Crysta's existing A/B
performance gates still supply its side of gate 7.
