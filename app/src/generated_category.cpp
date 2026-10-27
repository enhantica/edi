// SPDX-License-Identifier: BSD-3-Clause
#include "generated_category.hpp"

#include <string>

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
    const std::string id = id_.toStdString();
    const edi::TextCategory category =
        source_ != nullptr && !id.empty() ? edi::text_category(source_->text().toStdString(), id) : edi::TextCategory{};
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
