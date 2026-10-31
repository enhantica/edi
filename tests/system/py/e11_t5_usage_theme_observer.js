(function(action, definition) {
    const all = testAppObjects.snapshot();
    function matches(name) {
        return all.filter(x => Qt.isQtObject(x) && x.objectName === name);
    }
    const captures = matches('e11.usageThemeCapture');
    if (action === 'absent') return {remaining: captures.length};
    if (action === 'cleanup') {
        if (captures.length !== 1) return {found: captures.length, restored: false};
        const capture = captures[0];
        capture.colors.theme = capture.originalTheme; // Existing public theme, restored exactly.
        const restored = capture.colors.theme === capture.originalTheme;
        capture.label = null; // TEST Connections only.
        capture.destroy();
        return {found: 1, restored: restored};
    }
    const panels = matches('assistant.popup'), buttons = matches('assistant.usage');
    if (panels.length !== 1 || buttons.length !== 1)
        return {problem: 'one actual current Panel/button required'};
    const panel = panels[0], button = buttons[0], label = button.contentItem;
    let capture = captures.length === 1 ? captures[0] : null;
    if (action === 'install') {
        if (captures.length !== 0) return {problem: 'capture already present'};
        capture = Qt.createQmlObject(definition, window, 'qrc:/tests/UsageThemeCapture.qml');
        capture.button = button;
        capture.label = label;
        capture.original = panel.assistant;
        capture.colors = EaStyle.Colors;
        capture.originalTheme = EaStyle.Colors.theme;
    } else if (!capture) {
        return {problem: 'actual capture missing'};
    }
    if (action === 'light') EaStyle.Colors.theme = EaStyle.Colors.LightTheme;
    else if (action === 'dark') EaStyle.Colors.theme = EaStyle.Colors.DarkTheme;
    else if (action !== 'install' && action !== 'snapshot') return {problem: 'unknown test action'};
    return {problem: '', owner: panel.assistant === Session.assistant,
        same_owner: panel.assistant === capture.original,
        same_button: button === capture.button, same_label: label === capture.label,
        same_colors: EaStyle.Colors === capture.colors,
        actual_window: label.Window.window === window,
        visible: button.visible && label.visible, enabled: button.enabled,
        hovered: button.hovered, down: button.down, visual_focus: button.visualFocus,
        remaining: panel.remainingPercent, text: button.text,
        theme: EaStyle.Colors.theme, dark: EaStyle.Colors.isDarkPalette,
        original_theme: capture.originalTheme,
        changes: capture.changes, actual: String(label.color),
        expected: String(EaStyle.Colors.themeForeground),
        matches_foreground: Qt.colorEqual(label.color, EaStyle.Colors.themeForeground)};
})(ACTION, DEFINITION)
