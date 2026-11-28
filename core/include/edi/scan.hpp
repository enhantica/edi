// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SCAN_HPP
#define EDI_SCAN_HPP

#include <cstdint>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include "edi/model.hpp"
#include "edi/scan_views.hpp"

namespace edi {

/// A scan project's datasets, read for viewing one at a time: the files crysta's sequential driver fits, in its
/// order, the measured pattern and extracted values of one of them, and the rows the driver wrote to
/// `analysis/results.csv`. Listing reads only the directory; no data file is opened until one is asked for.
struct ScanDatasets {
    std::string directory;           ///< The scan's data directory, resolved as the driver resolves it.
    std::vector<std::string> files;  ///< The file names in fitting order; a series of joint fits' point keys.
    /// A series of joint fits (several experiments, one file pattern each): its experiments in project order and,
    /// per point, one file per experiment. Empty for a scan of one experiment.
    std::vector<std::string> experiments;
    std::vector<std::vector<std::string>> point_files;
    /// A series' incomplete points: some experiment has no file for the point, or two. Listed with the files the
    /// point has and why, never fitted.
    struct IncompletePoint {
        std::string key;
        std::vector<std::string> files;
        std::string reason;
    };
    std::vector<IncompletePoint> incomplete;
    bool joint() const { return !experiments.empty(); }
};

/// The datasets of `project`'s declared scan (crysta::sequential_scan_files). Throws with the driver's message on
/// an undeclared scan, a project with no directory, a missing directory or no matching file.
ScanDatasets scan_datasets(const Project& project);

/// Finishes or undoes a parametric fit's publication of `directory`'s results that a crash interrupted (crysta
/// ADR-0136); nothing when none was. Throws when the folder cannot be changed.
void recover_scan_publication(const std::string& directory);

/// Every file of the scan's folder its datasets name: a scan's files, or a series' files of every point, incomplete
/// points included. What copying a linked scan into the project carries and what its size counts (ADR-0088 point 3).
std::vector<std::string> scan_data_files(const ScanDatasets& datasets);

/// ADR-0088 point 4: for each point key of a series of joint fits, whether a file it was fitted from has changed since:
/// a `results_experiments.csv` row of the point records a size or modification time the file no longer has, or the
/// file is gone. A point without rows is not changed. Only the named points' files are looked at; nothing is read
/// from them. All false for a scan of one experiment or without the file.
std::vector<bool> scan_points_changed(const Project& project, const ScanDatasets& datasets,
                                      const std::vector<std::string>& points);

/// The scan's template dataset in effect: `_sequential_fit.template_file` when declared, else the first file of the
/// scan's listing; empty when there is neither. A scan's report is this dataset's, and its fit record keeps this
/// dataset's correlation pairs (edi ADR-0034), so the report shows the same pairs in the app and from the saved files.
std::string effective_scan_template_file(const Project& scan, const ScanDatasets& datasets);
/// The same, listing the scan's files itself; the declared file, or empty, when they cannot be listed.
std::string effective_scan_template_file(const Project& scan);

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

/// One agreement-factor column of `analysis/results.csv` (`fit_result.r_*`): a value with no s.u. column.
struct ScanFactorColumn {
    std::string name;
    std::size_t value = 0;
};

/// A recorded `results.csv` value as the Evolution view shows it: an agreement factor is kept as a fraction and shown
/// in percent (ADR-0089); χ² and parameters stay as recorded.
double scan_display_value(const std::string& name, double recorded);

/// The largest magnitude a chart point may have, on every route that draws one.
inline constexpr double kScanChartLimit = 1e300;

/// What `analysis/results.csv` records, checked, with one small entry per dataset: no row's parameter cells are kept
/// (`read_scan_row` reads one row at its offset). The header must be crysta's: `file_path`,
/// `fit_result.reduced_chi_square`, `fit_result.success`, `fit_result.iterations`, one column per extract rule's
/// target in rule order, then each parameter's value and `.uncertainty`, and optional fit-condition columns, every name once. Every complete row must
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
        std::string termination;  ///< why its fit stopped, from the result row, or a legacy ledger; empty when not recorded
        /// From crysta's `analysis/scan-notes.csv`: the file's rows skipped for a negative intensity, whether the
        /// whole file was skipped for having no intensity above zero (it then has no row), and why its fit refused
        /// (its row is a failed one, with `nan` where the fit produced nothing).
        std::size_t negative_points = 0;
        bool skipped = false;
        std::string refusal;
        bool noted = false;  ///< the notes file has a row for it
    };
    std::string error;
    std::vector<std::string> header;
    /// The columns, resolved by name: the file, χ², success and iteration count; each extract rule's (its target's
    /// column, else its id's; -1 when the file has none); the parameters' value/uncertainty pairs.
    std::size_t file = 0, chi = 0, success = 0, iterations = 0;
    /// The scan directory as crysta writes it before each file name (`<data_dir>/`).
    std::string directory;
    std::vector<std::ptrdiff_t> extract;
    std::vector<ScanParameterColumns> parameters;
    /// Each point's agreement factors, in the file's order; none in an older file.
    std::vector<ScanFactorColumn> factors;
    /// The fixed inputs a point's fit used (crysta ADR-0136 decision 9): `input.<column>` cells after every other
    /// column, a value without an s.u., by the parameter's results column name (the `input.` taken off).
    std::vector<ScanFactorColumn> inputs;
    std::vector<Row> rows;      ///< by dataset place
    std::int64_t end = 0;       ///< the offset after the last complete row (0: no file)
    std::size_t fitted = 0;     ///< datasets with a row
    std::size_t skipped = 0;    ///< datasets skipped for having no intensity above zero
    std::int64_t notes_end = 0; ///< the offset after the last complete notes line read (0: none read)
};
/// A results file that is there must read whole; `writing`: a run is appending to it, so a last line still being
/// written is left out rather than refused.
ScanResultIndex index_scan_results(const Project& project, const ScanDatasets& datasets, bool writing = false);
/// As above, with the datasets' places a caller already holds (`scan_places`), so they are not built again.
ScanResultIndex index_scan_results(const Project& project, const ScanDatasets& datasets,
                                   const std::unordered_map<std::string, std::size_t>& places, bool writing = false);

