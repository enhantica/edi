# 0105. Declared columns

- **Status:** Proposed
- **Date:** 2026-11-26
- **Implementation:** 🟡 Partially implemented — the kind tables whose texts are plain model roles; tables with icons,
  selectors or derived texts are still measured from their rows
- **Priority:** Medium
- **Forward constraint (binding on new features):** a new sidebar table declares a kind for every column and, for each
  text column, the model role it shows (`DataTable.columnTexts`); a column that cannot name one says why in a comment.

## Context

ADR-0103 decision 4 gives every sidebar table its columns' kinds, and rule T5 sizes a number by its kind, never by its
values. Text columns were still measured by making every row of the model beside the view and reading its cells. A
table inside a folded group, which is made on its first open, did that measuring on the open: 111 to 295 ms, and a
width that the sidebar learned only then (Structure 605 to 615 px on the moments).

## Decision

1. A column's width need comes from its kind and the fonts: the row number from the row count, a mark and a control by
   their fixed boxes, a number by its kind's typical value, a unit by the widest unit. A header wider than that wins.
2. A text column names the model role it shows, plain or as an input (`{role, edited: true}`, measured in the bold an
   edit takes with room for the caret). Its width is the widest value of that role read from the model, with the cell
   margins. No row is made for it. A model over 1000 rows is read for its first 200, as before.
3. When every column of a table is answered by 1 or 2, the table reads nothing else: its widths are known while its
   group is folded or its page hidden, a changed row reads only the model, and a first unfold changes no width.
4. A table whose text is not a plain role (an icon line, a selector, a derived text, a list of values per row) keeps
   the row measure until its texts can be declared. Today: Examples, Structures, Atom sites, the moments table in crystal
   axes, Aliases, Fit start, Linked structures, Magnetic form factors, Excluded regions on a single crystal, the
   generated category tables and the Analysis parameter table, which has its own rule.
5. Kinds say what a column holds: a user's id or label is a `name`, a fitted parameter a `value`, an icon-only column a
   `mark`, a long fixed text such as h k l a `text`.

## Consequences

- Most kind tables make no row to size themselves, so opening their group costs only the rows it shows.
- A text column's width follows its model's texts; a cell that draws more than its role (an icon, a suffix) must not
  be declared, or its text is cut.
- The row measure stays for the tables in point 4; removing it there needs icon and selector widths from fixed
  metrics.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Make the folded groups' contents at page load so they measure early | Rejected: the page switch cost that made them lazy comes back |
| A fixed width per text kind (twelve M for a name) | Rejected: wider than most names and still cuts a long one (T10) |
