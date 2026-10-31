// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EXPERIMENT_VIEW_MODEL_HPP
#define EDI_APP_EXPERIMENT_VIEW_MODEL_HPP

#include <QObject>
#include <QSet>
#include <QtNumeric>
#include <QString>
#include <QtQml/qqmlregistration.h>
#include <cstdint>
#include <optional>

#include "block_text.hpp"
#include "category_list_model.hpp"
#include "edi/background_estimate.hpp"
#include "edi/model.hpp"
#include "edi/presentation.hpp"
#include "experiment_models.hpp"
#include "option_list_model.hpp"
#include "parameter_item.hpp"
#include "pattern_model.hpp"
#include "project_editor.hpp"

namespace edi_app {

class ParameterRegistry;
class ProjectEditor;

// One experiment of the project. The four type axes are read-only; the selectors offer the
// core's supported set for the type and write through the D11 core functions; everything the
// library lets a user set is editable (§15.3).
class ExperimentViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(QString name READ name WRITE setName NOTIFY nameChanged)
    // How the project's last fit ended on this experiment (FitOutcomes key; empty when it fitted none): set by
    // the project, which knows which experiments a fit took part.
    Q_PROPERTY(QString fitOutcome READ fitOutcome NOTIFY fitOutcomeChanged)
    Q_PROPERTY(SampleForm sampleForm READ sampleForm CONSTANT)
    Q_PROPERTY(BeamMode beamMode READ beamMode CONSTANT)
    Q_PROPERTY(RadiationProbe radiationProbe READ radiationProbe CONSTANT)
    Q_PROPERTY(ScatteringType scatteringType READ scatteringType CONSTANT)
    Q_PROPERTY(QString sampleFormToken READ sampleFormToken CONSTANT)
    Q_PROPERTY(QString beamModeToken READ beamModeToken CONSTANT)
    Q_PROPERTY(QString radiationProbeToken READ radiationProbeToken CONSTANT)
    Q_PROPERTY(QString scatteringTypeToken READ scatteringTypeToken CONSTANT)
    // ADR-0053: the experiment's description, its effective values.
    Q_PROPERTY(QString dimensionalityToken READ dimensionalityToken CONSTANT)
    Q_PROPERTY(QString polarisationToken READ polarisationToken CONSTANT)
    Q_PROPERTY(QString instrumentName READ instrumentName CONSTANT)
    Q_PROPERTY(QString facility READ facility CONSTANT)
    // The Facility and Instrument selectors: the names held, empty for "Not specified", and their options, the
    // instruments those of the chosen facility for the experiment's sample form. They can be chosen for an
    // experiment made from a data file; one read from a `.edi` or `.cif` file shows what its file states.
    Q_PROPERTY(QString facilityToken READ facilityToken WRITE setFacility NOTIFY descriptionChanged)
    Q_PROPERTY(QString instrumentToken READ instrumentToken WRITE setInstrument NOTIFY descriptionChanged)
    Q_PROPERTY(bool descriptionEditable READ descriptionEditable NOTIFY descriptionChanged)
    Q_PROPERTY(edi_app::OptionListModel* facilityOptions READ facilityOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* instrumentOptions READ instrumentOptions CONSTANT)
    // Each type axis's values by their dictionary names, for the Experiment type group's selectors.
    Q_PROPERTY(edi_app::OptionListModel* sampleFormOptions READ sampleFormOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* beamModeOptions READ beamModeOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* radiationProbeOptions READ radiationProbeOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* scatteringTypeOptions READ scatteringTypeOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* dimensionalityOptions READ dimensionalityOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* polarisationOptions READ polarisationOptions CONSTANT)
    Q_PROPERTY(QString peakType READ peakType WRITE setPeakType NOTIFY peakTypeChanged)
    Q_PROPERTY(edi_app::OptionListModel* peakTypeOptions READ peakTypeOptions CONSTANT)
    Q_PROPERTY(QString absorptionType READ absorptionType WRITE setAbsorptionType NOTIFY absorptionTypeChanged)
    Q_PROPERTY(edi_app::OptionListModel* absorptionTypeOptions READ absorptionTypeOptions CONSTANT)
    Q_PROPERTY(QString extinctionType READ extinctionType WRITE setExtinctionType NOTIFY extinctionTypeChanged)
    Q_PROPERTY(edi_app::OptionListModel* extinctionTypeOptions READ extinctionTypeOptions CONSTANT)
    Q_PROPERTY(QString mosaicDistribution READ mosaicDistribution WRITE setMosaicDistribution NOTIFY
                   mosaicDistributionChanged)
    Q_PROPERTY(edi_app::OptionListModel* mosaicDistributionOptions READ mosaicDistributionOptions CONSTANT)
    // A single crystal's observed threshold (edi ADR-0050): n (NaN until set; 2 by default), the basis (empty until set;
    // intensity by default) and the expression they make.
    Q_PROPERTY(double reflnsThresholdSigma READ reflnsThresholdSigma WRITE setReflnsThresholdSigma NOTIFY
                   reflnsThresholdSigmaChanged)
    Q_PROPERTY(QString reflnsThresholdBasis READ reflnsThresholdBasis WRITE setReflnsThresholdBasis NOTIFY
                   reflnsThresholdBasisChanged)
    Q_PROPERTY(edi_app::OptionListModel* reflnsThresholdBasisOptions READ reflnsThresholdBasisOptions CONSTANT)
    Q_PROPERTY(QString reflnsThresholdExpression READ reflnsThresholdExpression NOTIFY
                   reflnsThresholdExpressionChanged)
    // The background model; another type replaces the background (edi::select_background_type).
    Q_PROPERTY(QString backgroundType READ backgroundType WRITE setBackgroundType NOTIFY backgroundTypeChanged)
    // The polynomial's origin and the Chebyshev domain's ends; NaN when the type has none.
    Q_PROPERTY(double backgroundOrigin READ backgroundOrigin WRITE setBackgroundOrigin NOTIFY backgroundOriginChanged)
    Q_PROPERTY(double backgroundXMin READ backgroundXMin WRITE setBackgroundXMin NOTIFY backgroundXMinChanged)
    Q_PROPERTY(double backgroundXMax READ backgroundXMax WRITE setBackgroundXMax NOTIFY backgroundXMaxChanged)
    Q_PROPERTY(edi_app::OptionListModel* backgroundTypeOptions READ backgroundTypeOptions CONSTANT)
    // ADR-0040: the background estimate's settings (`_background_estimate`): the mode in force (manual or auto,
    // edi::background_estimate_mode) and its options; the method and its options; each override as declared (NaN,
    // or 0 points, when blank) and the value the estimate derives for it, which a blank field shows; whether to
    // subtract the calculated peaks; and the core's warning or refusal for the derived values (empty when none).
    Q_PROPERTY(QString backgroundEstimateMode READ backgroundEstimateMode WRITE setBackgroundEstimateMode NOTIFY backgroundEstimateModeChanged)
    Q_PROPERTY(edi_app::OptionListModel* backgroundEstimateModes READ backgroundEstimateModes CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* backgroundEstimateMethods READ backgroundEstimateMethods CONSTANT)
    Q_PROPERTY(QString backgroundEstimateMethod READ backgroundEstimateMethod WRITE setBackgroundEstimateMethod NOTIFY backgroundEstimateMethodChanged)
    Q_PROPERTY(double backgroundEstimateWidth READ backgroundEstimateWidth WRITE setBackgroundEstimateWidth NOTIFY backgroundEstimateWidthChanged)
    Q_PROPERTY(double backgroundEstimateSmoothness READ backgroundEstimateSmoothness WRITE setBackgroundEstimateSmoothness NOTIFY backgroundEstimateSmoothnessChanged)
    Q_PROPERTY(int backgroundEstimatePoints READ backgroundEstimatePoints WRITE setBackgroundEstimatePoints NOTIFY backgroundEstimatePointsChanged)
    // The tolerance in noise units as declared (NaN when blank), and the one a blank field means.
    Q_PROPERTY(double backgroundEstimateTolerance READ backgroundEstimateTolerance WRITE setBackgroundEstimateTolerance NOTIFY backgroundEstimateToleranceChanged)
    Q_PROPERTY(double estimateTolerance READ estimateTolerance CONSTANT)
    // The calculated peaks (`use_model`: auto, subtract or ignore), their choices, and what an estimate now does
    // with them and why (for auto, what it measured).
    Q_PROPERTY(edi_app::OptionListModel* backgroundEstimateModels READ backgroundEstimateModels CONSTANT)
    Q_PROPERTY(QString backgroundEstimateUseModel READ backgroundEstimateUseModel WRITE setBackgroundEstimateUseModel NOTIFY backgroundEstimateUseModelChanged)
    Q_PROPERTY(QString estimateModelChoice READ estimateModelChoice NOTIFY estimateModelChoiceChanged)
    Q_PROPERTY(QString estimateModelReason READ estimateModelReason NOTIFY estimateModelReasonChanged)
    Q_PROPERTY(QString estimateMethod READ estimateMethod NOTIFY estimateMethodChanged)
    Q_PROPERTY(double estimateWidth READ estimateWidth NOTIFY estimateWidthChanged)
    Q_PROPERTY(double estimateSmoothness READ estimateSmoothness NOTIFY estimateSmoothnessChanged)
    // How many points Estimate places with the settings as they stand, when the most points is blank (else 0).
    Q_PROPERTY(int estimatePoints READ estimatePoints NOTIFY estimatePointsChanged)
    // A polynomial's or Chebyshev's most terms (0 when blank), and how many terms Estimate uses now.
    Q_PROPERTY(int backgroundEstimateMaxTerms READ backgroundEstimateMaxTerms WRITE setBackgroundEstimateMaxTerms NOTIFY backgroundEstimateMaxTermsChanged)
    Q_PROPERTY(int estimateTerms READ estimateTerms NOTIFY estimateTermsChanged)
    Q_PROPERTY(QString estimateNote READ estimateNote NOTIFY estimateNoteChanged)
    Q_PROPERTY(double cutoffFwhm READ cutoffFwhm WRITE setCutoffFwhm NOTIFY cutoffFwhmChanged)
    Q_PROPERTY(QString linkedStructureId READ linkedStructureId WRITE setLinkedStructureId NOTIFY linkedStructureIdChanged)
    Q_PROPERTY(double datasetWeight READ datasetWeight WRITE setDatasetWeight NOTIFY datasetWeightChanged)
    Q_PROPERTY(bool calculationOnly READ calculationOnly CONSTANT)
    // Load data… reads a plain-data file into this experiment, in place of any data it has: every experiment but a
    // scan's (the owner, 2026-10-11). `dataFile`: the plain-data file its data came from, or empty.
    Q_PROPERTY(bool canLoadData READ canLoadData NOTIFY canLoadDataChanged)
    Q_PROPERTY(QString dataFile READ dataFile CONSTANT)
    Q_PROPERTY(edi_app::CategoryListModel* categories READ categories CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* instrument READ instrument CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* peak READ peak CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* peakAsymmetry READ peakAsymmetry CONSTANT)
    // `peak`'s fields by family, one sidebar row each (edi ADR-0017 §5): the back-to-back exponentials
    // (`rise_*`, `decay_*`), the Gaussian broadening (`broad_gauss_*`), the Lorentzian (`broad_lorentz_*`), and
    // any other field.
    Q_PROPERTY(edi_app::ParameterListModel* peakBackToBack READ peakBackToBack CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* peakGaussian READ peakGaussian CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* peakLorentzian READ peakLorentzian CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* peakOther READ peakOther CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* absorption READ absorption CONSTANT)
    Q_PROPERTY(edi_app::ParameterItem* scale READ scale NOTIFY scaleChanged)
    Q_PROPERTY(edi_app::BackgroundListModel* background READ background CONSTANT)
    Q_PROPERTY(edi_app::BackgroundTermListModel* backgroundTerms READ backgroundTerms CONSTANT)
    Q_PROPERTY(edi_app::ExcludedRegionListModel* excludedRegions READ excludedRegions CONSTANT)
    Q_PROPERTY(edi_app::ReflectionListModel* reflections READ reflections CONSTANT)
    Q_PROPERTY(edi_app::SingleCrystalReflectionModel* singleCrystalReflections READ singleCrystalReflections CONSTANT)
    Q_PROPERTY(edi_app::ParameterListModel* extinction READ extinction CONSTANT)
    Q_PROPERTY(edi_app::PrefOrientListModel* preferredOrientation READ preferredOrientation CONSTANT)
    Q_PROPERTY(edi_app::LinkedStructureListModel* linkedStructures READ linkedStructures CONSTANT)
    Q_PROPERTY(edi_app::ScatteringSourceViewModel* scatteringSource READ scatteringSource CONSTANT)
    Q_PROPERTY(edi_app::RangeViewModel* measuredRange READ measuredRange CONSTANT)
    Q_PROPERTY(edi_app::PatternModel* pattern READ pattern CONSTANT)
    Q_PROPERTY(edi_app::BlockText* text READ text CONSTANT)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

