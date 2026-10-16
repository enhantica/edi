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

Empty reasoning effort means Provider default and stays empty on the wire; explicit tags use localized
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

Successful selected-file add/remove and ordinary project/manual-fit changes invalidate the staged thread/context, not the genuine managed process/account/catalog. Host-owned selected snapshots and retained conversation remain. Existing file admission runs only when execution/retirement is settled; its own staging flag does not imply account logout. For active manual changes, the same original terminal/input/control cancellation proof and first revoke deadline used by Clear settle execution, with a distinct context-pending flag and no archive clear. Old progress is suppressed and existing pending rows are interrupted honestly; fresh context consent and a new thread are mandatory. Explicit logout, unfinished/unadmitted connection preparation, unknown protocol/transport failures retain real process/account retirement. Retired workspace files remain available for explicit recovery; a new staged thread never relabels them as fresh. No authenticated assignment, manual approval bypass or new RPC ownership table is introduced.

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
