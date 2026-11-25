// SPDX-License-Identifier: BSD-3-Clause
#include "toolbar_row.hpp"

#include <QVariant>

#include <algorithm>
#include <cmath>
#include <array>
#include <string_view>
#include <vector>

namespace edi_app {

namespace {

// Least important first. The owner's last four (2026-11-16) end it: subtract background, the intensity scale, the x
// axis and reset. A name not listed sits between the view options and the pointer modes.
constexpr std::array<std::string_view, 38> kOrder{
    "hover", "highlight", "legend", "structureCurves", "includedRange", "thinBars", "errorBars", "range", "smooth",
    "reverse", "labels", "moments", "polyhedra", "bonds", "axes", "cell", "projection", "a", "b", "c", "atomView",
    "atoms", "colors", "measuredStyle", "direction", "colourMap", "spacing", "rows", "singleCrystalQuantity",
    "quantity", "pan", "zoom", "subtractBackground", "yscale", "scale", "xaxis", "singleCrystalXAxis", "reset"};
constexpr int kUnlisted = 28;

struct Unit {
    double width = 0;
    QString group;
    int rank = 0;
    bool movable = false;
    bool shown = true;
    bool inMore = false;  // the view puts it in the More popup whatever the room
    bool axis = false;    // one of the structure view's a, b, c buttons, which move as one (decision 2026-11-22)
};

double rowWidth(const std::vector<Unit>& units, double spacing, double groupSpacing) {
    double width = 0;
    const Unit* before = nullptr;
    for (const Unit& unit : units) {
        if (!unit.shown) continue;
        if (before) width += before->group == unit.group ? spacing : groupSpacing;
        width += unit.width;
        before = &unit;
    }
    return width;
}

bool isBox(const QObject* item) { return item->property("closedTexts").isValid(); }
bool isControl(const QObject* item) { return isBox(item) || item->property("fontIcon").isValid(); }

QVariantMap unit(QQuickItem* item, const QString& group, bool movable) {
    return {{QStringLiteral("item"), QVariant::fromValue(static_cast<QObject*>(item))},
            {QStringLiteral("group"), group},
            {QStringLiteral("movable"), movable}};
}

}  // namespace

void ToolbarRow::collect(QQuickItem* lines, QQuickItem* more) const {
    if (lines == nullptr) return;
    QVariantList units;
    // Buttons straight in the row are one group until a spacer item; any other item is its own.
    int index = 0, direct = 0;
    const QList<QQuickItem*> children = lines->childItems();
    for (QQuickItem* child : children) {
        ++index;
        if (child == more) continue;
        if (child->property("toolbarUnits").toBool()) {
            int spacer = 0;
            const QList<QQuickItem*> own = child->childItems();
            for (QQuickItem* item : own) {
                if (isControl(item)) {
                    const QString group = isBox(item) ? QStringLiteral("box:") + item->property("toolbarGroup").toString()
                                                      : QStringLiteral("h%1:%2").arg(index).arg(spacer);
                    item->setParentItem(lines);
                    units.append(unit(item, group, true));
                } else if (item->width() > 0) {
                    ++spacer;
                }
            }
        } else if (isBox(child)) {
            units.append(unit(child, QStringLiteral("box:") + child->property("toolbarGroup").toString(), true));
        } else if (isControl(child)) {
            units.append(unit(child, QStringLiteral("d%1").arg(direct), true));
        } else if (!child->childItems().isEmpty()) {
            units.append(unit(child, QStringLiteral("other%1").arg(index), false));
        } else if (child->width() > 0) {
            ++direct;
        }
    }
    lines->setProperty("units", units);
    place(lines, more);
}

void ToolbarRow::place(QQuickItem* lines, QQuickItem* more) const {
    if (lines == nullptr || more == nullptr || !lines->isVisible()) return;
    const QVariantList all = lines->property("units").toList();
    QList<QQuickItem*> items;
    QVariantList input;
    for (const QVariant& entry : all) {
        const QVariantMap map = entry.toMap();
        auto* item = qobject_cast<QQuickItem*>(map.value(QStringLiteral("item")).value<QObject*>());
        if (item == nullptr || !item->isVisible()) continue;
        items.append(item);
        input.append(QVariantMap{{QStringLiteral("width"), item->width()},
                                 {QStringLiteral("group"), map.value(QStringLiteral("group"))},
                                 {QStringLiteral("name"), item->objectName()},
                                 {QStringLiteral("movable"), map.value(QStringLiteral("movable"))},
                                 {QStringLiteral("inMore"), item->property("toolbarInMore").toBool()}});
    }
    // The block selector, when it shares the row, reaches this far from the left edge.
    const double left = lines->property("leftEdge").toDouble() + lines->property("reservedLeft").toDouble();
    const QVariantMap result = layout(input, left, lines->property("rightEdge").toDouble(),
                                      lines->property("spacing").toDouble(), lines->property("groupSpacing").toDouble(),
                                      more->width());
    const QVariantList shown = result.value(QStringLiteral("shown")).toList(), xs = result.value(QStringLiteral("x")).toList();
    // The row's own width with nothing moved into More, which the block selector leaves it when the two share a row.
    {
        const QVariantMap whole = layout(input, 0, 1e9, lines->property("spacing").toDouble(),
                                         lines->property("groupSpacing").toDouble(), more->width());
        const QVariantList on = whole.value(QStringLiteral("shown")).toList(), at = whole.value(QStringLiteral("x")).toList();
        double low = 1e9, high = 0;
        for (qsizetype i = 0; i < items.size(); ++i) {
            if (!on.value(i).toBool()) continue;
            low = std::min(low, at.value(i).toDouble());
            high = std::max(high, at.value(i).toDouble() + items[i]->width());
        }
        if (whole.value(QStringLiteral("more")).toBool()) high = std::max(high, whole.value(QStringLiteral("moreX")).toDouble() + more->width());
        const double natural = high > low ? std::ceil(high - low) : 0.0;
        if (lines->property("naturalWidth").toDouble() != natural) lines->setProperty("naturalWidth", natural);
    }
    const double height = lines->implicitHeight();
    QVariantList overflow;
    for (qsizetype i = 0; i < items.size(); ++i) {
        QQuickItem* item = items[i];
        if (shown.value(i).toBool()) {
            item->setPosition({xs.value(i).toDouble(), std::round((height - item->height()) / 2)});
        } else {
            // Out of sight while it is in the popup; it keeps every binding and handler the copy calls.
            item->setPosition({-100000.0, 0.0});
            overflow.append(QVariant::fromValue(static_cast<QObject*>(item)));
        }
    }
    const bool any = result.value(QStringLiteral("more")).toBool();
    more->setVisible(any);
    more->setPosition({result.value(QStringLiteral("moreX")).toDouble(), std::round((height - more->height()) / 2)});
    if (lines->property("overflow").toList() != overflow) lines->setProperty("overflow", overflow);
}

int ToolbarRow::rank(const QString& name) {
    const QByteArray last = name.section(QLatin1Char('.'), -1).toUtf8();
    const auto it = std::find(kOrder.begin(), kOrder.end(), std::string_view(last.constData(), static_cast<std::size_t>(last.size())));
    if (it == kOrder.end()) return kUnlisted * 2 + 1;
    return static_cast<int>(it - kOrder.begin()) * 2;
}

QVariantMap ToolbarRow::layout(const QVariantList& list, double left, double right, double spacing,
                               double groupSpacing, double moreWidth) const {
    std::vector<Unit> units;
    units.reserve(static_cast<std::size_t>(list.size()));
    for (const QVariant& entry : list) {
        const QVariantMap map = entry.toMap();
        const bool inMore = map.value(QStringLiteral("inMore")).toBool() && map.value(QStringLiteral("movable")).toBool();
        const QString name = map.value(QStringLiteral("name")).toString();
        const QString last = name.section(QLatin1Char('.'), -1);
        units.push_back({map.value(QStringLiteral("width")).toDouble(), map.value(QStringLiteral("group")).toString(),
                         rank(name), map.value(QStringLiteral("movable")).toBool(), !inMore, inMore,
                         last == QLatin1String("a") || last == QLatin1String("b") || last == QLatin1String("c")});
    }
    const double room = right - left;
    bool more = std::any_of(units.begin(), units.end(), [](const Unit& unit) { return unit.inMore; });
    // With the ⋯ button the row ends in its own group.
    const auto needed = [&] { return rowWidth(units, spacing, groupSpacing) + (more ? groupSpacing + moreWidth : 0); };
    // A group of three or more never keeps one member alone: a lone "c" read as nothing (the owner, 2026-11-21).
    const auto lonely = [&units](const QString& group) -> Unit* {
        int members = 0, shown = 0;
        Unit* last = nullptr;
        for (Unit& unit : units) {
            if (unit.group != group || !unit.movable) continue;
            ++members;
            if (unit.shown) {
                ++shown;
                last = &unit;
            }
        }
        return members >= 3 && shown == 1 ? last : nullptr;
    };
    while (needed() > room) {
        // The lowest rank leaves first; of equal ranks, the rightmost.
        Unit* out = nullptr;
        for (Unit& unit : units)
            if (unit.shown && unit.movable && (!out || unit.rank <= out->rank)) out = &unit;
        if (!out) break;
        out->shown = false;
        // The a, b, c buttons leave together, all to More (the decision of 2026-11-22).
        if (out->axis)
            for (Unit& unit : units)
                if (unit.axis && unit.movable) unit.shown = false;
        if (Unit* alone = lonely(out->group)) alone->shown = false;
        more = true;
    }
    // A control that fits again comes back, the highest rank first: a wide one leaving could leave room for others,
    // and the row ended in ⋯ with room to spare (the owner, 2026-11-21).
    std::vector<Unit*> waiting;
    for (Unit& unit : units)
        if (!unit.shown && unit.movable && !unit.inMore) waiting.push_back(&unit);
    std::stable_sort(waiting.begin(), waiting.end(), [](const Unit* a, const Unit* b) { return a->rank > b->rank; });
    for (Unit* unit : waiting) {
        if (unit->shown) continue;
        // The a, b, c buttons come back together or not at all.
        std::vector<Unit*> together{unit};
        if (unit->axis) {
            together.clear();
            for (Unit& other : units)
                if (other.axis && other.movable) together.push_back(&other);
            if (std::any_of(together.begin(), together.end(), [](const Unit* other) { return other->inMore; })) continue;
        }
        for (Unit* member : together) member->shown = true;
        if (needed() > room || (!unit->axis && lonely(unit->group) == unit))
            for (Unit* member : together) member->shown = false;
    }
    more = std::any_of(units.begin(), units.end(), [](const Unit& unit) { return !unit.shown && unit.movable; });
    const double total = needed();
    double x = std::max(left, (left + right - total) / 2);
    QVariantList shown, xs;
    const Unit* before = nullptr;
    for (const Unit& unit : units) {
        shown.append(unit.shown);
        if (!unit.shown) {
            xs.append(0.0);
            continue;
        }
        if (before) x += before->group == unit.group ? spacing : groupSpacing;
        xs.append(x);
        x += unit.width;
        before = &unit;
    }
    if (more && before) x += groupSpacing;
    return {{QStringLiteral("shown"), shown},
            {QStringLiteral("x"), xs},
            {QStringLiteral("more"), more},
            {QStringLiteral("moreX"), x}};
}

}  // namespace edi_app
