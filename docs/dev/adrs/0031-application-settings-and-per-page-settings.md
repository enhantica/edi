# ADR-0031 — Application settings and per-page settings

- **Status:** Accepted
- **Date:** 2026-10-11
- **Implementation:** 🟡 Partially implemented — the desktop store and its one-time carry-over, the Settings tab on
  every page ("Pattern updates during a scan" on the Analysis page), the shown path with
  Open folder and Reset, the window's geometry, the recent and last projects and each project's selection; the
  browser keeps local storage until its measurement (4)
- **Priority:** Medium
- **Forward constraint (binding on new features):** a setting about how the app looks or behaves on this machine goes
  in the app-settings store, never in a project's `.edi` files; a setting that changes what a project calculates or
  fits goes in the project.

## Context

edi keeps two kinds of state. A project's data (its structures, experiments and analysis, with their options under
each page's Main and Extras tabs) is written to the project's `.edi` files and travels with the project. Other state
belongs to the person and the machine: the preferences in the app bar's dialog (ADR-0017 §12), the window's size and
place, the projects opened lately, the y-axis scale chosen on a chart, how often a followed scan redraws its pattern
(ADR-0029).

Today the second kind sits in one file the base's `Settings` objects write (`settings.ini` in the platform's
application configuration folder; in the browser its text is kept in local storage, ADR-0023 §5). Nothing says which
side of the line a new setting falls on. A choice that belongs to one page, such as the pattern updates, has no home of
its own: it sits among the Analysis page's Extras, next to project options it has nothing to do with. The settings
file's place differs per platform and is not shown anywhere, so a user who wants to see it, copy it or start afresh has
to know where Qt puts it.

## Decision

1. **The split.** A project's data, Main and Extras on every page, lives in the project's `.edi` files. Everything else
   lives in one app-settings store and never in `.edi`:
   - the app bar's settings (the Preferences dialog);
   - each page's Settings tab (2);
   - the window's size and position;
   - the last open project and the recent projects;
   - for each project, the structure and the experiment last selected in it, keyed by the project's path;
   - for each project, its scan views' Stacked spacing and Map direction (edi ADR-0041), keyed the same way, so a
     project reopens with them (the owner, 2026-10-26).

   A project opened on another machine, or by someone else, opens with that machine's settings, and changing a
   setting never marks a project modified. The report's settings are project data, not app settings (ADR-0036 §7):
   the Analysis page's correlation level and its chart's x axis are `analysis/analysis.edi` items, the Report page's
   Contents and Embed choices `reports/report.edi` items; only the Embed default for new projects is a preference.
2. **A Settings tab on each page.** Each workflow page's sidebar gains a Settings tab beside Main, Extras and Text. It
   holds that page's options that only change what the app shows or how it behaves, in groups, as Main and Extras hold
   project data. They are kept in the app-settings store under the page's name and apply to that page, unlike the app
   bar's settings, which apply to the whole app. The Analysis page's Settings tab is the first: "Pattern updates during
   a scan" moves there from Analysis, Extras. A page with no such options has its Settings tab disabled, as an empty
   Extras tab is (the owner, 2026-10-14).

   A choice made on a chart lives on the chart only, never also in Settings (the owner, 2026-10-21): each choice has
   one place. The pattern chart's y-axis type (linear, square root or log) and the Experiment chart's x axis are on the
   chart's own selectors. The chart still keeps them in the app-settings store under the page's name (7), so the chosen
   scale is kept. The Experiment page has no other view options, so its Settings tab is disabled.
3. **One ini file on the desktop.** The store is `QSettings` in `IniFormat` on every desktop platform, one file named
   after the organisation and the application: `~/.config/EasyScience/EasyDiffraction.ini` on Linux and macOS,
   `%APPDATA%\EasyScience\EasyDiffraction.ini` on Windows. Not the native formats (a property list on macOS, the
   registry on Windows): the file is the same text on every platform, a user can read, copy or remove it, and a bug
   report can include it.
4. **The browser.** The web app keeps the `.ini` file only where the page's files persist across reloads (WasmFS on the
   browser's private file system or on IndexedDB). Otherwise the settings stay in the browser's own storage, as now.
   Which of the two the web app uses is decided by measurement: in each browser edi supports, the time to read the
   settings at start and to save a change, and whether a reload keeps them.
5. **The file is shown.** The app bar's settings show the settings file's full path, with "Open folder", which opens
   the folder in the system's file manager, and "Reset to defaults", which returns every setting to its default after
   a confirmation. In the web app the path reads "stored in this browser" and there is no "Open folder".
6. A demo capture or a test run keeps its own fresh settings folder (as now), so it never reads or writes the user's
   settings.
7. **The groups.** The store's groups are named for what holds them: `Appearance` (`colourScheme`, the one figure palette since
   2026-10-26, edi ADR-0038; a stored `patternColourScheme` of 2026-10-22 is read into it once and cleared; the Stacked
   and Map colours are chosen beside it in the dialog and kept in `ScanViews`), `Projects`
   (the defaults for new projects, `recent` and `last`), `Window` (`x`, `y`, `width`, `height` in logical pixels; a
   position on no screen is moved onto the primary screen), one group per page (`Analysis`: `scanPatternUpdates`),
   `PatternChart` for the one pattern chart every page shows (`yScale`, `structureCurves`, `legendShown`,
   `hoverShown`, `pointerMode`, `measuredStyle`; amended 2026-10-21: the Analysis and Experiment charts' y scales and the Experiment
   chart's x axis merged into it, the x axis being the project's own for every page, edi ADR-0017 §15), `ScanViews`
   for the Stacked and Map views (`stackedPalette`, `mapColours`, `mapSmooth`, `stackedReversed`; edi ADR-0041; the included range only is `Charts/includedOnly`, every pattern chart's), `Selections` (each project's structure, experiment and
   scan dataset file, keyed by the project's folder) and `ProjectViews` (each project's `stackedSpacing` and
   `mapDirection`, keyed by its folder; written when changed and at every save, so a project saved to a new folder
   takes them along). Today's `settings.ini` is carried over once: a key the store
   holds is never overwritten, the keys that moved go to their groups, and a marker keeps a later start from carrying
   anything again.

## Consequences

- Projects carry no machine state: two users' copies of a project stay identical whatever each of them chose to see.
- A new option that only changes the view goes in a page's Settings tab and the store, never into the `.edi` schema.
- Settings saved before this change are in today's file. The release that builds this decision carries over, once, the
  keys it keeps, so nobody loses their preferences.
- On macOS and Windows the settings are not where many applications keep theirs (a property list, the registry).
  Shown in the app bar's settings with "Open folder", the file is easy to find.
- The browser's choice of store waits for its measurement; until then the web app keeps its settings in local
  storage.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Native `QSettings` formats (a property list on macOS, the registry on Windows) | Rejected: a different store per platform, not one text file a user can read, copy, remove or attach to a report. |
| A user selector between the ini file and the native store | Not taken: the choice would itself have to be read from a fixed file before the settings are, switching would need the settings moved from one store to the other, and the web app has no choice to offer. |
| Page settings among each page's Extras | Rejected: Extras holds project data written to `.edi`, so options there look like part of the project. |
| A chart's display choices also in the page's Settings tab | Rejected by the owner: one choice in two places, and the chart already shows it. |
| View settings in the project's `.edi` files | Rejected: they would travel with a project to another machine and person, and a change of view would mark the project modified. |
