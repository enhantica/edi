# 0076. Tooltip levels and the app bar

- **Status:** Accepted
- **Date:** 2026-11-07
- **Implementation:** 🟡 Partially implemented — levels, delay, the one decision, Preferences and the app bar are in;
  the files other open work changes keep reading the older switch until they move to the decision, and disabled
  controls' tooltips are being added
- **Priority:** Medium
- **Forward constraint (binding on new features):** every new tooltip sets `requested` and, where its control's label or
  icon already says what it does, `selfExplanatory`; it never binds `visible` itself or reads `showToolTips`.

## Context

Tooltips were on or off. Every use bound its own `visible` to its hover state and `EaGlobals.Vars.showToolTips`, so the
rule for when a tooltip shows lived in about a hundred places, and a tooltip opened the moment the pointer arrived. The
owner asked for levels, a delay and a switch in the app bar, and for the app bar to hold only app controls.

## Decision

1. **Levels.** Tooltips open at level All, Important (the default) or Off. Important leaves out controls whose label or
   icon already says what they do (tabs, OK and Cancel), but never a disabled control: its tooltip says why it is
   disabled and how to enable it. All shows every tooltip; Off shows none, warnings included.
2. **One decision.** gui-components' `EaGlobals.Vars` holds `toolTipLevel`, `toolTipDelay` and `toolTipAllowed`, the one
   function that decides. A tooltip sets `requested` (usually its control's hover) and, where it applies,
   `selfExplanatory`; its own `visible` is `requested`, non-empty text and the decision. edi's copy of the base tooltip
   does the same. The delay is Qt's tooltip delay, 1500 ms by default: before, a tooltip started at once and faded in
   over 1000 ms, which stays as it was.
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

## Consequences

The rule for when a tooltip shows is in one function, and a tooltip names only why it is wanted. A disabled control
gets no hover in Qt, so its tooltip needs a hover area around it rather than on it. Warnings now follow the level too.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep each use's `visible` and add the level to every binding | The rule would stay in a hundred places; rejected |
| A popup with the level and delay on right click | Preferences already has both rows; one place to change them is simpler |
| Migrate the old flag by writing the new level at start | It wrote over a stored choice while settings loaded; the level is read once instead |
