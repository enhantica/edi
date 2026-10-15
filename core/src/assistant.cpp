// SPDX-License-Identifier: BSD-3-Clause
#include "edi/assistant.hpp"

#include <atomic>
#include <chrono>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>

#include "assistant_json.hpp"
#include "assistant_capabilities.hpp"
#include "edi/calculation.hpp"
#include "edi/categories.hpp"
#include "edi/fit_job.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include "fit_inputs.hpp"

namespace edi::assistant {
using namespace detail;
namespace {
const char* dependence(Dependence value) {
    switch (value) {
        case Dependence::Independent: return "independent";
        case Dependence::SymmetryFixed: return "symmetry_fixed";
        case Dependence::SymmetryTied: return "symmetry_tied";
        case Dependence::Constrained: return "constrained";
    }
    return "unknown";
}
J parameters(Project& project) {
    std::map<const Parameter*, std::string> names;
    for (const auto& slot : named_slots(project)) names[slot.parameter] = slot.unique_name;
    A rows;
    std::uint64_t bytes = 2;
    for (const auto& entry : parameter_entries(project)) {
        const Parameter& p = *entry.parameter;
        const auto named = names.find(&p);
        const std::string unique_name = named == names.end() ? std::string() : named->second;
        J row = O{{"path", entry.path}, {"unique_name", unique_name}, {"value", p.value.get()},
                            {"uncertainty", p.uncertainty.get() ? J(*p.uncertainty.get()) : J(nullptr)},
                            {"free", p.free.get()}, {"dependence", dependence(p.dependence)},
                            {"unit", p.spec ? p.spec->units : "dimensionless"}};
        const auto growth = payload_size(row, Limits::context_bytes) + (rows.empty() ? 0 : 1);
        if (growth > Limits::context_bytes - bytes) refuse("resource_exhausted", "Project parameter context exceeds limit");
        bytes += growth; rows.push_back(std::move(row));
    }
    return rows;
}
J diagnostics(Project* project) {
    A rows;
    if (project) {
        for (const auto& entry : parameter_entries(*project)) {
            const auto& p = *entry.parameter;
            if (!std::isfinite(p.value.get()) || (p.spec && (p.value.get() < p.spec->range.min || p.value.get() > p.spec->range.max)))
                rows.emplace_back(O{{"code", "edi.assistant.parameter_range"}, {"severity", "error"},
                                    {"path", entry.path}, {"message", "Parameter is outside its physical range"},
                                    {"params", O{}}, {"source", "edi_core"}});
        }
        rows.emplace_back(O{{"code", "edi.assistant.diagnostics_unavailable"}, {"severity", "info"},
                            {"path", ""}, {"message", "A general engine diagnostic/action catalog is not available"},
                            {"params", O{}}, {"source", "edi_core"}});
    }
    return rows;
}
J manifest() {
    A tools;
    const auto add = [&](const char* name, const char* description, O properties, A required, bool mutates = false) {
        if (mutates) { properties.emplace_back("plan_id", O{{"type", "string"}}); required.emplace_back("plan_id"); }
        tools.emplace_back(O{{"name", name}, {"description", description},
                             {"input_schema", O{{"type", "object"}, {"properties", std::move(properties)},
                                                {"required", std::move(required)}, {"additionalProperties", false}}}});
    };
    const J text = O{{"type", "string"}}, num = O{{"type", "number"}}, integer = O{{"type", "integer"}, {"minimum", 1}};
    const auto object = [](O fields, A required) -> J {
        return O{{"type", "object"}, {"properties", std::move(fields)}, {"required", std::move(required)},
                 {"additionalProperties", false}};
    };
    const auto array = [](J items) -> J { return O{{"type", "array"}, {"items", std::move(items)}}; };
    add("inspect_project", "Read the open project and parameter context", {}, {});
    add("list_parameters", "Read parameter paths, values, units and dependence", {}, {});
    add("diagnostics", "Read available physical diagnostics", {}, {});
    add("propose_plan", "Show a bounded refinement plan for explicit user approval",
        {{"summary", text}, {"groups", array(object({{"id", text}, {"paths", array(text)}}, {"id", "paths"}))},
         {"budget", object({{"max_trials", integer}, {"max_iterations", integer}, {"max_elapsed_ms", integer}},
                           {"max_trials", "max_iterations", "max_elapsed_ms"})},
         {"objective", object({{"absolute_tolerance", num}, {"relative_tolerance", num}},
                              {"absolute_tolerance", "relative_tolerance"})}},
        {"summary", "groups", "budget", "objective"});
    add("ask_question", "Ask the real user for scientific choices; wait for their answer before continuing",
        {{"text", text}, {"options", array(object({{"id", text}, {"label", text}, {"description", text}}, {"id", "label", "description"}))},
         {"recommended", O{{"type", A{"string", "null"}}}}, {"allow_free_text", O{{"type", "boolean"}}}},
        {"text", "options", "recommended", "allow_free_text"});
    add("set_parameters", "Set approved independent parameter values",
        {{"values", array(object({{"path", text}, {"value", num}}, {"path", "value"}))}}, {"values"}, true);
    add("set_free", "Choose the approved independent free flags",
        {{"flags", array(object({{"path", text}, {"free", O{{"type", "boolean"}}}}, {"path", "free"}))}}, {"flags"}, true);
    add("begin_trial", "Create one isolated candidate from the accepted state", {{"group_id", text}}, {"group_id"}, true);
    for (const char* name : {"fit_trial", "evaluate_trial", "discard_trial"})
        add(name, "Operate on the one owned refinement trial", {{"trial_id", text}}, {"trial_id"}, true);
    return tools;
}
}

struct Controller::State : std::enable_shared_from_this<Controller::State> {
    work::Worker& worker;
    Hooks hooks;
    Project* live = nullptr;
    Revision version;
    std::uint64_t serial = 0, event_serial = 0;
    bool open = true, ready = false, response_done = false, had_tools = false;
    enum class OutputFailure { none, interrupted, resource };
    OutputFailure output_failure = OutputFailure::none;
    bool user_scope_committed = false;
    std::string conversation, request_trial;
    std::string phase = "disconnected", connection, turn, request, model, effort, text, active_job, question;
    J capabilities = A{}, history = A{}, attachments = A{};
    J question_record;
    std::string question_call;
    std::map<std::string, std::pair<std::string, Reply>> answers;
    struct Plan {
        std::string id;
        J description;
        std::map<std::string, std::set<std::string>> groups;
        std::set<std::string> allowed;
        std::uint64_t max_trials = 0, max_iterations = 0, max_ms = 0, started = 0, trials = 0;
        double absolute = 0, relative = 0;
        bool approved = false;
        WorkStamps stamps;
        edi::detail::FitInputs inputs;
    };
    std::optional<Plan> plan;
    struct Trial {
        std::string id, group, call_id;
        J scope;
        std::shared_ptr<Project> project, accepted;
        WorkStamps accepted_stamps, fitted_stamps;
        edi::detail::FitInputs accepted_inputs, fitted_inputs;
        work::Ticket baseline_ticket = 0;
        bool quarantined = false;
        std::uint64_t revision = 0;
        double baseline = std::numeric_limits<double>::quiet_NaN();
        std::optional<FitReport> report;
        std::unique_ptr<FitJob> job;
    };
    std::shared_ptr<Trial> trial;
    struct Cached { std::string binding; Reply reply; };
    std::uint64_t history_used = 2, cache_used = 2;
    std::string admitting_call, active_call;
    J admitting_event;
    struct Hold { std::uint64_t history = 0, cache = 0; };
    std::map<std::string, Hold> holds;
    using CallMap = std::map<std::string, Cached>;
    using HoldMap = std::map<std::string, Hold>;
    CallMap calls;
    struct Admission {
        Reply result;
        J history;
        CallMap::node_type call;
        HoldMap::node_type hold;
        std::uint64_t history_bytes = 0, cache_bytes = 0;
        // A question can fail publication after admission. Prepare its complete
        // interrupted alternative before exposing the pending question.
        J interrupted_history;
        CallMap::node_type interrupted_call;
        std::uint64_t interrupted_history_bytes = 0, interrupted_cache_bytes = 0;
    };
    std::optional<Admission> admission;
    Reply admitted() {
        if (!admission) throw std::logic_error("No prepared assistant admission");
        return std::move(admission->result);
    }
    Reply output_refusal() const {
        return output_failure == OutputFailure::resource
            ? failure("resource_exhausted", "Assistant output could not be retained")
            : failure("interrupted", "Assistant publication was interrupted");
    }
    void publication_failed(OutputFailure reason) noexcept {
        output_failure = reason;
        interrupt_output();
    }

