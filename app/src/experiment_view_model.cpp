// SPDX-License-Identifier: BSD-3-Clause
#include "experiment_view_model.hpp"

#include <QStringList>

#include <algorithm>
#include <exception>
#include <filesystem>
#include <iterator>
#include <string>
#include <utility>
#include <vector>

#include "edi/background_estimate.hpp"
#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "parameter_registry.hpp"
#include "project_editor.hpp"

namespace edi_app {

namespace {
// A peak field's family, its sidebar row (edi ADR-0017 §5): 0 the back-to-back exponentials, 1 the Gaussian
// broadening with the CW profile's two shape fields (U V W, then X Y or eta0 eta1, on one row), 2 the TOF
// Lorentzian, 3 any other.
int peak_family(const std::string& name) {
    const auto starts = [&name](const char* prefix) { return name.rfind(prefix, 0) == 0; };
    if (starts("rise_") || starts("decay_")) {
        return 0;
    }
    if (starts("broad_gauss_") || starts("mixing_eta_") || name == "broad_lorentz_x" || name == "broad_lorentz_y") {
        return 1;
    }
    if (starts("broad_lorentz_")) {
        return 2;
    }
    return 3;
}

// The instrument fields in the sidebar's order (display only; the file and the parameter paths keep the
// core's): the wavelengths first, then the corrections, so an X-ray CW group reads Wavelength, Wavelength 2,
// Intensity ratio 2/1 on one row and 2θ offset, Polarization coefficient, Monochromator 2θ on the next.
std::vector<edi::CategoryField> instrument_display_order(std::vector<edi::CategoryField> fields) {
    static constexpr const char* order[] = {"setup_wavelength",
                                            "setup_wavelength_2",
                                            "setup_wavelength_2_to_1_ratio",
                                            "calib_twotheta_offset",
                                            "setup_polarization_coefficient",
                                            "setup_monochromator_twotheta"};
    const auto rank = [](const std::string& name) {
        const auto* found = std::find(std::begin(order), std::end(order), name);
        return static_cast<int>(found - std::begin(order));
    };
    std::stable_sort(fields.begin(), fields.end(), [&rank](const edi::CategoryField& a, const edi::CategoryField& b) {
        return rank(a.name) < rank(b.name);
    });
    return fields;
}
}  // namespace

ExperimentViewModel::ExperimentViewModel(SavedFile saved, edi::Project& project, edi::ExperimentBase& experiment,
                                         ProjectEditor& editor, ParameterRegistry& registry, QObject* parent)
    : QObject(parent),
      project_(project),
      experiment_(experiment),
      editor_(editor),
      registry_(registry),
      peak_type_options_(new OptionListModel(this)),
      absorption_type_options_(new OptionListModel(this)),
      extinction_type_options_(new OptionListModel(this)),
      mosaic_distribution_options_(new OptionListModel(this)),
      reflns_threshold_basis_options_(new OptionListModel(this)),
      background_type_options_(new OptionListModel(this)),
      background_estimate_methods_(new OptionListModel(this)),
      background_estimate_modes_(new OptionListModel(this)),
      background_estimate_models_(new OptionListModel(this)),
      categories_(new CategoryListModel(this)),
      instrument_(new ParameterListModel([this] { return instrument_display_order(category("instrument").fields); },
                                          registry, this)),
      peak_(new ParameterListModel([this] { return category("peak").fields; }, registry, this)),
      peak_asymmetry_(new ParameterListModel([this] { return category("peak").asymmetry; }, registry, this)),
      absorption_(new ParameterListModel([this] { return category("absorption").fields; }, registry, this)),
      extinction_(new ParameterListModel([this] { return category("extinction").fields; }, registry, this)),
      background_(new BackgroundListModel(experiment, editor, registry, this)),
      background_terms_(new BackgroundTermListModel(experiment, editor, registry, this)),
      excluded_regions_(new ExcludedRegionListModel(experiment, editor, this)),
      reflections_(new ReflectionListModel(experiment, this)),
      single_crystal_reflections_(new SingleCrystalReflectionModel(experiment, project, this)),
      preferred_orientation_(new PrefOrientListModel(experiment, editor, registry, this)),
      linked_structures_(new LinkedStructureListModel(project, experiment, editor, registry, this)),
      scattering_source_(new ScatteringSourceViewModel(experiment, editor, this)),
      measured_range_(new RangeViewModel(experiment, this)),
      pattern_(new PatternModel(experiment, this)),
      text_(new BlockText([saved, &experiment] { return saved(std::filesystem::path(edi::entity_path("", "experiment", experiment.name)).generic_string()); }, this)) {
    capturePattern();  // the measured data shows before the first calculation is published
    // The options follow the experiment's type, which is read-only, so they are set once.
    const edi::BeamModeEnum mode = experiment_.effective_beam_mode();
    const std::vector<std::string> profiles = edi::supported_peak_profiles(mode);
    std::vector<std::string> profile_labels;
    for (const std::string& profile : profiles) {
        profile_labels.push_back(edi::peak_profile_label(profile));
    }
    peak_type_options_->setOptions(profiles, edi::default_peak_profile(mode), profile_labels);
    absorption_type_options_->setOptions(edi::supported_absorption_families(mode));
    extinction_type_options_->setOptions(edi::extinction_type_tokens(), "none", edi::extinction_type_choice_labels());
    mosaic_distribution_options_->setOptions(edi::mosaic_distribution_tokens(), "gaussian",
                                             edi::mosaic_distribution_labels());
    reflns_threshold_basis_options_->setOptions(edi::reflns_threshold_basis_tokens(), "intensity",
                                                edi::reflns_threshold_basis_labels());
    background_type_options_->setOptions(edi::supported_background_types());
    background_estimate_methods_->setOptions(edi::background_estimator_methods());
    background_estimate_modes_->setOptions({"manual", "auto"});
    background_estimate_models_->setOptions({"auto", "subtract", "ignore"});
    for (int family = 0; family < 4; ++family) {
        peak_families_[family] = new ParameterListModel(
            [this, family] {
                std::vector<edi::CategoryField> fields = category("peak").fields;
                fields.erase(std::remove_if(fields.begin(), fields.end(),
                                            [family](const edi::CategoryField& field) {
                                                return peak_family(field.name) != family;
                                            }),
                             fields.end());
                return fields;
            },
            registry, this);
    }
    sync();
}

edi::Category ExperimentViewModel::category(const char* id) const {
    if (std::string(id) == "peak") {
        return edi::peak_category(experiment_);
    }
    if (std::string(id) == "instrument") {
        // A time-of-flight single crystal has no instrument category (its wavelength band is shown instead).
        if (experiment_.reflections.has_value() &&
            experiment_.effective_beam_mode() == edi::BeamModeEnum::TIME_OF_FLIGHT) {
            return edi::Category{"instrument"};
        }
        return edi::instrument_category(experiment_);
    }
    if (std::string(id) == "extinction") {
        edi::Category extinction{"extinction"};
        edi::detail::add_optional(extinction.fields, "crystal_radius", experiment_.extinction.crystal_radius);
        if (experiment_.extinction.crystal_radius) {
            extinction.fields.back().fittable = false;  // a descriptor of the crystal (is_fixed_setting)
        }
        edi::detail::add_optional(extinction.fields, "domain_radius", experiment_.extinction.domain_radius);
        edi::detail::add_optional(extinction.fields, "mosaic_spread", experiment_.extinction.mosaic_spread);
        edi::detail::add_optional(extinction.fields, "coefficient", experiment_.extinction.coefficient);
        edi::detail::add_optional(extinction.fields, "coefficient_11", experiment_.extinction.coefficient_11);
        edi::detail::add_optional(extinction.fields, "coefficient_22", experiment_.extinction.coefficient_22);
        edi::detail::add_optional(extinction.fields, "coefficient_33", experiment_.extinction.coefficient_33);
        edi::detail::add_optional(extinction.fields, "coefficient_12", experiment_.extinction.coefficient_12);
        edi::detail::add_optional(extinction.fields, "coefficient_13", experiment_.extinction.coefficient_13);
        edi::detail::add_optional(extinction.fields, "coefficient_23", experiment_.extinction.coefficient_23);
        return extinction;
    }
    return edi::absorption_category(experiment_);
}

ExperimentViewModel::SampleForm ExperimentViewModel::sampleForm() const {
    return experiment_.experiment_type.effective_sample_form() == edi::SampleFormEnum::POWDER ? Powder : SingleCrystal;
}
ExperimentViewModel::BeamMode ExperimentViewModel::beamMode() const {
    return experiment_.effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH ? ConstantWavelength
                                                                                        : TimeOfFlight;
}
ExperimentViewModel::RadiationProbe ExperimentViewModel::radiationProbe() const {
    return experiment_.experiment_type.effective_radiation_probe() == edi::RadiationProbeEnum::XRAY ? Xray : Neutron;
}
ExperimentViewModel::ScatteringType ExperimentViewModel::scatteringType() const {
    return experiment_.experiment_type.effective_scattering_type() == edi::ScatteringTypeEnum::TOTAL ? Total : Bragg;
}
QString ExperimentViewModel::sampleFormToken() const {
    return QString::fromUtf8(edi::token(experiment_.experiment_type.effective_sample_form()));
}
QString ExperimentViewModel::beamModeToken() const {
    return QString::fromUtf8(edi::token(experiment_.effective_beam_mode()));
}
QString ExperimentViewModel::radiationProbeToken() const {
    return QString::fromUtf8(edi::token(experiment_.experiment_type.effective_radiation_probe()));
}
QString ExperimentViewModel::scatteringTypeToken() const {
    return QString::fromUtf8(edi::token(experiment_.experiment_type.effective_scattering_type()));
}
// The declared model, now that edi computes more than one.
ExperimentViewModel::EstimateSettings ExperimentViewModel::read_estimate_settings() const {
    EstimateSettings out;
    out.mode = QString::fromStdString(edi::background_estimate_mode(experiment_));
    out.method = QString::fromStdString(experiment_.background_estimate_method.value_or("auto"));
    out.width = experiment_.background_estimate_width.value_or(qQNaN());
    out.smoothness = experiment_.background_estimate_smoothness.value_or(qQNaN());
    out.points = experiment_.background_estimate_n_points.value_or(0);
    out.tolerance = experiment_.background_estimate_tolerance.value_or(qQNaN());
    out.use_model = QString::fromStdString(experiment_.background_estimate_use_model.value_or("auto"));
    out.max_terms = experiment_.background_estimate_max_terms.value_or(0);
    try {
        const edi::BackgroundEstimateOptions options = edi::background_estimate_options(experiment_);
        const edi::BackgroundEstimate defaults = edi::background_estimate_defaults(experiment_, options);
        out.derived_method = QString::fromStdString(defaults.method);
        out.derived_width = defaults.width;
        out.derived_smoothness = defaults.smoothness.value_or(qQNaN());
        out.model_choice = QString::fromStdString(defaults.model_choice);
        out.model_reason = QString::fromStdString(defaults.model_reason);
        // A blank most points or most terms has no value to derive, so the field shows how many Estimate places.
        if (experiment_.background_type == "line-segment") {
            if (!options.n_points) {
                out.derived_points = static_cast<int>(edi::estimate_background(experiment_, options).points.size());
            }
        } else if (!options.max_terms) {
            out.derived_terms = static_cast<int>(edi::estimate_background(experiment_, options).terms.size());
        }
        QStringList warnings;
        for (const std::string& warning : defaults.warnings) {
            warnings.append(QString::fromStdString(warning));
        }
        out.note = warnings.join(QLatin1Char('\n'));
    } catch (const std::exception& error) {
        out.note = QString::fromUtf8(error.what());
    }
    return out;
}

void ExperimentViewModel::setBackgroundEstimateMode(const QString& mode) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_estimate_mode(experiment, mode.toStdString()), false));
}