   public:
    enum SampleForm { Powder, SingleCrystal };
    Q_ENUM(SampleForm)
    enum BeamMode { ConstantWavelength, TimeOfFlight };
    Q_ENUM(BeamMode)
    enum RadiationProbe { Neutron, Xray };
    Q_ENUM(RadiationProbe)
    enum ScatteringType { Bragg, Total };
    Q_ENUM(ScatteringType)

    ExperimentViewModel(SavedFile saved, edi::Project& project, edi::ExperimentBase& experiment,
                        ProjectEditor& editor, ParameterRegistry& registry, QObject* parent);

    QString name() const { return name_; }
    QString fitOutcome() const { return fit_outcome_; }
    void setFitOutcome(const QString& outcome);
    // The calculation grid of an experiment without measured data (edi::Edit::data_range): its start,
    // end and step; refused, with `lastError`, for one with data.
    Q_INVOKABLE void setRange(double start, double end, double step);
    void setName(const QString& name);
    SampleForm sampleForm() const;
    BeamMode beamMode() const;
    RadiationProbe radiationProbe() const;
    ScatteringType scatteringType() const;
    QString sampleFormToken() const;
    QString beamModeToken() const;
    QString radiationProbeToken() const;
    QString scatteringTypeToken() const;
    QString dimensionalityToken() const;
    QString polarisationToken() const;
    QString instrumentName() const;
    QString facility() const;
    QString facilityToken() const { return facility_token_; }
    QString instrumentToken() const { return instrument_token_; }
    bool descriptionEditable() const { return description_editable_; }
    OptionListModel* facilityOptions() const { return facility_options_; }
    OptionListModel* instrumentOptions() const { return instrument_options_; }
    void setFacility(const QString& facility);
    void setInstrument(const QString& instrument);
    OptionListModel* sampleFormOptions() const { return sample_form_options_; }
    OptionListModel* beamModeOptions() const { return beam_mode_options_; }
    OptionListModel* radiationProbeOptions() const { return radiation_probe_options_; }
    OptionListModel* scatteringTypeOptions() const { return scattering_type_options_; }
    OptionListModel* dimensionalityOptions() const { return dimensionality_options_; }
    OptionListModel* polarisationOptions() const { return polarisation_options_; }
    QString peakType() const { return peak_type_; }
    void setPeakType(const QString& token);
    OptionListModel* peakTypeOptions() const { return peak_type_options_; }
    QString absorptionType() const { return absorption_type_; }
    void setAbsorptionType(const QString& token);
    OptionListModel* absorptionTypeOptions() const { return absorption_type_options_; }
    QString extinctionType() const { return extinction_type_; }
    void setExtinctionType(const QString& token);
    OptionListModel* extinctionTypeOptions() const { return extinction_type_options_; }
    // Empty for a type without a mosaic spread.
    QString mosaicDistribution() const { return mosaic_distribution_; }
    void setMosaicDistribution(const QString& token);
    OptionListModel* mosaicDistributionOptions() const { return mosaic_distribution_options_; }
    double reflnsThresholdSigma() const { return reflns_threshold_sigma_; }
    void setReflnsThresholdSigma(double sigma);
    QString reflnsThresholdBasis() const { return reflns_threshold_basis_; }
    void setReflnsThresholdBasis(const QString& token);
    OptionListModel* reflnsThresholdBasisOptions() const { return reflns_threshold_basis_options_; }
    QString reflnsThresholdExpression() const { return reflns_threshold_expression_; }
    QString backgroundType() const { return background_type_; }
    void setBackgroundType(const QString& token);
    double backgroundOrigin() const { return background_origin_; }
    void setBackgroundOrigin(double origin);
    double backgroundXMin() const { return background_x_min_; }
    void setBackgroundXMin(double value);
    double backgroundXMax() const { return background_x_max_; }
    void setBackgroundXMax(double value);
    OptionListModel* backgroundTypeOptions() const { return background_type_options_; }
    QString backgroundEstimateMode() const { return estimate_.mode; }
    void setBackgroundEstimateMode(const QString& mode);
    OptionListModel* backgroundEstimateModes() const { return background_estimate_modes_; }
    OptionListModel* backgroundEstimateModels() const { return background_estimate_models_; }
    OptionListModel* backgroundEstimateMethods() const { return background_estimate_methods_; }
    QString backgroundEstimateMethod() const { return estimate_.method; }
    void setBackgroundEstimateMethod(const QString& method);
    double backgroundEstimateWidth() const { return estimate_.width; }
    void setBackgroundEstimateWidth(double width);
    double backgroundEstimateSmoothness() const { return estimate_.smoothness; }
    void setBackgroundEstimateSmoothness(double smoothness);
    int backgroundEstimatePoints() const { return estimate_.points; }
    double backgroundEstimateTolerance() const { return estimate_.tolerance; }
    static double estimateTolerance() { return edi::kDefaultBackgroundTolerance; }
    QString estimateModelChoice() const { return estimate_.model_choice; }
    QString estimateModelReason() const { return estimate_.model_reason; }
    void setBackgroundEstimatePoints(int points);
    void setBackgroundEstimateTolerance(double tolerance);
    QString backgroundEstimateUseModel() const { return estimate_.use_model; }
    void setBackgroundEstimateUseModel(const QString& useModel);
    QString estimateMethod() const { return estimate_.derived_method; }
    double estimateWidth() const { return estimate_.derived_width; }
    double estimateSmoothness() const { return estimate_.derived_smoothness; }
    int estimatePoints() const { return estimate_.derived_points; }
    int backgroundEstimateMaxTerms() const { return estimate_.max_terms; }
    void setBackgroundEstimateMaxTerms(int maxTerms);
    int estimateTerms() const { return estimate_.derived_terms; }
    QString estimateNote() const { return estimate_.note; }
    double cutoffFwhm() const { return cutoff_fwhm_; }
    void setCutoffFwhm(double cutoff);
    QString linkedStructureId() const { return linked_structure_id_; }
    void setLinkedStructureId(const QString& id);
    double datasetWeight() const { return dataset_weight_; }
    void setDatasetWeight(double weight);
    bool calculationOnly() const { return experiment_.calculation_only; }
    bool canLoadData() const { return can_load_data_; }
    QString dataFile() const { return QString::fromStdString(experiment_.data_file); }
    // Set by the project, which knows how the experiment was made.
    void setCanLoadData(bool can_load_data);
    CategoryListModel* categories() const { return categories_; }
    ParameterListModel* instrument() const { return instrument_; }
    ParameterListModel* peak() const { return peak_; }
    ParameterListModel* peakAsymmetry() const { return peak_asymmetry_; }
    ParameterListModel* peakBackToBack() const { return peak_families_[0]; }
    ParameterListModel* peakGaussian() const { return peak_families_[1]; }
    ParameterListModel* peakLorentzian() const { return peak_families_[2]; }
    ParameterListModel* peakOther() const { return peak_families_[3]; }
    ParameterListModel* absorption() const { return absorption_; }
    ParameterListModel* extinction() const { return extinction_; }
    SingleCrystalReflectionModel* singleCrystalReflections() const { return single_crystal_reflections_; }
    ParameterItem* scale() const { return scale_; }
    BackgroundListModel* background() const { return background_; }
    BackgroundTermListModel* backgroundTerms() const { return background_terms_; }
    ExcludedRegionListModel* excludedRegions() const { return excluded_regions_; }
    ReflectionListModel* reflections() const { return reflections_; }
    PrefOrientListModel* preferredOrientation() const { return preferred_orientation_; }
    LinkedStructureListModel* linkedStructures() const { return linked_structures_; }
    ScatteringSourceViewModel* scatteringSource() const { return scattering_source_; }
    RangeViewModel* measuredRange() const { return measured_range_; }
    PatternModel* pattern() const { return pattern_; }
    // The experiment's pattern as the chart draws it (edi ADR-0021 §1): immutable buffers, captured when
    // a calculation is published and when the experiment is first shown. On the d axis it is the d-spacing capture,
    // kept while a chart is on d; until there is one, the pattern on the experiment's own axis.
    const edi::PatternSource& patternSource(edi::PatternAxis axis = edi::PatternAxis::Native) const {
        return axis == edi::PatternAxis::DSpacing && d_source_ ? *d_source_ : pattern_source_;
    }
    void capturePattern();
    // A running fit's pattern at one iteration: shown until the fit ends and the pattern is captured
    // again. A scan dataset's view brings its d-spacing capture too; a fit's frame does not, and the chart on d
    // keeps the last one until the fit's result is captured.
    void showPattern(edi::PatternSource source, std::optional<edi::PatternSource> d_source = std::nullopt);
    // A chart's x axis: while one chart is on d, the pattern is captured on d as well.
    void setChartAxis(const QObject* chart, edi::PatternAxis axis);
    bool dSpacingWanted() const { return !d_charts_.isEmpty(); }
    // The colour of this experiment's pattern (edi::pattern_colour) is its place among a count: by default among the
    // project's experiments; a scan's template shows one dataset at a time and takes that dataset's place among the
    // scan's datasets, as the Project page lists them (setColourPlace).
    std::size_t colourPlace() const { return colour_place_.value_or(place()); }
    std::size_t colourCount() const { return colour_place_ ? colour_count_ : project_.experiments.size(); }
    // The project's structures, whose ticks the pattern shows.
    std::size_t structureCount() const { return project_.structures.size(); }
    void setColourPlace(std::optional<std::size_t> place, std::size_t count);
    // An edit was admitted: what the pattern shows was calculated before it. The frame stays; the pattern
    // reports stale and the chart's source reports that it no longer describes the model, until the newest
    // request's publication captures the pattern again.
    void markPatternStale();
    // A parameter's slider is held (ProjectViewModel::adjusting): a pattern chart holds its y range while the
    // calculated curve stays inside it, and fits it once again when the slider is let go.
    bool adjusting() const { return adjusting_; }
    void setAdjusting(bool adjusting) {
        if (adjusting != adjusting_) {
            adjusting_ = adjusting;
            emit adjustingChanged();
        }
    }
    // Pattern charts showing this experiment's pattern register here while they are shown (on the page and the tab
    // the window shows): a followed scan file counts as drawn only while one is (edi ADR-0029).
    bool patternShown() const { return !shown_charts_.isEmpty(); }
    void setChartShown(const QObject* chart, bool shown);
    // Each new pattern source has the next generation; a shown chart notes the one it drew, so a followed file's
    // receipt can tell that its own pattern reached the screen.
    std::uint64_t patternGeneration() const { return pattern_generation_; }
    std::uint64_t presentedGeneration() const { return presented_generation_; }
    void notePresented() { presented_generation_ = pattern_generation_; }
    BlockText* text() const { return text_; }
    QString lastError() const { return last_error_; }

