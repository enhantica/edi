// SPDX-License-Identifier: BSD-3-Clause
#include "edi/assistant.hpp"

#include <map>
#include <utility>

#include "assistant_json.hpp"

namespace edi::assistant {
using namespace detail;

struct OpenAiStream::State {
    std::string turn, request, pending, record;
    Sink sink;
    bool terminal = false, failed = false;
    struct Call { std::string id, name, arguments; bool emitted = false; };
    std::map<std::string, Call> calls;
    void emit(O fields) {
        fields.emplace_back("schema", "edi.assistant/1");
        fields.emplace_back("turn_id", turn);
        fields.emplace_back("request_id", request);
        if (sink) sink(json::write(fields));
    }
    void tool(Call& call, const std::string& arguments) {
        if (call.emitted) {
            if (call.arguments != arguments) refuse("invalid_argument", "Conflicting completed tool arguments");
            return;
        }
        if (call.id.empty() || call.name.empty()) refuse("invalid_argument", "Tool identity is incomplete");
        J args = parse(arguments);
        args.object("arguments");
        O domain;
        O event{{"type", "tool_call"}, {"call_id", call.id}, {"name", call.name}};
        for (const auto& [name, value] : args.object("arguments")) {
            if (name == "plan_id") event.emplace_back("plan_id", value);
            else domain.emplace_back(name, value);
        }
        event.emplace_back("arguments", std::move(domain));
        emit(std::move(event));
        call.arguments = arguments;
        call.emitted = true;
    }
    void event() {
        if (record.empty()) return;
        std::string body = std::exchange(record, {});
        if (!body.empty() && body.back() == '\n') body.pop_back();
        if (body == "[DONE]") {
            if (!terminal) refuse("interrupted", "Stream ended without a completed response");
            return;
        }
        if (terminal) refuse("invalid_argument", "Data after terminal response");
        const J message = parse(body);
        const auto type = string(message, "type");
        if (type == "response.output_text.delta") {
            emit({{"type", "text_delta"}, {"text", string(message, "delta", true)}});
        } else if (type == "response.output_item.added" || type == "response.output_item.done") {
            const J& item = message.at("item");
            if (string(item, "type") != "function_call") return;
            auto& call = calls[string(item, "id")];
            call.id = string(item, "call_id");
            call.name = string(item, "name");
            if (type == "response.output_item.done") tool(call, string(item, "arguments", true));
        } else if (type == "response.function_call_arguments.delta") {
            auto& call = calls[string(message, "item_id")];
            call.arguments += string(message, "delta", true);
            if (call.arguments.size() > kMessageLimit) refuse("invalid_argument", "Tool arguments too large");
        } else if (type == "response.function_call_arguments.done") {
            auto& call = calls[string(message, "item_id")];
            if (has(message, "call_id")) call.id = string(message, "call_id");
            if (has(message, "name")) call.name = string(message, "name");
            tool(call, string(message, "arguments", true));
        } else if (type == "response.completed" || type == "response.failed" || type == "response.incomplete" || type == "error") {
            std::string status = "failed";
            if (type == "response.completed") {
                if (string(message.at("response"), "status") != "completed")
                    refuse("provider_error", "Completion event has no completed response");
                for (const auto& [id, call] : calls) {
                    (void)id;
                    if (!call.emitted) refuse("interrupted", "Incomplete function call at response completion");
                }
                status = "completed";
            } else if (type == "response.incomplete") status = "interrupted";
            emit({{"type", "turn_finished"}, {"status", status}});
            terminal = true;
        }
    }
};

OpenAiStream::OpenAiStream(std::string turn_id, std::string request_id, Sink sink)
    : state_(std::make_unique<State>()) {
    state_->turn = std::move(turn_id); state_->request = std::move(request_id); state_->sink = std::move(sink);
}
OpenAiStream::~OpenAiStream() = default;
Reply OpenAiStream::feed(std::string_view bytes) {
    auto& state = *state_;
    if (state.failed) return failure("interrupted", "The stream has already failed");
    try {
        state.pending.append(bytes);
        if (state.pending.size() > kMessageLimit) refuse("invalid_argument", "SSE line too large");
        std::size_t end = 0;
        while ((end = state.pending.find('\n')) != std::string::npos) {
            std::string line = state.pending.substr(0, end);
            state.pending.erase(0, end + 1);
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) state.event();
            else if (line.starts_with("data:")) {
                auto data = line.substr(5);
                if (data.starts_with(' ')) data.erase(0, 1);
                state.record += data + '\n';
                if (state.record.size() > kMessageLimit) refuse("invalid_argument", "SSE event too large");
            }
        }
        return success();
    } catch (const Refusal& error) { state.failed = true; return failure(error.code, error.what()); }
    catch (const std::exception& error) { state.failed = true; return failure("invalid_argument", error.what()); }
}
Reply OpenAiStream::finish() {
    if (state_->failed || !state_->terminal || !state_->record.empty() || !state_->pending.empty())
        return failure("interrupted", "Provider stream ended before terminal settlement");
    return success();
}
}  // namespace edi::assistant