void ExperimentViewModel::setBackgroundEstimateMethod(const QString& method) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_estimate_method(experiment, method.toStdString()), false));
}

// A NaN width or smoothness, or fewer than one point, is blank: derived from the data.
void ExperimentViewModel::setBackgroundEstimateWidth(double width) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(
        edi::Edit::background_estimate_width(experiment, qIsNaN(width) ? std::nullopt : std::optional(width)), false));
}

void ExperimentViewModel::setBackgroundEstimateSmoothness(double smoothness) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_estimate_smoothness(
                                   experiment, qIsNaN(smoothness) ? std::nullopt : std::optional(smoothness)),
                               false));
}

void ExperimentViewModel::setBackgroundEstimatePoints(int points) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(
        edi::Edit::background_estimate_n_points(experiment, points < 1 ? std::nullopt : std::optional(points)), false));
}

void ExperimentViewModel::setBackgroundEstimateMaxTerms(int maxTerms) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(
        edi::Edit::background_estimate_max_terms(experiment, maxTerms < 1 ? std::nullopt : std::optional(maxTerms)),
        false));
}

void ExperimentViewModel::setBackgroundEstimateTolerance(double tolerance) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_estimate_tolerance(
                                   experiment, qIsNaN(tolerance) ? std::nullopt : std::optional(tolerance)),
                               false));
}

