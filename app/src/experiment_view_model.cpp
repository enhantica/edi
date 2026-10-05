// SPDX-License-Identifier: BSD-3-Clause
#include "experiment_view_model.hpp"

#include <algorithm>
#include <filesystem>

#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "parameter_registry.hpp"
#include "project_editor.hpp"

namespace edi_app {

namespace {
// A peak field's family, its sidebar row (edi ADR-0017 §5): 0 the back-to-back exponentials, 1 the Gaussian
// broadening, 2 the Lorentzian, 3 any other.
int peak_family(const std::string& name) {
    const auto starts = [&name](const char* prefix) { return name.rfind(prefix, 0) == 0; };
    if (starts("rise_") || starts("decay_")) {
        return 0;
    }
    if (starts("broad_gauss_")) {
        return 1;
    }
    if (starts("broad_lorentz_")) {
        return 2;
    }
    return 3;
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
      background_type_options_(new OptionListModel(this)),
      categories_(new CategoryListModel(this)),
      instrument_(new ParameterListModel([this] { return category("instrument").fields; }, registry, this)),
      peak_(new ParameterListModel([this] { return category("peak").fields; }, registry, this)),
      peak_asymmetry_(new ParameterListModel([this] { return category("peak").asymmetry; }, registry, this)),
      absorption_(new ParameterListModel([this] { return category("absorption").fields; }, registry, this)),
      background_(new BackgroundListModel(experiment, editor, registry, this)),
      excluded_regions_(new ExcludedRegionListModel(experiment, editor, this)),
      reflections_(new ReflectionListModel(experiment, this)),
      preferred_orientation_(new PrefOrientListModel(experiment, editor, registry, this)),
      scattering_source_(new ScatteringSourceViewModel(experiment, editor, this)),
      measured_range_(new RangeViewModel(experiment, this)),
      pattern_(new PatternModel(experiment, this)),
      text_(new BlockText([saved, &experiment] { return saved(std::filesystem::path(edi::entity_path("", "experiment", experiment.name)).generic_string()); }, this)) {
    capturePattern();  // the measured data shows before the first calculation is published
    // The options follow the experiment's type, which is read-only, so they are set once.
    const edi::BeamModeEnum mode = experiment_.effective_beam_mode();
    peak_type_options_->setOptions(edi::supported_peak_profiles(mode));
    absorption_type_options_->setOptions(edi::supported_absorption_families(mode));
    background_type_options_->setOptions(edi::supported_background_types());
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
        return edi::instrument_category(experiment_);
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
QString ExperimentViewModel::backgroundType() const {
    return QString::fromStdString(experiment_.background_type);
}

void ExperimentViewModel::setName(const QString& name) {
    edi::Project& project = project_;
    edi::ExperimentBase& experiment = experiment_;
    // A name another experiment of the project carries is refused (the adder's rule).
    setLastError(editor_.apply(edi::Edit::rename_experiment(project, experiment, name.toStdString()), true));
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

void ExperimentViewModel::setCutoffFwhm(double cutoff) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(editor_.apply(edi::Edit::assign(experiment.peak.cutoff_fwhm, cutoff), false));
}

void ExperimentViewModel::setLinkedStructureId(const QString& id) {
    edi::ExperimentBase& experiment = experiment_;
    setLastError(
        editor_.apply(edi::Edit::assign(experiment.linked_structure.structure_id, id.toStdString()), false));
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

void ExperimentViewModel::sync() {
    const auto update = [this](auto& member, const auto& value, void (ExperimentViewModel::*signal)()) {
        if (member != value) {
            member = value;
            emit(this->*signal)();
        }
    };
    update(name_, QString::fromStdString(experiment_.name), &ExperimentViewModel::nameChanged);
    const std::string default_profile = experiment_.effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH
                                            ? "cwl-pseudo-voigt"
                                            : "tof-jorgensen";
    update(peak_type_, QString::fromStdString(experiment_.peak.type.value_or(default_profile)),
           &ExperimentViewModel::peakTypeChanged);
    update(absorption_type_, QString::fromStdString(experiment_.absorption.type.value_or("none")),
           &ExperimentViewModel::absorptionTypeChanged);
    update(cutoff_fwhm_, experiment_.peak.cutoff_fwhm, &ExperimentViewModel::cutoffFwhmChanged);
    update(linked_structure_id_, QString::fromStdString(experiment_.linked_structure.structure_id),
           &ExperimentViewModel::linkedStructureIdChanged);
    update(dataset_weight_, experiment_.dataset_weight, &ExperimentViewModel::datasetWeightChanged);
    update(scale_, registry_.find(&experiment_.linked_structure.scale), &ExperimentViewModel::scaleChanged);
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
    background_->sync();
    excluded_regions_->sync();
    reflections_->sync();
    preferred_orientation_->sync();
    scattering_source_->sync();
}

void ExperimentViewModel::capturePattern() {
    std::size_t place = 0;
    for (std::size_t i = 0; i < project_.experiments.size(); ++i) {
        if (project_.experiments[i].get() == &experiment_) {
            place = i;
        }
    }
    pattern_source_ = edi::capture_pattern(project_, place);
    emit patternSourceChanged();
}

void ExperimentViewModel::showPattern(edi::PatternSource source) {
    pattern_source_ = std::move(source);
    emit patternSourceChanged();
}

void ExperimentViewModel::markPatternStale() {
    pattern_->markStale();
    if (pattern_source_.current) {
        pattern_source_.current = false;
        emit patternWentStale();  // the series are the same: the chart changes its `current` and nothing else
    }
}

}  // namespace edi_app