    State(work::Worker& runner, Hooks services) : worker(runner), hooks(std::move(services)) {
        if (!hooks.monotonic_ms) hooks.monotonic_ms = [] {
            return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count());
        };
    }
    std::string id(const char* kind) {
        static std::atomic<std::uint64_t> next{0};
        auto value = next.load();
        do {
            if (value == UINT64_MAX) refuse("resource_exhausted", "Assistant identity limit exceeded");
        } while (!next.compare_exchange_weak(value, value + 1));
        return std::string(kind) + '-' + std::to_string(value + 1);
    }
    J state() const {
        return O{{"state", phase}, {"project_id", version.project_id}, {"revision", std::to_string(version.revision)},
                 {"active_turn_id", turn}, {"active_job_id", active_job},
                 {"pending_plan_id", plan && !plan->approved ? plan->id : ""},
                 {"pending_question_id", question}, {"can_cancel", !turn.empty() || !active_job.empty()}};
    }
    J context() const {
        J project;
        if (live) project = O{{"id", version.project_id}, {"revision", std::to_string(version.revision)},
                             {"name", live->metadata.name}, {"fitting_mode", live->fitting_mode}};
        return O{{"schema", "edi.assistant.context/1"}, {"project", project},
                 {"parameters", live ? parameters(*live) : J(A{})}, {"diagnostics", diagnostics(live)}};
    }
    void emit(const std::string& type, O fields = {}, const J* scope = nullptr) {
        if (!open || !hooks.event) return;
        fields.emplace_back("schema", "edi.assistant/1"); fields.emplace_back("type", type);
        fields.emplace_back("event_id", std::to_string(++event_serial));
        fields.emplace_back("connection_id", scope ? scope->at("connection_id") : J(connection));
        fields.emplace_back("turn_id", scope ? scope->at("turn_id") : J(turn));
        fields.emplace_back("request_id", scope ? scope->at("request_id") : J(request));
        fields.emplace_back("project_id", scope ? scope->at("project_id") : J(version.project_id));
        fields.emplace_back("revision", scope ? scope->at("revision") : J(std::to_string(version.revision)));
        hooks.event(json::write(fields));
    }
    template <typename Fields>
    bool safe_emit(std::string_view type, Fields&& fields, const J* scope = nullptr) noexcept {
        if (output_failure != OutputFailure::none) return false;
        try { emit(std::string(type), fields(), scope); return true; }
        catch (const std::bad_alloc&) { publication_failed(OutputFailure::resource); }
        catch (const std::length_error&) { publication_failed(OutputFailure::resource); }
        catch (const Refusal& error) { publication_failed(error.code == "resource_exhausted" ? OutputFailure::resource : OutputFailure::interrupted); }
        catch (...) { publication_failed(OutputFailure::interrupted); }
        return false;
    }
    bool status(std::string_view next) noexcept {
        if (output_failure != OutputFailure::none) return false;
        try { phase.assign(next); emit("state_changed", {{"state", state()}}); return true; }
        catch (const std::bad_alloc&) { publication_failed(OutputFailure::resource); }
        catch (const std::length_error&) { publication_failed(OutputFailure::resource); }
        catch (const Refusal& error) { publication_failed(error.code == "resource_exhausted" ? OutputFailure::resource : OutputFailure::interrupted); }
        catch (...) { publication_failed(OutputFailure::interrupted); }
        return false;
    }
    std::uint64_t held_history() const { std::uint64_t n = 0; for (const auto& row : holds) n += row.second.history; return n; }
    std::uint64_t held_cache() const { std::uint64_t n = 0; for (const auto& row : holds) n += row.second.cache; return n; }
    void check_history(const std::vector<J>& items, std::uint64_t future = 0) const {
        auto bytes = history_used; auto count = history.array("history").size();
        for (const auto& item : items) {
            const auto size = payload_size(item, Limits::history_bytes);
            const auto growth = size + (count ? 1 : 0);
            if (growth > Limits::history_bytes - bytes) refuse("resource_exhausted", "Conversation history limit exceeded");
            bytes += growth; ++count;
        }
        if (held_history() + future > Limits::history_bytes - bytes || count + holds.size() + (future ? 1 : 0) > Limits::history_entries)
            refuse("resource_exhausted", "Conversation terminal capacity is unavailable");
    }
    void history_item(J item) {
        check_history({item});
        auto& rows = std::get<A>(history.data);
        history_used += payload_size(item) + (rows.empty() ? 0 : 1);
        rows.push_back(std::move(item));
    }
    J invocation(const J& event) const {
        J arguments = event.at("arguments");
        if (has(event, "plan_id")) set(arguments, "plan_id", event.at("plan_id"));
        return O{{"type", "tool_call"}, {"call_id", string(event, "call_id")}, {"name", string(event, "name")}, {"arguments", arguments}};
    }
    J result_row(const std::string& call, const Reply& result, bool pending = false, const J* scope = nullptr) const {
        // Build independently owned fields in stages. Move the parsed result into
        // the envelope instead of copying its whole recursive JSON tree through
        // an initializer_list while constructing the surrounding temporary.
        auto value = parse(result.value);
        O row;
        row.reserve(11);
        row.emplace_back("type", "tool_result"); row.emplace_back("call_id", call);
        row.emplace_back("ok", result.ok); row.emplace_back("code", result.code);
        row.emplace_back("result", std::move(value)); row.emplace_back("pending", pending);
        row.emplace_back("connection_id", scope ? scope->at("connection_id").string("connection_id") : connection);
        row.emplace_back("turn_id", scope ? scope->at("turn_id").string("turn_id") : turn);
        row.emplace_back("request_id", scope ? scope->at("request_id").string("request_id") : request);
        row.emplace_back("project_id", scope ? scope->at("project_id").string("project_id") : version.project_id);
        row.emplace_back("revision", scope ? scope->at("revision").string("revision") : std::to_string(version.revision));
        return row;
    }
    std::uint64_t cache_size(const J& event, const Reply& result) const {
        return payload_size(O{{"binding", canonical(event)}, {"reply", result_row(string(event, "call_id"), result, false, &event)}});
    }
    void preflight(const Reply& result, bool pending = false) {
        if (admitting_call.empty()) return;
        if (result.value.size() > Limits::message_bytes) refuse("resource_exhausted", "Tool result exceeds the assistant payload limit");
        const auto call_row = invocation(admitting_event);
        const auto reply_row = result_row(admitting_call, result, pending, &admitting_event);
        const auto cache = cache_size(admitting_event, result) + (calls.empty() ? 0 : 1);
        if (calls.size() + 1 > Limits::completed_calls || cache + held_cache() > Limits::completed_call_bytes - cache_used)
            refuse("resource_exhausted", "Completed-call capacity is unavailable");
        std::uint64_t reserve = 0;
        if (pending) {
            const J skeleton = result_row(admitting_call, success(), false);
            reserve = payload_size(skeleton) - 2 + Limits::message_bytes + 1;
        }
        check_history({call_row, reply_row}, reserve);
        if (pending) {
            const auto final_cache = payload_size(O{{"binding", canonical(admitting_event)}, {"reply", result_row(admitting_call, success())}}) - 2 + Limits::message_bytes;
            const auto growth = final_cache > cache ? final_cache - cache : 0;
            if (cache + growth + held_cache() > Limits::completed_call_bytes - cache_used)
                refuse("resource_exhausted", "Completed terminal capacity is unavailable");
        }
        Admission prepared;
        prepared.result = result;
        prepared.history = history;
        auto& next_rows = std::get<A>(prepared.history.data);
        next_rows.reserve(next_rows.size() + 2);
        next_rows.push_back(call_row); next_rows.push_back(reply_row);
        prepared.history_bytes = payload_size(prepared.history, Limits::history_bytes);
        prepared.cache_bytes = cache_used + cache;
        CallMap staged_call;
        staged_call.emplace(admitting_call, Cached{json::write(canonical(admitting_event)), result});
        prepared.call = staged_call.extract(admitting_call);
        if (pending) {
            const auto terminal_history = payload_size(result_row(admitting_call, success())) - 2 + Limits::message_bytes + 1;
            const auto next_cache = payload_size(O{{"binding", canonical(admitting_event)}, {"reply", result_row(admitting_call, success())}}) - 2 + Limits::message_bytes;
            const auto previous_cache = cache_size(admitting_event, result);
            HoldMap staged_hold;
            staged_hold.emplace(admitting_call, Hold{terminal_history, next_cache > previous_cache ? next_cache - previous_cache : 0});
            prepared.hold = staged_hold.extract(admitting_call);
        }
        if (pending && string(admitting_event, "name") == "ask_question") {
            const auto interrupted = failure("interrupted", "The question was interrupted before an answer");
            prepared.interrupted_history = prepared.history;
            std::get<A>(prepared.interrupted_history.data).push_back(result_row(admitting_call, interrupted, false, &admitting_event));
            prepared.interrupted_history_bytes = payload_size(prepared.interrupted_history, Limits::history_bytes);
            prepared.interrupted_cache_bytes = cache_used + cache_size(admitting_event, interrupted) + (calls.empty() ? 0 : 1);
            if (prepared.interrupted_cache_bytes + held_cache() > Limits::completed_call_bytes)
                refuse("resource_exhausted", "Interrupted-question capacity is unavailable");
            CallMap staged_interrupted;
            staged_interrupted.emplace(admitting_call, Cached{json::write(canonical(admitting_event)), interrupted});
            prepared.interrupted_call = staged_interrupted.extract(admitting_call);
        }
        admission.emplace(std::move(prepared));
    }
    void commit_admission(bool interrupted_question = false) noexcept {
        if (interrupted_question && !admission->interrupted_call.empty()) {
            history = std::move(admission->interrupted_history); history_used = admission->interrupted_history_bytes;
            cache_used = admission->interrupted_cache_bytes; calls.insert(std::move(admission->interrupted_call));
        } else {
            history = std::move(admission->history); history_used = admission->history_bytes;
            cache_used = admission->cache_bytes; calls.insert(std::move(admission->call));
            if (!admission->hold.empty()) holds.insert(std::move(admission->hold));
        }
        admission.reset();
    }
    void finish_call(const std::string& call, const Reply& result) {
        const auto old = calls.find(call);
        if (old == calls.end()) return;
        const auto hold = holds.find(call);
        const auto held = hold == holds.end() ? Hold{} : hold->second;
        const auto event = parse(old->second.binding, Limits::completed_call_bytes);
        const auto row = result_row(call, result, false, &event);
        bounded(parse(result.value), Limits::message_bytes);
        const auto previous = cache_size(event, old->second.reply);
        const auto next = cache_size(event, result);
        if (next > previous && next - previous > Limits::completed_call_bytes - cache_used)
            refuse("resource_exhausted", "Completed tool outcome exceeds reserved capacity");
        // The reservation belongs to this settlement; other pending calls keep theirs.
        holds.erase(call);
        try { check_history({row}); }
        catch (...) { if (held.history || held.cache) holds.emplace(call, held); throw; }
        Reply prepared = result;
        auto& rows = std::get<A>(history.data);
        rows.reserve(rows.size() + 1);
        cache_used = cache_used - previous + next;
        old->second.reply = std::move(prepared);
        history_item(row);
        emit("tool_result", {{"call_id", call}, {"ok", result.ok}, {"code", result.code}, {"result", parse(result.value)}}, &event);
    }
    void reset_conversation() {
        auto next = id("conversation");
        history = A{}; history_used = 2; calls.clear(); cache_used = 2;
        holds.clear(); answers.clear(); conversation = std::move(next);
        admitting_call.clear(); admitting_event = J{}; admission.reset();
    }
    void interrupt_output() noexcept {
        plan.reset(); response_done = true; turn.clear(); request.clear();
        const auto interrupted_question = std::move(question_call);
        question.clear(); question_record = J{}; question_call.clear();
        if (trial) {
            trial->quarantined = true;
            try { if (trial->baseline_ticket) worker.cancel(trial->baseline_ticket); } catch (...) {}
            try { if (trial->job) trial->job->cancel(); } catch (...) {}
        }
        if (!interrupted_question.empty()) {
            try { finish_call(interrupted_question, failure("interrupted", "The question was interrupted")); } catch (...) {}
        }
        phase = "interrupted";
        try { emit("state_changed", {{"state", state()}}); } catch (...) {}
    }
    void stop() noexcept {
        try {
            // Revoke the request before notifying any retaining/rendering host.
            turn.clear(); request.clear(); plan.reset();
            if (!question.empty()) {
                const auto call = std::move(question_call);
                const auto question_id = std::move(question);
                question.clear(); question_record = J{}; question_call.clear();
                finish_call(call, failure("interrupted", "The question was interrupted before an answer"));
                safe_emit("question_invalidated", [&] { return O{{"question_id", question_id}}; });
            }
            if (trial && trial->baseline_ticket) worker.cancel(trial->baseline_ticket);
            if (trial && (trial->baseline_ticket || (trial->job && trial->job->running()))) {
                if (trial->job) trial->job->cancel();
                status("cancelling");
            } else {
                if (!trial || !trial->quarantined) trial.reset();
                active_job.clear(); status(ready ? "idle" : "disconnected");
            }
        } catch (...) { interrupt_output(); }
    }
    void stamps() { if (plan && live) { plan->stamps = work_stamps(*live); plan->inputs = edi::detail::inputs_of(*live); } }
    void current() {
        if (plan && (!unchanged_since(*live, plan->stamps) || edi::detail::inputs_of(*live) != plan->inputs)) {
            stop(); refuse("stale_revision", "The project changed outside the approved action");
        }
    }
    void approved(const J& event) {
        if (!plan || !plan->approved || !has(event, "plan_id") || string(event, "plan_id") != plan->id)
            refuse("approval_required", "Approve this plan in the assistant before execution");
        current();
        if (const auto now = hooks.monotonic_ms(); now < plan->started || now - plan->started >= plan->max_ms) {
            stop(); refuse("out_of_scope", "The approved elapsed-time budget is exhausted");
        }
    }
    J request_payload(const std::string& next_turn, const std::string& next_request,
                      const std::string& next_conversation, const std::string& next_text,
                      const std::string& next_model, const std::string& next_effort, const J& next_history) const {
        const auto project_context = context(); bounded(project_context, Limits::context_bytes);
        O out{{"schema", "edi.assistant/1"}, {"type", "request"}, {"connection_id", connection},
              {"turn_id", next_turn}, {"request_id", next_request}, {"conversation_id", next_conversation},
              {"model", next_model}, {"text", next_text}, {"attachments", A{}},
              {"context", project_context}, {"history", next_history}, {"tools", manifest()}};
        if (!next_effort.empty()) out.emplace_back("effort", next_effort);
        bounded(out, Limits::request_bytes); return out;
    }
    bool send_request() {
        const auto next_request = id("request");
        const auto outgoing = json::write(request_payload(turn, next_request, conversation, text, model, effort, history));
        request_trial = trial ? trial->id : "";
        request = next_request; response_done = false; had_tools = false;
        if (!status("streaming")) return false;
        if (hooks.provider_request) hooks.provider_request(outgoing);
        return true;
    }
    bool continue_turn() {
        if (output_failure != OutputFailure::none) return false;
        if (!response_done || !active_job.empty() || !question.empty() || (plan && !plan->approved)) return true;
        if (had_tools && !turn.empty()) return send_request();
        turn.clear(); request.clear(); return status(ready ? "idle" : "disconnected");
    }
    std::map<std::string, std::pair<Parameter*, std::string>> paths(Project& project) {
        std::map<const Parameter*, std::string> names;
        for (const auto& slot : named_slots(project)) names[slot.parameter] = slot.unique_name;
        std::map<std::string, std::pair<Parameter*, std::string>> rows;
        for (const auto& row : parameter_entries(project)) {
            const auto named = names.find(row.parameter);
            if (named != names.end()) rows[row.path] = {row.parameter, named->second};
        }
        return rows;
    }
    void apply(const Edit& edit, bool structural = false) {
        if (!hooks.apply) refuse("apply_refused", "No project edit host is attached");
        if (version.revision == UINT64_MAX) refuse("resource_exhausted", "Project revision identity limit exceeded");
        const auto message = hooks.apply(edit, structural);
        if (!message.empty()) refuse("apply_refused", message);
        ++version.revision;
        try { stamps(); }
        catch (const std::bad_alloc&) { publication_failed(OutputFailure::resource); }
        catch (const std::length_error&) { publication_failed(OutputFailure::resource); }
        catch (...) { publication_failed(OutputFailure::interrupted); }
    }
    Reply tool(const J& event) {
        const auto name = string(event, "name");
        const J& args = event.at("arguments"); args.object("arguments");
        if (name == "inspect_project" || name == "list_parameters" || name == "diagnostics") {
            shape(args, {});
            if (name == "inspect_project") return success(context());
            if (name == "diagnostics") return success(O{{"diagnostics", diagnostics(live)}});
            return success(O{{"parameters", parameters(*live)}});
        }
        if (name == "propose_plan") {
            shape(args, {"summary", "groups", "budget", "objective"});
            string(args, "summary");
            Plan next;
            next.id = id("plan"); next.description = args;
            const auto rows = paths(*live);
            for (const J& group : args.at("groups").array("groups")) {
                shape(group, {"id", "paths"});
                const auto group_id = string(group, "id");
                if (next.groups.count(group_id)) refuse("invalid_argument", "Duplicate group ID");
                std::set<std::string> group_paths;
                for (const J& path : group.at("paths").array("paths")) {
                    const auto key = path.string("path");
                    if (!rows.count(key) || !group_paths.insert(key).second) refuse("invalid_argument", "Unknown or duplicate parameter path: " + key);
                    next.allowed.insert(key);
                }
                if (group_paths.empty()) refuse("invalid_argument", "A parameter group is empty");
                next.groups.emplace(group_id, std::move(group_paths));
            }
            if (next.groups.empty()) refuse("invalid_argument", "A plan requires a parameter group");
            const J& budget = args.at("budget"); shape(budget, {"max_trials", "max_iterations", "max_elapsed_ms"});
            next.max_trials = positive(budget, "max_trials"); next.max_iterations = positive(budget, "max_iterations");
            if (next.max_iterations > static_cast<std::uint64_t>(std::numeric_limits<int>::max())) refuse("invalid_argument", "Iteration budget is too large");
            next.max_ms = positive(budget, "max_elapsed_ms");
            const J& objective = args.at("objective"); shape(objective, {"absolute_tolerance", "relative_tolerance"});
            next.absolute = number(objective, "absolute_tolerance"); next.relative = number(objective, "relative_tolerance");
            if (next.absolute < 0 || next.relative < 0) refuse("invalid_argument", "Negative objective tolerance");
            if (trial || !active_job.empty()) refuse("busy", "Finish the current trial first");
            next.stamps = work_stamps(*live); next.inputs = edi::detail::inputs_of(*live);
            J shown = args; set(shown, "plan_id", next.id);
            preflight(success(O{{"plan_id", next.id}}));
            plan = std::move(next);
            if (!safe_emit("plan_proposed", [&] { return O{{"plan", shown}, {"plan_id", plan ? plan->id : ""}}; })) return admitted();
            status("awaiting_approval");
            return admitted();
        }
        if (name == "ask_question") {
            shape(args, {"text", "options", "recommended", "allow_free_text"});
            if (!question.empty() || !active_job.empty() || (plan && !plan->approved)) refuse("busy", "Another human decision or fit is pending");
            const auto checked_text = [](const J& object, const char* key, std::uint64_t limit) {
                const auto value = string(object, key);
                if (value.find_first_not_of(" \t\r\n") == std::string::npos) refuse("invalid_argument", "Question text must not be blank");
                if (value.size() > limit) refuse("resource_exhausted", "Question text exceeds its limit");
            };
            checked_text(args, "text", Limits::question_text_bytes);
            const auto& options = args.at("options").array("options");
            if (options.size() > Limits::question_options) refuse("resource_exhausted", "Too many question options");
            if (options.size() == 1) refuse("invalid_argument", "Supply zero or at least two options");
            std::set<std::string> ids;
            for (const auto& option : options) {
                shape(option, {"id", "label", "description"});
                const auto option_id = string(option, "id");
                if (option_id.empty() || option_id.size() > 32 || option_id.front() < 'a' || option_id.front() > 'z' ||
                    !std::all_of(option_id.begin(), option_id.end(), [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_'; }) || !ids.insert(option_id).second)
                    refuse("invalid_argument", "Invalid or duplicate question option ID");
                checked_text(option, "label", Limits::question_option_label_bytes);
                checked_text(option, "description", Limits::question_option_description_bytes);
            }
            const bool free_text = args.at("allow_free_text").boolean("allow_free_text");
            if (options.empty()) {
                if (!free_text || !args.at("recommended").is_null()) refuse("invalid_argument", "A text question requires free text and no recommendation");
            } else if (args.at("recommended").is_null() || !ids.count(args.at("recommended").string("recommended")))
                refuse("invalid_argument", "Recommendation must name an offered option");
            const auto next = id("question");
            J shown = args;
            for (const auto* key : {"connection_id", "turn_id", "request_id", "project_id", "revision", "call_id"}) set(shown, key, event.at(key));
            set(shown, "question_id", next);
            auto question_id = next; auto call = admitting_call; J stored = shown;
            preflight(success(O{{"question_id", next}, {"pending", true}}), true);
            question = std::move(question_id); question_record = std::move(stored); question_call = std::move(call);
            if (!safe_emit("question", [&] { return O{{"question", shown}}; })) return admitted();
            status("awaiting_answer");
            return admitted();
        }
        static const std::set<std::string> mutations{"set_parameters", "set_free", "begin_trial", "fit_trial", "evaluate_trial", "discard_trial"};
        if (!mutations.count(name)) refuse("unknown_tool", "Unknown tool: " + name);
        approved(event);
        if (request_trial != (trial ? trial->id : "")) refuse("stale_revision", "This request belongs to another candidate generation");
        if (name == "set_parameters" || name == "set_free") {
            if (!active_job.empty()) refuse("busy", "A fit is running");
            if (trial && trial->report) refuse("invalid_argument", "Discard the fitted trial before changing its setup");
            Project& target = trial ? *trial->project : *live;
            const auto rows = paths(target);
            const auto& allowed = trial ? plan->groups.at(trial->group) : plan->allowed;
            std::map<std::string, ParameterEntry> metadata;
            for (const auto& row : parameter_entries(target)) metadata.emplace(row.path, row);
            const bool values = name == "set_parameters";
            shape(args, {values ? "values" : "flags"});
            std::set<std::string> seen;
            std::vector<std::pair<std::string, double>> edits;
            std::vector<std::pair<std::string, bool>> flags;
            for (const J& row : args.at(values ? "values" : "flags").array("parameter batch")) {
                shape(row, {"path", values ? "value" : "free"});
                const auto path = string(row, "path");
                if (!seen.insert(path).second || !rows.count(path)) refuse("invalid_argument", "Unknown or duplicate parameter: " + path);
                if (!allowed.count(path)) refuse("out_of_scope", "Parameter not approved: " + path);
                auto [parameter, unique_name] = rows.at(path);
                if (parameter->dependence != Dependence::Independent) refuse("out_of_scope", "Dependent parameter: " + path);
                if (values) edits.emplace_back(unique_name, number(row, "value"));
                else {
                    const bool free = row.at("free").boolean("free");
                    const auto& meta = metadata.at(path);
                    if (free && (!meta.refinable || !meta.fittable || !meta.used_by_profile))
                        refuse("out_of_scope", "The parameter is not independently fittable in this profile");
                    flags.emplace_back(unique_name, free);
                }
            }
            if (seen.empty()) refuse("invalid_argument", "Empty parameter batch");
            Project validated = target;
            if (values) Edit::parameter_values(validated, edits)();
            else Edit::set_free(validated, flags)();
            if (!validated.aliases.empty() || !validated.constraints.empty()) complete_relations(validated);
            else refresh_relations(validated);
            const Edit change = values ? Edit::parameter_values(target, std::move(edits)) : Edit::set_free(target, std::move(flags));
            O predicted{{"revision", std::to_string(version.revision + (trial ? 0 : 1))}};
            if (trial) { predicted.emplace_back("trial_id", trial->id); predicted.emplace_back("candidate_revision", std::to_string(trial->revision + 1)); }
            preflight(success(predicted));
            if (trial) { change(); ++trial->revision; }
            else apply(change);
            return admitted();
        }
        if (name == "begin_trial") {
            shape(args, {"group_id"}); const auto group = string(args, "group_id");
            if (trial || !active_job.empty()) refuse("busy", "A trial already exists");
            if (!plan->groups.count(group)) refuse("out_of_scope", "Unknown parameter group");
            if (plan->trials >= plan->max_trials) refuse("out_of_scope", "Trial budget exhausted");
            auto next = std::make_shared<Trial>();
            next->id = id("trial"); next->group = group; next->project = std::make_shared<Project>(*live);
            refresh_relations(*next->project);
            const auto candidate_paths = paths(*next->project);
            const auto group_paths = plan->groups.at(group);
            std::map<std::string, ParameterEntry> metadata;
            for (const auto& row : parameter_entries(*next->project)) metadata.emplace(row.path, row);
            for (auto* parameter : next->project->parameters()) parameter->free = false;
            for (const auto& path : group_paths) {
                const auto& row = metadata.at(path);
                if (row.parameter->dependence != Dependence::Independent)
                    refuse("out_of_scope", "The selected group contains a dependent parameter");
                // Editable approved setup values need not be optimizer variables.
                if (row.refinable && row.fittable && row.used_by_profile)
                    candidate_paths.at(path).first->free = true;
            }
            next->accepted = std::make_shared<Project>(*live);
            next->accepted_stamps = work_stamps(*live); next->accepted_inputs = edi::detail::inputs_of(*live);
            preflight(success(O{{"trial_id", next->id}}));
            auto next_trial = next->id;
            trial = std::move(next); request_trial = std::move(next_trial); ++plan->trials;
            return admitted();
        }
        shape(args, {"trial_id"});
        if (!trial || string(args, "trial_id") != trial->id) refuse("unknown_trial", "Unknown trial");
        if (!active_job.empty()) refuse("busy", "Wait for the fit to settle");
        if (name == "discard_trial") { preflight(success(O{{"discarded", true}})); trial.reset(); return admitted(); }
        if (name == "fit_trial") {
            if (trial->report) refuse("invalid_argument", "This trial has already been fitted");
            const auto mode = effective_fitting_mode(*trial->project);
            if (mode == "sequential" || mode == "independent")
                refuse("out_of_scope", "Assistant scan trials require the pending checked result-artifact unit");
            const auto max_iterations = static_cast<int>(plan->max_iterations);
            const auto job_id = id("job"); preflight(success(O{{"job_id", job_id}}), true);
            auto next_call = admitting_call; auto next_scope = event;
            auto next_job = job_id; auto next_active_call = admitting_call;
            const auto self = shared_from_this();
            FitJob::Hooks callbacks;
            callbacks.iterated = [self, job_id](const IterationRecord& iteration) {
                if (self->open && self->active_job == job_id)
                    self->emit("job_progress", {{"job_id", job_id}, {"objective", iteration.objective_value ? J(*iteration.objective_value) : J(nullptr)}, {"reduced_chi_square", iteration.reduced_chi_square}}, self->trial ? &self->trial->scope : nullptr);
            };
            callbacks.finished = [self, job_id](const FitReport& report) {
                const auto& state = self;
                const auto candidate = state->trial;
                if (!candidate || !state->open || state->active_job != job_id) return;
                candidate->report = report; state->active_job.clear();
                candidate->job.reset();
                candidate->fitted_stamps = work_stamps(*candidate->project);
                candidate->fitted_inputs = edi::detail::inputs_of(*candidate->project);
                const auto status = [](FitStatus value) {
                    switch (value) {
                        case FitStatus::DONE: return "done";
                        case FitStatus::MAX_ITER: return "max_iter";
                        case FitStatus::NO_STEP: return "no_step";
                        case FitStatus::CANCELLED: return "cancelled";
                        case FitStatus::SUPERSEDED: return "superseded";
                        case FitStatus::UNAVAILABLE: return "unavailable";
                        default: return "error";
                    }
                };
                O values, uncertainties;
                if (report.result) {
                    for (const auto& item : report.result->values) values.emplace_back(item.first, item.second);
                    for (const auto& item : report.result->uncertainty) uncertainties.emplace_back(item.first, item.second);
                }
                const auto& record = candidate->project->fit_result;
                J outcome = O{{"job_id", job_id}, {"trial_id", candidate->id}, {"status", status(report.status)},
                    {"message", report.refusal}, {"candidate_adopted", report.adopted()}, {"live_adopted", false},
                    {"converged", report.result && report.result->converged}, {"objective_name", "chi_square"},
                    {"objective", report.adopted() ? J(record.objective_value) : J(nullptr)},
                    {"baseline_objective", std::isfinite(candidate->baseline) ? J(candidate->baseline) : J(nullptr)},
                    {"reduced_chi_square", report.result ? J(report.result->reduced_chi_square) : J(nullptr)},
                    {"rwp", report.result ? J(report.result->rwp) : J(nullptr)},
                    {"iterations", report.result ? report.result->iterations : 0},
                    {"n_points_fitted", report.result ? J(static_cast<double>(report.result->n_points_fitted)) : J(nullptr)},
                    {"n_free_parameters", record.n_free_parameters}, {"values", values}, {"uncertainties", uncertainties},
                    {"diagnostics", diagnostics(candidate->project.get())}};
                const Reply terminal = report.status == FitStatus::ERROR || report.status == FitStatus::SUPERSEDED || report.status == FitStatus::CANCELLED
                    ? Reply{false, "edi.assistant.interrupted", json::write(outcome)} : success(outcome);
                state->finish_call(candidate->call_id, terminal);
                state->emit("job_finished", {{"job_id", job_id}, {"result", outcome}, {"status", status(report.status)},
                    {"candidate_adopted", report.adopted()}, {"live_adopted", false}}, &candidate->scope);
                if (candidate->quarantined) { state->status("interrupted"); return; }
                if (state->turn.empty()) { state->trial.reset(); state->status(state->ready ? "idle" : "disconnected"); }
                else if (state->status("streaming")) state->continue_turn();
            };
            const auto now = hooks.monotonic_ms();
            const auto elapsed = now >= plan->started ? now - plan->started : plan->max_ms;
            const auto remaining = plan->max_ms - std::min(plan->max_ms, elapsed);
            const auto wall_start = std::chrono::steady_clock::now();
            const auto policy_start = hooks.monotonic_ms();
            const auto clock = hooks.monotonic_ms;
            const auto expired = [remaining, wall_start, policy_start, clock] {
#if EDI_WORKER_OWNER_THREAD
                const auto value = clock();
                if (value < policy_start || value - policy_start >= remaining) return true;
#endif
                return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - wall_start).count() >= static_cast<std::int64_t>(std::min<std::uint64_t>(remaining, INT64_MAX));
            };
            auto prepared_job = std::make_unique<FitJob>(*trial->project, worker, std::move(callbacks), FitJob::Seams{}, expired);
            auto baseline = std::make_shared<Project>(*trial->accepted);
            const auto candidate_slots = named_slots(*trial->project);
            const auto baseline_slots = named_slots(*baseline);
            if (candidate_slots.size() != baseline_slots.size()) refuse("stale_revision", "Baseline parameter identities changed");
            for (std::size_t i = 0; i < candidate_slots.size(); ++i) {
                if (candidate_slots[i].unique_name != baseline_slots[i].unique_name) refuse("stale_revision", "Baseline parameter identities changed");
                baseline_slots[i].parameter->free = candidate_slots[i].parameter->free.get();
            }
            const auto candidate_id = trial->id;
            const auto baseline_ticket = worker.submit("assistant-baseline", [self, baseline, candidate_id, expired, mode](const work::CancelToken& token, const work::Emit&) {
                std::optional<double> objective;
                std::string error;
                try {
                    if (!token.cancelled() && !expired()) {
                        const auto started = [&objective](const FitPreamble& facts) { objective = facts.pre_fit.objective_value; };
                        if (mode == "joint") baseline->fit_joint(IterationCallback{}, started, [] { return true; });
                        else baseline->fit(IterationCallback{}, started, [] { return true; });
                    }
                } catch (const std::exception&) { error = "The accepted baseline could not be evaluated"; }
                return [self, candidate_id, objective, error] {
                    if (!self->open || !self->trial || self->trial->id != candidate_id) return;
                    auto& candidate = *self->trial; candidate.baseline_ticket = 0;
                    if (!objective || !std::isfinite(*objective) || !error.empty() || self->turn.empty()) {
                        FitReport refused; refused.status = self->turn.empty() ? FitStatus::CANCELLED : FitStatus::ERROR;
                        refused.refusal = error.empty() ? "The baseline was interrupted or unavailable" : error;
                        candidate.report = refused; candidate.job.reset(); const auto job_id = self->active_job; self->active_job.clear();
                        self->finish_call(candidate.call_id, {false, "edi.assistant.interrupted", json::write(O{{"job_id", job_id}, {"trial_id", candidate.id}, {"status", self->turn.empty() ? "cancelled" : "error"}, {"message", refused.refusal}, {"candidate_adopted", false}, {"live_adopted", false}})});
                        self->emit("job_finished", {{"job_id", job_id}, {"status", self->turn.empty() ? "cancelled" : "error"}, {"message", refused.refusal}, {"live_adopted", false}}, &candidate.scope);
                        self->status("interrupted");
                        if (self->turn.empty() && !candidate.quarantined) self->trial.reset();
                        return;
                    }
                    candidate.baseline = *objective;
                    if (!candidate.job->start()) { self->active_job.clear(); self->status("failed"); }
                };
            });
            trial->call_id = std::move(next_call); trial->scope = std::move(next_scope);
            trial->job = std::move(prepared_job); trial->baseline_ticket = baseline_ticket;
            if (trial->project->minimizer_max_iterations == 0 || trial->project->minimizer_max_iterations > max_iterations)
                trial->project->minimizer_max_iterations = max_iterations;
            active_job = std::move(next_job); active_call = std::move(next_active_call);
            if (!safe_emit("job_started", [&] { return O{{"job_id", job_id}, {"trial_id", trial->id}}; })) return admitted();
            status("executing");
            return admitted();
        }
        if (!trial->report) refuse("busy", "Fit the trial before evaluating it");
        const auto candidate = trial;
        const auto& report = *candidate->report;
        bool accepted = report.status == FitStatus::DONE && report.result && report.result->converged;
        if (!unchanged_since(*live, candidate->accepted_stamps) || edi::detail::inputs_of(*live) != candidate->accepted_inputs ||
            !unchanged_since(*candidate->project, candidate->fitted_stamps) || edi::detail::inputs_of(*candidate->project) != candidate->fitted_inputs)
            refuse("stale_revision", "The fit evidence no longer describes the accepted and candidate states");
        const auto& record = candidate->project->fit_result;
        const double objective = record.objective_value;
        accepted = accepted && record.held() && record.objective_name == "chi_square" && std::isfinite(objective);
        if (std::isfinite(candidate->baseline))
            accepted = accepted && objective < candidate->baseline - std::max(plan->absolute, std::abs(candidate->baseline) * plan->relative);
        else accepted = false;
        for (const auto& row : parameter_entries(*candidate->project)) {
            const Parameter& p = *row.parameter;
            accepted = accepted && std::isfinite(p.value.get()) && (!p.spec || (p.value.get() >= p.spec->range.min && p.value.get() <= p.spec->range.max));
        }
        const std::string reason = accepted ? "Converged comparable improvement" :
            (std::isfinite(candidate->baseline) ? "The trial did not meet the approved acceptance criteria" : "The accepted project needs a baseline objective before automatic adoption");
        O result{{"accepted", accepted}, {"reason", reason}, {"trial_id", candidate->id},
                 {"revision", std::to_string(version.revision + (accepted ? 1 : 0))}, {"diagnostics", diagnostics(candidate->project.get())}};
        preflight(success(result));
        if (accepted) apply(Edit::assistant_result(*live, candidate->project));
        if (!safe_emit("trial_finished", [&] { return O{{"result", result}}; })) return admitted();
        trial.reset();
        return admitted();
    }
    Reply user(const J& command) {
        output_failure = OutputFailure::none;
        envelope(command); const auto type = string(command, "type");
        if (type == "cancel") {
            shape(command, {"schema", "type"}); user_scope_committed = true; stop();
            return output_failure == OutputFailure::none ? success() : output_refusal();
        }
        if (type == "approve_plan") {
            shape(command, {"schema", "type", "plan_id", "project_id", "revision"});
            if (string(command, "project_id") != version.project_id) refuse("stale_project", "Project changed");
            if (detail::revision(command) != version.revision) refuse("stale_revision", "Project revision changed");
            if (!plan || string(command, "plan_id") != plan->id) refuse("approval_required", "Plan is no longer pending");
            if (plan->approved) { approved(command); return success(O{{"plan_id", plan->id}}); }
            current(); const auto started = hooks.monotonic_ms();
            user_scope_committed = true;
            plan->approved = true; plan->started = started;
            if (!safe_emit("plan_approved", [&] { return O{{"plan_id", plan ? plan->id : ""}}; }) ||
                !status("streaming") || !continue_turn()) return output_refusal();
            return success();
        }
        if (type == "answer") {
            shape(command, {"schema", "type", "question_id", "answer"});
            const auto question_id = string(command, "question_id"); const auto answer = string(command, "answer");
            if (const auto old = answers.find(question_id); old != answers.end()) {
                if (old->second.first != answer) refuse("invalid_argument", "This question was already answered differently");
                return old->second.second;
            }
            if (question.empty() || question_id != question) refuse("invalid_argument", "No matching live question");
            if (answer.size() > Limits::question_answer_bytes) refuse("resource_exhausted", "Question answer exceeds limit");
            bool selected = false;
            for (const auto& option : question_record.at("options").array("options")) if (string(option, "id") == answer) selected = true;
            if (!selected && (!question_record.at("allow_free_text").boolean("allow_free_text") || answer.find_first_not_of(" \t\r\n") == std::string::npos))
                refuse("invalid_argument", "Choose an offered option or provide permitted free text");
            if (string(question_record, "connection_id") != connection || string(question_record, "project_id", true) != version.project_id || detail::revision(question_record) != version.revision)
                refuse("invalid_argument", "Question scope changed");
            const auto result = success(O{{"question_id", question}, {"answer", answer}, {"selected_option_id", selected ? J(answer) : J(nullptr)}});
            if (answers.size() >= Limits::completed_calls) refuse("resource_exhausted", "Answered-question capacity is unavailable");
            user_scope_committed = true;
            finish_call(question_call, result);
            answers.emplace(question, std::make_pair(answer, result));
            emit("question_answered", {{"question_id", question}, {"answer", answer}});
            question.clear(); question_record = J{}; question_call.clear();
            if (!continue_turn()) return output_refusal();
            return result;
        }
        if (type != "message") refuse("invalid_argument", "Unknown user command");
        shape(command, {"schema", "type", "text", "connection_id", "model"}, {"effort", "attachments"});
        if (!ready || string(command, "connection_id") != connection) refuse("connection_required", "Connect a provider first");
        if (!turn.empty() || !active_job.empty()) refuse("busy", "A conversation turn is running");
        auto selected = string(command, "model");
        auto selected_effort = has(command, "effort") ? string(command, "effort") : "";
        bool supported = false;
        const auto mapped_model = openai_efforts(selected);
        if (mapped_model.array("efforts").empty()) refuse("invalid_argument", "Model has no reviewed capability mapping");
        for (const J& item : capabilities.array("capabilities")) if (string(item, "id") == selected) {
            supported = selected_effort.empty();
            for (const J& option : item.at("efforts").array("efforts")) if (option.string("effort") == selected_effort) supported = true;
        }
        if (!supported) refuse("invalid_argument", "Model or effort is not available");
        if (has(command, "attachments") && !command.at("attachments").array("attachments").empty())
            refuse("out_of_scope", "Attachment transfer requires the pending selected-handle unit");
        auto next_text = string(command, "text");
        auto next_turn = id("turn"), next_request = id("request");
        auto next_conversation = conversation.empty() ? id("conversation") : conversation;
        const J user_row = O{{"type", "message"}, {"role", "user"}, {"text", next_text}, {"turn_id", next_turn}, {"request_id", ""}};
        check_history({user_row});
        J next_history = history; std::get<A>(next_history.data).push_back(user_row);
        const auto outgoing = json::write(request_payload(next_turn, next_request, next_conversation, next_text, selected, selected_effort, next_history));
        const auto growth = payload_size(user_row) + (history.array("history").empty() ? 0 : 1);
        auto admitted_message = success(O{{"turn_id", next_turn}, {"request_id", next_request}});
        auto next_trial = trial ? trial->id : std::string();
        // All context/history/wire/return construction succeeded before admission commits.
        user_scope_committed = true;
        text = std::move(next_text); model = std::move(selected); effort = std::move(selected_effort); attachments = A{};
        turn = std::move(next_turn); request = std::move(next_request); conversation = std::move(next_conversation);
        history_used += growth;
        history = std::move(next_history); request_trial = std::move(next_trial); response_done = false; had_tools = false;
        if (!status("streaming")) return output_refusal();
        try { if (hooks.provider_request) hooks.provider_request(outgoing); }
        catch (...) { interrupt_output(); return failure("interrupted", "The admitted provider request could not start"); }
        return admitted_message;
    }
    Reply provider(const J& event) {
        output_failure = OutputFailure::none;
        envelope(event); const auto type = string(event, "type");
        if (type == "connection") {
            shape(event, {"schema", "type", "connection_id", "status", "capabilities"});
            const auto state = string(event, "status");
            if (state != "ready" && state != "disconnected" && state != "expired") refuse("invalid_argument", "Invalid connection status");
            bounded(event.at("capabilities"), Limits::http_json_bytes, Limits::models);
            std::set<std::string> model_ids;
            for (const auto& item : event.at("capabilities").array("capabilities")) {
                shape(item, {"id", "display_name", "efforts", "attachment_types"}); string(item, "id"); string(item, "display_name");
                if (!model_ids.insert(string(item, "id")).second) refuse("invalid_argument", "Duplicate model ID");
                bounded(item.at("efforts"), Limits::http_json_bytes, Limits::model_options);
                bounded(item.at("attachment_types"), Limits::http_json_bytes, Limits::model_options);
                const auto mapped = openai_efforts(string(item, "id"));
                if (mapped.array("efforts").empty()) refuse("invalid_argument", "Model has no reviewed capability mapping");
                for (const J& option : item.at("efforts").array("efforts")) {
                    const auto tag = option.string("effort");
                    if (!effort_tag(tag)) refuse("invalid_argument", "Unsupported reasoning effort tag");
                    if (!mapped.array("efforts").empty() && std::none_of(mapped.array("efforts").begin(), mapped.array("efforts").end(), [&](const J& x) { return x.string("effort") == tag; }))
                        refuse("invalid_argument", "Unsupported model effort combination");
                }
                for (const J& attachment : item.at("attachment_types").array("attachment_types")) attachment.string("attachment type");
            }
            const auto next = string(event, "connection_id");
            if (next != connection || state != "ready") { stop(); reset_conversation(); }
            connection = next; ready = state == "ready"; capabilities = event.at("capabilities");
            if (!status(ready ? "idle" : "disconnected")) return output_refusal();
            return success();
        }
        if (type != "text_delta" && type != "tool_call" && type != "turn_finished") refuse("invalid_argument", "Unknown provider event");
        if (type == "text_delta") shape(event, {"schema", "type", "connection_id", "turn_id", "request_id", "text"});
        else if (type == "turn_finished") shape(event, {"schema", "type", "connection_id", "turn_id", "request_id", "status"}, {"message"});
        else shape(event, {"schema", "type", "connection_id", "turn_id", "request_id", "call_id", "name", "project_id", "revision", "arguments"}, {"plan_id"});
        if (!ready || string(event, "connection_id") != connection) refuse("connection_required", "Connection changed");
        if (turn.empty() || string(event, "turn_id") != turn || string(event, "request_id") != request)
            refuse(type == "tool_call" && !turn.empty() ? "invalid_argument" : "interrupted", "Provider event does not belong to the active request");
        if (type == "text_delta") {
            if (response_done) refuse("interrupted", "Text arrived after response completion");
            const auto delta = string(event, "text", true);
            auto& rows = std::get<A>(history.data);
            if (!rows.empty() && rows.back().get("type").string("type") == "message" && rows.back().get("role").string("role") == "assistant" &&
                rows.back().get("turn_id").string("turn_id") == turn && rows.back().get("request_id").string("request_id") == request) {
                const auto& previous = rows.back().at("text").string("text");
                const auto growth = payload_size(J(delta)) - 2;
                if (growth + held_history() > Limits::history_bytes - history_used) refuse("resource_exhausted", "Conversation text limit exceeded");
                J next = rows.back(); set(next, "text", previous + delta); rows.back() = std::move(next); history_used += growth;
            } else history_item(O{{"type", "message"}, {"role", "assistant"}, {"text", delta}, {"turn_id", turn}, {"request_id", request}});
            emit("message_delta", {{"text", delta}}); return success();
        }
        if (type == "turn_finished") {
            if (response_done) refuse("interrupted", "Response is already terminal");
            const auto result = string(event, "status");
            if (result != "completed" && result != "failed" && result != "interrupted") refuse("invalid_argument", "Invalid terminal status");
            if (result != "completed") { interrupt_output(); return failure("interrupted", "Provider turn did not complete"); }
            response_done = true;
            if (!continue_turn()) return output_refusal();
            return success();
        }
        const auto call = string(event, "call_id");
        const auto binding = json::write(canonical(event));
        if (const auto old = calls.find(call); old != calls.end()) {
            if (old->second.binding != binding) refuse("invalid_argument", "Call ID reused with different content");
            return old->second.reply;
        }
        if (response_done) refuse("interrupted", "Tool arrived after response completion");
        if (!question.empty()) refuse("busy", "Answer the pending question before another tool");
        const bool no_project_question = string(event, "name") == "ask_question" && !live && string(event, "project_id", true).empty();
        if (!no_project_question && (!live || string(event, "project_id") != version.project_id)) refuse("stale_project", "Project changed");
        if (detail::revision(event) != version.revision) refuse("stale_revision", "Project revision changed");
        const auto name = string(event, "name");
        admitting_call = call; admitting_event = event; admission.reset();
        Reply result;
        try { result = tool(event); }
        catch (const Refusal& error) {
            admission.reset();
            if (error.code == "resource_exhausted") throw;
            result = failure(error.code, error.what());
        }
        catch (const std::bad_alloc&) { throw; }
        catch (const std::length_error&) { throw; }
        catch (const std::exception& error) { admission.reset(); result = failure("invalid_argument", error.what()); }
        const bool pending = result.ok && (name == "fit_trial" || name == "ask_question");
        if (!admission) preflight(result, pending);
        const bool failed_publication = output_failure != OutputFailure::none;
        commit_admission(failed_publication && name == "ask_question");
        admitting_call.clear();
        if (failed_publication) return output_refusal();
        had_tools = true;
        if (!safe_emit("tool_result", [&] { return O{{"call_id", call}, {"ok", result.ok}, {"code", result.code}, {"result", parse(result.value)}, {"pending", pending}}; }, &event))
            return output_refusal();
        return result;
    }
};

Controller::Controller(work::Worker& worker, Hooks hooks) : state_(std::make_shared<State>(worker, std::move(hooks))) {}
Controller::~Controller() { state_->open = false; state_->stop(); state_->trial.reset(); }
Reply Controller::attach(Project* project, std::string project_id) {
    if ((project == nullptr) != project_id.empty()) return failure("invalid_argument", "A project requires a session ID");
    if (project && project_id == state_->version.project_id) {
        if (project != state_->live) return failure("stale_project", "A replacement project requires a fresh session ID");
        return success();
    }
    state_->stop(); state_->live = project; state_->version = {std::move(project_id), 0};
    state_->history = A{}; state_->history_used = 2; state_->calls.clear(); state_->cache_used = 2; state_->holds.clear(); state_->answers.clear(); state_->conversation = state_->id("conversation"); state_->emit("state_changed", {{"state", state_->state()}}); return success();
}
Revision Controller::revision() const { return state_->version; }
void Controller::notify_changed() { ++state_->version.revision; state_->stop(); }
Reply Controller::user_command(const JsonText& command) {
    state_->user_scope_committed = false;
    try { return state_->user(parse(command)); }
    catch (const Refusal& error) {
        if (error.code == "resource_exhausted" && state_->user_scope_committed) state_->interrupt_output();
        return failure(error.code, error.what());
    }
    catch (const std::bad_alloc&) { if (state_->user_scope_committed) state_->interrupt_output(); return failure("resource_exhausted", "Assistant publication could not be retained"); }
    catch (const std::length_error&) { if (state_->user_scope_committed) state_->interrupt_output(); return failure("resource_exhausted", "Assistant publication exceeds its capacity"); }
    catch (const std::exception& error) { return failure("invalid_argument", error.what()); }
}
Reply Controller::provider_event(const JsonText& event) {
    bool bound = false;
    try {
        const auto input = parse(event);
        bound = !state_->turn.empty() && has(input, "connection_id") && has(input, "turn_id") && has(input, "request_id") &&
            string(input, "connection_id") == state_->connection && string(input, "turn_id") == state_->turn && string(input, "request_id") == state_->request;
        return state_->provider(input);
    }
    catch (const Refusal& error) {
        if (bound && error.code == "resource_exhausted") state_->interrupt_output();
        return failure(error.code, error.what());
    }
    catch (const std::length_error&) { if (bound) state_->interrupt_output(); return failure("resource_exhausted", "A retaining host exhausted its payload capacity"); }
    catch (const std::bad_alloc&) { if (bound) state_->interrupt_output(); return failure("resource_exhausted", "Assistant output could not be retained"); }
    catch (const std::exception& error) { return failure("invalid_argument", error.what()); }
}
JsonText Controller::state() const { return json::write(state_->state()); }
JsonText Controller::context() const {
    try { const auto context = state_->context(); bounded(context, Limits::context_bytes); return json::write(context); }
    catch (...) { return json::write(O{{"schema", "edi.assistant.context/1"}, {"error", O{{"code", "edi.assistant.resource_exhausted"}, {"message", "Project context exceeds the assistant limit."}}}}); }
}
void Controller::poll() {
    if (state_->plan && state_->plan->approved) {
        const auto now = state_->hooks.monotonic_ms();
        if (now < state_->plan->started || now - state_->plan->started >= state_->plan->max_ms) state_->stop();
    }
}
void Controller::cancel() { state_->stop(); }
}  // namespace edi::assistant
