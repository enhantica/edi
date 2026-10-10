// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PARAMETER_TABLE_MODEL_HPP
#define EDI_APP_PARAMETER_TABLE_MODEL_HPP

#include <QSortFilterProxyModel>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>

#include "row_table_model.hpp"

namespace edi_app {

class ParameterItem;
class ParameterRegistry;

// The parameters a fit can vary, one row each, in page order (packet §3, §2b (iv)): the Analysis
// page's table. A parameter symmetry fixes or ties is not listed, and in a scan mode (sequential,
// independent) an experiment's parameters are listed for the selected experiment only (edi
// ADR-0019). The value, uncertainty and free roles follow each parameter, one dataChanged per row
// naming the changed roles, so sorting and filtering see edits (I3).
class ParameterTableModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(int freeCount READ freeCount NOTIFY freeCountChanged)
    Q_PROPERTY(int fixedCount READ fixedCount NOTIFY fixedCountChanged)

   public:
    ParameterTableModel(ParameterRegistry& registry, QObject* parent);
    int freeCount() const { return free_count_; }
    int fixedCount() const { return fixed_count_; }
    // The one experiment whose parameters are listed; empty lists every experiment's. Takes effect at
    // the next sync.
    void setExperimentScope(const QString& experiment);
    void sync();

   signals:
    void freeCountChanged();
    void fixedCountChanged();

   protected:
    // `value` and `free` write through the row's ParameterItem (assign_value, D5).
    bool setRole(int row, const QString& role, const QVariant& value) override;

   private:
    ParameterRegistry& registry_;
    QString experiment_scope_;
    int free_count_ = 0;
    int fixed_count_ = 0;
};

// The Analysis table's filter: a name substring and the variability (all, free or fixed).
class ParameterFilterModel : public QSortFilterProxyModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QString nameFilter READ nameFilter WRITE setNameFilter NOTIFY nameFilterChanged)
    Q_PROPERTY(Variability variability READ variability WRITE setVariability NOTIFY variabilityChanged)
    Q_PROPERTY(QString categoryFilter READ categoryFilter WRITE setCategoryFilter NOTIFY categoryFilterChanged)
    Q_PROPERTY(QStringList categories READ categories NOTIFY categoriesChanged)
    Q_PROPERTY(QVariantList categoryGroups READ categoryGroups NOTIFY categoriesChanged)

   public:
    enum Variability { All, Free, Fixed };
    Q_ENUM(Variability)

    explicit ParameterFilterModel(QObject* parent = nullptr);
    QString nameFilter() const { return name_filter_; }
    void setNameFilter(const QString& filter);
    Variability variability() const { return variability_; }
    void setVariability(Variability variability);
    void setSourceModel(QAbstractItemModel* source) override;
    QString categoryFilter() const { return category_filter_; }
    void setCategoryFilter(const QString& category);
    QStringList categories() const { return categories_; }
    QVariantList categoryGroups() const { return category_groups_; }
    Q_INVOKABLE QString text(int row, const QString& role) const;
    // The shown rows' parameters, for the table's selection (edi ADR-0017 §11): the one at a shown row (null
    // past the end), and whether a parameter is among the shown ones.
    Q_INVOKABLE edi_app::ParameterItem* parameterAt(int row) const;
    Q_INVOKABLE bool shows(edi_app::ParameterItem* parameter) const;

   signals:
    void nameFilterChanged();
    void variabilityChanged();
    void categoryFilterChanged();
    void categoriesChanged();

   protected:
    bool filterAcceptsRow(int source_row, const QModelIndex& source_parent) const override;

   private:
    void refreshCategories();
    QString category_filter_;
    QStringList categories_{QString()};
    QVariantList category_groups_;
    QList<QMetaObject::Connection> source_connections_;
    QString name_filter_;
    Variability variability_ = All;
};

}  // namespace edi_app

#endif  // EDI_APP_PARAMETER_TABLE_MODEL_HPP
