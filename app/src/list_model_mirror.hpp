// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_LIST_MODEL_MIRROR_HPP
#define EDI_APP_LIST_MODEL_MIRROR_HPP

#include <QAbstractListModel>
#include <QList>
#include <QPointer>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// One list that shows another list model's rows, whichever model that is: a view bound to it keeps its delegates when
// the source becomes another block's list of the same kind (the next experiment's peak fields), and only the rows that
// differ are inserted or removed; the others are announced as changed, so each delegate reads its new row (ADR-0096
// rule 2). The source's own changes pass through as they are. Every source is expected to have the same roles.
class ListModelMirror : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QAbstractItemModel* source READ source WRITE setSource NOTIFY sourceChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    explicit ListModelMirror(QObject* parent = nullptr) : QAbstractListModel(parent) {}
    QAbstractItemModel* source() const { return source_; }
    void setSource(QAbstractItemModel* source);
    int count() const { return rowCount(); }

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    bool setData(const QModelIndex& index, const QVariant& value, int role) override;
    QHash<int, QByteArray> roleNames() const override;

   signals:
    void sourceChanged();
    void countChanged();

   private:
    void follow();
    QPointer<QAbstractItemModel> source_;
    QHash<int, QByteArray> roles_;
    QList<QMetaObject::Connection> connections_;
};

}  // namespace edi_app

#endif  // EDI_APP_LIST_MODEL_MIRROR_HPP
