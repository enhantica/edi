# 0064. Built-in tutorials as written steps

- **Status:** Accepted
- **Date:** 2026-11-02
- **Implementation:** 🟡 Partially implemented — the written steps, their callouts and the temporary project are in;
  playing the steps in the app comes later
- **Priority:** Medium

## Context

Home's tutorial buttons were disabled placeholders. New users need a guided start: where everything is, how to simulate
a pattern from a structure defined by hand, and how to fit one. Later the same tutorials should play themselves through
the app's emulated actions; the step scripts written now are what that player will run.

## Decision

- The tutorials are one file, `app/tutorials/manifest.json`. Each has an `id`, a title, a description, a `project` rule
  and its steps; a step has a title of one to three words (`title`, such as Space group or Free the B iso), names the
  control it is about (`target`, an object name) and says what to do (`text`) and what should hold after it
  (`expected`). It may name the control that leads to it (`via`), the condition that is its state (`check`, such as
  `space-group:221`, `open:group.cell` or `fits:1`) and whether it opens the tab it describes (`open`). The Interface
  tour's steps are their own file, `app/tutorials/tour.json`, one list per page keyed by object name, for the
  documentation and later tours to share. The first three are `interface` (Interface tour), `simulation` and `fitting`.
- Home → Tutorials lists them, one row each, so the list grows with the file, as the Examples list draws an example
  (`ExampleCell`): number, title with its chips (`tags`, in the examples' tones from `app/examples/tags.json`, a neutral
  Tour chip for the Interface tour) and a one-line description, under the Examples list's filters (`ExampleFilters`, the
  one filter bar both lists use, over the same list model): a search and a property with its values and counts, the
  values coming from the tutorial's `family:value` tags. A click anywhere on a row starts its tutorial, as a click on an
  Examples row opens the example: the same row, hover tint and pointer. A tutorial shows its steps one at a time in a
  callout that leaves the page usable: the step's title with Step n of N at the right of the same line, and the text.
  The tutorial's name opens its first step's text and is the tooltip of the status bar's Step n of N. Each step names
  its page, which opens as the step shows; every change of page is a step of its own, pointing at the page's app bar tab
  ("Open the Analysis page"), before the steps on that page.
- A step that needs a closed group or another tab first has a step of its own asking to open it ("Open the Cell group"),
  done once it is open. Every step also sets up its whole context itself, the same on Next, Back or a jump, never
  relying on an earlier step: its page; the copy of its control on that page that has content (pages and tabs share
  names: a category has a group on Main and one on Extra) on the step's sidebar tab, which is the step's `tab` or else
  the tab the last sidebar-tab step on its page opened; that copy's sidebar or main-view tab made current; every folded
  group around it unfolded, and the group itself when the step is on a group; and its list scrolled only as far as
  needed, from the nearest edge. Only lists that scroll up and down are scrolled: setting a tab view's sideways list
  while it slid stopped it half way, leaving an emptied tab on screen under the new tab's name.
- No step lands on a disabled control in the loaded project unless the control is disabled by design there, and then its
  text says when it becomes enabled (Stacked and Map: when the experiment is a scan). A step on a sidebar tab with no
  controls yet says only "<Tab>: not used on this page yet."; a step on a tab with controls names them. Every group the
  app shows on every tab of every page with the LBCO example loaded has a step.
- The callout and its pointer are one shape, one fill and one 1 px border, drawn by the curve renderer, so no seam shows
  and its edges are smooth. It sits beside the control the step names, found by object name (ADR-0066), at a small fixed
  gap on the first side with room: right, left, below, above, sliding along that side to stay in the window, never
  covering the control or the status bar's strip. The pointer is always the same size and reaches across the gap, aiming
  at the field or box itself rather than its labelled row, and the control is outlined. On every Next or Back the
  callout fades out (about 150 ms), the step's page, tab, groups and list change, and once nothing moves any more (its
  control twice in the same place) it fades in at its final place with the new step, so it never moves with its control;
  the status bar's Step n of N changes with the fade-in. It follows the control when the window is resized or the
  control appears. A control that cannot be shown is pointed at through the nearest group holding it (its header), else
  the step's `via` control; a step whose control is not found shows no callout.