/// Checks one row's cells against an accepted index's header (as `index_scan_results` checks a row) and returns its
/// facts with the place of the dataset it names; throws, saying why, for a row that does not belong.
using ScanPlaces = std::unordered_map<std::string, std::size_t>;
/// Each dataset's place by its file name.
ScanPlaces scan_places(const ScanDatasets& datasets);
/// Whether a scan state file (results.csv, results-provenance.csv, scan-notes.csv) is there. Absent is allowed; a
/// path that exists must be a regular file or a link to one. Anything else throws std::invalid_argument, starting
/// with `label`, rather than reading as no state or as an empty file; crysta applies the same rule. Every reader
/// of those files asks this before it opens one.
bool scan_state_present(const std::filesystem::path& path, const std::string& label);
/// crysta's `analysis/scan-notes.csv` (file_path, negative_points, skipped_dataset, refusal), read from byte
/// `from` onto `index`; returns the offset after the last complete line. A file that is there must be whole and
/// well formed: the header, four cells a row, negative_points a decimal integer of at most 12 digits,
/// skipped_dataset True or False, a scan file named once. Anything else throws std::invalid_argument saying why,
/// since the skipped and refused files cannot then be known. `writing`: a last line still being written is left
/// for the next read. The CLI (`edi fit`) and crysta's resume read the file by the same rule.
std::int64_t read_scan_notes(const Project& project, const ScanPlaces& places, ScanResultIndex& index,
                             std::int64_t from, bool writing);
/// What a scan's results and notes say about its skipped and refused files, as `edi fit` reports them: read by the
/// results index, so by the same rule. Throws std::invalid_argument with the index's own message when the results or
/// the notes cannot be read by their rules.
struct ScanNotesReport {
    std::size_t skipped = 0;          ///< datasets skipped for having no intensity above zero
    std::size_t negative_points = 0;  ///< rows skipped for a negative intensity, over every dataset
    std::vector<std::pair<std::string, std::string>> refused;  ///< (file, why) per refused dataset
};
ScanNotesReport scan_notes_report(const Project& project);
/// The file a row names: its `file_path` cell is `<data_dir>/<file>` as crysta writes it, or the bare file name;
/// empty for any other path (a file of another directory is not this scan's, whatever its name).
std::string scan_row_file(const ScanResultIndex& index, const std::vector<std::string>& cells);
std::pair<std::size_t, ScanResultIndex::Row> scan_row_facts(const Project& project, const ScanPlaces& places,
                                                           const ScanResultIndex& index,
                                                           const std::vector<std::string>& cells);

