// SPDX-License-Identifier: BSD-3-Clause
#include "edi/assistant.hpp"

#include <map>
#include <set>
#include <utility>
#include "assistant_json.hpp"

namespace edi::assistant {
using namespace detail;
struct OpenAiStream::State {
    std::string turn, request, pending, record, failure_code;
    Sink sink;
    const char* diagnostic_stage = "SSE framing";
    std::string diagnostic(const std::string& reason) const {
        // The only dynamic member named by current Refusal messages is a JSON
        // duplicate key. Do not copy an arbitrary provider-supplied member name.
        const auto safe = reason.starts_with("Duplicate JSON member:") ? std::string("Duplicate JSON member in streamed response") : reason;
        return std::string(diagnostic_stage) + ": " + safe;
    }
    std::string exception_diagnostic(const std::exception& error) const {
        // Accessor errors use app-owned field names. Preserve only exact known
        // forms; an arbitrary exception message may contain tool/user content.
        const std::string_view supplied(error.what());
        for (const char* field : {"id", "type", "item_id", "output_index", "content_index", "part", "text", "refusal", "call_id", "name", "arguments", "response", "status", "content", "namespace", "output", "object", "plan_id"}) {
            const auto missing = std::string("report JSON: no member '") + field + "'";
            if (supplied == missing) return diagnostic(missing);
            for (const char* expected : {"a boolean", "a number", "a string", "an array", "an object"}) {
                const auto typed = std::string("report JSON: ") + field + " is not " + expected;
                if (supplied == typed) return diagnostic(typed);
            }
        }
        return diagnostic("Stream decoder operation failed");
    }
    bool terminal = false, failed = false, refused = false;
    std::uint64_t wire = 0, events = 0, retained_base = 0;
    // Provider item/part identities belong only to this decoder. The normalized
    // controller text envelope remains unchanged (Responses streaming-events).
    struct Part {
        std::string kind, text;
        bool text_done = false, part_done = false, deltas = false;
        J complete, declaration;
        bool started = false;
    };
    struct Item {
        J original;
        bool done = false;
        std::uint64_t index = 0;
        std::map<std::uint64_t, Part> parts;
    };
    struct Call { std::string id, name, arguments; bool emitted = false, deltas = false; };
    std::map<std::string, Item> items;
    std::map<std::string, Call> calls;
    std::map<std::uint64_t, std::string> positions;

