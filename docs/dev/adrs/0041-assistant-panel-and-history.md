# Assistant panel and conversation history

Status: Accepted
Date: 2026-10-15
Implementation: Partial; terminal-retention/app lifecycle unit pending independent verification
Priority: High

The assistant is a Session-owned view model, separate from the currently open ProjectViewModel. It remains available without a project and rebinds the controller whenever the project changes. The controller borrows the existing project and worker; approved edits enter ProjectViewModel's existing apply/preview door (ADR-0020). External edits and manual fit completion invalidate the assistant revision. Queued provider requests are fenced across rebinds. Closing a session detaches before child project destruction.

`app/qml/Components/Assistant*.qml` adopts edi's existing EasyApplication components, theme, font and AppSizes spacing. The owner's shared-sidebar decision supersedes the opposite second-sidebar/popup default: one persistent panel overlays the actual workflow sidebar at its exact bounds/side/width. The app-bar action alone changes session visibility through the device gate. Hiding reveals the retained manual controls without cancelling work. The main chart/content geometry does not change. The previous independent width preference is dormant rather than a second reserved strip; no resize handle or segmented selector is introduced.

The panel shows the provider connection, dynamically offered model/effort, public conversation, exact proposed parameter groups, budgets and improvement tolerances, questions, trial activity and Stop. Approval is an explicit user action bound to the current plan and revision. Text is plain and selectable; model text cannot activate links or invoke edits. The scientific chart remains edi's real chart, not a chat replacement. Actual light/dark, left/right, narrow/wide and keyboard visual acceptance is owed; adding QML files alone does not prove it.

Public conversation and activity use the declared `Limits::ui_history_bytes` and `Limits::ui_messages` ceilings in edi's separate app-local history file, written with owner file permissions. Invalid or oversized loaded history is refused and preserved rather than silently evicted. History never includes credentials or hidden provider reasoning. Prior displayed history is an archive; a new controller does not silently replay it to the provider. Clear conversation resets both the visible archive and the controller conversation while idle. Portable export, retention settings and complete protected cross-platform persistence remain subsequent units.

Prior art: edi's sidebar preferences and AppPreferencesDialog, RowTableModel, app-bar extension seam, ProjectViewModel apply and single-fit undo. No base gui-components fork, alternate style system or production test command is introduced. The native test runner observes the real view model and QML object names defined by the accepted task interface.

The committed app foundation includes the actual outgoing-context disclosure and explicit reconsent, available
model/effort selection, queued project-generation fences, literal untrusted text, and save/report edit invalidation.
`configure_engine` owns one real Session per QML engine; the default production chain remains
Session → AssistantViewModel → ChatGptConnection with production services. Internal native-only dependency
composition supports independent offline hosts without replacing the real VM or altering provider security.

This is unfinished integration on the draft branch, not a verified desktop preview. The VM installs the approved `Hooks::reserve_terminal` for its actual public-message/activity/archive role.
Independent capacity, failure/recovery and current production visual/live verification are still required;
headless absence of the hook does not establish GUI retention. Actual `edi_app` production smoke, visual review
and live provider-owned sign-in/model selection/chat evidence remain owed. No completion claim or follow-up
timer follows this checkpoint; the full import/refinement/Claude/browser scope remains active.

The real VM lease prepares complete known call/start/question rows and a terminal placeholder using the
accepted R4 compact-array formula, both byte and slot ceilings, actual wrapper metadata and full original
arguments. Every append/coalesced extension preserves outstanding holds. Started/settle/quarantine run on
the owner thread without reentering controller/provider; complete terminal T is retained as an object. Failed
file retention returns false before canonical terminal commit and keeps the actual core report/lease/hold.
Quarantine displays bounded failure metadata while retaining terminal capacity. Ordinary Stop preserves
that evidence; explicit Clear/project/account retirement fences queued work and releases its old owner.
State retires its controller/leases before archive/model/services destruction. The model reads canonical
JSON payloads on demand instead of retaining another recursively converted payload archive. Rendering is
queued; it reads the retained canonical state after the callback, and rendering failure cannot erase T.

A separate finite per-request failure-row allowance covers the declared generated-error/identity bounds,
with complete row framing and worst-case escaping. It does not reserve another full scientific terminal.
Failed/incomplete/refused/interrupted requests keep bounded original correlation and a visible explanation
in the same conversation; unsuccessful file writes preserve pending evidence and the prior file until
retention succeeds or the user explicitly clears the owner. Provider replay remains the native contract.
New prompts use the actual command acknowledgement, prewritten QSaveFile staging and queued physical
dispatch fences. Composer clearing observes a new actual user-row ID, never lastError emptiness.
Queued initial/continuation sends recheck live connection, turn and privately captured request identity,
project generation and exact disclosure consent before physical I/O.

Empty reasoning effort means Provider default and stays empty in the saved selection. Official-runtime
thread/settings requests resolve it through the selected model's advertised default; explicit tags use localized
app-owned labels. Incompatible model effort resets visibly to that default; busy setters refuse changes.
The existing canCancel/state/connectionLabel properties include the VM's accepted pending browser sign-in.
Stop uses existing native sign-out/teardown to retire that attempt and its late callbacks; no token getter,
new provider endpoint or alternate dependency route is introduced. This source unit does not establish
full S6 pre-growth/retaining-role closure, cost compliance, imports/refinement/Claude/browser completeness,
actual subscription access, official SDK/task CI or readiness; no follow-up timer follows it.

The connection consent dialog presents a readable summary of the exact current project, parameter/free
counts and diagnostic count. Optional technical details retain the unchanged complete outgoing context.
Sign in with ChatGPT and Approve context name the existing actions explicitly; untrusted project text
remains PlainText. A typed local path is text, not file access: the chooser/drop handle/import unit remains
unimplemented, so no decorative attachment control claims that capability. These QML changes need actual
production visual/interaction verification; source syntax checks are not that evidence.

The consent action label follows the current connected role while open as well as on opening. The
local dialog bounds its width and complete disclosure viewport to the overlay, preserving the themed
header and ordinary standard-button footer outside the scrolling content. Summary and exact technical
context are retained in full and literal text; scrolling changes presentation only. Actual narrow/short,
long-project-name, technical-details and mid-dialog connection-transition exercises remain required.


## Device eligibility and assistant entry

ApplicationInfo captures one bounded browser-device decision during construction, before its CONSTANT
assistantAvailable/assistantUnavailableReason properties are observed by QML. Native desktop stays
eligible without navigator inspection. Eligibility means the computer can open assistant setup, not
that a browser provider connector or subscription is working. Existing connected/catalog/context
consent/currentness and scientific permissions remain authoritative.

The existing Emscripten browser bridge reads only bounded userAgent/platform, maxTouchPoints and optional
userAgentData mobile/platform. Each string is admitted at4096 UTF-16 code units inside JavaScript before
any conversion; no token, network/high-entropy request or persisted fingerprint is involved. Missing,
throwing, malformed, oversized, mobile or contradictory facts refuse. Explicit mobile evidence wins.
Recognized Windows/Linux/ChromeOS computers remain eligible regardless of touch or width. ChromeOS UA
and Linux legacy platform are compatible; Chrome OS/Chromium OS branding is normalized. Macintosh without
an explicit consistent desktop hint requires a supplied0/1 touch fact; high-touch/unknown Macs refuse,
including iPadOS desktop-style identification. This is conservative UI availability, not a security grant.

The toolbar remains visible but disabled with an accessible reason. Its handler, popup visibility and
focus helper consume that same immutable decision. Preferences show only a wrapped literal explanation;
no hover or alternate opening control is required. Enforcing availability never overwrites saved shown/width/side preferences. Thus a
restored true default cannot show a phone panel or reserve chart margins, while eligible computers retain
their prior choice. Narrowness is presentation, not a reason to disable a recognized computer.

The two browser VM messages state only that AI connection is unavailable in this build. No local runtime,
provider authorization, responsive redesign, B/Q lifecycle repair, live chat or device/CI readiness follows.
The reviewed connection dialog and current manual/scientific UI are unchanged. Actual native/browser
entry and accessible-explanation gates plus rendered behavior remain required.


## Shared existing-sidebar composition

Main owns the sole AssistantPanel outside page Loaders and changes only its visual parent. WorkflowPage
exposes the actual existing sidebar container through the readonly QML assistantOverlayHost reference.
Its manual SideBar remains instantiated but hidden/disabled while covered; the host stays enabled for the
assistant sibling and keeps its normal fixed geometry. No pinned base component is edited. Actual objects
carry unique workflow.<page>.sidebarHost/mainContent/manualSidebar names; Home's actual page and fallback
host use workflow.home.mainContent/sidebarHost. The fallback uses the same preferred side and normal
sidebar width between app/status bars, without navigation/project creation or main margins.

A local opaque pointer/wheel shield prevents background pass-through; Home keyboard focus behind the
covered strip returns to the composer without disabling the entire main page. The app-bar control and
close remain reachable while busy. Focus restoration checks actual visibility/enabled lifetime, and
reparenting restores an existing chat focus target instead of rebuilding content. Preferences dialogs
retain their focus until closed. No hide/show path invokes cancellation, Clear or provider actions.

Transcript following is local to the existing ListView. Actual newly admitted user rows resume tail
following; streamed/coalesced text follows only while that mode remains active. Reading older content
turns following off; explicit return to the end resumes it. Hide/reparent retains the same ListView,
composer, selections, draft and actual VM/history rather than forcing the end. Populated actual scrolling,
focus/input isolation, both sides and Home/workflow geometry need independent runtime gates and actual
running-app captures. No generated mockup is visual authority or a claim of provider/scientific success.


## App-bar-only nonmodal Popup clarification

Owner99d50f selects one Qt Quick Controls Popup with NoAutoClose, Popup.Item, no modal surface/dimming,
zero content padding and the actual sidebar host size. Its Item content retains assistant.panel identity;
the wrapper is assistant.popup. Normal existing edi palette/widgets remain unchanged. Outside interaction
and Escape do not close it. The app-bar button alone toggles requested visibility, including its normal
keyboard activation; remove the old shortcut, separate close and Preferences checkbox. Preferences retain
a readonly eligibility explanation. Session visibility starts false and is no longer aliased to the old
persisted shown key; reset of unrelated preferences does not open or close chat. Dormant stored width and
unrelated settings are preserved. No separate native OS window or new segmented selector is introduced.

The Popup and content remain Main-owned outside page Loaders; the actual host is its positioning parent.
Manual subtrees remain instantiated/hidden/disabled siblings, not disabled hosts. Popup closure restores
an actual valid focus target or app-bar opener; Qt's automatic dismissal never becomes a cancellation.
Draft/history/scientific state remain independent of visibility. Home is reachable without project creation.
Actual desktop geometry/input/keyboard/scroll/busy/device exercises and captures remain owed; compiling
or constructing a Popup alone does not establish ready chat, live provider access, CI or SDK qualification.


## Observed Classic ChatGPT interior, edi controls

The visual comparison uses actual official Classic macOS reference captures, not generated mockups or a
claim about the newest unified app. A rounded existing-theme composer contains the actual model/effort
choices and Send/Stop toolbar; the existing connection control stays honest about the disconnected state.
Unimplemented attachment actions are absent. Existing submit acknowledgement, model/effort/default/busy,
cancellation and literal/selectable text paths are retained. User text has a restrained right-aligned
bubble; public assistant text is plain, without a copied logo or invented rich-content capability.

Comparison A is the committed pre-interior layout; B is compact; C temporarily increases writing space
using an explicit local QML patch. Normal native dependency rebuilds and actual-window captures identify
every source/artifact/draft state, then restore only the owned variant patch. No runtime option framework,
mock VM, fabricated conversation or live provider/scientific success is part of this visual comparison.


## Popup keyboard, focus ownership and retained text selection

Standard KeyNavigation edges connect the existing popup controls to the sole existing app-bar toggle;
no key gesture hides the popup directly. Composer/editor traversal exits even when intervening controls
are disabled. Retained workflow pages are input-disabled while noncurrent, without destroying their
loaders or manual state. Rehost and close focus restoration validates the current page, actual sidebar
host, project and popup epoch; a synchronous safe opener focus precedes Qt's own popup exit restoration.
Home focus eligibility observes complete target/ancestor/strip geometry: wholly covered controls yield
focus to chat, while partially exposed controls retain their outside usability under the local pointer
shield. The page is never disabled globally. Draft/message/details text retains selection; deliberate
composer focus restores a still-current selection, without reinstating selection across changed text.
Actual keyboard, geometry and selection gates must exercise these mechanics; source does not establish
macOS, populated-history or busy-path qualification by itself.


Normal transcript bodies expose localized You/Assistant/Activity identity with their accessible static
text name, retaining the selected unboxed/bubble appearance. The compact effort's full explanation
uses an actual existing styled ToolTip on hover or keyboard focus, respecting the shared tooltip
preference; setting attached text alone is not considered visible explanation delivery.


## Owner-selected short composer and shared selector surface

The owner's actual reference photograph selects the lower-toolbar arrangement with a short initial
entry, growing with actual text to the existing finite scroll limit. Model and effort selectors measure
their real display content and share the rounded composer surface rather than separate filled boxes;
normal keyboard focus retains its visible border, tooltip and accessible name. Send/Stop stays at the
right. The actual selected manual-sidebar host is unchanged, and Right/light before/open/after captures
must compare that same rectangle and scientific workspace. File selection is a separate functional
boundary: no enabled decorative plus button or implied upload is added by this presentation change.


## Sidebar header and confined slide lifecycle

The Assistant label uses the actual manual tab-bar height and left inset. Its existing connection
button is a compact Sign in/account label beside Clear, opening the same consent/connection dialog;
the full actual account remains accessible while the visual label elides. Actual sign-out and
connecting/error behavior remain, without a separate full-width connection row or persistent
introductory paragraph. No file picker capability is implied by this presentation unit.

One persistent sheet slides within a fixed, clipped sidebar-sized Popup viewport using the shared
translation duration/easing. Neither the host nor scientific main geometry moves. A fixed local input
shield covers the strip throughout enter/exit; retained manual controls remain hidden and disabled
until the Popup is actually closed. Closing moves focus to the existing app-bar toggle immediately;
only actual close restores a still-current page/host/project/epoch target. A closing sheet does not
receive deferred composer focus, and rapid reversals keep the same conversation and selection tree.
Actual intermediate-frame confinement and interrupted transitions require runtime observation; these
source mechanics alone do not establish device, accessibility, provider or full-task readiness.


## Header navigation after compact connection placement

The app-bar Tab entry now starts with the actual Sign in/account button, followed by conditional
visible/enabled Sign out and then Clear. Explicit reverse edges include the same header actions; the
existing later children/composer/sole app-bar toggle routes remain. Moving the controls does not make
keyboard reachability implicit. The bundled Font Awesome robot replaces the old chat-bubbles glyph
on that same app-bar control, without changing its accessible name, identity, device gate or action.

This corrects review46 HDR1; the independent baseline proved a forward Sign in omission while its
reverse case already passed. Existing source63 motion and host ownership remain unchanged. Actual
connected/connecting and platform/focus cases still need their own reached runtime evidence.


## First real desktop selected-file intake

The actual lower-left plus begins the VM's one-shot initiating capability before opening the existing
native FileDialog. Accept/reject and file-drop carry that exact original capability; no completion
mints authority. Clear/rebind, manual revision, Stop, account/connection retirement and teardown fence
pending intake before receiver cleanup. Disconnected/Home selection is permitted without provider I/O.

Native reads use actual regular-file handles, admit declared count/file/aggregate bounds before vector
growth, read bounded chunks and refuse changed/incomplete reads atomically. Only the Controller owns
admitted bytes. The VM retains bounded descriptors, publishes actual rows/removal and clears prior
scope consent. A successful core admission remains acknowledged if row delivery later fails: its exact
descriptor is retained and sending is blocked while presentation recovers, rather than silently treating
admitted files as a preflight refusal. No selected bytes enter saved project/history implicitly.

Disclosure names the actual selected files and permits bounded read_selected_file outcomes under the
same request/account/project/collection/currentness and complete history limits. No provider upload,
path permission, converter, project creation or fit is implied. Browser action/drop stays disabled until
its shared bounded WebFiles pipeline and genuine File transfer are implemented and independently
qualified. Both computer-browser and scientific import/skills scope remain owed; desktop method tests
alone do not prove a genuine OS chooser gesture, Windows/Mac or a live subscription tool turn.


## Explicit effort, remembered choices and sidebar scroll indicators

Owner94ffecaa5 makes the compact effort selector explicit and reuses the FIRST manual-sidebar indicator: pinned EasyApplication SideBarColumn attaches EaElements.ScrollBar with AsNeeded and interactive false. Chat, draft/file overflow, plan and disclosure retain their existing complete contents, reading/tail logic and selection; only the actual shared indicator/settings replace the bare defaults.

The VM uses the existing configured settings_file_path()/QSettings Ini store and store_settings_now() browser flush, matching ProjectViewModel's application preference boundary. No configured path means no storage access or personal/default fallback. One QStringList model/effort pair at Assistant/Providers/chatgpt/selection binds the last actual user choice to this provider, independent of opaque connection/account IDs; another provider needs its own explicit adapter identity. Restore only from a current available catalog and while no operation is active. Sign-out, transient empty catalogs, Clear/project rebind and automatic unavailable-value/default fallbacks never overwrite the saved user pair. Missing/unavailable choices remain truthful and may be restored once supported; explicit user selection replaces the pair. A local sync failure reports that the current choice was not saved, without inferring provider success or sending a request. This extends existing setters rather than adding a public settings service/API.

Original SAMPLE messages for visual inspection are fixtures in an isolated task-owned history.json, rendered by the actual history/AssistantMessage route. They are visibly marked SAMPLE and do not represent an account/provider/scientific outcome. Usage metrics and user-message arrows from owner221a76dac are a separate unfinished private continuation; this candidate does not pretend to supply them.


### Preference read recovery, local navigation and honest usage

PREF1 private review71 identifies a failed load cached as completed. The load boundary now binds/clears old-store association before preparation, checks sync/contains/value status before absence or acceptance, and marks completion only after a successful validated read or confirmed absence/rejection. Access/preparation failures remain retryable on the same path; saved user choice is not replaced by the automatic catalog fallback. This is a correction within the existing configured store, not a new API or permanent-memory guarantee.

Owner221/a8d/e41 add previous/next actual-user-message chevrons above the composer, with actual row IDs/kinds/order and ListView boundary positioning, disabled ends, preserved selection/draft and explicit reading cursor. The larger blue straight-arrow Send and same-place white-square Stop retain existing admission/busy/cancel logic; follow-up steering while busy remains unimplemented pending its real provider lifecycle contract. Owner6f02 makes the same Clear action a compact header text button with its existing full accessible meaning. Usage is a neutral unavailable ring/details dialog until a separately reviewed real account-bound metric exists; no percent, elapsed fill, token estimate or provider request is fabricated.

The native URL DropArea moves from the nested composer to ONE visible/current chat-body boundary including messages and composer. It captures the original accepted VM capability before reading/admitting the dropped URLs. Ordinary text drops remain with existing text editors; hidden/exiting/device-ineligible/browser chat admits nothing. No native directory/browser-transfer/import permission or new public interface is introduced.


### Preference-owned diagnostic recovery and resting navigation circles

PREF2 separates the existing local preference/selection diagnostic from unrelated operation/provider/scientific/storage errors inside the VM. The existing lastError property presents an operation error first, then the local preference diagnostic; no new public error service/API or string-equality ownership guess is introduced. Confirmed read/absence recovery, restored supported saved choices and successful explicit saves (including same-value retries) retire only their owned diagnostic. A valid explicit choice replaces an invalid/unavailable selection warning; failed read/save remains visible as appropriate. A restored in-memory choice does not pretend a still-failed store read recovered. Native/provider/fit failures remain untouched. This extends existing configured-store/notify/getter paths.

The two small neutral navigation buttons retain visible circular backings at rest using the existing content-background/hover/focus colours and ToolButton dimensions. Icons, IDs, actual user-boundary logic, disabled ends, selection/tail behavior and the larger primary composer action remain unchanged. No selector background, widget fork, new action or additional opener is added.


### Owner-revised composer hierarchy

