// SPDX-License-Identifier: BSD-3-Clause
#include "option_list_model.hpp"

namespace edi_app {

OptionListModel::OptionListModel(QObject* parent) : QAbstractListModel(parent) {}

void OptionListModel::setOptions(const std::vector<std::string>& tokens, const std::string& default_token) {
    QStringList next;
    for (const std::string& token : tokens) {
        next.append(QString::fromStdString(token));
    }
    const QString next_default = default_token.empty() ? next.value(0) : QString::fromStdString(default_token);
    if (next == tokens_ && next_default == default_token_) {
        return;
    }
    const bool count_changed = next.size() != tokens_.size();
    beginResetModel();  // an option set changes only when the block's type does
    tokens_ = next;
    default_token_ = next_default;
    endResetModel();
    if (count_changed) {
        emit countChanged();
    }
}

int OptionListModel::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : static_cast<int>(tokens_.size());
}

QVariant OptionListModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() >= tokens_.size()) {
        return {};
    }
    const QString& token = tokens_.at(index.row());
    switch (role) {
        case TokenRole:
        case LabelRole:
        case Qt::DisplayRole: return token;
        case IsDefaultRole: return token == default_token_;
        default: return {};
    }
}

QHash<int, QByteArray> OptionListModel::roleNames() const {
    return {{TokenRole, "token"}, {LabelRole, "label"}, {IsDefaultRole, "isDefault"}};
}

}  // namespace edi_app
