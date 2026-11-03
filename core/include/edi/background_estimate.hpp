// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_BACKGROUND_ESTIMATE_HPP
#define EDI_BACKGROUND_ESTIMATE_HPP

// The automatic line-segment background estimate (ADR-0040): crysta computes it, edi reads its own
// experiment and writes the points as any edit of the points would.

#include <cstdint>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace edi {

/// The estimation methods, as the Estimate dialog and `show_supported` list them: `auto` (which
/// means `arpls`), `snip`, `arpls` and `fabc`.
std::vector<std::string> background_estimator_methods();

/// The tolerance, in units of the noise, when the settings leave it blank (the engine's).
inline constexpr double kDefaultBackgroundTolerance = 2.0;
// What `auto` allows before it ignores the calculated peaks: the share of the points that fall below three times the
// noise once they are subtracted.
inline constexpr double kAutoModelBelowShare = 0.01;

/// The optional settings of an estimate. Each value left empty is derived from the data.
struct BackgroundEstimateOptions {
    std::string method = "auto";
    std::optional<double> width;       ///< peak width in points; positive
    std::optional<double> smoothness;  ///< the arPLS/FABC penalty; positive; SNIP ignores it
    std::optional<int> n_points;       ///< the points to place, both ends included; >= 2
    std::optional<double> tolerance;   ///< how far the line may stray from the curve, in noise units; positive
    std::string in_peaks = "move";     ///< a point on a peak moves off it (`move`) or is dropped (`drop`)
    std::string use_model = "auto";  ///< the calculated peaks: `auto`, `subtract` or `ignore`
    std::optional<int> max_terms;    ///< polynomial and Chebyshev: the most terms; 1..30
};

/// One estimate, or (from background_estimate_defaults) what an estimate would derive.
struct BackgroundEstimate {
    std::vector<LineSegment> points;  ///< numbered 1, 2, ..., fixed; empty for the defaults
    std::vector<PolynomialTerm> terms;  ///< for a polynomial or Chebyshev: orders 0, 1, ..., fixed
    double origin = 0.0;                ///< the polynomial's origin the terms are about
    double x_min = 0.0;                 ///< the Chebyshev domain they are over
    double x_max = 0.0;
    std::string method;               ///< the method that runs: arpls, snip or fabc
    double width = 0.0;               ///< peak width in points
    double noise = 0.0;               ///< the noise sigma
    std::optional<double> smoothness;  ///< the penalty arPLS and FABC use
    std::optional<int> half_window;    ///< the window SNIP uses
    bool used_model = false;           ///< whether the calculated peaks were subtracted
    std::string model_choice;          ///< what was done with them: `subtract` or `ignore`
    std::string model_reason;          ///< why, in a sentence (for auto, what it measured)
    std::vector<std::string> warnings;
    std::string summary;  ///< e.g. "Background estimate: arpls, 12 points, width 9 pts"
};

/// What an estimate of `experiment` would derive for the options left empty, changing nothing.
/// @throws std::invalid_argument for bad options.
BackgroundEstimate background_estimate_defaults(const ExperimentBase& experiment,
                                                const BackgroundEstimateOptions& options = {});

/// Estimates the points of `experiment` from its measured pattern outside its excluded regions,
/// and its last calculated pattern when it holds one; changes nothing. An experiment with no
/// measured points gives no points and a warning.
/// @throws std::invalid_argument for a background type other than line-segment, bad options, or an
/// estimate crysta refuses.
BackgroundEstimate estimate_background(const ExperimentBase& experiment,
                                       const BackgroundEstimateOptions& options = {});

/// The options the experiment's `_background_estimate` declares, each blank item at its default.
BackgroundEstimateOptions background_estimate_options(const ExperimentBase& experiment);

/// The mode the experiment declares: `auto` or `manual` (the default). An auto-mode background whose points or terms
/// differ from the estimate is refused by the next calculation, fit or save, never read as manual (ADR-0040).
std::string background_estimate_mode(const ExperimentBase& experiment);

