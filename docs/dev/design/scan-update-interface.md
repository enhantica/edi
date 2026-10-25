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
control and reach the actual fit worker. Adaptive remains independently
selectable after either one.

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

While a parameter is adjusted, the actual Pattern chart's `chart.axis.y`
keeps both endpoints if the newly calculated curve lies inside them. If a
curve leaves either boundary, only widening is permitted: the new range must
contain the curve without shrinking the opposite edge. Selecting another
dataset or opening another model recomputes a fitted range. The user's zoom
reset and fit-end behaviour retain their existing meaning.

The range gate edits a real background intensity through the production
parameter field in a private saved project. It observes actual
`chart.series.calc` points and `chart.axis.y` endpoints after calculation and
rendering. Deliberate upper and lower excursions exercise widening; interior
edits and a parameter round trip exercise holding. User reset, switching a
saved bank, and opening another model exercise independent reset paths.
Expected holding comes from the previous visible range, not another copy of
the controller's range algorithm.

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