void ExperimentViewModel::setBackgroundEstimateUseModel(const QString& useModel) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_estimate_use_model(experiment, useModel.toStdString()), false));
}

void ExperimentViewModel::setBackgroundType(const QString& token) {
    if (token == background_type_) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_type(experiment, token.toStdString()), true));
}

void ExperimentViewModel::setBackgroundOrigin(double origin) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_origin(experiment, origin), false));
}

void ExperimentViewModel::setBackgroundXMin(double value) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_domain(experiment, false, value), false));
}

void ExperimentViewModel::setBackgroundXMax(double value) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::background_domain(experiment, true, value), false));
}

void ExperimentViewModel::setName(const QString& name) {
    edi::Project& project = project_;
    edi::ExperimentBase& experiment = experiment_;
    // A name another experiment of the project carries is refused (the adder's rule).
    setLastError(editor_.rename_experiment(project, experiment, name.toStdString()));
}

void ExperimentViewModel::setFitOutcome(const QString& outcome) {
    if (outcome != fit_outcome_) {
        fit_outcome_ = outcome;
        emit fitOutcomeChanged();
    }
}

void ExperimentViewModel::setRange(double start, double end, double step) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::data_range(experiment, start, end, step), false));
}

void ExperimentViewModel::setPeakType(const QString& token) {
    if (token == peak_type_) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::peak_profile(experiment, token.toStdString()), true));
}

