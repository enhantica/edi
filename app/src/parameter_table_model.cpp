// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_table_model.hpp"

#include <algorithm>

#include "category_list_model.hpp"
#include "parameter_item.hpp"
#include "parameter_registry.hpp"

namespace edi_app {

namespace {
const QStringList kRoles{"parameter", "path",  "blockKind", "blockName", "category", "rowLabel", "name",
                         "displayName", "value", "uncertainty", "hasUncertainty", "free", "minimum",
                         "maximum", "units", "refinable"};
// One predicate serves menu counts and filtering, so parent groups include all their children.
bool matches_group(const QString& group, const QString& kind, const QString& category, const QString& name) {
    if (group.isEmpty()) return true;
    if (group == QLatin1String("@structure")) return kind == QLatin1String("structure");
    if (group == QLatin1String("@experiment")) return kind == QLatin1String("experiment");
    if (group == QLatin1String("@atoms")) return category == QLatin1String("atom_site") || category == QLatin1String("atom_site_aniso");
    if (group == QLatin1String("@coordinates")) return category == QLatin1String("atom_site") && name.startsWith(QLatin1String("fract_"));
    if (group == QLatin1String("@occupancies")) return category == QLatin1String("atom_site") && name == QLatin1String("occupancy");
    if (group == QLatin1String("@displacement")) return category == QLatin1String("atom_site_aniso") || (category == QLatin1String("atom_site") && name.startsWith(QLatin1String("adp_")));
    if (group == QLatin1String("@peakBroadening")) return category == QLatin1String("peak") && name.startsWith(QLatin1String("broad_"));
    if (group == QLatin1String("@peakMixing")) return category == QLatin1String("peak") && name.startsWith(QLatin1String("mixing_"));
    if (group == QLatin1String("@peakAsymmetry")) return category == QLatin1String("peak") &&
        (name.startsWith(QLatin1String("asym_")) || name.startsWith(QLatin1String("rise_alpha_")) || name.startsWith(QLatin1String("decay_beta_")));
    return category == group;
}
}  // namespace

ParameterTableModel::ParameterTableModel(ParameterRegistry& registry, QObject* parent)
    : RowTableModel(kRoles, parent), registry_(registry) {
    sync();
}

void ParameterTableModel::setExperimentScope(const QString& experiment) {
    experiment_scope_ = experiment;
}

void ParameterTableModel::sync() {
    QList<Row> rows;
    int free_count = 0;
    for (ParameterItem* item : registry_.items()) {
        if (!item->isRefinable() || !item->isFittable()) {
            continue;  // symmetry fixes or ties it, or a fixed setting: shown on its page, never fitted
        }
        if (!experiment_scope_.isEmpty() && item->blockKind() == QLatin1String("experiment") &&
            item->blockName() != experiment_scope_) {
            continue;  // a scan mode fits one experiment at a time: another experiment's parameter
        }
        free_count += item->isFree() ? 1 : 0;
        rows.append({item,
                     {QVariant::fromValue<QObject*>(item), item->path(), item->blockKind(), item->blockName(),
                      item->category(), item->rowLabel(), item->name(), item->displayName(), item->value(),
                      item->uncertainty(), item->hasUncertainty(), item->isFree(), item->minimum(), item->maximum(),
                      item->displayUnits(), item->isRefinable()}});
    }
    setTableRows(rows);
    const int fixed_count = count() - free_count;
    if (free_count != free_count_) {
        free_count_ = free_count;
        emit freeCountChanged();
    }
    if (fixed_count != fixed_count_) {
        fixed_count_ = fixed_count;
        emit fixedCountChanged();
    }
}

int ParameterTableModel::numberOf(const QString& path) const {
    for (int row = 0; row < count(); ++row) {
        if (text(row, QStringLiteral("path")) == path) {
            return row + 1;
        }
    }
    return 0;
}

bool ParameterTableModel::setRole(int row, const QString& role, const QVariant& value) {
    auto* item = const_cast<ParameterItem*>(static_cast<const ParameterItem*>(keyAt(row)));
    if (item == nullptr) {
        return false;
    }
    if (role == QLatin1String("value")) {
        item->setValue(value.toDouble());
    } else if (role == QLatin1String("free")) {
        item->setFree(value.toBool());
    } else {
        return false;
    }
    return item->lastError().isEmpty();
}

ParameterFilterModel::ParameterFilterModel(QObject* parent) : QSortFilterProxyModel(parent) {}

void ParameterFilterModel::setSourceModel(QAbstractItemModel* source) {
    for (const auto& connection : source_connections_) {
        disconnect(connection);
    }
    source_connections_.clear();
    QSortFilterProxyModel::setSourceModel(source);
    if (source != nullptr) {
        source_connections_.append(connect(source, &QAbstractItemModel::modelReset, this, &ParameterFilterModel::refresh));
        source_connections_.append(connect(source, &QAbstractItemModel::rowsInserted, this, &ParameterFilterModel::refresh));
        source_connections_.append(connect(source, &QAbstractItemModel::rowsRemoved, this, &ParameterFilterModel::refresh));
        source_connections_.append(connect(source, &QAbstractItemModel::dataChanged, this, &ParameterFilterModel::refresh));
    }
    refresh();
}

namespace {

// A datablock entry's key: its kind and name.
QString datablock_key(const QString& kind, const QString& name) { return kind + QLatin1Char(':') + name; }

bool matches_datablock(const QString& key, const QString& kind, const QString& name) {
    return key.isEmpty() || key == datablock_key(kind, name);
}

}  // namespace

void ParameterFilterModel::refresh() {
    struct Row { QString kind, block, category, name; bool free = false; };
    QList<Row> rows;
    if (sourceModel() != nullptr) {
        const auto roles = sourceModel()->roleNames();
        const auto value = [&](int row, const char* role) {
            return sourceModel()->data(sourceModel()->index(row, 0), roles.key(role));
        };
        for (int row = 0; row < sourceModel()->rowCount(); ++row) {
            rows.append({value(row, "blockKind").toString(), value(row, "blockName").toString(),
                         value(row, "category").toString(), value(row, "name").toString(), value(row, "free").toBool()});
        }
    }

    // The datablocks: all, then every structure, then every experiment, in page order.
    QStringList datablocks;
    QList<CategoryGroup> datablock_groups;
    datablocks.append(QString());
    datablock_groups.append(CategoryGroup{{}, tr("All datablocks (%1)").arg(rows.size()), {}, false, static_cast<int>(rows.size()), {}, {}});
    for (const QString& kind : {QStringLiteral("structure"), QStringLiteral("experiment")}) {
        for (const Row& row : rows) {
            const QString key = datablock_key(kind, row.block);
            if (row.kind != kind || datablocks.contains(key)) continue;
            const auto count = std::count_if(rows.begin(), rows.end(), [&](const Row& other) {
                return other.kind == kind && other.block == row.block;
            });
            datablocks.append(key);
            datablock_groups.append(CategoryGroup{key, QStringLiteral("%1 (%2)").arg(row.block).arg(count),
                                                  kind == QLatin1String("structure") ? QStringLiteral("layer-group")
                                                                                     : QStringLiteral("microscope"),
                                                  false, static_cast<int>(count), kind, row.block});
        }
    }
    if (!datablocks.contains(datablock_filter_)) {
        beginFilterChange();
        datablock_filter_.clear();
        endFilterChange(Direction::Rows);
        emit datablockFilterChanged();
    }
    QList<Row> scoped;
    for (const Row& row : rows) {
        if (matches_datablock(datablock_filter_, row.kind, row.block)) scoped.append(row);
    }

    // The categories of the selected datablocks.
    QStringList categories;
    QList<CategoryGroup> groups;
    const auto countGroup = [&](const QString& key) {
        int count = 0;
        for (const Row& row : scoped) {
            count += matches_group(key, row.kind, row.category, row.name) ? 1 : 0;
        }
        return count;
    };
    const auto add = [&](const QString& key, const QString& title, const QString& icon, bool datablock = false) {
        const int count = countGroup(key);
        if (count == 0 && !key.isEmpty()) return;
        categories.append(key);
        groups.append(CategoryGroup{key, title + QStringLiteral(" (%1)").arg(count), icon, datablock, count, {}, {}});
    };
    // A subset must narrow its category; otherwise its second menu entry adds no choice.
    const auto addSubset = [&](const QString& parent, const QString& key, const QString& title, const QString& icon) {
        if (countGroup(key) < countGroup(parent)) add(key, title, icon);
    };
    add({}, tr("All categories"), {});
    for (const QString& kind : {QStringLiteral("structure"), QStringLiteral("experiment")}) {
        add(QLatin1Char('@') + kind, kind == QLatin1String("structure") ? tr("Structure") : tr("Experiment"),
            kind == QLatin1String("structure") ? QStringLiteral("layer-group") : QStringLiteral("microscope"), true);
        QStringList seen;
        for (const Row& row : scoped) {
            if (row.kind != kind || seen.contains(row.category)) continue;
            seen.append(row.category);
            if (row.category == QLatin1String("atom_site") || row.category == QLatin1String("atom_site_aniso")) {
                if (seen.contains(QStringLiteral("@atoms"))) continue;
                seen.append(QStringLiteral("@atoms"));
                add(QStringLiteral("@atoms"), category_presentation(QStringLiteral("atom_site")).title,
                    category_presentation(QStringLiteral("atom_site")).icon);
                addSubset(QStringLiteral("@atoms"), QStringLiteral("@coordinates"), tr("Atomic coordinates"), QStringLiteral("map-marker-alt"));
                addSubset(QStringLiteral("@atoms"), QStringLiteral("@occupancies"), tr("Atomic occupancies"), QStringLiteral("fill"));
                addSubset(QStringLiteral("@atoms"), QStringLiteral("@displacement"),
                          category_presentation(QStringLiteral("atom_site_aniso")).title,
                          category_presentation(QStringLiteral("atom_site_aniso")).icon);
                continue;
            }
            const auto presentation = category_presentation(row.category);
            QString title = presentation.title;
            if (title.isEmpty()) { title = row.category; title.replace(QLatin1Char('_'), QLatin1Char(' ')); }
            add(row.category, title, presentation.icon);
            if (row.category == QLatin1String("peak")) {
                addSubset(row.category, QStringLiteral("@peakBroadening"), tr("Peak broadening"), QStringLiteral("arrows-alt-h"));
                addSubset(row.category, QStringLiteral("@peakMixing"), tr("Peak mixing"), QStringLiteral("shapes"));
                addSubset(row.category, QStringLiteral("@peakAsymmetry"), tr("Peak asymmetry"), QStringLiteral("balance-scale-left"));
            }
        }
    }
    // Any additional block kind remains selectable when the parameter walk grows.
    for (const Row& row : scoped) {
        if (row.kind == QLatin1String("structure") || row.kind == QLatin1String("experiment") || categories.contains(row.category)) continue;
        const auto presentation = category_presentation(row.category);
        QString title = presentation.title;
        if (title.isEmpty()) { title = row.category; title.replace(QLatin1Char('_'), QLatin1Char(' ')); }
        add(row.category, title, presentation.icon);
    }
    if (!categories.contains(category_filter_)) {
        beginFilterChange();
        category_filter_.clear();
        endFilterChange(Direction::Rows);
        emit categoryFilterChanged();
    }

    // The parameters the datablock and category leave: all, free, fixed.
    QList<int> counts{0, 0, 0};
    for (const Row& row : scoped) {
        if (!matches_group(category_filter_, row.kind, row.category, row.name)) continue;
        ++counts[0];
        ++counts[row.free ? 1 : 2];
    }

    const bool datablocks_changed = datablocks != datablocks_;
    const bool datablock_groups_changed = datablock_groups != datablock_groups_;
    const bool keys_changed = categories != categories_;
    const bool groups_changed = groups != category_groups_;
    const bool counts_changed = counts != variability_counts_;
    datablocks_ = std::move(datablocks);
    datablock_groups_ = std::move(datablock_groups);
    categories_ = std::move(categories);
    category_groups_ = std::move(groups);
    variability_counts_ = std::move(counts);
    if (datablocks_changed) emit datablocksChanged();
    if (datablock_groups_changed) emit datablockGroupsChanged();
    if (keys_changed) emit categoriesChanged();
    if (groups_changed) emit categoryGroupsChanged();
    if (counts_changed) emit variabilityCountsChanged();
}

void ParameterFilterModel::setDatablockFilter(const QString& datablock) {
    if (datablock != datablock_filter_) {
        beginFilterChange();
        datablock_filter_ = datablock;
        endFilterChange(Direction::Rows);
        emit datablockFilterChanged();
        refresh();
    }
}

void ParameterFilterModel::setCategoryFilter(const QString& category) {
    if (category != category_filter_) {
        beginFilterChange();
        category_filter_ = category;
        endFilterChange(Direction::Rows);
        emit categoryFilterChanged();
        refresh();
    }
}

void ParameterFilterModel::clearFilters() {
    setNameFilter({});
    setVariability(All);
    setCategoryFilter({});
    setDatablockFilter({});
}

QString ParameterFilterModel::text(int row, const QString& role) const {
    if (sourceModel() == nullptr || row < 0 || row >= rowCount()) {
        return {};
    }
    return data(index(row, 0), sourceModel()->roleNames().key(role.toUtf8())).toString();
}

void ParameterFilterModel::setNameFilter(const QString& filter) {
    if (filter != name_filter_) {
        beginFilterChange();
        name_filter_ = filter;
        endFilterChange(Direction::Rows);
        emit nameFilterChanged();
    }
}

ParameterItem* ParameterFilterModel::parameterAt(int row) const {
    if (sourceModel() == nullptr || row < 0 || row >= rowCount()) {
        return nullptr;
    }
    const int role = sourceModel()->roleNames().key("parameter");
    return qobject_cast<ParameterItem*>(data(index(row, 0), role).value<QObject*>());
}

int ParameterFilterModel::rowOf(ParameterItem* parameter) const {
    if (parameter == nullptr) {
        return -1;
    }
    for (int row = 0; row < rowCount(); ++row) {
        if (parameterAt(row) == parameter) {
            return row;
        }
    }
    return -1;
}

bool ParameterFilterModel::shows(ParameterItem* parameter) const {
    return rowOf(parameter) >= 0;
}

void ParameterFilterModel::setVariability(Variability variability) {
    if (variability != variability_) {
        beginFilterChange();
        variability_ = variability;
        endFilterChange(Direction::Rows);
        emit variabilityChanged();
    }
}

bool ParameterFilterModel::filterAcceptsRow(int source_row, const QModelIndex& source_parent) const {
    const QModelIndex index = sourceModel()->index(source_row, 0, source_parent);
    const QHash<int, QByteArray> roles = sourceModel()->roleNames();
    const auto value = [&](const char* name) { return sourceModel()->data(index, roles.key(name)); };
    if (!matches_datablock(datablock_filter_, value("blockKind").toString(), value("blockName").toString()) ||
        !matches_group(category_filter_, value("blockKind").toString(), value("category").toString(), value("name").toString())) {
        return false;
    }
    const bool free = value("free").toBool();
    if ((variability_ == Free && !free) || (variability_ == Fixed && free)) {
        return false;
    }
    return name_filter_.isEmpty() || value("path").toString().contains(name_filter_, Qt::CaseInsensitive) ||
           value("displayName").toString().contains(name_filter_, Qt::CaseInsensitive);
}

}  // namespace edi_app