Ownerbef37ebaa replaces the blue primary with theme-bound black/white Send/Stop and contrasting icons. Disabled admission stays disabled and visibly subdued. The smaller normal secondary user-boundary buttons now follow the primary inside the same composer toolbar; the existing ListView owns navigation and passes only internal QML availability/signals. Compact flat selectors share the remaining toolbar width. A conversation/composer divider, spaced existing header actions and smaller usage glyph preserve the actual sidebar geometry and hit target. No new provider capability or C++ interface is introduced.

Ownerd03c7aff4 uses Effort as the disconnected/undiscovered placeholder, then the genuine current catalog choice (Low, High, etc.). The canonical empty choice reads Auto and explains that the provider chooses; no inferred level, settings/wire mutation or guessed connected state is introduced.


### Cause-specific preference persistence recovery

PREF3 keeps an unsuccessful explicit write separate from read/selection diagnostics inside the existing VM. Reading an older pair, confirmed absence or restoring an available in-memory choice cannot acknowledge that a newer explicit choice was persisted. Only a successful explicit write through the existing sync/flush path, or retirement of that configured store's ownership, clears its save cause. Same-value retries and pre-staging/sync/flush exceptions use that same boundary. Existing unrelated operation errors retain priority; no public error/settings interface is added.


### Final owner composer order and uniform actions

Ownerda4acf953 supersedes the preceding primary/navigation arrangement: plus, flat selectors, Previous/Next, then rightmost Send/Stop. All composer actions derive their circular size from the actual plus control; wider current-style gaps and remaining selector width preserve a compact toolbar. Owner0c5b2b16e subsequently clarifies Send state: enabled remains black in light mode/white in dark mode with a contrasting icon; disabled Send uses the existing themeBackgroundDisabled gray. Actual admission state and subdued disabled icon remain honest. Stop keeps its contrasting active cancellation treatment. Keyboard links follow the same actual order, skip disabled ends and return to the sole appbar toggle. The usage inner ring is modestly larger than the immediately preceding version while its full hit target remains unchanged. No provider, admission, cancellation, settings or public API changes.

### Explicit workflow guidance

The VM's read-only skills rows and selectedSkill are derived from the current core catalog/context. The idle selectSkill wrapper uses the existing trusted command boundary and invalidates context consent. A compact workflow link above the transcript opens the existing AppDialog with exact bundled PlainText content, version and prerequisite status; no hidden filename inference or additional execution door is added. The connection disclosure names the selected workflow and included structure/dataset/relation metadata before approval. Resource/row/context wrappers retain existing caps.

Ownerb9df68548 refines disabled Send to the exact existing navigation ToolButton backgroundColor()/foregroundColor() behavior, with ordinary opacity instead of an additional primary fade. Enabled primary contrast and all real admission/cancellation semantics remain unchanged.


### Desktop trial: actual Send approval and sidebar theme integration

Owner12c7da698 and59882d61b extend the existing native desktop path. Idle Send or Enter with changed context opens the SAME outgoing-context dialog, retains the exact draft and captures the disclosed context. Only genuine approval followed by current connected/unchanged-context/model/effort/draft checks can resume that explicit submit once; cancellation, hidden panel or changed owner/selection/context retires that intent. The VM remains the final consent/admission fence; neither opening the dialog nor sign-in alone fabricates a sent user row. This does not yet implement busy follow-up admission.

Home closes the actual sliding sheet and disables its existing robot opener, preserving requested visibility for return to a workflow. Current workflow manual controls remain rendered at their real theme colours beneath the sheet instead of fading through a visibility animation. The local pointer/wheel shield and current-strip geometry/focus guard still exclude covered input through actual exit; retained offscreen pages keep their existing disabled ownership. A safe current app tab receives fallback focus when the robot is unavailable. The scientific main view does not move.

The sheet uses one main-facing vertical boundary rather than doubled outer top/bottom borders. Text selection uses the FIRST EasyApplication field's themeAccent/themeBackground colours across draft, response, details and workflow content. Model/effort popup widths measure the actual offered labels and fit the window, leaving compact flat closed selectors; keyboard focus uses the existing neutral appBarComboBoxBorder instead of a custom red highlight. The unavailable usage ring is 1.5 times its preceding visible glyph, with the same actual hit target and no invented metrics.

DT1 observes that equal context is not equal conversation ownership. The app-local conversationRetired signal fires at the start of the existing VM bind boundary (including public Clear/same-null rebind), before fallible preparation. The panel retires deferred submit immediately; only a fresh explicit submit may follow replacement. Ordinary same-context approval notifications are still valid and do not trigger this signal. No conversation token/getter or provider/core interface is added.


### Passive Markdown presentation of assistant prose

Owner0c48dbab5 extends the existing reply TextEdit, not canonical history. An app-only AssistantMarkdown helper installs a Qt QTextDocument on that same editor and invokes the built-in Markdown parser with MarkdownNoHTML. User/error/activity text uses setPlainText. Original row.text, history/request bytes and accessible role identity remain unchanged; selection/scroll use the existing control and EasyApplication colours. No HTML serialization, regex sanitizer or second Markdown parser is added.

The document overrides loadResource without calling base and returns a valid empty resource, preventing both Qt's default local/data/parent loader and resource-provider fallback. Parsed image objects become literal alternative text, so no automatic media fetch occurs. Links have no opening action. The document is owned by the actual QQuickTextDocument editor wrapper, matching Qt6.11 caller-ownership semantics through delegate/helper lifetime. This is passive rendering only, with ordinary resource/selection/large-content/device runtime qualification still required.


### Final compact desktop presentation

Owner8746ea392 keeps the current compact composer and equal circular actions while increasing its inner text/toolbar inset slightly. The history divider spans the actual sidebar width. Previous/Next highlights only the real user row identified by the existing jumpedUserId cursor; ordinary scrolling and a new user admission clear that cursor through the existing list behavior. Supported platforms no longer repeat the appbar-button instruction in Preferences; unsupported-device explanation remains visible. No conversation, consent or provider authority changes.


### Generic official-runtime native prototype

The default native AssistantViewModel now uses the app-internal CodexAgent QProcess/JSONL transport. The existing injected NativeDependencies constructor remains a diagnostic compatibility door for the restricted adapter, with no automatic production fallback. WASM remains explicitly unavailable. The runtime owns its normal managed account/profile; Edi never reads/copies auth/config or assigns HOME/CODEX_HOME. Actual initialization/account/model/skill/thread readbacks precede input. Effective cwd, workspace-write sandbox, no network, excluded temporary roots, approval policy/reviewer and OpenAI provider must match admission; broader command/file approvals are declined visibly. Inherited runtime extensions are not claimed confined by the shell boundary.

Selected inputs are retained as immutable app-owned snapshots, then copied beside an optional saved project into a unique workspace. Clear/replacement/manual edits revoke process and pending scope before cleanup. Owned working copies remain recoverable but no scientific result is adopted into the open project. All bundled skills and companion references are resources materialized in `.agents/skills`; actual enabled discovery is verified. The optional catalogue inspects complete content, not exclusive workflow routing. New valid packaged skill files need no per-skill C++ or QML registration.

Original runtime request/thread/turn/item IDs govern replies, questions, steering and Stop. Busy input uses turn/steer without model/effort overrides. Admission is persisted before physical write, acknowledgement never means completed work, and uncertain input is retained rather than blindly replayed. Runtime command/file originals are bounded and displayed as activity; only a genuine matching terminal settles assistant output. One-shot server requests retain literal IDs and unknown requests receive explicit errors. Exact public Limits bound JSONL assembly/depth/wire/events, pending requests, items, archives and deadlines. Overflow/process loss fences continuation before bounded diagnostics; no allocator or external process memory guarantee is implied.

The existing app-with-crysta command builds bindings through the compatible default environment into build/app-python against the same local prefix, and exports the actual extension directory/app Python to runtime children. The app Qt graph keeps bindings off. This reuses the current Python/CLI surface rather than adding workflow chatbot tools; scientific recipes, engine results, accepted-best restoration and safe current-owner publication still require their actual separate qualification.


### Generic prototype authority and operation-role recovery

Nonadmitted input failures (text/preparation/record/pending/write-queue capacity or a not-yet-known turn ID) preserve the active request and draft. Admission is persisted before a physical input write; only admitted uncertain delivery or an actual active transport/output failure fences the process. Account replacement/expiry/logout revokes the ready predicate and all question/acknowledgement authority synchronously, with pending rows interrupted before reconnect. A reconnect always stages a new current snapshot; modified old workspaces remain separate recovery artifacts.

Steer acknowledgements must supply the actual expected turn ID. Events use their method's actual required thread/turn/item binding. Final item type/original lifecycle is immutable, deltas cannot extend finalized text, and enclosing turn completion cannot fabricate an unfinished tool's final outcome. Questions use an opaque frontend intent ID bound to the original runtime question/request/thread/turn/item and consume once. Unknown/duplicate/stale notifications are not progress. Wire/event roles reset only for a new operation after genuine settlement; raw paginated catalogue results are bounded before normalization. Auto effort sends the model catalogue's actual supported default explicitly each new turn, resetting a sticky previous override without guessing null semantics. Busy steer carries no selection override.

The existing local-prefix core producer honors positive CMAKE_BUILD_PARALLEL_LEVEL (bounded fallback), and the owner's developer command ensures its declared compatible default environment through the normal frozen setup. Development qualification uses only existing environments and the owned SDK, never a global runtime install or provider/profile action.


### Bundled official runtime, owner53138596a

A native app configure acquires the complete pinned0.162.1 dedicated app-server package for the declared Linux x86_64/macOS arm64 targets. Public release SHA256, exact layout/version/target/variant, required regular executable members and preserved modes are checked before staging. The source and installed app retain the complete resource layout and matching licence/notice material. Normal build and install verify every staged member hash before exposing it. Missing/corrupt packages fail acquisition/build/install, without silently falling back to PATH or global installers. Other platform packages require their own pinned/qualified target entry before a native build can succeed.

The dedicated entrypoint receives --listen directly, not the full CLI's app-server subcommand. Build-tree and relocated-install resolution are explicit and deterministic. EDI_CODEX_DEVELOPMENT_EXECUTABLE is an explicit offline/developer composition: an absolute existing executable implementing that same dedicated protocol entrypoint, with invalid overrides refused and no fallback. Ordinary users set nothing. The optional bundled zsh-fork feature is disabled with the supported per-launch feature override so inherited opt-in cannot select its higher-minimum helper on older supported macOS. Upstream executables/signatures/entitlements remain intact; no profile, HOME/CODEX_HOME or credential-store redirection occurs. Actual Mac outer-distribution signing and user-managed login remain separate witnesses.


### Generic final-item and progress siblings

A successful enclosing turn never completes retained partial assistant text or tool activity. Genuine item/completed originals or matching successful final snapshots supply final evidence. Status-bearing command/file/MCP/dynamic/collaborative items validate their actual supported final statuses; interrupted/failed snapshots retain unfinished activity and actual enclosing failure without inventing completion. Final originals cannot be changed by a later snapshot. User-input and private-reasoning rows remain distinct from public completed outcomes.

Idle tracking admits method-specific current command output, plan deltas/changed plan snapshots, reasoning deltas/new summary parts and a newly presented current question. It does not display private reasoning, refresh for unknown/unchanged metadata or treat identical append-delta bytes as a duplicated snapshot. Retained progress metadata shares the existing stream capacity. Repeated Stop/logout are idempotent while pending; deadline changes preserve the earliest owned total/revoke deadline rather than extending it. No public cap, API, new agent loop or automatic scientific adoption is introduced.


### Immutable runtime publication and staging-to-install predicates

A complete digest-verified official package plus the owned legal-resource bytes determines a new immutable publication directory. Configure never deletes or overwrites a published identity: an unchanged valid tree is reused; a damaged existing identity refuses; a new complete staging tree is renamed only into an absent identity. Prior generated checks and running consumers therefore keep their original resource paths across configure, failure, interruption and a later legal-resource revision. The acquisition lock still excludes writers; readers need no new lifecycle service.

Configure, normal-build and install verification all require every retained member to remain a regular nonlink file with its expected bytes. Server, code-mode host, rg, packaged zsh and Linux bwrap must additionally remain executable at each boundary. Metadata/legal resources have no executable requirement. Signed upstream bytes and mode-preserving installation remain unchanged; this is not a Mac signing, live-login or full distribution qualification.

Generated verifier scripts also carry the immutable publication identity and are reused without rewrite. New app headers are configured only after the candidate tree is published and checked; old generated readers never point into unpublished staging.


### Remaining progress, human-retirement and deadline siblings

The pinned item/mcpToolCall/progress notification renews idle only for a bound current unfinished MCP original and a nonempty message within the existing encoded message bound. The transport already charges wire/event/record capacity; Edi does not retain or publish another progress-text copy. Unknown/stale traffic and empty messages remain inert.

Stop revokes human completion synchronously as it begins bounded interrupt settlement: retire the visible/queued question identity, fence public answer callbacks and reject new server human-completion requests while revoke is pending. Terminal/error/request-resolution traffic remains admitted at its existing owner. No invented question result is sent, and repeated Stop/logout do not extend the deadline.

Operation transitions recheck inclusive total/idle expiry and monotonic order at the actual new-role clock sample. A finite exhausted budget fails before subtraction/assignment; it never becomes the zero value reserved for an absent deadline. This applies to control/inference/revoke transitions without a new clock API or timeout increase.


### Stable full-context data input and exact request nonadmission

Pinned0.162.1 rejects additionalContext without experimentalApi; enabling it would promote application fragments to developer role and independently middle-truncate both fragment kinds at1000 tokens. Edi therefore uses the existing stable UserInput::Text array: first the exact user draft, then a separately marked EDI_APPROVED_CONTEXT_DATA_V1 text containing the complete approved context. Fixed app-owned developer instructions identify that second input as project/file DATA. No experimental context field/opt-in, untrusted-content developer role, silent truncation or advertised capacity reduction remains. Both new turns and admitted steers use current approved context. Existing complete request/context/retained-item/history bounds still apply; clientUserMessageId maps only to the exact public draft row, and provider user-item echoes do not replace or duplicate it.

A well-formed owned RPC error retains actual method and bounded integer code with an app-owned known cause; opaque message/data/stderr, echoed inputs, credentials, paths and reasoning are never displayed. Only -32600 together with exact pinned pre-dispatch context-gate or NotSubmitted steer reasons, including the original expected-turn mismatch shape, proves nonadmission. It settles only that retained input/maps; an idle start settles its operation while a refused steer preserves the original active turn, Stop and deadline. No automatic replay or invented turn occurs. Numeric categories alone, unknown/internal/auth/handshake errors, stale bindings, EOF, uncertain acknowledgement and history retention failure preserve the existing authority fence and do not assert that credentials were lost.

One full-width assistant bottom separator uses existing app-border theme color/thickness inside the clipped sidebar strip, preserving main/status-bar geometry and appbar-only visibility.


### Pending steer refusal after the original terminal

Each existing pending steer correlation retains its original thread/expected-turn pair plus one local terminal-retained bit. The bit is set only after that exact thread/turn's completed, interrupted or failed original terminal has passed full validation and durable outcome publication. It does not claim that the pending follow-up executed. The bounded pending-RPC map owns this evidence; account/project/Clear/reconnect failure and retirement clear it with the existing request maps.

An exact previously qualified pre-admission steer refusal can therefore settle only its own retained follow-up even after the original active turn was cleared. It still requires the literal owned response ID, original expected turn, current authenticated thread, actual pending row and nonretiring/nonrevoking authority. A subsequent same-owner turn does not erase the old pending receipt or get cancelled by its refusal. Unknown errors, absent/foreign correlation, changed thread/owner, Stop/account retirement, malformed terminal, failed outcome retention and uncertain delivery preserve the existing fences. No busy check is globally removed, no numeric category alone grants recovery, and no automatic replay/new turn or result is invented.


### Compact literal command activity (owner live trial)

Only activity rows whose retained original is `commandExecution` use a compact,
checkable existing EasyApplication Button. The caption reports Running/Ran plus
actual status and available numeric exit code; it does not infer a semantic file
operation or scientific success from shell text. Real refusals without that
original type keep their complete human explanation. User/error text stays
literal and assistant prose retains passive Markdown.

Expansion exposes complete admitted command, cwd and available aggregated output
as separate labelled, selectable PlainText fields. Empty and unavailable output
are distinct. A bounded scrolling viewport wraps long content; bytes are not
truncated, independently summarized or accumulated. Technical JSON is secondary
and formatted only while its own disclosure is open. Canonical VM text/payload,
IDs/status, history/retention budgets and all execution/approval semantics stay
unchanged. Disclosure grants no authority and never runs/retries a command.

The Panel passes the actual public row ID. ID changes and ListView pooled/reused
signals reset expansion, literal selection and detail scrolling so a recycled
row cannot inherit another activity's disclosure. Actual disclosure press stops
outer tail following before the height changes; no forced tail reposition is
performed while a reader inspects details. Existing draft/selection/theme/main
geometry remain unchanged. Actual narrow/light/dark/reuse/keyboard and tail
qualification is still required; this source unit does not establish a saved
artifact handoff, fit/conversion result or full scientific completion.


ACT1 lifecycle fidelity: the compact caption reads BOTH the retained original
item and the normalized public row status. An unfinished original is called
Running only while its public activity is also in_progress. Interrupted/failed,
refused or completed enclosing activity with no matching settled command outcome
is explicitly unconfirmed; it never acquires an invented exit/completion from
that host lifecycle. A genuinely matching settled original/public status retains
its actual command status and available exit code. All original fields remain
available unchanged in disclosure. This same presentation rule covers Stop,
transport/deadline retirement, sign-out/workspace retirement and archived reload;
no event emitter or protocol authority is changed.


## Compact controls and readable activity

Keep the existing popup, manual workspace geometry and sole appbar opener. Secondary composer actions use three quarters of the prior actual tool-button size; plus/navigation are transparent with ordinary visible theme focus, while Send/Stop retain their distinct primary colors and actual enabled semantics. Skills moves to the existing header. Model/effort popups map their anchors into the assistant viewport, bound both dimensions there and wrap item labels. Close choices on hide, side or width changes. Top/bottom strokes overlay the existing appbar/statusbar separator coordinates; never add a neighbouring stroke.

Retained typed activity is muted and expandable. Command categories come only from agreeing supported commandActions, never shell text. Public normalized retirement remains authoritative when an original command is still inProgress: show an unconfirmed command outcome and the actual enclosing interruption/failure, not a fake command exit. Real exit/status/output and immutable payload remain inside literal details. Other recognized event kinds follow the same compact disclosure; unrecognized refusals and questions remain visible. Delegate reuse collapses disclosure; expansion retains the existing reader/tail rules.

A subtle working cue requires actual agent_active, a shown panel and no pending question/plan; canCancel alone is not execution evidence. The existing shared translation duration controls its animation. No new motion preference or numerical progress is invented. Passive Markdown keeps Qt MarkdownNoHTML and the no-resource document; only presentation margins, indentation, wrap behavior and theme anchor color change. No source text, hidden break characters, automatic URL opening or fetch is introduced. Long code/path/table rendering and popup confinement require actual Qt witnesses before a visual claim.


## Native created-result handoff and fresh Save As

Prior art: `Session::open/replaceProject/saveAs`, the managed Codex facade's stable text inputs/owned RPC and retained-turn settlement, and the existing native `FolderDialog`. The first result unit does not add an agent tool or a shell grant. Each eligible empty-Session input discloses app-owned `EDI_RESULT_HANDOFF_V1` nonce/receipt metadata in a separate ordinary text input; exact user draft and approved context data remain separate and unchanged. A receipt only qualifies after the matching acknowledged input, successful complete durable turn settlement, no pending input/question/revoke, and unchanged owner/generation/thread/turn. Stop, Clear, logout/account change, protocol/retention failure and arbitrary rebind revoke it. A refused follow-up retires only its own receipt intent; it cannot invalidate or promote another input.