/// The settings, each checked as the loader checks it (std::invalid_argument otherwise; width, smoothness and
/// tolerance positive and finite, the width at most 100000 points, in_peaks move or drop). Choosing auto keeps the points as they are for comparison and makes
/// the next calculation or fit estimate; an empty value is the default.
void set_background_estimate_mode(ExperimentBase& experiment, const std::string& mode);
void set_background_estimate_method(ExperimentBase& experiment, const std::string& method);
void set_background_estimate_width(ExperimentBase& experiment, std::optional<double> width);
void set_background_estimate_smoothness(ExperimentBase& experiment, std::optional<double> smoothness);
void set_background_estimate_n_points(ExperimentBase& experiment, std::optional<int> n_points);
void set_background_estimate_tolerance(ExperimentBase& experiment, std::optional<double> tolerance);
void set_background_estimate_in_peaks(ExperimentBase& experiment, const std::string& in_peaks);
void set_background_estimate_use_model(ExperimentBase& experiment, const std::string& use_model);
void set_background_estimate_max_terms(ExperimentBase& experiment, std::optional<int> max_terms);

/// A saved `_background_estimate.inputs_digest` or `.points_digest`: 16 lowercase hex digits.
/// @throws std::invalid_argument for any other text.
std::uint64_t parse_background_digest(const std::string& text);

/// What the loader does once an experiment's points and data are read: one declaring auto compares later edits with
/// the points as loaded, or with the saved points digest (so points edited in the file read as manual), and estimates
/// at its next calculation unless the file saved what its points came from.
void settle_loaded_background_estimate(ExperimentBase& experiment);

/// Writes an estimate's points (set_background_points) and records what they came from: the experiment's
/// included measured pattern and `options`, the settings the estimate ran with.
void apply_background_estimate(ExperimentBase& experiment, const BackgroundEstimate& estimate,
                               const BackgroundEstimateOptions& options);

/// Whether refresh_background_estimates would change the experiment: it declares auto with points edited by hand, or
/// whose included measured pattern or settings differ from what its points came from.
bool background_estimate_due(const ExperimentBase& experiment);
bool background_estimates_due(const Project& project);

/// What every calculation, fit and scan does first, once (ADR-0040): crysta refreshes the project's estimates, and edi
/// takes its points and modes back. An auto-mode experiment whose points were edited by hand becomes manual; one whose
/// included measured pattern or settings changed re-estimates its points with its settings, subtracting the peaks the
/// current model calculates when it uses the model. A file that saved what its points came from does not estimate
/// again when nothing changed. Returns whether any points changed. An estimate the engine refuses throws, with nothing
/// written. With `reasons`, each estimate written with the calculated peaks set to auto adds its experiment's name and
/// why they were subtracted or ignored.
bool refresh_background_estimates(Project& project,
                                  std::vector<std::pair<std::string, std::string>>* reasons = nullptr);

/// In auto mode the estimate owns the background's points or terms (ADR-0040): an edit of one through Python refuses
/// here, saying to set the mode to manual first. Freeing or fixing one stays allowed.
/// @throws std::invalid_argument when background_estimate_mode(experiment) is `auto`.
void require_background_edit(const ExperimentBase& experiment);

/// The values an auto-mode experiment's estimate owns (ADR-0040): its points' intensities or its terms' coefficients.
/// None in manual mode. The app refuses a typed or dragged value for any of them and shows them locked.
std::vector<const Parameter*> estimated_background_values(const ExperimentBase& experiment);

/// After a fit or its undo: an auto-mode experiment's points or terms as they now are become the ones it is compared
/// with, so the next calculation neither refuses nor estimates again (ADR-0040).
void record_fitted_background(ExperimentBase& experiment);

/// After a background type change replaced the rows: an auto-mode experiment compares later edits with the new rows
/// and estimates at the next calculation (ADR-0040). Nothing for a manual one.
void rebaseline_background_estimate(ExperimentBase& experiment);

/// The line-segment points with the mode and what they came from: what an Undo of an estimate puts back.
struct BackgroundState {
    std::string type;  ///< the type the rows and constants belong to; a restore puts it back too
    std::vector<LineSegment> points;
    std::vector<PolynomialTerm> terms;
    std::optional<double> origin, x_min, x_max;
    std::optional<std::string> mode;
    std::uint64_t inputs = 0;
    std::uint64_t written = 0;
};
BackgroundState capture_background(const ExperimentBase& experiment);
void restore_background(ExperimentBase& experiment, const BackgroundState& state);

}  // namespace edi

#endif  // EDI_BACKGROUND_ESTIMATE_HPP
