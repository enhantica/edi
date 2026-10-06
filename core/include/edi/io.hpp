// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_IO_HPP
#define EDI_IO_HPP

#include <cstdint>
#include <functional>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

// edi project I/O (ADR-0009 — product logic in the core, not the binding). Reads/writes the
// declarative `.edi` project format and reads CIF structures, shaped after diffraction-lib's io module
// (the `_category.item` STAR layout + line-segment background + joint-fit analysis) without importing
// its code. Every entry point fails closed: malformed input raises `edi::IoError` and no partial model
// escapes. The crysta engine is never consulted here — parity with crysta's loader is proven by the
// gate comparing values, not by sharing code.

namespace edi {

// Raised for every structured I/O failure (missing/truncated file, unknown block, non-finite numeric,
// wrong-format handoff). Maps to a Python exception at the binding boundary.
class IoError : public std::runtime_error {
   public:
    explicit IoError(const std::string& message) : std::runtime_error(message) {}
};

// Load a declarative `.edi` project directory (structures/, experiments/, analysis/) into a
// Project: the single structure, every experiment bank (sorted by filename), and the analysis
// fitting mode. THE ONE LOADER: a successful return PROVES the project is complete, with the
// postconditions selected by what each experiment file declares —
//   * an embedded `_data` loop  -> fit-ready: the loop is non-empty, declares all required
//     columns, and every value is finite with a strictly positive sigma;
//   * a `_data_range.<axis>_min/_max/_step` grid -> calculation-only: the generated axis carries
//     no observation and the fit entry points refuse;
//   * neither, or both, is a load-time IoError naming the offending file.
// Any violation throws before the Project escapes — a partially-loaded project is
// unrepresentable, and after a fit-ready load refinement cannot fail for a data reason.
//
// The loader's two warnings (an unsupported `_minimizer.type`, a directory without
// `project.edi`) go to `std::cerr`, exactly as the CLI and `import edi` have always printed them,
// unless the caller passes `on_warning`; then each message goes only to the sink. The app passes
// one so it can show the warnings to its user.
using WarningSink = std::function<void(const std::string&)>;
Project load_project(const std::string& directory, const WarningSink& on_warning = {});

// Structures and experiments enter an open project only from `.edi` block files. Each load
// refuses a path without the `.edi` extension and content without the project format's
// `_edi.schema_version` (so a classic CIF is refused, although the from-text entries below read
// that vocabulary too), then builds through the loader's own block builder. An experiment file
// must also declare its type — all four `_experiment_type` axes — and a type edi's experiment
// class implements (powder + bragg); a project directory keeps the loader's presence-tracked
// axes. Nothing is changed by a load: adding is the separate step below.
Structure load_structure_edi_file(const std::string& path);
BraggPdExperiment load_experiment_edi_file(const std::string& path);
// A batch, checked as a whole before anything is added: every file as above, and each name
// unique against the project and within the batch. The first refusal names its file.
std::vector<BraggPdExperiment> load_experiment_edi_files(const Project& project,
                                                         const std::vector<std::string>& paths);
// Add a loaded structure: refused when the project already holds one (edi persists one structure
// per project — load_project reads one, save_project refuses more).
void add_loaded_structure(Project& project, Structure structure);
// Add a loaded experiment: refused when its name is already in the project (upstream's collection
// `add` replaces by key; edi refuses rather than silently replacing — divergence D-k).
void add_loaded_experiment(Project& project, BraggPdExperiment experiment);
// Rename an experiment of the project, the adder's rule: refused when the new name is already in the
// project, so a rename never makes two experiments share one name.
void rename_experiment(Project& project, ExperimentBase& experiment, const std::string& name);
// A new project holding no structure and no experiment (`Project()` carries a default of each).
Project empty_project(const std::string& name, const std::string& description);

// The `.edi` text a save writes for one block of the project — the file crysta's writer produces,
// byte for byte, taken from a save into a scratch directory that is removed afterwards. A writer
// refusal (several structures, a calculation-only experiment) is thrown as the IoError
// save_project throws.
enum class BlockKind : std::uint8_t { PROJECT, STRUCTURE, EXPERIMENT, ANALYSIS };
std::string block_edi_text(const Project& project, BlockKind kind, const std::string& name = {});

// ADR-0016: THE composition of an entity document's path from a datablock name — crysta's
// `datablock_key` (an empty name is `kind`'s default) and `entity_path`, reached through the
// adapter, so edi has no naming policy of its own. `kind` is "structure" or "experiment"; the
// result is `directory/<kind>s/<key>.edi`. Refuses (std::invalid_argument) a name outside the
// persisted-name domain.
std::string entity_path(const std::string& directory, const std::string& kind,
                        const std::string& name);
// Every file a save writes, in the loader's read order (project, structures, experiments,
// analysis), each as its path relative to the project directory and its text.
std::vector<std::pair<std::string, std::string>> project_edi_files(const Project& project);

// The crystal system of a space-group setting, named by crysta (its resolver and
// per-setting freedom map); throws what crysta's resolver throws for an unknown setting.
std::string crystal_system_name(const SpaceGroup& space_group);
// The IT number of a space-group setting as crysta resolves it — the number crysta's writer writes
// when `_space_group.it_number` is absent; throws what crysta's resolver throws.
int space_group_it_number(const SpaceGroup& space_group);

// Write a Project back out as a `.edi` project directory (inverse of load_project: structures,
// experiments, analysis). Each bank's embedded `_data` loop is written back IFF present, so
// presence round-trips — a complete project stays complete, a model-only one stays model-only.
void save_project(const Project& project, const std::string& directory);

// Save the project to `directory` and make it the project's directory (Project.path and
// metadata.path) — the binding's save_as rule: the last-modified time advances before the write and
// is restored if the write fails, and the directory is remembered only after it succeeds. The app's
// Save and Save as go through it.
void save_project_as(Project& project, const std::string& directory);

// The delegated write — converts the model and calls crysta::save_project. Implemented in
// the adapter (the one crysta-touching TU); edi-only signature (ADR-0003).
void save_project_via_crysta(const Project& project, const std::string& directory);

// The project's relations checked by crysta (a refusal is a DomainValidationError carrying crysta's
// `crysta.domain.constraint_*` codes), every parameter marked with its dependence, and a dependent's
// free flag cleared with crysta's `crysta.domain.dependent_free_ignored` warning to `warn`. The loader
// runs it; so does every edit of the relations.
void refresh_relations(Project& project, const WarningSink& warn = {});

// Every dependent (a cell sibling, a special-position follower, a constrained parameter) set from
// its relation at the model's current independent values by crysta's one applier, values only.
// Implemented in the adapter (the one crysta-touching TU, ADR-0003). Returns false and changes
// nothing when the model cannot be converted or its relations do not hold; a calculation says why.
bool apply_relations(Project& project);

// The same, refusing instead: crysta's refusal (a relation that cannot hold, a value outside its
// range) propagates, and the model is unchanged. A read that needs the completed values, such as a
// geometry, calls it.
void complete_relations(Project& project);

// Undo's half: apply_relations, then each dependent's e.s.d. back to the one it held before the
// fit (kept in memory by the fit's write-back, or seeded by the loader from a legacy file).
void restore_dependents(Project& project);

// Review-9 F1 — the lossless prior-state property on edi's own paths (implemented in the
// adapter, ADR-0003). rebalance_positional_fit_state runs between write_back and the
// completions: it moves the basic's snapshot onto the designated axis (the representative
// when free, else the first free axis — one snapshot per basic), lands the fitted e.s.d. on
// the declared free axes only, and puts a fixed representative's own uncertainty presence
// back. restore_positional_dependents is undo's positional pass: a restored snapshot axis
// derives its basic back onto the representative sign-correctly, free tied axes that did not
// restore their own snapshot take the restored uncertainty, and fixed axes are never touched;
// restore_dependents then completes the values.
void rebalance_positional_fit_state(Structure& structure);
void restore_positional_dependents(Structure& structure,
                                   const std::set<const Parameter*>& restored);

// Review-9 (the start_tied mirror): resolve each loaded _fit_parameter row's free tied companions
// and seed their esd-only snapshots — from the row's start_tied token when the file carries the
// column ('), else from each companion's own coordinate su (under the keep-prior rule that IS the
// prior). A token contradicting the model's free tied set refuses. Implemented in the adapter
// (ADR-0003);
// `where` names the analysis file for error messages.
void seed_positional_start_companions(
    Project& project,
    const std::vector<std::pair<Parameter*, std::optional<std::string>>>& rows,
    const std::string& where);

// Review-10 F2: the loader's own numeric rule — finite, full-token, classic-locale — exported
// so every serialized number the adapter parses (the start_tied payload) crosses the SAME
// boundary as every other number in the format; throws the loader's structured errors.
double parse_edi_double(const std::string& text, const std::string& where);

// Review-8 F4: the ruled absorption family contract at the MUTATION boundary — the one
// spelling shared with the loader. "none" clears the coefficient body (a typed family's
// parameters exist only when the type says so); "cylinder" keeps declared coefficients and
// supplies a missing one as the owner's general default ("0" ⇒ A ≡ 1); any other token throws
// std::invalid_argument. The factory and the public type setter route every supported
// selection through this, so a mutated model always matches what both loaders accept.
void apply_absorption_family(AbsorptionBase& absorption, const std::string& token);

// Undo the last fit (diffraction-lib `undo_fit`, the single-level pre-fit snapshot). Restores each
// parameter carrying persisted start state to its start_value/start_uncertainty, clears the snapshot,
// and reports the structured outcome; with no persisted state it reports was_no_op and changes NOTHING
// (a second undo is a reported no-op by construction). Lives beside the loader because the snapshot is
// persistence state (the analysis.edi _fit_parameter loop); crysta's crysta/analysis.hpp mirrors it.
// An undone model is the PRE-FIT model, so a restoring undo refreshes the stored calculated pattern
// with it — refresh_calculated_pattern(), last, under the same was_no_op guard; an undo that restores
// nothing still changes nothing.
struct UndoFitOutcome {
    std::vector<std::string> restored_parameters;  // fit-state slot ids, walk order
    bool was_no_op = false;
};
UndoFitOutcome undo_fit(Project& project);
// Undo_fit without its last step, the refresh of the stored calculated pattern — for a caller that
// calculates elsewhere (the app's worker). Restores exactly what undo_fit restores.
UndoFitOutcome restore_fit_start(Project& project);
// The last fit's result record (`_fit_result` and each experiment's `_fit_result_bank` share).
// `copy_fit_result` writes `from`'s onto `to`, a project `from` was copied from (experiments by position);
// `clear_fit_result` leaves none. An undo clears it (restore_fit_start), as diffraction-lib's undo does.
void copy_fit_result(Project& to, const Project& from);
void clear_fit_result(Project& project);

// Build one entity from text (diffraction-lib `StructureFactory.from_cif_str` /
// `ExperimentFactory.from_cif_str` — ruling absorb-ten-26). BOTH entries accept the dot-form
// `.edi` schema and the classic CIF vocabulary: the structure entry dispatches on
// the cell vocabulary to the restored reader (B/U/aniso ADP ladder); the experiment entry
// translates diffraction-lib's `cif_names` spellings (`_pd_meas.*`, `_instr.*`,
// `_easydiffraction_peak.*`, …) to their `.edi` tags and flows through the one experiment
// builder. Fails closed (IoError) as the directory loader does.
Structure structure_from_edi_text(const std::string& text);
BraggPdExperiment experiment_from_edi_text(const std::string& text);

/// The type of a new experiment, by its `.edi` tokens (`_experiment_type.*`).
struct ExperimentTypeTokens {
    std::string sample_form = "powder";
    std::string beam_mode = "constant wavelength";
    std::string radiation_probe = "neutron";
    std::string scattering_type = "bragg";
};

/// A new experiment without measured data: a simulation over its beam mode's default calculation grid
/// (`_data_range`, so calculation_only), linked to `structure_id` at scale 1 when that is not empty, with
/// default instrument and peak values and every parameter fixed. Built from `.edi` text by the one
/// experiment builder, so a type token or a name the loader refuses is refused here with its message
/// (IoError).
BraggPdExperiment simulation_experiment(const std::string& name, const ExperimentTypeTokens& type,
                                        const std::string& structure_id);
/// The same, linked to each of `structure_ids` at scale 1 (Create experiment links every structure).
BraggPdExperiment simulation_experiment(const std::string& name, const ExperimentTypeTokens& type,
                                        const std::vector<std::string>& structure_ids);

/// The rows of a plain two- or three-column data file `x y [σ]`, read by crysta's plain-data reader, and what
/// it dropped or changed: lines that are not two or three numbers, rows with y <= 0, repeated
/// x, rows moved by the sort, and rows whose σ was derived from y. Throws IoError when the file cannot be read or
/// keeps no row.
struct PlainDataRows {
    std::vector<double> x;
    std::vector<double> y;
    std::vector<double> sigma;
    std::size_t skipped = 0;
    std::size_t nonpositive = 0;
    std::size_t duplicates = 0;
    std::size_t reordered = 0;
    std::size_t derived = 0;
};
PlainDataRows read_plain_data(const std::string& path);

/// A plain-data file read into an experiment (Load data): the experiment as it was, with the file's rows as
/// its measured data, so its type, instrument, peak, background and excluded regions stay.
struct PlainDataLoad {
    BraggPdExperiment experiment;
    std::string file_name;  // the file's own name, without its directory
    std::size_t points = 0;
    std::size_t skipped = 0;
    std::size_t nonpositive = 0;
    std::size_t duplicates = 0;
    std::size_t reordered = 0;
    std::size_t derived = 0;
};
/// `experiment` with the rows of the plain-data file at `path` as its measured data. With `take_file_name`,
/// the experiment is renamed to the file's name without its extension, when that is a name the project can
/// use. Throws IoError when the file cannot be read or keeps no row.
PlainDataLoad experiment_with_plain_data(const BraggPdExperiment& experiment, const std::string& path,
                                         bool take_file_name);

// Registration-live loader vocabulary (seam 20 / I15): the Python registration seam adds a new
// `_peak.type` token here so the loader and selector accept it without a rebuild — crysta's
// registry-built known_peak_types() pattern, mirrored. Idempotent; a shipped row is never
// overwritten. `peak_type_known` is the selector's fail-closed query.
void register_peak_type(const std::string& token, BeamModeEnum mode);
bool peak_type_known(const std::string& token);
// The beam mode of a known, implemented `_peak.type` token (empty for an unknown or reserved one),
// and every registered token in the registry's order — the selector's supported-set query.
std::optional<BeamModeEnum> peak_type_beam_mode(const std::string& token);
std::vector<std::string> registered_peak_types();



}  // namespace edi

#endif  // EDI_IO_HPP