The host captures the exact bounded fixed-layout native files with descriptor-relative no-follow reads, byte counts and SHA256, complete represented-entry/alias closure, and original source identity rechecks. The copied lease is outside the runtime's writable working copy. The real core loader and declared-mode check precede ProjectViewModel construction. Unsupported external scan/report dependencies refuse. Only the same still-empty Session is automatically replaced; existing-project/save-back/dirty merge is deferred. Captured files outlive the displayed reader. This is saved-project validation, not scientific convergence or conversion proof.

A controlled settled rebind preserves the actual managed runtime/account/model catalogue, draft and archived conversation while retiring the old workspace/thread/call/question/context authority. A later request requires ordinary fresh context approval and an independently staged/validated new thread; no credentials are copied or sign-in fabricated. Normal rebind and retirement retain their existing fail-closed behavior. During fresh thread preparation, a draft remains in the composer; no unacknowledged request is invented or replayed.

Adopted results require fresh Save As. The existing native parent picker is followed by an existing-style leaf-name dialog. `beginSaveAs`, `completeSaveAs`, and `cancelSaveAs` serve those real asynchronous controls with one initiating project/QPointer, owner epoch, WorkStamps, lease and one-shot token. The ordinary native Save As picker receives the same initiating-owner protection. Browser behavior is unchanged and this host publisher is unavailable there.

First export copies the exact already bounded, hash-sealed native artifact; it does not invoke `project_edi_files` or an unbounded ScratchSave and call it pre-growth validation. The real loader must leave scientific inputs unchanged during host cache construction. Save As refuses any intervening model edit/WorkStamps change: export this first created result before editing it. Edited-result export needs an actual bounded writer seam and remains deferred. After a successful fresh export, ordinary manual project Save retains its established behavior.

The host copies those exact bytes descriptor-relatively into a staging folder inside the pinned chosen parent, verifies/reopens the independent local copy through its retained descriptor, then rechecks current owner and destination identities. Linux uses `renameat2(RENAME_NOREPLACE)`; macOS uses `renameatx_np(RENAME_EXCL)`, with no overwrite/copy/delete fallback. Case aliases, existing destinations and unsupported publication refuse. The disk-commit latch and preallocated exported receipt are retained before fallible model loading/rebind. A late failure reports the actual exported-but-not-opened path and never deletes the committed result. Failed staging and host snapshots may remain as bounded recovery cache: cleanup never recursively deletes a mutable pathname that could have been substituted. Existing-target rollback, edited-result export, crash durability and actual macOS runtime/export qualification are not claimed.

The core-private `load_assistant_project` shares the actual loader/parser, requires embedded observations before `_data_range` axis generation, and refuses external scan/report declarations before outside materialization. The public `load_project` behavior is unchanged. Receipt admission reuses the existing assistant bounded UTF-8/depth/unique JSON wrapper; it does not assume the report JSON reader imposes assistant bounds.


### First-result loader and two-picker namespace checks

The copied result is a host-owned directory outside the runtime's writable root. All four loader entrances (capture, Session adoption, destination-local validation and postcommit reopen) use one checked real-loader door: hash closure and named-directory/retained-descriptor identity before/after loading. Linux reads through /proc/self/fd; macOS uses the actual physical immutable-copy pathname because /dev/fd does not support appended child lookup. This preserves the no-follow admission and real core grammar, not a second parser. It is not an absolute jail against an arbitrary same-user process changing host-private objects during a synchronous load; the runtime is never granted this path for writes, and namespace changes observed around the loader refuse.

Publication prepares syscall byte arguments, hashes and checks initiating currentness, then immediately reopens/rechecks both the actual selected parent and named stage before the common Linux/Mac non-overwrite rename branches. The pinned source alone cannot authorize a substituted name. The remaining instruction-level same-user namespace race is not claimed inode-conditionally atomic; no overwrite/delete/copy fallback or mutable-path cleanup is added. A selected-parent change observed before publication refuses instead of claiming the stale recovery pathname as successful.

The first native picker callback calls the Session's real saveAsCurrent(token) action before reading the initiating project's suggested name or opening the leaf dialog. That action and final completeSaveAs share the same SaveIntent owner/epoch/project/work-stamp/lease/readiness predicate. Repeated, Clear/account-retired, manually replaced or edited owners cannot open the stale second form. Cancellation and the final one-shot consumption remain intact.


### Disabled primary action and boundary-first reply wrapping

Disabled Send retains the existing themeBackgroundDisabled circular backing, with its actual disabled foreground/admission unchanged. Plus and user-message navigation remain transparent secondary actions; enabled Send/Stop keep the existing monochrome primary palette. Reply bodies use Qt TextEdit.Wrap (WrapAtWordBoundaryOrAnywhere), preserving word boundaries before falling back for unbroken paths/URLs/code. The passive document's nonbreakable-block correction remains; canonical/copied bytes, no-resource behavior and technical literal details are unchanged.


### Compact disclosure and recognized refusal details

Activity and technical disclosures use the same small centered chevron. Retained decision/item reference rows show one muted expandable outcome, with the existing app-authored explanation inside. Known decision fields receive ordinary labels; the unmodified JSON remains selectable behind Original payload. A decision/item pair never invents a user, Desktop destination or reason. Disabled-primary backing and boundary-first body wrapping remain as above.


File-removal controls use the existing transparent EA secondary-button treatment, a smaller glyph and the same compact action hit area. Only Flow's inter-file gap increases; each filename stays close to its own remove action. Original model IDs, disabled/accessibility behavior, responsive wrapping and literal elided names remain.


### Steady work text and one icon choice per appearance

The real work cue retains its existing execution/question/plan/visibility predicate and label accessibility. Working… stays at full text opacity. Its small fixed monochrome icon slot chooses once when the cue becomes visible between the simple ring and genuine EasyDiffraction BW mark, keeping that choice until hidden; hidden cues stop their animations. The BW source is unchanged easyscience/assets-branding easydiffraction/icons/bw.svg, git blob5813e570173676bc1ccb94868315b1ff880abff4. QtQuick.Controls.impl IconImage (already used by EA controls) supplies theme tint without a new effect/dependency.

Branded motion reuses the actual EA SplashScreen RotationAnimation and Edi WASM make_logo.py/splash.css curve:2160 degrees in2000ms, Easing.OutInElastic amplitude1/period0.3. It is not a linear approximation of the generated CSS keyframes. The simple ring uses the selected preview's1600ms linear loop. Existing zero translation-time behavior leaves a static icon. Neither icon represents elapsed progress, provider usage or a fabricated live operation; no status predicate, protocol, canonical message or auth state changes.


### Disclosure measurement uses the actual caption and fixed icon slot

Command/activity, technical and original-payload disclosure widths include the actual fixed glyph width, spacing and control padding, measuring the exact painted caption font and rounding its advance upward. Elision applies only when the available parent row is truly narrower. The original chevron is vertically centered without a height feedback loop. File removal keeps its existing compact hit area/transparent secondary treatment but aligns the glyph toward its own filename and reduces only their internal gap; the larger Flow gap between distinct files remains. Canonical text, selection, accessibility and disabled actions are unchanged. Actual geometry/render qualification remains required.

The small working icon uses the selected application themeAccent; the label remains steady themeForegroundMinor. Neither the selected once-per-appearance motion nor actual execution visibility changes.

Selected-file Flow uses the actual editor left/right padding for its inset and available width, aligning the first filename with message text without adding a second spacing constant or extending the scroll viewport.

The compact caption adds a short action/object excerpt from the pinned 0.162.1 structured CommandAction read name/path, list path, search query, file-change path, web query or tool name. It describes the supplied action, never an inferred scientific purpose or successful validation. Opaque shell commands use “Run shell command”; mixed structured actions use “Run combined actions”. No raw-shell heuristic or invented “Checked input data” claim is used. Literal targets/queries remain unchanged in retained payload/details; caption excerpts alone are bounded to three object words/40 characters and rendered as plain text. Existing actual public/original status accounting remains authoritative.

Caption excerpts cut only between Unicode scalar values. “Run combined actions” additionally requires every entry to be an actual known typed command-action declaration with the pinned required/optional field shapes; null, primitive, missing-type/required-field or malformed optional-field entries retain the opaque fallback. Canonical data is not changed.


### Stable sidebar sheet and return action

The sole app-bar opener uses the actual bundled Font Awesome 5 columns ligature (U+F0DB) while Assistant is shown, naming its action Show project sidebar; while hidden it uses robot/Open assistant. Home/unavailable enablement, same toggle, preferences and focus semantics remain. Font metadata was checked in the pinned bundled OTF, including the lowercase columns GSUB ligature.

The existing fixed assistantFallbackHost is the popup's visual parent on every workflow page, not only Home. It already matches the window's app-bar-to-status-bar strip, current sidebar width/side and clipping. Previously rehostAssistant reparented Popup.Item into the target page's sideBar.parent; ContentArea is a real SwipeView, so the target page's moving transform also moved the popup during navigation. Keep activeAssistantHost and the initiating/current page/project references as logical focus/currentness identities, but use the existing stable window-content strip for rendering. Both main-page animations and the assistant's own enter/exit remain enabled. Actual reciprocal-transition geometry qualification is required; this source rationale is not a captured runtime claim.



### Bundled code metrics and report-style Markdown tables

The passive parser remains Qt MarkdownNoHTML with parsed images replaced and resource fallback blocked. Qt6.11's importer selects a system fixed font, although it copies the document's nominal size. Presentation overrides parsed inline/block code with the actual EA monoFontFamily (bundled PT Mono) and matches its x-height to the actual body font, scaling only code. Body uses the real QML font and scale. Font/colour changes reformat existing document ranges without changing source/history/copied text or reparsing HTML. Actual visual equality still needs font-metric/readback and light/dark qualification; nominal equality alone is not asserted.

Tables reuse report_html.cpp's thin outer/header rules, collapsed borders, zero vertical padding, horizontal spacing ratio6/20.4 and alternating/header shading; app theme border/content colours replace the report's paper palette. Parsed table/alignment/merged-cell and Markdown emphasis semantics remain intact. No external resource, new parser, arbitrary HTML or link action is introduced.

The parsed-table styling explicitly bridges Markdown's one-header-row semantics into QTextTableFormat before calculating its header rule/background and body stripe phase. Qt6.11.2 Markdown importer sets TH character boldness but leaves headerRowCount0; relying on that absent property was MD1. Every table in this passive document comes from setMarkdown with MarkdownNoHTML, so no heuristic over raw source, bold cells or arbitrary HTML is required. Parsed cells/alignment/spans and original content remain unchanged. Real document header/body/font/theme readback still qualifies the presentation; source metadata alone is not a visual-size claim.


The owner's larger working cue scales the actual decorative glyph by1.75 from its former0.75-font-pixel extent. Its allocated slot and label left padding use that same new extent, and the layout's minimum height contains it without overlap. Both genuine icon and steady Working text use themeAccent. Text, visibility/question suppression, per-appearance random choice, exact branded/simple motions, reduced-motion and hidden-stop behavior are unchanged. No new progress state or fake busy source is introduced.

### Purposeful titles and open table typography

Assistant tables use left-aligned header/value blocks, larger cell/frame spacing and no vertical borders. Only the restrained horizontal header rule and alternating row shade remain. Activity suffixes use an explicitly supplied purpose/description; missing metadata yields the truthful category/outcome alone, never a guessed goal from shell text or repeated file names. Retained source/copy text and passive Markdown resource handling are unchanged.



### Clear preserves a genuine managed connection

Clear discards the conversation and retires pending UI/result/file/context authority; it does not request logout. For an authenticated managed runtime it suppresses publication of the discarded conversation while retaining its bounded original protocol proof. It interrupts the known turn once (or waits for the actual admitted ID), then waits for the real terminal and correlated input/interrupt replies under the existing first revoke deadline. Only settled Clear uses the existing idle-only managed rebind, preserving actual account/catalog/process while retiring the old thread/workspace and requiring fresh context approval. Repeated Clear cannot refresh cancellation. Account changes, unknown refusals, transport failure and timeout remain authoritative failures, never forced ready/authentication. Sign-out/project replacement retires the pending Clear. No old rows or questions may reappear.


Clear cancellation settlement retires the completed revoke operation only after real terminal plus all correlated input/control acknowledgements, before managed idle reuse. Turn-bound interruption-issued evidence survives its RPC acknowledgement until that turn's terminal/owner teardown, so Stop→ack→Clear cannot issue another interrupt. The outstanding RPC ID independently retains acknowledgement ownership; repeated controls cannot refresh the first unsettled deadline. These correct CLR1/CLR2 from the complete private review; runtime proof remains owed.

CLR3 uses the existing single-control admission policy: while an interruption or its real input/control settlement remains pending, refuse new input before any row/wire/deadline change and retain its draft/account. An older pending interrupt ID cannot prove interruption of a different turn or be overwritten by Stop/Clear. Clear's issued evidence is strictly thread/turn-bound; a pending older control is separately awaited. A terminal no longer settles an unfinished revoke deadline: only terminal plus every owned input/control acknowledgement releases it. Both acknowledgement/terminal orderings use the same bounded settlement check; actual failures/timeouts remain authoritative. No new RPC map or public API is introduced.


CLR4 preserves only the established, exact pinned nonadmission recovery for an already-owned steer inside Stop settlement: genuine authenticated owner, matching thread/expected turn or its retained terminal proof, exact pending row and allowed reason remain mandatory. Its early return runs the same full revoke/clear settlement helpers; no unknown error, stale input or automatic replay becomes eligible. A pending start does not prematurely settle an active revoke scope.

CLR5 releases a discarded question's exact existing transport request through CodexAgent::reject after clearing its UI authority. The request table retires the ID/byte charge before the refusal write; answered/resolved/already-retired IDs are inert. No answer is fabricated, no old UI callback is revived, no new request map is introduced. An actual uncertain transport write retains the normal failure fence. Thus late old-thread resolution cannot orphan a charge across a preserved-process rebind.


CLR6 separates no-write question detachment/answer transfer from deliberate discard. A validated public answer takes the original RPC/key, clears UI authority without rejection, then calls the existing once-only CodexAgent::answer. Discard uses reject only; already resolved/answered IDs are inert. Failure/full workspace teardown detaches while its existing transport retirement clears records, and an actual resolved notification detaches only after releasing that known record. Every discard caller checks synchronous owner/auth/thread/generation retirement before proceeding or clearing diagnostics: Clear, Stop, sign-out, item completion, terminal handling and managed bind stop on failure. No fabricated answer, fake connected flag, private API or extra request map is introduced. Runtime answer/discard/reentrant-failure proof remains owed.

Initial assistant-result host preparation validates the existing canonical scientific definition plus exact parameter states/declarations and unchanged input/membership/edit evidence across ownership moves. ItemVec move generation renewal is not a user edit. The strictly captured WorkStamps belong to the FINAL ProjectViewModel owner and remain mandatory for every subsequent Save As/currentness check; unchanged_since is not weakened globally. No provider result or scientific value is synthesized.

### Context retirement is not account retirement

Successful selected-file add/remove and actual owner/disclosure changes invalidate their original native authority, not the genuine managed process/account/catalog. Host-owned selected snapshots and retained conversation remain. Existing file admission runs only when execution/retirement is settled; its own staging flag does not imply account logout. Ordinary project/manual-fit changes within the same approved scope invalidate scientific freshness only: they settle the original conflicting operation without interrupting the official turn or rewriting unrelated activity. A retained fresh inspection establishes authority for later operations; actual changed disclosure still requires real approval. Clear and scope retirement drain original correlated work naturally; only the AI Stop requests a turn interrupt. Explicit logout, unfinished/unadmitted connection preparation, unknown protocol/transport failures retain real process/account retirement. Retired workspace files remain available for explicit recovery; a new staged thread never relabels them as fresh. No authenticated assignment, manual approval bypass or new RPC ownership table is introduced.

FA1 preserves the matching old-turn interrupt-issued evidence through repeated binds, before and after its actual acknowledgement. FA2 propagates interruption-archive retention failure: keep the bounded original archive, retain the actual storage diagnostic and block new execution until explicit Clear, while real cancellation still settles and admitted file changes remain committed. No missing outcome is relabelled successful. FA3 contains the entire bool-returning context transition, including cancellation admission failure, at its ordinary Qt callback boundary; genuine authority failure uses the existing fail/retire fence without undoing or misreporting a published manual edit/fit. These are ownership/publication corrections, not a new request map or persistence framework.

FA2-R records the bounded cause of failed context-history retention separately from uncertain input delivery. Send refuses before encoding/consent/wire; sign-in and ordinary pending RPC/terminal/handshake notifications cannot acknowledge it. Explicit successful Clear owns releasing it. An unrelated preflight refusal cannot turn that retained-history block into account failure. FA3-R retires the chooser/result and notifies the committed project revision before the fallible context transition on both manual-edit/fit callbacks. Ordinary Session bind always completes consistent project/controller attachment even when context retention/cancellation fails; it does not throw a recoverable false return after Session's project commit. Existing actual fatal cancellation/account fences and pending control proof remain.

A user-click report link is resolved against its app-retained completed-message/workspace owner, never the newest workspace or an unvalidated URL. Report ownership survives context changes while its actual row/files remain; Clear removes it. The narrow desktop route accepts local relative/file HTML/PDF targets only, reads every path component no-follow with existing regular-file/identity/byte checks, and opens a host-owned immutable copy outside the runtime write root. It reuses existing per-file/aggregate selected-file bounds and UI-message count for retained views; unsupported/missing/stale provenance is visibly unavailable. Passive Markdown still fetches no resources or HTML, and only the explicit click invokes the platform viewer. No arbitrary external/script URL, shell invocation, provider lookup or project mutation is added.

HTML report viewing preserves a bounded no-follow snapshot of the actual report directory and local descendant assets with original filenames/relative layout, rather than renaming/copying its text alone; PDF remains single-file. Every entry/type/alias/count and each pre-read file/aggregate byte admission is checked before copying; original directory/file identities are rechecked after the complete copy. External/parent-directory assets are not acquired or promised by this first route. Actual self-contained/relative-asset report rendering remains a runtime witness, not an inference from an .html extension. Existing native-result verifier bounds remain unchanged.

Both successful explicit Clear paths release report row provenance, retained immutable views and their byte charge together through the same state helper. This includes Clear after genuine logout or transport failure. Failed archive discard preserves all three owners with the retained history; ordinary context retirement preserves historical read provenance.

Actual saved-result opening success/failure is retained as a chronological Edi-authored activity with a stable per-intent row ID, app-known human title and literal explanation. It does not impersonate a model response or treat writing a receipt as opening. Failure is emitted only while its exact original settled intent is still current; success requires the actual adoption return and the expected one managed bind, same final project and no later owner retirement. The existing bounded history/pending-row storage fallback remains authoritative; successful retention does not add the old duplicate floating opening-error banner. Technical payload remains secondary.

A validated terminal for an already retired Clear/context does not retry archive publication or turn a prior history-storage refusal into account loss. Pending steer proof records observed settlement separately from durable retention. Only that same owned retired-context/storage-blocked request may use its observed terminal for the existing exact known nonadmission recovery; ordinary requests still require genuine durable terminal proof. No unpersisted outcome is labelled retained and no result opening capability is minted from discarded output. The held storage diagnostic/block survives protocol cancellation settlement until successful explicit Clear.

The native Save As picker authorizes its selected parent root, including an alias to a writable physical directory. Export pins that resolved physical root and re-resolves/rebonds the same selected parent immediately before publication and reopening. The existing strict directory helper and every untrusted stage/final descendant no-follow check remain unchanged; a different alias target cannot redirect a pinned export. Child collisions/symlinks still refuse, no overwrite/fallback is added, and no directories are created through an unverified child path.

Review140: result notices are prepared before opening and published through an independent noexcept boundary with prepared-row/storage fallback. A post-adoption notice failure cannot become a failed-opening event. Runtime items cannot use the reserved ediOutcome type; only host-created rows select that title. Observed terminal proof covers both healthy Clear and context retirement as well as storage-blocked retirement, always with the original pending RPC/thread/expected-turn and exact known nonadmission reason. Discarded output is never labelled durable or used for report/result authority.


### Header focus-tooltip placement