/// Whether a results column is a value crysta derives from the fitted ones rather than fits: a moment's spherical form
/// or a linked structure's weight fraction. Its value may be undefined in a converged row.
bool scan_derived_column(const std::string& name);

/// The cells of the row that starts at `offset`; throws when the file has no complete row there.
std::vector<std::string> read_scan_row(const Project& project, std::int64_t offset);

/// The parameters a scan's evolution charts list, the Evolution tab's and the report's: every free parameter of the
/// template by its unique name, listed before any dataset is fitted, then each one `analysis/results.csv` records
/// that is not free (any more), by its column, in the file's order, then the agreement factors it records.
std::vector<std::string> evolution_parameters(const Project& project, const ScanResultIndex& index);

/// One point of a parameter's evolution: a fitted dataset's value and s.u., at its x.
struct EvolutionPoint {
    double x = 0.0;
    double y = 0.0;
    double su = 0.0;
    std::size_t dataset = 0;  ///< the dataset's place in the scan
};

/// Visits each point of `parameter` (a unique name or a results column) in `analysis/results.csv`, reading the file
/// once while it still has the index's header: each row naming a file of the scan that holds a fit result (a refused
/// file's row does not) and whose value, s.u. and x are finite numbers, the error bar's ends within ±1e300. x is the
/// first extract rule's value when `by_value` and the scan has a rule, else the dataset's place counted from 1. A
/// parameter the file does not record has no point; a results path that is there but not a regular file throws.
void evolution_series(const Project& project, const ScanPlaces& places, const ScanResultIndex& index,
                      const std::string& parameter, bool by_value,
                      const std::function<void(const EvolutionPoint&)>& visit);

/// The same for several parameters in one read of the file: `visit` gets each point with its parameter's place in
/// `parameters`, row by row. A report draws every parameter's chart from one read.
void evolution_series(const Project& project, const ScanPlaces& places, const ScanResultIndex& index,
                      const std::vector<std::string>& parameters, bool by_value,
                      const std::function<void(std::size_t, const EvolutionPoint&)>& visit);

/// ADR-0088 point 1: files of a series of joint fits grouped by name, one group per experiment. In each name the
/// first run of digits that differs between the names becomes `*`; names sharing the result form a group, in the
/// order their first file comes. Names that do not split this way (one name, no differing digits, or a different
/// number of digit runs) come back as one group per name, with the name as its pattern.
struct SeriesGroup {
    std::string pattern;
    std::vector<std::string> files;
};
std::vector<SeriesGroup> group_series_files(const std::vector<std::string>& names);

/// ADR-0088 point 1: declares `project` a series of joint fits over the folder `data_dir`, one experiment per group:
/// the experiment `template_experiment` takes the first group's pattern and each further group a copy of it, named
/// after its pattern (the `*` and the extension dropped, the ends trimmed of `_` and `-`, a `_copy` suffix when
/// taken). The experiments form the experiment set `set_id`, the template first. No data file is read. Returns the
/// experiments' names in group order. Throws std::invalid_argument for an unknown template, no group, a project of
/// more than one experiment, or a set id or membership already taken, and changes nothing when it throws.
std::vector<std::string> declare_series_of_joint_fits(Project& project, const std::string& template_experiment,
                                                      const std::string& data_dir,
                                                      const std::vector<SeriesGroup>& groups,
                                                      const std::string& set_id);

/// The rule crysta's series driver holds each `analysis/results_experiments.csv` row of a recorded point to before it
/// resumes (crysta::SeriesRowRule), made from the project as fit_scan hands it over: the full read, a live row and every
/// read of a point's rows hold the file to this one rule, so the app accepts exactly what Continue accepts. Copies share
/// it; a default one is no rule (not a series).
class SeriesBankRule {
   public:
    SeriesBankRule() = default;
    explicit SeriesBankRule(const Project& project);
    bool empty() const { return rule_ == nullptr; }
    const std::vector<std::string>& header() const;
    /// Why `row` is refused, empty when it is admitted; `point_files`: the point's file of each experiment, project
    /// order; `succeeded`: the point's results.csv row records success.
    std::string refusal(const std::vector<std::string>& row, const std::vector<std::string>& point_files,
                        bool succeeded) const;