void ExperimentViewModel::setAbsorptionType(const QString& token) {
    if (token == absorption_type_) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::absorption(experiment, token.toStdString()), true));
}

void ExperimentViewModel::setExtinctionType(const QString& token) {
    if (token == extinction_type_) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::extinction(experiment, token.toStdString()), true));
}

void ExperimentViewModel::setMosaicDistribution(const QString& token) {
    if (token == mosaic_distribution_) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::mosaic_distribution(experiment, token.toStdString()), false));
}

void ExperimentViewModel::setReflnsThresholdSigma(double sigma) {
    const std::optional<double> value = qIsNaN(sigma) ? std::nullopt : std::optional<double>(sigma);
    if (value == experiment_.reflns_threshold_sigma) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply_unread(edi::Edit::reflns_threshold_sigma(experiment, value)));
}

void ExperimentViewModel::setReflnsThresholdBasis(const QString& token) {
    const std::optional<std::string> value =
        token.isEmpty() ? std::nullopt : std::optional<std::string>(token.toStdString());
    if (value == experiment_.reflns_threshold_basis) {
        return;
    }
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply_unread(edi::Edit::reflns_threshold_basis(experiment, value)));
}

void ExperimentViewModel::setCutoffFwhm(double cutoff) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::assign(experiment.peak.cutoff_fwhm, cutoff), false));
}

void ExperimentViewModel::setLinkedStructureId(const QString& id) {
    edi::ExperimentBase& experiment = experiment_;
    if (experiment.linked_structures.size() != 1) {
        // A bank of several phases changes a link in its Linked structures table.
        setLastError(tr("This experiment links %1 structures: change a link in its Linked structures table")
                         .arg(experiment.linked_structures.size()));
        return;
    }
    setLastError(editor_.apply(edi::Edit::link_structure(experiment.linked_structure(), id.toStdString()), false));
}

void ExperimentViewModel::setDatasetWeight(double weight) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::assign(experiment.dataset_weight, weight), false));
}

void ExperimentViewModel::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

