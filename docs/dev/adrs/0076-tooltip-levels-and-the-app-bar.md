# 0076. Tooltip levels and the app bar

- **Status:** Accepted
- **Date:** 2026-11-07
- **Implementation:** 🟡 Partially implemented — levels, delay, the one decision, Preferences and the app bar are in;
  the files other open work changes keep reading the older switch until they move to the decision, and disabled
  controls' tooltips are being added; point 6 is in for the base controls, `NumberLabel`, `ValueField` and
  `SelectorField`, and the files other open work changes follow it when that work has merged
- **Priority:** Medium
- **Forward constraint (binding on new features):** a new control gives its text to its base owner (point 6) and, where
  its label or icon already says what it does, sets `toolTipSelfExplanatory`; a popup of its own, where no base owns
  one, sets `requested` and `selfExplanatory`, and never binds `visible` itself or reads `showToolTips`.

## Context

Tooltips were on or off. Every use bound its own `visible` to its hover state and `EaGlobals.Vars.showToolTips`, so the
rule for when a tooltip shows lived in about a hundred places, and a tooltip opened the moment the pointer arrived. The
owner asked for levels, a delay and a switch in the app bar, and for the app bar to hold only app controls.

## Decision

1. **Levels.** Tooltips open at level All, Important (the default) or Off. Important leaves out controls whose label or
   icon already says what they do (tabs, OK and Cancel, a sidebar group's title), but never a disabled control: its tooltip says why it is
   disabled and how to enable it. All shows every tooltip; Off shows none, warnings included.
2. **One decision.** gui-components' `EaGlobals.Vars` holds `toolTipLevel`, `toolTipDelay` and `toolTipAllowed`, the one
   function that decides. A tooltip sets `requested` (usually its control's hover) and, where it applies,
   `selfExplanatory`; its own `visible` is `requested`, non-empty text and the decision. edi's copy of the base tooltip
   does the same. The delay is Qt's tooltip delay, 1000 ms by default (the owner, 2026-11-08; 1500 ms before): before levels, a
   tooltip started at once and faded in over 1000 ms, which stays as it was. A change to the delay applies to every
   tooltip at once and is kept as the level is.
3. **Settings.** Preferences keeps the level, the delay and the last level that was not Off under `Edi.Preferences`, and
   writes a choice at once. With no level stored, the earlier on/off flag decides it: off is Off, on or unset
   Important. That flag is left as stored. Preferences' Prompts tab has the level and the delay in place of the old
   check box.
4. **The app bar.** Its left group (Save, Undo, Redo, Reset) stays. Its right side holds only the AI assistant, the
   tooltip switch and Preferences, after the status bar's faint rule. Help and the bug report left it; Home's Help and
   feedback and Documentation links reach them. A click on the switch turns tooltips off, or back on at the last level;
   a right click opens Preferences.
5. **The older switch.** `showToolTips` stays in the base, kept equal to "level is not Off", only for files other open
   work is changing; they move to the decision when that work has merged.

6. **Who owns a control's popup.** A control shows at most one popup at a time, and the base control it is built on
   owns it. A wrapper or a caller gives text and flags through the inputs below, never a popup of its own. A popup can
   carry three kinds of text, in this order of precedence:
   - **A warning** (a refused value, a value outside its range, a domain warning). The wrapper that knows why sets
     the base's `warned` and shows its `WarningToolTip` with the warning's text. While `warned` is set, the base asks
     for nothing, so the warning is the one popup; once it clears, the base's popup is asked for again. A wrapper
     that sets `warned` always has a warning text: a typed text its rule refuses shows that rule. The warning owners
     are listed in the second table, each with when its warning is asked for.
   - **Help**: what the control does or means (the dictionary label and `.edi` name, an action's description), or,
     for a disabled control, why it is disabled and what enables it. It is the attached `ToolTip.text`. The base
     asks for its popup on hover from a hover handler, which reports hover on a disabled control too, whether or not
     the text fits.
   - **The full text**: what the control would show with room (the whole name, the number in full). The base's
     `fullText`, by default its own text, is shown while `shortened` is set, by default while the text is elided
     (`truncated` for a label, `overflows` for a table text input; a text field has no default). A control that
     shows a value shorter than it is (a number in scientific notation) sets both.

   The popup's text is the full text and then the help, one per line, when both apply, or whichever applies. The full
   text is left out when the help already contains it, since a header's help starts with its label. Focus: a table
   text input (`ListViewTextInput`) asks for neither help nor the full text while it has focus, where the typed text is
   what the user reads; a text field's help stays asked for on hover whether or not it has focus; focus alone never
   asks for help or the full text. A warning is asked for on focus too, as its owner's row says.

   **Self-explanatory controls.** Every base owner has `toolTipSelfExplanatory` (false by default), which its one popup
   reads as its `selfExplanatory`. A caller whose control's label or icon already says what it does sets it on the
   control, never on a popup. The level then decides as in point 1: at Important such a control shows nothing while
   enabled and its reason while disabled; at All it shows; at Off nothing does. `TabButton` keeps its popup's fixed
   classification. `ChartToolButton` and `StatusBarItem` keep their own popups, which set the classification directly.

   Every popup still goes through the level and the delay (points 1 and 2): none shows before the chosen delay.

   | Base owner | Help | Full text | Warning | Wrappers and callers give |
   |---|---|---|---|---|
   | `Button` | `ToolTip.text`, on hover | none | none | `GroupButton` and callers: `ToolTip.text`, `toolTipSelfExplanatory` |
   | `ListViewLabel` | `ToolTip.text`, on hover, fitting or not | `fullText` while `shortened` (elided) | none | `NumberLabel`: `fullText` the number in full, `shortened` while shown shorter or elided; `HeaderLabel` and table titles: the dictionary help; a file-name link: its action |
   | `ListViewTextInput` | `ToolTip.text`, on hover without focus | `fullText` while `shortened` (overflowing) | `warned` steps aside | `TextCell`: `fullText` as the file writes it or in full, `shortened` while shown shorter or overflowing, `warned` and its `WarningToolTip` for a refusal |
   | `TextField` | `ToolTip.text`, on hover | `fullText` while `shortened` (no default) | `warned` steps aside | `ValueField`: help or its disabled reason, `warned` and the refusal or its rule; `ParameterField`: the item's help or its hint, `fullText` its value while shown shorter, `warned` and the warning |
   | `ComboBox` | `ToolTip.text`, on hover while closed | none | `warned` steps aside | `SelectorField`: its help (the caller's `helpText`, else the dictionary's option help) or its disabled reason, `warned` and the refusal; `ToolbarComboBox` and callers: `ToolTip.text` |
   | `Slider` | `ToolTip.text` while disabled (the reason) | `toolTipText` while enabled, the value by default | none | callers: the reason and, if they want, `toolTipText` |

   Every base owner above also takes `toolTipSelfExplanatory`.

   | Warning owner | Built on | Warning text | Asked for | Otherwise |
   |---|---|---|---|---|
   | `ValueField` | `TextField` | the refusal, else the rule a typed text breaks | on hover (also disabled) or focus | the base's help or disabled reason |
   | `ParameterField` | `TextField` | the refusal, else outside its range, else the item's domain warning | on hover or focus | the base's popup: value while shown shorter, then the hint or the item's help |
   | `TextCell` | `ListViewTextInput` | the refusal | on hover or focus | the base's popup: the number in full while shown shorter |
   | `SelectorField` | `ComboBox` | the refusal | on hover while its list is closed; none while open, where the list is what the user reads | the base's help or disabled reason |
   | `ParameterCell` | `ListViewParameter`, on edi's `TextInput` | the refusal, else outside its range, else the item's domain warning | on hover or focus | its own ordinary popup, kept: a caller's help where it sets `helpToolTip`, else the number in full while shown shorter, else the whole text while it overflows, else the item's help; on hover without focus |
   | Project name (`DescriptionTab`) | edi's `TextInput` | the refusal | on hover or focus | nothing: the name has no help |

   `ParameterCell` and the project name keep their own popups, since their base has none to give: each shows one at
   a time by the conditions above, and goes through the level as every popup does.

## Consequences

The rule for when a tooltip shows is in one function, and a tooltip names only why it is wanted. A disabled control
gets no hover in Qt, so its tooltip needs a hover area around it rather than on it. Warnings now follow the level too. With point 6, a control has one popup whose text is the warning, else its full
text and help: a number keeps its full precision, a header its dictionary help whether or not it fits, and a refusal
is never covered by ordinary text. A check of it hovers or focuses each base owner and each warning owner in each case of
the tables (fitting and elided, help and none, enabled and disabled, warned and not, focused and not, a selector's list
open and closed), through the inputs a caller sets, and counts the popups shown, which is one or none, and reads the
one text. It sees none before the delay and the popup after it, and sees the base's popup come back when a warning
clears while hovered or focused.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep each use's `visible` and add the level to every binding | The rule would stay in a hundred places; rejected |
| Let each wrapper delete the base's popup and draw its own | Every new base popup (overflow, a disabled reason) needed one more deletion in every wrapper, and a missed one showed two; rejected |
| Keep the selector's rule of emptying its help while refused | It worked for one wrapper only; `warned` on the combo box is the rule the text fields follow |
| Set the self-explanatory flag on a caller's own popup | That is a second popup; the base reads its control's flag instead |
| Show only the help when a label is elided | A file name or a header with its units would lose the part that did not fit; the full text goes first instead |
| A popup with the level and delay on right click | Preferences already has both rows; one place to change them is simpler |
| Migrate the old flag by writing the new level at start | It wrote over a stored choice while settings loaded; the level is read once instead |
