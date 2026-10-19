# Versioned assistant product guidance

Status: Accepted design; initial content present, runtime loading and resource browsing pending.

## Context and first prior art

The assistant already serializes revision-bound project/parameter/diagnostic and selected-file context in core/src/assistant.cpp (ADR0037); native transport consumes that same consented context (ADR0038), and ADR0041 owns disclosure/rendering. Existing core CMake capability/palette embedding is the resource prior art. Product knowledge belongs in edi, while organization/developer AGENTS and Codex skills remain in the separate developer tooling.

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


### Confirmed mixed-site ADP candidates within delegated scope

The refinement skill's explicit pre-fit same-phase/co-occupant relationship check and bounded shared-ADP comparison do not add a new preference gate after the refinement/model choices were delegated. Explicit no-sharing/independent-model constraints remain authoritative, and attempted candidates require unchanged observations/objective, actual physical validity/uncertainty/covariance assessment and saved/reopened relation/calculation readback before acceptance. High uncertainty alone does not establish a shared site or justify universal equality.

The real Python relation entrances are project.analysis.aliases.create(id=..., param=...) and project.analysis.constraints.create(expression=..., id=...), as implemented by Analysis in lib/edi/__init__.py and existing keyword-only bindings. No Project forwarding API is added to repair earlier guidance. This changes versioned guidance and its manifest digest, not a C++ autonomous strategy/controller or a claimed scientific result.


Native production guidance names only the actual C++ tools, treats Python/CLI helpers as development/test references, and never requires a Python install/module/source checkout. The automatic bundled skill catalog and digest validation remain; descriptions distinguish live fit outcomes from unavailable isolated trials/checkpoints/import/constraints. Existing restricted compatibility instructions apply only when those actual tools are offered. No extra scientific-plan confirmation is imposed on a genuinely delegated native objective.


The project-assistance 1.4 guidance names the implemented `create_cwl_project` recipe/selected-ID boundary and distinguishes native creation/adoption, reader diagnostics, asynchronous calculation, unsaved state and fitting. Delegated routine starting choices remain authorized, explicitly identified as assumptions rather than measured facts; unsupported packed formats, save/report, constraints and checkpoint operations cannot be replaced with production Python. Skill/index hashes are updated together; normal automatic discovery remains.


### Skill capabilities remain bound to their actual execution registry

The shared skill index is validated by the restricted core Controller before serializing any project context, even in the generic native app. Its `capabilities` rows name only implemented tools in that Controller's closed manifest; an app-only dynamic tool must not be inserted there as though the compatibility dispatcher could execute it. The native `create_cwl_project` name is declared by the app's real DynamicToolSpec catalog and complete outgoing `native_actions`, and its conditional skill instructions remain. Removing that unsupported entry from the shared index does not remove the native tool, relax unknown-capability validation, or synthesize a core create handler/approval. Native relation and future save/report tools follow the same rule unless their actual compatibility implementation exists. Skill content hashes and versions remain unchanged when only this registry attribution is corrected.

The reached regression was earlier than launch/auth: `Controller::context` always validates the bundled index, the creation-only capability was unknown to its manifest, and the normalized invalid-argument metadata error blocked Sign in before any helper request. Empty and loaded contexts share that validation; no scientific fixture or account change repairs it. App sign-in and its disclosure now distinguish the existing resource-exhausted, invalid-metadata and unavailable cases using known codes; they never echo raw provider/config/error data or report every context error as a capacity problem. Genuine malformed/oversized context still refuses before launch and consent/admission.


A genuine Sign in attempt also owns a bounded app-local failure dialog, using the existing AppDialog/scrollbar/plain-label presentation. A synchronous prelaunch refusal or an actually failed connecting transition displays the already bounded public error, rather than disappearing when the consent dialog accepts. A successful connection emits no failure; an unrelated error without an initiated attempt cannot open it. Actual conversation/owner retirement cancels that presentation attempt. This is failure feedback, not another scientific-plan/context approval or a provider reply. The original consent, launcher, auth and restricted Controller permission paths are unchanged.


### Native recipe profile choices are actual core tokens (2026-10-16)

The native creation recipe previously described peak_profile as arbitrary short text while the actual selector accepts canonical core IDs. A delegated agent could therefore invent plausible display spellings and fail before project creation. The recipe schema now derives its enum from supported_peak_profiles(CONSTANT_WAVELENGTH), the same existing core catalog used by normal selectors, and parses only those exact choices. No parallel profile list, synonym guessing, new scientific model or host-selected profile default is introduced. User-supplied wavelength/recipe intent remains authoritative; the agent chooses justified offered options only within delegation. A fresh actual thread/catalog is needed for updated tool metadata; old instructions are not retroactively changed. Source preparation is not an observed explanation for any unexpanded owner error beyond the confirmed metadata omission.

