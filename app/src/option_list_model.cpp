// SPDX-License-Identifier: BSD-3-Clause
#include "option_list_model.hpp"

#include <cstddef>

namespace edi_app {

OptionListModel::OptionListModel(QObject* parent) : QAbstractListModel(parent) {}

void OptionListModel::setOptions(const std::vector<std::string>& tokens, const std::string& default_token,
                                 const std::vector<std::string>& labels) {
    QStringList next;
    QStringList next_labels;
    for (std::size_t index = 0; index < tokens.size(); ++index) {
        next.append(QString::fromStdString(tokens[index]));
        next_labels.append(QString::fromStdString(index < labels.size() ? labels[index] : tokens[index]));
    }
    const QString next_default = default_token.empty() ? next.value(0) : QString::fromStdString(default_token);
    if (next == tokens_ && next_labels == labels_ && next_default == default_token_) {
        return;
    }
    const bool count_changed = next.size() != tokens_.size();
    beginResetModel();  // an option set changes only when the block's type does
    tokens_ = next;
    labels_ = next_labels;
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
        case TokenRole: return token;
        case LabelRole:
        case Qt::DisplayRole: return labels_.value(index.row(), token);
        case IsDefaultRole: return token == default_token_;
        default: return {};
    }
}

QHash<int, QByteArray> OptionListModel::roleNames() const {
    return {{TokenRole, "token"}, {LabelRole, "label"}, {IsDefaultRole, "isDefault"}};
}

}  // namespace edi_app
