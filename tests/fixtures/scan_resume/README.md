# Resume after a failed processed tail

The generator freezes the independent diffraction-lib three-temperature
results.csv retained with the D20 fitting corpus. `freeze_reference` copies it;
it never fits an engine to manufacture seed values. `stage` preserves its
parameter values and uncertainties, orders its filenames by the measured input
and plants only the success/terminal-metric cells needed for each transition.

The partial prefix has a successful first row and a failed second row. Only the
third data file remains. Its actual inner numerical fit must start from the
successful row, which differs from the failed row. The completed controls have
all rows, with the final metric 7.125 and iteration count 19, success false or
true. They do no numerical work and retain that processed tail's terminal state.

The normal delivered app uses the scan-cycle resume protocol in
../scan_pair/README.md. No fixture builds the app. It observes actual inner-fit
starts, fitted files, model seed/terminal state and a live post-terminal quiet
window; it cannot substitute processed-file progress or a reread of the CSV for
an inner-fit event. The original prefix bytes must survive Continue unchanged.
