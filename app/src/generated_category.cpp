// SPDX-License-Identifier: BSD-3-Clause
#include "generated_category.hpp"

#include <string>
#include <vector>

#include <QScopeGuard>

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

namespace {

QVariantList option_identities(const QList<OptionListModel*>& options) {
    QVariantList identities;
    for (OptionListModel* options_model : options) {
        identities.append(QVariant::fromValue(static_cast<QObject*>(options_model)));
    }
    return identities;
}

}  // namespace

QList<GeneratedCell> GeneratedCategory::cells() const {
    QList<GeneratedCell> cells;
    for (qsizetype column = 0; column < names_.size(); ++column) {
        cells.append({names_.at(column), static_cast<int>(column), kinds_.value(column, QStringLiteral("text"))});
    }
    return cells;
}

void GeneratedCategory::read() {
    const QPointer<GeneratedCategory> receiver(this);
    // A value is signalled against the one last signalled, once the read is complete and only by the latest read, so
    // a read started from a notification never has an older one signal after it. What did not change is not
    // signalled; the values always are (rowCount).
    const auto remember = [this](const char* name, const QVariant& value) {
        if (!property_notifications_.contains(name)) property_notifications_[name] = value;
    };
    remember("loop", QVariant::fromValue(loop_));
    remember("output", QVariant::fromValue(output_));
    remember("names", QVariant::fromValue(names_));
    remember("labels", QVariant::fromValue(labels_));
    remember("units", QVariant::fromValue(units_));
    remember("setByProgram", QVariant::fromValue(set_by_program_));
    remember("kinds", QVariant::fromValue(kinds_));
    remember("options", option_identities(options_));
    remember("cells", QVariant::fromValue(cells()));
    quint64 publication = 0;
    const auto propertyNotifications = qScopeGuard([receiver, &publication] {
        const auto current = [&] {
            return receiver && publication != 0 && receiver->notification_publication_ == publication;
        };
        const auto publish = [&](const char* name, const QVariant& value, void (GeneratedCategory::*signal)()) {
            if (!current() || receiver->property_notifications_.value(name) == value) return;
            receiver->property_notifications_[name] = value;
            emit(receiver.data()->*signal)();
        };
        if (!current()) return;
        publish("loop", QVariant::fromValue(receiver->loop_), &GeneratedCategory::loopChanged);
        if (!current()) return;
        publish("output", QVariant::fromValue(receiver->output_), &GeneratedCategory::outputChanged);
        if (!current()) return;
        publish("names", QVariant::fromValue(receiver->names_), &GeneratedCategory::namesChanged);
        if (!current()) return;
        publish("labels", QVariant::fromValue(receiver->labels_), &GeneratedCategory::labelsChanged);
        if (!current()) return;
        publish("units", QVariant::fromValue(receiver->units_), &GeneratedCategory::unitsChanged);
        if (!current()) return;
        publish("setByProgram", QVariant::fromValue(receiver->set_by_program_),
                &GeneratedCategory::setByProgramChanged);
        if (!current()) return;
        // A field reads its value through value(), which this signal has it read again.
        emit receiver->rowCountChanged();
        if (!current()) return;
        publish("kinds", QVariant::fromValue(receiver->kinds_), &GeneratedCategory::kindsChanged);
        if (!current()) return;
        publish("options", option_identities(receiver->options_), &GeneratedCategory::optionsChanged);
        if (!current()) return;
        publish("cells", QVariant::fromValue(receiver->cells()), &GeneratedCategory::cellsChanged);
    });
    const std::string id = id_.toStdString();
    const edi::TextCategory category =
        source_ != nullptr && !id.empty() ? edi::text_category(source_->text().toStdString(), id) : edi::TextCategory{};
    publication = ++notification_publication_;
    if (publication == 0) publication = ++notification_publication_;
    loop_ = category.loop;
    output_ = edi::category_is_output(id);
    names_.clear();
    labels_.clear();
    units_.clear();
    set_by_program_.clear();
    kinds_.clear();
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
