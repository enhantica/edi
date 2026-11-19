# Linked structure work

Build `edi_linked_structure_calculation_tests` in the app build, then run it with
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`. This uses the actual linked-structure
model's append operation on the committed TOF powder fixture, with a second structure.
The native test counts preview admissions and actual structure-factor evaluations against
one forward calculation (or less when the control warmed the factor cache), and checks
the published pattern against that independent calculation. It also checks that superseding requests cancel the first token,
skip the intermediate membership and publish only the newest result.

For the full engine-call count (structure-factor reuse can hide a pattern recalculation):

```sh
.pixi/envs/default/bin/python tests/fixtures/linked_structure_work/check_calculations.py --gdb gdb
```

The debugger counts `crysta::calculate_project` between the link action's markers,
including calls made internally by spelling validation, plus parses and loop renders.
This is a real native replay, not a count of preview signals. GDB 15.1 was used locally;
GDB 18.1 exited before finishing this threaded replay, without a diagnostic.

For a Linux attach sample set `EDI_LINK_PROBE_HOLD=1` on the native test. It prints its pid
and allows ptrace, then holds briefly before the link action. The ordinary test does not
change ptrace permissions. The fixture never builds itself or reads the hidden test tiers.
