The live follow-up uses the existing managed runtime login, gpt-6.1-sol at high
effort, and one ordinary Send per fresh assistant session. The exact request is
in live_request.txt. The model chooses all tool calls and fit trials; the driver
only opens the initial project, attaches the two inputs, selects the requested
model/effort, sends the request and observes the result.

The inputs are this directory's transcribed lbco.cif and the retained
background_estimate/meas-lbco-hrpt.xye measurements. A real copy of the retained
LBCO project is opened first under each session's last-open/previous directory.
This reconstructs the requested workflow on Linux; it is not the owner's exact
macOS session or attachments.

Local receipts are retained under build/tests-seq18. They include the frozen
probe executable, preflight identity, login-availability metadata without account
identifiers, exact driver and request, each session's original canonical history,
native tool outcomes, per-Save path/location/filesystem observations, final UI and
the project copy before teardown. save-observations.jsonl reads Session.locationText,
the Project tab's text binding, without navigating away during the model's work.
Any realized project.location text items are retained separately in that receipt.

The existing Weston/Xwayland display supplies real active-window input. No new
build, authored tool sequence, fit oracle or CI acceptance is supplied by this
diagnostic. The executable is frozen before either run so an independent build
cannot replace it between sessions. Source hashes and dirty state are retained;
the diagnostic does not claim a clean build.

Both original turns completed. Each naturally fitted, used Undo, and reported a
successful Save with an existing folder. The reported missing-folder error did
not reproduce. Both created under isolated Documents instead of the last-open
parent, and both retained an empty project.location text item despite a populated
Session.locationText. Save replies had saved=true and presentation_complete=false.
The per-Save fields and raw native Save replies are in live_observation.json;
full original receipts remain under the local evidence directory.
