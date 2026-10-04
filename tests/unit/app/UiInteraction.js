.pragma library

// The base keeps non-current SwipeView pages alive. Scope lookups to the selected
// page, then test clipping geometry. A decorative z:2 TabBar background does not
// accept input, so stacking order alone is not an exposure oracle.
function page(window) {
    return window.contentArea[window.appBarCentralTabs.currentIndex];
}

function windowRoot(window) {
    let root = window.contentItem;
    while (root.parent) root = root.parent;
    return root;
}

function target(control) {
    if (!control || !control.objectName.startsWith("group.")) return control;
    //  note 8: only explicitly untitled, fixed-open groups use content
    // as their exposure target. A missing/hidden ordinary header still fails.
    if (control.title === "" && control.collapsible === false && control.collapsed === false)
        return control.contentItem;
    return control.titleArea;
}

function clickPoint(control) {
    if (!control || !control.visible || control.width <= 0 || control.height <= 0)
        return null;
    let left = 0, top = 0, right = control.width, bottom = control.height;
    for (let parent = control.parent; parent; parent = parent.parent) {
        if (parent.clip) {
            const clip = control.mapFromItem(parent, 0, 0, parent.width, parent.height);
            left = Math.max(left, clip.x);
            top = Math.max(top, clip.y);
            right = Math.min(right, clip.x + clip.width);
            bottom = Math.min(bottom, clip.y + clip.height);
        }
    }
    // A partially clipped row is actionable through its visible portion. Never
    // click through a viewport boundary merely because the delegate exists.
    return right > left && bottom > top ? {x: (left + right) / 2, y: (top + bottom) / 2} : null;
}

function exposed(control) {
    return clickPoint(control) !== null;
}

function scrollIntoView(control) {
    // A table's own positioning does not scroll an enclosing sidebar Flickable.
    // Move viewports only; the row's production action still needs real input.
    for (let parent = control.parent; parent; parent = parent.parent) {
        if (typeof parent.contentY !== "number" || parent.contentHeight <= parent.height)
            continue;
        const rect = control.mapToItem(parent, 0, 0, control.width, control.height);
        if (rect.y < 0 || rect.y + rect.height > parent.height) {
            const origin = typeof parent.originY === "number" ? parent.originY : 0;
            parent.contentY = Math.max(origin, Math.min(origin + parent.contentHeight - parent.height,
                parent.contentY + rect.y + rect.height / 2 - parent.height / 2));
        }
    }
}

function rendered(item) {
    if (!item || !item.visible || item.width <= 0 || item.height <= 0)
        return false;
    for (let parent = item.parent; parent; parent = parent.parent) {
        if (parent.clip) {
            const first = item.mapToItem(parent, 0, 0);
            const last = item.mapToItem(parent, item.width, item.height);
            if (last.x <= 0 || last.y <= 0 || first.x >= parent.width || first.y >= parent.height)
                return false;
        }
    }
    return true;
}

function find(root, name) {
    if (!root || !root.visible)
        return null;
    if (root.objectName === name && rendered(target(root)))
        return root;
    // Repeater/ListView delegates are visual children, not necessarily QObject children.
    const children = root.children || [];
    for (let i = 0; i < children.length; ++i) {
        const found = find(children[i], name);
        if (found !== null) return found;
    }
    return null;
}

function control(probe, window, name) {
    const root = /^(appBar|home|warning|warnings|statusBar)\./.test(name) ? windowRoot(window) : page(window);
    return find(root, name);
}

function moving(root) {
    if (root.moving === true) return true;
    const children = root.children || [];
    return children.some(child => moving(child));
}

function inPane(control) {
    // Inventory/discovery permits vertical scrolling, but never another
    // horizontal SwipeView pane. Input still requires full clipping checks.
    if (!control || !control.visible || !(control.width > 0)) return false;
    for (let parent = control.parent; parent; parent = parent.parent) {
        const point = control.mapToItem(parent, control.width / 2, control.height / 2);
        if (parent.clip && (point.x < 0 || point.x >= parent.width)) return false;
    }
    return true;
}

function groupNames(root) {
    if (!root || !root.visible) return [];
    let names = [];
    if (root.objectName.startsWith("group.")) {
        const header = target(root);
        if (!header) return names;
        if (inPane(header)) names.push(root.objectName.slice(6));
    }
    const children = root.children || [];
    children.forEach(child => names = names.concat(groupNames(child)));
    return names;
}

function text(root) {
    if (!root || !root.visible) return "";
    let result = typeof root.text === "string" && rendered(root) ? root.text : "";
    const children = root.children || [];
    children.forEach(child => result += "\n" + text(child));
    return result;
}

function click(testCase, probe, window, name) {
    testCase.verify(testCase.waitForPolish(window, 2000),
                    "I10/I19: layout updates finish before locating real input");
    testCase.tryVerify(() => {
        const found = control(probe, window, name);
        return found !== null && found.enabled && exposed(target(found));
    }, 2000, "I10/I19: real input target is enabled and inside the visible viewport: " + name);
    const item = target(control(probe, window, name));
    // A ListView can deliberately defer presses (the pinned base uses pressDelay).
    // Exercise that real event path with its declared delay, not a zero-duration click.
    let inputDelay = 0;
    for (let parent = item.parent; parent; parent = parent.parent)
        if (typeof parent.pressDelay === "number")
            inputDelay = Math.max(inputDelay, parent.pressDelay + 1);
    const point = clickPoint(item);
    testCase.mouseClick(item, point.x, point.y, undefined, undefined, inputDelay);
    testCase.verify(testCase.waitForRendering(window.contentItem),
                    "I10/I19: real input is followed by a rendered frame");
    if (name.includes(".tab."))
        testCase.tryCompare(item, "checked", true, 2000,
                            "I10/I19: real input selects the requested tab: " + name);
    testCase.tryVerify(() => !moving(window.contentItem), 2000,
                       "I10/I19: the selected viewport finishes moving before the next input");
}

function expandGroup(testCase, probe, window, name) {
    let group = null;
    testCase.tryVerify(() => {
        group = control(probe, window, name);
        return group !== null;
    }, 2000, "I10/I19: the group exposure target belongs to the active visible pane: " + name);
    testCase.verify(group !== null, "I10/I19: the selected page owns the requested group: " + name);
    scrollIntoView(target(group));
    if (group.collapsed) click(testCase, probe, window, name);
    testCase.tryVerify(() => !group.collapsed && Math.abs(group.height -
        (group.titleArea.height + group.spacing + group.contentHeight + group.bottomPadding)) < 0.01,
        2000, "I10/I19: group expansion finishes before its content is positioned or used: " + name);
}
