// SPDX-License-Identifier: BSD-3-Clause
#include "generated_category.hpp"

#include <algorithm>
#include <set>
#include <string>
#include <vector>

#include <QScopeGuard>

#include "crysta/dictionary_items.hpp"
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

// The items whose value is a parameter's unique name (`tb2ti2o7.atom_site.O1.fract_x`). The dictionary types them as
// strings, so they are declared here, the one list every generated table reads.
bool names_parameter(const std::string& uid) {
    static const std::set<std::string> items = {"alias.parameter_unique_name",
                                                "fit_parameter_correlation.parameter_unique_name_i",
                                                "fit_parameter_correlation.parameter_unique_name_j"};
    return items.contains(uid);
}

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
    remember("descriptions", QVariant::fromValue(descriptions_));
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
        publish("descriptions", QVariant::fromValue(receiver->descriptions_), &GeneratedCategory::descriptionsChanged);
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
    edi::TextCategory category =
        source_ != nullptr && !id.empty() ? edi::text_category(source_->text().toStdString(), id) : edi::TextCategory{};
    // The atoms in the cell number shared positions in `cluster_id`; with no position shared it only repeats the row
    // number, so the column shows only when some position is shared.
    if (id == "expanded_atom_site") {
        const auto at = std::find(category.names.begin(), category.names.end(), "cluster_id");
        if (at != category.names.end()) {
            const auto column = static_cast<std::size_t>(at - category.names.begin());
            std::set<std::string> seen;
            bool shared = false;
            for (const std::vector<std::string>& row : category.rows) {
                shared = shared || (column < row.size() && !seen.insert(row[column]).second);
            }
            if (!shared) {
                category.names.erase(at);
                for (std::vector<std::string>& row : category.rows) {
                    if (column < row.size()) {
                        row.erase(row.begin() + static_cast<std::ptrdiff_t>(column));
                    }
                }
            }
        }
    }
    publication = ++notification_publication_;
    if (publication == 0) publication = ++notification_publication_;
    loop_ = category.loop;
    // The magnetic operators and centrings follow the magnetic space group, so they are shown read-only, as the
    // symmetry operators are (edi ADR-0078; the owner, 2026-11-03).
    output_ = edi::category_is_output(id) || id == "space_group_symop_magn_operation" ||
              id == "space_group_symop_magn_centering";
    names_.clear();
    labels_.clear();
    units_.clear();
    descriptions_.clear();
    set_by_program_.clear();
    kinds_.clear();
    options_.clear();
    for (const std::string& name : category.names) {
        // A file spells some names as CIF does (`name_H-M_alt`, `IT_number`), so the item is found by its `.edi` name,
        // compared as CIF compares names, and the dictionary's uid is used from there; the name is kept as written.
        const crysta::DictionaryItem* item = crysta::find_dictionary_item_by_edi_name("_" + id + "." + name);
        const std::string uid = item != nullptr ? item->uid : id + "." + name;
        const bool known = edi::has_item(uid);
        names_.append(QString::fromStdString(name));
        labels_.append(QString::fromStdString(known ? edi::label(uid) : name));
        units_.append(QString::fromStdString(known ? edi::units_label(uid) : std::string()));
        descriptions_.append(QString::fromStdString(known ? edi::description(uid) : std::string()));
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
        // A calculated cell holding a parameter's unique name is named as the Analysis table names the parameter.
        kinds_.append(output_ && names_parameter(uid)      ? QStringLiteral("parameter")
                      : dtype == "enum"                    ? QStringLiteral("choice")
                      : dtype == "bool"                    ? QStringLiteral("flag")
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
