# 0082. Built-in tutorials generated from the docs plans

- **Status:** Accepted
- **Date:** 2026-11-09
- **Implementation:** 🟡 Partially implemented — the step kinds and the generator; every case's tutorial follows
- **Priority:** High
- **Forward constraint (binding on new features):** a built-in tutorial is generated from its case's docs plan
  (`tools/docs/app_tutorial_plan.py`), never written by hand; a new kind of action in a plan gets its step kind here
  before any tutorial uses it.

## Context

Every catalogue case has an app tutorial on the docs site, captured from a plan the case's Python tutorial gives:
each stage's actions, named by category (website/app_groups.py). The app's own Tutorials dialog held three tutorials
written by hand, on an older GUI. The owner wants one built-in tutorial per case, the user doing each step
while the tutorial points at the control and waits, and a check that replays each one to its end.

The tutorial panel (TutorialPanel.qml) already runs steps: each points at a control (`target`), says what to do
(`text`) and waits until its `check` holds; **Next** performs the check's action for a user who asks it to (`perform`).
Its vocabulary covers creating a project, building a structure by hand, one bundled pattern, free and fixed lists of
named parameters and the category and name filters. It cannot load from EasyDiffraction's collection, choose a
datablock, choose a fitting mode, fix a group, or set an ADP type, all of which the cases' plans use.

## Decision

1. **New step kinds**, each a `perform` (what Next does) and a `holds` (what the step waits for), as the user would do
   it in the app:
   - `example:<id>`: open the catalogue example from Project → Examples; holds when the open project is it.
   - `download:<kind>:<entry>=<name>`: load a structure, an experiment or a pattern from the EasyDiffraction
     collection through Load ▾ From web…; holds when the project has the block `<name>`.
   - `datablock:<name>`: the Parameters table's datablock filter on one structure or experiment; holds when it is.
   - `fitting-mode:<mode>`: the fitting mode on Analysis → Extra; holds when the project has it.
   - `group:<state>:<category>[:<datablock>][:<word>]`: one group action, as the app pages describe it: the category
     filter, the name filter for a part of one, then the Free column header's Free · all or Fixed · all; holds when
     every fittable parameter the filters show is free (or fixed).
   - `adp-type:<type>`: every atom site's ADP type on the Structure page; holds when each site has it.
   - `adp-iso:<value>` and `background-points:<position>=<intensity>,…`: the starting displacements and the
     background points of a project built by hand, as the Structure and Experiment tables set them.
2. **One tutorial per case, generated.** `tools/docs/app_builtin_tutorials.py` turns each case's docs plan into
   `app/tutorials/manifest.json` steps: each plan step a tutorial step, its target the step's first highlighted
   control, its text the app page's sentence for the stage, its check the step kind its actions are. Each tutorial
   carries the case's tags from the tag registry and its section; LBCO on HRPT comes first, under Getting started.
3. **The Interface tour stays hand-written** (it explains the window, not a fit) and follows the current GUI.
4. **The replay check drives the same steps.** It walks each tutorial with the panel's own navigation to its last step
   and requires every target to be a rendered control, so a renamed or removed control fails it.
5. **One visible action per step** (owner, 2026-11-10). The generator translates the plan's actions one to one:
   a field typed, an option chosen, a selector's token, a row added, the Free header's menu opened and its choice
   made, each its own step on that control (`field`, `pick`, `token`, `rows`, `free-menu`, `free-choice`); a web
   load is Load, From web, Search and the row; a fit is Fit, then closing its results. Only navigation (pages, tabs,
   reveals, commit keys, waits) has no step; any other action stops generation naming it.
6. **The cases are the tutorials** (owner, 2026-11-10). The Tutorials dialog lists the Interface tour and one
   tutorial per case. The hand-written Simulation and Fitting guides are gone; the LBCO simulation builds its
   structure and experiment by hand instead of opening its example (`app/tutorials/lbco-simulation-by-hand.json`).

## Consequences

- The docs pages and the built-in tutorials cannot tell a different story: both come from one plan and one wording.
- The panel's vocabulary grows by eight kinds; each new plan action needs its kind first (the forward constraint).
- A download step needs a collection source the app can reach; offline, the step says so and waits.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Run the docs plan's actions through the demo driver from a tutorial step | Rejected (2026-11-09): a built-in tutorial guides the user, who does each step. |
| Keep hand-written tutorials and add more | Rejected: three drifted from the GUI; twenty-five would drift the same way. |
| Free named parameters step by step, as the old Fitting tutorial did | Rejected: a group is freed in one action (the owner, 2026-11-09). |
