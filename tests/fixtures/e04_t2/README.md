#  independent acceptance inputs

`generate.py` parses every `loop_` in the committed CLI project directories and
 witness projects. `loops.json` records source paths, SHA-256, columns and
row counts. No app category API or Python edi package supplies that inventory.
Regenerate with `python tests/fixtures/e04_t2/generate.py` at authoring time only.

The look reference is easyscience/easydiffractionbeta `ec1d04ee`:
`easyDiffractionApp/Gui/Components/Pages/Analysis/SideBarBasic.qml` makes the
Parameters/Fitting groups untitled and non-collapsible; its
`SideBarBasic/Fittables.qml` puts native limit boxes on each side of the slider.
`Pages/Model/SideBarText.qml` puts a block selector above the aligned text view.
The theme tokens come from gui-components' `Gui/Style/Colors.qml`, and bundled
font families from the owner's committed 2026-09-28 font records.
The absent-value tolerance is 1e-6, from the producer's
`include/crysta/fit.hpp::kDefaultChiSquareTolerance`, forwarded by
`core/src/adapter.cpp::default_chi_square_tolerance`. The  editable
project omits the tolerance and witnesses that fallback. Separately,
`docs/user/cli/pd-neut-tof_si-sepd_start-2/project/analysis/analysis.edi`
declares 1e-4; its loaded value and a subsequent 0.0025 edit witness explicit
overrides. The packet's 0.0001 Analysis Text example is not the default.

Published test seam: `AppState.platformColorScheme` is writable for the Qt test
and demo, and normally bound to `Qt.styleHints.colorScheme`. The test selects
Light/Dark/System through the base `Colors.theme` setting. The seam does not
claim to test the OS integration on the headless Linux runner.

Category targets retain 's `group.<edi category>` names. Each loop group
contains a real ListView-based base TableView, with header and row delegates;
its count must equal the input file's row count. A fields-only negative witness
must be rejected by the same observer. Colour-pair controls reject a fixed
foreground across a theme switch.

CI/build contracts live in `tests/integration/py/test_e04_t2_build_contract.py`,
where Python is the appropriate harness. The Qt tier consumes committed data
only; it neither invokes Python nor imports edi's Python extension. CI timing
and image review remain measured/review evidence, not a claim that a source
scanner proves speed or appearance.

Capture evidence map: implementation supplies
`docs/dev/design/-captures.json`, with a `captures` array. Each entry names
`image` (basename in the shared edi expected-image set), `notes` (owner note
numbers), `theme` (`light`, `dark`, `system`), optional `expanded` (category ids)
and, for Report Text note 13, the pinned `timestamp`. Every visible note 1–14
is mapped. This is an inventory gate only: normal app-ui-test compares every
image, and review/conductor still inspect the images against the owner notes.

Note 19's shell check observes evaluated BUILD/PREFIX paths before a controlled
fetch refusal for app and default environments. It proves the declared path
separation, not that a real compiler cache hit occurred. CI wall-clock payoff
and ccache persistence remain implementation measurement evidence.

Display precision is the reference gui-components
`Gui/Logic/Utils.js::toDefaultPrecision`: three significant digits when no
uncertainty supplies the precision. The nontrivial witnesses are
1.2866603586797143 → 1.29 and 0.0025646436261 → 0.00256. Both retain their
original stored double, including on focus loss without an edit.


## Corrected note 20 (owner, 2026-09-29)

Authority: development hub `knowledge/decision-records.md`, "OWNER CORRECTION: 
note 20 means build once per full run", committed with the amended packet.
A full sequence builds once before checks; each standalone step builds first
on every invocation. Freshness detection is no longer an acceptance property.

The removed assertion `test_checks_do_not_depend_on_a_build` prohibited build
dependencies for each of `app-lint`, `app-test`, `app-ui-test`, `group-app` and
`app-build-recovery`. Every instance contradicted the corrected standalone
requirement, so all its parameter rows are removed from the runtime bank.
The Qt runtime witness previously admitted a stale-artifact refusal instead
of running the checker, and attributed its no-build assertion to notes 16/20.
It now requires the explicit runner seam to execute, with no Python/build/network
during that runtime (note 16). The independent note 15 app-run no-build checks
are unchanged. The checked-in `test_e04_t2_gate_escapes.py` contains only runner
matrix and image inventory controls: it has no freshness case or associated
freshness runtime row to remove; all those unrelated controls remain.

The replacement shell witnesses copy production task declarations and scripts
into a temporary directory. `task_spy.py` interprets declared dependency order
and per-invocation deduplication; builders and terminal checker programs are
spies. Real shell orchestration runs, including nested task invocations and CI
step environments; no compiler, fetch or native GUI runs. Only unrelated verify
tasks are omitted. Counts and order are independently specified from note 20,
not generated from implementation output. The recovery exercise's deliberate
second build remains separately conditional under note 21.

Coverage includes repeated standalone calls with existing artifacts, failed
builds stopping checks, app-verify/app-gates, verify-quick/verify-full/verify,
and both desktop CI matrix platforms. Observer controls reject missing,
duplicated or late builds and omitted checks. This is a shell sequencing claim,
not a pixi implementation test or native app/full-suite attestation.

Review-7 adaptation: the dispatcher previously keyed only on the task name,
which hid the observed duplicate between inherited and explicitly qualified
app-build references. It now keeps the declared environment in task identity;
a dispatcher-level negative witness must produce both builds and fail the
same sequence assertion. Explicit shared references still execute once.
`--skip-deps` is accepted before or after the environment switch, omits the
build dependency and retains the checker and selected environment. Controls
include the recovery invocation; the normal CI witness still excludes its
intentional change-scoped rebuild. `merge-tasks` joins the verify aliases.

The retained  gate previously searched all dependency command text for
task names, losing group-app when it became a direct pytest command. It now
requires each task to be reachable and to carry its actual checker command,
including the Python app suite; missing-edge and empty-checker controls fail.
Both desktop platforms, native app checks and failure-image uploads remain
required. These changes adapt representation without relaxing build counts,
ordering, repeated standalone builds or failure propagation.

The retained  CLI wiring gate previously walked only string task dependencies
and accepted any one matching CI step. The corrected note-20 graph introduced an
environment-qualified dependency mapping, which raised TypeError during that walk.
It now resolves task definitions and dependency identity in the declared environment,
and checks verify, verify-quick and verify-full for the complete registry runner.
For note 18, CI runner matrices resolve through the existing shared runner observer;
both Linux and macOS must execute the full CLI task in an unconditional, non-optional
pull-request step. Dispatch-only native placeholders, optional/conditional jobs or
steps, shell guards and project-subset invocations cannot supply that evidence.
The other retained workflow gates already support the matrices or inspect unaffected
jobs, so their assertions remain unchanged. No native build is part of this check.

The retained  parameter-column observer previously positioned the ListView,
scrolled its row once, then read after one polish/render wait. macOS CI exposed a
row still outside its enclosing sidebar viewport. It now scrolls and polishes the
table before positioning the row, then retries row exposure within a bounded wait
until rendering has settled, scrolling has stopped and every asserted label is
inside its clipped viewports. It retries geometry only: the same native name,
units, uncertainty and admissible-bound assertions still run once against the
independent inputs. Hidden, clipped, blank and incorrect text remain failures.