The connection and Clear tooltips share keyboard-focus/hover availability and accessible names. The assistant header is immediately below the app bar, so these app-local custom tooltips open below their controls using the existing font-relative gap, instead of extending an above-control popup over the actual app-bar toggle. This preserves the stable global assistant parent, genuine account keyboard focus and ordinary single-click toggle; it changes neither the shared EA widget nor global animation/input policy. The original default tooltip outer padding, not just its text rectangle, is part of this placement boundary. Actual pointer/header-tab regression must be exercised with the real tooltip visible; no extra click or disabled-tooltip oracle substitutes for that check.


### Actual account allowance windows

The existing usage button reads account/rateLimits/read once after genuine managed account/catalog readiness (before any prompt) and when opened, coalescing sparse account/rateLimits/updated notifications into one optional full read. Only supplied bounded windows, bucket metadata and per-bucket credits are retained; no quota, currency, five-hour/week label, recovery permission or context-occupancy numerator is invented. Explicit empty bucket data is not replaced by older state. The ring clamps paint only and labels its most constrained actual window; details list all actual windows/credits/reset/duration and read time. Context occupancy remains independently unavailable.

Usage cache/request identity belongs to the genuine account/process epoch, not conversation generation. Normal Clear/context/project changes preserve it; actual logout/account/process retirement clears it. There is no imagined workspaceRouting identity from account/read. The exact optional read is handled before general RPC failures and cannot begin/settle/refresh inference activity. Optional timeout/capacity/unsupported/invalid metrics mark unavailable/stale without logout. CodexAgent retains bounded exact issued-ID late dispositions and may preempt an optional read before it crowds a required control slot/byte reservation. Genuine write uncertainty, malformed transport, unknown IDs and required request deadlines remain fatal fences. No polling, token/context percentage, credit/reset/email action, provider inference or new service is added. Runtime offline peer/UI and actual account availability remain to be qualified.


### Optional usage observation: required capacity and account visibility

Usage read remains optional at every shared required admission door: client requests, incoming original reverse RPCs, answers/rejections and the physical outgoing queue. Exact issued optional identities retain their bounded late-response disposition when logically preempted. Optional writes start only with an empty physical queue and required pending-byte/slot headroom. QProcess cannot retract already-buffered optional bytes: one bounded existing-limit required-byte holding slot preserves the exact complete original record until the physical queue drains. The existing physical write cap is unchanged. Required logical queue ownership is admitted independently of the optional FIFO head; the holding slot is bounded by retained_record_bytes and retains its first control deadline across appends. Full records transfer once; partial write/EOF/error/required timeout retires delivery without replay, rebuilding from changed state or activity/deadline refresh. Process retirement discards the old exact ownership.

Sparse notifications advance a nonallocating update serial. A read started before a newer observation may supply only stale data; it cannot erase the notification and declare freshness. Refresh remains coalesced and bounded, with no polling or response-triggered retry loop. Account/process epoch and a separate nonallocating snapshot visibility latch govern cached values, including immediate sign-out initiation and allocation failure in best-effort JSON clearing. Conversation/context retirement preserves a genuine account snapshot; a later account cannot expose its predecessor's cache merely by becoming ready.

Canvas invalidation distinguishes supplied zero usage from no supplied window, including availability/visibility recreation. The Usage dialog shares AssistantSkillsDialog's actual viewport, chrome/body accounting, available scroll width and EA AsNeeded/noninteractive scrollbar. All actual windows/credits stay bucket-bound; stale/unavailable and context-unavailable remain honest. Static source-path review is not compiler, peer, rendered or live allowance qualification.


The initial optional account usage observation is issued only after the genuine required skills/thread bootstrap reaches its ready callback. Final model-catalog readiness records the account epoch but does not start an observation that the immediately following required skills request would preempt. Popup-open/sparse-update refresh and exact optional priority/disposition remain unchanged; no polling or response-completion retry loop is added.


### Usage fills the compact circle, not an outer button ring (2026-10-16)

The user explicitly wants the small account-usage circle itself filled proportionally, with no outside button ring. Its existing hit area/navigation/dialog and real-window accessibility stay unchanged; the secondary ToolButton background is transparent. The actual most-constrained returned usedPercent fills that fraction of the inner circle using themeAccent. No allowance is invented: unavailable has no numeric fill, known zero has zero fill, and the genuine remaining/reset/bucket/credit text retains its original meaning. Availability, actual percentage, theme and size changes repaint. This does not add polling/context-percent estimates or alter waiting animation.


The usage ToolButton's assigned contentItem is a framework-sized host, not a glyph-size promise: hiding the backing does not remove its implicit size. The child Canvas is explicitly centered and bounded to the intended compact EA unit size, clamped to the host's available dimensions. The normal hit area, keyboard/dialog behavior and every data/theme/availability repaint remain. It no longer relies on implicit dimensions of a Control-managed contentItem to constrain drawing.


### Clear and reentrant row projection (2026-10-16)

The assistant's app-local Rows adapter owns model keys while message values borrow the retained canonical JSON history. A successful archive Clear could leave old model keys until the queued render; those keys then read null roles from the empty canonical array. Ordinary assign publication could also be reentered from Qt data/insert/remove/move/count notifications: a nested latest assignment changed the source, but the outer key target could continue and reinstall stale keys.

The existing adapter now serializes its assign transactions. Nested requests only mark a newer projection; the current Qt begin/end transaction finishes before the adapter drains the newest canonical array and announces it. This applies to the same adapter's message, model, skill and selected-file rows, without changing the shared RowTableModel protocol, adding a second payload snapshot, or invoking Controller code from a retention/event hook.

The existing clearHistoryNow API boundary reconciles model keys against current canonical history after an actual committed discard, on all authenticated/disconnected/deferred attachment return paths. Failed discard does not reconcile/erase retained data. A nested newer owner is presented from its current history; a stale Clear cannot manufacture an empty replacement history. A presentation allocation failure keeps the actual discard latch, records the existing warning and queues a normal render rather than claiming archive rollback, authentication loss, or successful durable output. This closes model projection; account, cancellation, attachment and retained artifact authority remain their existing separate contracts.


### Assistant report link reuses the main Report page (2026-10-16)

Owner013474622 supersedes the unapplied separate report-generation design. The
exact user-click URI `edi:report` navigates to the CURRENT project's existing
Report page via `AppState.open(AppState.Page.Report)`, only when the current
Session project exists and the same `reportPageEnabled` guard used by the normal
Report tab is true. The existing page owns its normal ReportViewModel, preview,
plots, Contents and export controls; no report model, native tool, Worker, HTML
artifact or new filesystem authority is created. A navigation link is not a
saved/historical report, convergence statement or successful export receipt.

The existing AssistantMessage anchor signal and pointing-hand cursor are
unchanged. AssistantPanel intercepts only the exact internal URI before its
existing row-bound protected file-report router. Every other link still uses
that router and its retained provenance, no-follow/path/byte/view checks. A
missing or disabled current Report page opens the ordinary app dialog with a
plain-language explanation. No arbitrary URL opener or project replacement is
introduced. The versioned project-assistance skill names the exact current-page
link; its catalog digest changes without claiming a new native capability.


### Native working-folder scope

Choose working folder uses the existing native FolderDialog pattern with one host-created VM intent capturing the actual Session/project/controller revision, selected-file/connection generations and accepted-input/account epochs. Only its current one-shot picker callback can replace the host's pinned physical folder; chat/provider paths are not setters. Cancel or stale/unavailable selection preserves the earlier scope. The visible folder is Session-owned, separate from account/conversation/report read leases. Normal contextual retirement preserves genuine account/catalog/history and admitted selected snapshots, prepares a fresh execution thread and revokes old write authority. A picker-authorized folder change does not ask the same scope permission twice; complete first outgoing-data disclosure and any changed scientific data remain separately guarded. No native save/report operation is registered by this increment.

The existing app-private descriptor boundary pins the physically selected directory, refuses protected host-storage overlap and checks its identity/access again before new request/native admission. Pinned official runtime0.162.1 thread/start config replaces the workspace-write table with exact app-owned staging plus the chosen folder, network false and both temporary-directory exclusions true. Thread readback must return that exact root set and unchanged cwd/provider/reviewer/approval policy; every turn/start sends the same explicit sandboxPolicy. No named broad profile, external grant, inherited extra root, filesystem read jail, continuous same-user rename guarantee or global profile mutation is promised. Without a folder choice, the existing app-owned temporary workspace remains the complete writable scope. Removed/unavailable roots refuse fresh requests honestly; local pre-RPC staging refusal preserves the actual account.


The working-folder extension owns the earlier selected-snapshot cache: it now lives under protected AppLocalDataLocation/assistant/input-cache, alongside the already protected creation/result/report leases, rather than a default temporary-directory sibling that the user could accidentally grant. Picker retirement consumes its one-shot ID before native dialog closure across context/bind/Clear/Stop/sign-out; a retirement interval refuses new folder intents and mutual picker starts. Clear does not silently reset the chosen folder or release historical report provenance on ordinary context changes. Returning to temporary mode uses the same actual intent/currentness/consent door as choosing a folder. Both preserve genuine account/catalog/history while replacing obsolete execution context; actual protocol/auth failure remains authoritative. Complete created-project context is augmented through the same private grant/action envelope before the original creation commit, preserving its native receipt and selected-byte ownership.

A locally unavailable root before thread submission or Send is a definite refusal with no input admission; a vanished root during a genuine thread reply does not turn valid policy/account evidence into logout. Exact policy comparison still uses the declared root set, and all subsequent Send/native admission requires the pinned physical root to remain current. Scope transfer only preserves already approved data for the exact unchanged owner/stamps/selected-file/account/input generations. A first or changed outgoing data disclosure is not fabricated. No continuous filesystem lock, read isolation, supported edited Save As, newly registered save/report tool, or live platform witness is claimed. The grant is ordinary folder read/write scope; prompt/objective rules preserve originals and native model adoption/Save As retains its own strict currentness and external-disk guards.


The new folder actions extend the existing explicit header/composer keyboard cycle rather than relying on default focusability. Forward order is Usage -> Choose working folder -> Use temporary folder when visible/enabled -> composer; reverse follows the same actual controls. Missing/disabled folder actions are skipped in both directions, preserving the existing app-bar/popup focus boundary and active-operation behavior. This owns the preceding Usage-to-composer route; no new focus framework or shortcut is introduced.


### Retire the staged Python launch prerequisite (2026-10-16)

ADR0009/0015 require a self-contained C++/QML production app. The historical staged-scripting bootstrap recorded above is superseded for normal app launch: actual app native DynamicToolSpec dispatch uses the existing C++ Session/ProjectVM/FitVM/core doors, and the current production launcher/runtime/skill guidance has no consumer of EDI_AGENT_PYTHON, EDI_EXTENSION_DIR or PYTHONPATH. The developer app-with-crysta launcher therefore no longer installs the default binding environment, builds/imports the edi extension, or injects those Python paths before launching. It retains the genuine local crysta native build, pinned/local SDK distinction, app bindings-OFF graph, CI refusal and forwarded app arguments. Explicit Python binding development/tests remain separate declared commands; build metadata tools may still use development Python. This is source dependency closure, not a claim of tested packaging/platform sign-in or complete assistant capability.


### Native positioner intrinsic sizing at startup (2026-10-16)

The working-folder controls use QtQuick Flow within the existing ColumnLayout. Flow inherits the native implicit-size positioner; its implicitHeight is read-only in the pinned Qt6.11.2 import and already follows its laid-out children. The invalid childrenRect-height assignment is removed. The existing Layout.fillWidth and spacing determine wrapping, and the native intrinsic height supplies the layout's preferred height; no extra height binding, feedback loop, component or sizing framework is introduced.

The finite application-QML positioner audit covers direct Flow/Row/Column/Grid and locally derived root types, including nested objects: no other implicitWidth/implicitHeight property assignment on a positioner was found. Ordinary controls' writable implicit-size assignments remain. Actual Main instantiation, wrapping and affected controls still require the original runtime consumer; C++ compilation and syntax parsing alone do not prove QML startup.


### Optional genuine visible native actions (2026-10-16)

The owner requested both fast native execution and optional human-like controls. Show actions is off at each new app Session; toggling it never creates an extra scientific approval or a different provider loop. Normal native capabilities remain unchanged. The mode exposes only an actual singleton value/free input and the existing available single/joint fit. Creation, relation editing, multi-input batches and unavailable/filtered widget paths refuse before writing; no pointer animation decorates a hidden direct scientific mutation. Native inspection reports the actual mode. Full create/import, selection/scrolling, save and accepted-best visual workflows are not supplied by this slice.

This owns the compiled EaElements.RemotePointer prior art and app demo_driver real QMouseEvent/QKeyEvent/QTimer principles. The old RemoteController imports QtTest/QtMultimedia and is excluded; neither dependency nor blocking wait is added. The helper reuses the matched pointer's move500ms, press100ms and click-relaxation500ms, plus RemoteController's character100ms as asynchronous timers. Controls are host-selected by exact actual ParameterItem identity/path and genuine named tab/value/free/fit widgets, never provider QObject selectors or a command language. Hidden, clipped, disabled or missing controls refuse; actual event delivery and model readback determine the result.

The sidebar's preference is retained while the manual controls are temporarily revealed. Finish, question and programmatic retirement restore ordinary sidebar visibility, respecting the user's current preference. Genuine manual input instead marks a takeover scoped to the actual current project before cancellation, leaving the manual sidebar exposed until the user explicitly opens the assistant. This avoids changing geometry/focus over the original press/release, key, wheel or touch event. It never replays an event or overwrites the preference; a replacement project does not inherit that takeover. The Stop slot remains present during takeover so cancellation cannot shift app-bar targets before the same event is delivered. The new mode checkbox extends the actual Usage/folder/composer Tab/Backtab chain and skips disabled controls. Only an explicit AI Stop interrupts the official turn. Genuine conflicting project input supersedes the original visible operation with factual partial results before the same event continues; harmless input and application switching do not interrupt the turn. Old timer/completion callbacks can neither hide a replacement pointer nor settle a later RPC.

ParameterField and ParameterCell now own an app-private view-only draft guard: paced text is not accepted by ordinary focus-loss/editingFinished. Only the prepared final Return releases that guard. Cancel resets the current model binding rather than replaying an old number or leaving a valid partial number to commit after focus loss. The real setter enters an exact prepared editor receipt, so the existing recorded Undo/validation/publication path remains authoritative. Fit completion is prearmed before the real Start fitting release and remains owned by the actual FitReport, independent of fallible running/presentation notifications. No scientific rollback of later user edits or fabricated worker completion is used.


### Visible input discovery, draft preflight and contained cleanup (2026-10-16)

Both the named-tab/fit and exact-parameter lookup doors own DemoDriver::find's two-tree convention: search window QObject descendants and recursively include actual visual childItems, deduplicating them. Select an actual current-window visible/enabled on-screen unclipped center; no hidden/offscreen match is a substitute. Actual event/readback still decides whether the supported control committed.

Before hiding the assistant or changing focus/navigation, value/free/fit all inspect the current focused ParameterField/ParameterCell ancestor for a manual draft. Any text different from both current displayed and full committed value refuses before input. The helper repeats that guard before actual navigation/press and excludes only its exact owned paced draft. It does not commit, overwrite or focus away from a pre-existing manual draft. Its cancel guard is released only after the current committed binding has been restored, never before a fallible view cleanup.

Balancing release, timer stop, editor finish, pointer-hide/active notifications and original completion each have their own containment and original-request checks. Failure of one does not terminate a noexcept path or skip the other prepared cleanup. A failed refusal diagnostic uses the already owned native uncertainty/response roles and fences further work; it never invents a durable outcome. Public Start fitting separately contains real Worker cancellation and observer diagnostics; a submitted worker keeps its real FitReport callback. A cancellation trace failure after the actual flag is set keeps the original worker/RPC and refuses new work rather than logging out merely because that new cleanup notification failed. No permanent-allocation guarantee or fabricated completion is implied.


### Explicit managed sign-in and bounded bootstrap diagnostics (2026-10-16)

The genuine Sign in with ChatGPT choice starts the official interactive managed flow for a missing account or known API-key/Bedrock account. Those other credentials never authorize model/inference/API billing, forced login success or an implicit logout/copy. Each genuine Sign in attempt admits at most one interactive login request; a subsequent read that still reports a non-managed account refuses honestly instead of reopening browser login. Unknown/malformed account variants still refuse, and the official runtime remains authoritative for configured login restrictions and actual account completion.

Skill discovery returns global/plugin errors alongside the requested workspace. Well-formed errors outside Edi's staged workspace do not invalidate complete required Edi registrations. Relevant or malformed errors still refuse. Required paths must remain exactly registered, enabled, unique and named by the actual bundled index; staged bytes must match its existing SHA256. Missing/changed/disabled content, aggregate bounds, thread policy and exact writable-root/currentness checks remain fail-closed. No global profile or skill is altered.

Bootstrap failure reports only a fixed app-owned stage/method/reason through existing lastError and the existing connectionFailure dialog, for example checking bundled skills [skills/list: SKILL_DISCOVERY]. No raw exception/server text, account/email/login IDs, auth URL/query, paths, contents, response payload or stderr is exposed. Fixed reasons distinguish reply shape, request admission, account kind, login/browser, catalogs/required skills, thread/root policy and publication; unknown failure stays fixed. This addresses concrete response classes and makes the still-unobserved Mac failure attributable; it is not a claim of qualified live sign-in. Owner authorizes draft push before verification, with checks to continue afterward.


### Implicit workspace in official root readback (2026-10-16)

The pinned official WorkspaceWrite compatibility projection represents the exact current working directory implicitly and may omit it from additional writableRoots. After the existing exact cwd/policy check, Edi therefore includes that workspace once in its effective returned set. A separate explicit-entry set still rejects duplicates, including repeated explicit cwd. Every explicit root must be an admitted root and the complete effective set must exactly equal the requested workspace plus genuine chosen folder. A missing chosen folder, extra root, changed cwd, malformed root or changed network/tmp/provider/reviewer policy still refuses. Requests and permissions are unchanged; no canonicalization, alias acceptance or extra filesystem grant is introduced. This corrects the owner-reached thread/start THREAD_ROOTS representation failure, without claiming live Mac sign-in qualification.


### Prepared native document export foundation (2026-10-16)

The native save implementation reuses AssistantResultExport, not a second directory publisher. Its new app-private input captures an ALREADY bounded real-writer document set into the same protected immutable result snapshot/receipt/no-follow/real-loader boundary. It admits all path aliases, complete fixed native closure, byte/count/directory roles and SHA-256 metadata before any destination file/copy; it does not make an unbounded upstream scratch save safe. Existing selected-result capture now shares the protected snapshot constructor.

Native automated export accepts the genuine shared pinned AssistantWorkingFolder capability, not a provider parent string. Writes duplicate its actual directory descriptor, retain that grant and recheck current physical identity after original host currentness and immediately before the existing no-overwrite rename. The ordinary picker Save As constructor remains. Both routes independently load protected source bytes and verify the destination-local stage against that exact closure, then keep the existing immediate committed latch. There is no overwrite/copy/remove fallback or unsafe mutable-path cleanup.

A chosen runtime root is writable by the official agent. The actual parser therefore never reads its mutable children directly: before commit the exporter preowns one bounded protected validation slot; after commit it verifies/copies actual published bytes by retained descriptors into that slot and uses the same real loader there. Repeated reopen validates/reuses the same slot. The final published namespace/closure is checked again, and a postcommit failure remains committed rather than claimed rolled back. The displayed model/path/modified/Undo are untouched by this foundation.

This private foundation is not registered as a save tool. The actual native writer still requires pre-growth bounded preparation before conversion/currentness/derived work/serialization; the pinned SDK save_project alone provides no such admission. Original request/account/current project/stamps/Stop ownership, complete outcome and artifact budget reservation and worker settlement must be wired before any native save registration. No app-owned scratch output, posthoc byte check, copied model losing computed provenance, Python fallback, arbitrary root or accepted-best/trial claim closes that dependency. No runtime/platform/packaging or genuine save success is claimed by source inspection.


### Complete current native saving integration

The prepared-document exporter foundation above is now consumed by the actual
normal-mode `save_project` original-RPC operation. The native picker pins the
physical parent; the model supplies only a fresh basename. Before real work the
host jointly admits original record/row/response, immutable source/container and
prepared factual-outcome roles. Actual worker completion remains owned through
Stop/Clear/sign-out/context retirement; the shared worker hold includes saves.
Successful explicit Clear still immediately removes UI authority and does not
repopulate discarded rows when the real worker later settles. Failed Clear keeps
its retained archive, actual warning and existing execution fence.

