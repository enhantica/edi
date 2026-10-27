// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PARAMETER_TABLE_MODEL_HPP
#define EDI_APP_PARAMETER_TABLE_MODEL_HPP

#include <QSortFilterProxyModel>
#include <QtQml/qqmlregistration.h>

#include "row_table_model.hpp"

namespace edi_app {

class ParameterItem;
class ParameterRegistry;

// Every numerical model input, one row each, in page order: the Analysis page's table. Parameters and descriptors
// alike, with whether a fit can vary each and why not (edi ADR-0053); in a scan mode (sequential, independent) an
// experiment's are listed for the selected experiment only (edi ADR-0019). The value, uncertainty and free roles follow
// each parameter, one dataChanged per row naming the changed roles, so sorting and filtering see edits (I3).
class ParameterTableModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(int freeCount READ freeCount NOTIFY freeCountChanged)
    Q_PROPERTY(int fixedCount READ fixedCount NOTIFY fixedCountChanged)
    // Rows no fit can vary that are not free; free, fixed and these partition the rows.
    Q_PROPERTY(int notFittableCount READ notFittableCount NOTIFY notFittableCountChanged)
    // The rows each show-filter adds, by ParameterItem::FitGroup from NotMeasured: the group's rows that are not free.
    Q_PROPERTY(QList<int> groupCounts READ groupCounts NOTIFY groupCountsChanged)

   public:
    ParameterTableModel(ParameterRegistry& registry, QObject* parent);
    int freeCount() const { return free_count_; }
    int fixedCount() const { return fixed_count_; }
    int notFittableCount() const { return not_fittable_count_; }
    QList<int> groupCounts() const { return group_counts_; }
    // The one experiment whose parameters are listed; empty lists every experiment's. Takes effect at
    // the next sync.
    void setExperimentScope(const QString& experiment);
    void sync();

   signals:
    void freeCountChanged();
    void fixedCountChanged();
    void notFittableCountChanged();
    void groupCountsChanged();

   protected:
    // `value` and `free` write through the row's ParameterItem (assign_value, D5).
    bool setRole(int row, const QString& role, const QVariant& value) override;

   private:
    ParameterRegistry& registry_;
    QString experiment_scope_;
    int free_count_ = 0;
    int fixed_count_ = 0;
    int not_fittable_count_ = 0;
    QList<int> group_counts_{0, 0, 0, 0};
};

// One entry of an Analysis filter picker (datablocks or categories): the filter key, its title with the parameter
// count, its icon, whether it stands for a whole datablock kind (shown bold), and for a datablock entry its kind and
// name, which give its colour. QML reads a list of them as an array (edi ADR-0030).
struct CategoryGroup {
    Q_GADGET
    QML_VALUE_TYPE(categoryGroup)
    Q_PROPERTY(QString key MEMBER key CONSTANT)
    Q_PROPERTY(QString title MEMBER title CONSTANT)
    Q_PROPERTY(QString icon MEMBER icon CONSTANT)
    Q_PROPERTY(bool datablock MEMBER datablock CONSTANT)
    Q_PROPERTY(int count MEMBER count CONSTANT)
    Q_PROPERTY(QString blockKind MEMBER block_kind CONSTANT)
    Q_PROPERTY(QString blockName MEMBER block_name CONSTANT)

   public:
    QString key;
    QString title;
    QString icon;
    bool datablock = false;
    int count = 0;
    QString block_kind;
    QString block_name;
    bool operator==(const CategoryGroup&) const = default;
};

