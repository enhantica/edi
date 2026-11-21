// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_CATEGORY_LIST_MODEL_HPP
#define EDI_APP_CATEGORY_LIST_MODEL_HPP

#include <QAbstractListModel>
#include <QPointer>
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
    // group the app makes from the dictionary (GeneratedCategory), so every category of the file has a group, with
    // the count the file has: `text` gives the block's saved text, read on every call (the project caches it), and
    // `calculated` the categories the file holds while its calculation is current (edi::calculated_categories), which
    // a text made without calculating leaves out.
    void setCategories(const std::vector<edi::Category>& categories, const std::function<std::string()>& text = {},
                       const std::function<std::vector<edi::Category>()>& calculated = {});
    // The same list against the block's text and calculation as they are now: after a calculation, which adds
    // computed categories, or an edit no core category shows.
    void refresh();
    // The same rows as `other`, brought in by the same diff, so a view keeps the delegates of the ids both lists have.
    void mirror(const CategoryListModel& other) {
        // The other list's rows as they are, applied by the same diff: its text is not read and parsed again.
        other.settle();
        categories_ = other.categories_;
        text_ = other.text_;
        calculated_ = other.calculated_;
        applyRows(other.rows_);
    }
    int count() const {
        settle();
        return static_cast<int>(rows_.size());
    }
    Q_INVOKABLE bool contains(const QString& categoryId) const;
    Q_INVOKABLE int itemCount(const QString& categoryId) const;

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

   signals:
    void countChanged();

   private:
    // A list nothing shows or follows (no view, mirror or binding on its signals) is not brought up to date at each
    // change: the change is owed, and settled without signals when the list is next read (ADR-0096 rule 1), since the
    // block's text it reads is made and parsed for it.
    bool observed() const;
    void settle() const;
    mutable bool owed_ = false, quiet_ = false;
    struct Row;
    // Brings the rows to `target`: rows inserted, removed and moved by id, counts updated in place.
    void applyRows(const std::vector<Row>& target);
    struct Row {
        QString id;
        int items = 0;
        bool is_loop = false;
        bool admitted = true;
    };
    std::vector<Row> rows_;
    std::vector<edi::Category> categories_;
    std::function<std::string()> text_;
    std::function<std::vector<edi::Category>()> calculated_;
};

// One list that follows another block's categories: a page binds its groups to it, so changing the block (the next
// experiment) updates the rows by id and keeps the groups both blocks have, instead of making every group again for
// the new block's own model (ADR-0096 rule 2).
class CategoryListMirror : public CategoryListModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::CategoryListModel* source READ source WRITE setSource NOTIFY sourceChanged)

   public:
    explicit CategoryListMirror(QObject* parent = nullptr) : CategoryListModel(parent) {}
    CategoryListModel* source() const { return source_; }
    void setSource(CategoryListModel* source);

   signals:
    void sourceChanged();

   private:
    void follow();
    QPointer<CategoryListModel> source_;
    QMetaObject::Connection reset_, inserted_, removed_, changed_;
};

// The app's presentation of a category id: which sidebar tab shows it, its title and its icon
// (presentation only, I1). Every id the core returns has exactly one entry.
// `extras_part`: a Basic category that also has a group of its own name in Extras, for its settings
// (`peak`'s `cutoff_fwhm`).
struct CategoryPresentation {
    CategoryListModel::Tier tier{};
    QString title;
    QString icon;
    bool extras_part = false;
    QString tool_tip;  // what the group holds, one sentence from the dictionary's description
    // Only of use with measured data: hidden while its block has none (the owner, 2026-10-27). `extras_needs_data`
    // is the same for a Basic category's Extras part.
    bool needs_data = false;
    bool extras_needs_data = false;
    QString extras_title;  // the Extras part's own title, when it differs from the category's
};
CategoryPresentation category_presentation(const QString& id);
std::vector<const edi::Category*> category_presentation_order(const std::vector<edi::Category>&);

}  // namespace edi_app

#endif  // EDI_APP_CATEGORY_LIST_MODEL_HPP
