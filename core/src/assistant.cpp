// SPDX-License-Identifier: BSD-3-Clause
#include "edi/assistant.hpp"

#include <chrono>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>

#include "assistant_json.hpp"
#include "edi/calculation.hpp"
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
    for (const auto& entry : parameter_entries(project)) {
        const Parameter& p = *entry.parameter;
        const auto named = names.find(&p);
        const std::string unique_name = named == names.end() ? std::string() : named->second;
        rows.emplace_back(O{{"path", entry.path}, {"unique_name", unique_name}, {"value", p.value.get()},
                            {"uncertainty", p.uncertainty.get() ? J(*p.uncertainty.get()) : J(nullptr)},
                            {"free", p.free.get()}, {"dependence", dependence(p.dependence)},
                            {"unit", p.spec ? p.spec->units : "dimensionless"}});
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
    std::string phase = "disconnected", connection, turn, request, model, effort, text, active_job, question;
    J capabilities = A{}, history = A{}, attachments = A{};
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
        std::string id, group;
        std::shared_ptr<Project> project;
        std::uint64_t revision = 0;
        double baseline = std::numeric_limits<double>::quiet_NaN();
        std::optional<FitReport> report;
        std::unique_ptr<FitJob> job;
    };
    std::shared_ptr<Trial> trial;
    struct Cached { std::string binding; Reply reply; };
    std::map<std::string, Cached> calls;

    State(work::Worker& runner, Hooks services) : worker(runner), hooks(std::move(services)) {
        if (!hooks.monotonic_ms) hooks.monotonic_ms = [] {
            return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count());
        };
    }
    std::string id(const char* kind) { return std::string(kind) + '-' + std::to_string(++serial); }
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
    void emit(const std::string& type, O fields = {}) {
        if (!open || !hooks.event) return;
        fields.emplace_back("schema", "edi.assistant/1"); fields.emplace_back("type", type);
        fields.emplace_back("event_id", std::to_string(++event_serial));
        fields.emplace_back("connection_id", connection); fields.emplace_back("turn_id", turn);
        fields.emplace_back("project_id", version.project_id); fields.emplace_back("revision", std::to_string(version.revision));
        hooks.event(json::write(fields));
    }
    void status(std::string next) { phase = std::move(next); emit("state_changed", {{"state", state()}}); }
    void history_item(J item) { std::get<A>(history.data).push_back(std::move(item)); }
    void stop() {
        turn.clear(); request.clear(); plan.reset(); calls.clear();
        if (trial && trial->job && trial->job->running()) { trial->job->cancel(); status("cancelling"); }
        else { trial.reset(); active_job.clear(); status(ready ? "idle" : "disconnected"); }
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
        if (hooks.monotonic_ms() - plan->started >= plan->max_ms) {
            stop(); refuse("out_of_scope", "The approved elapsed-time budget is exhausted");
        }
    }
    void send_request() {
        request = id("request"); response_done = false; had_tools = false;
        O out{{"schema", "edi.assistant/1"}, {"type", "request"}, {"connection_id", connection},
              {"turn_id", turn}, {"request_id", request}, {"model", model}, {"text", text},
              {"attachments", attachments}, {"context", context()}, {"history", history}, {"tools", manifest()}};
        if (!effort.empty()) out.emplace_back("effort", effort);
        status("streaming");
        if (hooks.provider_request) hooks.provider_request(json::write(out));
    }
    void continue_turn() {
        if (!response_done || !active_job.empty() || (plan && !plan->approved)) return;
        if (had_tools && !turn.empty()) send_request();
        else { turn.clear(); request.clear(); status(ready ? "idle" : "disconnected"); }
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
        const auto message = hooks.apply(edit, structural);
        if (!message.empty()) refuse("apply_refused", message);
        ++version.revision; stamps();
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
            plan = std::move(next); stamps();
            J shown = args; set(shown, "plan_id", plan->id);
            emit("plan_proposed", {{"plan", shown}, {"plan_id", plan->id}}); status("awaiting_approval");
            return success(O{{"plan_id", plan->id}});
        }
        static const std::set<std::string> mutations{"set_parameters", "set_free", "begin_trial", "fit_trial", "evaluate_trial", "discard_trial"};
        if (!mutations.count(name)) refuse("unknown_tool", "Unknown tool: " + name);
        approved(event);
        if (name == "set_parameters" || name == "set_free") {
            if (!active_job.empty()) refuse("busy", "A fit is running");
            Project& target = trial ? *trial->project : *live;
            const auto rows = paths(target);
            const auto& allowed = trial ? plan->groups.at(trial->group) : plan->allowed;
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
                else flags.emplace_back(unique_name, row.at("free").boolean("free"));
            }
            if (seen.empty()) refuse("invalid_argument", "Empty parameter batch");
            Project validated = target;
            if (values) Edit::parameter_values(validated, edits)();
            else Edit::set_free(validated, flags)();
            complete_relations(validated);
            const Edit change = values ? Edit::parameter_values(target, std::move(edits)) : Edit::set_free(target, std::move(flags));
            if (trial) { change(); ++trial->revision; }
            else apply(change);
            O result{{"revision", std::to_string(version.revision)}};
            if (trial) { result.emplace_back("trial_id", trial->id); result.emplace_back("candidate_revision", std::to_string(trial->revision)); }
            return success(result);
        }
        if (name == "begin_trial") {
            shape(args, {"group_id"}); const auto group = string(args, "group_id");
            if (trial || !active_job.empty()) refuse("busy", "A trial already exists");
            if (!plan->groups.count(group)) refuse("out_of_scope", "Unknown parameter group");
            if (plan->trials >= plan->max_trials) refuse("out_of_scope", "Trial budget exhausted");
            auto next = std::make_shared<Trial>();
            next->id = id("trial"); next->group = group; next->project = std::make_shared<Project>(*live);
            if (live->fit_result.held() && live->fit_result.objective_name == "chi_square") next->baseline = live->fit_result.objective_value;
            trial = std::move(next); ++plan->trials;
            return success(O{{"trial_id", trial->id}});
        }
        shape(args, {"trial_id"});
        if (!trial || string(args, "trial_id") != trial->id) refuse("unknown_trial", "Unknown trial");
        if (!active_job.empty()) refuse("busy", "Wait for the fit to settle");
        if (name == "discard_trial") { trial.reset(); return success(O{{"discarded", true}}); }
        if (name == "fit_trial") {
            if (trial->report) refuse("invalid_argument", "This trial has already been fitted");
            const auto mode = effective_fitting_mode(*trial->project);
            if (mode == "sequential" || mode == "independent")
                refuse("out_of_scope", "Assistant scan trials require the pending checked result-artifact unit");
            const auto max_iterations = static_cast<int>(plan->max_iterations);
            if (trial->project->minimizer_max_iterations == 0 || trial->project->minimizer_max_iterations > max_iterations)
                trial->project->minimizer_max_iterations = max_iterations;
            const auto job_id = id("job"); active_job = job_id;
            const std::weak_ptr<State> weak = shared_from_this();
            const std::weak_ptr<Trial> weak_candidate = trial;
            FitJob::Hooks callbacks;
            callbacks.iterated = [weak, job_id](const IterationRecord& iteration) {
                if (const auto state = weak.lock(); state && state->open && state->active_job == job_id)
                    state->emit("job_progress", {{"job_id", job_id}, {"objective", iteration.reduced_chi_square}});
            };
            callbacks.finished = [weak, weak_candidate, job_id](const FitReport& report) {
                const auto state = weak.lock();
                const auto candidate = weak_candidate.lock();
                if (!state || !candidate || !state->open || state->active_job != job_id) return;
                candidate->report = report; state->active_job.clear();
                state->emit("job_finished", {{"job_id", job_id}, {"adopted", report.adopted()}, {"message", report.refusal},
                                             {"converged", report.result && report.result->converged}});
                if (state->turn.empty()) { state->trial.reset(); state->status(state->ready ? "idle" : "disconnected"); }
                else { state->status("streaming"); state->continue_turn(); }
            };
            trial->job = std::make_unique<FitJob>(*trial->project, worker, std::move(callbacks));
            if (!trial->job->start()) { active_job.clear(); refuse("busy", "The fit could not start"); }
            emit("job_started", {{"job_id", job_id}, {"trial_id", trial->id}}); status("executing");
            return success(O{{"job_id", job_id}});
        }
        if (!trial->report) refuse("busy", "Fit the trial before evaluating it");
        const auto candidate = trial;
        const auto& report = *candidate->report;
        bool accepted = report.status == FitStatus::DONE && report.result && report.result->converged;
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
        if (accepted) apply(Edit::assistant_result(*live, candidate->project));
        O result{{"accepted", accepted}, {"reason", reason}, {"trial_id", candidate->id},
                 {"revision", std::to_string(version.revision)}, {"diagnostics", diagnostics(candidate->project.get())}};
        emit("trial_finished", {{"result", result}}); trial.reset();
        return success(result);
    }
    Reply user(const J& command) {
        envelope(command); const auto type = string(command, "type");
        if (type == "cancel") { shape(command, {"schema", "type"}); stop(); return success(); }
        if (type == "approve_plan") {
            shape(command, {"schema", "type", "plan_id", "project_id", "revision"});
            if (string(command, "project_id") != version.project_id) refuse("stale_project", "Project changed");
            if (detail::revision(command) != version.revision) refuse("stale_revision", "Project revision changed");
            if (!plan || string(command, "plan_id") != plan->id) refuse("approval_required", "Plan is no longer pending");
            current(); plan->approved = true; plan->started = hooks.monotonic_ms();
            emit("plan_approved", {{"plan_id", plan->id}}); status("streaming"); continue_turn(); return success();
        }
        if (type == "answer") {
            shape(command, {"schema", "type", "question_id", "answer"});
            if (question.empty() || string(command, "question_id") != question) refuse("invalid_argument", "No matching question");
            emit("question_answered", {{"question_id", question}, {"answer", string(command, "answer", true)}});
            question.clear(); continue_turn(); return success();
        }
        if (type != "message") refuse("invalid_argument", "Unknown user command");
        shape(command, {"schema", "type", "text", "connection_id", "model"}, {"effort", "attachments"});
        if (!ready || string(command, "connection_id") != connection) refuse("connection_required", "Connect a provider first");
        if (!turn.empty() || !active_job.empty()) refuse("busy", "A conversation turn is running");
        const auto selected = string(command, "model");
        const auto selected_effort = has(command, "effort") ? string(command, "effort") : "";
        bool supported = false;
        for (const J& item : capabilities.array("capabilities")) if (string(item, "id") == selected) {
            supported = selected_effort.empty();
            for (const J& option : item.at("efforts").array("efforts")) if (option.string("effort") == selected_effort) supported = true;
        }
        if (!supported) refuse("invalid_argument", "Model or effort is not available");
        if (has(command, "attachments") && !command.at("attachments").array("attachments").empty())
            refuse("out_of_scope", "Attachment transfer requires the pending selected-handle unit");
        text = string(command, "text"); model = selected; effort = selected_effort;
        attachments = A{}; turn = id("turn");
        history_item(O{{"type", "message"}, {"role", "user"}, {"text", text}}); send_request();
        return success(O{{"turn_id", turn}, {"request_id", request}});
    }
    Reply provider(const J& event) {
        envelope(event); const auto type = string(event, "type");
        if (type == "connection") {
            shape(event, {"schema", "type", "connection_id", "status", "capabilities"});
            const auto state = string(event, "status");
            if (state != "ready" && state != "disconnected" && state != "expired") refuse("invalid_argument", "Invalid connection status");
            for (const auto& item : event.at("capabilities").array("capabilities")) {
                shape(item, {"id", "display_name", "efforts", "attachment_types"}); string(item, "id"); string(item, "display_name");
                for (const J& effort_value : item.at("efforts").array("efforts")) effort_value.string("effort");
                for (const J& attachment : item.at("attachment_types").array("attachment_types")) attachment.string("attachment type");
            }
            const auto next = string(event, "connection_id");
            if (next != connection || state != "ready") stop();
            connection = next; ready = state == "ready"; capabilities = event.at("capabilities");
            status(ready ? "idle" : "disconnected"); return success();
        }
        if (type != "text_delta" && type != "tool_call" && type != "turn_finished") refuse("invalid_argument", "Unknown provider event");
        if (type == "text_delta") shape(event, {"schema", "type", "connection_id", "turn_id", "request_id", "text"});
        else if (type == "turn_finished") shape(event, {"schema", "type", "connection_id", "turn_id", "request_id", "status"}, {"message"});
        else shape(event, {"schema", "type", "connection_id", "turn_id", "request_id", "call_id", "name", "project_id", "revision", "arguments"}, {"plan_id"});
        if (!ready || string(event, "connection_id") != connection) refuse("connection_required", "Connection changed");
        if (turn.empty() || string(event, "turn_id") != turn || string(event, "request_id") != request)
            refuse(type == "tool_call" && !turn.empty() ? "invalid_argument" : "interrupted", "Provider event does not belong to the active request");
        if (type == "text_delta") {
            const auto delta = string(event, "text", true);
            emit("message_delta", {{"text", delta}});
            history_item(O{{"type", "message"}, {"role", "assistant"}, {"text", delta}}); return success();
        }
        if (type == "turn_finished") {
            const auto result = string(event, "status");
            if (result != "completed" && result != "failed" && result != "interrupted") refuse("invalid_argument", "Invalid terminal status");
            if (result != "completed") { stop(); status("interrupted"); return failure("interrupted", "Provider turn did not complete"); }
            response_done = true; continue_turn(); return success();
        }
        const auto call = string(event, "call_id");
        const auto binding = json::write(event);
        if (const auto old = calls.find(call); old != calls.end()) {
            if (old->second.binding != binding) refuse("invalid_argument", "Call ID reused with different content");
            return old->second.reply;
        }
        if (response_done) refuse("interrupted", "Tool arrived after response completion");
        if (!live || string(event, "project_id") != version.project_id) refuse("stale_project", "Project changed");
        if (detail::revision(event) != version.revision) refuse("stale_revision", "Project revision changed");
        Reply result;
        try { result = tool(event); }
        catch (const Refusal& error) { result = failure(error.code, error.what()); }
        catch (const std::exception& error) { result = failure("invalid_argument", error.what()); }
        calls.emplace(call, Cached{binding, result}); had_tools = true;
        history_item(O{{"type", "tool_call"}, {"call_id", call}, {"name", string(event, "name")}, {"arguments", event.at("arguments")}});
        history_item(O{{"type", "tool_result"}, {"call_id", call}, {"ok", result.ok}, {"code", result.code}, {"result", parse(result.value)}});
        emit("tool_result", {{"call_id", call}, {"ok", result.ok}, {"code", result.code}, {"result", parse(result.value)}});
        return result;
    }
};