    const edi::ExperimentBase* experiment() const { return &experiment_; }
    void sync();
    // The estimate settings and what they derive, re-read: after an edit (sync) and after a calculation, which
    // changes the calculated pattern use_model reads.
    void syncEstimate();

   signals:
    void nameChanged();
    void canLoadDataChanged();
    void fitOutcomeChanged();
    void peakTypeChanged();
    void absorptionTypeChanged();
    void descriptionChanged();
    void extinctionTypeChanged();
    void mosaicDistributionChanged();
    void reflnsThresholdSigmaChanged();
    void reflnsThresholdBasisChanged();
    void reflnsThresholdExpressionChanged();
    void backgroundTypeChanged();
    void backgroundEstimateModeChanged();
    void backgroundEstimateMethodChanged();
    void backgroundEstimateWidthChanged();
    void backgroundEstimateSmoothnessChanged();
    void backgroundEstimatePointsChanged();
    void backgroundEstimateMaxTermsChanged();
    void estimateTermsChanged();
    void backgroundEstimateToleranceChanged();
    void estimateModelChoiceChanged();
    void estimateModelReasonChanged();
    void backgroundEstimateUseModelChanged();
    void estimateMethodChanged();
    void estimateWidthChanged();
    void estimateSmoothnessChanged();
    void estimatePointsChanged();
    void estimateNoteChanged();
    void backgroundOriginChanged();
    void backgroundXMinChanged();
    void backgroundXMaxChanged();
    void cutoffFwhmChanged();
    void linkedStructureIdChanged();
    void datasetWeightChanged();
    void scaleChanged();
    void lastErrorChanged();
    void patternSourceChanged();
    void patternWentStale();
    void adjustingChanged();
    void patternShownChanged();