### Configured native skill inventory and immutable disclosure

The first implementation is the app's existing bundled resource staging, runtime skills/list discovery and complete context/disclosure lifecycle. Built-in and selected local packages now use one bounded inventory capture. Local selection is an instruction-read scope only. A source is a standard SKILL.md package or a collection of immediate packages; names/front matter must be valid and unique, and every captured file belongs to a declared package. Files/entries, path lengths, payload and catalog size retain the existing Limits/SelectedFileLimits. Canonical directory identity is pinned and rechecked; directory/file opens reject links and special members, compare actual opened/named identity, and refuse changed files/directories. Missing, malformed or duplicate sources admit no partial replacement. The bundled manifest still binds its original resource hashes. Compiled Qt skill resources are fixed for the process lifetime. After the existing fresh preference reload and original owner/validity checks, an already captured inventory may be reused when no local source is enabled; initial capture still validates every bundled hash. Configuration changes invalidate or replace that inventory before publication, and invalid settings clear it. Any enabled local source keeps the original full physical/content capture, even when its previous fingerprint matches. This reuses the existing retained owner, not a presentation/authorization cache: context, consent, staged-file checks and native admission remain fresh, with the original resource accounting and no poll change. No remote source fetch or source text can add native tool IDs, project roots, writes or network permission.

Approval owns the immutable captured inventory and configuration identity. Staging copies those exact approved bytes into a fresh Edi-owned instruction directory; it never recaptures a different source at this boundary and never overwrites an existing provider-modified stage. The staged snapshot, runtime declarations, bootstrap/backend proof and final submitted disclosure are bonded. Every required staged resource, including auxiliary files, is hashed before Send; changed source/staged content or configuration refuses before input admission. A source/configuration A→B→A transition cannot make staged B stand in for approved A. Disabling/removing a source retires the existing context through its original lifecycle; the next Edi-managed stage/disclosure excludes it. All-disabled stages an empty skills directory and requires zero registered Edi source paths. Unrelated provider-global/plugin behavior is not relabeled as configured-source authority or isolated by this feature.

The settings decoder reuses the first strict JSON parser and the receipt parser's concrete pre-admission accounting: borrowed QSettings value, raw encoding, strict AST/key/number/string temporaries, decoded strings, replacement rows and old/new canonical COW/configuration/encoded/settings owners overlap until their actual release. Token/depth/closed-shape checks precede owning parser copies. Source capture charges payload, file/path/catalog/decode/front-matter/hash and concurrent manifest owners before growth. It counts UTF-8/UTF-16 explicitly, without a guessed Unicode multiplier or capacity increase. A weak inventory identity list keeps an original snapshot counted while a local callback frame still owns it; shared inventory bytes are counted once across approval, stage, backend and local frames. Registration transfers the existing reservation to that actual live owner without a double charge. Conservative temporary high-water charges remain until the original frame exits; they are not released while payloads are live. Edi's scientific model is not charged again as an instruction inventory.

Loading may emit the existing model and property signals. Every affected preparation/disclosure/bootstrap/Send/native refresh caller carries its original weak receiver/State/controller/project/account/input proof before its first post-effect member read, catch publication or admission. A deleted/rebound receiver abandons old presentation; a genuine committed settings or scientific result remains factual. Source setters additionally carry the original serial through reload and publication. This extends the existing common callback/transport retirement rules rather than suppressing observers, recapturing a replacement owner or adding a callback framework. Existing effective readOnly/never policy and final model/effort proof remain required. Raw measurement/general-read exposure warnings stay accurate; this is not the later isolated host/privacy boundary.

### Discovery catalog ownership and disclosure refresh

Runtime discovery extends the original bundled catalog. Each required staged
file is compared with its approved immutable bytes using the existing bounded
read buffer. Borrowed provider strings are sized before their decoded owners;
the complete content decode, temporary JSON row, growing catalog and table-key
replacement roles are admitted before construction against the same joint
application/transport slot. The encoded catalog limit remains strict. Empty
and all-disabled inventories require no file-read buffer.

The catalog uses the original canonical Rows mechanism rather than another
independent model payload. A const shared catalog snapshot owns its JSON rows;
weak identities count each live snapshot once, including an old callback frame
after a replacement. Transfer removes its preparation reservation only after
the tracked owner exists. Current model rows remain charged until replaced or
cleared; source disable/removal alone cannot declare them released. Temporary
roles unwind after their actual payloads and reconcile the original transport
generation. These are retained-payload/container admissions under the existing
policy, not a claim to measure Qt allocator overhead or process RSS.

Source reload and successful or failed settings writes retire the corresponding
old approval and synchronously publish the existing context/consent properties
with original-owner guards before exposing replacement table rows. A failed
write stays explicitly invalid; a committed configuration remains factual if
later presentation retires. No builtin error fallback, replacement-owner
recapture, deferred publication dependency or additional permission is added.


