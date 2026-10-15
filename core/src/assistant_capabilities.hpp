// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "assistant_json.hpp"
namespace edi::assistant::detail {
std::string_view openai_capabilities_data();
inline J openai_efforts(const std::string& model) {
    static const J policy = [] {
        auto value = parse(std::string(openai_capabilities_data()));
        shape(value, {"schema", "reviewed_on", "models"});
        if (string(value, "schema") != "edi.assistant.openai-capabilities/1") throw std::logic_error("Invalid shipped capability schema");
        std::set<std::string> ids;
        for (const auto& row : value.at("models").array("models")) {
            shape(row, {"id", "efforts", "sources"});
            if (!ids.insert(string(row, "id")).second || row.at("efforts").array("efforts").size() > Limits::model_options)
                throw std::logic_error("Invalid shipped model capabilities");
        }
        return value;
    }();
    for (const auto& row : policy.at("models").array("models")) if (string(row, "id") == model) return row.at("efforts");
    return A{};
}
inline bool effort_tag(const std::string& value) {
    static const std::set<std::string> tags{"none", "minimal", "low", "medium", "high", "xhigh", "max"};
    return tags.count(value) != 0;
}
}
