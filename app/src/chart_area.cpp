// SPDX-License-Identifier: BSD-3-Clause
#include "chart_area.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>

namespace edi_app {

namespace {

struct Row {
    double x = 0.0, upper = 0.0, lower = 0.0;
};

// The rows of one run, cut where an edge or the run itself leaves the limits.
class Run {
   public:
    Run(AreaEdges& area, const AreaRange& limits) : area_(area), limits_(limits) {}

    void add(const Row& row) {
        if (any_) cut(last_, row);
        put(row);
        last_ = row;
        any_ = true;
    }

   private:
    void put(const Row& row) {
        if (row.x < limits_.x_min || row.x > limits_.x_max) return;
        area_.upper.append(QPointF(row.x, std::clamp(row.upper, limits_.y_min, limits_.y_max)));
        area_.lower.append(QPointF(row.x, std::clamp(row.lower, limits_.y_min, limits_.y_max)));
    }

    void cut(const Row& from, const Row& to) {
        std::vector<double> at;
        const auto crossing = [&at](double a, double b, double limit) {
            if ((a < limit) != (b < limit)) at.push_back((limit - a) / (b - a));
        };
        for (const double limit : {limits_.y_min, limits_.y_max}) {
            crossing(from.upper, to.upper, limit);
            crossing(from.lower, to.lower, limit);
        }
        for (const double limit : {limits_.x_min, limits_.x_max}) crossing(from.x, to.x, limit);
        std::sort(at.begin(), at.end());
        for (const double t : at) {
            Row row{std::lerp(from.x, to.x, t), std::lerp(from.upper, to.upper, t), std::lerp(from.lower, to.lower, t)};
            // A crossing of an x limit is on it, whatever the rounding.
            row.x = std::clamp(row.x, limits_.x_min, limits_.x_max);
            put(row);
        }
    }

    AreaEdges& area_;
    const AreaRange& limits_;
    Row last_;
    bool any_ = false;
};

}  // namespace

AreaEdges area_edges(const QList<QPointF>& curve, const std::vector<double>& base, double floor, double lift,
                     const AreaRange& range) {
    AreaEdges area;
    const double width = range.x_max - range.x_min, height = range.y_max - range.y_min;
    if (!(width > 0.0) || !(height > 0.0) || !std::isfinite(width) || !std::isfinite(height)) {
        return area;
    }
    const AreaRange limits{range.x_min - width, range.x_max + width, range.y_min - height, range.y_max + height};
    area.upper.reserve(curve.size() + 2);
    area.lower.reserve(curve.size() + 2);
    const auto close = [&area, lift] {
        const QPointF bottom = area.lower.back();
        area.upper.append(QPointF(bottom.x(), bottom.y() + lift));
        area.lower.append(bottom);
    };
    std::optional<Run> run;
    for (qsizetype k = 0; k < curve.size(); ++k) {
        if (!std::isfinite(curve[k].x()) || !std::isfinite(curve[k].y())) {
            if (run && !area.lower.isEmpty()) close();
            run.reset();
            continue;
        }
        const auto at = static_cast<std::size_t>(k);
        const double low = at < base.size() ? base[at] : std::numeric_limits<double>::quiet_NaN();
        const double bottom = std::isfinite(low) ? low : floor;
        const Row row{curve[k].x(), std::max(curve[k].y(), bottom + lift), bottom};
        if (!run) {
            run.emplace(area, limits);
            if (!area.upper.isEmpty()) run->add({row.x, bottom + lift, bottom});
        }
        run->add(row);
    }
    return area;
}

}  // namespace edi_app
