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
