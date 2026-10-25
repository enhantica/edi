# Scan updates and stable view state

## Separate Every-pattern choices

Analysis, Settings, Pattern updates during a scan offers these distinct choices:

- Adaptive, the unchanged default;
- About once a second;
- Every pattern, fit waits for the display;
- Every pattern, display catches up;
- Only at the end.

The old saved Every-pattern setting is the integer zero in
`Preferences.scanPatternUpdates`. Reading it in a fresh application engine
must select **fit waits for the display**. The two Every-pattern choices must
remain separately selectable through the actual `analysis.patternUpdates`
control and reach the actual fit worker. The menu position is independent of
the stored identifier: catch-up follows fit-waits while old identifiers keep
their meanings. Adaptive remains independently
selectable after either one. The fresh-engine migration read instantiates only
a settings object. An earlier orphan PatternUpdatesGroup had no visual parent
and could disturb focus and layout. The adapted gate returns to the active
production window, reopens Analysis Settings, unfolds its group, finds the
visible selector and waits for each popup transition before the next choice.

Fit waits retains the existing behaviour: each fitted file is drawn before the
worker proceeds. Display catches up permits fitting to finish while drawing
is behind, retains every file, and draws the queued files in their original
order. `fit.scanFitted` counts scientific work; `scanPatternUpdates` counts
presented patterns and `scanShownFile` identifies the last presented file.
The actual status bar must say `Showing N of M` while behind, with N the
presented count. After the complete saved scan fits, M is its complete file
count. A final dataset selection alone does not prove that intermediate files
were drawn.

The behavioural gate opens a private copy of the saved 162-file scan, selects
the mode through the real UI, and observes shown-file receipts together with
actual window frames. It temporarily slows rendering through a test-only
observer, making backlog observable on fast GPU hosts as well as the VM.
The worker must finish before the queue drains. The delay is then removed,
and all saved files must be presented once, in ascending filename order,
ending on the final dataset. The measured timing cases never enable this
delay.

## Timing scope before and after the mode split

Previously the timing gate bounded the single Every-pattern mode against
Adaptive. It now bounds **display catches up** at no more than 1.05 times
Adaptive's fit duration, independently on Pattern and Stacked and on each
observed backend. Fit-waits duration and ratio are still measured and reported
without that bound. Old Every-pattern baseline measurements describe fit
waits; they cannot serve as catch-up evidence.

The producer selects the actual UI label in a native application host and
times scientific fitting through its real completion signal. Drawing may
finish later. Each sample records the selected label, visible tab, complete
file count, duration and native Qt API/renderer. Both tabs require separate
repeated samples for catch-up, fit-waits and Adaptive. Missing choices,
incomplete scans, absent receipts or mismatched modes fail before a timing
can be used. Software OpenGL and hardware results remain separate.

## Parameter edits and the Pattern y range

The owner amended the earlier holding rule: **only a pressed slider holds the
range**. While dragging, `chart.axis.y` keeps both endpoints when the calculated
curve stays inside. A curve leaving a boundary widens the range without
shrinking the opposite edge. Slider release fits once to the current measured
and calculated curves, allowing shrinkage. A typed commit and a discrete
parameter step also fit immediately, rather than retaining a previous envelope.
Another model or dataset, fit end and the existing zoom reset retain their
behaviour.

Before the amendment the gate typed background values and required their
range to hold. That expectation is retired. The adapted gate gives the real
experiment scale an independently excessive value, selects it in the actual
Analysis parameter group, and holds the real slider with pointer input.
It drags down inside the range, widens above it, then drags down again. Release
must shrink the range. The actual Qt axis endpoint signals count the commit;
each endpoint may change at most once, with an actual upper-endpoint change
for the deliberately shrinking release.

The gate reads actual `chart.series.calc` and `chart.measured` points, checks
containment, and compares the committed range with the existing fit-to-data
zoom reset at the same values. A typed round trip and a discrete value commit
exercise immediate refitting. Dataset and model replacements separately
exercise recomputation after an expanded range. `ProjectViewModel.adjusting`
is observed to prove that the pointer-held phase reaches the production
adjustment state. No second copy of the controller's range algorithm is used.

## First group in each sidebar tab

Every page and enabled sidebar tab starts with its first group unfolded when
no user state exists. A remembered user fold takes precedence. This is one
shared sidebar rule, including Settings; it does not introduce a new storage
lifetime for remembered state.

The gate gives each page a fresh private settings file, discovers its actual
enabled sidebar tabs, and orders groups by their visible header positions
within the selected page and tab. It records tabs without groups, including
the Home page's lack of a sidebar. For each foldable first group it checks the
fresh default, folds it through actual header input, leaves the page, returns
to that tab and checks the remembered fold. The older gate that required every
group to start folded now expects the first group open while retaining its
separator checks and the other groups' previous default.


Native captures retain one checked executable snapshot for the pytest run,
with its SHA-256 recorded in the log. A concurrent build may relink the
original path; later captures continue using the same retained artifact.
The fixture refuses a copy that straddles a relink, and cleans up its own
snapshots. Unit controls exercise both races.