- The callout is the dialog background with a faint tint of the accent colour, fully opaque, with a 1 px border in a
  pale blue only a little darker than it; Step n of N, in the callout and the strip, is in the app's accent colour, the
  one of unfolded group names and selected tabs; the callout's padding is the same on all four sides, measured from what
  shows (the top of the heading's letters, the bottom of the icons' glyphs), so the icon buttons' taller hit area adds
  no space below; the text keeps the theme's colours.
- The callout's actions sit at its bottom right as one row (`TutorialControls`), the status bar's strip using the same:
  Stop (x), Back and Next (chevrons) with equal gaps, Next shown but off on the last step, where Stop ends the tutorial,
  each with a tooltip. In the callout they are plain icons, without background or border; in the status bar the bar's
  light round buttons, as the assistant's status buttons. The last step's choices, in every tutorial (`completion`), are
  Discard and Keep this project in place of the callout's Stop. The left and right arrow keys step back and on and
  Escape stops, while no text field, list or other control that takes those keys has the focus.
- While a tutorial runs, the status bar shows a strip, a group of its own at its far right after the whole fit area, a
  separator between them, so the fit status appearing never moves its buttons: Step n of N and the same row of Stop,
  Back and Next, acting on the same tutorial as the callout's; one set of actions, two views of it. The strip goes when
  the tutorial ends, and the status bar shows during a tutorial on Home too.
- A step about one parameter names it, never its row: `parameters.su@La.adp_iso` is the s.u. cell of the parameters
  table's row whose path ends so, `correlations.cell@La.adp_iso|Ba.adp_iso` the Correlations square of the two. A step
  about a whole area (`workflow.<page>.mainContent`) has a callout without a pointer, centred in the app window as a
  dialog is; only when that would cover what the step names (the area itself, unless the step's `coversTarget` says it
  names nothing in it) or the status bar's strip does it move to the nearest place clear of them. A step selecting a
  parameter (`parameters.name@<path>`, check `selected`) scrolls the table only as far as its row needs and makes the
  row current, so the slider acts on it; the callout keeps clear of that row and of the slider. Simulation changes four
  parameters this way, each with the table's filter (cell a with the Cell category, the wavelength with the name filter
  "wave", La's B iso with Atomic displacement, the peak width W with Peak profile): filter, select the row, change it
  with the slider (Next sets a fixed value) and watch the pattern, then clear the filters.
- The callout is drawn above every dialog and popup, so a step can point into a dialog's field; it keeps clear of that
  dialog's other fields and buttons, and a callout for a control in the main view keeps clear of the sidebar. A step on
  a control in a dialog whose dialog closes goes on when its action is done, else back to the step that opens it. A
  control the reveal cannot find is looked for only on the step's own sidebar tab: clicking through the tabs left a
  closed dialog's step on whichever tab came last.
- A step comes while its control can still act: one asking to keep or set a value comes before what disables it (the
  experiment's type before its data are loaded). The pointer's point stops a few pixels short of its control in every
  direction. A fit's results window is part of the walk: Fitting has a step on it after the first fit (status, reduced
  chi-squared, R values; OK), and every later fit step goes on only once its results are closed. Fitting frees its
  parameters in stages with the table's own tools: the category or name filter, the free column's menu, which acts on
  the rows shown, the fit, and the eraser before the next stage.
- In every tutorial, the Interface tour's included, the temporary project's last step offers Keep working on <project>
  and Return to my project, or Close <project> when no project was open, named from the real projects, each in one
  sentence, on their own row above the back button; Stop there returns to the user's project.