void ExperimentViewModel::syncEstimate() {
    // Every value is stored before any signal, so a handler reads the new settings throughout.
    const EstimateSettings before = std::exchange(estimate_, read_estimate_settings());
    const auto notify = [this](bool changed, void (ExperimentViewModel::*signal)()) {
        if (changed) {
            emit(this->*signal)();
        }
    };
    const auto moved = [](double a, double b) { return !(qIsNaN(a) && qIsNaN(b)) && a != b; };
    notify(estimate_.mode != before.mode, &ExperimentViewModel::backgroundEstimateModeChanged);
    notify(estimate_.method != before.method, &ExperimentViewModel::backgroundEstimateMethodChanged);
    notify(moved(estimate_.width, before.width), &ExperimentViewModel::backgroundEstimateWidthChanged);
    notify(moved(estimate_.smoothness, before.smoothness), &ExperimentViewModel::backgroundEstimateSmoothnessChanged);
    notify(estimate_.points != before.points, &ExperimentViewModel::backgroundEstimatePointsChanged);
    notify(moved(estimate_.tolerance, before.tolerance), &ExperimentViewModel::backgroundEstimateToleranceChanged);
    notify(estimate_.model_choice != before.model_choice, &ExperimentViewModel::estimateModelChoiceChanged);
    notify(estimate_.model_reason != before.model_reason, &ExperimentViewModel::estimateModelReasonChanged);
    notify(estimate_.use_model != before.use_model, &ExperimentViewModel::backgroundEstimateUseModelChanged);
    notify(estimate_.derived_method != before.derived_method, &ExperimentViewModel::estimateMethodChanged);
    notify(moved(estimate_.derived_width, before.derived_width), &ExperimentViewModel::estimateWidthChanged);
    notify(moved(estimate_.derived_smoothness, before.derived_smoothness), &ExperimentViewModel::estimateSmoothnessChanged);
    notify(estimate_.derived_points != before.derived_points, &ExperimentViewModel::estimatePointsChanged);
    notify(estimate_.max_terms != before.max_terms, &ExperimentViewModel::backgroundEstimateMaxTermsChanged);
    notify(estimate_.derived_terms != before.derived_terms, &ExperimentViewModel::estimateTermsChanged);
    notify(estimate_.note != before.note, &ExperimentViewModel::estimateNoteChanged);
}

void ExperimentViewModel::sync() {
    const auto update = [this](auto& member, const auto& value, void (ExperimentViewModel::*signal)()) {
        if (member != value) {
            member = value;
            emit(this->*signal)();
        }
    };
    update(name_, QString::fromStdString(experiment_.name), &ExperimentViewModel::nameChanged);
    const std::string default_profile = edi::default_peak_profile(experiment_.effective_beam_mode());
    update(peak_type_, QString::fromStdString(experiment_.peak.type.value_or(default_profile)),
           &ExperimentViewModel::peakTypeChanged);
    update(absorption_type_, QString::fromStdString(experiment_.absorption.type.value_or("none")),
           &ExperimentViewModel::absorptionTypeChanged);
    update(extinction_type_, QString::fromStdString(experiment_.extinction.type.value_or("none")),
           &ExperimentViewModel::extinctionTypeChanged);
    update(mosaic_distribution_, QString::fromStdString(experiment_.extinction.mosaic_distribution.value_or("")),
           &ExperimentViewModel::mosaicDistributionChanged);
    // The observed threshold: n, the basis and the expression they make, each with its own signal.
    const double threshold_sigma = experiment_.reflns_threshold_sigma.value_or(qQNaN());
    if ((qIsNaN(threshold_sigma) != qIsNaN(reflns_threshold_sigma_)) ||
        (!qIsNaN(threshold_sigma) && threshold_sigma != reflns_threshold_sigma_)) {
        reflns_threshold_sigma_ = threshold_sigma;
        emit reflnsThresholdSigmaChanged();
    }
    update(reflns_threshold_basis_, QString::fromStdString(experiment_.reflns_threshold_basis.value_or("")),
           &ExperimentViewModel::reflnsThresholdBasisChanged);
    update(reflns_threshold_expression_, QString::fromStdString(edi::reflns_threshold_expression(experiment_)),
           &ExperimentViewModel::reflnsThresholdExpressionChanged);
    update(background_type_, QString::fromStdString(experiment_.background_type),
           &ExperimentViewModel::backgroundTypeChanged);
    // NaN never equals itself: a constant the type lacks is compared as absent.
    const auto update_constant = [this](double& member, const std::optional<double>& value,
                                        void (ExperimentViewModel::*signal)()) {
        if (value.has_value() ? qIsNaN(member) || member != *value : !qIsNaN(member)) {
            member = value.value_or(qQNaN());
            emit(this->*signal)();
        }
    };
    update_constant(background_origin_, experiment_.background_origin, &ExperimentViewModel::backgroundOriginChanged);
    update_constant(background_x_min_, experiment_.background_x_min, &ExperimentViewModel::backgroundXMinChanged);
    update_constant(background_x_max_, experiment_.background_x_max, &ExperimentViewModel::backgroundXMaxChanged);
    update(cutoff_fwhm_, experiment_.peak.cutoff_fwhm, &ExperimentViewModel::cutoffFwhmChanged);
    syncEstimate();
    // The one link's id and scale; empty for a bank of several phases, whose rows the Linked structures
    // table shows.
    const bool one_link = experiment_.linked_structures.size() == 1;
    update(linked_structure_id_,
           one_link ? QString::fromStdString(experiment_.linked_structure().structure_id.value()) : QString(),
           &ExperimentViewModel::linkedStructureIdChanged);
    update(dataset_weight_, experiment_.dataset_weight, &ExperimentViewModel::datasetWeightChanged);
    update(scale_, one_link ? registry_.find(&experiment_.linked_structure().scale) : nullptr,
           &ExperimentViewModel::scaleChanged);
    // `data` is a loop in `.edi` — its points — though the core's category list counts no rows for it; the
    // sidebar titles it as a loop, with the number of measured points (edi ADR-0017 §3).
    measured_range_->sync();
    std::vector<edi::Category> categories = edi::experiment_categories(experiment_);
    for (edi::Category& category : categories) {
        if (category.id == "data") {
            category.is_loop = true;
            category.rows = static_cast<std::size_t>(measured_range_->points());
        }
    }
    categories_->setCategories(categories);
    instrument_->sync();
    peak_->sync();
    peak_asymmetry_->sync();
    for (ParameterListModel* family : peak_families_) {
        family->sync();
    }
    absorption_->sync();
    extinction_->sync();
    single_crystal_reflections_->sync();
    background_->sync();
    background_terms_->sync();
    excluded_regions_->sync();
    reflections_->sync();
    preferred_orientation_->sync();
    linked_structures_->sync();
    scattering_source_->sync();
}

