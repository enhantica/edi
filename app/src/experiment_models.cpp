// SPDX-License-Identifier: BSD-3-Clause
#include "experiment_models.hpp"

#include <cmath>

#include <QVariantMap>
#include <QtNumeric>
#include <algorithm>
#include <exception>
#include <optional>

#include "edi/edits.hpp"
#include "edi/selectors.hpp"
#include "edi/su_text.hpp"
#include "parameter_item.hpp"
#include "parameter_registry.hpp"
#include "project_editor.hpp"

namespace edi_app {

// ---- ParameterListModel -------------------------------------------------------------------------

ParameterListModel::ParameterListModel(Fields fields, ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"parameter", "name", "displayName", "shortName", "displayUnits", "usedByProfile"}, parent),
      fields_(std::move(fields)),
      registry_(registry) {
    sync();
}

void ParameterListModel::sync() {
    QList<Row> rows;
    int used_count = 0;
    for (const edi::CategoryField& field : fields_()) {
        used_count += field.used_by_profile ? 1 : 0;
        const edi::ParameterSpec* spec = field.parameter->spec;
        const ParameterItem* item = registry_.find(field.parameter);
        rows.append({field.parameter,
                     {parameter_role(registry_, field.parameter), QString::fromStdString(field.name),
                      spec != nullptr ? QString::fromUtf8(spec->display_name) : QString::fromStdString(field.name),
                      item != nullptr ? item->shortName() : QString::fromStdString(field.name),
                      spec != nullptr ? QString::fromUtf8(spec->display_units) : QString(), field.used_by_profile}});
    }
    setTableRows(rows);
    if (used_count != used_count_) {
        used_count_ = used_count;
        emit usedCountChanged();
    }
}

ParameterItem* ParameterListModel::parameterNamed(const QString& name) const {
    for (int row = 0; row < count(); ++row) {
        if (get(row, QStringLiteral("name")).toString() == name) {
            return qobject_cast<ParameterItem*>(get(row, QStringLiteral("parameter")).value<QObject*>());
        }
    }
    return nullptr;
}

// ---- BackgroundListModel ------------------------------------------------------------------------

BackgroundListModel::BackgroundListModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                         ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"id", "position", "intensity"}, parent), experiment_(experiment), editor_(editor), registry_(registry) {
    sync();
}

void BackgroundListModel::sync() {
    QList<Row> rows;
    for (const auto& point : experiment_.background) {
        rows.append({point.get(), {QString::fromStdString(point->id.value()), point->position.get(), parameter_role(registry_, &point->intensity)}});
    }
    setTableRows(rows);
}

bool BackgroundListModel::setId(int row, const QString& id) {
    auto* point = const_cast<edi::LineSegment*>(static_cast<const edi::LineSegment*>(keyAt(row)));
    return point != nullptr &&
           editor_.apply_background_edit(experiment_, edi::Edit::background_id(*point, id.toStdString()), true).isEmpty();
}

bool BackgroundListModel::setPosition(int row, double position) {
    auto* point = const_cast<edi::LineSegment*>(static_cast<const edi::LineSegment*>(keyAt(row)));
    return point != nullptr &&
           editor_.apply_background_edit(experiment_, edi::Edit::background_position(*point, position), false).isEmpty();
}

void BackgroundListModel::append() {
    edi::ExperimentBase& experiment = experiment_;
    edi::LineSegment point;
    if (experiment.background.size() > 0) {
        const edi::LineSegment& last = *experiment.background[experiment.background.size() - 1];
        point.position = last.position;
        point.intensity.value = last.intensity.value;
    }
    editor_.apply_background_edit(experiment, edi::Edit::append(experiment.background, std::move(point)), true);
}

void BackgroundListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply_background_edit(experiment, edi::Edit::erase(experiment.background, static_cast<std::size_t>(row)), true);
}

BackgroundTermListModel::BackgroundTermListModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                                 ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"id", "order", "coef"}, parent), experiment_(experiment), editor_(editor), registry_(registry) {
    sync();
}

