#include "edi/assistant.hpp"
#include "edi/live_preview.hpp"
#include "edi/fit_job.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "json.hpp"
#ifdef EDI_TEST_ADMISSION_FAULT
#include "interruption_fixture.hpp"
#endif
#ifdef EDI_TEST_TERMINAL_RETENTION
#include "terminal_retention_fixture.hpp"
#endif

#include <cstdlib>
#include <new>
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

namespace {
thread_local bool publication_fault_armed=false;
thread_local bool publication_fault_fired=false;
thread_local edi::Parameter* publication_observed_parameter=nullptr;
thread_local edi::Project* publication_observed_project=nullptr;
thread_local double publication_original_value=0;
thread_local const std::string* publication_expected_message=nullptr;
void publication_allocation_boundary() {
    if(publication_fault_armed && publication_observed_parameter->value.get()!=publication_original_value &&
       publication_observed_project->fit_result.message!=*publication_expected_message) {
        publication_fault_armed=false; publication_fault_fired=true;
        throw std::bad_alloc();
    }
}
}
void* operator new(std::size_t size) {
#ifdef EDI_TEST_ADMISSION_FAULT
    independent_fault::allocation();
#endif
    publication_allocation_boundary();
    if(void* memory=std::malloc(size ? size : 1)) return memory;
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete[](void* memory) noexcept { std::free(memory); }
void operator delete(void* memory,std::size_t) noexcept { std::free(memory); }
void operator delete[](void* memory,std::size_t) noexcept { std::free(memory); }

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


// Independent queued-before-start observation; never substitutes optimizer results.
struct IndependentQueueHold {
    std::mutex mutex;
    std::condition_variable condition;
    bool entered=false, released=false;
    void release() {
        {std::lock_guard lock(mutex);released=true;}
        condition.notify_all();
    }
};
struct IndependentHoldRelease {
    std::shared_ptr<IndependentQueueHold>& hold;
    ~IndependentHoldRelease() {if(hold) hold->release();}
};

int main() {
    std::mutex mutex;
    std::condition_variable arrived;
    const auto owner = std::this_thread::get_id();
    std::atomic<int> owner_clock_violations{0};
    std::deque<edi::work::Delivery> deliveries;
    std::mutex queue_trace_mutex;
    std::vector<edi::work::Event> queue_trace;
    std::size_t queue_mark=0;
    edi::work::Ticket queue_predecessor=0;
    std::shared_ptr<IndependentQueueHold> queue_hold;
    edi::work::Worker worker([&](edi::work::Delivery delivery) {
        std::lock_guard lock(mutex);
        deliveries.push_back(std::move(delivery));
        arrived.notify_one();
    }, {.clock_ns={}, .trace=[&](const edi::work::Event& event) {
        std::lock_guard lock(queue_trace_mutex);queue_trace.push_back(event);
    }});
    auto project = std::make_unique<edi::Project>();
    project->structure().cell.length_a.value = 4.37;
    project->structure().cell.length_b.value = 5.19;
    project->structure().cell.length_a.uncertainty = .023;
    project->structure().cell.length_b.uncertainty = std::nullopt;
    auto preview = std::make_unique<edi::LivePreview>(*project, worker, edi::LivePreview::Hooks{});
    Array events, requests;
    std::uint64_t now = 107;
    bool steady_clock = false;
    bool clock_on_fit = false;
    auto clock_start = std::chrono::steady_clock::now();
    int applies = 0;
    bool refuse_apply = false;
#ifdef EDI_TEST_TERMINAL_RETENTION
    const char* retention_mode=std::getenv("EDI_TEST_RETENTION_MODE");
    IndependentRetention retention(retention_mode?retention_mode:"accept");
#endif
    edi::assistant::Hooks controller_hooks{
        [&](const std::string& text) {
#ifdef EDI_TEST_ADMISSION_FAULT
            independent_fault::HostHook safe_host;
            auto event=edi::json::parse(text);
            independent_fault::event(event);
            events.push_back(std::move(event));
#else
            events.push_back(edi::json::parse(text));
#endif
        },
        [&](const std::string& text) {
#ifdef EDI_TEST_ADMISSION_FAULT
            independent_fault::HostHook safe_host;
#endif
#ifdef EDI_TEST_TERMINAL_RETENTION
            if(retention.mode!="headless") retention.record("request");
#endif
            requests.push_back(edi::json::parse(text));
        },
        [&](const edi::Edit& edit, bool) {
#ifdef EDI_TEST_ADMISSION_FAULT
            independent_fault::HostHook safe_host;
#endif
            ++applies;
            if (refuse_apply) return std::string("independent host refusal");
            try { preview->apply(edit); return std::string{}; }
            catch (const std::exception& e) { return std::string(e.what()); }
        },
        [&] {
#ifdef EDI_TEST_ADMISSION_FAULT
            independent_fault::HostHook safe_host;
#endif
            if (std::this_thread::get_id() != owner) ++owner_clock_violations;
            if (steady_clock) return now + static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-clock_start).count());
            return now;
        }
    };
