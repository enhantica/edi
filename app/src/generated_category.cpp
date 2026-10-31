// SPDX-License-Identifier: BSD-3-Clause
#include "generated_category.hpp"

#include <string>
#include <vector>

#include "edi/display.hpp"

namespace edi_app {

void GeneratedRows::setRows(QList<QStringList> rows) {
    beginResetModel();
    rows_ = std::move(rows);
    endResetModel();
}

int GeneratedRows::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : static_cast<int>(rows_.size());
}

QVariant GeneratedRows::data(const QModelIndex& index, int role) const {
    return index.isValid() && role == Qt::UserRole && index.row() < rows_.size() ? QVariant(rows_.at(index.row()))
                                                                                   : QVariant();
}

QHash<int, QByteArray> GeneratedRows::roleNames() const { return {{Qt::UserRole, "values"}}; }

GeneratedCategory::GeneratedCategory(QObject* parent) : QObject(parent) {}

void GeneratedCategory::setSource(BlockText* source) {
    if (source == source_) {
        return;
    }
    if (source_ != nullptr) {
        disconnect(source_, nullptr, this, nullptr);
    }
    source_ = source;
    if (source_ != nullptr) {
        connect(source_, &BlockText::textChanged, this, &GeneratedCategory::read);
    }
    emit sourceChanged();
    read();
}

void GeneratedCategory::setCategoryId(const QString& id) {
    if (id != id_) {
        id_ = id;
        emit categoryIdChanged();
        read();
    }
}

void GeneratedCategory::read() {
    const std::string id = id_.toStdString();
    const edi::TextCategory category =
        source_ != nullptr && !id.empty() ? edi::text_category(source_->text().toStdString(), id) : edi::TextCategory{};
    loop_ = category.loop;
    output_ = edi::category_is_output(id);
    names_.clear();
    labels_.clear();
    units_.clear();
    set_by_program_.clear();
    kinds_.clear();
    for (OptionListModel* options : options_) {
        if (options != nullptr) {
            options->deleteLater();
        }
    }
    options_.clear();
    for (const std::string& name : category.names) {
        const std::string uid = id + "." + name;
        const bool known = edi::has_item(uid);
        names_.append(QString::fromStdString(name));
        labels_.append(QString::fromStdString(known ? edi::label(uid) : name));
        units_.append(QString::fromStdString(known ? edi::units_label(uid) : std::string()));
        // The control the dictionary's type asks for: a selector shows its options, as every designed selector does.
        const std::string dtype = edi::item_dtype(uid);
        OptionListModel* options = nullptr;
        if (dtype == "enum") {
            std::vector<std::string> tokens;
            for (const edi::DisplayOption& option : edi::options(uid)) {
                tokens.push_back(option.token);
            }
            options = new OptionListModel(this);
            options->setItemOptions(uid, tokens);
        }
        options_.append(options);
        kinds_.append(dtype == "enum"                       ? QStringLiteral("choice")
                      : dtype == "bool"                     ? QStringLiteral("flag")
                      : dtype == "float" || dtype == "int" ? QStringLiteral("number")
                                                            : QStringLiteral("text"));
        if (edi::item_is_set_by_program("_" + uid)) {
            set_by_program_.append(QString::fromStdString(name));
        }
    }
    QList<QStringList> rows;
    for (const std::vector<std::string>& row : category.rows) {
        QStringList values;
        for (const std::string& value : row) {
            values.append(QString::fromStdString(value));
        }
        rows.append(values);
    }
    rows_->setRows(std::move(rows));
    emit loopChanged();
    emit outputChanged();
    emit namesChanged();
    emit labelsChanged();
    emit unitsChanged();
    emit setByProgramChanged();
    emit rowCountChanged();
    emit kindsChanged();
}

OptionListModel* GeneratedCategory::optionsAt(int index) const {
    return index >= 0 && index < options_.size() ? options_.at(index) : nullptr;
}

QString GeneratedCategory::editedText(int row, const QString& name, const QString& value) const {
    if (source_ == nullptr || row < 0) {
        return {};
    }
    return QString::fromStdString(edi::with_text_value(source_->text().toStdString(), id_.toStdString(),
                                                       static_cast<std::size_t>(row), name.toStdString(),
                                                       value.toStdString()));
}

}  // namespace edi_app
