// Observe the SDK's compiled scan object without replacing its loop or reader.
#include <filesystem>

#include "crysta/analysis.hpp"
#include "scan_contract_work.hpp"

extern crysta::FitResultBase scan_contract_real_sequential(crysta::Project&,
                                                           const crysta::IterationCallback&,
                                                           const crysta::CancelCallback&,
                                                           const crysta::FileCompleteCallback&);

crysta::FitResultBase scan_contract_optimizer(crysta::Project& project,
                                              const crysta::IterationCallback& iteration,
                                              const crysta::CancelCallback& cancel,
                                              const crysta::FileCompleteCallback& complete) {
    scan_contract_work("", project);
    return crysta::fit_project(project, iteration, cancel, complete);
}

namespace crysta {
FitResultBase sequential_fit_project(Project& project, const IterationCallback& iteration,
                                     const CancelCallback& cancel,
                                     const FileCompleteCallback& complete) {
    const FileCompleteCallback observed = [&](const std::vector<std::string>& row) {
        if (complete) complete(row);
        scan_contract_work_receipt(std::filesystem::path(row.at(0)).filename().string());
        scan_contract_file_completed(std::filesystem::path(row.at(0)).filename().string());
    };
    return scan_contract_real_sequential(project, iteration, cancel, observed);
}
}  // namespace crysta