#ifdef EDI_TEST_TERMINAL_RETENTION
    if(retention.mode!="headless") controller_hooks.reserve_terminal=[&](const std::string& text) {
        return retention.reserve(text);
    };
#endif
    edi::assistant::Controller controller(worker,std::move(controller_hooks));
    IndependentHoldRelease release_before_controller_teardown{queue_hold};
    double owner_work_max_ms=0;
    auto deliver = [&](int milliseconds) {
        edi::work::Delivery next;
        {
            std::unique_lock lock(mutex);
            arrived.wait_for(lock, std::chrono::milliseconds(milliseconds), [&] { return !deliveries.empty(); });
            if (deliveries.empty()) return false;
            next = std::move(deliveries.front()); deliveries.pop_front();
        }
        auto began=std::chrono::steady_clock::now();
        next();
        owner_work_max_ms=std::max(owner_work_max_ms,std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count());
        return true;
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
            } else if (op == "objective") {
                auto copy=std::make_unique<edi::Project>(*project);
                copy->calculate();
                double objective=0;
                int points=0;
                for(std::size_t bank=0;bank<copy->experiments.size();++bank) {
                    auto pattern=edi::capture_pattern(*copy,bank);
                    if(!pattern.current || !pattern.meas || !pattern.calc || !pattern.su)
                        throw std::runtime_error("independent weighted residual requires current measured pattern");
                    for(std::size_t i=0;i<pattern.meas->size();++i) {
                        if(!std::isfinite(pattern.calc->at(i))) continue;
                        const double residual=(pattern.meas->at(i)-pattern.calc->at(i))/pattern.su->at(i);
                        objective+=copy->experiments[bank]->dataset_weight*residual*residual;
                        ++points;
                    }
                }
                result=Object{{"objective",objective},{"points",points},
                              {"held_objective",project->fit_result.objective_value}};
            } else if (op == "publication_fault") {
                auto fitted=std::make_shared<edi::Project>(*project);
                auto& target=project->structure().cell.length_a;
                fitted->structure().cell.length_a.value=target.value.get()*1.01;
                fitted->structure().cell.length_a.uncertainty=.037;
                fitted->structure().cell.length_a.start_value=target.value.get();
                fitted->fit_result.message=std::string(4096,'m');
                auto edit=edi::Edit::assistant_result(*project,fitted);
                publication_observed_parameter=&target;
                publication_observed_project=project.get();
                publication_original_value=target.value.get();
                publication_expected_message=&fitted->fit_result.message;
                publication_fault_fired=false;
                publication_fault_armed=input.at("armed").boolean("armed");
                bool threw=false;
                try {
                    if(input.at("door").boolean("door")) preview->apply(edit);
                    else edit();
                } catch(const std::bad_alloc&) { threw=true; }
                publication_fault_armed=false;
                result=Object{{"threw",threw},{"fired",publication_fault_fired},
                              {"complete",target.value.get()==fitted->structure().cell.length_a.value.get() &&
                               project->fit_result.message==fitted->fit_result.message}};
            } else if (op == "prepare_free_group") {
                std::set<std::string> paths;
                for(const auto& item:input.at("paths").array("paths")) paths.insert(item.string("path"));
                for(auto& item:edi::parameter_entries(*project)) item.parameter->free=paths.contains(item.path);
                project->note_edit(); controller.notify_changed(); result=Object{};
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
                steady_clock=input.at("steady").boolean("steady"); clock_on_fit=!input.get("fit_admission").is_null() && input.at("fit_admission").boolean("fit_admission"); owner_work_max_ms=0; clock_start=std::chrono::steady_clock::now();
                result=Object{};
            } else if (op == "queue_hold") {
                if(queue_hold) throw std::invalid_argument("queue hold already exists");
                queue_hold=std::make_shared<IndependentQueueHold>();
                {std::lock_guard lock(queue_trace_mutex);queue_mark=queue_trace.size();}
#if !EDI_WORKER_OWNER_THREAD
                auto hold=queue_hold;
                queue_predecessor=worker.submit("independent-preceding-job",
                    [hold](const edi::work::CancelToken& stop,const edi::work::Emit&) {
                        std::unique_lock lock(hold->mutex);
                        hold->entered=true;hold->condition.notify_all();
                        hold->condition.wait_for(lock,std::chrono::seconds(2),[&] {
                            return hold->released || stop.cancelled();
                        });
                        return edi::work::Delivery{};
                    });
                std::unique_lock lock(hold->mutex);
                if(!hold->condition.wait_for(lock,std::chrono::milliseconds(500),[&] {return hold->entered;}))
                    throw std::runtime_error("independent preceding job never entered");
#endif
                result=Object{{"armed",true}};
            } else if(op == "queue_elapsed") {
                const int delay=static_cast<int>(input.at("milliseconds").number("milliseconds"));
                if(!queue_hold || delay<1 || delay>250) throw std::invalid_argument("independent bounded queue delay");
                const auto began=std::chrono::steady_clock::now();
                std::this_thread::sleep_for(std::chrono::milliseconds(delay));
                const auto spent=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();
                std::size_t submitted=0,started=0;
                {std::lock_guard lock(queue_trace_mutex);
                 for(std::size_t i=queue_mark;i<queue_trace.size();++i) {
                    const auto& event=queue_trace[i];
                    if(event.id<=queue_predecessor) continue;
                    submitted+=event.kind==edi::work::EventKind::Submitted;
                    started+=event.kind==edi::work::EventKind::Started;
                 }}
                std::size_t pending;
                {std::lock_guard lock(mutex);pending=deliveries.size();}
                result=Object{{"elapsed_ms",spent},{"submitted",static_cast<double>(submitted)},
                              {"started",static_cast<double>(started)},{"pending_owner_deliveries",static_cast<double>(pending)}};
            } else if(op == "queue_release") {
                if(!queue_hold) throw std::invalid_argument("independent hold is not armed");
                queue_hold->release();result=Object{{"released",true}};
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
            } else if (op == "clear_requests") {
                if(requests.size()>1) requests.erase(requests.begin(),requests.end()-1);
                result=Object{};
            } else if (op == "provider_chunks") {
                edi::assistant::Reply last;
                int accepted=0;
                for(const auto& payload:input.at("payloads").array("payloads")) {
                    last=controller.provider_event(edi::json::write(payload));
                    if(!last.ok) break;
                    ++accepted;
                }
                result=Object{{"accepted",accepted},{"last",reply(last)}};
            } else if (op == "provider_repeat") {
                edi::assistant::Reply last;
                int accepted=0;
                const auto text=edi::json::write(input.at("payload"));
                const int count=static_cast<int>(input.at("count").number("count"));
                for(int i=0;i<count;++i) {
                    last=controller.provider_event(text);
                    if(!last.ok) break;
                    ++accepted;
                }
                result=Object{{"accepted",accepted},{"last",reply(last)}};
            } else if (op == "attach") {
                result = reply(controller.attach(project.get(), input.at("id").string("id")));
            } else if (op == "detach") {
                result = reply(controller.attach(nullptr, ""));
#ifdef EDI_TEST_ADMISSION_FAULT
            } else if (op == "fault_user" || op == "fault_provider") {
                const auto payload=edi::json::write(input.at("payload"));
                const auto ordinal=static_cast<std::uint64_t>(input.at("ordinal").number("ordinal"));
                const bool as_length=input.at("length").boolean("length");
                edi::assistant::Reply actual;
                {
                    independent_fault::Arm armed(ordinal,as_length);
                    actual=op=="fault_user" ? controller.user_command(payload) : controller.provider_event(payload);
                }
                result=reply(actual);
#endif
            } else if (op == "user") {
                result = reply(controller.user_command(edi::json::write(input.at("payload"))));
            } else if (op == "user_raw") {
                result = reply(controller.user_command(input.at("text").string("text")));
            } else if (op == "provider") {
                if(clock_on_fit && !input.at("payload").get("name").is_null() &&
                   input.at("payload").at("name").string("name")=="fit_trial") {
                    clock_on_fit=false; steady_clock=true; clock_start=std::chrono::steady_clock::now();
                }
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
            } else if (op == "stream_repeat" || op == "stream_chunks") {
                edi::assistant::Reply last;
                int accepted=0;
                if(op == "stream_repeat") {
                    const auto text=input.at("text").string("text");
                    const int count=static_cast<int>(input.at("count").number("count"));
                    for(int i=0;i<count;++i) {
                        last=stream->feed(text);
                        if(!last.ok) break;
                        ++accepted;
                    }
                } else {
                    for(const auto& chunk:input.at("chunks").array("chunks")) {
                        last=stream->feed(chunk.string("chunk"));
                        if(!last.ok) break;
                        ++accepted;
                    }
                }
                result=Object{{"accepted",accepted},{"last",reply(last)}};
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
                {"owner_work_max_ms",owner_work_max_ms},
                {"owner_thread_kit", static_cast<bool>(EDI_WORKER_OWNER_THREAD)}};
#ifdef EDI_TEST_TERMINAL_RETENTION
            std::get<Object>(output.data).emplace_back("retention",retention.observation());
#endif
#ifdef EDI_TEST_ADMISSION_FAULT
            std::get<Object>(output.data).emplace_back("allocation_fault",independent_fault::observation());
#endif
            std::cout << edi::json::write(output) << '\n' << std::flush;
        } catch (const std::exception& error) {
            std::cout << edi::json::write(Object{{"probe_error", error.what()}}) << '\n' << std::flush;
        }
    }
}