Controller::Controller(work::Worker& worker, Hooks hooks) : state_(std::make_shared<State>(worker, std::move(hooks))) {}
Controller::~Controller() { state_->open = false; state_->stop(); }
Reply Controller::attach(Project* project, std::string project_id) {
    if ((project == nullptr) != project_id.empty()) return failure("invalid_argument", "A project requires a session ID");
    if (project && project_id == state_->version.project_id) {
        if (project != state_->live) return failure("stale_project", "A replacement project requires a fresh session ID");
        return success();
    }
    state_->stop(); state_->live = project; state_->version = {std::move(project_id), 0};
    state_->history = A{}; state_->emit("state_changed", {{"state", state_->state()}}); return success();
}
Revision Controller::revision() const { return state_->version; }
void Controller::notify_changed() { ++state_->version.revision; state_->stop(); }
Reply Controller::user_command(const JsonText& command) {
    try { return state_->user(parse(command)); }
    catch (const Refusal& error) { return failure(error.code, error.what()); }
    catch (const std::exception& error) { return failure("invalid_argument", error.what()); }
}
Reply Controller::provider_event(const JsonText& event) {
    try { return state_->provider(parse(event)); }
    catch (const Refusal& error) { return failure(error.code, error.what()); }
    catch (const std::exception& error) { return failure("invalid_argument", error.what()); }
}
JsonText Controller::state() const { return json::write(state_->state()); }
JsonText Controller::context() const { return json::write(state_->context()); }
void Controller::poll() {
    if (state_->plan && state_->plan->approved && state_->hooks.monotonic_ms() - state_->plan->started >= state_->plan->max_ms)
        state_->stop();
}
void Controller::cancel() { state_->stop(); }
}  // namespace edi::assistant
