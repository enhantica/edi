// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QList>
#include <QPointF>
#include <vector>

namespace edi_app {

// An area's two edges for Qt Graphs.
struct AreaEdges {
    QList<QPointF> upper, lower;
};

// The ranges of the axes an area is drawn on.
struct AreaRange {
    double x_min = 0.0, x_max = 0.0, y_min = 0.0, y_max = 0.0;
};

// The area between `curve` and, per point, its base (not finite: `floor`). It holds the drawn points only: a gap (an
// excluded region, or a value the log scale cannot show) is not a point an area can take, so the area closes onto its
// base at each gap instead of bridging it. The upper edge keeps `lift` above the lower one: where the two met (a curve
// on its base, or a closed gap) Qt Graphs filled the area as a fan from its first point or not at all.
// Both edges end one range outside `range`, where nothing is seen: Qt fills an area by triangulating all of it, and a
// point far outside the plot crashed that.
AreaEdges area_edges(const QList<QPointF>& curve, const std::vector<double>& base, double floor, double lift,
                     const AreaRange& range);

}  // namespace edi_app
