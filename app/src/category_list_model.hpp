// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_CATEGORY_LIST_MODEL_HPP
#define EDI_APP_CATEGORY_LIST_MODEL_HPP

#include <QAbstractListModel>
#include <QString>
#include <QtQml/qqmlregistration.h>
#include <functional>
#include <vector>

#include "edi/categories.hpp"

namespace edi_app {

// A block's `.edi` categories in page order: presence and content from the core's *_categories;
// the tier ("Basic" or "Extras", the sidebar tab's name), title and icon from the app's
// presentation table.
class CategoryListModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Categories come from the core")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Tier { Basic, Extras };
    Q_ENUM(Tier)
    enum Role {
        CategoryIdRole = Qt::UserRole + 1,
        TierRole,
        TitleRole,
        IconRole,
        ItemCountRole,
        IsLoopRole,
        AdmittedRole,
        ExtrasPartRole,
        ToolTipRole,
        NeedsDataRole,
        ExtrasNeedsDataRole,
        ExtrasTitleRole
    };

    explicit CategoryListModel(QObject* parent = nullptr);

    // Bring the rows to the core's list: rows are inserted and removed by id, counts updated in place.
    // The core's categories of a block, and those its saved text carries that the core does not list, each with a
    // group the app makes from the dictionary (GeneratedCategory), so every category of the file has a group. The
    // text is read (a save) only when the core's set of categories changed: `text` gives it.
    void setCategories(const std::vector<edi::Category>& categories, const std::function<std::string()>& text = {});
    int count() const { return static_cast<int>(rows_.size()); }
    Q_INVOKABLE bool contains(const QString& categoryId) const;
    Q_INVOKABLE int itemCount(const QString& categoryId) const;

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

   signals:
    void countChanged();

   private:
    struct Row {
        QString id;
        int items = 0;
        bool is_loop = false;
        bool admitted = true;
    };
    std::vector<Row> rows_;
    std::vector<std::string> core_ids_;
    std::vector<Row> generated_;
};

// The app's presentation of a category id: which sidebar tab shows it, its title and its icon
// (presentation only, I1). Every id the core returns has exactly one entry.
// `extras_part`: a Basic category that also has a group of its own name in Extras, for its settings
// (`peak`'s `cutoff_fwhm`).
struct CategoryPresentation {
    CategoryListModel::Tier tier;
    QString title;
    QString icon;
    bool extras_part = false;
    QString tool_tip;  // the title and the `.edi` name, from the dictionary
    // Only of use with measured data: hidden while its block has none (the owner, 2026-10-27). `extras_needs_data`
    // is the same for a Basic category's Extras part.
    bool needs_data = false;
    bool extras_needs_data = false;
    QString extras_title;  // the Extras part's own title, when it differs from the category's
};
CategoryPresentation category_presentation(const QString& id);

}  // namespace edi_app

#endif  // EDI_APP_CATEGORY_LIST_MODEL_HPP
