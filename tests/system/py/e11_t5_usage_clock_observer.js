(function(action, definition) {
    const all = testAppObjects.snapshot();
    function matches(name) {
        return all.filter(x => Qt.isQtObject(x) && x.objectName === name);
    }
    const captures = matches('e11.usageClockCapture');
    if (action === 'cleanup') {
        if (captures.length !== 1) return {found: captures.length, destroyed: false};
        captures[0].timer = null; // ONLY test Connections target, not production Timer.
        captures[0].destroy();
        return {found: 1, destroyed: true};
    }
    if (action === 'absent') return {remaining: captures.length};
    const panels = matches('assistant.popup'), dialogs = matches('assistant.usageDialog');
    if (panels.length !== 1 || dialogs.length !== 1)
        return {problem: 'actual unique Panel/dialog missing'};
    const panel = panels[0], dialog = dialogs[0], timers = [];
    for (let i = 0; i < dialog.contentData.length; ++i) {
        const item = dialog.contentData[i];
        if (item instanceof Timer) timers.push(item);
    }
    if (timers.length !== 1) return {problem: 'one direct real Timer required'};
    const timer = timers[0];
    let capture = captures.length === 1 ? captures[0] : null;
    if (action === 'install') {
        if (captures.length !== 0) return {problem: 'capture already exists'};
        capture = Qt.createQmlObject(definition, window, 'qrc:/tests/UsageClockCapture.qml');
        capture.dialog = dialog;
        capture.panel = panel;
        capture.original = panel.assistant;
        capture.timer = timer;
    } else if (action !== 'snapshot' || !capture) {
        return {problem: 'snapshot requires installed capture'};
    }
    const before = Date.now(), clock = dialog.resetClock, after = Date.now();
    return {problem: '', wall_before: before, clock: clock, wall_after: after,
        connected: panel.assistant.connected, owner: panel.assistant === Session.assistant,
        same_original: panel.assistant === capture.original,
        imported_info: Qt.isQtObject(ApplicationInfo), visible: dialog.visible, opened: dialog.opened,
        interval: timer.interval, repeat: timer.repeat, running: timer.running,
        triggered_on_start: timer.triggeredOnStart, count: capture.count, events: capture.events};
})(ACTION, DEFINITION)
