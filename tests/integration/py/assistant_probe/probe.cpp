#include "edi/assistant.hpp"
#include "edi/live_preview.hpp"
#include "edi/fit_job.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "json.hpp"

#include <deque>
#include <chrono>
#include <condition_variable>
#include <atomic>
#include <set>
#include <thread>
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
        const auto& start_u = item.parameter->start_uncertainty.get();
        const auto& start_v = item.parameter->start_value.get();
        parameters.emplace_back(Object{{"path", item.path}, {"value", item.parameter->value.get()},
                                       {"uncertainty", u ? Value(*u) : Value(nullptr)},
                                       {"free", item.parameter->free.get()},
                                       {"start_value", start_v ? Value(*start_v) : Value(nullptr)},
                                       {"start_uncertainty", start_u ? Value(*start_u) : Value(nullptr)},
                                       {"row_address", std::to_string(reinterpret_cast<std::uintptr_t>(item.parameter))},
                                       {"fittable", item.fittable}});
    }
    Object files;
    std::string files_error;
    try { for (const auto& [name, text] : edi::project_edi_files(p)) files.emplace_back(name, text); }
    catch(const std::exception& error) { files_error=error.what(); }
    return Object{{"files", files}, {"files_error", files_error}, {"parameters", parameters}, {"aliases", static_cast<int>(p.aliases.size())},
                  {"constraints", static_cast<int>(p.constraints.size())}};
}
}

