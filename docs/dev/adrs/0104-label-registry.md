# 0104. The label registry

- **Status:** Proposed
- **Date:** 2026-11-26
- **Implementation:** 🟡 Partially implemented — the registry, its check, the table headers of `.edi` items, the selector
  short forms and the Evolution selector's derived names; other labels still set their texts themselves
- **Priority:** Medium
- **Forward constraint (binding on new features):** a new fixed label has a row in `app/data/labels.tsv` and shows
  through `AdaptiveLabel` (a table header through `HeaderLabel`); a short form is entered in the registry, never as a
  literal at the call site. `tools/checks/label_registry.py` refuses a key with no row; it and `build_labels.py --check` run as `label-registry-check` in verify-quick, verify-full and the CI lint job.

## Context

ADR-0103 says a header or fixed label is never cut (T9, N1) and a table declares its columns' widths before it is made
(T5). Labels had one form each, so a narrow column either cut its header or grew. Short forms existed only where a
call site added one by hand ("Sym 1", "Iso", the beam mode's CWL and TOF, the owner's interim rule of 2026-11-23: a
narrow selector shows its short form, never cut, with the full text in its tooltip), and a scan's derived values
reached the Evolution selector as raw item names such as `spherical_modulus`. The owner asked on 2026-11-23 for one
registry of the long and short forms of every visible label, one label component that picks the widest form that
fits, and this ADR.

## Decision

1. **One table.** `app/data/labels.tsv` has the columns key, long, short and icon (a Font Awesome name), short and icon
   empty where there is none, and is in the app's resources. A key is the `.edi` name where the label names one, as
   the GUI names parameters (ADR-0010): an item's `category.name`, a variant's `uid@token`, a selector option's
   `uid=token`, a category's id. Any other label is keyed by its control's objectName; a table header with none by
   `header.<text>`.
2. **The dictionary stays the source of names** (ADR-0051). For a dictionary key the app shows the dictionary's name
   (`Session.labelForms` asks `Session.label`, `optionLabel` or `categoryTitle`); the registry's long column copies it so
   the table lists every form, and `tools/data/build_labels.py --check` fails when the copy differs. The registry adds
   the short form and the icon. For any other key the registry's long form is shown.
3. **One label component.** `AdaptiveLabel` shows the long form if it fits its width, else the short one, else the
   icon alone; it is never cut, and while it shows another form its tooltip holds the long text. `longWidth`,
   `shortWidth` and `iconWidth` come from the font and the forms alone, and `formFor(width)` names the form a width
   shows, so a table can reserve a column before the label is made. `HeaderLabel` is an `AdaptiveLabel` keyed by its
   item, its units appended to both text forms; its reserved width is the short form's.
4. **No raw names.** A name the app builds from a dotted path (a scan's derived column, a column no parameter has)
   takes the registry's words for its item, after its row where it has one ("Co1 |M|"). The check refuses a raw
   `snake_case` name in a form, a derived scan column with no row, and code that shows the last part of a name
   without looking it up.
5. **Filled mechanically.** `tools/data/build_labels.py` writes the rows it can derive (the dictionary, literal texts
   of controls with an objectName, literal header texts, `wholeLabels ? long : short` pairs) and keeps short forms and
   icons entered by hand; it lists the labels whose text is not a literal.

## Consequences

- A narrow column shows a short form or an icon instead of a cut header, and its width is known before it is shown.
- Short forms live in one place, so a new one is a registry row, not a call-site literal.
- The registry is larger than the labels drawn through `AdaptiveLabel` today; the rest (dialog headers, group titles,
  tabs, toolbars) move to it one by one, and until then their rows only list their forms.
- A crysta pin that renames an item leaves the registry's copy stale until `build_labels.py` runs; the app still shows
  the new name.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Short forms in crysta's dictionary | Deferred: only `.edi` items live there, and many labels name controls; the registry can move its item rows there later |
| A short form per call site (`shortText`) | Rejected: the forms scatter, and a table cannot learn a header's widths before the header exists |
| Eliding a label that does not fit | Rejected by ADR-0103 (T9, N1): a fixed label is never cut |