std::size_t ExperimentViewModel::place() const {
    std::size_t place = 0;
    for (std::size_t i = 0; i < project_.experiments.size(); ++i) {
        if (project_.experiments[i].get() == &experiment_) {
            place = i;
        }
    }
    return place;
}

void ExperimentViewModel::capturePattern() {
    single_crystal_reflections_->sync();  // a single crystal's calculated F², published with the pattern
    pattern_source_ = edi::capture_pattern(project_, place());
    pattern_source_.experiment_place = colourPlace();
    if (!d_charts_.isEmpty()) {
        d_source_ = edi::capture_pattern(project_, place(), edi::PatternAxis::DSpacing);
        d_source_->experiment_place = colourPlace();
    }
    ++pattern_generation_;
    emit patternSourceChanged();
}

void ExperimentViewModel::showPattern(edi::PatternSource source, std::optional<edi::PatternSource> d_source) {
    if (source.refln_calc) {  // a single crystal's F²calc at a fit's iteration
        single_crystal_reflections_->showFrame(source.refln_calc);
    }
    pattern_source_ = std::move(source);
    pattern_source_.experiment_place = colourPlace();
    if (d_source) {
        d_source_ = std::move(d_source);
        d_source_->experiment_place = colourPlace();
    }
    ++pattern_generation_;
    emit patternSourceChanged();
}

void ExperimentViewModel::setColourPlace(std::optional<std::size_t> place, std::size_t count) {
    if (place == colour_place_ && (!place || count == colour_count_)) {
        return;
    }
    colour_place_ = place;
    colour_count_ = place ? count : 0;
    // The same pattern in its new colour: the chart draws it again, and nothing waiting on a new pattern counts it.
    pattern_source_.experiment_place = colourPlace();
    if (d_source_) {
        d_source_->experiment_place = colourPlace();
    }
    emit patternSourceChanged();
}

void ExperimentViewModel::setChartAxis(const QObject* chart, edi::PatternAxis axis) {
    const bool wanted = !d_charts_.isEmpty();
    if (axis == edi::PatternAxis::DSpacing) {
        d_charts_.insert(chart);
    } else {
        d_charts_.remove(chart);
    }
    if (d_charts_.isEmpty()) {
        d_source_.reset();
    } else if (!wanted) {
        d_source_ = edi::capture_pattern(project_, place(), edi::PatternAxis::DSpacing);
        d_source_->experiment_place = colourPlace();
        emit patternSourceChanged();
    }
}

void ExperimentViewModel::setChartShown(const QObject* chart, bool shown) {
    const bool was = patternShown();
    if (shown) {
        shown_charts_.insert(chart);
    } else {
        shown_charts_.remove(chart);
    }
    if (patternShown() != was) {
        emit patternShownChanged();
    }
}

void ExperimentViewModel::markPatternStale() {
    pattern_->markStale();
    if (pattern_source_.current) {
        pattern_source_.current = false;
        emit patternWentStale();  // the series are the same: the chart changes its `current` and nothing else
    }
}

void ExperimentViewModel::setCanLoadData(bool can_load_data) {
    if (can_load_data != can_load_data_) {
        can_load_data_ = can_load_data;
        emit canLoadDataChanged();
    }
}

}  // namespace edi_app
