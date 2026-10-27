// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <array>
#include <QString>
#include <stdexcept>
#include <string_view>
namespace edi_app {
inline constexpr std::array<const char*,19> action_errors{{"project_required","input_required","input_unavailable","unsupported_input","target_unavailable","data_already_present","type_locked","unsupported_type","reader_refused","operation_superseded","control_unavailable","invalid_range","purpose_too_long","workflow_page_unavailable","main_sidebar_unavailable","extra_sidebar_unavailable","control_delivery_unconfirmed","control_commit_unconfirmed","manual_input_pending"}};
inline constexpr std::array<const char*,18> action_fields{{"project","file_id","experiment","axis","token","offset","max_bytes","structure","atom","field","value","region","relation","phase","purpose","parameter","background","fit"}};
enum class ControlCause { None, Unavailable, WorkflowPage, MainSidebar, ExtraSidebar, Delivery, Commit, ManualInput, Superseded };
enum class ControlField { None, Parameter, Background, Relation, Project, Structure, Experiment, Phase, File, Fit };
inline constexpr const char* control_error(ControlCause cause) noexcept {
    switch(cause) {
    case ControlCause::Unavailable:return action_errors[10];
    case ControlCause::WorkflowPage:return action_errors[13];
    case ControlCause::MainSidebar:return action_errors[14];
    case ControlCause::ExtraSidebar:return action_errors[15];
    case ControlCause::Delivery:return action_errors[16];
    case ControlCause::Commit:return action_errors[17];
    case ControlCause::ManualInput:return action_errors[18];
    case ControlCause::Superseded:return action_errors[9];
    case ControlCause::None:return nullptr;
    }
    return nullptr;
}
inline constexpr const char* control_field(ControlField field) noexcept {
    switch(field) {
    case ControlField::Parameter:return action_fields[15];
    case ControlField::Background:return action_fields[16];
    case ControlField::Relation:return action_fields[12];
    case ControlField::Project:return action_fields[0];
    case ControlField::Structure:return action_fields[7];
    case ControlField::Experiment:return action_fields[2];
    case ControlField::Phase:return action_fields[13];
    case ControlField::File:return action_fields[1];
    case ControlField::Fit:return action_fields[17];
    case ControlField::None:return nullptr;
    }
    return nullptr;
}
struct ControlDiagnostic {
    ControlCause cause=ControlCause::None;
    ControlField field=ControlField::None;
    explicit constexpr operator bool() const noexcept {return control_error(cause) && control_field(field);}
    void latch(ControlCause first,ControlField target) noexcept {
        if(!*this && control_error(first) && control_field(target)){cause=first;field=target;}
    }
};
class ControlInputRefusal final : public std::exception {
public:
    ControlInputRefusal(ControlCause cause,const char* message) noexcept:cause(cause),message_(message){}
    const char* what() const noexcept override{return message_;}
    const ControlCause cause;
private:
    const char* message_;
};
#define EDI_ASSISTANT_CONTROL_GUIDANCE " Closed action_error/action_field control failures identify an observed original native UI prerequisite or confirmation limit, not scientific invalidity or completion. workflow_page_unavailable, main_sidebar_unavailable and extra_sidebar_unavailable identify the failed original navigation prerequisite; control_unavailable identifies an unreachable original control, control_delivery_unconfirmed or control_commit_unconfirmed an unconfirmed original input, and manual_input_pending an existing user draft. Inspect actual current state and the retained completed prefix; preserve applied/published/uncertain facts and ordinary Undo. Report the actual limit. Never replay partial/uncertain or unavailable work, switch modes, bypass controls, recreate/discard the project or change scientific/default values to force success. This diagnostic grants no automatic retry or navigation authority. Ask only for genuinely missing information or a real required user action, without repeating permission for delegated work."
inline constexpr std::string_view control_failure_guidance = EDI_ASSISTANT_CONTROL_GUIDANCE;
class ActionRefusal final : public std::invalid_argument {
public:
    ActionRefusal(const char* error,const char* field):std::invalid_argument("The original app action was refused"),error(error),field(field){}
    const char* const error;
    const char* const field;
};
inline bool structure_app_action(const QString& name) {
    return name=="create_structure" || name=="edit_structure" || name=="edit_atom";
}
inline bool individual_app_action(const QString& name) {
    return name=="edit_experiment" || structure_app_action(name) || name=="load_structure" || name=="create_experiment" || name=="set_experiment_type" || name=="load_data";
}
} // namespace edi_app