void BackgroundTermListModel::sync() {
    QList<Row> rows;
    for (const auto& term : experiment_.background_terms) {
        rows.append({term.get(), {QString::fromStdString(term->id.value()), term->order.get(), parameter_role(registry_, &term->coef)}});
    }
    setTableRows(rows);
}

bool BackgroundTermListModel::setId(int row, const QString& id) {
    auto* term = const_cast<edi::PolynomialTerm*>(static_cast<const edi::PolynomialTerm*>(keyAt(row)));
    return term != nullptr &&
           editor_.apply_background_edit(experiment_, edi::Edit::background_id(*term, id.toStdString()), true).isEmpty();
}

bool BackgroundTermListModel::setOrder(int row, int order) {
    auto* term = const_cast<edi::PolynomialTerm*>(static_cast<const edi::PolynomialTerm*>(keyAt(row)));
    edi::ExperimentBase& experiment = experiment_;
    return term != nullptr &&
           editor_.apply_background_edit(experiment, edi::Edit::background_term_order(experiment, *term, order), false)
               .isEmpty();
}

void BackgroundTermListModel::append() {
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply_background_edit(experiment, edi::Edit::append_background_term(experiment), true);
}

void BackgroundTermListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply_background_edit(experiment, edi::Edit::erase(experiment.background_terms, static_cast<std::size_t>(row)),
                                  true);
}

// ---- ExcludedRegionListModel --------------------------------------------------------------------

ExcludedRegionListModel::ExcludedRegionListModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                                 QObject* parent)
    : RowTableModel({"id", "start", "end"}, parent), experiment_(experiment), editor_(editor) {
    sync();
}

ReflectionListModel::ReflectionListModel(const edi::ExperimentBase& experiment, QObject* parent)
    : RowTableModel({"hkl", "dSpacing", "position", "fSquaredCalc"}, parent), experiment_(experiment) {
    sync();
}

void ReflectionListModel::sync() {
    QList<Row> rows;
    if (const auto& loop = experiment_.carried_reflections; loop.has_value()) {
        const auto column = [&loop](const char* name) {
            const auto found = std::find(loop->columns.begin(), loop->columns.end(), name);
            return found == loop->columns.end() ? -1 : static_cast<int>(found - loop->columns.begin());
        };
        const int h = column("index_h"), k = column("index_k"), l = column("index_l"), d = column("d_spacing"),
                  f2 = column("f_squared_calc");
        const int position = column("two_theta") >= 0 ? column("two_theta") : column("time_of_flight");
        for (std::size_t i = 0; i < loop->rows.size(); ++i) {
            const std::vector<std::string>& cells = loop->rows[i];
            const auto text = [&cells](int at) {
                return at >= 0 && at < static_cast<int>(cells.size()) ? QString::fromStdString(cells[at]) : QString();
            };
            const auto number = [&text](int at) {
                bool ok = false;
                const double value = text(at).toDouble(&ok);
                return ok ? value : qQNaN();
            };
            rows.append({reinterpret_cast<const void*>(i + 1),
                         {QStringList{text(h), text(k), text(l)}.join(QLatin1Char(' ')), number(d), number(position),
                          number(f2)}});
        }
    }
    setTableRows(rows);
}

namespace {
// The reflection table's columns, in the order the delegates read them.
const QStringList kSingleCrystalReflectionRoles{"h",        "k",        "l",          "dSpacing", "sinThetaOverLambda",
                                                "intensityMeas", "intensityMeasSu", "intensityCalc", "residual",
                                                "wavelength", "fitUse"};
}  // namespace

SingleCrystalReflectionModel::SingleCrystalReflectionModel(const edi::ExperimentBase& experiment,
                                                           const edi::Project& project, QObject* parent)
    : RowTableModel(kSingleCrystalReflectionRoles, parent),
      experiment_(experiment),
      project_(project) {
    sync();
}

