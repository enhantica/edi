// SPDX-License-Identifier: BSD-3-Clause
#include "generated_category.hpp"

#include <string>
#include <QScopeGuard>

#include "edi/display.hpp"

namespace edi_app {

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
    const QPointer<GeneratedCategory> receiver(this);
    if (!property_notifications_.contains("loop")) property_notifications_["loop"] = QVariant::fromValue(loop_);
    if (!property_notifications_.contains("output")) property_notifications_["output"] = QVariant::fromValue(output_);
    if (!property_notifications_.contains("names")) property_notifications_["names"] = QVariant::fromValue(names_);
    if (!property_notifications_.contains("labels")) property_notifications_["labels"] = QVariant::fromValue(labels_);
    if (!property_notifications_.contains("units")) property_notifications_["units"] = QVariant::fromValue(units_);
    if (!property_notifications_.contains("setByProgram")) property_notifications_["setByProgram"] = QVariant::fromValue(set_by_program_);
    if (!property_notifications_.contains("rows")) property_notifications_["rows"] = QVariant::fromValue(rows_);
    quint64 publication = 0;
    const auto propertyNotifications = qScopeGuard([receiver, &publication] {
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant loop = QVariant::fromValue(receiver->loop_);
        if (receiver->property_notifications_.value("loop") != loop) {
            receiver->property_notifications_["loop"] = loop;
            emit receiver->loopChanged();
        }
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant output = QVariant::fromValue(receiver->output_);
        if (receiver->property_notifications_.value("output") != output) {
            receiver->property_notifications_["output"] = output;
            emit receiver->outputChanged();
        }
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant names = QVariant::fromValue(receiver->names_);
        if (receiver->property_notifications_.value("names") != names) {
            receiver->property_notifications_["names"] = names;
            emit receiver->namesChanged();
        }
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant labels = QVariant::fromValue(receiver->labels_);
        if (receiver->property_notifications_.value("labels") != labels) {
            receiver->property_notifications_["labels"] = labels;
            emit receiver->labelsChanged();
        }
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant units = QVariant::fromValue(receiver->units_);
        if (receiver->property_notifications_.value("units") != units) {
            receiver->property_notifications_["units"] = units;
            emit receiver->unitsChanged();
        }
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant setByProgram = QVariant::fromValue(receiver->set_by_program_);
        if (receiver->property_notifications_.value("setByProgram") != setByProgram) {
            receiver->property_notifications_["setByProgram"] = setByProgram;
            emit receiver->setByProgramChanged();
        }
        if (!receiver || publication == 0 || receiver->notification_publication_ != publication) return;
        const QVariant rows = QVariant::fromValue(receiver->rows_);
        if (receiver->property_notifications_.value("rows") != rows) {
            receiver->property_notifications_["rows"] = rows;
            emit receiver->rowsChanged();
        }
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
    for (const std::string& name : category.names) {
        const std::string uid = id + "." + name;
        const bool known = edi::has_item(uid);
        names_.append(QString::fromStdString(name));
        labels_.append(QString::fromStdString(known ? edi::label(uid) : name));
        units_.append(QString::fromStdString(known ? edi::units_label(uid) : std::string()));
        if (edi::item_is_set_by_program("_" + uid)) {
            set_by_program_.append(QString::fromStdString(name));
        }
    }
    rows_.clear();
    for (const std::vector<std::string>& row : category.rows) {
        QStringList values;
        for (const std::string& value : row) {
            values.append(QString::fromStdString(value));
        }
        rows_.append(QVariant(values));
    }
    emit changed();
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