Real no-overwrite commit, actual-byte reopen verification and active same-PVM
saved-state landing are distinct facts. Their exact original record receives
preowned truthful state at each latch before fallible presentation. The final
conversation outcome reports these facts chronologically through the existing
native row, without a new report/artifact UI or floating success banner. Ordinary
working-folder/file actions do not log out or destroy selected snapshots/history.
The saved root remains user-owned; protected captured inputs/reopen leases stay
within existing bounded file/collection/count and lifetime checks.


### Occupied export destinations refuse before staging

The shared AssistantResultExport state checks the fresh leaf through its pinned
parent descriptor with fstatat/AT_SYMLINK_NOFOLLOW before mkdirat. An existing
directory, regular file, symlink (including dangling) or other occupied object,
and lookup errors other than absence, refuse without creating an export staging
directory. Both ordinary fresh-result Save As and native current-project saving
use this same admission. User destination bytes and link targets are untouched.

This is an early side-effect admission, not a replacement for Linux/Mac atomic
no-overwrite publication. A destination introduced after preparation still
refuses at the final no-replace rename. Existing bounded unpublished recovery
retention remains for such later failures; no mutable-path recursive deletion
or false inode-conditional cleanup guarantee is introduced.


### Visible presentation belongs to the running request

The first genuine visible action exposes manual controls through the existing
showingActions property. Finishing its widget input releases only that tool's
parameter/edit/fit-preparation state; the still-running authenticated request
keeps the sidebar exposed across subsequent actions and read-only gaps. Actual
terminal/retirement, failure, question or Stop releases presentation through the
existing notification/retirement seams, independently of genuine Worker/report
settlement. No widget, scientific edit lock or original RPC is retained merely
to keep the sidebar closed.

Real manual input between tools is owned by that same current native receipt.
It marks the existing manual-takeover presentation policy before settling the
original operation, then preserves the genuine event/target. The marker prevents
reopening over that event. Window/toggle changes can retire an unavailable
original tool without requesting whole-turn interruption.
Old cleanup checks the captured receipt and replacement widget before changing
presentation. This does not implement missing widget navigation or background
insertion, and does not treat animated pointer movement as user input.


### Deferred covered-focus enforcement and explicit report-message sizing

The existing covered-input focus guard schedules coverage-change enforcement
through the same Qt.callLater function used for focus changes. It rereads the
current coverage and respects genuine manual takeover, instead of synchronously
changing a dependency while its coverage binding is notifying. The guard remains
active for current covered controls; no old-page focus is captured.

The current-project Report-unavailable message uses the same explicit
contentWidth/contentHeight convention as the existing assistant connection
dialog: fixed available width constrains its plain wrapping text, whose
implicitHeight determines content height independently of popup availableHeight.
No report generator, URI permission or historical artifact authority changes.


### Common editor drafts block assistant navigation before blur

The existing AssistantWidgetInput manualDraftPresent preflight covers the common
ValueField and TextCell editors as well as ParameterField/ParameterCell. The
common editors expose a readonly dirty predicate using their OWN commit rule:
ValueField compares text with its inherited displayed value while editable;
TextCell compares text with shown, including the numeric display formatting.
Comparing against raw full precision would mark an unedited numeric cell dirty.
The same text/id/integer/numeric and clearable/invalid/partial editor variants
are covered; validation success is not a condition for protecting a draft.

Quick operation-page/Main/Extra following and every existing real visible
Navigation/Value/Free/Fit click consult that same helper BEFORE a focus change.
An unrelated manual draft refuses the assistant action without changing focus,
text, editor/core state or Undo. The helper does not commit, clear, discard,
validate or restore a manual draft. Existing parameter assistant-owned draft
exclusion and cancellation/commit rules remain unchanged. Read-only tools and
non-navigating saving acquire no new restriction or permission. This closes a
prior-art common-editor gap, not a general property/navigation executor.


### Compact genuine working-folder caption

The existing native working-folder selection and temporary-workspace actions
retain their actual intent/grant/currentness boundary and keyboard chain. Their
caption now shares the Show actions row: the actual chosen path's basename is a
single plain-text, middle-elided label, with the full actual path in its tooltip
and accessible name. An empty path explicitly names the app-owned temporary
workspace; a filesystem root retains its nonempty root spelling. A long basename
has no minimum/preferred layout width and gives way to the existing checkbox.
This is presentation only: it does not turn text into a grant, alter selected
files or conversation authority, toggle action mode, add a path editor, or open
a file. Sent-attachment acknowledgement and hidden-chat Working remain separate
UX changes, rather than being claimed by this compact caption.


### Acknowledged input presentation retains file authority

The original void send entrance is preserved. The composer uses a narrow
submitDraft entrance returning the actual admitted public user-row UUID; that
return is not acknowledgement. It consumes text only when that exact row has
reached durable completed status through its original successful input response,
and only if the actual editor revision/text and presentation owner still match.
Refusal, uncertain write, failed archive retention, rebind and a newer identical
draft do not erase unsent text. Real IME preedit/composition changes also advance
the editor revision, and acknowledgement never clears an active composition.
Independent steering acknowledgements keep their
own original row IDs rather than matching an arbitrary new equal-text row.

A user row owns bounded plain descriptor snapshots in its ordinary history
payload: actual selected ID, filename, byte length, readability and format. It
contains no copied file bytes, source path, credentials or provider reasoning.
Existing complete row/history admission and durable publication apply to this
payload. Pending/refused rows do not display it as sent. Only the exact durable
completed row makes those descriptors sent presentation. Old history without
descriptors remains valid. Fresh selected-file UUIDs distinguish later additions.

The selected-file model gains a presentation-only pending role derived from
actual completed history; its canonical Controller collection, immutable bytes,
hashes, native receipts and scope consent are unchanged. Sent chips move to the
user bubble rather than calling removeSelectedFile to hide them. An explicit
idle Remove remains available on each still-selected sent snapshot and uses that
same ordinary removal/currentness door; historical descriptors remain after
revocation and claim no current read lease. New files and refused-send chips stay
in the composer. Presentation is bounded by existing selection/history limits,
with no unbounded sent-ID store or duplicate archive.

### Shared genuine Working cue outside the hidden conversation

AssistantWorking extracts the existing panel cue, assets, accent, per-appearance
choice, exact rotations and reduced-motion/hidden-stop rules. Both panel and
statusbar use its actual agent_active/no-question/no-plan predicate. The hidden
chat instance reserves its measured width beside the independent fit area in
keysFit and roomFor; it neither replaces fit results nor infers activity from fit
progress or canCancel. Home may show this genuine active status too. The actual
Main panel visibility remains request-wide through showingActions, original
workflow host and user preference/manual-takeover precedence: final request
settlement returns the temporarily hidden panel once, while a later explicit hide
or genuine manual takeover is not overridden. No idle transition from sign-in,
picker, Stop or stale callbacks is treated as a successful completion trigger.


### Selected-file projection retains its original continuation

The ordinary picker, explicit removal and acknowledged-input presentation share
one selected-row publisher. Before model notification it owns a bounded serial
and the original receiver, State, project, Controller, generation, file epoch,
connection epoch and desktop account/input identity. Every post-notification dirty
flag, error and caller continuation checks that original proof, including catches.
A nested projection in the same project supersedes the old continuation even if
it later fails to prepare its rows. A deleted or rebound receiver is never used
for old presentation cleanup. Serial exhaustion refuses further projection.

Picker creation expects only its own prepared retirement epoch and cannot install
a chooser for a reentrant replacement. Selected-file admission finishes staging
and transfers the admitted descriptor before any context/model/retirement signal.
Later presentation failure or receiver replacement does not turn an already
admitted selection/removal into a false result, and old cleanup cannot release a
new chooser's staging. The real core selection policy, immutable source ownership,
file limits and explicit removal semantics remain authoritative. Send likewise
returns its actual admitted row independently of a later presentation failure;
only the original successful response and durable completion acknowledge it.


### Own retirement and original pre-write admission

Ordinary selected-file admission and offline import use the existing context and
workspace cleanup. Their original local continuation is advanced only where
usage_retire actually commits its own account epoch, before usageChanged is
emitted. Every subsequent helper/caller checks that same proof. No epoch delta is
inferred and no post-callback owner is recaptured. Genuine account/input/project,
selection or projection replacement still retires A; offline use needs no login.
The existing sign-in, account-update, sign-out and failure cleanup callers share
this exact transition boundary rather than guessing an increment in a caller.

The first managed transport in this ADR already prepares each input before its
physical write. That prepare callback now checks the original receiver/scope,
input receipt, thread/turn, disclosure and folder before inserting any pending
owner. Each inserted RPC/result/native entry is associated with its actual
original value. Retention, pending-row publication and catch cleanup recheck the
original proof and those entries; cleanup never removes B's ownership or fences
B after an old retention failure. Optional usage may become unavailable without
retiring a healthy request, but a real observer's scope replacement prevents A's
encoded request from being admitted or written. Successful durable response ACK
remains distinct from original row admission and transport uncertainty.

CodexAgent keeps local QObject/process-generation lifetime checks across its
existing optional-usage preemption, deadline, before-write prepare, deferred
flush and request/discard boundaries. Receiver destruction, synchronous failure
or replacement stops the original continuation before another member access.
This does not add a hook or provider method, alter framing, limits, optional-ID
late ownership, physical holding slots or first deadlines, replay a request, or
replace the existing process/account policy. These changes extend the original
ordinary selection and managed transport implementations together.


### Required retirement and original process callbacks

Required account revocation has a different owner from a selected-row
projection. A fatal transport failure, explicit sign-out or required workspace
retirement first records its existing retiring/disconnected admission state,
then carries the original receiver, State, controller, project, generation and
account identity through notifications. A refused Send, picker or same-owner
presentation update cannot cancel that retirement. Real account or project
replacement still ends the old continuation. The ordinary selected-file/import
and before-write paths retain their stricter file, connection, input and
projection identities. Actual admitted selections, message acknowledgements and
Worker final settlement remain factual; retirement does not manufacture an ACK,
erase canonical selected bytes or undo scientific work. The existing retiring
state remains set through the last retirement callback; a nested admitted file
change keeps its factual source update but cannot restart cancellation or create
a second account epoch for that same retiring transport. Once cleanup has ended,
ordinary offline selection remains available. The original fatal explanation is
retained independently of later presentation changes.

The first managed official-agent transport owns the same boundary in both its
helpers and their callers. Read/deadline and receive/preemption loops retain the
original QObject, QProcess and generation through synchronous callbacks before
another map, record or channel access. Started, stderr and finished callbacks,
including catches, cannot fail or detach a replacement transport. Failure
revokes its original maps before notification and publishes its original cause
before process termination can synchronously report exit; after that notification
only the captured process may be stopped. Explicit retirement detaches its old
process first and thereafter cleans up only that guarded process, including its
existing bounded shutdown timer. No new provider operation, public API, capacity,
ID class, deadline, replay, holding slot or scientific mutation is introduced.


### Common publication and factual refusal diagnostics

The common state publisher evaluates each property lazily: its original weak
receiver/State, controller/project, generation, account and admitted-input owner
must still match before a getter, after it and after its signal. A destroyed or
replaced receiver stops the old loop and its catch before any later member read.
Synchronization, model/catalog assignment and their actual continuation/catch
callers use the same rule. Catalog scalar selection commits before model signals,
so a nested explicit selection is not overwritten by the old post-signal path.
A sync already publishes its final state; an old caller does not enter a second
redundant notify after that common publisher returns from a replacement.

A refused input has no new factual-error ownership. For an already disconnected,
blocked official account, ordinary not-admitted Send and known picker/removal
policy refusals preserve the current nonempty factual error rather than replacing
it with a context-consent/busy message during that error's own notification.
This reuses the existing error value, not a new fatal cache or a changed native
error slot. Real new transport/native/calculation/storage/IO failures retain their
existing factual setters and may supersede it. An actually admitted input/source,
explicit Clear and genuine recovery retain their existing clears and owner fences;
no old diagnostic is rebound to another account or Session. Newer factual errors
are not suppressed, and refusal neither acknowledges input nor grants recovery.
The public lastError getter and ordinary signal set are unchanged.

Common history/model publication retains actual committed facts after observer
failure. Lifetime catches suppress only the already-retired original continuation;
an exception in the surviving original scope follows its existing handling. The
existing working-folder commit remains factual while its weak original cleanup
cannot clear a newer owner's transition. No callback ban, extra public hook,
capacity, scientific mutation, provider protocol or error-history store is added.


### Ownership after synchronous publication returns

The common lazy notification and row-model publishers can safely stop after an
observer retires their original receiver. Their normal return does not prove
that a calling bootstrap, control, provider or Worker stack still owns that
receiver. Each actual continuation carries the original weak receiver, State,
binding, account and admitted input proof and checks it before its next member
read, predicate, cleanup, outgoing request or catch. A replacement cannot become
current merely because an inner publisher returned without throwing.

The existing file proof separates admitted input identity from presentation
supersession. `input_current` retains the original receiver/State/controller/
project/generation/account/native-input/file/connection checks; `current` also
requires the original projection serial. Notification keeps its original broader
publication predicate. Strict selection/admission operations retain `current`;
normal protocol/control caller continuations use input identity, so a refused UI
attempt cannot acquire authority or unnecessarily retire a factual result.
Own file retirement updates the same carried proof at the actual epoch increment
before any chooser callback. Own sign-in/logout and offline scientific-context
retirement carry their existing exact account transition through the helper;
there is no guessed delta or recapture of a newer owner. Scientific project/fit
connectors keep their previous required offline cleanup behavior; ordinary
selection context operations retain their stricter presentation predicate.

Bootstrap model and skills settlement, question rejection/answers, cancellation,
turn/item/terminal handling, usage request/update/catches, queued core delivery,
project/fit connectors and their actual failure tails check the caller's original
proof. Queued core work captures that proof at the original event/request boundary,
not after it reaches a later owner. Immediate transport results remain local until
the caller proves scope; a request/answer that already transferred its original
ID is not repeated, relabelled as unwritten or assigned into a replacement.

Native terminal and creation predicates themselves check the weak receiver and
original State before reading ledger/current-call members. Exact original edit-id
and attachment cleanup remains identity-based even when presentation retires;
no later helper/call is cancelled. Permanent native teardown still works when
publication is disabled. Actual completed Worker reports, committed creation/save
and discarded archive facts remain owned by their original local records/latches.
An old continuation cannot invent failure, roll back science, release a newer
owner or abandon the real final-delivery/once boundary to improve presentation.

Session attachment returns also check their original weak State before any
post-bind/post-drain member read or catch. The existing attachment-depth and
explicit deferred-Clear boundary intentionally belongs to the actual Session:
it may reconcile the current canonical history after a real discard, while
independent Session replacement tokens and exact target checks still decide
whether the originating candidate attached. No stale stack force-clears a newer
history or turns a committed discard into failure. A redundant second sync after
successful bind is removed because bind already synchronizes its owned result.

This extends the prior common publication, prepared save/manual-completion and
transport ownership patterns. There is no new observer ban, signal suppression,
callback executor, model API, protocol/deadline/capacity change or error cache.
The factual error/refusal lifetime policy above is unchanged: original causes
survive known refused attempts; genuine new failures, admitted inputs, explicit
Clear and real recovery retain their existing ownership and reset rules.


### Guarded preparation and deadline returns

A successful inner publication return does not grant its caller a new owner.
Send honors the existing thread-preparation result and rechecks its original
strict draft proof before publishing a preparing message. Definite preparation
refusal preserves its actual diagnostic and the unsent draft; it does not claim
that a new conversation is being prepared. Working-folder adoption likewise
stops optional readiness publication after failed preparation while returning
the factual already-committed folder choice.

Clear retains its real archive-discard latch before cancellation or readiness
work. Starting a cancellation deadline can synchronously publish expiration,
so Clear checks the same original input proof before entering its next
settlement helper. An expired, deleted or replaced caller cannot read or update
another owner. Terminal preparation attempts after a committed Clear retain
that committed fact without interpreting preparation refusal as success.

These are the existing guarded-helper and transport-deadline caller rules.
No callback is suppressed, proof recaptured, deadline changed or request
replayed. Original admitted replies, consumed identifiers, native Worker
completion and required offline/destructor retirement remain unchanged.

## Account identity and outgoing-context entry

The original connected account label opens the existing account/usage dialog,
which shows the current connected identity as literal wrapping text and retains
its existing read-only usage refresh. It does not invoke sign-in, approve
outgoing context, capture a draft or alter file/context permissions. The
disconnected Sign in control retains its original connection-dialog entrance;
Send retains the existing required-context approval flow. Sign-out and actual
account changes update the same identity binding, without a stored email copy.


## Account controls, allowance presentation and signed-out sidebar

The original account/usage entrance and Clear action remain the authority for
account operations and conversation retirement. The header now places Clear,
the remaining allowance and the account initial in that order. Account and
Usage use separate compact ordinary dialogs. Only real account email/plan and
actual supplied usage windows are projected; missing identity uses a neutral
icon and missing usage an en dash. The most constrained supplied window sets
the remaining percentage. Its normal foreground changes to the theme warning
color below 25 percent remaining and error color below 5; bar fill still shows
the actual used fraction. Stale observations are explicitly labeled. Opening
Usage invokes the existing read-only refresh; opening Account grants no project
or context authority. The eye control in the original composer toolbar toggles
the existing Show actions setting, with a checked accent and accessible state.

Until actual sign-in readiness, the original chat/composer and ordinary
sidebar controls are hidden, while their draft/history models remain intact.
The empty area uses the existing scientific empty-state typography and exact
text “Sign in to use the assistant”. The single header Sign in entrance remains;
authentication Cancel, required retiring-work Stop and sidebar Close remain
usable. Signed-out drop input and stale authenticated file-choice completion
are refused at the original file-intent boundary. Ordinary offline scientific
file selection keeps its existing separate manual entrance. Global Preferences
remains available. Real account/project/input retirement, matching ACK/history
retention, Clear, native validation, Undo and Worker semantics are unchanged.

These controls use actual object identity and current geometry. No coordinates
or layout instructions belong in skill guidance. Existing working-folder and
context-consent behavior remains separate; these presentation changes do not
implement a new folder grant or conversation-continuity policy.


### One composer model and effort chooser

The original separate model/effort combos used the provider model Rows, current
selection and existing guarded setters. A single light rounded pill now shows
the same actual model and a visually muted effort label. Its ordinary bounded
popup contains two single-selection DataTables with shared radio/label widths.
Model selection refreshes the original dependent effort choices and keeps the
popup open; effort selection returns to the same pill. Default is still the
original empty provider-default token, never an invented model or quota.
Actual unavailable models remain disabled. Keyboard and pointer activation use
the same original setters; busy/auth/current assistant and popup-intent checks
prevent an old control from affecting a replacement. Popup retirement and queued
focus retain the same captured intent; Escape/outside close returns focus only
to the original eligible control. No hidden compatibility combos remain.

Footer Add, eye and history arrows use consistent circular light theme fills;
Send and Stop retain their stronger original styling and behavior. Eye checked
state retains the accent. No catalog/backend/session/scientific policy changes.


Each chooser table uses its own exclusive ButtonGroup, so genuine mouse/Space
activation cannot clear the current radio. After an original setter returns,
the same popup intent reconciles its instantiated group's checked button to
the actual selected model/effort; refused and same-value setters cannot leave
a false selection. Delegate creation retains its authoritative value binding.
Rows.text is explicitly interpreted as the string “true” for availability in
both focus traversal and choice admission; disabled middle rows are skipped.
The pill's real Return/Enter press calls the same guarded opener once, consumes
auto-repeat and release, and leaves native Space/pointer activation unchanged.


### Sign-in entry preserves the original control and divider

The disconnected header entry retires only the pending context-send intent and
opens the existing AssistantConnectionDialog through its declared API. It writes
no undeclared dialog property. Account access remains the separate authenticated
branch, and genuine dialog accept/reject and context-approved send handling stay
unchanged. Its custom label delegates foreground color to the original Button
contract, including hover, pressed and disabled states. The passive sidebar edge
paints above both signed-out and authenticated backgrounds on either sidebar
side; it adds no input surface or changed button geometry.