void SingleCrystalReflectionModel::sortBy(const QString& role) {
    if (!kSingleCrystalReflectionRoles.contains(role)) {
        return;
    }
    sort_ascending_ = role == sort_role_ ? !sort_ascending_ : true;
    sort_role_ = role;
    emit sortChanged();
    publish();
}

void SingleCrystalReflectionModel::publish() {
    QList<Row> rows = file_rows_;
    const qsizetype column = kSingleCrystalReflectionRoles.indexOf(sort_role_);
    if (column >= 0) {
        const bool ascending = sort_ascending_;
        std::stable_sort(rows.begin(), rows.end(), [column, ascending](const Row& a, const Row& b) {
            const double x = a.values.at(column).toDouble();
            const double y = b.values.at(column).toDouble();
            if (std::isnan(x) || std::isnan(y)) {
                return !std::isnan(x) && std::isnan(y);
            }
            return ascending ? x < y : y < x;
        });
    }
    setTableRows(rows);
}

void SingleCrystalReflectionModel::sync() {
    frame_.reset();
    refresh();
}

void SingleCrystalReflectionModel::showFrame(std::shared_ptr<const std::vector<double>> calculated) {
    frame_ = std::move(calculated);
    refresh();
}

void SingleCrystalReflectionModel::refresh() {
    QList<Row> rows;
    QList<double> calculated;
    QList<double> measured;
    QList<double> su;
    QList<bool> used;
    // The fit's cutoff (`_refine_ls.threshold_sigma`): a reflection is fitted when F² > n su(F²), as crysta selects
    // them; every one without a cutoff.
    const std::optional<double> cutoff = project_.refine_ls_threshold_sigma;
    double low = qInf();
    double high = -qInf();
    bool shown = false;
    if (const auto& reflections = experiment_.reflections; reflections.has_value() && reflections->rectangular()) {
        // A fit's frame shows its own F²calc; the rest of the computed columns are the model's, as they were.
        const std::vector<double>& calc = frame_ ? *frame_ : reflections->intensity_calc.values();
        const bool current = calc.size() == reflections->size() && (frame_ || experiment_.computed_current());
        for (std::size_t i = 0; i < reflections->size(); ++i) {
            const double meas = reflections->intensity_meas[i];
            const double sigma = reflections->intensity_meas_su[i];
            const double value = current ? calc[i] : qQNaN();
            const double residual = current && sigma > 0.0 ? (meas - value) / sigma : qQNaN();
            const auto column = [current, i](const edi::ComputedColumn<double>& values) {
                return current && i < values.size() ? values[i] : qQNaN();
            };
            const bool fitted = !cutoff.has_value() || meas > *cutoff * sigma;
            used.append(fitted);
            rows.append({reinterpret_cast<const void*>(i + 1),
                         {reflections->index_h[i], reflections->index_k[i], reflections->index_l[i],
                          column(reflections->d_spacing), column(reflections->sin_theta_over_lambda), meas, sigma,
                          value, residual,
                          i < reflections->wavelength.size() ? reflections->wavelength[i] : qQNaN(),
                          fitted ? 1.0 : 0.0}});
            calculated.append(value);
            measured.append(meas);
            su.append(sigma);
            for (const double end : {meas - sigma, meas + sigma, value}) {
                if (std::isfinite(end)) {
                    low = std::min(low, end);
                    high = std::max(high, end);
                }
            }
        }
        shown = current;
    }
    file_rows_ = rows;
    publish();
    if (!(high > low)) {
        low = 0.0;
        high = 1.0;
    }
    // The F view, by the Xtal ADDREF convention (as cctbx's f_sq_as_f_xtal_3_7): F = √F² for F² > 0 and 0 otherwise,
    // so a weak or negative reflection stays on the chart, and σ(F) = σ(F²) / (F + √(F² + σ(F²))), which is
    // σ(F²) / 2F for a strong reflection and √σ(F²) at F = 0 rather than growing without bound.
    QList<double> calculated_f;
    QList<double> measured_f;
    QList<double> measured_f_su;
    double high_f = 0.0;
    for (qsizetype i = 0; i < measured.size(); ++i) {
        const double calc_f = std::isfinite(calculated[i]) ? std::sqrt(std::max(calculated[i], 0.0)) : qQNaN();
        const double meas_f = std::isfinite(measured[i]) ? std::sqrt(std::max(measured[i], 0.0)) : qQNaN();
        const double su_f = std::isfinite(meas_f) && su[i] > 0.0 ? su[i] / (meas_f + std::sqrt(meas_f * meas_f + su[i]))
                                                                 : qQNaN();
        calculated_f.append(calc_f);
        measured_f.append(meas_f);
        measured_f_su.append(su_f);
        for (const double end : {meas_f + su_f, calc_f}) {
            if (std::isfinite(end)) {
                high_f = std::max(high_f, end);
            }
        }
    }
    calculated_f_ = calculated_f;
    measured_f_ = measured_f;
    measured_f_su_ = measured_f_su;
    low_f_ = 0.0;
    high_f_ = high_f > 0.0 ? high_f * 1.05 : 1.0;
    const double pad = (high - low) * 0.05;
    calculated_ = calculated;
    measured_ = measured;
    measured_su_ = su;
    used_ = used;
    fit_cutoff_ = cutoff.value_or(qQNaN());
    low_ = std::min(0.0, low - pad);
    high_ = high + pad;
    calculated_shown_ = shown;
    wavelength_low_ = qQNaN();
    wavelength_high_ = qQNaN();
    if (const auto& reflections = experiment_.reflections; reflections.has_value()) {
        for (const double wavelength : reflections->wavelength.get()) {
            if (std::isfinite(wavelength)) {
                wavelength_low_ = std::isnan(wavelength_low_) ? wavelength : std::min(wavelength_low_, wavelength);
                wavelength_high_ = std::isnan(wavelength_high_) ? wavelength : std::max(wavelength_high_, wavelength);
            }
        }
    }
    emit pointsChanged();
}

