// SPDX-License-Identifier: BSD-3-Clause
#include "experiment_models.hpp"

#include <QtNumeric>
#include <algorithm>

#include "edi/edits.hpp"
#include "edi/selectors.hpp"
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

// ---- BackgroundListModel ------------------------------------------------------------------------

BackgroundListModel::BackgroundListModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                         ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"position", "intensity"}, parent), experiment_(experiment), editor_(editor), registry_(registry) {
    sync();
}

void BackgroundListModel::sync() {
    QList<Row> rows;
    for (const auto& point : experiment_.background) {
        rows.append({point.get(), {point->position.get(), parameter_role(registry_, &point->intensity)}});
    }
    setTableRows(rows);
}

bool BackgroundListModel::setPosition(int row, double position) {
    auto* point = const_cast<edi::LineSegment*>(static_cast<const edi::LineSegment*>(keyAt(row)));
    return point != nullptr && editor_.apply(edi::Edit::background_position(*point, position), false).isEmpty();
}

void BackgroundListModel::append() {
    edi::ExperimentBase& experiment = experiment_;
    edi::LineSegment point;
    if (experiment.background.size() > 0) {
        const edi::LineSegment& last = *experiment.background[experiment.background.size() - 1];
        point.position = last.position;
        point.intensity.value = last.intensity.value;
    }
    editor_.apply(edi::Edit::append(experiment.background, std::move(point)), true);
}

void BackgroundListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    editor_.apply(edi::Edit::erase(experiment.background, static_cast<std::size_t>(row)), true);
}

// ---- ExcludedRegionListModel --------------------------------------------------------------------

ExcludedRegionListModel::ExcludedRegionListModel(edi::ExperimentBase& experiment, ProjectEditor& editor,
                                                 QObject* parent)
    : RowTableModel({"start", "end"}, parent), experiment_(experiment), editor_(editor) {
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
    // A region is a value pair in a vector, so its row key is its index (a row's identity is its place).
    QList<Row> rows;
    for (std::size_t i = 0; i < experiment_.excluded_regions.size(); ++i) {
        const auto& [start, end] = experiment_.excluded_regions[i];
        rows.append({reinterpret_cast<const void*>(i + 1), {start, end}});
    }
    setTableRows(rows);
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
    const double at = experiment.excluded_regions.empty() ? 0.0 : experiment.excluded_regions.back().second;
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

LinkedStructureListModel::LinkedStructureListModel(edi::Project& project, edi::ExperimentBase& experiment,
                                                   ProjectEditor& editor, ParameterRegistry& registry,
                                                   QObject* parent)
    : RowTableModel({"structureId", "scale", "enabled", "colorIndex"}, parent),
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
    QList<Row> rows;
    for (const auto& link : experiment_.linked_structures) {
        const QString id = QString::fromStdString(link->structure_id.value());
        rows.append({link.get(),
                     {id, parameter_role(registry_, &link->scale), link->enabled.get(),
                      static_cast<int>(names.indexOf(id))}});
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
