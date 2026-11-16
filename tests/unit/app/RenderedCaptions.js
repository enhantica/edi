.pragma library
.import "RenderedTable.js" as Render
.import "UiInteraction.js" as Ui

function field(owner) {
    return typeof owner.shortPrettyName === "string" &&
        (owner.shortPrettyName !== "" || (typeof owner.uid === "string" && owner.uid !== ""));
}

function titleItems(owner, probe, iconsFont) {
    // Identify the label by its visual role, never by equality to its backing text.
    return Array.from(owner.children || []).filter(item =>
        item !== owner.contentItem && item !== owner.contentItemLabel && item !== owner.indicator &&
        probe.inheritsType(item, "QQuickLabel") && item.font.family !== iconsFont && Ui.rendered(item));
}

function row(kind, owner, label, index) {
    return {
        kind: kind,
        owner: owner.objectName || owner.uid || String(owner).split("(")[0],
        slot: index,
        text: label ? label.text : null,
        width: label ? label.width : 0,
        height: label ? label.height : 0,
        enabled: owner.enabled
    };
}

function fields(owner, probe, iconsFont) {
    const labels = titleItems(owner, probe, iconsFont);
    if (!labels.length)
        return [row("field", owner, null, 0)];
    return labels.map((label, index) => row("field", owner, label, index));
}

function group(owner, probe, iconsFont) {
    const labels = Render.descendants(owner.titleArea).filter(item =>
        probe.inheritsType(item, "QQuickLabel") && item.font.family !== iconsFont && Ui.rendered(item));
    return labels.length ? labels.map((label, index) => row("group", owner, label, index)) :
        [row("group", owner, null, 0)];
}

function headers(owner, probe, iconsFont) {
    const labels = Render.descendants(owner.headerItem).filter(item =>
        probe.inheritsType(item, "QQuickLabel") && item.font.family !== iconsFont && Ui.rendered(item) &&
        (item.text !== "" || (typeof item.uid === "string" && item.uid !== "")));
    return labels.length ? labels.map((label, index) => row("header", owner, label, index)) :
        [row("header", owner, null, 0)];
}