QString SingleCrystalReflectionModel::hoverText(int row, bool squared) const {
    const auto& reflections = experiment_.reflections;
    if (!reflections.has_value() || !reflections->rectangular() || row < 0 ||
        static_cast<std::size_t>(row) >= reflections->size()) {
        return {};
    }
    const auto at = static_cast<qsizetype>(row);
    const double meas = squared ? measured_.value(at, qQNaN()) : measured_f_.value(at, qQNaN());
    const double su = squared ? measured_su_.value(at, qQNaN()) : measured_f_su_.value(at, qQNaN());
    const double calc = squared ? calculated_.value(at, qQNaN()) : calculated_f_.value(at, qQNaN());
    const QString quantity = squared ? QStringLiteral("F²") : QStringLiteral("F");
    QStringList lines{QStringLiteral("%1 %2 %3")
                          .arg(reflections->index_h[at])
                          .arg(reflections->index_k[at])
                          .arg(reflections->index_l[at])};
    // The measured value and its su as the tables write them; the calculated value to the same last digit.
    int decimals = 6;
    if (std::isfinite(meas) && std::isfinite(su) && su > 0.0) {
        const edi::SuText text = edi::su_text(meas, su, project_.su_rule);
        const auto dot = text.value.find('.');
        decimals = dot == std::string::npos ? 0 : static_cast<int>(text.value.size() - dot - 1);
        lines.append(QStringLiteral("%1 meas: %2 ± %3")
                         .arg(quantity, QString::fromStdString(text.value), QString::fromStdString(text.su)));
    } else if (std::isfinite(meas)) {
        lines.append(QStringLiteral("%1 meas: %2").arg(quantity, QString::number(meas, 'f', decimals)));
    }
    if (std::isfinite(calc)) {
        lines.append(QStringLiteral("%1 calc: %2").arg(quantity, QString::number(calc, 'f', decimals)));
    }
    if (at < used_.size() && !used_.at(at)) {
        lines.append(QStringLiteral("left out of the fit: F² ≤ %1 s.u.").arg(fit_cutoff_));
    }
    return lines.join(QStringLiteral("<br>"));
}

