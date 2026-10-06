// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SCAN_HPP
#define EDI_SCAN_HPP

#include <cstdint>
#include <map>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
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

/// A number as `analysis/results.csv` spells it: the whole token, in the C locale whatever the process locale is.
/// False for anything else (an empty or partial token, a decimal comma).
bool parse_scan_number(std::string_view token, double& value);

/// One fitted parameter's two columns in `analysis/results.csv`.
struct ScanParameterColumns {
    std::string name;
    std::size_t value = 0;
    std::size_t uncertainty = 0;
};

/// What `analysis/results.csv` records, checked, with one small entry per dataset: no row's parameter cells are kept
/// (`read_scan_row` reads one row at its offset). The header must be crysta's: `file_path`,
/// `fit_result.reduced_chi_square`, `fit_result.success`, `fit_result.iterations`, one column per extract rule's
/// target in rule order, then each parameter's value and `.uncertainty`, every name once. Every complete row must
/// have the header's width, name a file of the scan once, and carry finite numbers (uncertainties not negative). A
/// last line without its line break is a row still being written and is left out. Anything else refuses the whole
/// file: `error` says why and no row is kept.
struct ScanResultIndex {
    struct Row {
        std::int64_t offset = -1;  ///< where the row starts in the file; -1: the dataset has no row
        double reduced_chi_square = 0.0;
        bool converged = false;
        int iterations = 0;
        std::vector<std::string> extracted;  ///< the extract rules' cells, in rule order
    };
    std::string error;
    std::vector<std::string> header;
    std::vector<ScanParameterColumns> parameters;
    std::vector<Row> rows;      ///< by dataset place
    std::int64_t end = 0;       ///< the offset after the last complete row (0: no file)
    std::size_t fitted = 0;     ///< datasets with a row
};
ScanResultIndex index_scan_results(const Project& project, const ScanDatasets& datasets);

/// Checks one row's cells against an accepted index's header (as `index_scan_results` checks a row) and returns its
/// facts with the place of the dataset it names; throws, saying why, for a row that does not belong.
using ScanPlaces = std::unordered_map<std::string, std::size_t>;
/// Each dataset's place by its file name.
ScanPlaces scan_places(const ScanDatasets& datasets);
std::pair<std::size_t, ScanResultIndex::Row> scan_row_facts(const Project& project, const ScanPlaces& places,
                                                           const ScanResultIndex& index,
                                                           const std::vector<std::string>& cells);

/// The cells of the row that starts at `offset`; throws when the file has no complete row there.
std::vector<std::string> read_scan_row(const Project& project, std::int64_t offset);

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
