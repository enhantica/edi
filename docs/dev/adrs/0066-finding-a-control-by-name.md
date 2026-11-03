# 0066. Finding a control by its object name

- **Status:** Accepted
- **Date:** 2026-11-02
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

The tutorials' callouts point at the control a step is about (ADR-0064), and the assistant's Show Actions mode will
point at and act on controls too. Both name a control by its `objectName`. Two lookups that each walk the window their
own way would disagree about which of two same-named items is meant, or about whether a scrolled-away control counts.

## Decision

- `app/src/item_locator.hpp` is the one way to find a control by name. `findNamedItem(window, name)` walks the window's
  items depth first from its content item, children in the order they are drawn (by `z`, then their own order), and
  returns the first item with that name that is shown. A hidden item hides everything inside it.
- Shown (`isItemShown`) means the item and all its ancestors are visible and not fully transparent, and some part of it
  is inside the window and inside every ancestor that clips its children (`visibleSceneRect`, that part in window
  coordinates). A control scrolled out of its list is not shown, so nothing points at it; a tall group whose header is
  in view is.
- `itemSceneRect(item)` gives the item's whole rectangle in window coordinates. `findNamedItemAnywhere` finds a named
  item shown or not, for a caller that reveals it first.
- QML reaches the same functions through the `ItemLocator` singleton: `find`, `findAnywhere`, `shown`, `sceneRect` and
  `visibleRect`.
- A caller with stricter needs (for example, the assistant also requiring an enabled control before acting on it) adds
  its own check to the item this returns; it does not walk the window again.

## Consequences

- The callouts and Show Actions agree on which control a name means.
- A name used twice resolves to the first one shown in drawing order; a page that needs both distinguishes them by name.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A QML walk in each component | Rejected: the tutorial panel had one, and a second caller would have needed another. |
| `QObject::findChildren` by name | Rejected: it follows object ownership, not drawing order, so its first match need not be the one in front. |
