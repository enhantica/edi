// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_OPTION_LIST_MODEL_HPP
#define EDI_APP_OPTION_LIST_MODEL_HPP

#include <QAbstractListModel>
#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <string>
#include <vector>

namespace edi_app {

// The options one selector offers: always the core's supported set for the block's type, never a
// list written in the app. Roles `token` (the verbatim `.edi` token),
// `label` (what the combo shows) and `isDefault`.
class OptionListModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Options come from the core")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Role { TokenRole = Qt::UserRole + 1, LabelRole, IsDefaultRole };

    explicit OptionListModel(QObject* parent = nullptr);

    // Replace the options; the first is the default unless `default_token` names another.
    void setOptions(const std::vector<std::string>& tokens, const std::string& default_token = {});
    int count() const { return static_cast<int>(tokens_.size()); }
    Q_INVOKABLE int indexOf(const QString& token) const { return static_cast<int>(tokens_.indexOf(token)); }
    Q_INVOKABLE QString tokenAt(int row) const { return row >= 0 && row < tokens_.size() ? tokens_.at(row) : QString(); }

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

   signals:
    void countChanged();

   private:
    QStringList tokens_;
    QString default_token_;
};

}  // namespace edi_app

#endif  // EDI_APP_OPTION_LIST_MODEL_HPP
