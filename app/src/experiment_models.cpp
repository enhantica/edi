// SPDX-License-Identifier: BSD-3-Clause
#include "experiment_models.hpp"

#include <QVariantMap>
#include <QtNumeric>
#include <algorithm>
#include <exception>
#include <optional>

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
    : RowTableModel({"order", "coef"}, parent), experiment_(experiment), editor_(editor), registry_(registry) {
    sync();
}

void BackgroundTermListModel::sync() {
    QList<Row> rows;
    for (const auto& term : experiment_.background_terms) {
        rows.append({term.get(), {term->order.get(), parameter_role(registry_, &term->coef)}});
    }
    setTableRows(rows);
}

bool BackgroundTermListModel::setOrder(int row, int order) {
    auto* term = const_cast<edi::PolynomialTerm*>(static_cast<const edi::PolynomialTerm*>(keyAt(row)));
    edi::ExperimentBase& experiment = experiment_;
    return term != nullptr && editor_.apply(edi::Edit::background_term_order(experiment, *term, order), false).isEmpty();
}

void BackgroundTermListModel::append() {
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply(edi::Edit::append_background_term(experiment), true);
}

void BackgroundTermListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply(edi::Edit::erase(experiment.background_terms, static_cast<std::size_t>(row)), true);
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
    // A single structure's fraction is always 1 and says nothing: its cell stays empty, as the saved file writes
    // the column only when two or more structures take part.
    const auto enabled_links = std::count_if(experiment_.linked_structures.begin(), experiment_.linked_structures.end(),
                                             [](const auto& link) { return link->enabled.get(); });
    QList<Row> rows;
    for (const auto& link : experiment_.linked_structures) {
        const QString id = QString::fromStdString(link->structure_id.value());
        rows.append({link.get(),
                     {id, parameter_role(registry_, &link->scale), link->enabled.get(),
                      static_cast<int>(names.indexOf(id)),
                      enabled_links > 1 ? weight_fraction_cell(*link) : QVariantMap()}});
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