void ExcludedRegionListModel::sync() {
    QList<Row> rows;
    for (const auto& region : experiment_.excluded_regions) {
        rows.append({region.get(), {QString::fromStdString(region->id.value()), region->first.get(), region->second.get()}});
    }
    setTableRows(rows);
}

bool ExcludedRegionListModel::setId(int row, const QString& id) {
    auto* region = const_cast<edi::ExcludedRegion*>(static_cast<const edi::ExcludedRegion*>(keyAt(row)));
    return region != nullptr && editor_.apply(edi::Edit::excluded_region_id(*region, id.toStdString()), true).isEmpty();
}

bool ExcludedRegionListModel::setStart(int row, double start) {
    edi::ExperimentBase& experiment = experiment_;
    return row >= 0 && row < count() &&
           editor_.apply(edi::Edit::excluded_region_bound(experiment, static_cast<std::size_t>(row), false, start), false).isEmpty();
}

bool ExcludedRegionListModel::setEnd(int row, double end) {
    edi::ExperimentBase& experiment = experiment_;
    return row >= 0 && row < count() &&
           editor_.apply(edi::Edit::excluded_region_bound(experiment, static_cast<std::size_t>(row), true, end), false).isEmpty();
}

void ExcludedRegionListModel::append() {
    edi::ExperimentBase& experiment = experiment_;
    const double at = experiment.excluded_regions.empty() ? 0.0 : experiment.excluded_regions.back()->second.get();
    editor_.apply(edi::Edit::append_excluded_region(experiment, at, at), false);
}

void ExcludedRegionListModel::remove(int row) {
    edi::ExperimentBase& experiment = experiment_;
    if (row >= 0 && row < count()) {
        editor_.apply(edi::Edit::erase_excluded_region(experiment, static_cast<std::size_t>(row)), false);
    }
}

// ---- PrefOrientListModel ------------------------------------------------------------------------

// ---- LinkedStructureListModel --------------------------------------------------------------------

namespace {

// A weight fraction for its read-only cell: `value` and `uncertainty` (0 without one), written by the app's
// number rule in QML, or an empty map when there is none or the model cannot be calculated mid-edit.
QVariantMap weight_fraction_cell(const edi::LinkedStructure& link) {
    std::optional<edi::WeightFraction> fraction;
    try {
        fraction = edi::weight_fraction(link);
    } catch (const std::exception&) {
        return {};
    }
    if (!fraction) {
        return {};
    }
    return {{QStringLiteral("value"), fraction->value},
            {QStringLiteral("uncertainty"), fraction->uncertainty.value_or(0.0)}};
}

}  // namespace

LinkedStructureListModel::LinkedStructureListModel(edi::Project& project, edi::ExperimentBase& experiment,
                                                   ProjectEditor& editor, ParameterRegistry& registry,
                                                   QObject* parent)
    : RowTableModel({"structureId", "scale", "enabled", "colorIndex", "weightFraction"}, parent),
      project_(project),
      experiment_(experiment),
      editor_(editor),
      registry_(registry) {
    sync();
}

