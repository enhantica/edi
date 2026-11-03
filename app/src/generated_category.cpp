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
    // What did not change is not signalled, so the controls showing it stay as they are; the values always are.
    const bool loop = loop_;
    const bool output = output_;
    const QStringList names = names_, labels = labels_, units = units_, set_by_program = set_by_program_, kinds = kinds_;
    loop_ = category.loop;
    // The magnetic operators and centrings follow the magnetic space group, so they are shown read-only, as the
    // symmetry operators are (edi ADR-0068; the owner, 2026-11-03).
    output_ = edi::category_is_output(id) || id == "space_group_symop_magn_operation" ||
              id == "space_group_symop_magn_centering";
    names_.clear();
    labels_.clear();
    units_.clear();
    set_by_program_.clear();
    kinds_.clear();
    const QList<OptionListModel*> shown = options_;
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
            OptionListModel*& held = options_by_uid_[QString::fromStdString(uid)];
            if (held == nullptr) {
                std::vector<std::string> tokens;
                for (const edi::DisplayOption& option : edi::options(uid)) {
                    tokens.push_back(option.token);
                }
                held = new OptionListModel(this);
                held->setItemOptions(uid, tokens);
            }
            options = held;
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
    if (loop_ != loop) {
        emit loopChanged();
    }
    if (output_ != output) {
        emit outputChanged();
    }
    if (names_ != names) {
        emit namesChanged();
    }
    if (labels_ != labels) {
        emit labelsChanged();
    }
    if (units_ != units) {
        emit unitsChanged();
    }
    if (set_by_program_ != set_by_program) {
        emit setByProgramChanged();
    }
    emit rowCountChanged();  // a field reads its value through value(), which this signal has it read again
    if (kinds_ != kinds) {
        emit kindsChanged();
    }
    if (options_ != shown) {
        emit optionsChanged();
    }
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