   private:
    struct Rule;
    std::shared_ptr<const Rule> rule_;
};
/// What a reader of a series point's rows knows from the results index: the rule, the point's files, whether
/// results.csv records the point and whether its fit succeeded. A recorded point's rows must all be there and keep the
/// rule; an unrecorded point's rows are a torn tail and are not read.
struct SeriesPointCheck {
    SeriesBankRule rule;
    std::vector<std::string> files;
    bool recorded = false;
    bool succeeded = false;
};
SeriesPointCheck series_point_check(const SeriesBankRule& rule, const ScanDatasets& datasets,
                                    const ScanResultIndex& index, std::size_t place);

/// ADR-0089 point 4: each experiment's divisor in a series' merged d view at the point `point`: its first enabled
/// linked structure's scale as `analysis/results_experiments.csv` records it for the point, else the template's
/// value; 1 where neither is a positive finite number. In project order.
std::vector<double> series_point_scales(const Project& project, const std::string& point,
                                        const SeriesPointCheck& check);

/// ADR-0088: what a series of joint fits' point wrote for its experiments' own parameters, from
/// `analysis/results_experiments.csv`, by unique parameter name: the value and its s.u. (none where the row says `nan`).
/// Empty before the point is fitted, or for a scan of one experiment.
struct SeriesPointValue {
    double value = 0.0;
    std::optional<double> uncertainty;
};
std::map<std::string, SeriesPointValue> series_point_values(const Project& project, const std::string& point,
                                                            const SeriesPointCheck& check);
/// Checks a recorded series point's per-experiment rows (`check`) by the rule: every experiment's row there and each
/// admitted. Throws, saying why; changes nothing.
void check_series_point_rows(const Project& project, const std::string& point, const SeriesPointCheck& check);

/// ADR-0089 point 5: the summary of one Map or Stacked row of a series over [d_min, d_max] at `columns` columns: the
/// point's pattern of each experiment in `experiments` (places in project order), read from its file on the d axis by
/// that experiment's calibration as fitted at the point (the template's before; crysta's rule for `_data.d_spacing`)
/// and divided by its entry in `scales`; for one
/// experiment its columns, for several their merge (All experiments merged). Each pattern is released once summarised.
/// Throws std::out_of_range for a point or experiment the datasets do not hold, and as read_scan_dataset does.
ScanColumns series_row_columns(const Project& project, const ScanDatasets& datasets, std::size_t point,
                               const std::vector<std::size_t>& experiments, const std::vector<double>& scales,
                               double d_min, double d_max, std::size_t columns, const SeriesPointCheck& check);

/// ADR-0089 point 5: one row of a series as a pattern on the d axis for the Stacked and Map views: the point's pattern
/// of each experiment in `experiments` (places in project order), put on d as series_row_columns does and divided by
/// its entry in `scales`, the experiments' points together in order of d. Throws as series_row_columns does.
struct SeriesRowPattern {
    std::vector<double> d, intensity;
};
SeriesRowPattern series_row_pattern(const Project& project, const ScanDatasets& datasets, std::size_t point,
                                    const std::vector<std::size_t>& experiments, const std::vector<double>& scales,
                                    const SeriesPointCheck& check);

/// A series of joint fits' per-experiment parameters (ADR-0089): the value columns of `analysis/results_experiments.csv`,
/// by their names without the datablock, in the file's order; empty for a scan of one experiment or without the file.
std::vector<std::string> evolution_experiment_parameters(const Project& project);

/// Visits each point of a per-experiment parameter of a series of joint fits, read from
/// `analysis/results_experiments.csv`: the experiment's place in project order and the point, its x as
/// evolution_series takes it from the point's `results.csv` row. A refused point has no points.
/// Every recorded point's rows are held to `rule` (`datasets`: the points' files); a row it refuses throws.
void evolution_experiment_series(const Project& project, const ScanPlaces& places, const ScanResultIndex& index,
                                 const SeriesBankRule& rule, const ScanDatasets& datasets,
                                 const std::string& parameter, bool by_value,
                                 const std::function<void(std::size_t, const EvolutionPoint&)>& visit);
/// The points evolution_experiment_series visits for one point (`point_key`), read through the point's own rows: a
/// fit adds them as each point's row arrives, without reading the file again.
void evolution_experiment_point(const Project& project, const ScanPlaces& places, const ScanResultIndex& index,
                                const SeriesBankRule& rule, const ScanDatasets& datasets,
                                const std::string& parameter, bool by_value, const std::string& point_key,
                                const std::function<void(std::size_t, const EvolutionPoint&)>& visit);

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
