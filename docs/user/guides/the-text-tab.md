# The Text tab

Every page has a Text tab beside its Main and Extra tabs. It shows the `.edi` text a save writes for what the page
shows: the project's `project.edi` on Project, the selected structure or experiment on Structure and Experiment,
`analysis/analysis.edi` on Analysis and `reports/report.edi` on Report. The colours follow easydiffraction's:
datablock names orange, item names blue, loop column names green and `loop_` grey.

## What it shows

**Show**, at the tab's top right, chooses what the text holds:

- **Editable** (the default): the categories you set, such as the cell, the atom sites, the instrument, the peak
  profile, the background points and the constraints. This text can be edited.
- **Everything**: also the measured data and what the program computes, such as the calculated curves, the
  reflections and the fit results. This text is read-only.

Show is one setting for every Text tab. Changing it on one page changes it on all of them, and it is also in
Preferences > Appearance as "Text tab shows". It is saved with your preferences, not with the project.

## Editing and applying

Under Editable, type in the text as in any editor. The **✓** button at the top right is enabled once the text
differs from the project's. Clicking it applies the edit: edi reads the edited text exactly as it would read a
project file holding it, with every check an open runs, and only then changes the project. The measured data and
the results that Editable does not show are kept.

- An edit edi cannot read changes nothing. The text stays as you typed it, and the reason shows under the
  buttons, so you can correct it and apply again.
- An applied edit is one Undo step: Undo in the app bar puts the project back as it was before it.
- Under Everything, ✓ is disabled. Switch Show to Editable to edit the text.

If you leave an edit you have not applied (another structure or experiment, another page, or another Show choice),
edi asks "Discard changes?". Discard drops the edit. Cancel keeps it: the edited text is still there when you come
back to that block.

A scan project's datasets come from the scan's files, so a scan is edited on its pages, not as text.
