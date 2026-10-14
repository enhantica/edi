# Assistant panel and conversation history

Status: Accepted
Date: 2026-10-15
Implementation: Partial; native visual and live interaction verification pending
Priority: High

The assistant is a Session-owned view model, separate from the currently open ProjectViewModel. It remains available without a project and rebinds the controller whenever the project changes. The controller borrows the existing project and worker; approved edits enter ProjectViewModel's existing apply/preview door (ADR-0020). External edits and manual fit completion invalidate the assistant revision. Queued provider requests are fenced across rebinds. Closing a session detaches before child project destruction.

`app/qml/Components/Assistant*.qml` adopts edi's existing EasyApplication components, theme, font and AppSizes spacing. The panel sits opposite the existing workflow sidebar. Preferences persist visibility and width, and reset restores their defaults. At narrow widths it overlays the content instead of compressing both chart and workflow controls below usability. The app-bar action and keyboard shortcut reopen it. Resizing is bounded by app spacing tokens. The existing manual controls remain operable when it is hidden.

The panel shows the provider connection, dynamically offered model/effort, public conversation, exact proposed parameter groups, budgets and improvement tolerances, questions, trial activity and Stop. Approval is an explicit user action bound to the current plan and revision. Text is plain and selectable; model text cannot activate links or invoke edits. The scientific chart remains edi's real chart, not a chat replacement. Actual light/dark, left/right, narrow/wide and keyboard visual acceptance is owed; adding QML files alone does not prove it.

Public conversation and activity are bounded to one MiB in edi's separate app-local history file, written with owner file permissions. History never includes credentials or hidden provider reasoning. Prior displayed history is an archive; a new controller does not silently replay it to the provider. Clear conversation resets both the visible archive and the controller conversation while idle. Portable export, retention settings and complete protected cross-platform persistence remain subsequent units.

Prior art: edi's sidebar preferences and AppPreferencesDialog, RowTableModel, app-bar extension seam, ProjectViewModel apply and single-fit undo. No base gui-components fork, alternate style system or production test command is introduced. The native test runner observes the real view model and QML object names defined by the accepted task interface.
