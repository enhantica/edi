#  declaration gates

`seed-analysis-before.json` records the original analysis documents from edi main
`61c3e03` (). Regenerate with `python tests/fixtures/c34_t24_minimizer/generate.py`.
The  byte gate now allows only descent/tolerance declarations in these documents;
every other seed file retains its original blob identity. The scan extension alone changes
its expected.json. All three formerly non-executing seed expected.json files remain pinned.

The system gates accept a provenance column either unqualified or category-qualified;
its final component is `file_path`, `descent`, `chi_square_tolerance`, or `max_iterations`.
Each result row requires exactly one matching provenance row, in the same order.

Adaptations:  formerly passed --descent, now writes analysis.edi, preserving all
registry-id dispatch and numerical assertions. The parser gate now requires removed flags
to be unknown.  formerly listed failed names after the summary; it now asserts the
same counts, times, progress, and resume behavior while refusing that list.

Seq 2 adaptations (ADAPTATION, not WEAKENING):

- / previously pinned the exact  exceptions before the CLI removal.
  Now the exact set also includes `option:fit:descent` and `option:fit:list_descents`.
  The calc retirement, issue bindings, duplicate/stale refusal and wildcard controls remain.
-  previously anchored the adapter before declared-condition dispatch. Now its
  current-source digest and line count anchor the extended adapter. Regenerate using
  `python tests/fixtures/c34_t24_minimizer/refresh_adapter_anchor.py`.
  The frozen pre-extraction source, classification, totals and complete-file-set checks remain.
-  previously passed `failed_files` to the summary. Now it calls the reduced API
  and still requires the exact count, chi-square range and elapsed-time output with no list.
- Runtime banks previously lacked the  nodes and retained removed CLI node names.
  The standard focused measurement producers add only newly collected green nodes and drop
  stale rows; unchanged measurements, tier bounds and breach dispositions remain.
  Crysta  and development hub  keep their discovery/audit assertions unchanged.
- development hub  previously found the repo by a fixed parent depth. Now it uses the shared
  marker-based finder, preserving every register assertion and satisfying 's discovery rule.
- Both passenger whitespace-refusal cases now have an explicit whitespace-free pytest ID;
  the quoted trailing-space input and required refusal are unchanged. This preserves coverage
  while allowing the existing runtime parser to identify the measured node.
- CLI variant checks previously grouped all real fits into one test per project. Now each
  unchanged pinned variant executes as a separate real-fit node; a separate transport-only
  control traverses each full original manifest and verifies every launch and declaration.
  Its deliberately incomplete stub record must fail numerical comparison, so it cannot
  substitute for the real-fit evidence. The real later-variant corruption control remains.
  No variants, pins, thresholds or fit conditions are omitted or loosened.
