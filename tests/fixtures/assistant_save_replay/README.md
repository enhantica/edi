Run from the product checkout with the app environment, using a compatible
`assistant_real_owner_probe` executable from the revision being bisected:

Enter the existing app environment and use the same display harness as the GUI
checks for Show ON. From that environment:

```sh
source tools/ci/app-platform.sh
app_x_display save-bisect
export QT_QUICK_BACKEND=
python tests/fixtures/assistant_save_replay/replay.py \
  --binary /absolute/path/to/assistant_real_owner_probe \
  --output /absolute/path/to/new-evidence-directory
```

The output directory must not exist. The driver uses the existing native probe
protocol and offline Codex peer; it never contacts a provider. It does not build
or change a checkout. Keep this fixture and its native driver support at the
current revision while passing an older executable to `--binary`.

Each mode opens a retained LBCO project to establish a last-open parent, admits a
CIF and HRPT measurements, creates and imports into a fresh project, saves,
selects only its independent scale for a trial fit, invokes Undo, and saves again.
The CIF transcription and source are recorded in provenance.json. This is a
reconstruction of the reported workflow, not the owner's exact attachment or
an independent numerical fit validation.

`RESULT.json` and each mode's `steps.json` retain actual native tool replies,
Session path, filesystem existence, Session.locationText (the Project tab's
binding), and any realized project.location text item. The expected last-open
parent is separate from the actual Create destination. Refused tools are retained
as refusals; their mere invocation does not establish a fit or Undo. Driver/setup
failures are recorded separately. The original project is copied before opening;
all work happens in the evidence directory or the probe's temporary Documents.

No new production entry point is required. A binary missing an existing probe
operation fails with its original error. Historical binary compatibility must be
reported with that binary's hash; merely accepting --binary is not such evidence.

The current diagnostic observation is in observation.json. Both modes completed
an adopted fit, applied Undo and successful Saves. Neither reproduced the missing
folder error. Both used isolated Documents instead of the last-open parent.
Earlier offscreen/setup failures remain under build/tests-seq17; they are not
successful Save reproductions.
