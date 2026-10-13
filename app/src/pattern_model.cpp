// SPDX-License-Identifier: BSD-3-Clause
#include "pattern_model.hpp"

#include <algorithm>
#include <vector>

namespace edi_app {

// ---- RangeViewModel -----------------------------------------------------------------------------

RangeViewModel::RangeViewModel(const edi::ExperimentBase& experiment, QObject* parent)
    : QObject(parent), experiment_(experiment) {
    sync();
}

void RangeViewModel::sync() {
    double minimum = 0.0, maximum = 0.0, step = 0.0, step_minimum = 0.0, step_maximum = 0.0;
    int points = 0;
    if (experiment_.data.has_value()) {
        try {
            const std::vector<double>& axis = experiment_.data->axis();
            points = static_cast<int>(axis.size());
            if (!axis.empty()) {
                minimum = *std::min_element(axis.begin(), axis.end());
                maximum = *std::max_element(axis.begin(), axis.end());
            }
            step = points > 1 ? (maximum - minimum) / (points - 1) : 0.0;
            // The steps between neighbouring points, in axis order.
            std::vector<double> sorted(axis);
            std::sort(sorted.begin(), sorted.end());
            for (std::size_t i = 1; i < sorted.size(); ++i) {
                const double gap = sorted[i] - sorted[i - 1];
                step_minimum = i == 1 ? gap : std::min(step_minimum, gap);
                step_maximum = i == 1 ? gap : std::max(step_maximum, gap);
            }
        } catch (const std::exception&) {
            points = 0;  // no single engaged axis: nothing to summarise (the pattern names why)
        }
    }
    const auto update = [this](auto& member, const auto& value, void (RangeViewModel::*signal)()) {
        if (member != value) {
            member = value;
            emit(this->*signal)();
        }
    };
    update(minimum_, minimum, &RangeViewModel::minimumChanged);
    update(maximum_, maximum, &RangeViewModel::maximumChanged);
    update(step_, step, &RangeViewModel::stepChanged);
    update(step_minimum_, step_minimum, &RangeViewModel::stepMinimumChanged);
    update(step_maximum_, step_maximum, &RangeViewModel::stepMaximumChanged);
    update(points_, points, &RangeViewModel::pointsChanged);
}

// ---- PatternModel -------------------------------------------------------------------------------

PatternModel::PatternModel(const edi::ExperimentBase& experiment, QObject* parent)
    : QAbstractListModel(parent), experiment_(experiment) {
    readAxis();
}

void PatternModel::readAxis() {
    count_ = 0;
    x_min_ = x_max_ = 0.0;
    if (!experiment_.data.has_value()) {
        calculation_error_ = QStringLiteral("the experiment has no data node: nothing to calculate over");
        return;
    }
    try {
        const std::vector<double>& axis = experiment_.data->axis();
        count_ = static_cast<int>(axis.size());
        if (!axis.empty()) {
            x_min_ = *std::min_element(axis.begin(), axis.end());
            x_max_ = *std::max_element(axis.begin(), axis.end());
        }
        axis_kind_ = experiment_.data->two_theta.has_value() ? TwoTheta : TimeOfFlight;
    } catch (const std::exception& refusal) {
        calculation_error_ = QString::fromUtf8(refusal.what());
    }
}

int PatternModel::rowCount(const QModelIndex& parent) const { return parent.isValid() ? 0 : count_; }

QVariant PatternModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() >= count_ || !experiment_.data.has_value()) {
        return {};
    }
    const edi::PdDataBase& data = *experiment_.data;
    const auto at = [row = static_cast<std::size_t>(index.row())](const std::vector<double>& values) -> QVariant {
        return row < values.size() ? QVariant(values[row]) : QVariant();
    };
    switch (role) {
        case XRole: return at(data.axis());
        case IntensityMeasRole: return at(data.intensity_meas);
        case IntensityMeasSuRole: return at(data.intensity_meas_su);
        case IntensityCalcRole: return at(published_calc_);  // gated when published (calculated())
        case DSpacingRole: return at(published_d_);
        case IntensityBkgRole: return at(published_bkg_);
        case ResidualRole: return at(published_residual_);
        case CalcStatusRole:
            return static_cast<std::size_t>(index.row()) < published_status_.size()
                       ? QVariant(QString::fromStdString(published_status_[index.row()])) : QVariant();
        default: return {};
    }
}

QHash<int, QByteArray> PatternModel::roleNames() const {
    return {{XRole, "x"},
            {IntensityMeasRole, "intensityMeas"},
            {IntensityMeasSuRole, "intensityMeasSu"},
            {IntensityCalcRole, "intensityCalc"},
            {DSpacingRole, "dSpacing"},
            {IntensityBkgRole, "intensityBkg"},
            {CalcStatusRole, "calcStatus"},
            {ResidualRole, "residual"}};
}

void PatternModel::markStale() {
    if (!stale_) {
        stale_ = true;
        emit staleChanged();
    }
}

void PatternModel::calculated(const QString& error) {
    const QString previous_error = calculation_error_;
    const int previous_count = count_;
    const double previous_min = x_min_, previous_max = x_max_;
    const AxisKind previous_kind = axis_kind_;
    calculation_error_.clear();
    readAxis();  // names an axis problem itself; otherwise the recalculation's refusal applies
    if (calculation_error_.isEmpty()) {
        calculation_error_ = error;
    }
    static const std::vector<double> kNone;
    // Only a calculation that describes the experiment as it is now.
    const std::vector<double>& calc = experiment_.data.has_value() && experiment_.computed_current()
                                          ? experiment_.data->intensity_calc.values()
                                          : kNone;
    // Published before the views are told, since they read it back (data()).
    const bool calc_changed = calc != published_calc_;
    published_calc_ = calc;
    const edi::PdDataBase* current = experiment_.data.has_value() && experiment_.computed_current()
                                       ? &*experiment_.data : nullptr;
    const auto d = current ? current->d_spacing.values() : std::vector<double>();
    const auto bkg = current ? current->intensity_bkg.values() : std::vector<double>();
    const auto residual = current ? current->residual.values() : std::vector<double>();
    const auto status = current ? current->calc_status.values() : std::vector<std::string>();
    const bool fields_changed = d != published_d_ || bkg != published_bkg_ ||
                                residual != published_residual_ || status != published_status_;
    published_d_ = d;
    published_bkg_ = bkg;
    published_residual_ = residual;
    published_status_ = status;
    if (count_ != previous_count) {
        beginResetModel();  // only when the data node itself changed (a load), never on an edit
        endResetModel();
        emit countChanged();
    } else if (count_ > 0 && (calc_changed || fields_changed)) {
        emit dataChanged(index(0), index(count_ - 1), {IntensityCalcRole, DSpacingRole, IntensityBkgRole, CalcStatusRole, ResidualRole});
    }
    if (x_min_ != previous_min) {
        emit xMinChanged();
    }
    if (x_max_ != previous_max) {
        emit xMaxChanged();
    }
    if (axis_kind_ != previous_kind) {
        emit axisKindChanged();
    }
    if (calculation_error_ != previous_error) {
        emit calculationErrorChanged();
    }
    if (stale_) {
        stale_ = false;
        emit staleChanged();
    }
}

}  // namespace edi_app
