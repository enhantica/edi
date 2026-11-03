// SPDX-License-Identifier: BSD-3-Clause
#include "category_list_model.hpp"

#include <QHash>
#include <algorithm>
#include <iterator>
#include <string>
#include <string_view>
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
        // The magnetic structure's Main groups (edi ADR-0068); its operators, parent group and form factors are Extra.
        {QStringLiteral("space_group_magn"), {T::Basic}},
        {QStringLiteral("parent_propagation_vector"), {T::Basic}},
        {QStringLiteral("atom_site_moment"), {T::Basic}},
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
        // The Report page has one tab: its saved reports are listed there.
        {QStringLiteral("report_file"), {T::Basic}},
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
// Where a category sorts in the sidebar: the dictionary's place, except that Extra lists the magnetic operators and
// the moments in the cell after the bonds, so the nuclear groups come first (the owner, 2026-11-03). The files keep
// the dictionary's order.
std::pair<int, std::size_t> sidebar_order(std::string_view id) {
    static const char* const kMagneticExtras[] = {"space_group_symop_magn_operation",
                                                  "space_group_symop_magn_centering", "expanded_atom_site_moment"};
    const auto bonds = edi::category_order("geom_bond");
    for (std::size_t i = 0; i < std::size(kMagneticExtras); ++i) {
        if (id == kMagneticExtras[i]) {
            return {bonds.first, bonds.second + 1 + i};
        }
    }
    return edi::category_order(id);
}

// The sidebar's order is the dictionary's order number, the files' order, so the app keeps no order of its own beyond
// sidebar_order; categories the dictionary does not order keep the core's order, last. A category shown elsewhere
// has no sidebar group: the experiment type is edited in the Experiments explorer, and a structure's saved view
// (`_structure_view`) in Extra's Appearance group.
std::vector<const edi::Category*> presentation_order(const std::vector<edi::Category>& categories) {
    // The magnetic form factors are chosen per site in the Magnetic moments group, and the parent group shows in
    // the Magnetic space group group when it differs from the space group (edi ADR-0068).
    static const char* const kShownElsewhere[] = {"experiment_type", "structure_view", "magnetic_form_factor",
                                                  "parent_space_group"};
    std::vector<const edi::Category*> ordered;
    for (const edi::Category& category : categories) {
        if (std::find(std::begin(kShownElsewhere), std::end(kShownElsewhere), category.id) == std::end(kShownElsewhere)) {
            ordered.push_back(&category);
        }
    }
    std::stable_sort(ordered.begin(), ordered.end(), [](const edi::Category* a, const edi::Category* b) {
        return sidebar_order(a->id) < sidebar_order(b->id);
    });
    return ordered;
}
}  // namespace

CategoryListModel::CategoryListModel(QObject* parent) : QAbstractListModel(parent) {}

void CategoryListModel::refresh() {
    setCategories(std::vector<edi::Category>(categories_), std::function<std::string()>(text_),
                  std::function<std::vector<edi::Category>()>(calculated_));
}

void CategoryListModel::setCategories(const std::vector<edi::Category>& categories,
                                      const std::function<std::string()>& text,
                                      const std::function<std::vector<edi::Category>()>& calculated) {
    categories_ = categories;
    text_ = text;
    calculated_ = calculated;
    // The Atomic displacement and Magnetic moments groups list every atom site, so their headers count the sites.
    int sites = 0;
    for (const edi::Category& category : categories) {
        if (category.id == "atom_site") {
            sites = static_cast<int>(category.rows);
        }
    }
    std::vector<Row> target;
    for (const edi::Category* shown : presentation_order(categories)) {
        const edi::Category& category = *shown;
        const bool per_site = category.id == "atom_site_aniso" || category.id == "atom_site_moment";
        target.push_back({QString::fromStdString(category.id), per_site ? sites : static_cast<int>(category.rows),
                          category.is_loop, category.admitted});
        // An experiment's background carries its estimate settings (`_background_estimate`), a category of its own
        // with its own group; the core lists them with the background.
        if (category.id == "background") {
            target.push_back({QStringLiteral("background_estimate"), 0, false, true});
        }
    }
    std::vector<Row> generated;
    // Only what a user sets or reads gets a group (the owner, 2026-10-27): not the file header, the Cartesian
    // transform, the calculator (there is one), the curves' presentation order, the block list or the correlations,
    // which the Correlations tab shows. The bond settings get a designed group of their own later, and the type is
    // shown elsewhere.
    // Nor what another group shows: a structure's saved view (Appearance), its magnetic form factors (Magnetic
    // moments) and its parent group (Magnetic space group, when it differs from the space group).
    static const char* const kNotGenerated[] = {"geom",     "experiment_type",           "edi",
                                                "calculator", "atom_sites_cartn_transform", "pd_calc_overall",
                                                "pd_block", "fit_parameter_correlation", "structure_view",
                                                "magnetic_form_factor", "parent_space_group"};
    const auto generates = [](const std::string& id) {
        return std::find(std::begin(kNotGenerated), std::end(kNotGenerated), id) == std::end(kNotGenerated) &&
               !edi::category_label(id).empty();
    };
    if (text) {
        const std::string saved = text();
        for (const std::string& id : edi::text_category_ids(saved)) {
            if (!generates(id)) {
                continue;
            }
            const edi::TextCategory category = edi::text_category(saved, id);
            generated.push_back({QString::fromStdString(id),
                                 category.loop ? static_cast<int>(category.rows.size()) : 0, category.loop, true});
        }
    }
    if (calculated) {
        for (const edi::Category& category : calculated()) {
            const QString id = QString::fromStdString(category.id);
            const bool listed = std::any_of(generated.begin(), generated.end(), [&id](const Row& row) { return row.id == id; });
            if (!listed && generates(category.id)) {
                generated.push_back({id, static_cast<int>(category.rows), category.is_loop, true});
            }
        }
    }
    for (const Row& row : generated) {
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
        return sidebar_order(a.id.toStdString()) < sidebar_order(b.id.toStdString());
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
