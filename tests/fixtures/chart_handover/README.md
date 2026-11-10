# Scene receipt and queue witnesses

`test_chart_handover.py` compiles the exact current production definitions of
`ProjectViewModel::handFollowed`, `presentedFollowed`, `awaitRender` and
`followRendered` into a small Qt Quick boundary executable. No method body is
rewritten, and a missing method or changed unsupported interface fails closed.
The adapter supplies a real `QQuickWindow`, Qt queued invocation and timers;
the sink merely records every presentation and release call. It supplies no
handover, identity or scheduling policy. This is a source-level component
witness, not an application rendering or scientific-fit test.

The actor hands over A, starts and synchronizes A's frame, retains its queued
GUI callback, then hands over B before delivering A's callback. The stale
callback must not present or release B, clear its identity, disarm its frame,
or cancel its timer. B must then present and release on its own frame, exactly
once. Both Pattern and selection predicates run, with distinct filenames and
with a repeated filename under a new token; matching filenames alone cannot
satisfy the repeated-file case. Compiler work is shared by the module and
recorded as fixture cost. No mount application build or executable is used.

`BackloggedFrames.qml` separately runs the real 162-file scan in catch-up mode
with a deliberately slow display. The native passive `PatternProof` records
`fit.scanShownFile`, `scanPatternUpdates` and the actual `chart.measured` source
points together at `QQuickWindow::afterSynchronizing`, plus nonempty actual
calculated-series coverage. Those measured points are the points consumed by
that synchronization, not a GUI grab made before or after it. The observer
compresses consecutive identical receipt/point observations; every changed
receipt or point vector remains in the evidence. No newest-worker filename,
current-dataset index or calculated intensity supplies the file identity.

Hidden Python assertions independently enumerate and parse the saved measured
files, checking ordered complete counts, receipt filenames, every actual
measured point against that file and an unchanged vector for duplicate counts.
Calculated-series nonemptiness is a presentation check, not a scientific golden.
The actor navigates to Home, Correlations and Evolution while a genuine queue
remains; completed frames there must neither count nor drain it. Returning to
the Pattern chart must finish every queued presentation. The observer requires
a rebuilt native helper; an older helper fails an explicit API guard. The actor
has its own bounded process and performs only one real scientific fit.

The backlog actor explicitly uses the normal `linePoints` measured style and
requires actual marker points before fitting. A fresh store's band style has
no marker source. During catch-up, real navigation checks the exposed control
and its checked state without requiring the whole window to stop polishing:
`statusBar.fit.showing` changes its text with each presented file. Once the
queue drains, the actor requires the window to finish polishing, so a genuine
perpetual polish loop cannot hide behind the live-input adaptation.
The native helper's wire `points` list contains interleaved finite x/y numbers;
the Python adapter validates complete pairs before applying the unchanged
independent measured-file comparison. The full receipt is written to a unique
owned JSON file, whose fresh publication/count are checked and whose bytes are
retained in the test's private receipt directory. Qt console output contains
only its safe filename and count, avoiding the console's truncation limit.
