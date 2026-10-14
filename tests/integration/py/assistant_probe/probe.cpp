#include "edi/assistant.hpp"
#include "edi/live_preview.hpp"
#include "edi/parameter_walk.hpp"
#include "json.hpp"

#include <deque>
#include <iostream>
#include <mutex>
#include <memory>
#include <string>

using edi::json::Array;
using edi::json::Object;
using edi::json::Value;

namespace {
Value reply(const edi::assistant::Reply& r) {
    return Object{{"ok", r.ok}, {"code", r.code}, {"value", edi::json::parse(r.value)}};
}
Value snapshot(edi::Project& p) {
    Array parameters;
    for (const auto& item : edi::parameter_entries(p)) {
        const auto& u = item.parameter->uncertainty.get();
        parameters.emplace_back(Object{{"path", item.path}, {"value", item.parameter->value.get()},
                                       {"uncertainty", u ? Value(*u) : Value(nullptr)},
                                       {"free", item.parameter->free.get()}});
    }
    return Object{{"parameters", parameters}, {"aliases", static_cast<int>(p.aliases.size())},
                  {"constraints", static_cast<int>(p.constraints.size())}};
}
}

int main() {
    std::mutex mutex;
    std::deque<edi::work::Delivery> deliveries;
    edi::work::Worker worker([&](edi::work::Delivery delivery) {
        std::lock_guard lock(mutex);
        deliveries.push_back(std::move(delivery));
    });
    auto project = std::make_unique<edi::Project>();
    project->structure().cell.length_a.value = 4.37;
    project->structure().cell.length_b.value = 5.19;
    project->structure().cell.length_a.uncertainty = .023;
    project->structure().cell.length_b.uncertainty = std::nullopt;
    edi::LivePreview preview(*project, worker, {});
    Array events, requests;
    std::uint64_t now = 107;
    int applies = 0;
    bool refuse_apply = false;
    edi::assistant::Controller controller(worker, {
        [&](const std::string& text) { events.push_back(edi::json::parse(text)); },
        [&](const std::string& text) { requests.push_back(edi::json::parse(text)); },
        [&](const edi::Edit& edit, bool) {
            ++applies;
            if (refuse_apply) return std::string("independent host refusal");
            try { preview.apply(edit); return std::string{}; }
            catch (const std::exception& e) { return std::string(e.what()); }
        },
        [&] { return now; }
    });
    std::unique_ptr<edi::assistant::OpenAiStream> stream;
    Array stream_events;
    std::string line;
    while (std::getline(std::cin, line)) {
        try {
            const auto input = edi::json::parse(line);
            const auto op = input.at("op").string("op");
            Value result;
            if (op == "attach") {
                result = reply(controller.attach(project.get(), input.at("id").string("id")));
            } else if (op == "detach") {
                result = reply(controller.attach(nullptr, ""));
            } else if (op == "user") {
                result = reply(controller.user_command(edi::json::write(input.at("payload"))));
            } else if (op == "user_raw") {
                result = reply(controller.user_command(input.at("text").string("text")));
            } else if (op == "provider") {
                result = reply(controller.provider_event(edi::json::write(input.at("payload"))));
            } else if (op == "external") {
                const auto path = input.at("path").string("path");
                bool found = false;
                for (auto& item : edi::parameter_entries(*project)) {
                    if (item.path != path) continue;
                    item.parameter->value = input.at("value").number("value");
                    project->note_edit();
                    found = true;
                }
                if (!found) throw std::invalid_argument("test host parameter path missing");
                if (input.at("notify").boolean("notify")) controller.notify_changed();
                result = Object{{"changed", true}};
            } else if (op == "refuse_apply") {
                refuse_apply = input.at("value").boolean("value");
                result = Object{};
            } else if (op == "cancel") {
                controller.cancel(); result = Object{};
            } else if (op == "poll") {
                now = static_cast<std::uint64_t>(input.at("now").number("now"));
                controller.poll(); result = Object{};
            } else if (op == "stream_start") {
                stream_events.clear();
                stream = std::make_unique<edi::assistant::OpenAiStream>("turn-fixed", "request-fixed",
                    [&](const std::string& event) { stream_events.push_back(edi::json::parse(event)); });
                result = Object{};
            } else if (op == "stream_feed") {
                std::string bytes;
                for (const auto& value : input.at("bytes").array("bytes"))
                    bytes.push_back(static_cast<char>(static_cast<unsigned char>(value.number("byte"))));
                result = reply(stream->feed(bytes));
            } else if (op == "stream_finish") {
                result = reply(stream->finish());
            } else if (op == "inspect") {
                result = Object{};
            } else throw std::invalid_argument("test host operation missing");
            Value output = Object{{"reply", result}, {"state", edi::json::parse(controller.state())},
                {"context", edi::json::parse(controller.context())}, {"events", events},
                {"requests", requests}, {"stream_events", stream_events},
                {"snapshot", snapshot(*project)}, {"apply_count", applies}};
            std::cout << edi::json::write(output) << '\n' << std::flush;
        } catch (const std::exception& error) {
            std::cout << edi::json::write(Object{{"probe_error", error.what()}}) << '\n' << std::flush;
        }
    }
}
