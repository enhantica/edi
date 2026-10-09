// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_table_model.hpp"

#include "parameter_item.hpp"
#include "parameter_registry.hpp"

namespace edi_app {

namespace {
const QStringList kRoles{"parameter", "path",  "blockKind", "blockName", "category", "rowLabel", "name",
                         "displayName", "value", "uncertainty", "hasUncertainty", "free", "minimum",
                         "maximum", "units", "refinable"};
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
        source_connections_.append(connect(source, &QAbstractItemModel::modelReset, this, &ParameterFilterModel::refreshCategories));
        source_connections_.append(connect(source, &QAbstractItemModel::rowsInserted, this, &ParameterFilterModel::refreshCategories));
        source_connections_.append(connect(source, &QAbstractItemModel::rowsRemoved, this, &ParameterFilterModel::refreshCategories));
        source_connections_.append(connect(source, &QAbstractItemModel::dataChanged, this, &ParameterFilterModel::refreshCategories));
    }
    refreshCategories();
}

void ParameterFilterModel::refreshCategories() {
    QStringList categories;
    if (sourceModel() != nullptr) {
        const int role = sourceModel()->roleNames().key("category");
        for (int row = 0; row < sourceModel()->rowCount(); ++row) {
            const QString category = sourceModel()->data(sourceModel()->index(row, 0), role).toString();
            if (!category.isEmpty() && !categories.contains(category)) {
                categories.append(category);
            }
        }
    }
    categories.sort();
    categories.prepend(QString());
    if (categories != categories_) {
        categories_ = categories;
        emit categoriesChanged();
    }
    if (!categories_.contains(category_filter_)) {
        setCategoryFilter({});
    }
}

void ParameterFilterModel::setCategoryFilter(const QString& category) {
    if (category != category_filter_) {
        beginFilterChange();
        category_filter_ = category;
        endFilterChange(Direction::Rows);
        emit categoryFilterChanged();
    }
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

bool ParameterFilterModel::shows(ParameterItem* parameter) const {
    if (parameter == nullptr) {
        return false;
    }
    for (int row = 0; row < rowCount(); ++row) {
        if (parameterAt(row) == parameter) {
            return true;
        }
    }
    return false;
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
    if (!category_filter_.isEmpty() && value("category").toString() != category_filter_) {
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
