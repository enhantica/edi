// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_COMBO_BOX_METRICS_HPP
#define EDI_APP_COMBO_BOX_METRICS_HPP

#include <QAbstractItemModel>
#include <QFont>
#include <QObject>
#include <QPointer>
#include <QVariant>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// ADR-0026: measure a bounded sample once; fit progress does not resize the selector.
class ComboBoxMetrics : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QObject* comboBox READ comboBox WRITE setComboBox NOTIFY comboBoxChanged)
    Q_PROPERTY(int count MEMBER count_ NOTIFY countChanged)
    Q_PROPERTY(QString textRole MEMBER text_role_ NOTIFY textRoleChanged)
    Q_PROPERTY(QString displayText MEMBER display_text_ NOTIFY displayTextChanged)
    Q_PROPERTY(QFont font MEMBER font_ NOTIFY fontChanged)
    Q_PROPERTY(qreal optionTextWidth READ optionTextWidth NOTIFY optionTextWidthChanged)
    Q_PROPERTY(qreal displayTextWidth READ displayTextWidth NOTIFY displayTextWidthChanged)

   public:
    explicit ComboBoxMetrics(QObject* parent = nullptr);
    QObject* comboBox() const { return control_; }
    void setComboBox(QObject* control);
    qreal optionTextWidth() const { return option_width_; }
    qreal displayTextWidth() const { return display_width_; }

   signals:
    void comboBoxChanged();
    void countChanged();
    void textRoleChanged();
    void displayTextChanged();
    void fontChanged();
    void optionTextWidthChanged();
    void displayTextWidthChanged();

   private:
    int sampledCount() const;
    Q_SLOT void observeModel();
    void invalidate();
    void schedule();
    void refresh();

    QPointer<QObject> control_;
    QMetaObject::Connection control_model_connection_;
    QPointer<QAbstractItemModel> model_object_;
    int count_ = 0;
    QString text_role_, display_text_;
    QFont font_;
    QList<QMetaObject::Connection> model_connections_;
    qreal option_width_ = 0.0, display_width_ = 0.0;
    bool dirty_ = true, pending_ = false;
};

}  // namespace edi_app

#endif