int main() {
    std::mutex mutex;
    std::condition_variable arrived;
    const auto owner = std::this_thread::get_id();
    std::atomic<int> owner_clock_violations{0};
    std::deque<edi::work::Delivery> deliveries;
    edi::work::Worker worker([&](edi::work::Delivery delivery) {
        std::lock_guard lock(mutex);
        deliveries.push_back(std::move(delivery));
        arrived.notify_one();
    });
    auto project = std::make_unique<edi::Project>();
    project->structure().cell.length_a.value = 4.37;
    project->structure().cell.length_b.value = 5.19;
    project->structure().cell.length_a.uncertainty = .023;
    project->structure().cell.length_b.uncertainty = std::nullopt;
    auto preview = std::make_unique<edi::LivePreview>(*project, worker, edi::LivePreview::Hooks{});
    Array events, requests;
    std::uint64_t now = 107;
    bool steady_clock = false;
    auto clock_start = std::chrono::steady_clock::now();
    int applies = 0;
    bool refuse_apply = false;
    edi::assistant::Controller controller(worker, {
        [&](const std::string& text) { events.push_back(edi::json::parse(text)); },
        [&](const std::string& text) { requests.push_back(edi::json::parse(text)); },
        [&](const edi::Edit& edit, bool) {
            ++applies;
            if (refuse_apply) return std::string("independent host refusal");
            try { preview->apply(edit); return std::string{}; }
            catch (const std::exception& e) { return std::string(e.what()); }
        },
        [&] {
            if (std::this_thread::get_id() != owner) ++owner_clock_violations;
            if (steady_clock) return now + static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-clock_start).count());
            return now;
        }
    });
    auto deliver = [&](int milliseconds) {
        edi::work::Delivery next;
        {
            std::unique_lock lock(mutex);
            arrived.wait_for(lock, std::chrono::milliseconds(milliseconds), [&] { return !deliveries.empty(); });
            if (deliveries.empty()) return false;
            next = std::move(deliveries.front()); deliveries.pop_front();
        }
        next(); return true;
    };
    auto parameter = [&](const std::string& path) -> edi::Parameter& {
        for (auto& item : edi::parameter_entries(*project)) if(item.path == path) return *item.parameter;
        throw std::invalid_argument("test host parameter path missing");
    };
    auto fit_summary = [&](const edi::FitReport& report) -> Value {
        std::string status;
        switch(report.status) {
            case edi::FitStatus::DONE: status="done"; break;
            case edi::FitStatus::MAX_ITER: status="max_iter"; break;
            case edi::FitStatus::NO_STEP: status="no_step"; break;
            case edi::FitStatus::CANCELLED: status="cancelled"; break;
            case edi::FitStatus::ERROR: status="error"; break;
            case edi::FitStatus::SUPERSEDED: status="superseded"; break;
        }
        return Object{{"status",status},{"refusal",report.refusal},{"converged",report.result && report.result->converged},
                      {"objective",project->fit_result.objective_value}};
    };
    std::unique_ptr<edi::assistant::OpenAiStream> stream;
    Array stream_events;
    std::string line;
    while (std::getline(std::cin, line)) {
        try {
            const auto input = edi::json::parse(line);
            const auto op = input.at("op").string("op");
            Value result;
            if (op == "load") {
                controller.cancel(); controller.attach(nullptr, ""); preview.reset();
                project = std::make_unique<edi::Project>(edi::load_project(input.at("path").string("path")));
                preview = std::make_unique<edi::LivePreview>(*project, worker, edi::LivePreview::Hooks{});
                if(!input.get("mode").is_null()) project->fitting_mode=input.at("mode").string("mode");
                result = reply(controller.attach(project.get(), "project-A"));
            } else if (op == "manual_fit") {
                if(!input.get("free_paths").is_null()) {
                    std::set<std::string> paths;
                    for(const auto& item:input.at("free_paths").array("paths")) paths.insert(item.string("path"));
                    for(auto& item:edi::parameter_entries(*project)) item.parameter->free=paths.contains(item.path);
                }
                bool finished=false;
                edi::FitReport report;
                edi::FitJob::Hooks hooks;
                hooks.finished=[&](const edi::FitReport& value){report=value;finished=true;};
                edi::FitJob fit(*project,worker,std::move(hooks));
                if(!fit.start()) throw std::runtime_error("manual baseline fit did not start");
                auto end=std::chrono::steady_clock::now()+std::chrono::seconds(8);
                while(!finished && std::chrono::steady_clock::now()<end) deliver(10);
                if(!finished) throw std::runtime_error("manual baseline fit did not settle within host bound");
                controller.notify_changed(); result=fit_summary(report);
            } else if (op == "mutate") {
                auto& target=parameter(input.at("path").string("path"));
                if(!input.get("value").is_null()) target.value=input.at("value").number("value");
                if(!input.get("free").is_null()) target.free=input.at("free").boolean("free");
                project->note_edit();
                if(input.get("notify").is_null() || input.at("notify").boolean("notify")) controller.notify_changed();
                result=Object{};
            } else if (op == "profile") {
                preview->apply(edi::Edit::peak_profile(project->experiment(),input.at("name").string("profile")));
                controller.notify_changed(); result=Object{};
            } else if (op == "clock") {
                steady_clock=input.at("steady").boolean("steady"); clock_start=std::chrono::steady_clock::now();
                result=Object{};
            } else if (op == "fence") {
                const int milliseconds=static_cast<int>(input.at("milliseconds").number("milliseconds"));
                auto completed=std::make_shared<bool>(false);
                worker.submit("independent-owner-fence",[completed](const edi::work::CancelToken&,const edi::work::Emit&) {
                    return [completed] { *completed=true; };
                });
                auto end=std::chrono::steady_clock::now()+std::chrono::milliseconds(milliseconds);
                while(!*completed && std::chrono::steady_clock::now()<end) deliver(1);
                result=Object{{"fenced",*completed}};
            } else if (op == "pump") {
                const int milliseconds=static_cast<int>(input.at("milliseconds").number("milliseconds"));
                auto end=std::chrono::steady_clock::now()+std::chrono::milliseconds(milliseconds);
                int count=0;
                do {
                    if(deliver(1)) ++count;
                    const auto state=edi::json::parse(controller.state());
                    if(state.at("active_job_id").string("job").empty()) break;
                } while(std::chrono::steady_clock::now()<end);
                result=Object{{"deliveries",count}};
            } else if (op == "clear_events") {
                events.clear(); result=Object{};
            } else if (op == "attach") {
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
                {"snapshot", snapshot(*project)}, {"apply_count", applies},
                {"owner_clock_violations", owner_clock_violations.load()},
                {"owner_thread_kit", static_cast<bool>(EDI_WORKER_OWNER_THREAD)}};
            std::cout << edi::json::write(output) << '\n' << std::flush;
        } catch (const std::exception& error) {
            std::cout << edi::json::write(Object{{"probe_error", error.what()}}) << '\n' << std::flush;
        }
    }
}