### A chosen measured background spans its actual range

The existing project and refinement guidance now asks the assistant, when it chooses
a new measured line-segment background, for three distinct finite starting positions
spanning the actual measured range, with explicit justified starting intensities
and free flags. This starting model is not a scientific adequacy guarantee. It is strategy for a delegated new choice, not measured factory
facts or an automatic estimator. Missing actual range/evidence calls for offered
inspection or one focused question. User-explicit anchors/values, observations and
exclusions remain authoritative. Existing backgrounds are not rewritten merely to
meet the guidance.

The original native/manual minimum of two API domain, schemas, parser, scientific editor
and Undo are unchanged. The compiled developer instruction and both versioned
skills agree; the existing index bonds their exact bytes and versions. No material
constant, capability, tool, approval, model call or strategy execution engine is added.


### Individual and compound file-load guidance agree

The existing individual-action paragraph uses the same file-load contract as
compound creation and the registered tool descriptions: Show actions presents
the original Load pointer/click cue without dispatching device, clicked or
file-dialog events, then the original validated import consumes the admitted
file ID while original source proof is current. Missing or changed originals
refuse. Manual Load retains its system dialog; other real visible controls,
fresh Save As, attachment and skill-source choosers keep their original roles.
The bundled skill version and index digest change together. This corrects
instruction consistency, adding no native operation, schema or permission.


### Final captured inventory roles

The original capture_skill_sources tail keeps the measured encoded declarations
charged together with every live hashing/output role. Its existing sorting
QList handles are scoped and destroyed before hashing starts; the preceding
admission still covers their overlap with declarations. The next admission uses
the larger of the exact existing UTF-8 path size and SHA-256 output length before
path encoding, per-file digest or final fingerprint allocation. Those temporary
hashing outputs are successive. The final immutable declarations and fingerprint
remain charged together through transfer, including an empty all-disabled
inventory. No guessed padding or capacity increase is used.

Both original capture callers retain their existing high-water preparation
reservation until actual captured owners are either registered/transferred or
destroyed. retain_skill_inventory still checks the original retainedBytes result
before settings persistence; weak inventory registration, joint VM/transport
admission and old/new callback ownership remain unchanged. Source identity,
validation, ordering/fingerprint bytes, consent/currentness and publication
fences are preserved. An input click followed by a source error alone does not
identify which runtime exception occurred.


### Temporary preparation failure is not malformed configuration

The existing source-preference loader distinguishes strict content validation
from temporary transport, allocation, I/O or joint-admission failure. Actual
malformed configuration keeps its original invalid projection, cached refusal
and synchronous disclosure publication; it never falls back to built-in skills.
A temporary failure marks the existing load-readiness flag unavailable without
publishing a fictitious configuration change or destroying the last known rows.
Inventory authorization and source mutations check the loader result; pending
native admission also requires the existing loaded/valid flags. No stale retained
inventory becomes new authority. A later successful read validates actual settings
again. Unchanged valid rows restore readiness without changing their configuration
identity or discarding a good approval; changed rows follow the original
publication and retirement path. This prevents an old failing transport frame or
retired process buffer from permanently poisoning fresh reconnect context.

An already-open Add-source chooser retains its original owner/configuration serial
across temporary read failure, but its acceptance must fresh-load successfully
before using retained rows. A changed configuration retires that old intent; it
is never recaptured into the chooser. Common source commit repeats the fresh
read and original serial/readiness check before staging any replacement, and
rechecks readiness before persistence. Enable/remove retain their fresh-load
entry fences. Actual malformed-store recovery remains an explicit valid edit
from the original invalid projection; readiness does not imply validity.

### Natural visible groups preserve exact scientific requests

New measured background choices default to three spanning anchors. Explicit user
points, values and recipe counts remain authoritative; the native/manual minimum
is still two. Related aliases are requested together immediately before their
relation/use; the existing relation sequence completes aliases before constraints.
No orchestration layer or material-specific script is introduced. Compiled
developer guidance and both versioned skills/index use the same defaults.


### Selected text is an offered native read, not a new skill capability registry

Bundled project/FullProf/GSAS strategies now direct actual offered read_selected_file use for readable already-admitted text, preserve exact source identity/range/completeness and remove metadata-only/paste-again assertions. Scientific units/conventions, ambiguous associations, unsupported binary/GPX and absent app-action mappings stay explicit; no format-specific parser or generated-file workaround is introduced. Actual callable schemas/options/help remain code-owned. Skill bodies/version/index digests change together, while their restricted core capability lists/dependency validation remain unchanged; native app names are not inserted there. This source change alone does not establish a full PCR reconstruction workflow or a qualified dedicated runtime.
