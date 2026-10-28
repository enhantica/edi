// SPDX-License-Identifier: BSD-3-Clause
#include "experiment_models.hpp"
#include <string_view>

#include <cmath>

#include <QVariantMap>
#include <QtNumeric>
#include <algorithm>
#include <exception>
#include <optional>

#include "edi/display.hpp"
#include "edi/edits.hpp"
#include "edi/selectors.hpp"
#include "parameter_item.hpp"
#include "parameter_registry.hpp"
#include "project_editor.hpp"
#include "background_input.hpp"
#include <QPointer>

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
                      spec != nullptr ? QString::fromStdString(edi::label(edi::uid_of(*spec))) : QString::fromStdString(field.name),
                      item != nullptr ? item->shortName() : QString::fromStdString(field.name),
                      spec != nullptr ? QString::fromStdString(edi::units_label(edi::uid_of(*spec))) : QString(), field.used_by_profile}});
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
    if (!point) return false;
    try { return editor_.rename_background_point(experiment_, *point, id.toStdString()).isEmpty(); }
    catch (...) { return false; }
}
bool BackgroundListModel::setPosition(int row, double position) {
    auto* point = const_cast<edi::LineSegment*>(static_cast<const edi::LineSegment*>(keyAt(row)));
    if (!point) return false;
    edi::BackgroundPointInput input;
    input.action = edi::BackgroundPointInput::Action::Update; input.id = point->id.value();
    input.position = position; input.intensity = point->intensity.value.get(); input.free = point->intensity.free.get();
    return applyDefined(input).value("applied").toBool();
}
void BackgroundListModel::append() {
    const QPointer<BackgroundListModel> self(this);
    try { (void)applyDefined(background_append_input(experiment_)); }
    catch (...) {
        if (!self) return;
        const QString message = tr("A background point could not be appended");
        if (operation_error_ != message) { operation_error_ = message; emit operationErrorChanged(); }
    }
}
QVariantMap BackgroundListModel::changeDefined(const QString& operation, const QString& id, double position, double intensity, bool free) {
    std::optional<edi::BackgroundPointInput> input;
    try { input = background_input(operation, id, position, intensity, free, false); }
    catch (...) { return {{"applied", false}, {"published", false}, {"message", tr("The background input is invalid or exceeds its admitted capacity")}}; }
    return applyDefined(*input);
}
QVariantMap BackgroundListModel::applyDefined(const edi::BackgroundPointInput& input) {
    const QPointer<BackgroundListModel> self(this);
    ProjectEditor::BackgroundOutcome result;
    try { result = editor_.edit_background_point(experiment_, input); }
    catch (...) { result.message = tr("The background input is invalid or exceeds its admitted capacity"); }
    const QVariantMap outcome{{"applied", result.applied}, {"published", result.published}, {"message", result.message}};
    if (self && operation_error_ != result.message) { operation_error_ = result.message; emit operationErrorChanged(); }
    return outcome;
}
void BackgroundListModel::remove(int row) {
    auto* point = static_cast<const edi::LineSegment*>(keyAt(row));
    if (!point) return;
    edi::BackgroundPointInput input;
    input.action = edi::BackgroundPointInput::Action::Remove; input.id = point->id.value();
    (void)applyDefined(input);
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

// Equal for a change signal: NaN equals NaN, so a value still not calculated is no change.
bool same(double a, double b) { return a == b || (std::isnan(a) && std::isnan(b)); }
bool same(const QList<double>& a, const QList<double>& b) {
    return a.size() == b.size() && std::equal(a.begin(), a.end(), b.begin(), [](double x, double y) { return same(x, y); });
}
template <typename T>
bool same(const T& a, const T& b) {
    return a == b;
}

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
    const bool ascending = role == sort_role_ ? !sort_ascending_ : true;
    if (ascending != sort_ascending_) {
        sort_ascending_ = ascending;
        emit sortAscendingChanged();
    }
    if (role != sort_role_) {
        sort_role_ = role;
        emit sortRoleChanged();
    }
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

QVariant SingleCrystalReflectionModel::fileValue(qsizetype row, const QString& role) const {
    const auto column=kSingleCrystalReflectionRoles.indexOf(role);
    if(row<0 || row>=file_rows_.size() || column<0 || column>=file_rows_.at(row).values.size())return {};
    return file_rows_.at(row).values.at(column);
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
    double wavelength_low = qQNaN();
    double wavelength_high = qQNaN();
    if (const auto& reflections = experiment_.reflections; reflections.has_value()) {
        for (const double wavelength : reflections->wavelength.get()) {
            if (std::isfinite(wavelength)) {
                wavelength_low = std::isnan(wavelength_low) ? wavelength : std::min(wavelength_low, wavelength);
                wavelength_high = std::isnan(wavelength_high) ? wavelength : std::max(wavelength_high, wavelength);
            }
        }
    }
    // Each property notifies only when it changed, NaN equal to NaN; the chart then redraws once.
    const double pad = (high - low) * 0.05;
    bool changed = false;
    const auto update = [this, &changed](auto& member, const auto& value, void (SingleCrystalReflectionModel::*signal)()) {
        if (!same(member, value)) {
            member = value;
            changed = true;
            emit(this->*signal)();
        }
    };
    update(calculated_f_, calculated_f, &SingleCrystalReflectionModel::calculatedFChanged);
    update(measured_f_, measured_f, &SingleCrystalReflectionModel::measuredFChanged);
    update(measured_f_su_, measured_f_su, &SingleCrystalReflectionModel::measuredFSuChanged);
    update(low_f_, 0.0, &SingleCrystalReflectionModel::lowFChanged);
    update(high_f_, high_f > 0.0 ? high_f * 1.05 : 1.0, &SingleCrystalReflectionModel::highFChanged);
    update(calculated_, calculated, &SingleCrystalReflectionModel::calculatedChanged);
    update(measured_, measured, &SingleCrystalReflectionModel::measuredChanged);
    update(measured_su_, su, &SingleCrystalReflectionModel::measuredSuChanged);
    update(used_, used, &SingleCrystalReflectionModel::usedChanged);
    update(fit_cutoff_, cutoff.value_or(qQNaN()), &SingleCrystalReflectionModel::fitCutoffChanged);
    update(low_, std::min(0.0, low - pad), &SingleCrystalReflectionModel::lowChanged);
    update(high_, high + pad, &SingleCrystalReflectionModel::highChanged);
    update(calculated_shown_, shown, &SingleCrystalReflectionModel::calculatedShownChanged);
    update(wavelength_low_, wavelength_low, &SingleCrystalReflectionModel::wavelengthLowChanged);
    update(wavelength_high_, wavelength_high, &SingleCrystalReflectionModel::wavelengthHighChanged);
    if (changed) {
        emit pointsChanged();
    }
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
    QStringList lines;
    for (const std::string& line : edi::reflection_hover_lines(reflections->index_h[at], reflections->index_k[at],
                                                               reflections->index_l[at], meas, su, calc, squared,
                                                               project_.su_rule)) {
        lines.append(QString::fromStdString(line));
    }
    if (at < used_.size() && !used_.at(at)) {
        lines.append(QStringLiteral("left out of the fit: F² at most %1 s.u.")
                         .arg(QString::fromStdString(edi::display_text("refine_ls.threshold_sigma", fit_cutoff_))));
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
    if(row<0 || row>=count())return false;
    return editor_.apply_creation_control(edi::Edit::excluded_region_bound(experiment, static_cast<std::size_t>(row), false, start), false,
               {ProjectEditor::CreationAction::Kind::ExclusionStart, keyAt(row), {}, {}, start}).isEmpty();
}

bool ExcludedRegionListModel::setEnd(int row, double end) {
    edi::ExperimentBase& experiment = experiment_;
    if(row<0 || row>=count())return false;
    return editor_.apply_creation_control(edi::Edit::excluded_region_bound(experiment, static_cast<std::size_t>(row), true, end), false,
               {ProjectEditor::CreationAction::Kind::ExclusionEnd, keyAt(row), {}, {}, end}).isEmpty();
}

void ExcludedRegionListModel::append() {
    edi::ExperimentBase& experiment = experiment_;
    const double at = experiment.excluded_regions.empty() ? 0.0 : experiment.excluded_regions.back()->second.get();
    editor_.apply_creation_control(edi::Edit::append_excluded_region(experiment, at, at), false,
        {ProjectEditor::CreationAction::Kind::ExclusionAppend, &experiment});
}

void ExcludedRegionListModel::remove(int row) {
    edi::ExperimentBase& experiment = experiment_;
    if (row >= 0 && row < count()) {
        editor_.apply_creation_control(edi::Edit::erase_excluded_region(experiment, static_cast<std::size_t>(row)), false,
            {ProjectEditor::CreationAction::Kind::ExclusionRemove,keyAt(row)});
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
    const auto key=keyAt(row);
    for(const auto& held:experiment_.linked_structures)if(held.get()==key) {
        if(!held->enabled.get())return false;
        return editor_.apply_creation_control(edi::Edit::link_structure(*held,id.toStdString()),true,
            {ProjectEditor::CreationAction::Kind::PhaseRetarget,held.get(),{},id}).isEmpty();
    }
    return false;
}

bool LinkedStructureListModel::setEnabled(int row, bool enabled) {
    const auto key=keyAt(row);
    for(const auto& held:experiment_.linked_structures)if(held.get()==key)
        return editor_.apply_creation_control(edi::Edit::assign(held->enabled,enabled),true,
            {ProjectEditor::CreationAction::Kind::PhaseEnabled,held.get(),{},{},double(enabled)}).isEmpty();
    return false;
}

void LinkedStructureListModel::append() {
    // The first CURRENT project structure not linked yet, at the original defaults.
    // Cached Qt offers/counts are presentation, never live membership authority.
    for(const auto& structure:project_.structures) {
        const auto& raw=structure->name.value();
        const std::string_view name=raw.empty()?std::string_view("structure"):std::string_view(raw);
        const bool linked=std::any_of(experiment_.linked_structures.begin(),experiment_.linked_structures.end(),
            [&](const auto& link){return (link->structure_id.value().empty()?std::string_view("structure"):std::string_view(link->structure_id.value()))==name;});
        if(!linked) {
            edi::LinkedStructure link;link.structure_id=std::string(name);
            editor_.apply_creation_control(edi::Edit::append(experiment_.linked_structures,std::move(link)),true,
                {ProjectEditor::CreationAction::Kind::PhaseAppend,&experiment_,{},QString::fromUtf8(name.data(),static_cast<qsizetype>(name.size()))});
            return;
        }
    }
}

void LinkedStructureListModel::remove(int row) {
    const auto key=keyAt(row);
    if(experiment_.linked_structures.size()<=1)return;
    for(std::size_t i=0;i<experiment_.linked_structures.size();++i)if(experiment_.linked_structures[i].get()==key) {
        editor_.apply_creation_control(edi::Edit::erase(experiment_.linked_structures,i),true,
            {ProjectEditor::CreationAction::Kind::PhaseRemove,key});
        return;
    }
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
        options->setItemOptions("scattering_source." + name.toStdString(), edi::supported_scattering_sources(item));
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
