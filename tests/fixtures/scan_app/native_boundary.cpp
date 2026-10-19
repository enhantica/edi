// Observe the SDK's compiled scan object without replacing its loop or reader.
#include <filesystem>

#include "crysta/analysis.hpp"
#include "scan_contract_work.hpp"

// The scan's per-file entry is internal to the SDK, so its header is not installed.
namespace crysta {
FitResultBase fit_scan_file(Project&, const IterationCallback&, const CancelCallback&);
}

extern crysta::FitResultBase scan_contract_real_sequential(crysta::Project&,
                                                           const crysta::IterationCallback&,
                                                           const crysta::CancelCallback&,
                                                           const crysta::FileCompleteCallback&,
                                                           const crysta::FileFittedCallback&,
                                                           const crysta::FileResultCallback&);

crysta::FitResultBase scan_contract_optimizer(crysta::Project& project,
                                              const crysta::IterationCallback& iteration,
                                              const crysta::CancelCallback& cancel) {
    return crysta::fit_scan_file(project, iteration, cancel);
}

extern crysta::PdDataBase scan_contract_real_dataset_read(const std::string&);
extern crysta::FitResultBase scan_contract_real_fit(crysta::Project&,
                                                    const crysta::IterationCallback&,
                                                    const crysta::CancelCallback&);
void scan_contract_before_dataset_read(const std::string&);
void scan_contract_file_fitted_observed(const std::string&);
void scan_contract_file_result_observed(const std::string&);

namespace crysta {
PdDataBase read_sequential_scan_data(const std::string& path) {
    scan_contract_before_dataset_read(path);
    return scan_contract_real_dataset_read(path);
}
FitResultBase fit_scan_file(Project& project, const IterationCallback& iteration,
                            const CancelCallback& cancel) {
    scan_contract_work("", project);
    return scan_contract_real_fit(project, iteration, cancel);
}

FitResultBase sequential_fit_project(Project& project, const IterationCallback& iteration,
                                     const CancelCallback& cancel,
                                     const FileCompleteCallback& complete,
                                     const FileFittedCallback& fitted,
                                     const FileResultCallback& file_result) {
    const FileCompleteCallback observed = [&](const std::vector<std::string>& row) {
        if (complete) complete(row);
        scan_contract_work_receipt(std::filesystem::path(row.at(0)).filename().string());
    };
    const FileResultCallback observed_result = [&](const std::vector<std::string>& row,
                                                   const FitResultBase& result) {
        if (file_result) file_result(row, result);
        scan_contract_file_result_observed(std::filesystem::path(row.at(0)).filename().string());
        scan_contract_file_completed(std::filesystem::path(row.at(0)).filename().string());
    };
    const FileFittedCallback observed_fitted = [&](const std::vector<std::string>& row,
                                                   const Project& dataset) {
        if (fitted) fitted(row, dataset);
        scan_contract_file_fitted_observed(std::filesystem::path(row.at(0)).filename().string());
    };
    return scan_contract_real_sequential(project, iteration, cancel, observed, observed_fitted,
                                         observed_result);
}
}  // namespace crysta
