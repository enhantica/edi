# Assistant panel and conversation history

Status: Accepted
Date: 2026-10-15
Implementation: Partial; terminal-retention/app lifecycle unit pending independent verification
Priority: High

The assistant is a Session-owned view model, separate from the currently open ProjectViewModel. It remains available without a project and rebinds the controller whenever the project changes. The controller borrows the existing project and worker; approved edits enter ProjectViewModel's existing apply/preview door (ADR-0020). External edits and manual fit completion invalidate the assistant revision. Queued provider requests are fenced across rebinds. Closing a session detaches before child project destruction.

`app/qml/Components/Assistant*.qml` adopts edi's existing EasyApplication components, theme, font and AppSizes spacing. The panel sits opposite the existing workflow sidebar. Preferences persist visibility and width, and reset restores their defaults. At narrow widths it overlays the content instead of compressing both chart and workflow controls below usability. The app-bar action and keyboard shortcut reopen it. Resizing is bounded by app spacing tokens. The existing manual controls remain operable when it is hidden.

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