    void emit(O fields) {
        fields.emplace_back("schema", "edi.assistant/1"); fields.emplace_back("turn_id", turn); fields.emplace_back("request_id", request);
        bounded(fields, Limits::message_bytes);
        if (sink) sink(json::write(fields));
    }
    std::string identifier(const J& item, const char* key) const {
        const auto value = string(item, key);
        if (value.size() > Limits::id_bytes) refuse("resource_exhausted", "Provider identity exceeds limit");
        return value;
    }
    void retained() {
        std::uint64_t size = 0;
        for (const auto& [id, item] : items) {
            size += id.size() + payload_size(item.original, Limits::stream_retained_bytes);
            for (const auto& [index, part] : item.parts) {
                (void)index;
                size += payload_size(O{{"content_index", std::to_string(index)}, {"type", part.kind}, {"text", part.text},
                                       {"text_done", part.text_done}, {"part_done", part.part_done}, {"complete", part.complete}, {"declaration", part.declaration}}, Limits::stream_retained_bytes);
            }
            if (size > Limits::stream_retained_bytes) refuse("resource_exhausted", "Provider retained-item limit exceeded");
        }
        for (const auto& [id, call] : calls) {
            size += id.size() + call.id.size() + call.name.size() + call.arguments.size();
            if (size > Limits::stream_retained_bytes) refuse("resource_exhausted", "Provider retained-call limit exceeded");
        }
        retained_base = size;
        partial();
    }
    void partial() const {
        if (pending.size() + record.size() + retained_base > Limits::stream_retained_bytes)
            refuse("resource_exhausted", "Provider retained state exceeds limit");
    }
    void tool(Call& call, const std::string& arguments) {
        const auto args = parse(arguments); args.object("arguments");
        if (call.emitted) {
            if (json::write(canonical(parse(call.arguments))) != json::write(canonical(args))) refuse("invalid_argument", "Conflicting completed tool arguments");
            return;
        }
        if (call.deltas && json::write(canonical(parse(call.arguments))) != json::write(canonical(args)))
            refuse("invalid_argument", "Completed tool arguments contradict their deltas");
        if (call.id.empty() || call.name.empty()) refuse("invalid_argument", "Incomplete tool identity");
        O domain, event{{"type", "tool_call"}, {"call_id", call.id}, {"name", call.name}};
        for (const auto& [key, value] : args.object("arguments")) {
            if (key == "plan_id") event.emplace_back(key, value); else domain.emplace_back(key, value);
        }
        event.emplace_back("arguments", std::move(domain));
        call.arguments = arguments; call.emitted = true; retained(); emit(std::move(event));
    }
    std::uint64_t index(const J& event, const char* key) const {
        const auto value = number(event, key);
        if (value < 0 || value > 9007199254740991.0 || std::floor(value) != value)
            refuse("invalid_argument", "Provider content index must be a nonnegative safe integer");
        return static_cast<std::uint64_t>(value);
    }
    Item& content_owner(const J& event, const std::string& kind) {
        const auto id = identifier(event, "item_id");
        const auto found = items.find(id);
        if (found == items.end() || found->second.done)
            refuse("invalid_argument", "Content names an unavailable or completed item");
        const auto owner = string(found->second.original, "type");
        if ((kind == "reasoning_text" && owner != "reasoning") ||
            (kind != "reasoning_text" && owner != "message"))
            refuse("invalid_argument", "Content names an incompatible item");
        if (index(event, "output_index") != found->second.index)
            refuse("invalid_argument", "Provider output index changed");
        return found->second;
    }
    Part& declare_content(Item& owner, std::uint64_t slot, const std::string& kind) {
        if (kind != "output_text" && kind != "refusal" && kind != "reasoning_text")
            refuse("invalid_argument", "Unsupported public content kind");
        auto found = owner.parts.find(slot);
        if (found == owner.parts.end()) {
            if (slot != owner.parts.size()) refuse("invalid_argument", "Provider content index is unavailable");
            found = owner.parts.emplace(slot, Part{kind}).first;
        }
        if (found->second.kind != kind) refuse("invalid_argument", "Provider content kind changed");
        return found->second;
    }
    Part& started_content(Item& owner, std::uint64_t slot, const std::string& kind) {
        const auto found = owner.parts.find(slot);
        if (found == owner.parts.end() || !found->second.started || found->second.kind != kind)
            refuse("invalid_argument", "Provider content part has not started with this identity/kind");
        return found->second;
    }
    void completed_text(Part& part, const std::string& text) {
        if ((part.text_done || part.deltas) && part.text != text)
            refuse("invalid_argument", "Final provider content contradicts its public text");
        const bool publish = !part.text_done && !part.deltas;
        const auto before = payload_size(J(part.text)), after = payload_size(J(text));
        if (after > before && after - before > Limits::stream_retained_bytes - retained_base)
            refuse("resource_exhausted", "Provider retained text exceeds limit");
        part.text = text; part.text_done = true;
        if (part.kind == "refusal") refused = true;
        retained();
        if (publish && part.kind != "reasoning_text" && !text.empty()) emit({{"type", "text_delta"}, {"text", text}});
    }
    void completed_part(Part& part, const J& original) {
        if (part.part_done) {
            if (json::write(canonical(part.complete)) != json::write(canonical(original)))
                refuse("invalid_argument", "Completed provider part changed");
            return;
        }
        const auto key = part.kind == "refusal" ? "refusal" : "text";
        completed_text(part, string(original, key, true));
        part.complete = original; part.part_done = true; retained();
    }
    void item(const J& original, bool done, std::uint64_t output_index) {
        const auto id = identifier(original, "id"); const auto type = string(original, "type");
        const auto prior = items.find(id);
        if (prior == items.end()) {
            if (items.size() >= Limits::stream_items) refuse("resource_exhausted", "Provider item count exceeds limit");
            const auto position = positions.find(output_index);
            if (position != positions.end() && position->second != id)
                refuse("invalid_argument", "Provider output position already belongs to another item");
            const auto added = items.emplace(id, Item{original, false, output_index, {}}).first;
            try { positions.emplace(output_index, id); }
            catch (...) { items.erase(added); throw; }
        } else if (string(prior->second.original, "type") != type) refuse("invalid_argument", "Provider item type changed");
        auto& held = items.at(id);
        if (held.index != output_index) refuse("invalid_argument", "Provider output index changed");
        if (held.done) {
            if (!done || json::write(canonical(held.original)) != json::write(canonical(original))) refuse("invalid_argument", "Completed provider item changed");
            return;
        }
        if (type == "function_call") {
            const auto call_id = identifier(original, "call_id"), name = identifier(original, "name");
            if (has(original, "namespace") && string(original, "namespace") != "edi") refuse("invalid_argument", "Unknown provider tool namespace");
            auto found = calls.find(id);
            if (found == calls.end()) {
                if (calls.size() >= Limits::stream_calls) refuse("resource_exhausted", "Provider call count exceeds limit");
                for (const auto& entry : calls) if (entry.second.id == call_id) refuse("invalid_argument", "Provider call ID reused by another item");
                calls.emplace(id, Call{call_id, name, {}});
            } else if (found->second.id != call_id || found->second.name != name) refuse("invalid_argument", "Provider tool identity changed");
            if (done) tool(calls.at(id), string(original, "arguments", true));
        }
        // Live content identities start only through content_part.added.
        // A complete item snapshot may introduce completed parts without deltas.
        if (done && (type == "message" || (type == "reasoning" && has(original, "content")))) {
            std::uint64_t slot = 0;
            for (const auto& original_part : original.at("content").array("content")) {
                const auto kind = string(original_part, "type");
                if ((type == "reasoning" && kind != "reasoning_text") || (type == "message" && kind == "reasoning_text"))
                    refuse("invalid_argument", "Completed content has an incompatible owner");
                auto& part = declare_content(held, slot++, kind);
                completed_part(part, original_part);
            }
            if (slot != held.parts.size()) refuse("invalid_argument", "Completed provider item lost content parts");
        }
        held.original = original; held.done = done; retained();
    }
    void reconcile(const J& response, bool required) {
        if (!has(response, "output")) {
            if (required) refuse("invalid_argument", "Completed response has no output array");
            return;
        }
        const auto& output = response.at("output").array("output");
        if (output.size() > Limits::stream_items) refuse("resource_exhausted", "Terminal provider item count exceeds limit");
        std::set<std::string> membership;
        for (std::uint64_t slot = 0; const auto& original : output) {
            const auto id = identifier(original, "id");
            if (!membership.insert(id).second) refuse("invalid_argument", "Terminal provider item ID is repeated");
            const auto prior = items.find(id);
            if (prior != items.end() && prior->second.index != slot)
                refuse("invalid_argument", "Terminal provider item changed output position");
            const auto position = positions.find(slot++);
            if (position != positions.end() && position->second != id)
                refuse("invalid_argument", "Terminal provider output replaced an existing item");
        }
        std::uint64_t omitted = 0, unfinished = 0;
        const char* first_kind = "other";
        const char* first_status = "absent_or_null";
        bool first_done = false;
        for (const auto& [id, held] : items) {
            if (membership.contains(id)) continue;
            if (!held.done) ++unfinished;
            if (++omitted != 1) continue;
            // Structural diagnostics only. Never print an ID, arbitrary type or
            // status string, public text, arguments or encrypted/reasoning data.
            const auto* kind = std::get_if<std::string>(&held.original.get("type").data);
            for (const char* known : {"message", "function_call", "reasoning"})
                if (kind && *kind == known) { first_kind = known; break; }
            const auto& value = held.original.get("status");
            if (const auto* status = std::get_if<std::string>(&value.data)) {
                first_status = "other";
                for (const char* known : {"completed", "incomplete", "in_progress"})
                    if (*status == known) { first_status = known; break; }
            } else if (!std::holds_alternative<std::nullptr_t>(value.data)) first_status = "other";
            first_done = held.done;
        }
        if (omitted) refuse("invalid_argument", "Terminal provider output omitted a retained item (missing=" + std::to_string(omitted) +
            ", retained=" + std::to_string(items.size()) + ", terminal=" + std::to_string(output.size()) +
            ", unfinished=" + std::to_string(unfinished) + ", first_kind=" + first_kind + ", first_status=" + first_status +
            ", wire_done=" + (first_done ? "yes" : "no") + ")");
        for (std::uint64_t slot = 0; const auto& original : output) item(original, true, slot++);
    }
    void event() {
        if (record.empty()) return;
        auto body = std::exchange(record, {}); if (body.back() == '\n') body.pop_back();
        if (body.empty()) return;
        if (++events > Limits::stream_events) refuse("resource_exhausted", "Provider event count exceeds limit");
        if (body == "[DONE]") { if (!terminal) refuse("interrupted", "Stream ended without terminal response"); return; }
        if (terminal) refuse("invalid_argument", "Data after terminal response");
        diagnostic_stage = "event JSON";
        const auto message = parse(body);
        diagnostic_stage = "event type";
        const auto type = string(message, "type");
        diagnostic_stage = "unrecognized event";
        // Diagnostics only: these existing decoder branches remain unchanged.
        // Unknown event names, content, tool arguments and reasoning are never copied.
        for (const char* known : {"response.output_text.delta", "response.refusal.delta", "response.output_text.done", "response.refusal.done",
             "response.reasoning_text.delta", "response.reasoning_text.done", "response.content_part.added", "response.content_part.done",
             "response.output_item.added", "response.output_item.done", "response.function_call_arguments.delta", "response.function_call_arguments.done",
             "response.completed", "response.failed", "response.incomplete", "error"})
            if (type == known) { diagnostic_stage = known; break; }
        if (type == "response.output_text.delta" || type == "response.refusal.delta" ||
            type == "response.output_text.done" || type == "response.refusal.done" ||
            type == "response.reasoning_text.delta" || type == "response.reasoning_text.done") {
            const std::string kind = type.starts_with("response.refusal.") ? "refusal" :
                (type.starts_with("response.reasoning_text.") ? "reasoning_text" : "output_text");
            auto& owner = content_owner(message, kind);
            auto& part = started_content(owner, index(message, "content_index"), kind);
            if (type.ends_with(".done")) {
                completed_text(part, string(message, part.kind == "refusal" ? "refusal" : "text", true));
            } else {
                if (part.text_done || part.part_done) refuse("invalid_argument", "Text arrived after content completion");
                const auto delta = string(message, "delta", true);
                if (payload_size(J(delta)) - 2 > Limits::stream_retained_bytes - retained_base)
                    refuse("resource_exhausted", "Provider retained text exceeds limit");
                part.text += delta; part.deltas = true; retained();
                if (part.kind == "refusal") refused = true;
                if (part.kind != "reasoning_text") emit({{"type", "text_delta"}, {"text", delta}});
            }
        } else if (type == "response.content_part.added" || type == "response.content_part.done") {
            const auto& original = message.at("part");
            const auto kind = string(original, "type");
            auto& owner = content_owner(message, kind);
            const auto slot = index(message, "content_index");
            if (type.ends_with(".done")) {
                auto& part = started_content(owner, slot, kind);
                completed_part(part, original);
            } else {
                if (const auto found = owner.parts.find(slot); found != owner.parts.end()) {
                    if (!found->second.started || json::write(canonical(found->second.declaration)) != json::write(canonical(original)))
                        refuse("invalid_argument", "Provider content declaration changed");
                    return; // Matching declaration duplicates cannot republish text.
                }
                auto& part = declare_content(owner, slot, kind);
                part.declaration = original; part.started = true;
                part.text = string(original, kind == "refusal" ? "refusal" : "text", true);
                retained();
                if (!part.text.empty()) {
                    part.deltas = true;
                    if (kind == "refusal") refused = true;
                    if (kind != "reasoning_text") emit({{"type", "text_delta"}, {"text", part.text}});
                }
            }
        } else if (type == "response.output_item.added" || type == "response.output_item.done") {
            item(message.at("item"), type == "response.output_item.done", index(message, "output_index"));
        } else if (type == "response.function_call_arguments.delta" || type == "response.function_call_arguments.done") {
            const auto id = identifier(message, "item_id"); const auto found = calls.find(id);
            if (found == calls.end()) refuse("invalid_argument", "Arguments for an unknown tool item");
            if (index(message, "output_index") != items.at(id).index)
                refuse("invalid_argument", "Tool argument event changed output position");
            auto& call = found->second;
            if ((has(message, "call_id") && identifier(message, "call_id") != call.id) || (has(message, "name") && identifier(message, "name") != call.name))
                refuse("invalid_argument", "Tool argument identity changed");
            if (type.ends_with(".delta")) {
                if (call.emitted) refuse("invalid_argument", "Arguments changed after completion");
                const auto delta = string(message, "delta", true);
                if (delta.size() > Limits::message_bytes - call.arguments.size()) refuse("invalid_json", "Tool arguments exceed message limit");
                call.arguments += delta; call.deltas = true; retained();
            } else tool(call, string(message, "arguments", true));
        } else if (type == "response.completed" || type == "response.failed" || type == "response.incomplete" || type == "error") {
            std::string status = "failed";
            if (has(message, "response")) reconcile(message.at("response"), type == "response.completed");
            else if (type == "response.completed") refuse("invalid_argument", "Completed event has no response");
            if (type == "response.completed") {
                if (string(message.at("response"), "status") != "completed") refuse("provider_error", "Completion has no completed response");
                for (const auto& entry : calls) if (!entry.second.emitted) refuse("interrupted", "Incomplete function call at completion");
                for (const auto& entry : items) if (!entry.second.done) refuse("interrupted", "Incomplete output item at completion");
                status = refused ? "failed" : "completed";
            } else if (type == "response.incomplete") status = "interrupted";
            terminal = true;
            emit({{"type", "turn_finished"}, {"status", status}, {"message", refused ? "The model refused the request." : (status == "completed" ? "" : "The provider response failed or was incomplete.")}});
        }
    }
};
OpenAiStream::OpenAiStream(std::string turn, std::string request, Sink sink) : state_(std::make_unique<State>()) {
    state_->turn = std::move(turn); state_->request = std::move(request); state_->sink = std::move(sink);
}
OpenAiStream::~OpenAiStream() = default;
Reply OpenAiStream::feed(std::string_view bytes) {
    auto& state = *state_;
    if (state.failed) return failure(state.failure_code, "The provider stream has already failed");
    try {
        state.diagnostic_stage = "SSE framing";
        if (bytes.size() > Limits::stream_wire_bytes - state.wire) refuse("resource_exhausted", "Provider wire limit exceeded");
        state.wire += bytes.size();
        for (char c : bytes) {
            if (c != '\n') {
                if (state.pending.size() >= Limits::message_bytes && !(c == '\r' && state.pending.size() == Limits::message_bytes)) refuse("invalid_json", "SSE line exceeds message limit");
                state.pending += c; state.partial(); continue;
            }
            auto line = std::exchange(state.pending, {}); if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) { state.event(); state.diagnostic_stage = "SSE framing"; }
            else if (line.starts_with("data:")) {
                std::string_view data(line); data.remove_prefix(5); if (data.starts_with(' ')) data.remove_prefix(1);
                if (data.size() + 1 > Limits::message_bytes + 1 - state.record.size()) refuse("invalid_json", "SSE event exceeds message limit");
                state.record.append(data); state.record += '\n'; state.partial();
            }
        }
        return success();
    } catch (const Refusal& e) { state.failed = true; state.failure_code = e.code; return failure(e.code, state.diagnostic(e.what())); }
    catch (const std::exception& error) { state.failed = true; state.failure_code = "invalid_argument"; return failure("invalid_argument", state.exception_diagnostic(error)); }
}
Reply OpenAiStream::finish() {
    if (state_->failed) return failure(state_->failure_code, "Provider stream failed");
    if (!state_->terminal || !state_->pending.empty() || !state_->record.empty()) return failure("interrupted", "Provider stream ended before settlement");
    return success();
}
JsonText OpenAiStream::output() const {
    A output;
    for (const auto& [position, id] : state_->positions) {
        (void)position;
        if (state_->items.at(id).done) output.push_back(state_->items.at(id).original);
    }
    bounded(output, Limits::stream_retained_bytes, Limits::stream_items);
    return json::write(output);
}
}
