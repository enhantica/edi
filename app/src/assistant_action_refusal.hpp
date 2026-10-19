// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <array>
#include <QString>
#include <stdexcept>
namespace edi_app {
inline constexpr std::array<const char*,12> action_errors{{"project_required","input_required","input_unavailable","unsupported_input","target_unavailable","data_already_present","type_locked","unsupported_type","reader_refused","operation_superseded","control_unavailable","invalid_range"}};
inline constexpr std::array<const char*,7> action_fields{{"project","file_id","experiment","axis","token","offset","max_bytes"}};
class ActionRefusal final : public std::invalid_argument {
public:
    ActionRefusal(const char* error,const char* field):std::invalid_argument("The original app action was refused"),error(error),field(field){}
    const char* const error;
    const char* const field;
};
inline bool individual_app_action(const QString& name) {
    return name=="load_structure" || name=="create_experiment" || name=="set_experiment_type" || name=="load_data";
}
} // namespace edi_app
