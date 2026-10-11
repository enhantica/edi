// SPDX-License-Identifier: BSD-3-Clause
#include "correlation_view_model.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <map>

namespace edi_app {

CorrelationViewModel::CorrelationViewModel(QObject* parent) : QObject(parent) {}

void CorrelationViewModel::setRecord(const edi::Project& project, int experiment, bool fitted) {
    names_.clear();
    matrix_.clear();
    reason_.clear();
    const std::vector<edi::FitParameterCorrelation>& pairs = project.fit_result.correlations;
    const int experiments = static_cast<int>(project.experiments.size());
    if (!project.fit_result.held() || pairs.empty()) {
        reason_ = tr("No correlations yet");
    } else if (experiment < 0 || experiment >= experiments || !fitted) {
        reason_ = tr("Not in the last fit");
    } else {
        // Another experiment's parameters are named by its datablock key (io.cpp's parameter slot walk).
        std::vector<std::string> others;
        for (int i = 0; i < experiments; ++i) {
            if (i != experiment) {
                others.push_back(edi::datablock_key(project.experiments[static_cast<std::size_t>(i)]->name,
                                                    "experiment") +
                                 ".");
            }
        }
        const auto shown = [&others](const std::string& name) {
            return std::none_of(others.begin(), others.end(),
                                [&name](const std::string& prefix) { return name.starts_with(prefix); });
        };
        std::map<std::string, std::size_t> index;
        for (const edi::FitParameterCorrelation& pair : pairs) {
            for (const std::string* name : {&pair.parameter_unique_name_i, &pair.parameter_unique_name_j}) {
                if (shown(*name) && !index.contains(*name)) {
                    index.emplace(*name, names_.size());
                    names_.push_back(*name);
                }
            }
        }
        const std::size_t n = names_.size();
        matrix_.assign(n * n, std::numeric_limits<double>::quiet_NaN());
        for (std::size_t i = 0; i < n; ++i) {
            matrix_[i * n + i] = 1.0;
        }
        for (const edi::FitParameterCorrelation& pair : pairs) {
            const auto i = index.find(pair.parameter_unique_name_i);
            const auto j = index.find(pair.parameter_unique_name_j);
            if (i != index.end() && j != index.end()) {
                matrix_[i->second * n + j->second] = pair.correlation;
                matrix_[j->second * n + i->second] = pair.correlation;
            }
        }
        if (n < 2) {
            names_.clear();
            matrix_.clear();
            reason_ = tr("No correlations for this experiment");
        }
    }
    // Each parameter's strongest correlation with another, and those strengths from the strongest down.
    const std::size_t n = names_.size();
    strength_.assign(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            const double value = matrix_[i * n + j];
            if (i != j && std::isfinite(value)) {
                strength_[i] = std::max(strength_[i], std::abs(value));
            }
        }
    }
    ranked_ = strength_;
    std::sort(ranked_.begin(), ranked_.end(), std::greater<>());
    // A new matrix keeps the parameter count and sets the level from it.
    if (n >= 2) {
        setMaxParameters(max_parameters_);
    } else {
        rebuild();
    }
}

void CorrelationViewModel::setLevel(double level) {
    level = std::isfinite(level) ? std::clamp(level, 0.0, 1.0) : 0.0;
    // The count follows: the parameters whose strongest correlation reaches the level (owner, 2026-10-11).
    const int count = static_cast<int>(std::count_if(strength_.begin(), strength_.end(),
                                                     [level](double strength) { return strength >= level; }));
    apply(level, strength_.size() >= 2 ? count : max_parameters_);
}

void CorrelationViewModel::setMaxParameters(int count) {
    const int available = static_cast<int>(strength_.size());
    count = std::clamp(count, 2, std::max(2, available));
    // The level follows: the strongest correlation of the count-th most correlated parameter, so that many remain.
    apply(available >= count ? ranked_[static_cast<std::size_t>(count - 1)] : level_, count);
}

void CorrelationViewModel::apply(double level, int count) {
    const bool level_changed = level != level_;
    const bool count_changed = count != max_parameters_;
    level_ = level;
    max_parameters_ = count;
    if (level_changed) {
        emit levelChanged();
    }
    if (count_changed) {
        emit maxParametersChanged();
    }
    rebuild();
}

void CorrelationViewModel::rebuild() {
    QStringList labels;
    QList<qreal> values;
    QString empty_text = reason_;
    const std::size_t n = names_.size();
    if (n >= 2) {
        // The parameters whose strongest correlation reaches the level, as diffraction-lib's
        // _filter_correlation_dataframe keeps them, and the most correlated of these.
        const std::vector<double>& strength = strength_;
        std::vector<std::size_t> kept;
        for (std::size_t i = 0; i < n; ++i) {
            if (strength[i] >= level_) {
                kept.push_back(i);
            }
        }
        std::stable_sort(kept.begin(), kept.end(),
                         [&strength](std::size_t a, std::size_t b) { return strength[a] > strength[b]; });
        kept.resize(std::min(kept.size(), static_cast<std::size_t>(max_parameters_)));
        std::sort(kept.begin(), kept.end());
        if (kept.size() < 2) {
            empty_text = tr("No pairs at this level");
        } else {
            for (std::size_t row : kept) {
                labels.append(QString::fromStdString(names_[row]));
                for (std::size_t column : kept) {
                    const double value = matrix_[row * n + column];
                    values.append(column < row && std::isfinite(value) && std::abs(value) >= level_
                                       ? value
                                       : std::numeric_limits<double>::quiet_NaN());
                }
            }
        }
    }
    // NaN never equals itself, so the values are compared bit for bit.
    const bool same_values =
        values.size() == values_.size() &&
        std::equal(values.begin(), values.end(), values_.begin(), [](qreal a, qreal b) {
            return std::bit_cast<std::uint64_t>(static_cast<double>(a)) ==
                   std::bit_cast<std::uint64_t>(static_cast<double>(b));
        });
    // The values first: the chart's cells are counted from the labels and read the values.
    if (!same_values) {
        values_ = values;
        emit valuesChanged();
    }
    if (labels != labels_) {
        labels_ = labels;
        emit labelsChanged();
    }
    if (static_cast<int>(n) != available_) {
        available_ = static_cast<int>(n);
        emit availableChanged();
    }
    if (empty_text != empty_text_) {
        empty_text_ = empty_text;
        emit emptyTextChanged();
    }
}

}  // namespace edi_app