- A step that asks for an action goes on by itself as soon as its `check` holds through a change made while it is shown,
  never on arriving with it already true, so Back onto a done step stays there. Next on such a step does the action
  through the step's own control, as the user would (Create a new project and the dialog's OK, with what the form holds;
  the free column's Free, acting on the rows the filters show), and goes on: at once, or once it is done for one that
  takes time (a fit, asked again while the project still recalculates). The files step saves the tutorial's files to a
  temporary folder, and the steps loading them load from there, with no file dialog; in the browser they are downloaded,
  and Next loads them from a copy in the browser's memory, where its file chooser puts the files it opens. A step's
  `check` tests the scientific state it teaches, not only that something was done: the sites' occupancies, which
  parameter each alias names, a fit that succeeded. A step whose value is already set when it starts says it is
  preselected and what it means, and waits for Next, as every step that only explains does. The Interface tour explains,
  apart from its page changes and its fit on Analysis (Fit or Next runs it, then its results, Pattern after the fit and
  the filled Correlations), which are action steps.
- A tutorial with `"project": "temporary"` never works in the user's project. The open project is set aside in the
  session as it is, unsaved changes included (`Session.setProjectAside`, `openExampleAside`, `createProjectAside`).
  Simulation and Fitting (`"start": "aside"`) then open no project: their first step, on Home, says the user's project
  is put aside until the end and points at Start; on the Project page the user then creates and names the tutorial's
  project with Create a new project, which makes it unsaved and asks for no location, and asks nothing about the user's
  project held aside, changed or not; no project is made without the user. The creation dialog has two steps: Name,
  where Next types lbco into an empty Name field as if typed and keeps a name the user typed, then OK, which the user or
  Next clicks. Its title, authors and description fields say they are optional. The replacement guard lets that first
  project through, since it replaces nothing of the tutorial's. A tutorial may also start a new project itself
  (`"start": "new"`) or open a bundled example (`"start": "example:<id>"`); the Interface tour opens the LBCO example.
  At the end of Simulation or Fitting the user keeps the tutorial's project, which stays open unsaved and closes the
  set-aside one, or discards it; Discard and Stop bring the set-aside project back as it was (`"stop":
  "restore-user-project"`), or no project if there was none.
- Fitting builds its project the way a user's starts: from a structure CIF and a measured pattern. The two files are
  bundled with the app (`app/tutorials/files`: `lbco.cif` and `hrpt.xye`, from the `pd-neut-cwl_lbco-hrpt` example;
  `hrpt.xye` is byte for byte its source, sha256 `70dba3f6...`), and a step's "Save tutorial files" link writes them to
  a folder the user picks, or downloads them in the browser. The experiment values an .xye file does not carry (zero
  shift, U and Y, the scale) are the example's start, set in their steps. The fit goes in stages: the scale and the
  background, then the cell and the zero shift, then the peak profile, then every B_iso; La's and Ba's large
  uncertainties and their correlation then lead to the aliases and the constraint, and a last fit.
- One tutorial runs at a time: Tutorials' buttons are off while one runs, and the session refuses to set a second
  project aside. A pending Text-tab edit is applied before the project is set aside. Anything that would replace the
  tutorial's project or quit the app (open, new project, the app bar's reset, closing the window) asks about the user's
  project first when it has unsaved changes: Cancel goes on with the tutorial, Save or Discard brings that project back,
  ends the tutorial and goes ahead. With no unsaved changes it brings the user's project back and goes ahead. The
  set-aside project keeps its browser copy and place, so Save writes where it did before.
- An example or a read-only project is copied into the session's temporary folder under its own name, or the name with
  `-2`, `-3`, ... when the open project or the set-aside one still works in that folder. A new copy never replaces the
  files of a live project, whether it came from the same example before a tutorial, during one or after Keep.

## Consequences

- Adding a tutorial is adding an entry to the manifest; a step's target must be an object name that exists in the app.
- The player that plays the steps by emulated actions reads the same entries.
