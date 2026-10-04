#  scan contracts

`generate_scan_manifest.py` records SHA-256 hashes directly from the owner's
`tmp/projects/cosio-d20-scan-324f`; no calculated result is an oracle. The CLI
project must preserve those source inputs byte for byte.

The bounded performance tests observe native and Python data opens on real fits,
exercise callback delivery before the next file opens, and count per-event work
through 5,184 real CLI progress-consumer calls. The last 648 events may consume
at most 5% more work than the first 648. This operation-count gate is deterministic;
it is not a substitute for the packet's fitted 5,184-file wall-clock measurement
with `OMP_NUM_THREADS=1`, which implementation records separately. The original
baseline is the owner's `<author-runs>/perf5k.log`, documented in edi .

Cancellation tests cover both scan modes, direct single/joint fits, predicate
cancellation, callback KeyboardInterrupt, and real SIGINT at a live callback
boundary (human/machine CLI, first/second signal). No sleeps, polling waits, or
FullProf executions are involved. Partial-file cancellation preserves only the
completed CSV prefix, which is then exercised through a normal resume.

## Terminal callback cancellation (review F1, tests seq 4)

The oracle is the cancellation contract and state conservation, not a fitted
number. The short corpus scan uses a declared one-iteration budget. Its completed
rows may report failed fits; completed and converged are different properties.

| Reachable boundary | Positions exercised                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `on_file_complete` | First, middle and last file, after its durable row exists                                     |
| `on_iteration`     | First, middle and last file; cancellation retains only preceding rows                         |
| `on_scan_start`    | Fresh scan, resumes with one and two completed rows, fully completed no-op resume             |
| `should_cancel`    | Armed by each boundary above; also initially true on crysta's no-op resume                    |
| `on_start`         | Single-fit callback, deliberately silent for scans; fresh and no-op runs prove it cannot fire |

Both sequential and independent modes run through `Analysis.fit` and the native
`Project.fit_sequential` / `Project.fit_independent` entries. Caller cancellation
routes are exercised individually: direct `KeyboardInterrupt`, its subclass,
SIGINT using Python's default handler, setting a predicate flag, returning a truthy
predicate object, raising `KeyboardInterrupt` in the predicate, raising it while
converting the predicate result to bool, and SIGINT handled by a caller's flag
setter. The latter must be observed by the ordinary predicate poll.

Every probe proves that its selected boundary was reached. It checks CANCELLED,
unchanged parameter values and uncertainties, unchanged calculated arrays,
unchanged source model files, retained finished results/provenance bytes, and a
normal exact-once resume. These are distinct conditions: changing the status
alone cannot hide a model write-back.

CLI probes send real SIGINT synchronously at the same boundaries in both modes,
with human and machine reports. Human render callbacks are retained. Machine
reporting normally has no scan subscriber, so an observer supplies deterministic
signal timing at the real engine callback; the real CLI handler, native fit,
save policy, exit code and report are used. Human full verbosity exercises the
iteration renderer. Assertions require exit 130, machine `status=cancelled`, no
traceback, resume guidance, unchanged model files and retained finished rows.
The existing first/second-SIGINT gate continues to exercise hard second-signal
exit. There is no CLI predicate flag; those cancellation routes belong to Python.

Crysta's corresponding gate exercises its own public predicate contract at the
first/middle/last iteration and completion, plus the fully completed no-op resume.
Crysta has no scan-start subscriber; edi owns that boundary and translation of
Python `KeyboardInterrupt`. No new callback API is required by these gates.
