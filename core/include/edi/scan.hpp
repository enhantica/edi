// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SCAN_HPP
#define EDI_SCAN_HPP

#include <map>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

/// A scan project's datasets, read for viewing one at a time: the files crysta's sequential driver fits, in its
/// order, the measured pattern and extracted values of one of them, and the rows the driver wrote to
/// `analysis/results.csv`. Listing reads only the directory; no data file is opened until one is asked for.
struct ScanDatasets {
    std::string directory;           ///< The scan's data directory, resolved as the driver resolves it.
    std::vector<std::string> files;  ///< The file names in fitting order.
};

/// The datasets of `project`'s declared scan (crysta::sequential_scan_files). Throws with the driver's message on
/// an undeclared scan, a project with no directory, a missing directory or no matching file.
ScanDatasets scan_datasets(const Project& project);

/// One dataset's measured pattern, read as the driver reads it, on the axis of `mode`.
PdDataBase read_scan_dataset(const std::string& directory, const std::string& file, BeamModeEnum mode);

/// The values the scan's extract rules take from one dataset file, in rule order.
std::vector<std::string> scan_extract_values(const Project& project, const std::string& directory,
                                             const std::string& file);

/// The rows of `analysis/results.csv`: its header, and each row's cells by the file name it records. Empty when
/// the file does not exist yet; a row whose cell count differs from the header's is left out.
struct ScanResults {
    std::vector<std::string> header;
    std::map<std::string, std::vector<std::string>> rows;
};
ScanResults read_scan_results(const Project& project);

/// The header and the last row of `analysis/results.csv`, read from the file's two ends, so a scan in progress
/// takes each new row without reading the rows before it. Empty when there is no complete row.
ScanResults read_last_scan_result(const Project& project);

/// The template dataset (`_sequential_fit.template_file`): `file` must be one of the scan's files as its listing
/// names them. Throws, naming the file, for anything else (crysta::check_sequential_template_file); reads no file.
void check_scan_template_file(const Project& project, const std::string& file);

/// Makes `file` the template dataset: the template experiment's data becomes that file's, read as the driver reads
/// it, and `_sequential_fit.template_file` names it. No parameter changes; a refusal changes nothing.
void set_scan_template_file(Project& project, const std::string& file);

/// The `analysis/results.csv` column of a parameter's unique name: the same name, except that an instrument
/// parameter drops its `calib_` or `setup_` prefix, as diffraction-lib's results name it (`d20.instrument.twotheta_offset`).
std::string scan_results_column(const std::string& unique_name);

/// The unit of an extract rule's target, as a column heading shows it (`K` for a temperature), or empty.
std::string scan_target_unit(const std::string& target);

}  // namespace edi

#endif  // EDI_SCAN_HPP
