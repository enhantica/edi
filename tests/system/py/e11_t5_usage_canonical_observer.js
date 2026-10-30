(function() {
    const all = testAppObjects.snapshot();
    function named(name) {
        const found = all.filter(x => Qt.isQtObject(x) && x.objectName === name);
        if (found.length !== 1) return null;
        return found[0];
    }
    const p = named('assistant.popup');
    if (!p) return {problems: ['actual unique Panel missing']};
    const usage = p.usageData;
    const session = SESSION_CALL;
    const weekly = WEEKLY_CALL;
    function pathOf(selected) {
        if (selected === null) return null;
        for (let b = 0; b < usage.buckets.length; ++b)
            for (let w = 0; w < usage.buckets[b].windows.length; ++w)
                if (selected === usage.buckets[b].windows[w]) return [b, w];
        return ['NOT_AN_ACTUAL_MEMBER'];
    }
    const dialog = named('assistant.usageDialog');
    function inside(item, root) {
        if (!item || !root || typeof item.mapToItem !== 'function') return false;
        for (let parent = item; parent; parent = parent.parent)
            if (parent === root) return item.Window.window === window;
        return false;
    }
    const rows = [];
    for (const key of ['session', 'weekly']) {
        const matches = all.filter(x => Qt.isQtObject(x) &&
            x.objectName === 'assistant.usage.' + key && inside(x, dialog.contentItem));
        for (const row of matches) {
            const percent = named(row.objectName + '.percent');
            const reset = named(row.objectName + '.reset');
            rows.push({key: key, current: inside(row, dialog.contentItem), visible: row.visible,
                sceneY: row.mapToItem(null, 0, 0).y, descriptor: row.modelData,
                selected_member: row.window === (key === 'session' ? session : weekly),
                percent: percent ? percent.text : null,
                percent_current: inside(percent, row),
                reset: reset ? reset.text : null, reset_current: inside(reset, row)});
        }
    }
    const button = named('assistant.usage');
    const connection = named('assistant.connection');
    const status = named('assistant.usageUnavailable');
    return {problems: [], owner: p.assistant === Session.assistant,
        imported_info: Qt.isQtObject(ApplicationInfo),
        usage: usage, canonical: Session.assistant.usage,
        plain_projection: Object.getPrototypeOf(usage) === Object.prototype,
        global: p.usageWindow, remaining: p.remainingPercent,
        session_path: pathOf(session), weekly_path: pathOf(weekly),
        independent_session: session === SESSION_CALL,
        independent_weekly: weekly === WEEKLY_CALL,
        strict_string_duration: STRING_CALL === null,
        account: p.accountData, canonical_account: Session.assistant.account,
        plan: p.accountPlan, plan_label: p.accountPlanLabel, initial: p.accountInitial,
        button: button ? button.text : null,
        caption: button ? button.ToolTip.text : null,
        accessible: button ? button.Accessible.name : null,
        connection: connection ? connection.text : null,
        rows: rows,
        status: status ? {visible: status.visible, text: status.text} : null};
})()