### Robot head shares the existing work presentation

The shared sidebar/status work cue chooses once per visible appearance among the
existing ring, branded mark and the same icon-font robot head used by the app
bar. Its text and accessible name are "AI working...". The robot and branded mark
use the existing elastic logo rotation; the ring retains its linear rotation.
Actual agent activity with no pending question or plan remains authoritative.
Hidden cues and reduced motion stop and reset the glyph rotation.

The app-bar assistant button animates only its displayed robot content under the
same work predicate, while visible and enabled. Its selected columns glyph stays
still. The original ToolButton content, hover/theme state, hit target, focus,
accessible purpose and sidebar action remain intact; the button itself never
rotates. Ending work, input-required state, hidden/disabled control, selected
columns or reduced motion stops and resets the content rotation. No additional
backend activity state or filesystem authority is introduced.


The signed-out assistant prompt uses the original shared EmptyStateLabel, as the
existing chart empty states do, instead of copying its font/disabled/wrapping
properties. Its exact sign-in text, centered placement, bounded width and
signed-out ownership remain. The shared component supplies the original WordWrap
and visual style; no separate empty-state implementation or new registration is
introduced. The existing sign-in entry, native foreground and passive divider
correction remain intact.


### Brief sign-in and context disclosure

The existing connection/context dialog presents a few short human-readable items
first. Its existing Details toggle reveals the complete current capability and
sharing explanation plus the unchanged selectable, read-only exact context.
Current runtime access can expose measurements and permit workspace writes; that
limitation is stated upfront, with no promise that measurements stay local or
that model tools are Edi-only. This presentation change does not enforce a new
privacy or filesystem policy. Stale claims that native Save is unavailable are
removed; actual operation outcomes remain authoritative.

The separate Inspect outgoing context link is removed. Original Send still opens
the same dialog when context approval is needed, and only its original accepted
context signal can resume the exact captured draft once. Authentication,
connectionAttempt, current-owner/account/conversation checks, refusal, Cancel,
IME, ACK and native save/science behavior are unchanged. No second approval
window or scientific form is added.


### Account, allowance and model chooser use the ordinary dialog layout

The connected header initial is inside a fixed square native button with a
contrasting circular background, native foreground hover/pressed/disabled state
and focus ring. The account card uses the actual email and supplied plan (initial
capitalization, muted), tight identity spacing and a separate, more distant
icon-font Sign out action. The supported account response supplies email/planType
only: no full personal name is invented or derived from an address.

Model/effort uses the original app-centered AppDialog, standard margins/colors
and two side-by-side original DataTables. Shared measured radio/label columns
show full labels and all rows at natural size; only actual viewport overflow
scrolls. Keyboard focus reveals its real selector in that viewport. Existing
selection, unavailable-row skip, genuine inputs, owner/retirement and Escape
semantics remain. The composer pill has one measured text-space between model
and muted effort. Fixed circular action rectangles and the same layout spacing
keep previous/next/visible Stop/Send edge gaps equal; the width budget counts
whichever Stop/Send controls are actually visible.

Usage has only Session limit and Weekly allowance rows, actual percent used,
rounded accent bars and relative reset. The supported five-hour and seven-day
windows map by reported duration, never primary/secondary position. The most
constrained matching actual window is selected across buckets. Missing windows
show Unavailable, stale snapshots Last known. Other durations remain actual
constraints in the header's all-window minimum and its accessible tooltip,
without inventing a Session row. Bars turn orange below25 percent remaining and
red below5; otherwise use the accent. Reset labels derive only from supplied
reset time, updated once per minute only while the authenticated dialog is
visible. No context-occupancy, credits, balance, raw timestamp or duplicated
technical summary is presented. Account epochs, refresh-on-open and quota
observations remain original backend facts.

### Used allowance and native header presentation

The header and allowance details consistently display the actual supplied percent used, including values above 100; threshold colors still use the remaining allowance. Missing and stale observations remain explicit, and the most constraining supplied window governs the header. The clear glyph matches the composer action glyph size while retaining its full button target. Assistant action backgrounds use neutral keyboard-focus cues rather than blue outlines; the Show actions eye retains its checked glyph accent without a checked outline. The Assistant title strip uses the original Main/Extra TabButton resting `contentBackground` semantic color, separately from the body and passive divider.

### Human details and exact technical context

The outgoing-context dialog's Show details/Hide details link uses the native accent color in both states. Human-readable disclosure appears first. The exact current context remains unmodified, read-only and selectable, initially collapsed behind a separate Show technical data/Hide technical data link within Details. Closing Details closes that technical presentation too. These controls only change disclosure presentation; authentication, approval, cancellation and the current data-exposure warning retain their original behavior.

### Avatar, allowance tracks and native table extents

The avatar circle is smaller than its unchanged native button target, with a contrasting resting fill and a permanent border slightly darker than that fill. Allowance rows exist only for supplied Session/Weekly windows; when neither is supplied a single compact message explains their absence. The rounded track is always outlined, with its colored fraction inset inside the border. Relative minutes include a separating space. Sign out follows the first native SideBarButton row's vertical-center icon/text convention and keeps the same left edge as account identity.

The chooser accounts for the original table border using actual native top/bottom margins and positions the original attached scrollbars using the standard native ScrollView geometry and reserves their measured implicit width/height only when the application viewport requires them. Its natural dialog extent includes those real dimensions, bounded only by the application viewport; scrollbars do not overlay the last row or the right edge. Column widths, row heights and fonts remain the original native values.

Composer actions and the model pill have no border in any state; keyboard focus uses the existing neutral hover fill, and Show actions keeps its active glyph accent. The avatar and allowance track retain their separately requested faint outlines.

### Native border and chooser margin balance

The Usage track uses the existing application `appBorder` token in both palettes, retaining its thin rounded outline and inset actual fill. The chooser's natural width includes only content and its original side padding, without an invisible scrollbar gutter. Bottom padding matches the original native side-padding dimension. The same native scrollbars occupy those outer padding areas only for actual overflow; the table viewport remains clipped, so neither bar covers a row or steals the right edge. This removes the earlier cross-axis extent calculation while preserving native fonts, border-safe table rows, controls and currentness.

### Continuous reply-table paint and contained status activity

The original report table uses restrained horizontal rules, left-aligned cells and header/even-row shading. Replies keep that convention with additional space around and inside cells. Qt Quick's TextEdit does not paint complete QTextTable cell backgrounds: its native text nodes can shade only individual text runs. The existing AssistantMarkdown helper therefore also supplies passive scene-graph rectangles behind the same editor, using its single MarkdownNoHTML QTextDocument and native layout coordinates. It does not parse another representation, insert source characters, accept HTML or fetch resources. Full rows are shaded continuously, with a thin header rule and no vertical separators. Native cell padding remains visible at the outside edges, and decoration is contained within the editor viewport. Selection, link positions and copied semantic text remain the original editor's.

Table decorations admit their old/new retained rectangle buffers and maximum live scene-graph rectangle geometry against the existing UI-history capacity before allocation. Presentation overflow/failure preserves the complete original as literal text. Layout/content, width, font, palette and document changes refresh only the original document's presentation; weak receiver/document and presentation-revision checks abandon superseded callbacks. No full-message raster image or additional resource loader is retained.

The inline robot uses the bundled icon font's actual tight ink rectangle, including its bearings. Its centered ink diagonal fits the original icon slot at every rotation; the existing other two symbols, animation, reduced-motion reset and steady activity label remain. The original visible-action Stop moves to the status activity's right side, using the fit-status glyph size and native cancel handler. Its original widget identity and manual-takeover/press-release slot persist. The whole activity plus Stop participates in status width accounting and keeps the bar reachable on Home when needed; chat Stop and independent fit controls retain their original behavior.

### Ready consent submission and bounded status presentation

A Send-triggered approval retains one original composer receipt through asynchronous thread preparation. The receipt includes the actual text and IME revision, conversation owner, selected-file revision, current project, account and model/effort. Approval marks that receipt eligible; submission waits for the authenticated backend to become idle with the same context. A transient Connecting label is presentation, not account replacement. Cancel, conversation/account/project/input/model changes, newer text including identical retyping, or an actual manual submission retire the original pending send. The receipt is consumed before the automatic submission, and only the original admitted row's actual acknowledgment clears text/chips. No failed or admitted send is replayed by readiness notifications.

The status bar reserves the assistant activity and Stop target against its own viewport before allocating fit space. Complete original fit values, result control and progress remain in a native horizontally scrollable viewport when they exceed the remaining width. The original Stop receiver stays at the bar's right edge during chat presentation changes, manual takeover and its native press/release. Existing fit controls and actual value text are retained.

Table row decoration follows the native cell content origins and cell padding once; table blocks have zero additional vertical margins. Each next native row origin supplies the preceding row's shared boundary, including native border rounding. Wrapped lines expand their own row; shaded and unshaded single-line rows have the same ordinary cell padding. The same editor, semantic source/copy, resource restrictions and selection/link coordinates remain authoritative. GUI preparation failure still attempts complete literal text. Failure of owned scene-graph allocations instead deletes the complete partial owned decoration tree and returns no decoration, leaving the original editor intact; the rendering callback never accesses its GUI-thread document. The header keeps the last known actual used percentage during refresh without a stale suffix; internal freshness and missing/error handling remain.

## One project folder and application-owned IO

The separate assistant folder links/caption are removed with their backend grant,
writable-root, raw-staging and provider-result-writer dependencies. The existing
Project Create/Save destination controls are the only destination UI. Account
entry remains the account/usage dialog; it does not grant a folder. Current saved
project IO is Edi's owned native Save operation, not a reusable model write grant.
The required short Send disclosure continues to preserve the original draft,
revision/IME and attachment receipt through backend readiness and one actual ACK.
It accurately says that stock read-only execution can still expose general reads,
tools and measurement data; optional exact technical context remains available.

The original statusBar.project item now opens a standard application dialog with
the full selectable current project folder and native Copy/Open actions. Unsaved
projects have no path action. Original owner/path replacement retires this
presentation; a matching pathname alone never grants access. No separate AI path
or new destination wizard is introduced. Existing working/Stop placement,
viewport reservation, native table geometry and stable used-usage text remain
unchanged by this folder flow.

### Status folder presentation ownership

The original project-folder dialog installs one complete owner/path presentation
record. Its derived public owner/path bindings can notify ordinary observers;
no old opener writes another field after those callbacks. Opening, Copy and Open
folder each retain that exact record and check receiver lifetime, Session owner,
path and presentation identity before continuing. A reentrant new owner, a new
opening for the same owner/path or destruction supersedes the old opener. The
same standard dialog and unsaved behavior remain; no callbacks are suppressed and
no old opener restores or reopens a newer presentation.

### Application Preferences skill sources

The first manual door is the existing application Preferences dialog (ADR-0017 §12), with the original LinkedStructureGroup/DataTable add, enable and remove conventions. AI assistance contains that same table pattern and a genuine FolderDialog. EasyDiffraction is the built-in source's user-facing name; its repository/resource path is not presented. It can be disabled but not deleted. A local row represents the exact selected package/collection and physical directory identity. Its opaque ID is independent of row position. There is no new chat skill browser, science form, project folder grant or provider capability.

Preferences remains available without assistant sign-in. Its controls refuse changes while the assistant owns active work. A native row captures its original owner, opaque ID and configuration revision on press; an intervening replacement/configuration update cannot transfer that click to another row or owner. Folder completion consumes an original one-shot owner/account/project/input/configuration receipt before callbacks. Cancel, project/account/input retirement and dialog destruction retire only that chooser. Closing Preferences also retires its original outstanding chooser. The ordinary global settings store persists enabled source rows; opening Preferences explicitly reloads them. Reading an unchanged configuration does not change approval. Missing settings explicitly default to the built-in source, whereas unreadable, malformed, oversized or failed-write settings are assistant-invalid and never fall back to built-in instructions. That error cannot unwind ordinary Session construction or project replacement. Explicit reload/source correction can recover. All-disabled is a valid empty instruction catalog.

The current chat/header/composer, account/usage, palette, original scientific controls, Save, input and folder-free read-only lifecycle remain the existing implementation. This feature adds instruction-source preferences, not filesystem write authority or a privacy boundary against the runtime's other existing tools. Local capture uses the existing Unix native filesystem boundary; unsupported local platforms refuse. Injected restricted compatibility controllers retain their separate existing behavior. Native UI, persistence faults, provider discovery, race/fault injection and C++/Qt qualification require the actual consumer; source/grammar checks do not certify those intervals.

### Source-dependent consent publication

The original Send wrapper treats the consent getter as callback-capable. Each
branch checks its captured weak receiver, State, project/controller, account,
input and presentation proof before any refusal, member access or notification
after that getter. A changed source can retire the original offer; it cannot
transfer the original draft's Send authority to its replacement.

A factual source reload, invalid configuration or committed edit updates the
existing context-preview notifier synchronously through the original guarded
context lifecycle. Its continuation carries only that helper's own account
transition. The same good configuration keeps its approval; actual replacement
abandons old publication. Neither a timer nor a later archive render supplies
the disclosure bond. A first source load with no prior execution context
publishes the initial offer without retiring an unrelated account.

The existing composer and pending-send receipt functions also recheck their
original assistant/project, draft revision (including newer identical input),
file revision, model/effort and account after source-dependent getters. Offer
creation reuses that captured context rather than obtaining replacement values
mid-construction. The original dialog's accepted continuation retains its
existing disclosed-context object identity across sign-in, failure presentation
and the consent getter before emitting approval. Cancel, the real ACK and
consume-before-submit ordering remain unchanged; no new visual control or
public receipt API is introduced.

Receipt predicates can synchronously publish source changes and return failure
because their original component was retired. Every outer caller saves that
result and checks its captured component and assistant before any subsequent
property access, signal, cleanup or dialog opener, including false/null returns.
A failed draft capture emits no submission signal. A live old pending intent
may be retired only while it is still the same intent; it cannot clear its
replacement. The original consume-before-submit order also checks its receiver
and empty slot after the notifying property change. These checks extend the
existing consent receipt, with no new signal, control or callback suppression.


### Vertical-only assistant scrolling

The connection disclosure, its failure and wrapped technical-data views, and
the equivalent wrapped account, usage, skills, plan, attachment and composer
views explicitly disable horizontal scrollbars. Their content follows the
available width and retains native vertical scrolling; an unused horizontal
track must not intercept the final row's controls. This follows the existing
assistant message views. The model/effort chooser and fit-status viewport keep
their intentional horizontal scrolling. Original activation, focus, selection,
authentication and pending-send receipt behavior remain unchanged.


### Dedicated runtime ceiling and closed outgoing scientific roles

The first runtime integration used the complete official app-server package and its general tool/instruction discovery. The Edi-only flavour extends that same pinned app-server target and acquisition; it does not add an executor, protocol wrapper or second serializer. A narrow product source patch supplies immutable ToolPolicy and isolated-session attachments at the common thread constructor, forces Direct exposure and compares the final parsed nonempty advertised catalogue to both the captured request and actual dispatch definitions. The original dispatch guard precedes hooks/handlers. Startup/turn/config/parent/history entrances cannot relax this ceiling; the original final sampling boundary rechecks actual schemas/settings and refuses implicit tool declarations or media. The dedicated initial/refreshed context route omits inherited repository/global/plugin/environment/permission-root fragments while retaining explicit app-captured enabled task guidance. Model/effort choices keep their existing meaning; a changed choice establishes a fresh verified thread.

The explicit edi.runtime-policy/1 proof bonds the pinned source-patch identity, package flavour, actual thread/admitted turn, exact original settings and parsed catalogue. The product CMake-generated expected patch digest is independent of server-supplied proof. Real target archive/executable hashes remain separate build/qualification facts; an unbuilt archive cannot be enabled. Official account/authentication and app-owned local cache/session/input/Save IO remain distinct from model authority. Packaged unused executables do not become advertised or reachable tools.

Earlier raw read_selected_file and complete unprojected context descriptions are superseded for the dedicated runtime. The original outgoing context/native-response entrances use one closed typed role projector before Qt JSON encoding; top-level wire objects identify edi.assistant.outgoing/1. Native parameter values/SUs/units, current calculation/fit state, finite objectives and reader counts, opaque input IDs and factual applied/partial/committed/reopened/active/once outcomes survive. Raw measurement arrays/images/snippets/filenames/filesystem paths/content hashes/arbitrary native error text do not. Fixed error codes replace errors; native originals and local recovery receipts remain exact. Genuine user text and deliberately enabled captured SKILL instructions remain intentional outgoing roles, never new file/write/network grants. UTF8, measured UTF16 and construction owners use the existing joint VM/transport reservation policy before growth; no capacity increase, fixed headroom or truncation is introduced.

Enabling a dedicated package requires separate genuine package/app positive and forbidden-negative/sentinel qualification, including real native scientific and Save outcomes. The stock build retains its candid general-tools/raw-exposure warning until that proof exists; source authoring, a requested read-only setting or a model's text cannot establish enforcement. The existing GUI, nine vertical-only ScrollView policies, consent/draft/ACK lifecycle, Preferences sources and original scientific controls are preserved.


### Dedicated runtime: final wire and bounded ownership

The dedicated flavour validates the original final HTTP and WebSocket request after conversion, not merely a typed prompt. Regular Responses carries the exact admitted nonempty function catalogue in tools; Responses-Lite carries precisely one original developer AdditionalTools item whose parsed function catalogue is identical. Other namespaces, duplicates, extras, deferred/hidden callables, unknown/media/agent/compaction history and foreign settings refuse before inference. The same captured ceiling already binds the reachable original router and pre-effect dispatch. No model or effort is substituted to make an unsupported request pass. Dedicated WebSocket requests carry the full current admitted history and catalogue rather than an implicit previous-response history delta. Original authenticated account routing/residency and protocol headers remain separate from scientific context; arbitrary configured headers, project/workspace metadata and request contributors are not forwarded to inference.

The app verifies proof requestedTools against the digest of the actual original thread/start catalogue, avoiding a new schema-tree construction during incoming proof handling. Its 32-byte retained identity, actual proof replacement, compact encoding and temporary digest use the existing joint owner budget. Fixed proof-field/name views use bounded stack storage. Original before-write and projection receipts still guard settings and owner transitions. Serialized wire, LF-appended line, old/new deferred buffers and the actual QProcess queue are admitted together with current app/parsed/unread roles before growth and transferred only on the original process/generation. No capacity, fixed headroom, live-outcome eviction or retry is introduced.

Dedicated model compaction, memory summarization and realtime are not supported: their original common entrances refuse before hooks, history replacement or a separate model request. A long dedicated conversation may therefore reach a factual capacity refusal; the user can explicitly Clear or begin a new conversation. It is never silently compacted/truncated, restarted or replayed. This is a scoped runtime limitation, not an alternate compaction engine. Existing stock mode and the candid current exposure warning remain until a real dedicated package and app pass independent enforcement checks.


### Declared instructions and transport ownership through retirement

The dedicated instruction exception selects only each immutable declaration's exact id/SKILL.md entry with the captured SHA-256 identity. Both instruction sizing and construction use that selection, as does the original captured-skill catalogue. The wider local package inventory, resources and fingerprint remain useful for local currentness/staging; resource text or measurement files do not become instructions merely by residing beside SKILL.md. Disabled/all-disabled sources still contribute no configured instruction body. Declared text/digest/UTF-16 and encoding owners are admitted through the existing joint budget.

The original transport applies the same joint remaining-output view before stdout/stderr chunk reads, replacement assembly, delimiter splitting and parsed-record construction. Local chunks, old/new assembly, raw record and parsed representation keep their separate encoded-byte roles through callbacks and exceptions. Ordinary wire/event/depth/record caps and exact original record bytes remain; no raw diagnostic text becomes an outgoing error. One active stdout delivery drains subsequent available bytes after callbacks instead of recursively replacing its current record charge.

