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
        const auto& id = entry.at("id").string("id"); const auto& version = entry.at("version").string("version");
        if (id.size() > Limits::id_bytes || version.size() > Limits::id_bytes || !ids.insert(id).second)
            refuse("invalid_argument", "Invalid bundled skill identity");
        if (id.empty() || version.empty() || entry.at("title").string("title").empty() || entry.at("summary").string("summary").empty())
            refuse("invalid_argument", "Empty bundled skill metadata");
        if (string(entry, "path") != id + "/SKILL.md") refuse("invalid_argument", "Invalid bundled skill package path");
        const auto& hash = entry.at("sha256").string("sha256");
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
void charge(std::uint64_t& used, std::uint64_t amount, std::uint64_t limit) {
    if (used > limit || amount > limit - used) refuse("resource_exhausted", "Bundled workflow output exceeds context capacity");
    used += amount;
}
std::uint64_t text_size(std::string_view text, std::uint64_t limit) {
    try { return json::encoded_string_size(text, limit); }
    catch (const std::length_error&) { refuse("resource_exhausted", "Bundled workflow text exceeds context capacity"); }
}
void member(std::uint64_t& used, std::string_view key, std::uint64_t value, std::uint64_t limit, bool comma) {
    charge(used, text_size(key, limit) + 1 + (comma ? 1 : 0), limit); charge(used, value, limit);
}
}
J skill_context(std::string_view selected, const J& tools, std::uint64_t limit) {
    const auto index = bundled(tools);
    for (const auto& entry : index.at("skills").array("skills")) if (string(entry, "id") == selected) {
        const auto& resource = content_for(selected);
        std::uint64_t used = 4; // complete one-row array plus object braces
        member(used, "id", payload_size(entry.at("id"), limit), limit, false);
        member(used, "version", payload_size(entry.at("version"), limit), limit, true);
        member(used, "sha256", payload_size(entry.at("sha256"), limit), limit, true);
        member(used, "content", text_size(resource.content, limit), limit, true);
        J row = O{{"id", string(entry, "id")}, {"version", string(entry, "version")},
                  {"sha256", string(entry, "sha256")}, {"content", std::string(resource.content)}};
        return A{std::move(row)};
    }
    refuse("invalid_argument", "Unknown bundled workflow");
}
J skill_catalog(std::string_view selected, bool has_selected_files, const J& tools) {
    auto index = bundled(tools); A rows; std::uint64_t used = 2;
    // The outer object/selected identity and complete array are charged first.
    member(used, "selected_id", text_size(selected, Limits::context_bytes), Limits::context_bytes, false);
    member(used, "skills", 2, Limits::context_bytes, true);
    bool found = false;
    for (const auto& entry : index.at("skills").array("skills")) {
        const auto id = string(entry, "id");
        found = found || id == selected;
        bool available = true;
        for (const auto& prerequisite : entry.at("requires").array("requires"))
            if (prerequisite.string("requires") == "selected_files" && !has_selected_files) available = false;
        const auto& content = content_for(id).content;
        const std::string_view blocked = available ? "" : "Select the relevant files before this workflow can inspect them.";
        auto row_size = payload_size(entry, Limits::context_bytes);
        member(row_size, "content", text_size(content, Limits::context_bytes), Limits::context_bytes, true);
        member(row_size, "available", available ? 4 : 5, Limits::context_bytes, true);
        member(row_size, "blocked_reason", text_size(blocked, Limits::context_bytes), Limits::context_bytes, true);
        charge(used, row_size + (rows.empty() ? 0 : 1), Limits::context_bytes);
        J row = entry;
        set(row, "content", std::string(content));
        set(row, "available", available);
        set(row, "blocked_reason", available ? "" : "Select the relevant files before this workflow can inspect them.");
        rows.push_back(std::move(row));
    }
    if (!found) refuse("invalid_argument", "Unknown bundled workflow");
    J result = O{{"selected_id", std::string(selected)}, {"skills", std::move(rows)}};
    bounded(result, Limits::context_bytes); return result;
}
}