// The Analysis table's filters (edi ADR-0046): the datablock, the category, the variability (all, free, fixed, or not
// fittable: free, fixed and not fittable partition the rows, edi ADR-0053) and a
// name substring. Each narrows the next: the categories listed are those of the selected datablocks, the variability
// counts those of the selected datablocks and category, and the name searches only what the three leave. Every count
// is a number of parameters, and a selection that no longer exists after a change returns to all.
class ParameterFilterModel : public QSortFilterProxyModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QString nameFilter READ nameFilter WRITE setNameFilter NOTIFY nameFilterChanged)
    Q_PROPERTY(Variability variability READ variability WRITE setVariability NOTIFY variabilityChanged)
    Q_PROPERTY(QString datablockFilter READ datablockFilter WRITE setDatablockFilter NOTIFY datablockFilterChanged)
    Q_PROPERTY(QStringList datablocks READ datablocks NOTIFY datablocksChanged)
    Q_PROPERTY(QList<edi_app::CategoryGroup> datablockGroups READ datablockGroups NOTIFY datablockGroupsChanged)
    Q_PROPERTY(QString categoryFilter READ categoryFilter WRITE setCategoryFilter NOTIFY categoryFilterChanged)
    Q_PROPERTY(QStringList categories READ categories NOTIFY categoriesChanged)
    Q_PROPERTY(QList<edi_app::CategoryGroup> categoryGroups READ categoryGroups NOTIFY categoryGroupsChanged)
    // The parameters the datablock and category selections leave: all, free, fixed and not fittable.
    Q_PROPERTY(QList<int> variabilityCounts READ variabilityCounts NOTIFY variabilityCountsChanged)
    // Which groups of rows no fit can vary are shown on top of the fittable ones (the Settings tab's show-filters, the
    // owner, 2026-10-26), by ParameterItem::FitGroup from NotMeasured. A value marked free is shown whatever they say.
    Q_PROPERTY(QList<bool> shownGroups READ shownGroups NOTIFY shownGroupsChanged)

   public:
    enum Variability { All, Free, Fixed, NotFittable };
    Q_ENUM(Variability)

    explicit ParameterFilterModel(QObject* parent = nullptr);
    QString nameFilter() const { return name_filter_; }
    void setNameFilter(const QString& filter);
    Variability variability() const { return variability_; }
    void setVariability(Variability variability);
    void setSourceModel(QAbstractItemModel* source) override;
    QString datablockFilter() const { return datablock_filter_; }
    void setDatablockFilter(const QString& datablock);
    QStringList datablocks() const { return datablocks_; }
    QList<CategoryGroup> datablockGroups() const { return datablock_groups_; }
    QString categoryFilter() const { return category_filter_; }
    void setCategoryFilter(const QString& category);
    QList<int> variabilityCounts() const { return variability_counts_; }
    QList<bool> shownGroups() const { return shown_groups_; }
    // Show or hide one group (ParameterItem::FitGroup, NotMeasured to FixedSetting).
    Q_INVOKABLE void setShownGroup(int group, bool shown);
    // Every filter back to all, and the name filter empty, in one step.
    Q_INVOKABLE void clearFilters();
    QStringList categories() const { return categories_; }
    QList<CategoryGroup> categoryGroups() const { return category_groups_; }
    Q_INVOKABLE QString text(int row, const QString& role) const;
    // The shown rows' parameters, for the table's selection (edi ADR-0017 §11): the one at a shown row (null
    // past the end), the row a parameter is shown at (-1 when it is not shown), and whether it is shown.
    Q_INVOKABLE edi_app::ParameterItem* parameterAt(int row) const;
    Q_INVOKABLE int rowOf(edi_app::ParameterItem* parameter) const;
    Q_INVOKABLE bool shows(edi_app::ParameterItem* parameter) const;

   signals:
    void nameFilterChanged();
    void variabilityChanged();
    void datablockFilterChanged();
    void datablocksChanged();
    void datablockGroupsChanged();
    void categoryFilterChanged();
    void categoriesChanged();
    void categoryGroupsChanged();
    void variabilityCountsChanged();
    void shownGroupsChanged();

   protected:
    bool filterAcceptsRow(int source_row, const QModelIndex& source_parent) const override;

   private:
    // Rebuilds the pickers' lists and counts from the current selections; one that is no longer listed returns to all.
    void refresh();
    bool shownByGroup(bool free, int group) const;
    // Not measured in this fit shown, symmetry, constraints and setup values not (the owner's defaults).
    QList<bool> shown_groups_{true, false, false, false};
    QString datablock_filter_;
    QStringList datablocks_{QString()};
    QList<CategoryGroup> datablock_groups_;
    QList<int> variability_counts_{0, 0, 0, 0};
    QString category_filter_;
    QStringList categories_{QString()};
    QList<CategoryGroup> category_groups_;
    QList<QMetaObject::Connection> source_connections_;
    QString name_filter_;
    Variability variability_ = All;
};

}  // namespace edi_app

#endif  // EDI_APP_PARAMETER_TABLE_MODEL_HPP
