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
    bool terminal = false, failed = false, refused = false, unbound_text = false;
    std::uint64_t wire = 0, events = 0, retained_base = 0;
    struct Item { J original; bool done = false; };
    struct Call { std::string id, name, arguments; bool emitted = false, deltas = false; };
    std::map<std::string, Item> items;
    std::map<std::string, Call> calls;
    std::vector<std::string> order;
    std::set<std::string> text_items;

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
    void item(const J& original, bool done) {
        const auto id = identifier(original, "id"); const auto type = string(original, "type");
        const auto prior = items.find(id);
        if (prior == items.end()) {
            if (items.size() >= Limits::stream_items) refuse("resource_exhausted", "Provider item count exceeds limit");
            order.push_back(id); items.emplace(id, Item{original, false});
        } else if (string(prior->second.original, "type") != type) refuse("invalid_argument", "Provider item type changed");
        auto& held = items.at(id);
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
        held.original = original; held.done = done; retained();
        if (done && type == "message") for (const auto& content : original.at("content").array("content")) {
            const auto kind = string(content, "type");
            if (kind == "refusal") {
                refused = true;
                if (!text_items.count(id) && !unbound_text) emit({{"type", "text_delta"}, {"text", string(content, "refusal", true)}});
            } else if (kind == "output_text" && !text_items.count(id) && !unbound_text)
                emit({{"type", "text_delta"}, {"text", string(content, "text", true)}});
        }
    }
    void event() {
        if (record.empty()) return;
        auto body = std::exchange(record, {}); if (body.back() == '\n') body.pop_back();
        if (body.empty()) return;
        if (++events > Limits::stream_events) refuse("resource_exhausted", "Provider event count exceeds limit");
        if (body == "[DONE]") { if (!terminal) refuse("interrupted", "Stream ended without terminal response"); return; }
        if (terminal) refuse("invalid_argument", "Data after terminal response");
        const auto message = parse(body); const auto type = string(message, "type");
        if (type == "response.output_text.delta" || type == "response.refusal.delta") {
            if (has(message, "item_id")) text_items.insert(identifier(message, "item_id")); else unbound_text = true;
            if (type == "response.refusal.delta") refused = true;
            emit({{"type", "text_delta"}, {"text", string(message, "delta", true)}});
        } else if (type == "response.output_item.added" || type == "response.output_item.done") {
            item(message.at("item"), type == "response.output_item.done");
        } else if (type == "response.function_call_arguments.delta" || type == "response.function_call_arguments.done") {
            const auto id = identifier(message, "item_id"); const auto found = calls.find(id);
            if (found == calls.end()) refuse("invalid_argument", "Arguments for an unknown tool item");
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
            if (has(message, "response") && has(message.at("response"), "output"))
                for (const auto& output : message.at("response").at("output").array("output")) item(output, true);
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
        if (bytes.size() > Limits::stream_wire_bytes - state.wire) refuse("resource_exhausted", "Provider wire limit exceeded");
        state.wire += bytes.size();
        for (char c : bytes) {
            if (c != '\n') {
                if (state.pending.size() >= Limits::message_bytes && !(c == '\r' && state.pending.size() == Limits::message_bytes)) refuse("invalid_json", "SSE line exceeds message limit");
                state.pending += c; state.partial(); continue;
            }
            auto line = std::exchange(state.pending, {}); if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) state.event();
            else if (line.starts_with("data:")) {
                std::string_view data(line); data.remove_prefix(5); if (data.starts_with(' ')) data.remove_prefix(1);
                if (data.size() + 1 > Limits::message_bytes + 1 - state.record.size()) refuse("invalid_json", "SSE event exceeds message limit");
                state.record.append(data); state.record += '\n'; state.partial();
            }
        }
        return success();
    } catch (const Refusal& e) { state.failed = true; state.failure_code = e.code; return failure(e.code, e.what()); }
    catch (const std::exception&) { state.failed = true; state.failure_code = "invalid_argument"; return failure("invalid_argument", "Invalid provider stream"); }
}
Reply OpenAiStream::finish() {
    if (state_->failed) return failure(state_->failure_code, "Provider stream failed");
    if (!state_->terminal || !state_->pending.empty() || !state_->record.empty()) return failure("interrupted", "Provider stream ended before settlement");
    return success();
}
JsonText OpenAiStream::output() const {
    A output;
    for (const auto& id : state_->order) if (state_->items.at(id).done) output.push_back(state_->items.at(id).original);
    bounded(output, Limits::stream_retained_bytes, Limits::stream_items);
    return json::write(output);
}
}
