// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_skills.hpp"

namespace edi::assistant::detail {
namespace {
J bundled(const J& tools) {
    std::set<std::string> declared_tools;
    for (const auto& tool : tools.array("tools")) declared_tools.insert(string(tool, "name"));
    const auto bytes = skill_index_data();
    if (bytes.size() > Limits::context_bytes) refuse("resource_exhausted", "Bundled skill index exceeds context capacity");
    auto index = parse(std::string(bytes), Limits::context_bytes);
    shape(index, {"schema", "skills"});
    if (string(index, "schema") != "edi.assistant.skills/1") refuse("invalid_argument", "Unsupported bundled skill schema");
    const auto& entries = index.at("skills").array("skills");
    const auto resources = skill_resource_data();
    if (entries.empty() || entries.size() != resources.size() || entries.size() > Limits::models)
        refuse("resource_exhausted", "Bundled skill catalog capacity or content mismatch");
    std::set<std::string> ids;
    for (const auto& entry : entries) {
        shape(entry, {"id", "version", "title", "summary", "path", "sha256", "requires", "capabilities", "references"});
        const auto id = string(entry, "id"), version = string(entry, "version");
        if (id.size() > Limits::id_bytes || version.size() > Limits::id_bytes || !ids.insert(id).second)
            refuse("invalid_argument", "Invalid bundled skill identity");
        (void)string(entry, "title"); (void)string(entry, "summary");
        if (string(entry, "path") != id + "/SKILL.md") refuse("invalid_argument", "Invalid bundled skill package path");
        const auto hash = string(entry, "sha256");
        const auto resource = std::find_if(resources.begin(), resources.end(), [&](const auto& r) { return r.id == id; });
        if (resource == resources.end() || resource->sha256 != hash || resource->content.empty())
            refuse("invalid_argument", "Bundled skill content/hash mismatch");
        if (resource->content.size() > Limits::context_bytes)
            refuse("resource_exhausted", "Bundled skill content exceeds context capacity");
        for (const auto& required : entry.at("requires").array("requires")) {
            const auto& value = required.string("requires");
            if (value != "selected_files") refuse("invalid_argument", "Unknown bundled skill prerequisite");
        }
        for (const auto& capability : entry.at("capabilities").array("capabilities")) {
            const auto& value = capability.string("capabilities");
            if (value.empty() || value.size() > Limits::id_bytes || !declared_tools.contains(value)) refuse("invalid_argument", "Invalid bundled skill capability");
        }
        for (const auto& reference : entry.at("references").array("references")) {
            shape(reference, {"title", "url"}); (void)string(reference, "title");
            if (!string(reference, "url").starts_with("https://")) refuse("invalid_argument", "Invalid bundled skill reference");
        }
    }
    return index;
}
const SkillResource& content_for(std::string_view id) {
    const auto resources = skill_resource_data();
    const auto found = std::find_if(resources.begin(), resources.end(), [&](const auto& r) { return r.id == id; });
    if (found == resources.end()) refuse("invalid_argument", "Unknown bundled workflow");
    return *found;
}
void append_bounded(A& rows, J row, std::uint64_t& used) {
    const auto added = payload_size(row, Limits::context_bytes) + (rows.empty() ? 0 : 1);
    if (added > Limits::context_bytes - used) refuse("resource_exhausted", "Bundled workflow catalog exceeds context capacity");
    used += added; rows.push_back(std::move(row));
}
}
J skill_context(std::string_view selected, const J& tools) {
    const auto index = bundled(tools);
    for (const auto& entry : index.at("skills").array("skills")) if (string(entry, "id") == selected) {
        const auto& resource = content_for(selected);
        J row = O{{"id", string(entry, "id")}, {"version", string(entry, "version")},
                  {"sha256", string(entry, "sha256")}, {"content", std::string(resource.content)}};
        bounded(row, Limits::context_bytes);
        return A{std::move(row)};
    }
    refuse("invalid_argument", "Unknown bundled workflow");
}
J skill_catalog(std::string_view selected, bool has_selected_files, const J& tools) {
    auto index = bundled(tools); A rows; std::uint64_t used = 2;
    bool found = false;
    for (const auto& entry : index.at("skills").array("skills")) {
        const auto id = string(entry, "id");
        found = found || id == selected;
        bool available = true;
        for (const auto& prerequisite : entry.at("requires").array("requires"))
            if (prerequisite.string("requires") == "selected_files" && !has_selected_files) available = false;
        J row = entry;
        set(row, "content", std::string(content_for(id).content));
        set(row, "available", available);
        set(row, "blocked_reason", available ? "" : "Select the relevant files before this workflow can inspect them.");
        append_bounded(rows, std::move(row), used);
    }
    if (!found) refuse("invalid_argument", "Unknown bundled workflow");
    J result = O{{"selected_id", std::string(selected)}, {"skills", std::move(rows)}};
    bounded(result, Limits::context_bytes); return result;
}
}
