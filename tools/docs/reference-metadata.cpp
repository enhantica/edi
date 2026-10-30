// SPDX-License-Identifier: BSD-3-Clause
// Read the linked SDK dictionary; do not maintain a second parameter vocabulary for docs.
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <iostream>
#include "crysta/dictionary_items.hpp"

namespace {
QString text(const std::string& value) { return QString::fromStdString(value); }
QJsonArray strings(const std::vector<std::string>& values) {
    QJsonArray result;
    for (const auto& value : values) result.append(text(value));
    return result;
}
}
int main() {
    try {
        QJsonArray categories, items;
        for (const auto& category : crysta::dictionary_categories()) {
            categories.append(QJsonObject{{"id", text(category.id)}, {"edi_name", text(category.edi_name)},
                {"title", text(category.title)}, {"icon", text(category.icon)},
                {"description", text(category.description)}, {"loop", category.loop},
                {"output", category.output}, {"order", category.order}});
        }
        for (const auto& item : crysta::dictionary_items()) {
            QJsonArray options, variants;
            for (const auto& option : item.options)
                options.append(QJsonObject{{"token", text(option.token)}, {"label", text(option.display_name)},
                    {"description", text(option.description)}});
            for (const auto& variant : item.variants)
                variants.append(QJsonObject{{"by", text(variant.by)}, {"token", text(variant.token)},
                    {"label", text(variant.display_name)}, {"units", text(variant.display_units)},
                    {"cif_names", strings(variant.cif_names)}});
            items.append(QJsonObject{{"uid", text(item.uid)}, {"category", text(item.category)},
                {"name", text(item.name)}, {"edi_tag", text(item.edi_tag)},
                {"edi_aliases", strings(item.edi_aliases)}, {"cif_names", strings(item.cif_names)},
                {"label", text(item.display_name)}, {"units", text(item.display_units)},
                {"description", text(item.description)}, {"parameter", item.parameter},
                {"dtype", text(item.dtype)}, {"options", options}, {"variants", variants}});
        }
        std::cout << QJsonDocument(QJsonObject{{"schema", 1}, {"categories", categories}, {"items", items}})
                         .toJson(QJsonDocument::Indented).constData();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
