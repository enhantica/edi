// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_ROW_TABLE_MODEL_HPP
#define EDI_APP_ROW_TABLE_MODEL_HPP

#include <QAbstractListModel>
#include <QList>
#include <QStringList>
#include <QVariant>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// The shared shape of edi's list models: each row is keyed by the core object it shows and carries
// one value per role. `setTableRows` moves the model to a new table by single-row removals,
// inserts and moves — never a reset — and emits one dataChanged per row whose values changed,
// naming only the changed roles. A role holding a ParameterItem keeps the same object while the
// parameter is shown, so a value edit needs no model signal at all.
class RowTableModel : public QAbstractListModel {
    Q_OBJECT
    QML_ANONYMOUS
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    struct Row {
        const void* key = nullptr;
        QList<QVariant> values;  // one per role, in roleNames order
    };

    RowTableModel(const QStringList& roles, QObject* parent);

    int count() const { return static_cast<int>(rows_.size()); }
    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;
    // A write to a writable role goes through the model's setRole (then the core); the change comes
    // back as the ordinary dataChanged of the next publish.
    bool setData(const QModelIndex& index, const QVariant& value, int role) override;
    Qt::ItemFlags flags(const QModelIndex& index) const override;
    // The value of a role by name (C++ only: the QML contract carries no QVariant, I2).
    QVariant get(int row, const QString& role) const;
    // A role's value as text, for QML that shows a few rows without a view over all of them.
    Q_INVOKABLE QString text(int row, const QString& role) const { return get(row, role).toString(); }

   signals:
    void countChanged();

   protected:
    // Write one role of one row; false when the role is not writable or the core refused.
    virtual bool setRole(int row, const QString& role, const QVariant& value);
    void setTableRows(const QList<Row>& rows);
    // One row's values, the row staying where it is: only the roles that differ are announced.
    void setTableRow(int row, const QList<QVariant>& values);
    const void* keyAt(int row) const { return row >= 0 && row < rows_.size() ? rows_.at(row).key : nullptr; }
    // A row's values as data() and get() read them: those the row holds, unless a model builds them on demand.
    virtual QList<QVariant> rowValues(int row) const { return rows_.at(row).values; }
    // Every role of rows first..last changed (a model that builds its values on demand announces them so).
    void announceRows(int first, int last) {
        if (first <= last) {
            emit dataChanged(index(first), index(last));
        }
    }
    int roleIndex(int role) const { return role - Qt::UserRole - 1; }

   private:
    QStringList roles_;
    QList<Row> rows_;
};

}  // namespace edi_app

#endif  // EDI_APP_ROW_TABLE_MODEL_HPP