Authority retirement does not erase factual stack ownership. Original read/write/request/deferred and diagnostic frame counters settle only when their actual scopes return, even after a generation changes. A replacement start refuses while those frames or any retained role remain, and while the original detached QProcess has not actually been destroyed. No timeout, supervisor, automatic retry or weaker owner fence substitutes for that lifetime fact. Old queues/frames can therefore temporarily make reconnect or new growth unavailable; they cannot donate room to a replacement before destruction. Once the old owners are gone, the existing explicit connection flow can start normally. Original uncertainty, admitted-input/ACK/once and scientific/Save facts are unchanged.


### Instruction decoding and terminal transport delivery

Captured declared instruction construction admits the decoded UTF-16 body beside the already reserved final instruction buffer and its encoded role. The decode reservation is acquired before conversion and outlives the decoded QString, including allocation failure. Exact declaration identity, text, Unicode validation and all existing limits remain unchanged.

The same original stdout reader owns delivery through nested process completion. A finished notification records EOF only for its captured process and generation; if delivery is active, it leaves that reader to drain complete assembled records and final buffered bytes. Only after those local owners settle does the original reader apply the existing unfinished-work interruption and detach that process. Earlier genuine failure, cancellation, retirement or destruction wins; no request is replayed, no final reply is invented and process death is not success. There is no added timer or grace period.


### Pinned archive license alias

The existing offline runtime builder preserves the pinned upstream source's single bubblewrap LICENSE alias as a regular copied file. It resolves only that exact archive entry to the pinned same-directory COPYING regular member, verifies its declared size, content identity and mode, and copies the target bytes and mode at the alias path. No filesystem symlink is created or followed. Duplicate normalized member identities and unknown, absolute, escaping, special, unresolved or chained/cyclic links are refused. Both original source and platform-package entrances use the same extractor; the exception is source-only and a new owned extraction root prevents existing filesystem nodes from redirecting writes. This compatibility correction does not establish compiler, package or enforcement qualification.


### Pinned release workspace lock versions

The pinned upstream release workflow documents that a release tag updates the workspace manifest version without rewriting local package versions in Cargo.lock. The offline builder reconciles only that exact release mismatch before applying its source patch and running the original frozen build. It requires the pinned original lock identity, derives all local package names and inherited versions from the original workspace members and path dependencies, and changes only their version fields from 0.0.0 to 0.162.1. A complete parsed comparison preserves every external dependency version, source, revision, checksum, edge and other metadata; unexpected input or any wider delta refuses without dependency resolution or fallback.

The original lock bytes are retained beside the normalized lock as Cargo.lock.original. The separate generated build-facts document records both hashes and byte counts, the actual workspace version and affected local package names. Archive pins remain original archive identities; normalized lock bytes are never described as unchanged upstream input. No Cargo update/fetch or dependency selection is performed by this normalization helper, and compilation remains cargo build --frozen. This source/preparation correction does not establish a compiled package or runtime enforcement.


### Visible parameter arrays retain one original call

Parameter/free arrays extend the original NativeWidget scalar adapter and the relation/background factual-sequence pattern. The existing whole-array native preparation is validated and released before visible input; the prepared atomic edit is never executed in Show actions. One original call owns the typed bounded cursor, per-entry weak parameter/native identity and current editor. An initially unavailable original route refuses before any scientific input. Each entry rechecks the original owner, account, request, revision and fresh control membership; no-op entries settle before navigation/filtering/input. Existing final-event native validation and per-change Undo remain the only scientific effect path.

The cursor's settled prefix is separate from its cumulative factual-applied and current uncertain latches. A current applied receipt survives Stop/publication callbacks even before the helper completion arrives. Confirmed entries advance only after actual consumed/applied/published readback and original refresh; uncertain entries are never replayed. The original RPC/record/ACK and objective presentation settle once for the whole request. Visible complete/partial facts never imply GUI atomicity or rollback, and settled no-ops do not imply a scientific write.

The existing joint VM/transport budget admits the typed container and decoded path roles before growth, one current editor/filter/numeric conversion and original helper restoration, and the original maximum result/row/response variants before input. A weak frame registry continues to count actual retired callback-owned cursors, call records, receipts and outcomes until their last owner returns; resetting the active widget is not release. The registry owns no callback or project. Old/new results and helper delivery remain inclusive under the existing caps; there is no donated budget, added headroom, whole-project copy per entry or new resource framework. Original source-policy, approved skills, native scientific data and Save semantics are unchanged.


### Current original parameter binding before visible admission

A selected block name and a cached QObject path are not a live control binding. The original ProjectViewModel's sole ParameterRegistry current maps/items and original model parameter roles are authoritative; deferred-deletion children are never lookup candidates. Instrument additionally requires its original selected native experiment/model and usedByProfile visibility role, including the retained-free-but-inert case. Cell requires the actual selected native structure and exact six Cell model/member pairs. Analysis requires the actual current table parameter role, preserving its scan scope. No fallback, profile/selection change or extra input is inferred.

The same pinned registry/model/ParameterItem/native member/path is checked before scalar/array no-op, each currentness continuation and the genuine final event/readback. The original creation child's scalar parameter path uses this same entrance. An initially unavailable later array entry refuses the whole request before earlier inputs; a later retired binding stops with the original factual partial/uncertain result. Original scalar result shape, atomic normal mode, per-change visible Undo, old-owner once/ACK and retained callback budgets are preserved. Added weak identities are part of the existing typed frame size, and scalar path/callback backing uses the same prospective and retired-frame accounting as arrays.


### Catalogue selection before thread creation

The original catalogue selector also serves the official runtime's initial and replacement-thread bootstrap. After the complete validated model catalogue and current account are available, the common stock/dedicated thread-start entrance resolves the existing saved, explicit or offered fallback choice before requesting its effective default effort. This internal bootstrap does not publish ready or enable busy user setters. It requires the original account/owner projection, exact current catalogue, connecting state and no live thread or other active-operation cause; these are rechecked after preference loading before selection can mutate or thread creation can continue.

The original hidden/unavailable filtering and model/effort compatibility rules remain shared with ready-state selection. A valid saved choice restores as before; an unsupported or unavailable saved choice retains its saved value and warning while the ordinary offered fallback is used. Only a genuine explicit ready-state choice persists a preference. No model/effort literal, permission, catalogue validation or skill/consent/policy check is bypassed.


### Inline working ink and transient control presentation

The shared working cue extends the original IconLine/DigitText baseline and
native tight-ink convention. Its text-ink centre aligns all three symbols;
asymmetric label padding contains the original rotating slot above and below
that centre. The bundled robot ink is scaled by its diagonal to the circular
logo's maximum paint width, including during rotation. The existing symbols,
font, animation, clipping, visibility and reduced-motion reset remain shared.

Usage keeps the last valid same-account indicators while refreshing without a
transient cached-status label. Freshness/account retirement and missing values
still belong to the existing usage state. Composer action backgrounds use the
original hover, pressed and keyboard visual-focus states; restoring ordinary
pointer focus after closing the model chooser does not keep it highlighted.
Keyboard navigation and the existing chooser ownership are unchanged.


### Activity purposes and local technical copy

The original activity disclosure uses its full bounded retained purpose on one
elided line across the sidebar. Existing operation and recorded-status icons
replace the caption's category/status words and leading chevron; the whole
native checkable button still expands the original details with keyboard and
accessible checked state. A command's structured action metadata can supply an
actual purpose, never guessed shell semantics. Its recorded command/public
status agreement still controls whether completion is known. Native uncertain
outcomes are not presented as confirmed success.

The internal dynamicToolCall type is not an ordinary explanation. Its unchanged
canonical payload stays in the indented Technical details. A standard adjacent
Copy action uses the existing local ApplicationInfo clipboard door to copy that
whole current payload even with technical text collapsed, then briefly shows
the native check glyph/Copied label. Original row/payload identity is checked
around clipboard callbacks; retirement or replacement cannot retain feedback
for another row. No automatic copy, provider send, parser or retained science
change is introduced. Original literal command/output and selection stay exact.

The common activity explanation distinguishes public activity status from a
native unconfirmed or applied-unconfirmed scientific outcome. Both tooltip and
accessible name explicitly retain that uncertainty; an unknown activity status
is not promoted to success. Command retained/public disagreement continues to
use its original truthful explanation. The native activity Button owns the same
styled hover tooltip as the original ToolButton, honoring the application-wide
show-tooltips preference; attaching explanation text alone is not hover delivery.


### Approval recovery keeps its original offer

The original connection dialog compares exact captured outgoing-context text,
with its original component/account/project/model/effort and opening/retirement
owner, before and after callback-capable getters and approval. Parsed JSON is a
presentation object, not the offer identity: the shared context notification also
announces consent-required changes, so successful approval may rebuild that
object without changing the offered bytes. Only the still-owned original offer
can emit approval; the existing composer receipt consumes the original draft
before its single submission when backend readiness arrives. Clear, replacement,
changed draft/files/model/account, IME and Cancel retain their original fences.

A retained native/history outcome remains consent-required and separately blocks
approval. The original composer keeps its draft and existing inspection/Clear
diagnostic instead of reopening an approval which cannot settle that outcome.
An already-open original approval becomes unavailable while that fence holds;
the public send entrance preserves the same retention cause. Explicit Clear is
still the only discard door; this does not retry native work or claim that an
uncertain import was rolled back or completed.

The original Panel binds every offer to the dialog generation before its first
callback-capable draft capture, including a same-visible presentation and an
entering/reopened popup. The explicit presentation entrance owns that token;
the later opened transition does not mint a replacement. Acceptance publishes
its captured token, and Panel checks that exact original intent/token before
marking it approved. A current newer identical draft can never inherit an old
acceptance. The genuine accepted close does not retire its pending once receipt.


### Native recipe refusals stay typed and actionable

The existing explicit creation recipe and native reader remain authoritative in
both modes. In particular its line-segment background requires at least two
actual supplied anchors; no background or scientific default is invented.
Structural/text/number/array/profile recipe validation before native admission
uses a small app-owned typed refusal. The original reply carries only closed
field/reason identifiers and, for array bounds, the existing minimum or maximum.
The same outgoing projection validates those identifiers before construction.
It still excludes arbitrary messages, exception what(), paths and raw data.
The original generic refused code is retained; a malformed recipe is not an
admitted scientific edit and can be corrected with a fresh lawful request.

This does not attribute or weaken a separate retained-native-outcome fence.
After scientific work or uncertain publication, the original once-owned result,
inspection/Stop/Clear and no-automatic-replay rules remain authoritative.


### Live standard-footer sizing and shared activity ink

The connection dialog keeps the original EaElements.DialogButtonBox, its native
standard Ok/Cancel buttons, role dispatch and app styling. As in the original
WarningsDialog local footer override, only the owning dialog specializes its
footer. The original horizontal ListView measures its implicit width from the
button box's live natural contentWidth instead of the view's cached contentWidth.
Thus the standard Sign in with ChatGPT / Approve context label can change without
right-aligning its real action outside the popup. No hit target, synthetic accept,
extra delay or consent/offer behavior is introduced.

The shared working cue uses the actual Label baseline plus native tight text ink,
including the current label alignment/padding. The robot is fitted by its current
rotated natural ink bounds to the same fixed slot as the existing circular logo,
instead of permanently shrinking its upright ink by the full diagonal. Slot,
text placement, clipping, all three variants, rotation/reset and reduced-motion
guards remain shared between sidebar and status bar. Native rendered acceptance
is separate from these source changes.

A command activity still prefers an explicit purpose and validated structured
read/list/search actions. An unknown structured action or final command fallback
can show its retained literal command on the existing one-line, right-elided row.
It is display only: no shell parsing/execution or inferred purpose/outcome. With
no literal command it says Run command. Original status explanation, full literal
technical copy and canonical payload remain unchanged.


### Direct activity disclosure

The activity header now orders the truthful status icon before the type icon.
Every activity has its existing native main disclosure and a separate small,
muted native copy action at the far right, including while details are collapsed.
The copy glyph uses the type icon font size/color and original current-row,
canonical-payload clipboard guard and Copied feedback. Keyboard/disclosure and
uncertainty explanations remain native and truthful.

The main disclosure directly opens all retained details in one full-width,
rounded surface using the existing user-message contentBackground, radius and
padding conventions. One bounded vertical viewport contains the literal command,
working directory/output when applicable, readable activity/decision information
and the full selectable retained JSON. There is no secondary Technical details
or Original payload toggle. This supersedes the older nested technical layout;
no canonical payload or selectable literal is truncated or interpreted as HTML.

Sent attachment history is a read-only snapshot of the original filename and
byte count. Its former future-scope removal action and now-unused selection
listeners are removed. Pending composer attachment removal and explicit Clear
retain their existing selected-ID/grant behavior; history never revokes access.

The current Edi notice is an inline conversation ListView footer, with Edi as its
visible author and the exact current lastError in selectable plain text. It
replaces the former fixed label above the composer. It is not an assistant
message, retained history write or inference input; repeated updates replace the
one current notice, and the backend alone clears it. Existing tail-follow and
user scroll behavior apply. The same existing plan, question, trial and working controls also live in that
inline footer; their handlers, IDs and backend ownership are unchanged. The
composer area contains inputs and its separator only. The hidden-chat statusbar
working indicator is unchanged.


### Compact activity header extent

The activity copy action retains the original native ToolButton and icon/hover/
clipboard/ownership behavior, but uses a square natural extent equal to the
existing main disclosure's implicit text-line height. The original ToolButton
background has a toolbar-height implicit size even when hidden; that default
must not enlarge a compact conversation header. The real copy target fits the
same visible row rather than overlapping adjacent history. Existing message and
ListView spacing, details surface and glyph sizing are unchanged.


### Working cue capital alignment

The shared working cue follows the first IconLine convention: its vertical icon
anchor is the capital-H ink centre at the actual Label baseline, rather than the
whole working phrase's descender-inclusive bounds. TextMetrics uses that Label's
renderType, as required for matching the drawn text. Qt's Text baseline already
includes top padding and vertical alignment; no additional baseline offset is
added. The original padding containment policy re-evaluates against the capital
anchor, while accepted icon extent, robot ink/size/rotation fit, all animations,
clipping and both callers are unchanged. This source correction is not native
pixel acceptance.