void LinkedStructureListModel::sync() {
    QStringList names;
    for (const auto& structure : project_.structures) {
        names.append(QString::fromStdString(edi::datablock_key(structure->name, "structure")));
    }
    if (names != structure_names_) {
        structure_names_ = names;
        emit structureNamesChanged();
    }
    // A single enabled structure's fraction is exactly 1, as the saved file writes it; it is shown without asking the
    // engine, which would convert the whole project for a known answer.
    const auto enabled_links = std::count_if(experiment_.linked_structures.begin(), experiment_.linked_structures.end(),
                                             [](const auto& link) { return link->enabled.get(); });
    const auto fraction = [enabled_links](const edi::LinkedStructure& link) {
        if (enabled_links > 1) {
            return weight_fraction_cell(link);
        }
        if (link.enabled.get()) {
            return QVariantMap{{QStringLiteral("value"), 1.0}, {QStringLiteral("uncertainty"), 0.0}};
        }
        return QVariantMap();
    };
    QList<Row> rows;
    for (const auto& link : experiment_.linked_structures) {
        const QString id = QString::fromStdString(link->structure_id.value());
        rows.append({link.get(),
                     {id, parameter_role(registry_, &link->scale), link->enabled.get(),
                      static_cast<int>(names.indexOf(id)),
                      fraction(*link)}});
    }
    setTableRows(rows);
    const auto linked = [this](const QString& name) {
        return std::any_of(experiment_.linked_structures.begin(), experiment_.linked_structures.end(),
                           [&](const auto& link) { return QString::fromStdString(link->structure_id.value()) == name; });
    };
    const bool can_append = std::any_of(names.begin(), names.end(), [&](const QString& name) { return !linked(name); });
    if (can_append != can_append_) {
        can_append_ = can_append;
        emit canAppendChanged();
    }
    const bool can_remove = experiment_.linked_structures.size() > 1;
    if (can_remove != can_remove_) {
        can_remove_ = can_remove;
        emit canRemoveChanged();
    }
}

bool LinkedStructureListModel::setStructureId(int row, const QString& id) {
    auto* link = const_cast<edi::LinkedStructure*>(static_cast<const edi::LinkedStructure*>(keyAt(row)));
    return link != nullptr &&
           editor_.apply(edi::Edit::link_structure(*link, id.toStdString()), true).isEmpty();
}

bool LinkedStructureListModel::setEnabled(int row, bool enabled) {
    auto* link = const_cast<edi::LinkedStructure*>(static_cast<const edi::LinkedStructure*>(keyAt(row)));
    return link != nullptr && editor_.apply(edi::Edit::assign(link->enabled, enabled), true).isEmpty();
}

void LinkedStructureListModel::append() {
    if (!canAppend()) {
        return;
    }
    // The first structure the experiment does not link yet, at scale 1.
    for (const QString& name : structure_names_) {
        const bool linked = std::any_of(
            experiment_.linked_structures.begin(), experiment_.linked_structures.end(),
            [&](const auto& link) { return QString::fromStdString(link->structure_id.value()) == name; });
        if (!linked) {
            edi::LinkedStructure link;
            link.structure_id = name.toStdString();
            editor_.apply(edi::Edit::append(experiment_.linked_structures, std::move(link)), true);
            return;
        }
    }
}

void LinkedStructureListModel::remove(int row) {
    if (!canRemove() || keyAt(row) == nullptr) {
        return;
    }
    editor_.apply(edi::Edit::erase(experiment_.linked_structures, static_cast<std::size_t>(row)), true);
}

// ---- PrefOrientListModel -------------------------------------------------------------------------

PrefOrientListModel::PrefOrientListModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                         ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"structureId", "indexH", "indexK", "indexL", "marchR", "marchRandomFract"}, parent),
      experiment_(experiment),
      editor_(editor),
      registry_(registry) {
    sync();
}

void PrefOrientListModel::sync() {
    QList<Row> rows;
    for (const auto& row : experiment_.preferred_orientation) {
        rows.append({row.get(),
                     {QString::fromStdString(row->structure_id), row->index_h.get(), row->index_k.get(),
                      row->index_l.get(),
                      parameter_role(registry_, &row->march_r), parameter_role(registry_, &row->march_random_fract)}});
    }
    setTableRows(rows);
    // A row can be added while a linked structure has none.
    const bool can_append = std::any_of(
        experiment_.linked_structures.begin(), experiment_.linked_structures.end(), [this](const auto& link) {
            return std::none_of(experiment_.preferred_orientation.begin(), experiment_.preferred_orientation.end(),
                                [&](const auto& row) { return row->structure_id.value() == link->structure_id.value(); });
        });
    if (can_append != can_append_) {
        can_append_ = can_append;
        emit canAppendChanged();
    }
}