   private:
    edi::Category category(const char* id) const;
    void setLastError(const QString& error);
    // The experiment's place in the project.
    std::size_t place() const;

    edi::Project& project_;
    edi::ExperimentBase& experiment_;
    QSet<const QObject*> shown_charts_;
    QSet<const QObject*> d_charts_;
    std::uint64_t pattern_generation_ = 0;
    bool adjusting_ = false;
    std::optional<std::size_t> colour_place_;
    std::size_t colour_count_ = 0;
    std::uint64_t presented_generation_ = 0;
    ProjectEditor& editor_;
    bool can_load_data_ = false;
    ParameterRegistry& registry_;
    QString name_, peak_type_, absorption_type_, background_type_, linked_structure_id_, last_error_, fit_outcome_;
    double background_origin_ = qQNaN(), background_x_min_ = qQNaN(), background_x_max_ = qQNaN();
    double cutoff_fwhm_ = 0.0, dataset_weight_ = 1.0;
    OptionListModel* sample_form_options_;
    OptionListModel* beam_mode_options_;
    OptionListModel* radiation_probe_options_;
    OptionListModel* scattering_type_options_;
    OptionListModel* dimensionality_options_;
    OptionListModel* polarisation_options_;
    OptionListModel* peak_type_options_;
    OptionListModel* absorption_type_options_;
    OptionListModel* facility_options_;
    OptionListModel* instrument_options_;
    QString facility_token_, instrument_token_;
    bool description_editable_ = false;
    void sync_description();
    OptionListModel* extinction_type_options_;
    OptionListModel* mosaic_distribution_options_;
    QString extinction_type_, mosaic_distribution_;
    OptionListModel* reflns_threshold_basis_options_;
    double reflns_threshold_sigma_ = qQNaN();
    QString reflns_threshold_basis_, reflns_threshold_expression_;
    OptionListModel* background_type_options_;
    OptionListModel* background_estimate_methods_;
    OptionListModel* background_estimate_modes_;
    OptionListModel* background_estimate_models_;
    // What the estimate settings read now, compared at each sync; NaN never equals itself, so equal() compares them.
    struct EstimateSettings {
        QString mode, method, derived_method, note;
        double width = qQNaN(), smoothness = qQNaN(), tolerance = qQNaN(), derived_width = qQNaN(),
               derived_smoothness = qQNaN();
        int points = 0, derived_points = 0, max_terms = 0, derived_terms = 0;
        QString use_model = QStringLiteral("auto"), model_choice, model_reason;
    };
    EstimateSettings estimate_;
    EstimateSettings read_estimate_settings() const;
    CategoryListModel* categories_;
    ParameterListModel* instrument_;
    ParameterListModel* peak_;
    ParameterListModel* peak_asymmetry_;
    ParameterListModel* peak_families_[4] = {};
    ParameterListModel* absorption_;
    ParameterListModel* extinction_;
    ParameterItem* scale_ = nullptr;
    BackgroundListModel* background_;
    BackgroundTermListModel* background_terms_;
    ExcludedRegionListModel* excluded_regions_;
    ReflectionListModel* reflections_;
    SingleCrystalReflectionModel* single_crystal_reflections_;
    PrefOrientListModel* preferred_orientation_;
    LinkedStructureListModel* linked_structures_;
    ScatteringSourceViewModel* scattering_source_;
    RangeViewModel* measured_range_;
    PatternModel* pattern_;
    edi::PatternSource pattern_source_;
    std::optional<edi::PatternSource> d_source_;
    BlockText* text_;
};

}  // namespace edi_app

#endif  // EDI_APP_EXPERIMENT_VIEW_MODEL_HPP
