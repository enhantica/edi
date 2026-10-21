# 0046. Analysis sidebar: scan controls and parameter filters

- **Status:** Accepted
- **Date:** 2026-10-21
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

The Analysis page showed the Evolution tab and the Follow button in every project, greyed out when they could not
apply, although both only mean something for a scan's sequential or independent fit. Its parameter filters sat on one
line: a name field, a category picker and a variability picker. The category picker listed every category whatever
else was selected, its counts mixed categories and parameters, and there was no way to narrow the table to one
structure or one experiment, or to undo every filter at once.

## Decision

1. **Scan-only controls.** The Evolution tab and the Follow button are shown only when the fitting mode is sequential
   or independent. For single and joint fits both are hidden, not greyed, and Start fitting takes the full width of
   the row. They appear and disappear as soon as the mode changes; a page showing Evolution when it goes away returns
   to the pattern.
2. **Two filter lines.** The top line has three pickers of equal width: datablocks, categories, parameters (all, free
   or fixed). The bottom line has the "Filter by name" field and, at its end, a square button with the eraser icon
   that clears all four filters in one click ("Clear all filters").
3. **Datablocks.** The datablock picker lists "All datablocks", then every structure, then every experiment, each with
   its coloured icon, as the category picker shows its entries.
4. **Each filter narrows the next.** The categories listed are those of the selected datablocks, with the bold
   structure and experiment headings as before. The parameter picker counts what the two pickers above leave, and the
   name filter searches only that subset. A selection that no longer exists after a change returns to "All".
5. **Counts are parameters.** Every number in brackets, in every picker and its list, is the number of parameters the
   entry covers under the selections above it, never a count of datablocks or categories.

## Consequences

- A single or joint fit no longer shows controls it cannot use.
- Narrowing a large project to one structure or one dataset takes one choice, and undoing every filter takes one
  click.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Grey the Evolution tab and Follow outside scans | Rejected by the owner: hidden reads clearer than disabled for a control that never applies. |
| Counts of datablocks and categories in the pickers | Rejected by the owner: one unit everywhere is easier to read and remember. |
