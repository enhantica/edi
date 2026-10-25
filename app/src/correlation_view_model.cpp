// SPDX-License-Identifier: BSD-3-Clause
#include "correlation_view_model.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <map>

#include "edi/correlation_matrix.hpp"
#include "edi/io.hpp"

namespace edi_app {

CorrelationViewModel::CorrelationViewModel(QObject* parent) : QObject(parent) {}

void CorrelationViewModel::setRecord(const edi::Project& project, int experiment, bool fitted) {
    // The fit's own pairs; a scan file's (named by `file_path`) are the scan's, shown per dataset (setRows).
    std::vector<std::shared_ptr<const edi::FitParameterCorrelation>> rows;
    for (const auto& row : project.fit_result.correlations) {
        if (row->file_path.empty()) {
            rows.push_back(row);
        }
    }
    const int experiments = static_cast<int>(project.experiments.size());
    if (!project.fit_result.held() || rows.empty()) {
        show({}, {}, {}, tr("No correlations yet"));
    } else if (experiment < 0 || experiment >= experiments || !fitted) {
        show({}, {}, {}, tr("Not in the last fit"));
    } else {
        // The shown experiment's parameters only, as the report shows them (one core rule).
        std::vector<std::string> names;
        for (const auto& item : project.experiments) {
            names.push_back(item->name.value());
        }
        show({}, rows, edi::other_experiment_prefixes(names, static_cast<std::size_t>(experiment)),
             tr("No correlations for this experiment"));
    }
}

void CorrelationViewModel::setRows(const std::string& file,
                                   const std::vector<std::shared_ptr<const edi::FitParameterCorrelation>>& rows,
                                   const QString& absent) {
    const QString none = absent.isEmpty() ? tr("No correlations yet") : absent;
    show(file, rows, {}, rows.empty() ? none : tr("No correlations for this experiment"));
}

const std::vector<double>& CorrelationViewModel::numbers(
    const std::string& file, const std::vector<std::shared_ptr<const edi::FitParameterCorrelation>>& rows) {
    Numbers& kept = numbers_[file];
    bool same = kept.rows.size() == rows.size();
    for (std::size_t i = 0; same && i < rows.size(); ++i) {
        same = kept.rows[i] == rows[i].get() && kept.written[i] == rows[i]->correlation.written();
    }
    if (!same) {
        kept.rows.clear();
        kept.written.clear();
        kept.values.clear();
        kept.rows.reserve(rows.size());
        kept.written.reserve(rows.size());
        kept.values.reserve(rows.size());
        for (const auto& row : rows) {
            kept.rows.push_back(row.get());
            kept.written.push_back(row->correlation.written());
            kept.values.push_back(row->correlation.get());
        }
    }
    return kept.values;
}

void CorrelationViewModel::show(const std::string& file,
                                const std::vector<std::shared_ptr<const edi::FitParameterCorrelation>>& rows,
                                const std::vector<std::string>& hidden, const QString& reason) {
    names_.clear();
    matrix_.clear();
    reason_.clear();
    const auto shown = [&hidden](const std::string& name) {
        return std::none_of(hidden.begin(), hidden.end(),
                            [&name](const std::string& prefix) { return name.starts_with(prefix); });
    };
    std::map<std::string, std::size_t> index;
    for (const auto& row : rows) {
        for (const std::string* name : {&row->parameter_unique_name_i.value(), &row->parameter_unique_name_j.value()}) {
            if (shown(*name) && !index.contains(*name)) {
                index.emplace(*name, names_.size());
                names_.push_back(*name);
            }
        }
    }
    std::size_t n = names_.size();
    matrix_.assign(n * n, std::numeric_limits<double>::quiet_NaN());
    for (std::size_t i = 0; i < n; ++i) {
        matrix_[i * n + i] = 1.0;
    }
    if (n > 0) {
        const std::vector<double>& values = numbers(file, rows);
        for (std::size_t at = 0; at < rows.size(); ++at) {
            const auto i = index.find(rows[at]->parameter_unique_name_i.value());
            const auto j = index.find(rows[at]->parameter_unique_name_j.value());
            if (i != index.end() && j != index.end()) {
                matrix_[i->second * n + j->second] = values[at];
                matrix_[j->second * n + i->second] = values[at];
            }
        }
    }
    settle(reason);
}

void CorrelationViewModel::setTable(const edi::CorrelationTable& table) {
    // ADR-0034: the matrix straight from the table's numbers, its pairs i < j row by row (I2, I10).
    names_.clear();
    matrix_.clear();
    reason_.clear();
    if (table.names && table.values) {
        names_ = *table.names;
        const std::size_t n = names_.size();
        matrix_.assign(n * n, std::numeric_limits<double>::quiet_NaN());
        std::size_t at = 0;
        for (std::size_t i = 0; i < n; ++i) {
            matrix_[i * n + i] = 1.0;
            for (std::size_t j = i + 1; j < n && at < table.values->size(); ++j, ++at) {
                matrix_[i * n + j] = (*table.values)[at];
                matrix_[j * n + i] = (*table.values)[at];
            }
        }
    }
    settle(tr("No correlations for this experiment"));
}

void CorrelationViewModel::settle(const QString& reason) {
    std::size_t n = names_.size();
    if (n < 2) {
        names_.clear();
        matrix_.clear();
        reason_ = reason;
        n = 0;
    }
    // Each parameter's strongest correlation with another (the core filter, which the report shares).
    strength_ = edi::correlation_strengths(edi::CorrelationMatrix{names_, matrix_});
    if (n >= 2) {
        show();
    } else {
        rebuild();
    }
}

// The project's threshold (ADR-0036 §7): with one, the level is it; without, the count asked for sets it.
void CorrelationViewModel::show() {
    if (threshold_) {
        apply(*threshold_, static_cast<int>(edi::correlation_count_for_level(strength_, *threshold_)));
        return;
    }
    // The level follows the count by ADR-0036 §7's rule: the lowest that keeps at most that many, a tie kept
    // whole; the count then shows how many it keeps.
    const double level = edi::correlation_level_for_count(strength_, static_cast<std::size_t>(wanted_));
    apply(level, static_cast<int>(edi::correlation_count_for_level(strength_, level)));
}

void CorrelationViewModel::setThreshold(std::optional<double> threshold) {
    if (threshold == threshold_) {
        return;
    }
    threshold_ = threshold;
    if (strength_.size() >= 2) {
        show();
    }
}

void CorrelationViewModel::setLevel(double level) {
    level = std::isfinite(level) ? std::clamp(level, 0.0, 1.0) : 0.0;
    // The project keeps the level as its threshold; the count follows, the parameters reaching it (owner, 2026-10-11).
    ask(level);
}

void CorrelationViewModel::setMaxParameters(int count) {
    const int available = static_cast<int>(strength_.size());
    count = std::clamp(count, 2, std::max(2, available));
    wanted_ = count;
    if (available < 2) {
        apply(level_, count);
        return;
    }
    // The count sets the level by ADR-0036 §7's rule, and the project keeps that level.
    ask(edi::correlation_level_for_count(strength_, static_cast<std::size_t>(count)));
}

void CorrelationViewModel::ask(double level) {
    // The project applies it as an undoable edit and shows it back (setThreshold); a tab without one applies it here.
    if (receivers(SIGNAL(levelAsked(double))) > 0) {
        emit levelAsked(level);
    } else {
        threshold_ = level;
        show();
    }
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
        // Every parameter whose strongest correlation reaches the level, as diffraction-lib's
        // _filter_correlation_dataframe keeps them and as the report shows them (the core filter), with every pair
        // among them, whatever its size (owner, 2026-10-11).
        const edi::CorrelationSelection shown = edi::correlation_matrix(edi::CorrelationMatrix{names_, matrix_}, level_, n);
        if (shown.labels.size() < 2) {
            empty_text = tr("No pairs at this level");
        } else {
            for (const std::string& label : shown.labels) {
                labels.append(QString::fromStdString(label));
            }
            for (const double value : shown.values) {
                values.append(value);
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
