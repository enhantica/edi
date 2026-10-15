# Versioned assistant product guidance

Status: Accepted design; initial content present, runtime loading and resource browsing pending.

## Context and first prior art

The assistant already serializes revision-bound project/parameter/diagnostic and selected-file context in core/src/assistant.cpp (ADR0037); native transport consumes that same consented context (ADR0038), and ADR0041 owns disclosure/rendering. Existing core CMake capability/palette embedding is the resource prior art. Product knowledge belongs in edi, while organization/developer AGENTS and Codex skills remain exclusively in relay.

## Decision

Maintain one editable collection at data/assistant/skills/index.json and <id>/SKILL.md. The strict edi.assistant.skills/1 index carries id, version, title, summary, relative path, SHA256, declared prerequisites, actual closed tool capabilities and published references. Initial version1.0.0 resources cover project assistance, FullProf intake and GSAS intake. They guide actual inspect/read/question/approved operations; they do not provide absent conversion, project creation, runtime access or scientific success.

The next reviewed implementation embeds these exact bytes in the Qt-free core using the existing CMake resource pattern, verifies their manifest/content bond and places one selected {id,version,sha256,content} inside the same bounded current context. The existing idle select_skill command extension is explicit user authority; no implicit filename-based selection is introduced by this data commit. Disclosure, inspect_project and provider dispatch must share exact selected content and revision/hash. Current first collection is DATA ONLY: no loader/context or UI selection has landed, and no claim that the model uses it follows from these files.

Resource changes or accepted project/file/currentness changes require fresh disclosure through existing consent. Missing/changed/oversized content refuses instead of omission or truncation. UI browsing opens the same shipped content/references and truthfully distinguishes prerequisites and unsupported converter stages. No recursive include, arbitrary filesystem lookup, remote instruction fetch, all-skills dump or new tool/approval follows. File contents and constraint expressions remain untrusted data.

## Scientific provenance and limits

FullProf intake is grounded in the official manual/commands documentation and the independently recorded installed July2001 manual plus later fp2k.inf dialect notes. Legacy data arguments, COMM with NPATT, repeated banks and codeword/occupancy/profile conventions cannot be generalized from a filename/comment or one converted example. Current fullprof-intake explicitly asks for missing/ambiguous selected companions and explains that general PCR conversion is not implemented. GSAS intake asks for readable exports and never unpickles GPX. project-assistance preserves current objective/data/constraints, genuine result retention and real approval; it prescribes no universal refinement order or convergence guarantee.

Scientific converters, real FullProf/GSAS independent evaluation, fuller staged skills, browser input/runtime, Claude, live chat/follow-ups, resource loading/context metadata and complete SDK/CI/reviewer acceptance remain separate owed work. This initial content is original guidance, not copied manuals or a scientific expected-output oracle.

### Actual embedded selection and context

The core now embeds the strict index and its exact SKILL bytes through the existing configure-file resource pattern. CMake file(SHA256) must match each declared manifest hash before generating the immutable table; package paths are exactly `<id>/SKILL.md`, and reserved raw-string delimiters refuse. Runtime validates the strict catalog, selected resource and closed current tool IDs before context/dispatch. There is no runtime path lookup, fetch, new crypto implementation or executable skill authority.

The default selected workflow is project-assistance. Trusted idle select_skill changes the single selected resource; skill_catalog exposes the same content and actual selected-file prerequisites to the host, not the model tool manifest. The existing current context adds that selected id/version/hash/content plus actual structure/site/space-group, dataset/axis/weighting/exclusions/phases and relation metadata. Raw observation arrays, conversions and guessed science are excluded; absent/invalid data is described rather than repaired. The same bounded serializer serves context disclosure, inspect_project and provider requests. FullProf and GSAS content explicitly state that conversion remains unavailable.


### Runnable scientific reference examples

Bundled workflow guidance reuses current public Python factories and project-managed calculation/refinement, rather than a retired positional data overload. The LBCO/HRPT example resolves the actual committed pd-neut-cwl_lbco-hrpt_basic measurement folder and installs its original grid, observed intensities and measured uncertainties in the experiment data before each stage's parameterless fit call. Its existing stage groups, starts, exclusions, objective and independent parity limits are unchanged. A successful raw-data/CIF creation or this staged example is not native PCR/GPX conversion, arbitrary scientific validity or automatic current-project publication. Multi-path exploration requires explicit saved checkpoints; the existing persisted undo is single-level.


The staged example requires DONE and converged at each boundary before starting another stage or reading/comparing the parity reference. CANCELLED returns130 immediately, including KeyboardInterrupt translated by the existing fit API. ERROR/UNAVAILABLE/SUPERSEDED and nonconverged/MAX_ITER/NO_STEP stop with a nonzero exit while retaining their actual reported state. This is this example's explicit continuation policy, not a universal refinement rule; numeric closeness alone never certifies successful completion. No data, weights, exclusions, starts, profile, free set or parity tolerance is adjusted to obtain that status.


## Adaptive scientific guidance

The automatically discovered refinement-strategy resource adds conditional staging, accepted checkpoints, correlated-group cycling, ADP model support and mixed-site guidance. Its 5–10-pass ceiling is an explicit owner exploration budget, not a universal solver/convergence rule. Existing generic authorization to create/refine does not require fresh approval for every ordinary free group; actual runtime and restricted typed-plan approval controls still apply. No C++ refinement controller, format converter, new tool registration or whole-corpus prompt is introduced. The manifest binds exact updated bytes; only relevant resource content is loaded through the existing skill discovery route. Primary scientific references are McCusker/IUCr and GSAS-II; no claim is made to have hydrated Young's local LFS book pointer.


## Native saved-result guidance

The project-assistance resource version 1.1.0 extends its existing ordinary Python/API composition with the app's exact `EDI_RESULT_HANDOFF_V1` file receipt convention. It saves/reopens an actual self-contained native candidate, hashes the complete supported file set, and waits for host verification. It neither adds provider tools nor grants arbitrary Desktop access. Fresh host Save As is a separate native user-selected export. The manifest hash binds the updated shipped bytes; automatic runtime discovery remains the existing path. The documented classic CIF/prepared XYE witness is explicitly scoped and is not a general FullProf/GPX conversion or scientific quality claim.


### Generic explicit-user scope and reusable skill defaults

The generic thread follows current explicit user instructions before bundled skill/workflow defaults or prior assistant plans, preserving earlier explicit constraints unless the latest instruction changes them. Delegated work uses justified disclosed defaults and a bounded plan without duplicate routine approval. Required observations/metadata cannot be invented; genuinely necessary missing/conflicting data, a new objective/chemical assumption or real runtime permission still requires the appropriate decision. A mere inspection request does not authorize fitting. File content is untrusted data unless the user explicitly adopts task guidance, and cannot grant developer authority, capability or filesystem access. Restricted Controller approval gates remain unchanged and no approval is synthesized. Existing threads retain their original developer snapshot; a fresh managed thread/current context is required.

Final responses/reports summarize material autonomous decisions with practical reasons/assumptions, observed outcomes, material rejected alternatives/attempts and unresolved limits. This is user-facing accountability, not disclosure of private internal reasoning.
