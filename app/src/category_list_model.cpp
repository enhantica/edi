// SPDX-License-Identifier: BSD-3-Clause
#include "category_list_model.hpp"

#include <QHash>
#include <algorithm>
#include <utility>

namespace edi_app {

CategoryPresentation category_presentation(const QString& id) {
    using T = CategoryListModel::Tier;
    // The titles are the core's (edi::category_title), which the report shows too; icons are Font Awesome 5 names, as
    // the base's GroupBox takes them.
    struct Look {
        T tier;
        const char* icon;
        bool extras_part = false;
    };
    static const QHash<QString, Look> table{
        {QStringLiteral("metadata"), {T::Basic, "archive"}},
        {QStringLiteral("space_group"), {T::Basic, "satellite"}},
        {QStringLiteral("cell"), {T::Basic, "cube"}},
        {QStringLiteral("atom_site"), {T::Basic, "atom"}},
        {QStringLiteral("atom_site_aniso"), {T::Basic, "arrows-alt"}},
        {QStringLiteral("scattering_length"), {T::Extras, "ruler"}},
        {QStringLiteral("experiment_type"), {T::Basic, "radiation"}},
        {QStringLiteral("data"), {T::Extras, "arrows-alt-h"}},
        {QStringLiteral("data_range"), {T::Basic, "arrows-alt-h"}},
        {QStringLiteral("instrument"), {T::Basic, "microscope"}},
        {QStringLiteral("peak"), {T::Basic, "shapes", true}},
        {QStringLiteral("background"), {T::Basic, "wave-square", true}},
        {QStringLiteral("linked_structure"), {T::Basic, "layer-group"}},
        {QStringLiteral("excluded_region"), {T::Basic, "eraser"}},
        {QStringLiteral("absorption"), {T::Extras, "tint"}},
        {QStringLiteral("preferred_orientation"), {T::Extras, "compass"}},
        {QStringLiteral("scattering_source"), {T::Extras, "atom"}},
        {QStringLiteral("refln"), {T::Extras, "list"}},
        {QStringLiteral("minimizer"), {T::Extras, "level-down-alt"}},
        {QStringLiteral("fitting_mode"), {T::Extras, "sliders-h"}},
        {QStringLiteral("alias"), {T::Extras, "tag"}},
        {QStringLiteral("constraint"), {T::Extras, "equals"}},
        {QStringLiteral("joint_fit"), {T::Extras, "link"}},
        {QStringLiteral("sequential_fit"), {T::Extras, "list-ol"}},
        {QStringLiteral("sequential_fit_extract"), {T::Extras, "filter"}},
        {QStringLiteral("fit_parameter"), {T::Extras, "history"}},
    };
    const Look look = table.value(id, {T::Extras, "question"});
    return {look.tier, edi::category_title(id.toStdString()), look.icon, look.extras_part};
}

namespace {
// The sidebar's order where it differs from the core's page order (edi ADR-0017 §3): each first id is shown
// directly before the second. Presentation only: the core's order (the Analysis table, the files) stands.
// A category shown elsewhere has no sidebar group: the experiment type is edited in the Experiments explorer.
std::vector<const edi::Category*> presentation_order(const std::vector<edi::Category>& categories) {
    static const std::pair<const char*, const char*> kShownBefore[] = {{"background", "instrument"},
                                                                       {"excluded_region", "linked_structure"}};
    static const char* const kShownElsewhere[] = {"experiment_type"};
    std::vector<const edi::Category*> ordered;
    for (const edi::Category& category : categories) {
        if (std::find(std::begin(kShownElsewhere), std::end(kShownElsewhere), category.id) == std::end(kShownElsewhere)) {
            ordered.push_back(&category);
        }
    }
    const auto position = [&ordered](const char* id) {
        for (std::size_t i = 0; i < ordered.size(); ++i) {
            if (ordered[i]->id == id) {
                return static_cast<std::ptrdiff_t>(i);
            }
        }
        return static_cast<std::ptrdiff_t>(-1);
    };
    for (const auto& [moved, anchor] : kShownBefore) {
        const std::ptrdiff_t from = position(moved);
        const std::ptrdiff_t to = position(anchor);
        if (from > to && to >= 0) {
            std::rotate(ordered.begin() + to, ordered.begin() + from, ordered.begin() + from + 1);
        }
    }
    return ordered;
}
}  // namespace

CategoryListModel::CategoryListModel(QObject* parent) : QAbstractListModel(parent) {}

void CategoryListModel::setCategories(const std::vector<edi::Category>& categories) {
    std::vector<Row> target;
    for (const edi::Category* shown : presentation_order(categories)) {
        const edi::Category& category = *shown;
        target.push_back({QString::fromStdString(category.id), static_cast<int>(category.rows), category.is_loop,
                          category.admitted});
    }
    const std::size_t before = rows_.size();
    const auto find = [](const std::vector<Row>& rows, const QString& id, std::size_t from) {
        for (std::size_t i = from; i < rows.size(); ++i) {
            if (rows[i].id == id) {
                return static_cast<int>(i);
            }
        }
        return -1;
    };
    for (int i = static_cast<int>(rows_.size()) - 1; i >= 0; --i) {
        if (find(target, rows_[i].id, 0) < 0) {
            beginRemoveRows(QModelIndex(), i, i);
            rows_.erase(rows_.begin() + i);
            endRemoveRows();
        }
    }
    for (std::size_t i = 0; i < target.size(); ++i) {
        if (i < rows_.size() && rows_[i].id == target[i].id) {
            if (rows_[i].items != target[i].items) {
                rows_[i].items = target[i].items;
                const QModelIndex at = index(static_cast<int>(i));
                emit dataChanged(at, at, {ItemCountRole});
            }
            continue;
        }
        const int found = find(rows_, target[i].id, i);
        const int row = static_cast<int>(i);
        if (found < 0) {
            beginInsertRows(QModelIndex(), row, row);
            rows_.insert(rows_.begin() + row, target[i]);
            endInsertRows();
        } else {
            beginMoveRows(QModelIndex(), found, found, QModelIndex(), row);
            const Row moved = rows_[found];
            rows_.erase(rows_.begin() + found);
            rows_.insert(rows_.begin() + row, moved);
            endMoveRows();
            if (rows_[i].items != target[i].items) {
                rows_[i].items = target[i].items;
                emit dataChanged(index(row), index(row), {ItemCountRole});
            }
        }
    }
    if (rows_.size() != before) {
        emit countChanged();
    }
}

bool CategoryListModel::contains(const QString& categoryId) const {
    for (const Row& row : rows_) {
        if (row.id == categoryId) {
            return true;
        }
    }
    return false;
}

int CategoryListModel::itemCount(const QString& categoryId) const {
    for (const Row& row : rows_) {
        if (row.id == categoryId) {
            return row.items;
        }
    }
    return 0;
}

int CategoryListModel::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : static_cast<int>(rows_.size());
}

QVariant CategoryListModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() >= static_cast<int>(rows_.size())) {
        return {};
    }
    const Row& row = rows_[static_cast<std::size_t>(index.row())];
    const CategoryPresentation presentation = category_presentation(row.id);
    switch (role) {
        case CategoryIdRole: return row.id;
        case TierRole: return presentation.tier == Basic ? QStringLiteral("Basic") : QStringLiteral("Extras");
        case TitleRole:
        case Qt::DisplayRole: return QString::fromUtf8(presentation.title);
        case IconRole: return QString::fromUtf8(presentation.icon);
        case ItemCountRole: return row.items;
        case IsLoopRole: return row.is_loop;
        case AdmittedRole: return row.admitted;
        case ExtrasPartRole: return presentation.extras_part;
        default: return {};
    }
}

QHash<int, QByteArray> CategoryListModel::roleNames() const {
    return {{CategoryIdRole, "categoryId"}, {TierRole, "tier"},           {TitleRole, "title"},
            {IconRole, "icon"},             {ItemCountRole, "itemCount"}, {IsLoopRole, "isLoop"},
            {AdmittedRole, "admitted"}, {ExtrasPartRole, "extrasPart"}};
}

}  // namespace edi_app