Prior art: [IconLine.qml](../../../app/qml/Components/IconLine.qml), capital ink
centre and actual glyph baseline; [Qt Text updateBaseline](https://github.com/qt/qtdeclarative/blob/v6.11.2/src/quick/items/qquicktext.cpp#L382)
and [TextMetrics renderType](https://doc.qt.io/qt-6/qml-qtquick-textmetrics.html#renderType-prop).


### Hover and keyboard history copy

Activity copy keeps its compact native line-height target and permanent layout
slot, revealing its glyph on that line's passive hover or native keyboard/accessibility
focus. Opacity changes do not alter header width or height. The native copy action
uses TabFocus without stealing mouse focus/selection; unrevealed activations do
not write the clipboard. Main disclosure and canonical-payload copy are unchanged.

Sent user bubbles reserve a narrow right rail permanently, with the same small
muted copy glyph outside the top-right of the bubble and ordinary margins. The
passive hover region covers that bubble and rail, excluding unrelated empty
history space. The rail does not appear/disappear in layout on hover. A genuine
activation copies the exact immutable sent text once, including whitespace; it
does not export JSON, attachment bytes or an assistant response. Captured row,
text, payload, owner and lifetime are rechecked around the native clipboard call.
Feedback resets on replacement/reuse/text changes. Sent files remain read-only
metadata; pending attachment removal and Clear authority are unchanged.


### Sent-copy hover follows the native ancestor branch

The sent-user hover observer belongs to the existing message row, the actual
ancestor of the TextEdit, padding, file labels and copy control. Qt hover delivery
selects a leaf and then its ancestors; a separate overlapping sibling observer
cannot reliably see the text/copy branch. The passive, nonblocking row handler
uses its parent-local point position to restrict reveal and click admission to
bubble.x through the right copy rail and the row's vertical bounds. Unrelated
empty space left of the bubble does not reveal Copy. There is no reparenting,
input overlay, pointer grab or hover-dependent layout. Native selection/cursor,
TabFocus reveal, reserved rail, compact extent and the original clipboard
identity/lifetime/once guards remain unchanged. Actual rendered input and
clipboard acceptance require the normal native app vehicle.

Prior art: original activity-header ancestor HoverHandler and native TextEdit /
ToolButton handlers; [Qt handlerPoint parent-local position](https://github.com/qt/qtdeclarative/blob/v6.11.2/src/quick/handlers/qquickhandlerpoint.cpp#L174)
and [Qt hover delivery ancestor traversal](https://github.com/qt/qtdeclarative/blob/v6.11.2/src/quick/util/qquickdeliveryagent.cpp#L1088).


### Consent and detail bindings have one content owner

The technical context TextArea displays the dialog's existing live
`disclosedContextText` value, the same exact QString parsed by its human summary.
It no longer invokes the callback-capable context getter a second time from its
own text binding. The existing context notifier keeps that value live, and the
accepted-offer path still independently verifies the current exact context and
original owner before approval. No approval/currentness check, selection/copy or
sharing disclosure is removed or replaced by a stale snapshot.

The original native DialogButtonBox retains its real standard buttons, roles,
labels and accepted/rejected behavior. Its natural content width is the sum of
the actual buttons' implicit widths and native inter-button spacing, independent
of the ListView's laid-out width or implicit content feedback. Dynamic Sign in
and Approve labels therefore invalidate natural measurement directly. Both the
box content width and view implicit width follow this one natural measurement;
no fixed pixel width, enlarged hit target or delayed layout is introduced.

Every vertical-only ScrollView in this dialog and the unified activity-details
box owns an explicit content width derived solely from its already-explicit
viewport width and padding. The wrapped child follows that content width. This
removes the available/content/implicit-width feedback path while preserving
native vertical scroll, wrap, full selectable exact payload, horizontal AlwaysOff
and the original height/viewport bounds. Prior art is the shared native
DialogButtonBox/Button natural implicit sizing and original explicit viewport
widths; all popup/footer controls and unified details remain the same controls.

The four deprecated hash pointer/length overloads use QByteArrayView with the
identical pointer and explicit length, including the one-byte NUL separator.
Fingerprint/settings bytes, formats, resource accounting and scientific or
runtime policy behavior do not change. Source checks cannot certify native
Mac layout, binding-warning absence or one-click input; those remain real-app
qualification requirements.


### Chronological current Edi notice and human activity purposes

The assistant's current Edi notice is a bounded presentation fact, not a footer,
archive entry or model message. On the first publication of a new current error,
the panel retains one owner/text/canonical-row-ID anchor. Repeated publication of
the same error keeps that anchor. Its selectable Edi-labelled item follows that
canonical row in the scrolling list; subsequent messages appear after it. A
missing/removed anchor or empty history uses one scrolling header notice so an
orphan is never lost. Clearing the current error removes its presentation;
conversation/account/assistant retirement resets the anchor. No append to a
failed archive, inference input or secondary history store is attempted.

The native delegate Column preserves original message role/ID access and forwards
pool/reuse resets to the original AssistantMessage. Canonical model rows,
clipboard/report callbacks, navigation and reading/follow-tail rules remain the
original ones. Pending Plan/Question/Trial/Working controls keep their existing
handlers in the scrolling progress footer; the Edi notice does not live there.

Collapsed activity captions prefer actual supplied purpose/description, then
validated pinned CommandAction metadata. Known project-assistance/SKILL.md reads
use the existing bundled workflow identity; unknown shell intention says only
Run shell command, never a raw command prefix. Registered Edi tool names map to
short human action phrases; other categories use honest verb descriptions.
Captions do not claim success, inspect command syntax, invoke a shell or create
new provider fields. Literal commands, immutable details/canonical copy and
actual status/uncertainty remain unchanged.

The Preferences Add skill source button uses the full existing content width.
The redundant guide paragraph is removed; the original source settings,
FolderDialog tokens, enable/add/remove controls and their authority remain.
Prior art is the existing canonical messages model/row ID navigation and native
ListView header/delegate/footer composition, the original notice style and the
pinned structured command/tool metadata. Native chronology and rendered input
still require the actual app vehicle; source checks alone are not acceptance.


### Persistent native control surfaces and live context publication

Composer neutral round actions and the Clear/Usage header controls reuse the
original sidebar-hover surface token in both palettes: darker than the light
surrounding surfaces and the native translucent hover fill in dark mode.
Backgrounds remain present at rest; enabled hover glyphs/text use the existing
accent, including both model/effort labels and Usage. Disabled colors, checked
Show actions, native keyboard fill cue, action enablement, handlers and strong
Send/Stop surfaces remain. The accepted-size avatar adopts Send's contrasting
background/foreground with no border. No global palette or component library is
changed. Working progress gains the normal inter-item top gap only when its
independent working/presented state is true; parent visibility never depends on
the child's effective visibility, and no hidden gap is retained.

The dialog's exact context QString is synchronously refreshed through its
existing context notifier, owner and open entrances, rather than binding any
property to the callback-capable getter. Each refresh captures the original
component/assistant and its own presentation identity before reading the getter.
A synchronous newer inventory/context notification replaces that identity; the
old return cannot overwrite it. No timer, queued retry, notifier suppression or
stale snapshot is used. Initial/owner/open refreshes keep displayed bytes live;
the accepted handler remains unchanged and independently reads the real current
context, verifies exact offered bytes, original offer/account/owner/draft fences
and once approval. Failed projection clears only its own presentation and offer.
The source loader commits its state/digest before publication and unchanged
reloads return without notifying, so the display updater introduces no own
notification feedback. Native warning absence still requires a real app run.

Human captions additionally recognize only four exact whole app-guidance read
commands: the single workflow/refinement SKILL.md reads and the two-path cat in
either order, using the existing staged relative paths. No trim, tokenization,
quotes, options, substitutions, redirections, compounds, newlines or unknown
paths are accepted by this closed identity comparison. Structured read metadata
shares the same human workflow/refinement wording. Supplied purpose remains
preferred; every other unknown command retains the honest neutral fallback and
the exact literal stays in expanded canonical details/copy.


### Header gaps follow the visible composer action footprint

The header uses the same accepted three-quarter tool-button action extent as the
composer for Clear and the connected avatar's horizontal footprint, while their
accepted visual circle size and original native vertical targets/header height
remain unchanged. This removes the hidden side inset that previously widened
the visible surface gaps. Header RowLayout spacing is the original composer
half-unit spacing; each adjacent rounded background therefore has that same
visible gap, rather than half-unit spacing plus invisible full-size margins.
Usage left/right padding is the model pill's three-quarter unit. Signed-out
Sign in retains its natural text sizing, and native actions, keyboard order,
current-owner handlers, glyphs, palette, hover/checked/disabled states and circle
extent are unchanged. No global style or geometry override is introduced.
Native painted spacing still requires the real app; grammar is not pixel proof.


### Explicit Stop and current scientific inspection

The original sidebar/status Stop controls alone latch a requested official-turn
interrupt, including the original pre-ACK once/correlation path. Window
deactivation, pointer movement, typing, scroll/navigation and Show actions or
window presentation changes do not manufacture Stop. Genuine conflicting
project input settles only the captured original operation through its existing
refusal, partial-prefix or admitted-worker/report path. The same manual event is
not replayed. Destroyed owners, sign-out, protocol/transport and resource failures
remain failures; this policy does not promise that failed work continues.

The VM owns manual target classification in active and inter-action intervals;
the helper keeps exact private-device/replay rejection and local Close/Hide
cleanup. Its existing paced timer holds the same step while the original window
is inactive, under the unchanged original deadline. It never activates another
window or injects into an inactive application. Original focus and draft
ownership must survive reactivation; a lost assistant draft refuses that tool.

Original project-edited and unowned fit notifications still retire compatibility
plans and stale scientific state. Within the same approved owner/account/input
scope they do not retire official turn/history or relabel all activity as
interrupted. Writes using the old scientific receipt refuse. Only a genuinely
completed, retained inspect_project can capture full current state and establish
a separate receipt for subsequent operations. The old receipt is never updated
to new stamps; pending editors and late callbacks cannot inherit the inspection.
A further manual edit makes the new receipt stale again. Actual scope/account,
input or project replacement still revokes its original authority without
recapturing a newer owner.

Clear retires old authority immediately and lets real correlated work settle
before final conversation cleanup; it does not send a hidden AI Stop. The
original inference deadline, once replies, committed scientific state/Undo and
retention fences remain. No automatic Clear, retry, cap donation or import
recovery engine is introduced. The chronological notice retains full selectable
error text and its Edi accessibility ownership without a redundant visible
heading. Source reasoning does not qualify native app-switch/draft/pressed
receiver behavior or retention failures.


### Checkable assistant controls expose their actual accessibility state

The original activity disclosure and Preferences source toggle explicitly expose
Accessible.checkable and Accessible.checked. The composer Show actions eye and
the existing Details, technical-data and retained skill-selection toggles follow
that same convention: their accessibility flags bind to the actual control's
checkable/checked properties. The native checked binding and handler remain the
only state/action authority. Ordinary popup openers are buttons, and native radio
controls keep their original roles. No dimensions, ink, palette, enabled state,
keyboard behavior, Stop behavior or scientific permission changes with these
metadata bindings. Actual accessibility delivery requires native qualification.


### Explicit borderless assistant action backgrounds

The composer Add files, Show actions eye, model/effort, history navigation, Stop and Send custom backgrounds, plus header Clear, Usage and avatar circle, explicitly set border.width to zero. This states the accepted borderless-action intent without relying on Rectangle's default pen validity. A default width getter alone does not prove a painted outline. Original fills, hover/focus ink, dimensions, native handlers and accessibility metadata are unchanged; composer frame, Usage tracks, tables and dialog outlines retain their own styling. Native rendering remains separately qualified.


### Disabled Send and before-visible connection action labels

Disabled Send uses the same persistent neutral actionBackground as neighboring composer controls; enabled Send retains its strong contrast and the original disabled icon color remains. The original connection dialog prepares its standard Ok action label/enabled state on aboutToShow, following the original Diagnostics dialog lifecycle. Its full Sign in with ChatGPT / Approve context labels, standard button identity and role, existing onOpened live-context refresh and all consent/acceptance/currentness handlers remain. No new authentication action, label rewrite, geometry or theme is introduced. Native transient-label rendering remains separately qualified.


### Individual scientific app actions

The first implementation is ProjectViewModel's Structure Load, Create experiment, enabled Experiment Type selectors and Load data into a bound ExperimentViewModel. Native `load_structure`, `create_experiment`, `set_experiment_type` and `load_data` expose those same doors in normal and Show actions delivery. File authority is an immutable admitted ID; member authority is the actual current PVM/native member, with a result pin on the original input receipt before public model notifications. Replacement or automatic naming returns the actual new dataset ID. No provider path, generic QObject scripting, new importer or recovery scheduler is introduced.

Existing compound creation keeps its empty guard, typed recipe, normal atomic transaction/one Undo and visible per-control partial behavior. Shared app-owned snapshot IO and original visible load/current-member steps prevent scientific-reader divergence. The new calls preserve existing scientific members/metadata/explicit choices and each ordinary Undo. No-op type settles before navigation or input. Already measured targets refuse replacement. Native refusal uses closed app-owned action identifiers, never raw exception text. An actual applied input alone may advance its scientific/raw-data disclosure; selected files, project/account, skills and capabilities must still match the original approval. Late/retired callbacks preserve actual partial facts and cannot authorize or answer a newer owner. Normal mode requires no widget geometry; Show actions uses actual group/member controls and the same original one-shot picker token. Pending/retired callback owners remain charged until actual release. Native/compiler/input delivery and dedicated-package qualification are separate evidence.


The original type selector rebuilds settings for the selected type; wavelength or linked-phase scales can be reset. Successful actual replacement reports the fixed `experiment_type_settings_reinitialized` diagnostic and current member/type/links. An equal-type no-op does not report a reset. Guidance requires inspection and reapplication of explicit supported values through the original parameter controls, without pretending this action preserves all experiment configuration or silently reconstructing it.


Original file/creation inputs now receive the closed Edit's typed applied result directly through LivePreview before any Applied trace or edited/publication hook. No post-preview row lookup supplies that identity. A later failure retains actual applied/retired/Undo facts without pretending publication completed. Individual-action terminal preparation reuses actual phase IDs and bounds unknown result/diagnostic IDs by their full escaped JSON spelling, including the nested response text and app schema/code/refusal variants. Existing caps, lawful names and strict terminal checks remain unchanged. Only the four new tool declarations use the exact public canonical schema spelling; old tool declarations and requested-versus-advertised equality remain exact.


### Individual-action parsed identities are admitted before Edit

The original Structure/data reader result and original Create/type names and phase links must fit the existing assistant result identifier bound before an individual assistant input reaches Edit or Undo publication. A prearmed individual input opts into this check and keeps a fixed refusal latch; manual and compound readers keep their existing behavior. Structure Load checks its already parsed native name; Load data checks its already parsed replacement after normal name-collision handling; Create/type checks the exact generated names/links. There is one original parser and no rename, truncation, larger cap or rollback. Unsupported representation returns the existing closed unsupported_input/file_id (or project/experiment) refusal with no scientific edit, preserving the original supplied bytes and ordinary manual name domain. Final-result and encoded-terminal checks remain defense in depth; callback retirement never upgrades the refusal to a write or authorizes another owner.


## Retention first cause and refused Send presentation

A retained native outcome remains fenced until its existing explicit lifecycle resolves it. Native completion, disclosure refresh and bound dynamic-item publication retain one app-local fixed first stage, exception class, role bound and factual applied/published/retired markers before notification/cleanup. No exception text, command, JSON, file/path/account identity or scientific payload is logged or sent; a false history-retention result is reported as a refusal, not guessed to be a capacity or storage cause. Later cleanup cannot replace the first marker. Existing successful explicit discard or fresh thread clears that local marker with the original retired ledger. Diagnostics grant no admission, retry, recovery or larger budget.

An explicit blocked Send uses the existing VM refusal and reveals its existing chronological selectable notice. The draft, IME, pending attachments and ACK owner are not consumed, the archive is not appended while fenced, and no approval dialog is advertised as a repair. The notice stays at its original emission anchor; revealing it does not fabricate a model message or relocate chronology. A later native case must capture the first actual stage before attributing a post-fit/import retention failure.


### Directory enumeration uses the operating-system name contract

The original result/export/report and local-skill walkers retain their existing closedir-owning unique_ptr and pointer-sized ordinary function-pointer deleter. A file-local explicit pointer type avoids importing function declaration attributes into template arguments; the result metadata charge uses that exact owning type. The operating system supplies a NUL-terminated readdir name, as already relied on by the local-skill walker; the [readdir documentation](https://man7.org/linux/man-pages/man3/readdir.3.html) explicitly warns against deriving its name domain from sizeof(d_name). Determine its length without assuming that sizeof(d_name) limits a returned record, and admit the existing result-leaf or skill-ID length before constructing a byte-array view/copy. No record parser, renamed name, larger limit, changed filesystem identity rule, warning suppression or new ownership framework is introduced. Actual compiler warning elimination is separately qualified.


### Explicit command goals use existing typed presentation metadata

Command headers prefer actual supplied purposes and structured operation captions. A single existing unknown commandAction may additionally carry a supplied goal in its exact first script line: `# Edi purpose: ` followed by bounded valid Unicode prose and an actual newline. The display reader inspects only that bounded typed command prefix, not quoted payload.command, later lines, nested wrappers or shell syntax. Invalid, missing, multi-action or unsupported declarations keep the original honest fallback. Existing native-purpose limits apply; control/bidi text, malformed Unicode and trailing backslash refuse presentation. This is PlainText supplied intent, never verified meaning, status, success or permission. Status remains independent, and the retained canonical payload, history, clipboard, row identity and disclosure remain exact. The existing developer/skill instructions require this only for newly authored hash-comment-capable shell scripts; they never rewrite argv, retained commands or unsupported programs. No runtime protocol, parser, execution route or model call is added. Provider preservation and model compliance remain separately qualified.


## Standard action ink and wrapped details ownership

The connection and failure dialogs keep their existing standard buttons, roles and native
EasyApplication delegate. Local font-relative padding surrounds every standard action's
content; the footer measures their resulting natural extents. A label's advance is not a
promise that its painted ink fits an unpadded button. Sign in, Approve, Cancel and failure
acknowledgement retain the original callbacks, fonts, rendering and offered-context fences.

The message's single wrapped technical viewport decorates an explicit Flickable, following
Qt ScrollView's existing Flickable support and the app's TextTab scroll ownership. Only that
Flickable owns content size: its viewport width determines the fields' wrap width, and the
fields' natural height determines vertical content extent. The ScrollView no longer writes
content size back through its implicit-content synchronization. The original bounded height,
vertical native scrollbar, literal/selectable details, canonical copy and pooled-row reset
remain. Native ink, scrolling and warning-free runtime acceptance are separate qualification;
source and grammar checks alone do not establish those outcomes.


### Composer toolbar breathing room

The existing composer Column keeps its original file/text spacing and gains only a
natural spacer before its bottom toolbar. Together with the Column's two adjoining
spaces, the text-to-toolbar gap matches the same Column's existing top inset. The
composer's implicit height continues to follow its contents. No input, attachment,
IME, Send, Stop, button sizing or keyboard behavior changes.


### Whole-turn working motion and status Stop extent

The existing agent_active state owns the working cue for the whole official turn,
including pending question/plan presentation. Presentation visibility no longer
chooses a new variant or resets the cue between tools. The circle keeps its
1600ms linear full rotation. The robot, EDI logo and app-bar robot reuse the original
EA SplashScreen/Edi branded motion:2160 degrees in2000ms, OutInElastic amplitude1
and period0.3. These curves run through the existing native scene-graph
RotationAnimator, whose easing property accepts the original curve. The inline robot keeps its accepted upright ink size and optical
center. Its reserved layout envelope is the fixed safe diagonal of the icon circle;
no live QML angle or per-frame rescaling is needed, so GUI-thread work cannot stall
the rotation merely by preventing an angle-binding update. The actual icon circle
and the surrounding rotation envelope are distinct extents. The app-bar columns glyph stays stationary while the retained robot
timeline continues behind it. Reduced motion still stops and resets rotation. Each target resets only from its own
Animator stopped handler, after Qt has synchronized back its rendered angle, and
only while the original current animation remains disabled. A source-property
notification is not ordered against that synchronization.

The original status Stop receiver's implicit and background circle extents equal
the adjacent working iconExtent. Native foreground/background functions, actual
canCancel, pressed-slot retention and the same explicit cancel handler remain.
There is no new timer, backend state, cancellation path or promise that animation
continues while the operating system suspends rendering. Genuine frames and native
input remain separate qualification.


### Native response maximum includes closed outgoing metadata

The existing native result reservation keeps its raw outcome/row maximum, including
synthetic refusal padding. The separate response-specific maximum also
includes the exact canonical schema and longest closed error code that the actual
Result projector may add. Both use the same schema and code declarations. Otherwise
a read result can fit its own raw maximum but exceed the response role solely because
projection adds metadata inside the escaped response text.

The existing Qt encoding and inclusive joint reservation still own raw maximum,
projected/encoded text, response and retained terminal roles. Added metadata backing
is admitted before growth; no capacity ceiling, result field, schema, tool behavior,
first-failure evidence or ownership policy changes. All existing edit, fit, inspection,
input and save response-bound consumers use the corrected common maximum.


### Omitted native Save destination follows the current owned project

The original Session needsSaveAs predicate owns the destination default shared by
normal and Show actions saving. With a genuine current owned directory, omitted
destination chooses the existing current Save path and ignores an unused suggested
fresh name. It preserves the actual project name/path and does not open Save As.
Explicit fresh still uses the original one-operation destination chooser; explicit
current without an owned directory still refuses. Without an owned directory,
omission keeps the existing fresh-name Save As flow and its required basename.

Only destination selection changes. Argument closure, original owner/currentness,
physical source/publication proof, worker admission, cancellation, once delivery and
factual committed/reopened/active results keep their existing implementation.
No pathname supplied by the model becomes filesystem authority.


### Observe owner-thread work before changing disclosure caching

The existing 200ms assistant poll continues after a turn; sync and notification can
rebuild project context and recapture enabled skill sources before unchanged-value
comparison. Existing revision/configuration identities do not establish unchanged
external source bytes. No new cache or slower timer is substituted for authoritative
Send, approval or tool checks.

An opt-in Qt debug logging category, edi.assistant.elapsed, observes only the original
poll/sync/notify/context/skills boundaries with monotonic elapsed nanoseconds. Each
stack-local observation emits a fixed stage and duration on return/unwind, holds no
QObject/project/payload and cannot throw into the original caller. Nested observations
include their children and are not additive CPU totals. The category is disabled by
default; no timer, counter, profile store, runner, model operation or public API is added.
Existing Main monotonic/native-frame observations can correlate these intervals with
actual input/render gaps before a narrowly owned caching correction is chosen. Source
redundancy does not itself prove the owner's elapsed lag or a responsiveness fix.


### File-load cue is presentation rather than device input

The shared pointer sequencer has one narrow file-load cue: current target geometry,
movement and visual press, with no device/key/clicked/file-dialog dispatch. Its original
receiver/currentness checks still fence completion. Afterwards the existing PVM file
admission/import owns actual consumed/applied/published facts and ordinary Undo. Manual
Load opens its original dialog; parameter/free/relation controls retain genuine input.
Original URL/FD/content proof and approved reader bytes follow ADR0017. A visual cue never
claims that a Load button handler ran, nor proves scientific success.


### Original input proof lifetime and cue refusal

The original selected-input and acquired-input entrances share non-inheritable
descriptor duplication: POSIX close-on-exec duplication or a non-inheritable Windows
handle/CRT descriptor, with refusal when it cannot be established. The same rule
covers their verification and directory-read duplicates. A later runtime exec must
not inherit an original-input read capability.

Acquisition reserves proof backing before growing its vector. Local proofs are
destroyed before their origin and path preparation charges are released; successful
adoption still explicitly transfers those roles to the selected-input owner.
A still-current Load target records an unavailable original before either initial
cue admission or later cue rejection can publish a generic control refusal. A retired
target keeps its own retirement result. Compiled instructions describe the same
visual-only assistant cue and original manual system dialog.


### Sent-file delegate width lifetime

The sent-file Repeater delegate measures against its named original Flow owner rather than dereferencing its transient visual parent. Removal or pooling can detach a delegate before destruction. The stable owner gives the same live width and wrapping limit throughout that transition, without adding implicit-size feedback, changing attachment history, or affecting pending-file removal. Other message widths belong to statically parented children; this change does not introduce a general layout wrapper or geometry override.


### Natural visible category continuation

Visible parameter requests reuse the actual suitable live category and name/variability state instead of clicking Reset for every requested row. Only conflicting name or variability filters require the original Reset button; category changes use the existing offered selector, while cell rows remain unfiltered. Actual row scrolling and native checkboxes remain. The Free/Fixed header can serve any consecutive uniform requested category block only when its displayed eligible original members equal that complete requested set; the prepared receipt retains the exact members and partial/uncertain prefix. A subset, mixed flag, dependent/read-only member, replaced owner or changed filter cannot broaden that authority. Background flags use these same Analysis controls, and explicit position-derived naming reuses the original Experiment button. No new presentation restoration, context-menu workaround, input helper, scientific executor or navigation framework is introduced.

A live non-cell name/variability filter that already shows the requested original member is suitable and is reused; hidden/conflicting rows use the existing Reset and offered category controls. Cell rows retain the unfiltered presentation. Explicit standalone position naming checks equality before page/focus/filter/input changes, so an unchanged table creates neither a decorative click nor Undo.


### Follow streamed geometry after native positioning

The conversation retains its existing coalesced tail request, but also requests it after the actual message and footer Columns complete child positioning and when the viewport height changes. Before positioning at the native ListView end (including its footer), the callback resolves pending view layout and rechecks follow ownership; an ongoing gesture, pressed scrollbar or deliberate history/Details navigation is not overridden. The existing keyboard scrollbar end-state check remains unchanged. This closes the ordering gap between a streamed model change and its later wrapped-row/footer geometry, without pinning or duplicating the working cue. Text, Markdown, row identity, terminal/Stop handling and the original motion remain unchanged. No text prebuffer, typewriter, artificial wait, timer or new streaming controller is introduced. This scheduling correction does not establish the cause of GUI-thread or network stalls; measured responsiveness remains a separate question.
