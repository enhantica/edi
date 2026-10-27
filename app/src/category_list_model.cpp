// SPDX-License-Identifier: BSD-3-Clause
#include "category_list_model.hpp"

#include <QHash>
#include <algorithm>
#include <string>
#include <utility>

#include "edi/display.hpp"

namespace edi_app {

CategoryPresentation category_presentation(const QString& id) {
    using T = CategoryListModel::Tier;
    // Titles and icons are crysta's dictionary's, through the core's bridge, which the report reads too; the app keeps
    // only where a category sits: the Basic or the Extras group, and whether it also shows in Extras.
    struct Place {
        T tier;
        bool extras_part = false;
        bool needs_data = false;
        bool extras_needs_data = false;
    };
    static const QHash<QString, Place> places{
        {QStringLiteral("metadata"), {T::Basic}},         {QStringLiteral("space_group"), {T::Basic}},
        {QStringLiteral("cell"), {T::Basic}},             {QStringLiteral("atom_site"), {T::Basic}},
        {QStringLiteral("atom_site_aniso"), {T::Basic}},  {QStringLiteral("experiment_type"), {T::Basic}},
        {QStringLiteral("data_range"), {T::Basic}},       {QStringLiteral("instrument"), {T::Basic}},
        {QStringLiteral("peak"), {T::Basic, true}},
        {QStringLiteral("background"), {T::Basic}},
        // The estimate's settings, of use only with measured data (the owner, 2026-10-27).
        {QStringLiteral("background_estimate"), {T::Extras, false, true}},
        {QStringLiteral("linked_structure"), {T::Basic}},
        {QStringLiteral("excluded_region"), {T::Basic, false, true}},
        {QStringLiteral("extinction"), {T::Basic}},
        // What only a fit uses: hidden without measured data (the owner, 2026-10-27).
        {QStringLiteral("minimizer"), {T::Extras, false, true}},
        {QStringLiteral("fitting_mode"), {T::Extras, false, true}},
        {QStringLiteral("refine_ls"), {T::Extras, false, true}},
        {QStringLiteral("joint_fit"), {T::Extras, false, true}},
        {QStringLiteral("sequential_fit"), {T::Extras, false, true}},
        {QStringLiteral("sequential_fit_extract"), {T::Extras, false, true}},
        {QStringLiteral("fit_parameter"), {T::Extras, false, true}},
    };
    const Place place = places.value(id, {T::Extras});
    const std::string key = id.toStdString();
    const QString icon = QString::fromStdString(edi::category_icon(key));
    // Extra's peak group holds only the cutoff, so it is not read as a second profile group.
    const QString extras_title = id == QStringLiteral("peak") ? QObject::tr("Peak cutoff") : QString();
    return {place.tier,
            QString::fromStdString(edi::category_label(key)),
            icon.isEmpty() ? QStringLiteral("question") : icon,
            place.extras_part,
            QString::fromStdString(edi::category_tooltip(key)),
            place.needs_data,
            place.extras_needs_data,
            extras_title};
}

namespace {
// The sidebar's order is the dictionary's order number, the files' order, so the app
// keeps no order of its own; categories the dictionary does not order keep the core's order, last. A category
// shown elsewhere has no sidebar group: the experiment type is edited in the Experiments explorer.
std::vector<const edi::Category*> presentation_order(const std::vector<edi::Category>& categories) {
    static const char* const kShownElsewhere[] = {"experiment_type"};
    std::vector<const edi::Category*> ordered;
    for (const edi::Category& category : categories) {
        if (std::find(std::begin(kShownElsewhere), std::end(kShownElsewhere), category.id) == std::end(kShownElsewhere)) {
            ordered.push_back(&category);
        }
    }
    std::stable_sort(ordered.begin(), ordered.end(), [](const edi::Category* a, const edi::Category* b) {
        return edi::category_order(a->id) < edi::category_order(b->id);
    });
    return ordered;
}
}  // namespace

CategoryListModel::CategoryListModel(QObject* parent) : QAbstractListModel(parent) {}

void CategoryListModel::setCategories(const std::vector<edi::Category>& categories,
                                      const std::function<std::string()>& text) {
    std::vector<Row> target;
    for (const edi::Category* shown : presentation_order(categories)) {
        const edi::Category& category = *shown;
        target.push_back({QString::fromStdString(category.id), static_cast<int>(category.rows), category.is_loop,
                          category.admitted});
        // An experiment's background carries its estimate settings (`_background_estimate`), a category of its own
        // with its own group; the core lists them with the background.
        if (category.id == "background") {
            target.push_back({QStringLiteral("background_estimate"), 0, false, true});
        }
    }
    std::vector<std::string> ids;
    for (const edi::Category& category : categories) {
        ids.push_back(category.id);
    }
    if (text && ids != core_ids_) {
        core_ids_ = ids;
        generated_.clear();
        const std::string saved = text();
        // Only what a user sets or reads gets a group (the owner, 2026-10-27): not the file header, the Cartesian
        // transform, the calculator (there is one), the curves' presentation order, the block list or the
        // correlations, which the Correlations tab shows. The bond settings get a designed group of their own later,
        // and the type is shown elsewhere.
        static const char* const kNotGenerated[] = {"geom",     "experiment_type",           "edi",
                                                    "calculator", "atom_sites_cartn_transform", "pd_calc_overall",
                                                    "pd_block", "fit_parameter_correlation"};
        for (const std::string& id : edi::text_category_ids(saved)) {
            const bool excluded =
                std::find(std::begin(kNotGenerated), std::end(kNotGenerated), id) != std::end(kNotGenerated);
            if (excluded || edi::category_label(id).empty()) {
                continue;
            }
            const edi::TextCategory category = edi::text_category(saved, id);
            generated_.push_back({QString::fromStdString(id),
                                  category.loop ? static_cast<int>(category.rows.size()) : 0, category.loop, true});
        }
    }
    for (const Row& row : generated_) {
        const bool listed = std::any_of(target.begin(), target.end(), [&row](const Row& held) { return held.id == row.id; });
        // A file's `data` loop is the core's measured data or calculation range.
        const bool data = row.id == QLatin1String("data") &&
                          std::any_of(target.begin(), target.end(), [](const Row& held) {
                              return held.id == QLatin1String("data_range");
                          });
        if (!listed && !data) {
            target.push_back(row);
        }
    }
    std::stable_sort(target.begin(), target.end(), [](const Row& a, const Row& b) {
        return edi::category_order(a.id.toStdString()) < edi::category_order(b.id.toStdString());
    });
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
        case Qt::DisplayRole: return presentation.title;
        case IconRole: return presentation.icon;
        case ItemCountRole: return row.items;
        case IsLoopRole: return row.is_loop;
        case AdmittedRole: return row.admitted;
        case ExtrasPartRole: return presentation.extras_part;
        case ToolTipRole: return presentation.tool_tip;
        case NeedsDataRole: return presentation.needs_data;
        case ExtrasNeedsDataRole: return presentation.extras_needs_data;
        case ExtrasTitleRole: return presentation.extras_title;
        default: return {};
    }
}

QHash<int, QByteArray> CategoryListModel::roleNames() const {
    return {{CategoryIdRole, "categoryId"}, {TierRole, "tier"},           {TitleRole, "title"},
            {IconRole, "icon"},             {ItemCountRole, "itemCount"}, {IsLoopRole, "isLoop"},
            {AdmittedRole, "admitted"}, {ExtrasPartRole, "extrasPart"}, {ToolTipRole, "toolTip"},
            {NeedsDataRole, "needsData"},   {ExtrasNeedsDataRole, "extrasNeedsData"}, {ExtrasTitleRole, "extrasTitle"}};
}

}  // namespace edi_app