bool PrefOrientListModel::setStructureId(int row, const QString& id) {
    auto* texture = const_cast<edi::PrefOrient*>(static_cast<const edi::PrefOrient*>(keyAt(row)));
    return texture != nullptr &&
           editor_.apply(edi::Edit::texture_structure(*texture, id.toStdString()), false).isEmpty();
}

bool PrefOrientListModel::setIndex(int row, const QString& axis, int value) {
    auto* texture = const_cast<edi::PrefOrient*>(static_cast<const edi::PrefOrient*>(keyAt(row)));
    edi::detail::Written<int> edi::PrefOrient::*component =
        axis == QLatin1String("h")   ? &edi::PrefOrient::index_h
        : axis == QLatin1String("k") ? &edi::PrefOrient::index_k
        : axis == QLatin1String("l") ? &edi::PrefOrient::index_l
                                     : nullptr;
    return texture != nullptr && component != nullptr &&
           editor_.apply(edi::Edit::texture_axis_component(*texture, component, value), false).isEmpty();
}

void PrefOrientListModel::append() {
    if (!canAppend()) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    // The first linked structure without a row.
    for (const auto& link : experiment.linked_structures) {
        const bool textured =
            std::any_of(experiment.preferred_orientation.begin(), experiment.preferred_orientation.end(),
                        [&](const auto& row) { return row->structure_id.value() == link->structure_id.value(); });
        if (!textured) {
            edi::PrefOrient row;
            row.structure_id = link->structure_id.value();
            editor_.apply(edi::Edit::append(experiment.preferred_orientation, std::move(row)), true);
            return;
        }
    }
}

void PrefOrientListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply(edi::Edit::erase(experiment.preferred_orientation, static_cast<std::size_t>(row)), true);
}

// ---- ScatteringSourceViewModel ------------------------------------------------------------------

namespace {

edi::ScatteringSourceItem item_named(const QString& name) {
    for (const edi::ScatteringSourceItem item :
         {edi::ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH, edi::ScatteringSourceItem::XRAY_FORM_FACTOR,
          edi::ScatteringSourceItem::XRAY_DISPERSION}) {
        if (QString::fromStdString(edi::scattering_source_tag(item)).endsWith(QLatin1Char('.') + name)) {
            return item;
        }
    }
    return edi::ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH;
}

QString item_name(edi::ScatteringSourceItem item) {
    const QString tag = QString::fromStdString(edi::scattering_source_tag(item));
    return tag.mid(tag.indexOf(QLatin1Char('.')) + 1);
}

}  // namespace

ScatteringSourceViewModel::ScatteringSourceViewModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                                     QObject* parent)
    : RowTableModel({"name", "token", "effectiveToken", "isDeclared", "options"}, parent),
      experiment_(experiment),
      editor_(editor) {
    sync();
}

void ScatteringSourceViewModel::sync() {
    QList<Row> rows;
    for (const edi::ScatteringSourceItem item :
         edi::scattering_source_items(experiment_.experiment_type.effective_radiation_probe())) {
        const QString name = item_name(item);
        OptionListModel*& options = options_[name];
        if (options == nullptr) {
            options = new OptionListModel(this);
        }
        options->setOptions(edi::supported_scattering_sources(item));
        const QString token = QString::fromStdString(edi::scattering_source_value(experiment_, item));
        const QString effective = token.isEmpty() ? options->tokenAt(0) : token;
        rows.append({options, {name, token, effective, !token.isEmpty(), QVariant::fromValue<QObject*>(options)}});
    }
    setTableRows(rows);
}

bool ScatteringSourceViewModel::select(const QString& name, const QString& token) {
    edi::ExperimentBase& experiment = experiment_;
    const edi::ScatteringSourceItem item = item_named(name);
    return editor_.apply(edi::Edit::scattering_source(experiment, item, token.toStdString()), false).isEmpty();
}

OptionListModel* ScatteringSourceViewModel::optionsFor(const QString& name) const { return options_.value(name); }

}  // namespace edi_app
