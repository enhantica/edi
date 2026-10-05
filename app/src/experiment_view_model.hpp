// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EXPERIMENT_VIEW_MODEL_HPP
#define EDI_APP_EXPERIMENT_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

#include "block_text.hpp"
#include "category_list_model.hpp"
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
    Q_PROPERTY(SampleForm sampleForm READ sampleForm CONSTANT)
    Q_PROPERTY(BeamMode beamMode READ beamMode CONSTANT)
    Q_PROPERTY(RadiationProbe radiationProbe READ radiationProbe CONSTANT)
    Q_PROPERTY(ScatteringType scatteringType READ scatteringType CONSTANT)
    Q_PROPERTY(QString sampleFormToken READ sampleFormToken CONSTANT)
    Q_PROPERTY(QString beamModeToken READ beamModeToken CONSTANT)
    Q_PROPERTY(QString radiationProbeToken READ radiationProbeToken CONSTANT)
    Q_PROPERTY(QString scatteringTypeToken READ scatteringTypeToken CONSTANT)
    Q_PROPERTY(QString peakType READ peakType WRITE setPeakType NOTIFY peakTypeChanged)
    Q_PROPERTY(edi_app::OptionListModel* peakTypeOptions READ peakTypeOptions CONSTANT)
    Q_PROPERTY(QString absorptionType READ absorptionType WRITE setAbsorptionType NOTIFY absorptionTypeChanged)
    Q_PROPERTY(edi_app::OptionListModel* absorptionTypeOptions READ absorptionTypeOptions CONSTANT)
    Q_PROPERTY(QString backgroundType READ backgroundType CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* backgroundTypeOptions READ backgroundTypeOptions CONSTANT)
    Q_PROPERTY(double cutoffFwhm READ cutoffFwhm WRITE setCutoffFwhm NOTIFY cutoffFwhmChanged)
    Q_PROPERTY(QString linkedStructureId READ linkedStructureId WRITE setLinkedStructureId NOTIFY linkedStructureIdChanged)
    Q_PROPERTY(double datasetWeight READ datasetWeight WRITE setDatasetWeight NOTIFY datasetWeightChanged)
    Q_PROPERTY(bool calculationOnly READ calculationOnly CONSTANT)
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
    Q_PROPERTY(edi_app::ExcludedRegionListModel* excludedRegions READ excludedRegions CONSTANT)
    Q_PROPERTY(edi_app::ReflectionListModel* reflections READ reflections CONSTANT)
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
    QString peakType() const { return peak_type_; }
    void setPeakType(const QString& token);
    OptionListModel* peakTypeOptions() const { return peak_type_options_; }
    QString absorptionType() const { return absorption_type_; }
    void setAbsorptionType(const QString& token);
    OptionListModel* absorptionTypeOptions() const { return absorption_type_options_; }
    QString backgroundType() const;
    OptionListModel* backgroundTypeOptions() const { return background_type_options_; }
    double cutoffFwhm() const { return cutoff_fwhm_; }
    void setCutoffFwhm(double cutoff);
    QString linkedStructureId() const { return linked_structure_id_; }
    void setLinkedStructureId(const QString& id);
    double datasetWeight() const { return dataset_weight_; }
    void setDatasetWeight(double weight);
    bool calculationOnly() const { return experiment_.calculation_only; }
    CategoryListModel* categories() const { return categories_; }
    ParameterListModel* instrument() const { return instrument_; }
    ParameterListModel* peak() const { return peak_; }
    ParameterListModel* peakAsymmetry() const { return peak_asymmetry_; }
    ParameterListModel* peakBackToBack() const { return peak_families_[0]; }
    ParameterListModel* peakGaussian() const { return peak_families_[1]; }
    ParameterListModel* peakLorentzian() const { return peak_families_[2]; }
    ParameterListModel* peakOther() const { return peak_families_[3]; }
    ParameterListModel* absorption() const { return absorption_; }
    ParameterItem* scale() const { return scale_; }
    BackgroundListModel* background() const { return background_; }
    ExcludedRegionListModel* excludedRegions() const { return excluded_regions_; }
    ReflectionListModel* reflections() const { return reflections_; }
    PrefOrientListModel* preferredOrientation() const { return preferred_orientation_; }
    LinkedStructureListModel* linkedStructures() const { return linked_structures_; }
    ScatteringSourceViewModel* scatteringSource() const { return scattering_source_; }
    RangeViewModel* measuredRange() const { return measured_range_; }
    PatternModel* pattern() const { return pattern_; }
    // The experiment's pattern as the chart draws it (edi ADR-0021 §1): immutable buffers, captured when
    // a calculation is published and when the experiment is first shown.
    const edi::PatternSource& patternSource() const { return pattern_source_; }
    void capturePattern();
    // A running fit's pattern at one iteration: shown until the fit ends and the pattern is captured
    // again.
    void showPattern(edi::PatternSource source);
    // An edit was admitted: what the pattern shows was calculated before it. The frame stays; the pattern
    // reports stale and the chart's source reports that it no longer describes the model, until the newest
    // request's publication captures the pattern again.
    void markPatternStale();
    BlockText* text() const { return text_; }
    QString lastError() const { return last_error_; }

    const edi::ExperimentBase* experiment() const { return &experiment_; }
    void sync();

   signals:
    void nameChanged();
    void peakTypeChanged();
    void absorptionTypeChanged();
    void cutoffFwhmChanged();
    void linkedStructureIdChanged();
    void datasetWeightChanged();
    void scaleChanged();
    void lastErrorChanged();
    void patternSourceChanged();
    void patternWentStale();

   private:
    edi::Category category(const char* id) const;
    void setLastError(const QString& error);

    edi::Project& project_;
    edi::ExperimentBase& experiment_;
    ProjectEditor& editor_;
    ParameterRegistry& registry_;
    QString name_, peak_type_, absorption_type_, linked_structure_id_, last_error_;
    double cutoff_fwhm_ = 0.0, dataset_weight_ = 1.0;
    OptionListModel* peak_type_options_;
    OptionListModel* absorption_type_options_;
    OptionListModel* background_type_options_;
    CategoryListModel* categories_;
    ParameterListModel* instrument_;
    ParameterListModel* peak_;
    ParameterListModel* peak_asymmetry_;
    ParameterListModel* peak_families_[4] = {};
    ParameterListModel* absorption_;
    ParameterItem* scale_ = nullptr;
    BackgroundListModel* background_;
    ExcludedRegionListModel* excluded_regions_;
    ReflectionListModel* reflections_;
    PrefOrientListModel* preferred_orientation_;
    LinkedStructureListModel* linked_structures_;
    ScatteringSourceViewModel* scattering_source_;
    RangeViewModel* measured_range_;
    PatternModel* pattern_;
    edi::PatternSource pattern_source_;
    BlockText* text_;
};

}  // namespace edi_app

#endif  // EDI_APP_EXPERIMENT_VIEW_MODEL_HPP
