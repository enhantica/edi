# Defined line-segment background editing

- **Status:** Accepted
- **Date:** 2026-10-17
- **Implementation:** Partially implemented; native and manual source paths require compilation and behavioral qualification.
- **Priority:** High

## Context

The ordinary Experiment background UI in [ADR-0017](0017-app-gui-design.md) and `BackgroundListModel` already exposes line-segment position, intensity, free flags, IDs, Add and Remove. Its old Add chooses a default position immediately; the assistant needs an explicit scientifically justified anchor through that same visible UI. Position/removal previously used closed scalar/collection Edits without structural Undo. [ADR-0020](0020-calculation-worker-and-publication.md) owns the single closed Edit, LivePreview, calculation publication and Undo boundary. [ADR-0054](0054-assistant-controller-and-tools.md) owns original native calls, once-only outcomes, real widget input, resource admission and currentness. Background ID renaming already follows aliases and fit-result names through the model's existing rename rule.

## Decision

A typed `BackgroundPointInput` names add/update/remove, exact anchor ID and explicit position/intensity/free values where applicable. One preparation borrows the actual owned line-segment bank, applies the original caller policy and relation ownership, and preowns the before/after shared-row lists. Native requests require measured data, a matching complete axis/observation shape and finite distinct sorted in-domain anchors. Ordinary manual Add/position/remove retains simulation/calculation-only and no-measurement sources, finite extrapolation, duplicate positions and original row order; no measured-axis traversal or observation-length condition is imposed on that caller. Only a changed/new row is copied; surviving rows retain their actual objects, parameter specs, values, uncertainties and flags. Unchanged intensity preserves uncertainty; changed intensity uses the existing parameter setter. Removing an alias target refuses. Dependent intensity/free changes refuse. No observation, sigma, exclusion, weight, composition, unrelated parameter or relation is edited.

A closed background Edit rechecks optional source presence/identity, calculation-only state, raw-column writes where data exists, mode, exact row membership and relation lineage immediately before the single `ItemVec::assign` commit. The retained preparation keeps its original native/manual source policy. New native results retain strict measured/domain checks; Undo restores the exact lawful captured original arrangement rather than admitting it as a new native request. A native removal/update may therefore repair an ordinary duplicate or extrapolating anchor, and its one inverse still restores that original finite arrangement and order. That existing collection admits new columns, holds and anchors before live mutation. Its adjacent committed latch precedes publication. One preowned structural Undo restores only the exact prior shared rows, with surviving unrelated row objects shared rather than overwritten. A replaced source/owner, changed affected-row state or conflicting relation lineage refuses Undo. Restoration for either caller preserves the captured finite extrapolating/equal-position arrangement and original order; it does not silently clamp, sort or normalize the user's anchors. Exact live membership, affected-row snapshots and source/dependency conflicts remain authoritative; surviving unrelated rows retain their actual later state. It never restores a whole project. Renaming uses the existing common alias/correlation rename rule and records the prior IDs for ordinary Undo.

The first manual implementation is BackgroundGroup's original Add-and-edit
LineSegment table: BackgroundListModel::append selects the first unused ordinal
ID and copies the last row's position/intensity (or zero for an empty table).
Add again creates that actual editable row through the common closed editor and
records its ordinary Undo. The duplicate staged background form and its
insertionRequested callback are removed. Existing ID, position, intensity and
Remove cells remain; the original intensity parameter context menu owns its free
flag. No alternate scientific form or extra Apply exists.

Normal edit_background retains one strict validated operation/Undo. Show actions
prevalidates the requested final native result, then uses those same human
controls: Add if needed, exact ID/position/intensity edits, the real right-button
parameter menu and refine checkbox, genuine Escape to dismiss that exact menu,
or Remove. Page/tab/group/row navigation uses existing controls only if needed.
Each actual edit is separately prearmed for its exact original member/value and
uses ordinary manual policy, including lawful transient defaults. It is not an
atomic batch: complete, atomic:false and steps_completed expose actual progress;
Stop/refusal/takeover preserves completed changes and their individual Undo.
An applied latch precedes publication and survives retirement, including rename
and parameter-value/free siblings. Exact original account/RPC/project/bank,
source stamps, member, window/menu, deadline and manual drafts remain fences.
Private mouse ownership carries the actual left/right button through normal and
held/deferred release cleanup; Escape is delivered to the exact original popup's
keyboard owner, never by assigning visibility or invoking close().

Native requests retain the existing inclusive 256-row and 256 UTF-8-byte identity policy, plus bounded borrowed source/alias work and a separately admitted temporary preparation envelope. That envelope includes before/after/candidate pointers, selected-row copies, actual column/row/anchor/index roles and ordinary model publication. Existing context/response/transport roles remain separate; no cap is raised. Ordinary manual row position/remove/rename does not acquire the assistant's 256-row ceiling. Both callers share science and Undo while native packet capacity is explicitly caller-owned. New native identities use valid control-free Unicode; ordinary row ID editing retains its prior common key rule. Ordinary row position/removal constructs the typed operation from the exact already-owned stored key bytes, without QString decoding/re-encoding or readmission through the new-text validator. A valid existing tab/control-containing key therefore remains movable/removable and Undoable. This is ownership of an existing row, not relaxed admission for a new native request.

The existing context and `inspect_project` metadata gain complete actual `background.anchors` descriptors: ID, position, intensity, uncertainty, free and dependence. The same borrowed encoded-size preflight accounts for every descriptor before the ordinary JSON writer constructs it. Oversized/nonfinite complete context refuses instead of truncating or inventing ordinal IDs. The native registry gains the implemented app operation; strict core bundled-skill prerequisites remain unchanged so app-only capability discovery cannot break bootstrap. Bundled instructions name the operation conditionally and preserve current-project refinement and access-scope rules.

## Consequences

Normal native and each ordinary control share the existing scientific editors and Undo. A visible multi-control operation has truthful per-step outcomes rather than one-edit semantics. Polynomial/Chebyshev conversion, automatic background estimation, bulk operations, arbitrary input-folder access and visible Save are not provided by this operation. Existing source/root grants and actual native lifecycle remain unchanged. This source change requires ordinary compiled consumers and independent scientific, Undo, input, cancellation and reentry checks before delivery claims.

## Alternatives

A separate staged setup form duplicates the original human row controls and is removed. The original Add defaults are transient real manual state, not a claimed scientifically justified final anchor. Visible sequencing reports those actual partial states and preserves their Undo on interruption. A private mutation decorated with pointer movement would not be a real GUI workflow; a full-project rollback would overwrite unrelated edits. Neither is used.
