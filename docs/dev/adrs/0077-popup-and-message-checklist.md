# 0077. Popups, tooltips and messages: a checklist

- **Status:** Accepted
- **Date:** 2026-11-07
- **Implementation:** 🟡 Partially implemented — the base buttons, dialog buttons and menus carry icons, and the
  popups in files no other open work changes follow the list; the assistant's popups and What's new follow it when
  that work merges
- **Priority:** Medium
- **Forward constraint (binding on new features):** a change that adds or edits a popup, a tooltip or a message goes
  through this list for what it touches.

## Context

The owner asked for popups that read the same and for tooltips and messages that are clear and short and say how to
proceed (2026-11-02). Each popup had been written on its own: some buttons had icons, most did not, and Home's links
drew their icon with a button of their own. The list below is what every popup, tooltip and message now follows, so
later work can apply it to the files it changes instead of a pass over the whole app.

## Decision

1. **Every button in a popup has an icon** from the icon font: in a dialog, a menu or a window that opens over the
   app.
   - A standard dialog button takes its role's icon from the base `DialogButtonBox`: OK, Yes and Apply a check,
     Cancel and No a cross, a destructive button a bin, Reset an undo arrow, Help a question mark.
   - Any other button names its icon in `fontIcon`, which the base `Button` draws before the text. A menu's action
     names it in `icon.name`.
   - A button without one says why in a comment beside it. There is none yet.
2. **Tooltips go through the level** (ADR-0076). A tooltip sets `requested`, never `visible`; a control whose label or
   icon already says what it does declares `selfExplanatory`. A disabled control's tooltip says why it is disabled
   and what enables it. Each control has one help popup and owns it: a base control opens its own, a caller or a
   wrapper gives only its text (`ToolTip.text`, or a component's `helpText` or `disabledReason`), never a second
   popup, and a warning steps the base's popup aside so that it is the one shown. Which inputs each base control
   takes, and how help, the full text and a warning share its one popup, is ADR-0076 point 6.
3. **Tooltips and messages are short and say how to proceed.** One or two sentences: what is the case, then what to
   do about it. Name the control or page to use by the name it shows. Say what failed in the user's words, not the
   code's.
4. **Labels and table headers start with a capital letter**, except a symbol whose case matters (*hkl*, *d*).
5. **A popup is an `AppDialog`** (ADR-0017 §14): centred on whole pixels, its standard buttons in the footer. Enter
   accepts a dialog without a text field of its own.

## Consequences

The popup census in the integration checks finds every button in a popup and fails on one without an icon and
without a stated reason; the tooltip census does the same for tooltips that bypass the level. Points 3 and 4 are read
in review. Home's links (`IconLink`) are now plain base buttons with an icon.
