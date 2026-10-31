// SPDX-License-Identifier: BSD-3-Clause
#include "demo_driver.hpp"

#include <algorithm>

#include <QCoreApplication>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QGuiApplication>
#include <QKeyEvent>
#include <QKeySequence>
#include <QMouseEvent>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QThread>
#include <QUrl>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <system_error>

#include "analysis_view_model.hpp"
#include "crysta/project_output.hpp"
#include "edi/categories.hpp"
#include "edi/palette.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#include "scan_session.hpp"
#include "scan_view_model.hpp"
#include "session.hpp"
#include "structure_view_model.hpp"

namespace edi_app {
namespace {

// A frame counts as settled when two grabs this far apart are identical (the base's animations run
// up to 1 s); a state that never settles within the bound fails the run.
constexpr int kSettleIntervalMs = 100;
constexpr int kSettleMaxAttempts = 30;
// A fit the demo starts ends within this, or the run fails; `capture-now` captures this long after its actions.
constexpr int kFitWaitMs = 300000;
// The timed scenario's idle poll: fine enough not to blur a measured interval.
constexpr int kIdlePollMs = 5;
constexpr int kUnsettledCaptureMs = 150;
// A timed change whose frame has not been swapped within this counts as none.
constexpr int kFrameWaitMs = 5000;

// Open a bundled example from the Project page: scroll its row into view, click it.
QStringList open_example(const QString& id) {
    const qsizetype row = ExampleListModel::bundledIds().indexOf(id);
    return {QStringLiteral("appBar.tab.project"), QStringLiteral("sideBar.tab.basic"),
            QStringLiteral("show:examples.list:%1").arg(row),
            QStringLiteral("examples.open.") + id};
}

// Open a test project the app does not bundle, from the Project page, when a step needs that project's own content.
QStringList open_cli_project(const QString& id) {
    return {QStringLiteral("appBar.tab.project"), QStringLiteral("open-cli-project:") + id};
}

}  // namespace

// The copy goes through the engine's project output (ADR-0039), so it refuses to write over anything already there.
QString copy_cli_project(const QString& id, const QDir& into) {
    namespace fs = std::filesystem;
    const fs::path source = fs::path(EDI_CLI_PROJECTS_DIR) / id.toStdString() / "project";
    const fs::path target = fs::path(into.filePath(id).toStdString()) / "project";
    std::error_code error;
    if (!fs::is_directory(source, error)) {
        return {};
    }
    crysta::output::create_directories(target.parent_path(), error);
    if (!error) {
        crysta::output::copy_new(source, target, crysta::output::CopyFiles::copied, error);
    }
    return error ? QString() : QString::fromStdString(target.string());
}

DemoDriver::DemoDriver(QQuickWindow& window, const QString& output_dir, const QString& only, QObject* parent)
    : QObject(parent), window_(window), output_dir_(output_dir) {
    // A new atom is random (edi::new_atom_site): the demo draws it from one seed, so its images repeat.
    AtomSiteListModel::fixRandomSeed(17);
    const QString experiment = QStringLiteral("appBar.tab.experiment");
    const QString basic = QStringLiteral("sideBar.tab.basic");
    const QString extras = QStringLiteral("sideBar.tab.extras");
    const QString text = QStringLiteral("sideBar.tab.text");
    // The states of the owner's v0.9.9 originals, in their order, on the Co2SiO4/D20 example the
    // originals show ...
    steps_ = {
        // The platform appearance "System" follows is pinned to light first: the set is captured light on
        // every host, whatever its appearance (a dark Mac rendered every capture dark); the dark and "System"
        // captures below switch through the same seam explicitly.
        {"01-home", {"platform:light"}},
        // Every foldable group but Get started starts folded (edi ADR-0017 §3), so each capture opens what it
        // shows; Get started is open already.
        {"02-project-no-project", {"home.start"}},
        {"03-project-examples", {"group.examples"}},
        {"04-project-loaded", {"examples.open.pd-neut-cwl_cosio-d20"}},
        {"05-model-models", {"appBar.tab.structure", "expand:group.structures"}},
        {"06-model-space-group", {"group.space_group"}},
        {"07-model-cell", {"group.cell"}},
        {"08-model-atom-site", {"group.atom_site"}},
        {"09-model-text-mode", {text}},
        {"10-experiment-experiments", {experiment, "expand:group.experiments"}},
        {"11-experiment-profile-shape", {"group.peak"}},
        {"12-experiment-background", {"group.background"}},
        {"13-analysis-basic", {"appBar.tab.analysis"}},
        {"14-analysis-extra-minimizer", {extras, "group.minimizer"}},
        {"15-summary", {"appBar.tab.report"}},
        {"16-summary-preferences", {"appBar.button.preferences"}},
    };
    // ... then the capabilities edi has and the original had not (§1.7, §5b, §15.4) ...
    steps_.push_back({"17-experiment-profile-selector", QStringList{"choose:OK"}  // close the Preferences dialog
                                                            + open_example("pd-neut-cwl_lbco-hrpt")
                                                            + QStringList{experiment, basic, "group.peak", "peak.type"}});
    steps_.push_back({"18-experiment-tch", {"choose:Thompson-Cox-Hastings pseudo-Voigt (TCH) + Finger-Cox-Jephcoat asymmetry (FCJ)"}});
    steps_.push_back({"19-experiment-extras", {extras}});
    steps_.push_back({"20-experiment-tof", open_example("pd-neut-tof_si-sepd")
                                               + QStringList{experiment, basic, "group.peak"}});
    steps_.push_back({"21-structure-extras", {"appBar.tab.structure", extras, "group.scattering_length"}});
    steps_.push_back({"22-analysis-fitting-mode", {"appBar.tab.analysis", extras, "group.fitting_mode"}});
    steps_.push_back({"23-experiment-text", {experiment, text}});
    steps_.push_back({"24-analysis-text", {"appBar.tab.analysis", text}});
    // The Report page's Text tab shows the project's `_metadata.created`, which a loaded example takes
    // from the clock, so it cannot be a pin: the Report page of the TOF project instead.
    steps_.push_back({"25-report-tof", {"appBar.tab.report"}});
    steps_.push_back({"26-experiment-loaded",
                      open_example("pd-neut-cwl_cosio-d20")
                          + QStringList{experiment, basic,
                                        "load-experiments:pd-neut-cwl_lbco-hrpt/project/experiments/hrpt.edi",
                                        // The offscreen software renderer draws the new experiment's
                                        // background rows unclipped until the page is drawn anew;
                                        // leaving and returning redraws it.
                                        "appBar.tab.analysis", experiment}});
    steps_.push_back({"27-experiment-xray", open_example("pd-xray-cwl_pbso4-lab") + QStringList{experiment, extras,
                                                                                          "group.scattering_source"}});
    // ... then the owner's review notes, each on the page it changed (the note-to-image map is
    // docs/dev/design/app-review-captures.json): the constant-wavelength instrument, the linked structure table,
    // the Extras peak group, the Analysis sidebar with a parameter selected, and the Report's Text at a
    // pinned time; then the dark theme and "system" through the platform seam, the status bar included; then
    // the Project Text tab and the new loop tables; and back to light for the rest.
    const QString analysis = QStringLiteral("appBar.tab.analysis");
    // The review notes are captured on the Co2SiO4 test project's own state, its saved reflections included.
    steps_.push_back({"t2-01-instrument-cw", open_cli_project("pd-neut-cwl_cosio-d20_start-1")
                                                 + QStringList{experiment, basic, "group.instrument"}});
    steps_.push_back({"t2-02-linked-structure", {"group.linked_structure"}});
    steps_.push_back({"t2-03-experiment-extras-peak", {extras, "group.peak"}});
    steps_.push_back({"t2-04-analysis-slider", {analysis, basic, "parameters.row.0"}});
    // The Report page's Text tab holds the report's own settings, not the project's CIF, so nothing is scrolled to.
    steps_.push_back({"t2-05-report-text",
                      {"pin-time:28 Sep 2026 12:00:00", QStringLiteral("appBar.tab.report"), text}});
    steps_.push_back({"t2-06-dark-experiment", {"theme:dark", experiment, basic}});
    steps_.push_back({"t2-07-dark-analysis", {analysis, basic}});
    steps_.push_back({"t2-08-dark-structure-text", {"appBar.tab.structure", text}});
    steps_.push_back({"t2-09-system-dark-report", {"platform:dark", "theme:system", QStringLiteral("appBar.tab.report")}});
    steps_.push_back({"t2-10-system-light-report", {"platform:light"}});
    // ... the Project Text tab, and every loop table the task made visible (note 6), expanded ...
    steps_.push_back({"t2-11-project-text", {"appBar.tab.project", text}});
    // Measured data is on Extras (edi ADR-0017 §3).
    steps_.push_back({"t2-12-measured-data", {experiment, extras, "group.data"}});
    // Measured data, open, fills the tab: it is folded again (a click on its title) to reach Reflections.
    steps_.push_back({"t2-13-reflections", {extras, "group.data", "group.refln"}});
    steps_.push_back({"t2-14-joint-fit", {analysis, extras, "group.joint_fit"}});
    steps_.push_back({"t2-15-scan-extraction", open_cli_project("pd-neut-cwl_cosio-d20_scan-324f")
                                                   + QStringList{analysis, extras, "group.sequential_fit_extract"}});
    steps_.push_back({"t2-16-fit-start", {"group.fit_parameter"}});
    // The four constant-wavelength fields, which no bundled project declares: the D20 experiment
    // loaded again with both shifts declared, as a user edits it.
    steps_.push_back({"t2-17-instrument-cw-four",
                      open_example("pd-neut-cwl_cosio-d20") + QStringList{experiment, basic, "load-experiments:pd-neut-cwl_cosio-d20/project/experiments/d20.edi"
                       "|data_d20=data_d20_shifted"
                       "|_instrument.calib_twotheta_offset 0()=_instrument.calib_twotheta_offset 0()\\n"
                       "_instrument.calib_sample_displacement 0.05\\n_instrument.calib_sample_transparency -0.02",
                       "group.instrument"}});
    // ... and every Example's Experiment page with its peak group open, where the types differ most; a single
    // crystal has no peak, so its extinction group instead, in the light theme. The first returns to the light theme
    // the rest are captured in. Each opens its example from Home, so `--demo-only ex-<id>` captures one alone.
    const QStringList start = {QStringLiteral("appBar.tab.home"), QStringLiteral("home.start"),
                               QStringLiteral("expand:group.examples")};
    for (const QString& id : ExampleListModel::bundledIds()) {
        const bool crystal = id.startsWith(QLatin1String("sc-"));
        const QStringList theme = crystal || steps_.back().image.startsWith(QLatin1String("t2-"))
                                      ? QStringList{"theme:light"}
                                      : QStringList{};
        const QString group = crystal ? QStringLiteral("group.extinction") : QStringLiteral("group.peak");
        steps_.push_back({QStringLiteral("ex-") + id, theme + start + open_example(id) + QStringList{experiment, basic, group}});
    }
    // ... and the anisotropic ADP draft on the Structure page: the Atomic displacement group, a site shown as Uani,
    // the ADP atom view with its probability, and the space-group name picker with its search field.
    steps_.push_back({"c13-01-atomic-displacement", open_example("pd-neut-cwl_cosio-d20")
                                                        + QStringList{"appBar.tab.structure", basic,
                                                                      "group.atom_site_aniso"}});
    steps_.push_back({"c13-02-adp-uani", {"atomSiteAdp.type.1", "choose:Uani"}});
    steps_.push_back({"c13-03-adp-view", {extras, "group.appearance", "structure.appearance.atomView", "choose:adp"}});
    steps_.push_back({"c13-04-space-group-name", {basic, "group.space_group", "spaceGroup.nameHM"}});
    // A name typed into the search field: red while it matches nothing, then a whole space group, whose
    // structure the view redraws.
    steps_.push_back({"c13-05-space-group-no-match", QStringList{"key:Escape"} + open_example("pd-neut-tof_ceo2-pearl")
                                                         + QStringList{"appBar.tab.structure", basic, "group.space_group",
                                                                       "spaceGroup.nameHM", "type:Pnmc"}});
    steps_.push_back({"c13-06-space-group-changed", {"key:Escape", "spaceGroup.nameHM", "type:Im-3m", "key:Return"}});
    // The pattern of the new space group, then the IT number typed: back to F m -3 m, with its default code.
    steps_.push_back({"c13-07-space-group-pattern", {"appBar.tab.experiment"}});
    steps_.push_back({"c13-08-space-group-number", {"appBar.tab.structure", "spaceGroup.itNumber", "key:Ctrl+A",
                                                    "type:225", "key:Return"}});
    // A number outside 1-230, typed: red, and not applied.
    steps_.push_back({"c13-09-space-group-number-invalid", {"spaceGroup.itNumber", "key:Ctrl+A", "type:999"}});
    // The diagnostics view, from Preferences > Develop, then both dialogs closed.
    steps_.push_back({"c13-10-diagnostics", {"key:Escape", "appBar.button.preferences", "preferences.tab.develop",
                                             "preferences.diagnostics"}});
    steps_.push_back({"c13-11-diagnostics-closed", {"choose:OK", "choose:OK"}});
    // ... then ideas no capture above shows (edi ADR-0017): the Experiment type grid three
    // wide (§2), and Measured data's one increment where the steps are equal (§6; t2-12 shows the range) ...
    steps_.push_back({"t4-01-experiment-type", open_example("pd-neut-cwl_lbco-hrpt")
                                                   + QStringList{experiment, basic, "expand:group.experiments"}});
    steps_.push_back({"t4-02-measured-data-uniform", {extras, "group.data"}});
    // ... and the messages (ideas 24-26; §14): the example that always has three, counted in the status bar
    // before they are viewed, listed in the dialog, and counted again after it closes; then a refused
    // calculation's error in the list, below a loader warning and over its neutral chart placeholder. No
    // bundled project is refused, so another project's experiment is loaded: its preferred orientation
    // names a structure this project does not have. The project is not a scan, which keeps its one
    // template experiment and refuses a second.
    // The example that always has messages is a verification project, which the app does not bundle (ADR-0031).
    steps_.push_back({"t4-03-messages-not-viewed", {"appBar.tab.project", "open-cli-project:pd-neut-tof_fe_pseudo-voigt"}});
    steps_.push_back({"t4-04-messages-list", {"statusBar.warnings"}});
    steps_.push_back({"t4-05-messages-viewed", {"choose:OK"}});
    steps_.push_back({"t4-06-messages-error",
                      open_example("pd-neut-cwl_cosio-d20")
                          + QStringList{experiment, basic,
                                        "load-experiments:pd-neut-cwl_lbco-hrpt/project/experiments/hrpt.edi",
                                        "statusBar.warnings"}});
    // ... and the About dialog, last: it stays open.
    steps_.push_back({"28-home-about", {"choose:OK",  // close the Messages dialog
                                        "appBar.tab.home", "home.about"}});
    // ... and the fit area, the fitting buttons, the block selector in the main view's tab bar, the Experiments
    // explorer with its Fit column, type selectors and Create experiment, and a searchable combo box. Each
    // opens its example from Home, so `--demo-only t16-` runs them alone.
    steps_.push_back({"t16-01-analysis", start + open_example("pd-neut-cwl_cosio-d20") + QStringList{analysis, basic}});
    steps_.push_back({"t16-02-fit-running", {"fitting.start", "capture-now"}});
    steps_.push_back({"t16-03-fit-done", {"wait-fit"}});
    steps_.push_back({"t16-04-fit-results", {"statusBar.fit.outcome"}});
    steps_.push_back({"t16-05-experiments", {"choose:OK", experiment, basic, "expand:group.experiments"}});
    steps_.push_back({"t16-06-structure", {"appBar.tab.structure", basic}});
    steps_.push_back({"t16-07-narrow", {"resize:900x768", experiment}});
    steps_.push_back({"t16-08-lif", QStringList{"resize:1280x768"} + start + open_cli_project("pd-xray-cwl_lif_single")
                                         + QStringList{experiment, basic, "expand:group.experiments"}});
    steps_.push_back({"t16-08-create-experiment", {"experiments.create"}});
    steps_.push_back({"t16-09-create-tof", {"experimentType.beamMode", "choose:time-of-flight"}});
    steps_.push_back({"t16-09-create-text", {text}});
    steps_.push_back({"t16-10-create-undone", {basic, "appBar.button.undo"}});
    steps_.push_back({"t16-11-alias-search", start + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                                                 + QStringList{analysis, extras, "expand:group.alias", "aliases.append",
                                                               "alias.parameter.0"}});
    steps_.push_back({"t16-12-alias-search-filtered", {"type:scale"}});
    // The owner's review of the first look (2026-10-05): the selector row at the top of the main area, its
    // list and the outcome icons, on a project with two structures and two experiments and on one with one each.
    const QString structure = QStringLiteral("appBar.tab.structure");
    const QString blocks = QStringLiteral("mainArea.blocks.box");
    const QString close = QStringLiteral("key:Escape");
    steps_.push_back({"t16-20-beer-structure", start + open_example("pd-neut-tof_ferrite-austenite-beer")
                                                   + QStringList{structure, basic}});
    steps_.push_back({"t16-21-beer-structure-list", {blocks}});
    steps_.push_back({"t16-22-beer-experiment", {close, experiment, basic}});
    steps_.push_back({"t16-23-beer-experiment-list", {blocks}});
    steps_.push_back({"t16-24-beer-analysis-fitted", {close, analysis, basic, "fitting.start", "wait-fit", "choose:OK"}});
    steps_.push_back({"t16-25-beer-analysis-list", {blocks}});
    steps_.push_back({"t16-26-beer-experiment-fitted", {close, experiment, basic}});
    steps_.push_back({"t16-27-cosio-structure", start + open_example("pd-neut-cwl_cosio-d20")
                                                    + QStringList{structure, basic}});
    steps_.push_back({"t16-28-cosio-experiment", {experiment, basic}});
    steps_.push_back({"t16-29-cosio-experiment-list", {blocks}});
    steps_.push_back({"t16-30-cosio-analysis", {close, analysis, basic}});
    steps_.push_back({"t16-31-lbco-structure", start + open_example("pd-neut-cwl_lbco-hrpt")
                                                   + QStringList{structure, basic}});
    steps_.push_back({"t16-32-lbco-experiment", {experiment, basic}});
    steps_.push_back({"t16-33-lbco-analysis", {analysis, basic}});
    // A scan's datasets as experiments: the bundled 162-file example, before any scan has been fitted.
    steps_.push_back({"t16-50-scan-experiment", start + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                                    + QStringList{experiment, basic, "expand:group.experiments"}});
    steps_.push_back({"t16-51-scan-list", {blocks}});
    steps_.push_back({"t16-52-scan-dataset-5", {"key:Escape", "show:experiments.list:4", "experiments.row.4"}});
    // A scan run from the app on the 162-file example: running (the S3 bar, Follow on), stopped part way,
    // continued to the end, and the Evolution tab after it.
    steps_.push_back({"t16-60-scan-ready", QStringList{"resize:1280x960"} + start
                                               + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                               + QStringList{analysis, basic, "reveal:fitting.start"}});
    steps_.push_back({"t16-61-scan-running", {"fitting.start", "wait-files:40", "capture-now"}});
    steps_.push_back({"t16-62-scan-stopped", {"fitting.start", "wait-fit"}});
    steps_.push_back({"t16-63-scan-continue", {"choose:OK"}});
    steps_.push_back({"t16-64-scan-done", {"fitting.start", "wait-fit"}});
    steps_.push_back({"t16-65-scan-evolution", {"choose:OK", "mainArea.analysis.tab.evolution"}});
    steps_.push_back({"t16-66-scan-experiment", {experiment, basic, "expand:group.experiments"}});
    // After the scan: the single mode (a setting: the results stay current); a single fit on the shown dataset makes
    // it the template dataset, tagged in the lists, and marks the results out of date on the status bar.
    steps_.push_back({"t16-67-single-mode", {analysis, extras, "expand:group.fitting_mode", "fittingMode.type",
                                              "choose:Single experiment", basic, "mainArea.analysis.tab.evolution"}});
    steps_.push_back({"t16-68-single-fit-on-dataset",
                      {"mainArea.analysis.tab.fitting", "reveal:fitting.start", "fitting.start", "wait-fit"}});
    // The single fit's correlations are the fitted dataset's, shown on its Correlations tab.
    steps_.push_back({"t16-68b-single-fit-correlations", {"choose:OK", "mainArea.analysis.tab.correlations"}});
    steps_.push_back({"t16-69-template-dataset", {experiment, basic, "show:experiments.list:161"}});
    // The scan's buttons follow its fits (owner, 2026-10-06): all fitted, Start fitting is disabled and Reset fits
    // enabled; Reset clears them (Start again); a stop leaves Continue. The Evolution chart zooms to a dragged box
    // and resets with a right click; the Project page shortens a long dataset list.
    steps_.push_back({"t16-70-scan-all-fitted", QStringList{"resize:1280x960"} + start
                                                    + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                                    + QStringList{analysis, basic, "reveal:fitting.start", "fitting.start",
                                                                  "wait-fit", "choose:OK"}});
    steps_.push_back({"t16-71-scan-reset", {"fitting.reset"}});
    steps_.push_back({"t16-72-scan-stopped-continue", {"fitting.start", "wait-files:40", "fitting.start", "wait-fit",
                                                        "choose:OK"}});
    steps_.push_back({"t16-73-evolution-zoomed", {"fitting.start", "wait-fit", "choose:OK",
                                                   "mainArea.analysis.tab.evolution",
                                                   "drag:evolution.pointer:0.2,0.1,0.6,0.9"}});
    steps_.push_back({"t16-74-evolution-reset", {"right-click:evolution.pointer"}});
    steps_.push_back({"t16-75-project-names", {"appBar.tab.project"}});
    // The Evolution tab while a fresh scan of the 324-file example runs: a point per fitted dataset as it completes,
    // the first parameter chosen, the marker on the dataset being fitted.
    steps_.push_back({"t16-76-home", {QStringLiteral("appBar.tab.home")}});
    steps_.push_back({"t16-77-evolution-mid-scan", start
                                                       + open_cli_project("pd-neut-cwl_cosio-d20_scan-324f")
                                                       + QStringList{analysis, basic, "reveal:fitting.start",
                                                                     "mainArea.analysis.tab.evolution", "fitting.start",
                                                                     "wait-files:200", "capture-now"}});
    steps_.push_back({"t16-78-evolution-stopped", {"fitting.start", "wait-fit", "choose:OK"}});
    // A single crystal (Tb2Ti2O7 on HEiDi): the reflections chart and table on Experiment and Analysis, in both themes,
    // before and after a fit of its scale.
    steps_.push_back({"sc-01-tb2ti2o7-experiment-light",
                      QStringList{"resize:1280x768", "theme:light"} + start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                          + QStringList{experiment, basic}});
    steps_.push_back({"sc-02-tb2ti2o7-analysis-light", {analysis, basic}});
    steps_.push_back({"sc-03-tb2ti2o7-fit-results-light", {"fitting.start", "wait-fit"}});
    steps_.push_back({"sc-03b-tb2ti2o7-analysis-fitted-light", {"choose:OK"}});
    steps_.push_back({"sc-04-tb2ti2o7-analysis-dark", {"theme:dark"}});
    steps_.push_back({"sc-05-tb2ti2o7-experiment-dark", {experiment, basic}});
    steps_.push_back({"sc-05b-tb2ti2o7-reflections-dark", {extras, "expand:group.refln"}});
    steps_.push_back({"sc-05c-tb2ti2o7-f-dark", {basic, "singleCrystal.toolbar.quantity", "choose:F"}});
    steps_.push_back({"sc-05d-tb2ti2o7-narrow-dark", {"singleCrystal.toolbar.quantity", "choose:F²", "resize:960x768"}});
    steps_.push_back({"sc-05e-tb2ti2o7-narrow-light", {"theme:light"}});
    steps_.push_back({"sc-05f-tb2ti2o7-isotropic-extinction", QStringList{"resize:1280x768"} + start
                                                                  + QStringList{"appBar.tab.project", "open-cli-project:sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction"}
                                                                  + QStringList{analysis, basic, "fitting.start", "wait-fit"}});
    steps_.push_back({"sc-05g-tb2ti2o7-isotropic-extinction-fitted", {"choose:OK", experiment, basic, "expand:group.extinction"}});
    steps_.push_back({"sc-06-pr2nio4-experiment-light",
                      QStringList{"theme:light"} + start + open_example("sc-neut-cwl_pr2nio4-5c2")
                          + QStringList{experiment, basic}});
    steps_.push_back({"sc-07-pr2nio4-analysis-dark", {"theme:dark", analysis, basic}});
    steps_.push_back({"sc-07a-pr2nio4-fit-results-dark", {"fitting.start", "wait-fit"}});
    steps_.push_back({"sc-07a2-pr2nio4-fitted-dark", {"choose:OK"}});
    steps_.push_back({"sc-07a3-pr2nio4-correlations-dark", {"mainArea.analysis.tab.correlations"}});
    steps_.push_back({"sc-07b-pr2nio4-zoomed",
                      {"mainArea.analysis.tab.fitting", "drag:singleCrystal.pointer:0.05,0.6,0.4,0.95"}});
    steps_.push_back({"sc-07c-pr2nio4-panned", {"chart.toolbar.pan", "drag:singleCrystal.pointer:0.5,0.5,0.3,0.3",
                                                "chart.toolbar.zoom"}});
    // The report of the fit: its chart and reflections on the Report page, then saved as HTML and PDF where
    // EDI_DEMO_REPORT_DIR names, else in the run's own folder.
    steps_.push_back({"sc-07r1-pr2nio4-report-chart", {QStringLiteral("appBar.tab.report"), "reveal:report.singleCrystal"}});
    const QString sc_report = qEnvironmentVariable("EDI_DEMO_REPORT_DIR");
    steps_.push_back({"sc-07r2-pr2nio4-report-saved",
                      {"save-as:" + (sc_report.isEmpty() ? QStringLiteral("report-sc") : sc_report), "report.writesPdf",
                       "report.save"}});
    steps_.push_back({"sc-07d-pr2nio4-created", {experiment, basic, "expand:group.experiments", "experiments.create"}});
    steps_.push_back({"sc-07e-pr2nio4-created-single-crystal", {"experimentType.sampleForm", "choose:single crystal"}});
    steps_.push_back({"sc-07f-pr2nio4-created-loaded", {"load-reflections"}});
    steps_.push_back({"sc-08-pr2nio4-messages", {"statusBar.warnings"}});
    steps_.push_back({"sc-09-pr2nio4-hover", {"choose:OK", "hover:singleCrystal.pointer:0.003,0.997"}});
    // Both single-crystal fitting examples' report charts after loading and after a fit; then the extinction's s.u.
    // after it is fixed and fitted again, and the reflection table filling the Extras sidebar. Run only when asked
    // (`--demo-only sccheck-`).
    const QStringList fit_sc{analysis, basic, "reveal:fitting.start", "fitting.start", "wait-fit", "choose:OK"};
    const QStringList sc_report_steps{QStringLiteral("appBar.tab.report"), "reveal:report.singleCrystal"};
    steps_.push_back({"sccheck-01-tb2ti2o7-report-loaded",
                      QStringList{"resize:1280x768", "theme:light"} + start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                          + sc_report_steps});
    steps_.push_back({"sccheck-02-tb2ti2o7-report-fitted", fit_sc + sc_report_steps});
    steps_.push_back({"sccheck-03-pr2nio4-report-loaded", start + open_example("sc-neut-cwl_pr2nio4-5c2") + sc_report_steps});
    steps_.push_back({"sccheck-04-pr2nio4-report-fitted", fit_sc + sc_report_steps});
    steps_.push_back({"sccheck-05-pr2nio4-extinction-free-fitted",
                      QStringList{analysis, basic, "parameters.nameFilter", "type:extinction", "parameters.free.0", "parameters.free.1",
                                  "reveal:fitting.start", "fitting.start", "wait-fit", "choose:OK"}});
    steps_.push_back({"sccheck-06-pr2nio4-extinction-fixed-refitted",
                      {"parameters.free.0", "parameters.free.1", "reveal:fitting.start", "fitting.start", "wait-fit",
                       "choose:OK"}});
    steps_.push_back({"sccheck-07-pr2nio4-reflections-extras", {experiment, extras, "expand:group.refln"}});
    steps_.push_back({"sccheck-08-pr2nio4-reflections-taller", {"resize:1280x1000"}});
    steps_.push_back({"sccheck-09-created-single-crystal",
                      QStringList{"resize:1280x768"} + start + open_example("sc-neut-cwl_pr2nio4-5c2")
                          + QStringList{experiment, basic, "expand:group.experiments", "experiments.create",
                                        "experimentType.sampleForm", "choose:single crystal"}});
    steps_.push_back({"sccheck-09b-created-back-to-powder", {"experimentType.sampleForm", "choose:powder"}});
    // A single crystal saved in another project, loaded where its structure is missing: the message, the link in
    // red, the structure's own text, then the link pointed at the project's structure.
    steps_.push_back({"sccheck-09c-loaded-missing-link",
                      start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                          + QStringList{experiment, basic, "expand:group.experiments",
                                        "load-experiments:sc-neut-cwl_pr2nio4-5c2/project/experiments/llb_5c2.edi"}});
    steps_.push_back({"sccheck-09d-missing-link-message", {"statusBar.warnings"}});
    steps_.push_back({"sccheck-09e-missing-link-red", {"choose:OK", "expand:group.linked_structure"}});
    steps_.push_back({"sccheck-09f-structure-text", {"appBar.tab.structure", text}});
    steps_.push_back({"sccheck-09g-relinked", {experiment, basic, "linkedStructure.structureId.0", "choose:tb2ti2o7"}});
    // A time-of-flight single crystal's Instrument group: its reflections' wavelength band, read-only.
    steps_.push_back({"sccheck-14-taurine-instrument",
                      start + open_example("sc-neut-tof_taurine-senju") + QStringList{experiment, basic, "group.instrument"}});
    // A single crystal's reflections through the row's Load data: FullProf's .int (its wavelength taken), a plain
    // h k l F² su file, then a malformed one; each into a created experiment linked to the project's structure.
    // The files are named by EDI_DEMO_SC_FILES, a folder holding prnio.int, tbti.dat and malformed.dat.
    const QString sc_files = qEnvironmentVariable("EDI_DEMO_SC_FILES");
    const QStringList create_sc{experiment, basic, "expand:group.experiments", "experiments.create",
                                "experimentType.sampleForm", "choose:single crystal"};
    steps_.push_back({"sccheck-10a-int-loaded", QStringList{"resize:1280x768"} + start + open_example("sc-neut-cwl_pr2nio4-5c2")
                                                    + create_sc + QStringList{"load-reflections:" + sc_files + "/prnio.int"}});
    steps_.push_back({"sccheck-10b-int-message", {"statusBar.warnings"}});
    steps_.push_back({"sccheck-10c-int-wavelength", {"choose:OK", "expand:group.instrument"}});
    steps_.push_back({"sccheck-10d-int-reflections", {extras, "expand:group.refln"}});
    // The two single crystals fit together, each with its own scale.
    steps_.push_back({"sccheck-10e-int-joint-fitted", {analysis, basic, "reveal:fitting.start", "fitting.start", "wait-fit"}});
    steps_.push_back({"sccheck-10f-dat-loaded", QStringList{"choose:OK"} + start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                                                    + create_sc + QStringList{"load-reflections:" + sc_files + "/tbti.dat"}});
    steps_.push_back({"sccheck-10g-dat-message", {"statusBar.warnings"}});
    steps_.push_back({"sccheck-10h-malformed", {"choose:OK", experiment, basic, "experiments.create", "experimentType.sampleForm",
                                                "choose:single crystal", "load-reflections:" + sc_files + "/malformed.dat"}});
    // The extinction type selector: the Tb2Ti2O7 example's mixed type with its three fields, the type choices, and
    // type II with the domain radius alone.
    // Taurine's six datasets: every experiment on one chart on the Stacked tabs, its legend shown, and the Pattern
    // chart's legend behind its button.
    steps_.push_back({"sccheck-15a-taurine-stacked-experiment", QStringList{"resize:1280x768"} + start + open_example("sc-neut-tof_taurine-senju")
                                                                    + QStringList{experiment, basic, "mainArea.experiment.tab.stacked"}});
    steps_.push_back({"sccheck-15b-taurine-stacked-analysis", {analysis, basic, "mainArea.analysis.tab.stacked"}});
    steps_.push_back({"sccheck-15c-taurine-pattern-legend", {"mainArea.analysis.tab.fitting", "chart.toolbar.legend"}});
    steps_.push_back({"sccheck-11-extinction-mixed", QStringList{"resize:1280x768"} + start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                                                         + QStringList{experiment, basic, "expand:group.extinction"}});
    steps_.push_back({"sccheck-11b-extinction-types", {"extinction.type"}});
    steps_.push_back({"sccheck-11c-extinction-type-2", {"choose:Isotropic Becker-Coppens type II (analytical)"}});
    steps_.push_back({"sccheck-11d-extinction-type-1", {"extinction.type", "choose:Isotropic Becker-Coppens type I (analytical)"}});
    steps_.push_back({"sccheck-11e-extinction-larson", {"extinction.type", "choose:Isotropic Larson (empirical)"}});
    steps_.push_back({"sccheck-11f-extinction-larson-anisotropic", {"extinction.type", "choose:Anisotropic Larson (empirical)"}});
    // Taurine on time of flight: the example's chart, its reflections with their wavelengths, and its fit.
    steps_.push_back({"sccheck-12a-taurine-experiment", QStringList{"resize:1280x768"} + start
                                                            + open_example("sc-neut-tof_taurine-senju") + QStringList{experiment, basic}});
    steps_.push_back({"sccheck-12b-taurine-reflections", {extras, "expand:group.refln"}});
    steps_.push_back({"sccheck-12c-taurine-fitted", {analysis, basic, "reveal:fitting.start", "fitting.start", "wait-fit"}});
    // The fit's cutoff (FullProf's Rmub 3), and the observed threshold above the reflection table switched to F.
    steps_.push_back({"sccheck-12d-taurine-fitted-reflections", {"choose:OK", extras, "expand:group.refine_ls"}});
    steps_.push_back({"sccheck-12e-taurine-observed-on-f",
                      {experiment, extras, "expand:group.refln", "reflns.thresholdBasis", "choose:F"}});
    // The aliases and constraints that share the first dataset's extinction, each id column as wide as its ids.
    steps_.push_back({"sccheck-12f-taurine-aliases", {analysis, extras, "expand:group.alias"}});
    steps_.push_back({"sccheck-12g-taurine-constraints", {"expand:group.constraint", "reveal:constraints.list"}});
    // At the 3 su cutoff: the reflection table's fit column and the chart's dimmed points, on both views.
    steps_.push_back({"sccheck-12h-taurine-fit-use", {experiment, extras, "expand:group.refln"}});
    steps_.push_back({"sccheck-12i-taurine-fit-use-stacked", {"mainArea.experiment.tab.stacked"}});
    // On F axes the weak reflections the cutoff leaves out spread away from the origin; then back to F².
    steps_.push_back({"sccheck-12j-taurine-fit-use-on-f",
                      {"mainArea.experiment.tab.chart", "singleCrystal.toolbar.quantity", "choose:F"}});
    steps_.push_back({"sccheck-12k-taurine-back-on-f-squared", {"singleCrystal.toolbar.quantity", "choose:F²"}});
    // Stacked with the selected dataset highlighted (the default), a point's experiment and h k l on hover, a click
    // there selecting that experiment, then every experiment drawn alike with the selection bold in the legend.
    steps_.push_back({"sccheck-12l-taurine-stacked-highlight", {"mainArea.experiment.tab.stacked"}});
    steps_.push_back({"sccheck-12m-taurine-stacked-hover", {"hover:singleCrystal.pointer:0.12,0.86"}});
    steps_.push_back({"sccheck-12n-taurine-stacked-click-selects",
                      {"drag:singleCrystal.pointer:0.12,0.86,0.12,0.86", "hover:singleCrystal.pointer:0.12,0.86"}});
    steps_.push_back({"sccheck-12o-taurine-stacked-all-alike", {"singleCrystal.toolbar.highlight"}});
    steps_.push_back({"sccheck-12p-taurine-stacked-highlight-again", {"singleCrystal.toolbar.highlight"}});
    // The Tb2Ti2O7 verification project's scale-only fit, its scale shown in the parameter table.
    steps_.push_back({"sccheck-13-tb2ti2o7-basic-fitted", QStringList{"resize:1280x768"} + start
                                                              + QStringList{"appBar.tab.project", "open-cli-project:sc-neut-cwl_tb2ti2o7-heidi_basic"}
                                                              + QStringList{analysis, basic, "reveal:fitting.start", "fitting.start", "wait-fit",
                                                                            "choose:OK", "parameters.nameFilter", "type:scale"}});
    // LiF is a verification project, which the app does not bundle (ADR-0031): it opens from the CLI projects.
    steps_.push_back({"t16-40-created-saved-reopened",
                      QStringList{"resize:1280x768"} + start
                          + QStringList{"appBar.tab.project", "open-cli-project:pd-xray-cwl_lif_single", experiment, basic, "expand:group.experiments",
                      "experiments.create", "save-as:created", "open-project:created", experiment, "mainArea.blocks.box",
                       "choose:experiment1 · experiment1.edi", text, "scroll-to:text.view:_data_range"}});
    // The Correlations tab: empty before a fit, the fitted matrix, a correlation level and a parameter
    // count typed into the toolbar, and a joint fit's two experiments.
    const QString correlations = QStringLiteral("mainArea.analysis.tab.correlations");
    steps_.push_back({"t17-01-correlations-empty",
                      QStringList{"resize:1280x768"} + start + open_example("pd-neut-cwl_cosio-d20")
                          + QStringList{analysis, basic, correlations}});
    steps_.push_back({"t17-02-correlations-fitted", {"fitting.start", "wait-fit", "choose:OK"}});
    steps_.push_back({"t17-03-correlations-ten", {"correlations.toolbar.parameters.number", "key:Ctrl+A", "type:10", "key:Return"}});
    steps_.push_back({"t17-04-correlations-level", {"correlations.toolbar.level.number", "key:Ctrl+A", "type:0.5", "key:Return"}});
    steps_.push_back({"t17-07-correlations-all", {"correlations.toolbar.parameters.number", "key:Ctrl+A", "type:43", "key:Return"}});
    steps_.push_back({"t17-05-beer-correlations", start + open_example("pd-neut-tof_ferrite-austenite-beer")
                                                      + QStringList{analysis, basic, "fitting.start", "wait-fit",
                                                                    "choose:OK", correlations}});
    steps_.push_back({"t17-06-beer-second-experiment", {"mainArea.blocks.down"}});
    // The main-view chart toolbars centred in one line (owner, 2026-10-11): the structure view and the pattern chart.
    steps_.push_back({"t17-08-structure-toolbar", {"appBar.tab.structure", basic}});
    steps_.push_back({"t17-09-pattern-toolbar", {analysis, "mainArea.analysis.tab.fitting"}});
    // The owner's app findings (2026-10-08): 9, Diagnostics' Show a button the Logging level box's size; 7, the sample
    // form and scattering type disabled while one choice is supported.
    steps_.push_back({"t17-20-diagnostics-show", {"appBar.button.preferences", "preferences.tab.develop"}});
    steps_.push_back({"t17-21-experiment-type", QStringList{"key:Escape"} + start + open_example("pd-neut-cwl_cosio-d20")
                                                    + QStringList{experiment, basic, "expand:group.experiments"}});
    // 5 and 6: without an experiment Analysis and Summary are disabled; without a structure Experiment too.
    steps_.push_back({"t17-22-no-experiment", {"experiments.remove.0"}});
    steps_.push_back({"t17-23-no-structure", {"appBar.tab.structure", basic, "expand:group.structures", "structures.remove.0"}});
    // 1: Create project's location, one separator between the folder and the name (not accepted: the demo writes
    // no project into the user's documents).
    steps_.push_back({"t17-25-create-project", {"key:Escape", "appBar.tab.project", basic, "expand:group.getStarted", "project.create", "createProject.name", "type:Corr"}});
    // 3 and 4: the Wyckoff position column and its list; a new atom on position a, and the structure's Text with no
    // error.
    steps_.push_back({"t17-27-wyckoff-column", QStringList{"key:Escape"} + start + open_example("pd-neut-cwl_lbco-hrpt")
                                                   + QStringList{"appBar.tab.structure", basic, "expand:group.atom_site"}});
    steps_.push_back({"t17-28-wyckoff-list", {"atomSite.wyckoffLetter.0"}});
    steps_.push_back({"t17-29-new-atom", {"key:Escape", "atomSites.append"}});
    steps_.push_back({"t17-29b-new-atom-text", {text}});
    // A sequential scan keeps each dataset's correlations from its own fit, and the Correlations tab follows the
    // shown dataset (owner, 2026-10-11).
    steps_.push_back({"t17-40-scan-correlations", QStringList{"key:Escape"} + start
                                                      + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                                                      + QStringList{analysis, basic, "fitting.start", "wait-fit",
                                                                    "choose:OK", "mainArea.analysis.tab.correlations"}});
    steps_.push_back({"t17-41-scan-second-dataset", {"mainArea.blocks.up"}});
    steps_.push_back({"t17-42-scan-first-dataset", {"mainArea.blocks.up"}});
    // A save keeps every dataset's correlations in analysis.edi, and the reopened project shows them.
    steps_.push_back({"t17-43-scan-reopened", {"save-as:scan", "open-project:scan", analysis,
                                               "mainArea.analysis.tab.correlations"}});
    steps_.push_back({"t17-44-scan-reopened-other-dataset", {"mainArea.blocks.down"}});
    // Large intensities on the y axes in NumberText's scientific form, clear of the titles (owner, 2026-10-11): the
    // example's experiment loaded again with its scale raised, so the calculated pattern reaches about 1e9.
    steps_.push_back({"t17-50-axis-scientific",
                      QStringList{"key:Escape"} + start + open_example("pd-neut-cwl_lbco-hrpt")
                          + QStringList{experiment, basic,
                                        "load-experiments:pd-neut-cwl_lbco-hrpt/project/experiments/"
                                        "hrpt.edi|data_hrpt=data_large|lbco 9()=lbco 30000000()",
                                        analysis, "mainArea.analysis.tab.fitting"}});
    // The fitting modes that apply, by their names (owner, 2026-10-11): one experiment, single only; several, joint
    // with its weights; a scan, its two modes and single.
    steps_.push_back({"t17-72-mode-single", QStringList{"key:Escape"} + start + open_example("pd-neut-cwl_lbco-hrpt")
                                                + QStringList{analysis, extras, "expand:group.fitting_mode"}});
    steps_.push_back({"t17-73-mode-joint", start + open_example("pd-neut-tof_ferrite-austenite-beer")
                                               + QStringList{analysis, extras, "expand:group.fitting_mode",
                                                             "expand:group.joint_fit"}});
    steps_.push_back({"t17-74-mode-scan", start + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                                              + QStringList{analysis, extras, "expand:group.fitting_mode", "fittingMode.type"}});
    // A click on the parameter table's "free" title: the shown rows' state, then all of them fixed at once.
    steps_.push_back({"t17-75-free-header", start + open_example("pd-neut-cwl_lbco-hrpt")
                                                + QStringList{analysis, basic, "parameters.freeHeader"}});
    steps_.push_back({"t17-76-free-header-fixed", {"parameters.freeHeader.fixed"}});
    // Reset to the initial state lands on the Project page (owner, 2026-10-11).
    steps_.push_back({"t17-77-reset", {"appBar.button.reset"}});
    // 8: a created experiment's Load data… button, left-aligned under Data file.
    steps_.push_back({"t17-24-load-data", start + open_example("pd-neut-cwl_cosio-d20")
                                              + QStringList{experiment, basic, "expand:group.experiments", "experiments.create"}});
    steps_.push_back({"t17-24b-load-data-dark", {"theme:dark"}});
    // Duplicate experiment and Duplicate structure, and the disabled Load from COD (the owner, 2026-10-11).
    steps_.push_back({"t17-60-duplicate-experiment", {"theme:light", "mainArea.blocks.up", "experiments.duplicate"}});
    steps_.push_back({"t17-61-duplicate-structure",
                      {"appBar.tab.structure", basic, "expand:group.structures", "structures.duplicate"}});
    // The polynomial and Chebyshev backgrounds' terms, and a type switch that asks before it removes the points.
    const QString background = QStringLiteral("expand:group.background");
    steps_.push_back({"t17-10-polynomial-terms",
                      QStringList{"theme:light"} + start + open_example("pd-neut-tof_ceo2-pearl")
                          + QStringList{experiment, basic, background}});
    steps_.push_back({"t17-11-polynomial-term-removed", {"background.removeTerm.2"}});
    steps_.push_back({"t17-12-polynomial-term-appended", {"background.appendTerm"}});
    steps_.push_back({"t17-13-chebyshev-terms", start + open_example("pd-neut-tof_cecoal-polaris")
                                                    + QStringList{experiment, basic, background}});
    steps_.push_back({"t17-14-type-question", start + open_example("pd-neut-cwl_cosio-d20")
                                                  + QStringList{experiment, basic, background, "background.type",
                                                                "choose:chebyshev"}});
    steps_.push_back({"t17-15-type-chebyshev", {"choose:OK"}});
    steps_.push_back({"t17-16-chebyshev-term-appended", {"background.appendTerm", "background.appendTerm"}});
    // Name points by position (owner, 2026-10-11): the line-segment points' ids from their positions, and the
    // parameter table naming them so.
    steps_.push_back({"t17-80-name-points", start + open_example("pd-neut-cwl_lbco-hrpt")
                                                + QStringList{experiment, basic, "expand:group.background",
                                                              "background.namePoints"}});
    steps_.push_back({"t17-81-named-points-in-table",
                      {analysis, basic, "parameters.nameFilter", "type:background"}});
    // Every loop row is named by its id in the parameter table (owner, 2026-10-11): the Chebyshev terms here.
    steps_.push_back({"t17-17-term-ids-in-table", start + open_example("pd-neut-tof_cecoal-polaris")
                                                      + QStringList{analysis, basic, "parameters.nameFilter",
                                                                    "type:background"}});
    // Timing: the 162-file scan fitted and reset, each interval on a monotonic clock with its work checked. Run only
    // when asked (`--demo-only perf-`); the two controls must fail.
    // Every Preferences tab in both themes, to check that each has the same label column and control width. Run only
    // when asked (`--demo-only prefs-`).
    if (only.startsWith(QLatin1String("prefs-"))) {
        for (const QString theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString name = QStringLiteral("prefs-") + theme + QStringLiteral("-");
            steps_.push_back({name + "1-prompts", {"key:Escape", "theme:" + theme, "appBar.button.preferences",
                                                   "preferences.tab.prompts"}});
            steps_.push_back({name + "2-updates", {"preferences.tab.updates"}});
            steps_.push_back({name + "3-appearance", {"preferences.tab.appearance"}});
            steps_.push_back({name + "4-projects", {"preferences.tab.projects"}});
            steps_.push_back({name + "5-experimental", {"preferences.tab.experimental"}});
            steps_.push_back({name + "6-develop", {"preferences.tab.develop"}});
        }
    }
    // The Report page's sidebar, Main and Text, in both themes. Run only when asked (`--demo-only report-sidebar-`).
    if (only.startsWith(QLatin1String("report-sidebar-"))) {
        const QString report = QStringLiteral("appBar.tab.report");
        steps_.push_back({"report-sidebar-1-light", QStringList{"resize:1280x960", "theme:light"} + start +
                                                        open_example("pd-neut-cwl_lbco-hrpt") +
                                                        QStringList{report, basic}});
        steps_.push_back({"report-sidebar-2-light-text", {text}});
        steps_.push_back({"report-sidebar-3-dark-text", {"theme:dark"}});
        steps_.push_back({"report-sidebar-4-dark", {basic}});
    }
    // A fitted scan's report, its preview at the evolution charts. Run only when asked (`--demo-only report-scan-`).
    if (only.startsWith(QLatin1String("report-scan-"))) {
        // EDI_DEMO_REPORT_PROJECT names a fitted scan to open instead of fitting the bundled one.
        const QString fitted = qEnvironmentVariable("EDI_DEMO_REPORT_PROJECT");
        const QStringList open =
            fitted.isEmpty() ? start + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f") +
                                   QStringList{analysis, basic, "reveal:fitting.start", "fitting.start", "wait-fit",
                                               "choose:OK"}
                             : QStringList{"open-project:" + fitted};
        steps_.push_back({"report-scan-1-evolution", QStringList{"resize:1280x960"} + open +
                                                         QStringList{"appBar.tab.report", "reveal:report.evolution"}});
        // Saved where EDI_DEMO_REPORT_DIR names, so the report files outlive the run, else in the run's own folder.
        const QString kept = qEnvironmentVariable("EDI_DEMO_REPORT_DIR");
        steps_.push_back({"report-scan-2-saved", {"save-as:" + (kept.isEmpty() ? QStringLiteral("report-scan") : kept),
                                                  "report.writesPdf", "report.save"}});
    }
    // The Evolution tab of a scan before and after its fit, with the parameter list open. Run only when asked
    // (`--demo-only evolution-`).
    if (only.startsWith(QLatin1String("evolution-"))) {
        const QStringList scan = QStringList{"resize:1280x960", "theme:light"} + start
                                 + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                 + QStringList{analysis, basic, "mainArea.analysis.tab.evolution"};
        steps_.push_back({"evolution-1-unfitted", scan});
        steps_.push_back({"evolution-2-unfitted-parameters", {"evolution.parameters"}});
        steps_.push_back({"evolution-3-fitted", {"key:Escape", "reveal:fitting.start", "fitting.start", "wait-fit",
                                                 "choose:OK", "mainArea.analysis.tab.evolution"}});
        steps_.push_back({"evolution-4-fitted-parameters", {"evolution.parameters"}});
    }
    // Every colour scheme in both themes, on the Analysis page's chart of a two-structure example. Run only when asked
    // (`--demo-only schemes-`).
    if (only.startsWith(QLatin1String("schemes-"))) {
        QStringList schemes;
        for (const std::string_view name : edi::colour_scheme_names()) {
            const std::string_view title = edi::colour_scheme_title(edi::colour_scheme_or_default(name));
            schemes.append(QString::fromUtf8(title.data(), static_cast<qsizetype>(title.size())));
        }
        const auto pick = [](const QString& scheme) {
            return QStringList{"appBar.button.preferences", "preferences.tab.appearance", "preferences.colours",
                               "choose:" + scheme, "choose:OK"};
        };
        steps_.push_back({"schemes-0-list", QStringList{"resize:1280x960", "theme:light"} + start
                                                + QStringList{"appBar.button.preferences", "preferences.tab.appearance",
                                                              "preferences.colours"}});
        for (const QString theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            for (int i = 0; i < schemes.size(); ++i) {
                QStringList actions = i == 0 && theme == QLatin1String("light")
                                          ? QStringList{"key:Escape", "key:Escape"} + start
                                                + open_example("pd-neut-tof_ferrite-austenite-beer")
                                                + QStringList{analysis, basic}
                                          : QStringList{};
                actions += QStringList{"theme:" + theme} + pick(schemes[i]);
                QString name = schemes[i].toLower();
                name.replace(QLatin1Char(' '), QLatin1Char('-'));
                steps_.push_back(
                    {QStringLiteral("schemes-%1-%2-%3").arg(theme).arg(i + 1, 2, 10, QLatin1Char('0')).arg(name),
                     actions});
            }
        }
    }
    // The Structure page's tables, the current structure's row marked, in both themes. Run only when asked
    // (`--demo-only tables-`).
    if (only.startsWith(QLatin1String("tables-"))) {
        steps_.push_back({"tables-1-structure-light",
                          QStringList{"resize:1280x960", "theme:light"} + start + open_example("pd-neut-tof_ferrite-austenite-beer")
                              + QStringList{"appBar.tab.structure", basic, "group.atom_site_aniso"}});
        steps_.push_back({"tables-2-structure-dark", {"theme:dark"}});
        steps_.push_back({"tables-3-report-dark", {"appBar.tab.report"}});
        steps_.push_back({"tables-4-report-light", {"theme:light"}});
        steps_.push_back({"tables-5-report-again", {"theme:light"}});
    }
    // Each structure's curve: the Analysis chart with the toolbar's switch on, in both themes, and the Experiment page's
    // data table with a column per structure. Run only when asked (`--demo-only curves-`).
    if (only.startsWith(QLatin1String("curves-"))) {
        const QString experiment = QStringLiteral("appBar.tab.experiment");
        steps_.push_back({"curves-1-analysis-light",
                          QStringList{"resize:1280x960", "theme:light"} + start + open_example("pd-neut-tof_ferrite-austenite-beer")
                              + QStringList{analysis, basic, "chart.toolbar.structureCurves"}});
        steps_.push_back({"curves-2-analysis-zoomed", {"drag:chart.pointer:0.74,0.05,0.80,0.95"}});
        steps_.push_back({"curves-3-analysis-dark", {"theme:dark"}});
        steps_.push_back({"curves-4-data-table", {"theme:light", experiment, extras, "group.data"}});
        steps_.push_back({"curves-5-analysis-off", {analysis, "chart.toolbar.structureCurves"}});
    }
    // The one pattern chart on the Structure, Experiment and Analysis pages: a zoom made on one page shows on the others.
    // Run only when asked (`--demo-only onechart-`).
    if (only.startsWith(QLatin1String("onechart-"))) {
        const QString experiment = QStringLiteral("appBar.tab.experiment");
        steps_.push_back({"onechart-1-analysis-zoomed",
                          QStringList{"resize:1280x960", "theme:light"} + start + open_example("pd-neut-tof_ferrite-austenite-beer")
                              + QStringList{analysis, basic, "drag:chart.pointer:0.74,0.05,0.80,0.95", "chart.toolbar.structureCurves"}});
        steps_.push_back({"onechart-2-experiment", {experiment}});
        steps_.push_back({"onechart-3-structure-pattern", {"appBar.tab.structure", "mainArea.structure.tab.pattern"}});
        steps_.push_back({"onechart-4-structure-view", {"mainArea.structure.tab.view"}});
        steps_.push_back({"onechart-5-analysis-again", {analysis, "chart.toolbar.structureCurves"}});
    }
    // The owner's first local test: latp_scan's three structures on the Experiment page, a zoom with each structure's
    // curve off, then the curves on and off again. Run only when asked (`--demo-only latp-`).
    if (only.startsWith(QLatin1String("latp-"))) {
        const QString experiment = QStringLiteral("appBar.tab.experiment");
        steps_.push_back({"latp-1-experiment", {"resize:1280x960", "theme:light", "open-cli-project:pd-xray-cwl_latp_scan-4f",
                                                experiment, basic}});
        steps_.push_back({"latp-2-zoomed", {"drag:chart.pointer:0.30,0.05,0.45,0.95"}});
        steps_.push_back({"latp-3-curves-on", {"chart.toolbar.structureCurves"}});
        steps_.push_back({"latp-4-curves-off", {"chart.toolbar.structureCurves"}});
        steps_.push_back({"latp-5-reset", {"chart.toolbar.reset"}});
    }
    // The owner's stray structure fill: ncaf's five banks, one structure, on log and square-root y with each
    // structure's curve off, then on and off again. Run only when asked (`--demo-only ncaf-`).
    if (only.startsWith(QLatin1String("ncaf-"))) {
        const QString yscale = QStringLiteral("chart.toolbar.yscale");
        steps_.push_back({"ncaf-1-log-off", {"resize:1280x960", "theme:dark", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5",
                                             analysis, basic, yscale, "choose:Log"}});
        steps_.push_back({"ncaf-2-sqrt-off", {yscale, "choose:Square root"}});
        steps_.push_back({"ncaf-3-sqrt-on", {"chart.toolbar.structureCurves"}});
        steps_.push_back({"ncaf-4-log-on", {yscale, "choose:Log"}});
        steps_.push_back({"ncaf-5-linear-on", {yscale, "choose:Linear"}});
        steps_.push_back({"ncaf-6-linear-off", {"chart.toolbar.structureCurves"}});
        steps_.push_back({"ncaf-7-log-off", {yscale, "choose:Log"}});
        steps_.push_back({"ncaf-8-bank2-sqrt-on", {"mainArea.blocks.down", yscale, "choose:Square root", "chart.toolbar.structureCurves"}});
        steps_.push_back({"ncaf-9-bank2-sqrt-off", {"chart.toolbar.structureCurves"}});
    }
    // The owner's retest: each structure's curve on (the default), off and on again through the toolbar on latp_scan, on
    // every y scale, then cosio's one structure and ncaf's banks, each opened with its full view.
    // Run only when asked (`--demo-only retest-`).
    if (only.startsWith(QLatin1String("retest-"))) {
        const QString experiment = QStringLiteral("appBar.tab.experiment");
        const QString yscale = QStringLiteral("chart.toolbar.yscale");
        const QString curves = QStringLiteral("chart.toolbar.structureCurves");
        steps_.push_back({"retest-01-latp-on", {"resize:1280x960", "theme:light", "open-cli-project:pd-xray-cwl_latp_scan-4f",
                                                experiment, basic, "drag:chart.pointer:0.30,0.05,0.45,0.95"}});
        steps_.push_back({"retest-02-latp-off", {curves}});
        steps_.push_back({"retest-03-latp-on", {curves}});
        steps_.push_back({"retest-04-latp-log", {yscale, "choose:Log"}});
        steps_.push_back({"retest-05-latp-sqrt", {yscale, "choose:Square root"}});
        steps_.push_back({"retest-06-cosio", {"open-cli-project:pd-neut-cwl_cosio-d20_start-4", analysis, basic}});
        steps_.push_back({"retest-07-cosio-linear", {yscale, "choose:Linear"}});
        steps_.push_back({"retest-08-ncaf", {"open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic}});
        steps_.push_back({"retest-09-ncaf-log", {yscale, "choose:Log"}});
        steps_.push_back({"retest-10-ncaf-off", {curves}});
    }
    // The owner's sequential fit: cosio's 155 patterns fitted with each structure's curve on (the default) and zoomed,
    // captured while the scan runs and after it. Run only when asked (`--demo-only seqfit-`).
    if (only.startsWith(QLatin1String("seqfit-"))) {
        steps_.push_back({"seqfit-1-running", QStringList{"resize:1280x960", "theme:light"} + start
                                                  + open_example("pd-neut-cwl_cosio-d20_scan")
                                                  + QStringList{analysis, basic, "reveal:fitting.start", "fitting.start",
                                                                "wait-files:10", "drag:chart.pointer:0.55,0.05,0.65,0.95",
                                                                "wait-files:30", "capture-now"}});
        steps_.push_back({"seqfit-2-running", {"wait-files:60", "capture-now"}});
        steps_.push_back({"seqfit-3-done", {"wait-fit", "choose:OK"}});
    }
    // The chart legend of latp_scan's three structures, each listed once as its Bragg peaks, in both themes. Run only
    // when asked (`--demo-only legend-`).
    if (only.startsWith(QLatin1String("legend-"))) {
        steps_.push_back({"legend-1-light", {"resize:1280x960", "theme:light", "open-cli-project:pd-xray-cwl_latp_scan-4f",
                                             QStringLiteral("appBar.tab.experiment"), basic, "chart.toolbar.legend"}});
        steps_.push_back({"legend-2-dark", {"theme:dark"}});
    }
    // A scan's stacked patterns and 2D map (edi ADR-0041) on cosio's 155 patterns, in both themes, before a fit and
    // while one runs, with the views' toolbars: the shown dataset's line, also on Evolution; the x box offering d only
    // after a calculation; the map on a log scale in Inferno and in Greys, zoomed on d-spacing; a narrow zoom drawn
    // from the measured points, reset by a secondary click; only the included range, on and off; a narrow chart's
    // toolbar on two centred lines. Then a joint fit, the WISH 5-bank example, on d-spacing, Stacked and Map, in both
    // themes. Run only when asked (`--demo-only scanviews-`).
    // Every page at the supported minimum (AppSizes.minimumAppWidth × minimumAppHeight), its sidebar scrolled to its
    // last inputs, to check every control can be reached. Run only when asked (`--demo-only minimum-`).
    if (only.startsWith(QLatin1String("minimum-"))) {
        steps_.push_back({"minimum-1-home", {"resize:1024x640", "theme:light", "appBar.tab.home"}});
        steps_.push_back({"minimum-2-project", {"open-cli-project:pd-neut-cwl_lbco-hrpt_start-4", "appBar.tab.project", basic}});
        steps_.push_back({"minimum-3-structure", {"appBar.tab.structure", basic}});
        steps_.push_back({"minimum-4-structure-space-group", {"expand:group.space_group", "reveal:spaceGroup.crystalSystem"}});
        steps_.push_back({"minimum-5-experiment", {"appBar.tab.experiment", basic}});
        steps_.push_back({"minimum-6-experiment-background", {"expand:group.background", "reveal:background.type"}});
        steps_.push_back({"minimum-7-analysis", {"appBar.tab.analysis", basic}});
        steps_.push_back({"minimum-8-report", {"appBar.tab.report"}});
    }
    // A click on the Pattern chart's legend hides the measured curve, keeping the y range; with the range fitted to the
    // visible curves, showing it and hiding it again fits the range each time (the owner, 2026-10-25). Run only when
    // asked (`--demo-only legendhide-`).
    if (only.startsWith(QLatin1String("legendhide-"))) {
        steps_.push_back({"legendhide-1-keep", {"resize:1280x960", "theme:light", "preference:chartHiddenRange=keep",
                                                "open-cli-project:pd-neut-cwl_lbco-hrpt_start-4", "appBar.tab.analysis", basic,
                                                "mainArea.analysis.tab.fitting", "chart.toolbar.legend", "chart.legend.toggle"}});
        steps_.push_back({"legendhide-2-shown", {"preference:chartHiddenRange=fit", "chart.legend.toggle"}});
        steps_.push_back({"legendhide-3-fit", {"chart.legend.toggle"}});
        // The Bragg row, the legend's last: its structure icon and the tick strip's label disabled with it.
        steps_.push_back({"legendhide-4-bragg", {"preference:chartHiddenRange=keep", "drag:chart.legend:0.5,0.9,0.5,0.9"}});
    }
    // The same three patterns as lines on the Pattern chart and on Stacked at full height, drawn on the GPU and then by
    // the painter, to compare the two charts' line quality (edi ADR-0041 §9). Run only when asked (`--demo-only
    // lines-`), at any QT_SCALE_FACTOR with EDI_DEMO_ANY_RATIO set.
    if (only.startsWith(QLatin1String("lines-"))) {
        steps_.push_back({"lines-1-pattern", {"resize:1280x960", "theme:light", "preference:scanRenderer=gpu",
                                              "open-cli-project:pd-neut-cwl_cosio-d20_scan-3f", "appBar.tab.analysis", basic,
                                              "mainArea.analysis.tab.fitting"}});
        steps_.push_back({"lines-2-stacked", {"mainArea.analysis.tab.stacked", "scanView.stacked.toolbar.spacing",
                                              "choose:Overlay", "wait-scan:stacked"}});
        // The same drawn by the painter, as a machine without a GPU draws it.
        steps_.push_back({"lines-3-stacked-painter", {"preference:scanRenderer=software", "wait-scan:stacked"}});
    }
    if (only.startsWith(QLatin1String("scanviews-"))) {
        steps_.push_back({"scanviews-01-stacked-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                            + open_example("pd-neut-cwl_cosio-d20_scan")
                                                            + QStringList{analysis, basic, "mainArea.analysis.tab.stacked"}});
        steps_.push_back({"scanviews-02-map-light", {"mainArea.analysis.tab.map"}});
        steps_.push_back({"scanviews-03-map-light-stepped", {"scanView.map.toolbar.smooth"}});
        steps_.push_back({"scanviews-04-map-light-log-inferno",
                          {"scanView.map.toolbar.smooth", "scanView.map.toolbar.yscale", "choose:Log",
                           "scanView.map.toolbar.colourMap", "choose:Inferno"}});
        steps_.push_back({"scanviews-05-map-light-running", {"reveal:fitting.start", "fitting.start", "wait-files:40",
                                                            "capture-now"}});
        steps_.push_back({"scanviews-06-stacked-light-running", {"mainArea.analysis.tab.stacked", "wait-files:60",
                                                                "capture-now"}});
        steps_.push_back({"scanviews-07-evolution-light-running", {"mainArea.analysis.tab.evolution", "wait-files:70",
                                                                  "capture-now"}});
        steps_.push_back({"scanviews-08-stacked-dark-running", {"theme:dark", "mainArea.analysis.tab.stacked",
                                                               "wait-files:80", "capture-now"}});
        steps_.push_back({"scanviews-09-map-dark-running", {"mainArea.analysis.tab.map", "wait-files:100", "capture-now"}});
        steps_.push_back({"scanviews-10-evolution-dark", {"wait-fit", "choose:OK", "mainArea.analysis.tab.evolution"}});
        steps_.push_back({"scanviews-11-map-dark-greys", {"mainArea.analysis.tab.map", "scanView.map.toolbar.colourMap",
                                                         "choose:Greys"}});
        steps_.push_back({"scanviews-12-map-dark-d-zoom", {"scanView.map.toolbar.xaxis", "choose:x: d-spacing",
                                                          "drag:scanView.map.pointer:0.05,0.2,0.45,0.7"}});
        steps_.push_back({"scanviews-13-stacked-dark-narrow-zoom", {"mainArea.analysis.tab.stacked",
                                                                   "scanView.stacked.toolbar.xaxis", "choose:2θ",
                                                                   "drag:scanView.stacked.pointer:0.40,0.02,0.46,0.6"}});
        steps_.push_back({"scanviews-14-stacked-dark-secondary-reset", {"right-click:scanView.stacked.pointer"}});
        steps_.push_back({"scanviews-15-stacked-dark-included-only", {"scanView.stacked.toolbar.includedRange"}});
        steps_.push_back({"scanviews-16-stacked-light-included-only", {"theme:light"}});
        steps_.push_back({"scanviews-17-map-light-included-only", {"mainArea.analysis.tab.map"}});
        steps_.push_back({"scanviews-17b-map-light-full-range", {"scanView.map.toolbar.includedRange"}});
        steps_.push_back({"scanviews-18-map-light-narrow-two-lines", {"resize:1000x960"}});
        steps_.push_back({"scanviews-19-joint-stacked-light-d",
                          {"resize:1280x960", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic,
                           "mainArea.analysis.tab.stacked", "scanView.stacked.toolbar.xaxis", "choose:x: d-spacing"}});
        steps_.push_back({"scanviews-20-joint-map-light-d", {"mainArea.analysis.tab.map"}});
        steps_.push_back({"scanviews-21-joint-map-dark-d", {"theme:dark"}});
        steps_.push_back({"scanviews-22-joint-stacked-dark-d", {"mainArea.analysis.tab.stacked"}});
        steps_.push_back({"scanviews-23-joint-stacked-dark-tof", {"scanView.stacked.toolbar.xaxis", "choose:TOF"}});
    }
    // The pattern chart's four measured styles (the owner, 2026-10-22), in both themes, with the background dashed:
    // the band of measured ± s.u. (the default) with the residual's band, the line, the points with their bars, and
    // line and points; then the band zoomed in. Run only when asked (`--demo-only mstyle-`).
    if (only.startsWith(QLatin1String("mstyle-"))) {
        steps_.push_back({"mstyle-1-band-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                     + open_example("pd-neut-cwl_lbco-hrpt")
                                                     + QStringList{analysis, basic, "chart.toolbar.measuredStyle", "choose:Band"}});
        steps_.push_back({"mstyle-2-line-light", {"chart.toolbar.measuredStyle", "choose:Line"}});
        steps_.push_back({"mstyle-3-points-light", {"chart.toolbar.measuredStyle", "choose:Points"}});
        steps_.push_back({"mstyle-4-linepoints-light", {"chart.toolbar.measuredStyle", "choose:Line + points", "chart.toolbar.legend"}});
        steps_.push_back({"mstyle-5-linepoints-dark", {"theme:dark"}});
        steps_.push_back({"mstyle-6-points-dark", {"chart.toolbar.measuredStyle", "choose:Points"}});
        steps_.push_back({"mstyle-7-line-dark", {"chart.toolbar.measuredStyle", "choose:Line"}});
        steps_.push_back({"mstyle-8-band-dark", {"chart.toolbar.measuredStyle", "choose:Band", "chart.toolbar.legend"}});
        steps_.push_back({"mstyle-9-band-dark-zoom", {"drag:chart.pointer:0.30,0.05,0.42,0.95"}});
        steps_.push_back({"mstyle-10-band-light-zoom", {"theme:light"}});
    }
    // The Experiment page's Stacked and Map tabs on cosio's scan before any fit, and the Preferences' four colour
    // choices (the owner, 2026-10-22), the structures and the patterns then in different schemes, in both themes.
    // Run only when asked (`--demo-only colours-`).
    if (only.startsWith(QLatin1String("colours-"))) {
        steps_.push_back({"colours-1-experiment-stacked-light",
                          QStringList{"resize:1280x960", "theme:light"} + start
                              + open_example("pd-neut-cwl_cosio-d20_scan")
                              + QStringList{QStringLiteral("appBar.tab.experiment"), basic,
                                            "mainArea.experiment.tab.stacked"}});
        steps_.push_back({"colours-2-experiment-map-light", {"mainArea.experiment.tab.map"}});
        steps_.push_back({"colours-3-preferences", {"appBar.button.preferences", "preferences.tab.appearance"}});
        steps_.push_back({"colours-4-classic",
                          {"preferences.colours", "choose:Classic", "choose:OK", "mainArea.experiment.tab.chart"}});
        steps_.push_back({"colours-5-dark", {"theme:dark"}});
        steps_.push_back({"colours-6-experiment-stacked-dark", {"mainArea.experiment.tab.stacked"}});
    }
    // The three-dataset test scan's Stacked view, its scan-value axis labelled only over the rows (the owner, 2026-10-22), in
    // both themes. Run only when asked (`--demo-only stackrange-`).
    if (only.startsWith(QLatin1String("stackrange-"))) {
        steps_.push_back({"stackrange-1-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                    + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                                                    + QStringList{analysis, basic, "mainArea.analysis.tab.stacked"}});
        steps_.push_back({"stackrange-2-dark", {"theme:dark"}});
        steps_.push_back({"stackrange-3-map-dark", {"mainArea.analysis.tab.map"}});
    }
    // The scan views' rows labelled by scan value, by file and, thinned, on cosio's 155 patterns; the Map's scale with a
    // tick per dataset by scan value, its bands labelled by file; a zoom bringing labels back; the three-dataset scan
    // with every label (the owner, 2026-10-22). Run only when asked (`--demo-only rowlabels-`).
    if (only.startsWith(QLatin1String("rowlabels-"))) {
        steps_.push_back({"rowlabels-01-stacked-value-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                                  + open_example("pd-neut-cwl_cosio-d20_scan")
                                                                  + QStringList{analysis, basic, "mainArea.analysis.tab.stacked"}});
        steps_.push_back({"rowlabels-01b-stacked-height-4x-light", {"scanView.stacked.toolbar.height", "choose:4×"}});
        steps_.push_back({"rowlabels-01c-stacked-height-2x-light", {"scanView.stacked.toolbar.height", "choose:2×"}});
        steps_.push_back({"rowlabels-02-map-value-ticks-light", {"mainArea.analysis.tab.map"}});
        steps_.push_back({"rowlabels-02b-map-bottom-zoom-light", {"drag:scanView.map.pointer:0.1,0.82,0.9,0.995"}});
        steps_.push_back({"rowlabels-02c-map-reset-light", {"right-click:scanView.map.pointer"}});
        steps_.push_back({"rowlabels-02d-map-dense-selected-light", {"drag:scanView.map.pointer:0.5,0.93,0.5,0.93"}});
        steps_.push_back({"rowlabels-02e-stacked-dense-selected-light", {"mainArea.analysis.tab.stacked"}});
        steps_.push_back({"rowlabels-03-map-file-light", {"mainArea.analysis.tab.map", "scanView.map.toolbar.rows", "choose:File"}});
        steps_.push_back({"rowlabels-04-stacked-file-light", {"mainArea.analysis.tab.stacked"}});
        steps_.push_back({"rowlabels-05-stacked-file-zoom-light", {"drag:scanView.stacked.pointer:0.1,0.55,0.9,0.85"}});
        steps_.push_back({"rowlabels-06-stacked-file-dark", {"theme:dark", "right-click:scanView.stacked.pointer"}});
        steps_.push_back({"rowlabels-07-stacked-value-dark", {"scanView.stacked.toolbar.rows", "choose:Temperature (K)"}});
        steps_.push_back({"rowlabels-08-map-value-dark", {"mainArea.analysis.tab.map"}});
        steps_.push_back({"rowlabels-09-three-stacked-light",
                          QStringList{"theme:light"} + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                              + QStringList{analysis, basic, "mainArea.analysis.tab.stacked"}});
        steps_.push_back({"rowlabels-10-three-map-dark", {"theme:dark", "mainArea.analysis.tab.map"}});
        steps_.push_back({"rowlabels-11-joint-stacked-datablock-light",
                          {"theme:light", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic,
                           "mainArea.analysis.tab.stacked"}});
        steps_.push_back({"rowlabels-11b-joint-stacked-tof-reversed-light", {"scanView.stacked.toolbar.reverse"}});
        steps_.push_back({"rowlabels-12-joint-map-datablock-dark", {"theme:dark", "mainArea.analysis.tab.map"}});
        // A datablock Map, each band its own bank: smooth, blended only across each band's edge; stepped, hard edges.
        // On d each bank's coverage ends at its own band's edges either way.
        steps_.push_back({"rowlabels-13-joint-map-d-smooth-dark", {"scanView.map.toolbar.xaxis", "choose:x: d-spacing",
                                                                   "drag:scanView.map.pointer:0.5,0.5,0.5,0.5"}});
        steps_.push_back({"rowlabels-14-joint-map-d-smooth-light", {"theme:light"}});
        steps_.push_back({"rowlabels-15-joint-map-d-stepped-light", {"scanView.map.toolbar.smooth"}});
        steps_.push_back({"rowlabels-16-joint-map-d-stepped-dark", {"theme:dark", "scanView.map.toolbar.smooth"}});
    }
    // Every colour map the scan views offer, on cosio's map on a log scale, in both themes (the six the owner chose on
    // 2026-10-26). Run only when asked (`--demo-only mapcands-`).
    if (only.startsWith(QLatin1String("mapcands-"))) {
        const QStringList titles = {"Blue-Red", "Viridis", "Batlow", "Inferno", "Lapaz", "Greys"};
        steps_.push_back({"mapcands-00-open", QStringList{"resize:1280x960", "theme:light"} + start
                                                  + open_example("pd-neut-cwl_cosio-d20_scan")
                                                  + QStringList{analysis, basic, "mainArea.analysis.tab.map",
                                                                "scanView.map.toolbar.yscale", "choose:Log"}});
        for (const QString theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            // The list is taller than the window, so a far entry cannot be clicked: the first map is chosen from the
            // list, and each next one by a key on the closed box (open it to give it the keyboard, close it, step),
            // down the list in the light theme and back up it in the dark.
            for (qsizetype k = 0; k < titles.size(); ++k) {
                const qsizetype i = theme == QLatin1String("light") ? k : titles.size() - 1 - k;
                const bool first = theme == QLatin1String("light") && k == 0;
                QStringList actions = first ? QStringList{"scanView.map.toolbar.colourMap", "choose:" + titles[i]}
                                      : k == 0 ? QStringList{}
                                               : QStringList{"scanView.map.toolbar.colourMap", "key:Escape",
                                                             theme == QLatin1String("light") ? "key:Down" : "key:Up"};
                if (k == 0) {
                    actions.prepend("theme:" + theme);
                }
                if (theme == QLatin1String("dark") && i == 0) {
                    // The last one inverted, to show the direction box.
                    actions << "scanView.map.toolbar.direction" << "choose:Inverted";
                }
                const QString slug = titles[i].section(QLatin1Char(' '), 0, 0).toLower();
                steps_.push_back({QStringLiteral("mapcands-%1-%2-%3").arg(theme).arg(i + 1, 2, 10, QLatin1Char('0')).arg(slug),
                                  actions});
            }
        }
    }
    // Element colours drawn flat, in both themes (edi ADR-0047): PbSO4's pale S and dark Pb in the Atom sites table, the
    // structure view's legend and the parameter table. Run only when asked (`--demo-only elements-`).
    if (only.startsWith(QLatin1String("elements-"))) {
        steps_.push_back({"elements-1-structure-light", {"resize:1280x960", "theme:light",
                                                         "open-cli-project:pd-xray-cwl_pbso4-lab_round-robin",
                                                         "appBar.tab.structure", basic}});
        steps_.push_back({"elements-2-analysis-light", {analysis, basic}});
        steps_.push_back({"elements-3-structure-dark", {"theme:dark", "appBar.tab.structure", basic}});
        steps_.push_back({"elements-4-analysis-dark", {analysis, basic}});
    }
    // The figure palettes and the scan views' controls (the owner, 2026-10-26), in both themes: the 3-file scan on the
    // pattern chart and Stacked, with its legend and the background subtracted, and the Preferences' colour order; the
    // 162-file scan on Stacked at Wide, Overlay and Separate, zoomed, with the short legend, and on the Map in Blue-Red
    // on Auto; NCAF's five banks on d; taurine's element icons. Each project is opened once, a copy of it being made
    // only once. Run only when asked (`--demo-only figures-`).
    if (only.startsWith(QLatin1String("figures-"))) {
        const QString stacked = QStringLiteral("mainArea.analysis.tab.stacked");
        const QString map = QStringLiteral("mainArea.analysis.tab.map");
        const QString pattern = QStringLiteral("mainArea.analysis.tab.fitting");
        const QString spacing = QStringLiteral("scanView.stacked.toolbar.spacing");
        const QString legend = QStringLiteral("scanView.stacked.toolbar.legend");
        const QString preferences = QStringLiteral("appBar.button.preferences");
        const QString colourMap = QStringLiteral("scanView.map.toolbar.colourMap");
        const QStringList figures[] = {
            {"figures-01-3f-pattern-light", "resize:1280x960", "theme:light",
             "open-cli-project:pd-neut-cwl_cosio-d20_scan-3f", analysis, basic, pattern},
            {"figures-02-3f-pattern-subtracted-light", "chart.toolbar.subtractBackground"},
            {"figures-03-3f-stacked-subtracted-light", stacked, "wait-scan:stacked"},
            {"figures-04-3f-stacked-legend-light", "scanView.stacked.toolbar.subtractBackground", legend},
            {"figures-05-3f-preferences-light", preferences, "preferences.tab.appearance"},
            {"figures-06-3f-preferences-dark", "theme:dark"},
            {"figures-07-3f-stacked-legend-dark", "key:Escape"},
            {"figures-08-3f-stacked-subtracted-dark", legend, "scanView.stacked.toolbar.subtractBackground"},
            {"figures-09-3f-pattern-subtracted-dark", pattern},
            {"figures-10-3f-pattern-dark", "chart.toolbar.subtractBackground"},
            {"figures-11-162f-stacked-wide-dark", "open-cli-project:pd-neut-cwl_cosio-d20_scan-162f", analysis, basic,
             stacked, "wait-scan:stacked"},
            {"figures-12-162f-stacked-legend-dark", legend},
            {"figures-13-162f-stacked-overlay-dark", legend, spacing, "choose:Overlay"},
            {"figures-14-162f-stacked-separate-dark", spacing, "choose:Separate"},
            {"figures-15-162f-stacked-separate-zoom-dark", "drag:scanView.stacked.pointer:0.55,0.70,0.75,0.95"},
            {"figures-16-162f-map-dark", "scanView.stacked.toolbar.reset", spacing, "choose:Wide", map,
             "wait-scan:map"},
            {"figures-17-162f-map-colour-maps-dark", colourMap},
            {"figures-18-162f-map-subtracted-dark", "key:Escape", "scanView.map.toolbar.subtractBackground"},
            {"figures-19-162f-map-subtracted-light", "theme:light"},
            {"figures-20-162f-map-colour-maps-light", "scanView.map.toolbar.subtractBackground", colourMap},
            {"figures-21-162f-map-light", "key:Escape"},
            {"figures-22-162f-stacked-separate-zoom-light", stacked, spacing, "choose:Separate",
             "drag:scanView.stacked.pointer:0.55,0.70,0.75,0.95"},
            {"figures-23-162f-stacked-separate-light", "scanView.stacked.toolbar.reset"},
            {"figures-24-162f-stacked-overlay-light", spacing, "choose:Overlay"},
            {"figures-25-162f-stacked-legend-light", spacing, "choose:Wide", legend},
            {"figures-26-162f-stacked-wide-light", legend},
            // The banks are calculated once opened, which gives their d columns: d is chosen a step later.
            {"figures-27-ncaf-stacked-light", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic,
             stacked, "wait-scan:stacked"},
            {"figures-28-ncaf-stacked-d-light", "scanView.stacked.toolbar.xaxis", "choose:x: d-spacing",
             "wait-scan:stacked"},
            {"figures-29-ncaf-map-d-light", map, "wait-scan:map"},
            {"figures-30-ncaf-map-d-dark", "theme:dark"},
            {"figures-31-ncaf-stacked-d-dark", stacked, "wait-scan:stacked"},
            {"figures-32-taurine-atom-sites-dark", "open-cli-project:sc-neut-tof_taurine_fit", "appBar.tab.structure",
             basic, "expand:group.atom_site", "reveal:atomSite.fractX.8"},
            {"figures-33-taurine-vesta-dark", "structure.toolbar.colors", "choose:VESTA"},
            {"figures-34-taurine-vesta-light", "theme:light"},
            {"figures-35-taurine-atom-sites-light", "structure.toolbar.colors", "choose:Jmol"},
            {"figures-36-taurine-preferences-light", preferences, "preferences.tab.appearance"},
            {"figures-37-taurine-preferences-dark", "theme:dark"},
        };
        for (const QStringList& step : figures) {
            steps_.push_back({step.front(), step.mid(1)});
        }
    }
    // The owner's chart fixes of 2026-10-27, in both themes: on cosio's 162-file scan, Stacked with the shown pattern
    // highlighted and not, its read-out, its legend and a click hiding a pattern, the included range rescaling at
    // Overlay, and the Map with its read-out and its black plot area in the dark; ncaf's banks; the 3-file scan's
    // pattern rescaled to the included range; heidi's correlations numbered. Run only when asked (`--demo-only fixes-`).
    if (only.startsWith(QLatin1String("fixes-"))) {
        const QString stacked = QStringLiteral("mainArea.analysis.tab.stacked");
        const QString map = QStringLiteral("mainArea.analysis.tab.map");
        const QString spacing = QStringLiteral("scanView.stacked.toolbar.spacing");
        const QStringList fixes[] = {
            {"fixes-01-162f-stacked-highlight-light", "resize:1280x960", "theme:light",
             "open-cli-project:pd-neut-cwl_cosio-d20_scan-162f", analysis, basic, stacked, "wait-scan:stacked"},
            {"fixes-02-162f-stacked-hover-light", "hover:scanView.stacked.pointer:0.5,0.5"},
            {"fixes-03-162f-stacked-highlight-off-light", "scanView.stacked.toolbar.highlight"},
            {"fixes-04-162f-stacked-legend-light", "scanView.stacked.toolbar.legend"},
            {"fixes-05-162f-stacked-legend-hidden-light", "drag:scanView.stacked.pointer:0.93,0.035,0.93,0.035"},
            {"fixes-06-162f-stacked-legend-highlight-light", "scanView.stacked.toolbar.highlight"},
            {"fixes-07-162f-stacked-overlay-included-light", spacing, "choose:Overlay",
             "scanView.stacked.toolbar.includedRange"},
            {"fixes-08-162f-map-light", map, "wait-scan:map"},
            {"fixes-09-162f-map-hover-light", "hover:scanView.map.pointer:0.5,0.5"},
            {"fixes-10-162f-map-dark", "theme:dark"},
            {"fixes-11-162f-map-hover-dark", "hover:scanView.map.pointer:0.5,0.5"},
            {"fixes-12-162f-stacked-overlay-included-dark", stacked, "wait-scan:stacked"},
            {"fixes-13-162f-stacked-overlay-dark", "scanView.stacked.toolbar.includedRange"},
            {"fixes-14-162f-stacked-wide-dark", "scanView.stacked.toolbar.legend", spacing, "choose:Wide"},
            {"fixes-15-ncaf-stacked-dark", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic,
             stacked, "wait-scan:stacked"},
            {"fixes-16-ncaf-stacked-hover-dark", "hover:scanView.stacked.pointer:0.3,0.5"},
            {"fixes-17-ncaf-map-dark", map, "wait-scan:map"},
            {"fixes-18-ncaf-map-light", "theme:light"},
            {"fixes-19-ncaf-stacked-light", stacked, "wait-scan:stacked"},
            {"fixes-20-3f-pattern-included-light", "open-cli-project:pd-neut-cwl_cosio-d20_scan-3f", analysis, basic,
             "mainArea.analysis.tab.fitting", "chart.toolbar.includedRange"},
            {"fixes-21-3f-pattern-light", "chart.toolbar.includedRange"},
            {"fixes-22-heidi-correlations-light", "open-cli-project:sc-neut-cwl_tb2ti2o7-heidi_fit", analysis, basic,
             "mainArea.analysis.tab.correlations"},
            {"fixes-23-heidi-correlations-dark", "theme:dark"},
        };
        for (const QStringList& step : fixes) {
            steps_.push_back({step.front(), step.mid(1)});
        }
    }
    // A click on any cell makes its row current, an editable cell's too, and every table marks the current row the
    // same way (the owner, 2026-10-22): Atom sites and the parameter table. Run only when asked (`--demo-only rows-`).
    if (only.startsWith(QLatin1String("rows-"))) {
        steps_.push_back({"rows-1-atom-sites", {"resize:1280x960", "theme:light",
                                                "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", "appBar.tab.structure",
                                                basic, "expand:group.atom_site"}});
        steps_.push_back({"rows-2-atom-sites-edit-row-4", {"reveal:atomSite.fractX.3", "atomSite.fractX.3"}});
        steps_.push_back({"rows-3-parameters-edit-row-5", {"key:Escape", analysis, basic, "reveal:parameters.value.4",
                                                           "parameters.value.4"}});
        steps_.push_back({"rows-4-parameters-name-row-2", {"key:Escape", "reveal:parameters.name.1", "parameters.name.1"}});
        steps_.push_back({"rows-5-parameters-down-row-3", {"key:Down"}});
        steps_.push_back({"rows-6-parameters-free-row-4", {"reveal:parameters.free.3", "parameters.free.3"}});
    }
    // The About window and its two popups, in both themes. Run only when asked (`--demo-only about-`).
    if (only.startsWith(QLatin1String("about-"))) {
        for (const QString theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString first = theme == QLatin1String("light") ? QStringLiteral("resize:1280x960") : QStringLiteral("key:Escape");
            steps_.push_back({"about-" + theme + "-1-window", {first, "theme:" + theme, "appBar.tab.home", "home.about"}});
            steps_.push_back({"about-" + theme + "-2-bsd", {"about.licence.BSD-3-Clause"}});
            steps_.push_back({"about-" + theme + "-3-third-party", {"key:Escape", "about.thirdParty"}});
        }
    }
    if (only.startsWith(QLatin1String("perf-"))) {
        // EDI_DEMO_PERF_PROJECT names a prepared copy to open in place, so two builds time the same input.
        const QString prepared = qEnvironmentVariable("EDI_DEMO_PERF_PROJECT");
        const QString scan = prepared.isEmpty() ? QStringLiteral("open-cli-project:pd-neut-cwl_cosio-d20_scan-162f")
                                                : QStringLiteral("open-project:") + prepared;
        steps_.push_back({"perf-162f", {scan, "timed-fit:162", "timed-reset"}});
        steps_.push_back({"perf-control-partial", {scan, "timed-fit:162:40"}});
        steps_.push_back({"perf-control-refused", {scan, "remove-scan-data", "timed-fit:162"}});
        // The scan views' frames on the 324-file scan, a 162-file scan's fit with every pattern drawn (the fit waiting
        // for each, or the display catching up) against the adaptive rule (edi ADR-0029), and slider steps on LBCO
        // before and after a fit (edi ADR-0041).
        const QString analysis = QStringLiteral("appBar.tab.analysis");
        QStringList views{"resize:1280x800", "open-cli-project:pd-neut-cwl_cosio-d20_scan-324f", analysis,
                          "mainArea.analysis.tab.stacked", "wait-scan:stacked"};
        for (const QString mode : {QStringLiteral("stacked"), QStringLiteral("map")}) {
            if (mode == QLatin1String("map")) {
                views << "mainArea.analysis.tab.map" << "wait-scan:map";
            }
            views << "timed-frames:" + mode + ":zoom:40" << "timed-frames:" + mode + ":pan:50"
                  << "timed-frames:" + mode + ":restyle:20" << "timed-frames:" + mode + ":select:20"
                  << "timed-frames:" + mode + ":data:10" << "timed-frames:" + mode + ":rows:10";
        }
        steps_.push_back({"perf-views-324f", views});
        // A data change alone on the Stacked view, to profile it.
        steps_.push_back({"perf-data-324f", {"resize:1280x800", "open-cli-project:pd-neut-cwl_cosio-d20_scan-324f", analysis,
                                             "mainArea.analysis.tab.stacked", "wait-scan:stacked",
                                             "timed-frames:stacked:data:10"}});
        // The same with the Stacked lines on the GPU, chosen as a user chooses it in Develop.
        views.insert(1, QStringLiteral("preference:scanRenderer=gpu"));
        steps_.push_back({"perf-gpu-views-324f", views});
        const QStringList updates{"resize:1280x800", scan, analysis, "sideBar.tab.settings", "expand:group.patternUpdates",
                                  "analysis.patternUpdates"};
        for (const auto& [name, choice] : {std::pair{"every", "Every pattern, fit waits for the display"},
                                           std::pair{"catchup", "Every pattern, display catches up"},
                                           std::pair{"adaptive", "Adaptive"}}) {
            steps_.push_back({QStringLiteral("perf-fit-%1-pattern").arg(QLatin1String(name)),
                              updates + QStringList{QStringLiteral("choose:") + QLatin1String(choice), "mainArea.analysis.tab.fitting",
                                                    "timed-fit:162"}});
            steps_.push_back({QStringLiteral("perf-fit-%1-stacked").arg(QLatin1String(name)),
                              updates + QStringList{QStringLiteral("choose:") + QLatin1String(choice), "mainArea.analysis.tab.stacked",
                                                    "wait-scan:stacked", "timed-fit:162"}});
        }
        const QStringList lbco{"resize:1280x800", "open-cli-project:pd-neut-cwl_lbco-hrpt_start-4", analysis,
                               "sideBar.tab.basic", "mainArea.analysis.tab.fitting", "parameters.nameFilter",
                               "type:length_a"};
        steps_.push_back({"perf-slider-lbco-1-before-fit", lbco + QStringList{"timed-slider:30"}});
        // The same steps again and again with no fit: what a growing edit history alone costs.
        steps_.push_back({"perf-slidernofit-1", lbco + QStringList{"timed-slider:30"}});
        for (int batch = 2; batch <= 4; ++batch) {
            steps_.push_back({QStringLiteral("perf-slidernofit-%1").arg(batch), {"timed-slider:30"}});
        }
        steps_.push_back({"perf-slider-lbco-2-after-fit", {"fitting.start", "wait-fit", "choose:OK", "timed-slider:30"}});
        // Note 45 says "after the fits": four more, five in all, from where the slider left the model each time.
        QStringList fits;
        for (int fit = 0; fit < 4; ++fit) {
            fits << "fitting.start" << "wait-fit" << "choose:OK";
        }
        steps_.push_back({"perf-slider-lbco-3-after-five-fits", fits + QStringList{"timed-slider:30"}});
    }
    if (!only.isEmpty()) {
        std::erase_if(steps_, [&only](const Step& step) { return !step.image.startsWith(only); });
    }
}

void DemoDriver::start() {
    if (!output_dir_.mkpath(QStringLiteral("."))) {
        fail(QStringLiteral("cannot create the output directory %1").arg(output_dir_.path()));
        return;
    }
    park_pointer();
    QTimer::singleShot(0, this, [this] { run_step(); });
}

void DemoDriver::run_step() {
    if (current_ == steps_.size()) {
        QCoreApplication::exit(0);
        return;
    }
    action_ = 0;
    next_action();
}

void DemoDriver::next_action() {
    const Step& step = steps_[current_];
    const bool unsettled = step.actions.contains(QStringLiteral("capture-now"));
    if (action_ < step.actions.size()) {
        const QString& action = step.actions.at(action_);
        ++action_;
        if (action == QLatin1String("capture-now")) {
            next_action();
            return;
        }
        if (action == QLatin1String("wait-fit")) {
            wait_fit_then([this] { settle_then([this] { next_action(); }); });
            return;
        }
        // A running scan keeps the worker busy, so its step is captured unsettled (capture-now).
        if (action.startsWith(QLatin1String("wait-files:"))) {
            wait_fit_then([this] { next_action(); }, 0, action.mid(11).toInt());
            return;
        }
        if (action.startsWith(QLatin1String("timed-fit:"))) {
            const QStringList parts = action.split(QLatin1Char(':'));
            timed_fit_then([this] { next_action(); }, parts.value(1).toInt(), parts.size() > 2 ? parts.at(2).toInt() : -1);
            return;
        }
        if (action.startsWith(QLatin1String("wait-scan:"))) {
            wait_scan_then([this] { next_action(); }, action.mid(10));
            return;
        }
        if (action.startsWith(QLatin1String("timed-frames:")) || action.startsWith(QLatin1String("timed-slider:"))) {
            const QStringList parts = action.split(QLatin1Char(':'));
            const bool done = parts.at(0) == QLatin1String("timed-frames")
                                  ? timed_frames(parts.value(1), parts.value(2), parts.value(3).toInt())
                                  : timed_slider(parts.value(1).toInt());
            if (done) {
                settle_then([this] { next_action(); });
            }
            return;
        }
        if (action == QLatin1String("timed-reset")) {
            if (timed_reset()) {
                next_action();
            }
            return;
        }
        if (!perform(action)) {
            return;  // fail() has ended the run
        }
        // A hover is what the step shows, so its pointer stays.
        if (!action.startsWith(QLatin1String("hover:"))) {
            park_pointer();
        }
        // What the action opened is drawn before the next; a step captured unsettled does not wait for it, nor
        // does an action a wait follows (a fit keeps the window changing until it ends).
        const bool waits = action_ < step.actions.size() && step.actions.at(action_).startsWith(QLatin1String("wait-"));
        if (unsettled || waits) {
            QTimer::singleShot(kSettleIntervalMs, this, [this] { next_action(); });
        } else {
            settle_then([this] { next_action(); });
        }
        return;
    }
    const auto save = [this] {
        const QString path = output_dir_.filePath(steps_[current_].image + QStringLiteral(".png"));
        if (!previous_frame_.save(path)) {
            fail(QStringLiteral("cannot write %1").arg(path));
            return;
        }
        ++current_;
        run_step();
    };
    if (unsettled) {
        QTimer::singleShot(kUnsettledCaptureMs, this, [this, save] {
            previous_frame_ = window_.grabWindow();
            save();
        });
        return;
    }
    settle_then(save);
}

void DemoDriver::wait_fit_then(std::function<void()> next, int waited_ms, int files) {
    QQmlEngine* engine = qmlEngine(window_.contentItem());
    auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
    const FitViewModel* fit = session != nullptr && session->project() != nullptr ? session->project()->fit() : nullptr;
    const bool running = fit != nullptr && fit->running();
    if (!running || (files >= 0 && fit->scanFitted() >= files)) {
        next();
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the fit did not end within %2 ms").arg(steps_[current_].image).arg(kFitWaitMs));
        return;
    }
    QTimer::singleShot(kSettleIntervalMs * 5, this, [this, next, waited_ms, files] {
        wait_fit_then(next, waited_ms + kSettleIntervalMs * 5, files);
    });
}

bool DemoDriver::perform(const QString& action) {
    // Scrolls the view a control is in until the control shows (a sidebar column longer than the window).
    if (action.startsWith(QLatin1String("reveal:"))) {
        QQuickItem* item = find(action.mid(7), false);
        for (QQuickItem* view = item != nullptr ? item->parentItem() : nullptr; view != nullptr; view = view->parentItem()) {
            // The first view that scrolls vertically (a swipe view's list scrolls sideways).
            auto* content = view->inherits("QQuickFlickable") ? view->property("contentItem").value<QQuickItem*>() : nullptr;
            if (content != nullptr && view->property("contentHeight").toDouble() > view->height()) {
                const double top = item->mapToItem(content, QPointF(0, 0)).y();
                const double most = std::max(0.0, view->property("contentHeight").toDouble() - view->height());
                view->setProperty("contentY", std::clamp(top - view->height() / 2, 0.0, most));
                return true;
            }
        }
        if (item == nullptr) {
            fail(QStringLiteral("step %1: cannot reveal '%2'").arg(steps_[current_].image, action.mid(7)));
            return false;
        }
        return true;  // nothing around it scrolls: it shows as it is
    }
    if (action.startsWith(QLatin1String("key:"))) {
        const QKeyCombination key = QKeySequence::fromString(action.mid(4))[0];
        QKeyEvent press(QEvent::KeyPress, key.key(), key.keyboardModifiers());
        QCoreApplication::sendEvent(&window_, &press);
        QKeyEvent release(QEvent::KeyRelease, key.key(), key.keyboardModifiers());
        QCoreApplication::sendEvent(&window_, &release);
        return true;
    }
    if (action.startsWith(QLatin1String("type:"))) {
        // Each character as a key press with its text, into whatever has the keyboard (a search field).
        for (const QChar character : action.mid(5)) {
            QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &press);
            QKeyEvent release(QEvent::KeyRelease, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &release);
        }
        return true;
    }
    if (action.startsWith(QLatin1String("show:"))) {
        const QStringList parts = action.split(QLatin1Char(':'));
        QQuickItem* view = find(parts.value(1), false);
        if (view == nullptr || parts.value(2).toInt() < 0) {
            fail(QStringLiteral("step %1: cannot show row %2 of '%3'").arg(steps_[current_].image, parts.value(2),
                                                                          parts.value(1)));
            return false;
        }
        QMetaObject::invokeMethod(view, "positionViewAtIndex", Q_ARG(int, parts.value(2).toInt()),
                                  Q_ARG(int, 1 /* ListView.Contain */));
        return true;
    }
    if (action.startsWith(QLatin1String("choose:"))) {
        // The open popup's entry: a visible, enabled button-like item showing the text.
        const QString wanted = action.mid(7);
        QList<QQuickItem*> candidates;
        std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
            for (QQuickItem* child : parent->childItems()) {
                if (child->isVisible() && child->isEnabled() && child->property("text").toString() == wanted &&
                    child->metaObject()->indexOfSignal("clicked()") >= 0) {
                    candidates.append(child);
                }
                walk(child);
            }
        };
        walk(window_.contentItem()->parentItem() != nullptr ? window_.contentItem()->parentItem()
                                                            : window_.contentItem());
        if (candidates.isEmpty()) {
            fail(QStringLiteral("step %1: no open entry shows '%2'").arg(steps_[current_].image, wanted));
            return false;
        }
        return click_item(candidates.last());
    }
    if (action.startsWith(QLatin1String("preference:"))) {
        // One of edi's Preferences, as its dialog sets it: preference:<name>=<value>, a string value.
        const QString setting = action.mid(11);
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        QObject* preferences = engine == nullptr ? nullptr : engine->singletonInstance<QObject*>("edi.app", "Preferences");
        if (preferences == nullptr || !setting.contains(QLatin1Char('=')) ||
            !preferences->setProperty(qPrintable(setting.section(QLatin1Char('='), 0, 0)), setting.section(QLatin1Char('='), 1))) {
            fail(QStringLiteral("step %1: cannot apply '%2'").arg(steps_[current_].image, action));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("theme:")) || action.startsWith(QLatin1String("platform:"))) {
        // The base's theme values (Colors.Themes) and Qt's colour schemes (Qt::ColorScheme).
        const QString value = action.section(QLatin1Char(':'), 1);
        const bool theme = action.startsWith(QLatin1String("theme:"));
        const int code = value == QLatin1String("light")  ? (theme ? 0 : static_cast<int>(Qt::ColorScheme::Light))
                         : value == QLatin1String("dark") ? (theme ? 1 : static_cast<int>(Qt::ColorScheme::Dark))
                         : value == QLatin1String("system") && theme ? 2
                                                                     : -1;
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        QObject* target = engine == nullptr ? nullptr
                          : theme ? engine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Colors")
                                  : engine->singletonInstance<QObject*>("edi.app", "AppState");
        if (code < 0 || target == nullptr ||
            !target->setProperty(theme ? "theme" : "platformColorScheme", code)) {
            fail(QStringLiteral("step %1: cannot apply '%2'").arg(steps_[current_].image, action));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("scroll-to:"))) {
        const QString name = action.section(QLatin1Char(':'), 1, 1);
        const QString wanted = action.section(QLatin1Char(':'), 2);
        QQuickItem* view = find(name, false);
        const qsizetype at = view != nullptr ? view->property("text").toString().indexOf(wanted) : -1;
        QQuickItem* flickable = view != nullptr ? view->parentItem() : nullptr;
        while (flickable != nullptr && flickable->metaObject()->indexOfProperty("contentY") < 0) {
            flickable = flickable->parentItem();
        }
        QRectF line;
        if (at < 0 || flickable == nullptr ||
            !QMetaObject::invokeMethod(view, "positionToRectangle", Q_RETURN_ARG(QRectF, line),
                                       Q_ARG(int, static_cast<int>(at)))) {
            fail(QStringLiteral("step %1: cannot scroll '%2' to '%3'").arg(steps_[current_].image, name, wanted));
            return false;
        }
        auto* content = qvariant_cast<QQuickItem*>(flickable->property("contentItem"));
        flickable->setProperty("contentY", content != nullptr ? view->mapToItem(content, line.topLeft()).y() : line.y());
        return true;
    }
    if (action.startsWith(QLatin1String("open-cli-project:"))) {
        // open-cli-project:<id> opens a copy of the CLI project docs/user/cli/<id>/project from this build's
        // source tree, so the image shows a temporary location as an example's does.
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        const QString id = action.section(QLatin1Char(':'), 1);
        loaded_cli_project_ = loaded_files_.isValid() ? copy_cli_project(id, QDir(loaded_files_.path())) : QString();
        if (loaded_cli_project_.isEmpty() || session == nullptr ||
            !session->openProject(QUrl::fromLocalFile(loaded_cli_project_))) {
            fail(QStringLiteral("step %1: %2 failed: %3")
                     .arg(steps_[current_].image, action, session ? session->lastError() : QStringLiteral("no session")));
            return false;
        }
        return true;
    }
    if (action == QLatin1String("remove-scan-data")) {
        const QDir data(loaded_cli_project_ + QStringLiteral("/experiments/d20_scan"));
        if (loaded_cli_project_.isEmpty() || !QDir(data).removeRecursively()) {
            fail(QStringLiteral("step %1: the scan's data could not be removed").arg(steps_[current_].image));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("save-as:")) || action.startsWith(QLatin1String("open-project:"))) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        const bool save = action.startsWith(QLatin1String("save-as:"));
        const QString name = action.section(QLatin1Char(':'), 1);
        const QUrl directory = QUrl::fromLocalFile(QDir::isAbsolutePath(name) ? name : loaded_files_.filePath(name));
        if (!save) {
            loaded_cli_project_ = directory.toLocalFile();
        }
        if (session == nullptr || !(save ? session->saveAs(directory) : session->openProject(directory))) {
            fail(QStringLiteral("step %1: %2 refused: %3")
                     .arg(steps_[current_].image, action, session ? session->lastError() : QStringLiteral("no session")));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("drag:")) || action.startsWith(QLatin1String("right-click:"))) {
        // drag:<name>:<x0>,<y0>,<x1>,<y1> drags the left button across the item, at fractions of its size;
        // right-click:<name> clicks its centre with the right button.
        const bool drag = action.startsWith(QLatin1String("drag:"));
        const QStringList parts = action.mid(drag ? 5 : 12).split(QLatin1Char(':'));
        QQuickItem* item = find(parts.value(0), true);
        const QStringList at = parts.value(1, QStringLiteral("0.5,0.5,0.5,0.5")).split(QLatin1Char(','));
        if (item == nullptr || at.size() != 4) {
            fail(QStringLiteral("step %1: cannot %2").arg(steps_[current_].image, action));
            return false;
        }
        const auto point = [item, &at](int i) {
            return item->mapToScene(QPointF(at[i].toDouble() * item->width(), at[i + 1].toDouble() * item->height()));
        };
        const Qt::MouseButton button = drag ? Qt::LeftButton : Qt::RightButton;
        const QPointF from = point(0), to = drag ? point(2) : point(0);
        QMouseEvent press(QEvent::MouseButtonPress, from, window_.mapToGlobal(from), button, button, Qt::NoModifier);
        QCoreApplication::sendEvent(&window_, &press);
        QMouseEvent move(QEvent::MouseMove, to, window_.mapToGlobal(to), Qt::NoButton, button, Qt::NoModifier);
        QCoreApplication::sendEvent(&window_, &move);
        QMouseEvent release(QEvent::MouseButtonRelease, to, window_.mapToGlobal(to), button, Qt::NoButton,
                            Qt::NoModifier);
        QCoreApplication::sendEvent(&window_, &release);
        return true;
    }
    if (action.startsWith(QLatin1String("hover:"))) {
        // hover:<name>:<x>,<y> moves the pointer over the item, at fractions of its size, with no button down.
        const QStringList parts = action.mid(6).split(QLatin1Char(':'));
        QQuickItem* item = find(parts.value(0), true);
        const QStringList at = parts.value(1, QStringLiteral("0.5,0.5")).split(QLatin1Char(','));
        if (item == nullptr || at.size() != 2) {
            fail(QStringLiteral("step %1: cannot %2").arg(steps_[current_].image, action));
            return false;
        }
        const QPointF to = item->mapToScene(QPointF(at[0].toDouble() * item->width(), at[1].toDouble() * item->height()));
        for (const QPointF& point : {to + QPointF(1.0, 1.0), to}) {
            QMouseEvent move(QEvent::MouseMove, point, window_.mapToGlobal(point), Qt::NoButton, Qt::NoButton,
                             Qt::NoModifier);
            QCoreApplication::sendEvent(&window_, &move);
        }
        return true;
    }
    if (action.startsWith(QLatin1String("expand:"))) {
        QQuickItem* group = find(action.mid(7), false);
        if (group == nullptr || !group->setProperty("collapsed", false)) {
            fail(QStringLiteral("step %1: cannot expand '%2'").arg(steps_[current_].image, action.mid(7)));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("type:"))) {
        for (const QChar character : action.mid(5)) {
            QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &press);
            QKeyEvent release(QEvent::KeyRelease, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &release);
        }
        return true;
    }
    if (action.startsWith(QLatin1String("resize:"))) {
        const QStringList size = action.mid(7).split(QLatin1Char('x'));
        window_.resize(size.value(0).toInt(), size.value(1).toInt());
        return true;
    }
    if (action.startsWith(QLatin1String("pin-time:"))) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        if (session == nullptr || session->project() == nullptr) {
            fail(QStringLiteral("step %1: no project to pin the time of").arg(steps_[current_].image));
            return false;
        }
        session->project()->pinTimestamps(action.mid(9));
        return true;
    }
    if (action == QLatin1String("load-reflections") || action.startsWith(QLatin1String("load-reflections:"))) {
        // Load data into the current experiment from the file the action names, else the one EDI_DEMO_REFLECTIONS
        // names, through the call the row's file dialog makes on accept; without either the step only captures.
        const QString path = action.contains(QLatin1Char(':')) ? action.section(QLatin1Char(':'), 1)
                                                                : qEnvironmentVariable("EDI_DEMO_REFLECTIONS");
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        if (!path.isEmpty() && session != nullptr && session->project() != nullptr) {
            session->project()->loadDataInto(session->project()->currentExperiment(), QUrl::fromLocalFile(path));
        }
        return true;
    }
    if (action.startsWith(QLatin1String("load-experiments:"))) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        QList<QUrl> files;
        if (!loaded_files_.isValid()) {  // its filePath() would be empty, naming the working directory
            fail(QStringLiteral("step %1: cannot create a directory for the loaded files: %2")
                     .arg(steps_[current_].image, loaded_files_.errorString()));
            return false;
        }
        // `<files>|<find>=<replace>|...`: each copy's text edited as a user would edit the file ("\n" in a
        // replacement is a line break), so a declared state no bundled file carries can be shown.
        const QStringList parts = action.mid(17).split(QLatin1Char('|'));
        for (const QString& resource : parts.first().split(QLatin1Char(','))) {
            const QString target = loaded_files_.filePath(resource.section(QLatin1Char('/'), -1));
            QFile source(QStringLiteral(":/edi/examples/") + resource);
            if (!source.open(QIODevice::ReadOnly)) {
                fail(QStringLiteral("step %1: no bundled file %2").arg(steps_[current_].image, resource));
                return false;
            }
            QString content = QString::fromUtf8(source.readAll());
            for (const QString& edit : parts.mid(1)) {
                const QString find = edit.section(QLatin1Char('='), 0, 0);
                if (!content.contains(find)) {
                    fail(QStringLiteral("step %1: %2 has no '%3' to edit").arg(steps_[current_].image, resource, find));
                    return false;
                }
                content.replace(find, edit.section(QLatin1Char('='), 1).replace(QLatin1String("\\n"), QLatin1String("\n")));
            }
            QFile copy(target);
            if (!copy.open(QIODevice::WriteOnly | QIODevice::Truncate) || copy.write(content.toUtf8()) < 0) {
                fail(QStringLiteral("step %1: cannot write %2").arg(steps_[current_].image, target));
                return false;
            }
            files.append(QUrl::fromLocalFile(target));
        }
        if (session == nullptr || session->project() == nullptr || !session->project()->loadExperiments(files)) {
            fail(QStringLiteral("step %1: the load was refused: %2")
                     .arg(steps_[current_].image, session ? session->lastError() : QStringLiteral("no session")));
            return false;
        }
        return true;
    }
    return click(action);
}

QQuickItem* DemoDriver::find(const QString& object_name, bool must_be_usable) {
    // Every page stays loaded, side by side in the content area's SwipeView, so a name can match on a
    // page not shown, and such an item still counts as visible: the visible, enabled one on screen
    // counts, before any other. Declared items are the window's QObject children; view delegates only
    // visual ones.
    QList<QQuickItem*> matches = window_.findChildren<QQuickItem*>(object_name);
    std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
        for (QQuickItem* child : parent->childItems()) {
            if (child->objectName() == object_name && !matches.contains(child)) {
                matches.append(child);
            }
            walk(child);
        }
    };
    walk(window_.contentItem());
    QQuickItem* off_screen = nullptr;
    for (QQuickItem* match : matches) {
        if (match->isVisible() && (!must_be_usable || match->isEnabled())) {
            if (on_screen(match)) {
                return match;
            }
            off_screen = off_screen != nullptr ? off_screen : match;
        }
    }
    if (off_screen != nullptr) {
        return off_screen;
    }
    return matches.isEmpty() ? nullptr : matches.first();  // the caller names why it is unusable
}

bool DemoDriver::on_screen(QQuickItem* item) const {
    // What is left of the item inside the window and inside every clipping ancestor: a sidebar tab not
    // shown lies within the window, beside the shown one, but its view clips it away (the Extras
    // `group.peak` beside the Basic one).
    QRectF shown = item->mapRectToScene(item->boundingRect())
                       .intersected(QRectF(QPointF(0, 0), QSizeF(window_.width(), window_.height())));
    for (QQuickItem* ancestor = item->parentItem(); ancestor != nullptr && !shown.isEmpty();
         ancestor = ancestor->parentItem()) {
        if (ancestor->clip()) {
            shown = shown.intersected(ancestor->mapRectToScene(ancestor->boundingRect()));
        }
    }
    return !shown.isEmpty();
}

bool DemoDriver::click(const QString& object_name) {
    QQuickItem* item = find(object_name, true);
    // A click at an item off screen reaches nothing, so the run stops rather than capture an unchanged page.
    if (item == nullptr || !item->isVisible() || !item->isEnabled() || !on_screen(item)) {
        fail(QStringLiteral("step %1: control '%2' is %3")
                 .arg(steps_[current_].image, object_name,
                      item == nullptr         ? QStringLiteral("missing")
                      : !item->isVisible()    ? QStringLiteral("hidden")
                      : !item->isEnabled()    ? QStringLiteral("disabled")
                                              : QStringLiteral("off screen")));
        return false;
    }
    return click_item(item);
}

bool DemoDriver::click_item(QQuickItem* item) {
    // A group box is clicked on its title bar (its centre may be its content when expanded).
    const QVariant title_area = item->property("titleArea");
    auto* target = title_area.isValid() ? qvariant_cast<QQuickItem*>(title_area) : nullptr;
    if (target == nullptr) {
        target = item;
    }
    const QPointF centre = target->mapToScene(QPointF(target->width() / 2, target->height() / 2));
    const QPointF global = window_.mapToGlobal(centre);
    QMouseEvent press(QEvent::MouseButtonPress, centre, global, Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
    QCoreApplication::sendEvent(&window_, &press);
    QMouseEvent release(QEvent::MouseButtonRelease, centre, global, Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
    QCoreApplication::sendEvent(&window_, &release);
    return true;
}

void DemoDriver::park_pointer() {
    // The pointer rests in the window's corner, where nothing reacts to it, from the start and after every
    // action: a capture then never shows the hover state of whatever lies under the host's own cursor. Without
    // it the images differed by host: a headless Linux display keeps its cursor at the window's centre, which
    // highlighted the Messages row drawn there, and a macOS runner's cursor did not (edi PR 97).
    const QPointF corner(1, 1);
    QMouseEvent move(QEvent::MouseMove, corner, window_.mapToGlobal(corner), Qt::NoButton, Qt::NoButton,
                     Qt::NoModifier);
    QCoreApplication::sendEvent(&window_, &move);
}

void DemoDriver::settle_then(std::function<void()> next) {
    settle_attempts_ = 0;
    previous_frame_ = QImage();
    auto poll = std::make_shared<std::function<void()>>();
    *poll = [this, next, poll] {
        // A calculation in flight will change the page when it is published (edi ADR-0020): the frame is
        // settled only once the project has no calculation in flight or owed.
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        const bool calculating =
            session != nullptr && session->project() != nullptr && session->project()->calculating();
        const QImage frame = window_.grabWindow();
        if (!calculating && !previous_frame_.isNull() && frame == previous_frame_) {
            next();
            return;
        }
        if (++settle_attempts_ > kSettleMaxAttempts) {
            // The last two frames, to see what kept changing.
            previous_frame_.save(output_dir_.filePath(steps_[current_].image + QStringLiteral("-unsettled-a.png")));
            frame.save(output_dir_.filePath(steps_[current_].image + QStringLiteral("-unsettled-b.png")));
            fail(QStringLiteral("step %1 did not settle within %2 ms (%3)")
                     .arg(steps_[current_].image)
                     .arg(kSettleIntervalMs * kSettleMaxAttempts)
                     .arg(calculating ? QStringLiteral("a calculation is in flight")
                                      : QStringLiteral("the window kept changing")));
            return;
        }
        previous_frame_ = frame;
        QTimer::singleShot(kSettleIntervalMs, this, *poll);
    };
    QTimer::singleShot(kSettleIntervalMs, this, *poll);
}

namespace {

ProjectViewModel* open_project(QQuickWindow& window) {
    QQmlEngine* engine = qmlEngine(window.contentItem());
    auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
    return session != nullptr ? session->project() : nullptr;
}

std::vector<double> parameter_values(const edi::Project& project) {
    std::vector<double> values;
    for (const edi::NamedParameter& named : edi::named_parameters(project)) {
        values.push_back(named.parameter->value.get());
    }
    return values;
}

// Whether a fit record still holds correlations; a build whose record has none has none left.
template <typename Record>
bool correlations_left(const Record& record) {
    if constexpr (requires { record.correlations.empty(); }) {
        return !record.correlations.empty();
    } else {
        return false;
    }
}

bool delay_from_environment() {
    const int ms = qEnvironmentVariableIntValue("EDI_DEMO_DELAY_MS");
    if (ms > 0) {
        QThread::msleep(static_cast<unsigned long>(ms));
    }
    return ms > 0;
}

}  // namespace

void DemoDriver::record_time(const QString& label, qint64 ms) {
    QFile file(output_dir_.filePath(QStringLiteral("timings.tsv")));
    if (file.open(QIODevice::Append | QIODevice::Text)) {
        file.write(QStringLiteral("%1\t%2\t%3\n").arg(steps_[current_].image, label).arg(ms).toUtf8());
    }
}

void DemoDriver::delay_then_record() {
    // The delay's start and end on the interval's clock, so a control can show the interval ends after it.
    const qint64 from = timer_.elapsed();
    if (delay_from_environment()) {
        record_time(QStringLiteral("delay from %1 to").arg(from), timer_.elapsed());
    }
}

QString DemoDriver::scan_work(int files) const {
    ProjectViewModel* project = open_project(window_);
    const ScanSession* scan = project != nullptr ? project->scanSession() : nullptr;
    if (scan == nullptr) {
        return QStringLiteral("no scan is open");
    }
    if (project->analysis() == nullptr || project->analysis()->fittingMode() != QLatin1String("sequential")) {
        return QStringLiteral("the scan does not run in its declared sequential mode");
    }
    if (static_cast<int>(scan->datasets().files.size()) != files ||
        static_cast<int>(scan->index().rows.size()) != files) {
        return QStringLiteral("the scan lists %1 files, not %2").arg(scan->datasets().files.size()).arg(files);
    }
    for (std::size_t i = 0; i < scan->index().rows.size(); ++i) {
        const auto& row = scan->index().rows[i];
        if (row.offset < 0 || row.skipped || !row.converged) {
            return QStringLiteral("file %1 (%2) was not fitted to convergence")
                .arg(i + 1)
                .arg(QString::fromStdString(scan->datasets().files[i]));
        }
    }
    return {};
}

void DemoDriver::idle_then(std::function<void()> next, int waited_ms) {
    ProjectViewModel* project = open_project(window_);
    if (project == nullptr || !project->calculating()) {
        next();
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: a calculation did not end").arg(steps_[current_].image));
        return;
    }
    QTimer::singleShot(kIdlePollMs, this, [this, next, waited_ms] { idle_then(next, waited_ms + kIdlePollMs); });
}

void DemoDriver::drawn_then(std::function<void()> next, int waited_ms) {
    ProjectViewModel* project = open_project(window_);
    if (project == nullptr || project->fit() == nullptr || !project->fit()->catchingUp()) {
        idle_then(std::move(next));
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the display did not catch up").arg(steps_[current_].image));
        return;
    }
    QTimer::singleShot(kIdlePollMs, this, [this, next, waited_ms] { drawn_then(next, waited_ms + kIdlePollMs); });
}

void DemoDriver::timed_fit_then(std::function<void()> next, int files, int stop_after) {
    ProjectViewModel* project = open_project(window_);
    FitViewModel* fit = project != nullptr ? project->fit() : nullptr;
    if (fit == nullptr || fit->running()) {
        fail(QStringLiteral("step %1: no idle fit to start").arg(steps_[current_].image));
        return;
    }
    pre_fit_values_ = parameter_values(project->project());
    auto refusal = std::make_shared<QString>();
    auto done = std::make_shared<bool>(false);
    auto connections = std::make_shared<std::vector<QMetaObject::Connection>>();
    const auto finish = [this, next, files, refusal, done, connections] {
        if (*done) {
            return;
        }
        *done = true;
        for (const QMetaObject::Connection& connection : *connections) {
            QObject::disconnect(connection);
        }
        // The fit's time ends with the fit: a display catching up draws on after it, and is waited for before the
        // next action.
        const qint64 ms = timer_.elapsed();
        drawn_then([this, next, files, refusal, ms] {
            QString problem = refusal->isEmpty() ? scan_work(files) : QStringLiteral("refused: ") + *refusal;
            if (!problem.isEmpty()) {
                fail(QStringLiteral("step %1: the timed fit did not do its work: %2").arg(steps_[current_].image, problem));
                return;
            }
            record_time(QStringLiteral("fit"), ms);
            next();
        });
    };
    connections->push_back(connect(fit, &FitViewModel::scanFinished, this, [this] { delay_then_record(); }));
    connections->push_back(connect(fit, &FitViewModel::scanFinished, this, finish));
    connections->push_back(connect(fit, &FitViewModel::refused, this, [refusal, finish](const QString& reason) {
        *refusal = reason.isEmpty() ? QStringLiteral("the fit was refused") : reason;
        finish();
    }));
    if (stop_after >= 0) {
        connections->push_back(connect(fit, &FitViewModel::scanFittedChanged, this, [fit, stop_after] {
            if (fit->running() && fit->scanFitted() >= stop_after) {
                fit->cancel();
            }
        }));
    }
    timer_.start();
    fit->start();
    if (!fit->running() && !*done) {
        *refusal = QStringLiteral("the fit did not start");
        finish();
    }
}

bool DemoDriver::timed_reset() {
    ProjectViewModel* project = open_project(window_);
    if (project == nullptr || project->fit() == nullptr) {
        fail(QStringLiteral("step %1: no project to reset").arg(steps_[current_].image));
        return false;
    }
    const QMetaObject::Connection delay =
        connect(project->fit(), &FitViewModel::scanSummaryChanged, this, [this] { delay_then_record(); });
    timer_.start();
    const QString refusal = project->resetScan();
    QObject::disconnect(delay);
    idle_then([this, project, refusal] {
        const qint64 ms = timer_.elapsed();
        QString problem = refusal;
        const ScanSession* scan = project->scanSession();
        if (problem.isEmpty() && scan != nullptr) {
            for (const auto& row : scan->index().rows) {
                if (row.offset >= 0) {
                    problem = QStringLiteral("a result row is left");
                }
            }
        }
        if (problem.isEmpty() && project->project().fit_result.held()) {
            problem = QStringLiteral("a fit result is left");
        }
        if (problem.isEmpty() && correlations_left(project->project().fit_result)) {
            problem = QStringLiteral("correlations are left");
        }
        if (problem.isEmpty() && parameter_values(project->project()) != pre_fit_values_) {
            problem = QStringLiteral("the model does not hold its pre-fit values");
        }
        if (problem.isEmpty() && !project->canUndo()) {
            problem = QStringLiteral("Undo is not available");
        }
        if (!problem.isEmpty()) {
            fail(QStringLiteral("step %1: the timed reset did not do its work: %2").arg(steps_[current_].image, problem));
            return;
        }
        record_time(QStringLiteral("reset"), ms);
        next_action();
    });
    return false;
}

void DemoDriver::record_samples(const QString& label, std::vector<double> samples) {
    QFile all(output_dir_.filePath(QStringLiteral("frames.tsv")));
    if (all.open(QIODevice::Append | QIODevice::Text)) {
        for (const double ms : samples) {
            all.write(QStringLiteral("%1\t%2\t%3\n").arg(steps_[current_].image, label).arg(ms, 0, 'f', 3).toUtf8());
        }
    }
    const auto missing = std::count_if(samples.begin(), samples.end(), [](double ms) { return ms < 0.0; });
    std::erase_if(samples, [](double ms) { return ms < 0.0; });
    std::sort(samples.begin(), samples.end());
    const auto at = [&samples](double share) {
        return samples.empty() ? -1.0 : samples[static_cast<std::size_t>(share * static_cast<double>(samples.size() - 1))];
    };
    QFile file(output_dir_.filePath(QStringLiteral("timings.tsv")));
    if (file.open(QIODevice::Append | QIODevice::Text)) {
        file.write(QStringLiteral("%1\t%2 median\t%3\n%1\t%2 p95\t%4\n%1\t%2 max\t%5\n%1\t%2 missing\t%6\n")
                       .arg(steps_[current_].image, label)
                       .arg(at(0.5), 0, 'f', 3)
                       .arg(at(0.95), 0, 'f', 3)
                       .arg(at(1.0), 0, 'f', 3)
                       .arg(missing)
                       .toUtf8());
    }
}

void DemoDriver::wait_scan_then(std::function<void()> next, const QString& mode, int waited_ms) {
    QQuickItem* layer = find(QStringLiteral("scanView.%1.layer").arg(mode), false);
    auto* model = layer != nullptr ? layer->property("model").value<ScanViewModel*>() : nullptr;
    if (model != nullptr && model->count() > 0 && model->loaded() == model->count()) {
        next();
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the scan's datasets were not read").arg(steps_[current_].image));
        return;
    }
    QTimer::singleShot(kSettleIntervalMs, this,
                       [this, next, mode, waited_ms] { wait_scan_then(next, mode, waited_ms + kSettleIntervalMs); });
}

double DemoDriver::frame_after(const std::function<void()>& change, const std::function<bool()>& ready) {
    std::atomic<bool> synced{false};
    std::atomic<qint64> swapped_ns{-1};
    QElapsedTimer clock;
    QEventLoop loop;
    // Both on the render thread, while the GUI thread waits for the synchronisation.
    const QMetaObject::Connection sync = connect(
        &window_, &QQuickWindow::afterSynchronizing, &window_,
        [&] {
            if (!ready || ready()) {
                synced = true;
            }
        },
        Qt::DirectConnection);
    const QMetaObject::Connection swap = connect(
        &window_, &QQuickWindow::frameSwapped, &window_,
        [&] {
            if (synced && swapped_ns < 0) {
                swapped_ns = clock.nsecsElapsed();
                QMetaObject::invokeMethod(&loop, &QEventLoop::quit, Qt::QueuedConnection);
            }
        },
        Qt::DirectConnection);
    // A state that turns ready after its last frame (a calculation ending after its pattern was drawn) asks for one.
    QTimer poll;
    connect(&poll, &QTimer::timeout, this, [&] {
        if (ready && !synced && ready()) {
            window_.update();
        }
    });
    QTimer guard;
    guard.setSingleShot(true);
    connect(&guard, &QTimer::timeout, &loop, &QEventLoop::quit);
    guard.start(kFrameWaitMs);
    if (ready) {
        poll.start(kIdlePollMs);
    }
    clock.start();
    change();
    loop.exec();
    disconnect(sync);
    disconnect(swap);
    return swapped_ns < 0 ? -1.0 : static_cast<double>(swapped_ns.load()) / 1e6;
}

bool DemoDriver::timed_frames(const QString& mode, const QString& kind, int count) {
    QQuickItem* chart = find(QStringLiteral("scanView.") + mode, false);
    QQuickItem* layer = find(QStringLiteral("scanView.%1.layer").arg(mode), false);
    auto* model = layer != nullptr ? layer->property("model").value<ScanViewModel*>() : nullptr;
    if (chart == nullptr || model == nullptr || model->count() == 0) {
        fail(QStringLiteral("step %1: no %2 view with datasets to time").arg(steps_[current_].image, mode));
        return false;
    }
    const double x_min = model->xMin(), x_max = model->xMax(), span = x_max - x_min;
    const auto zoom = [chart](const QVariantList& x) {
        QMetaObject::invokeMethod(chart, "setZoom", Q_ARG(QVariant, QVariant(x)), Q_ARG(QVariant, QVariant(QVariantList{})));
    };
    std::vector<double> samples;
    for (int i = 0; i < count; ++i) {
        std::function<void()> change;
        if (kind == QLatin1String("zoom")) {
            // In to the middle half and out again.
            change = [&, i] { zoom(i % 2 == 0 ? QVariantList{x_min + span / 4, x_max - span / 4} : QVariantList{}); };
        } else if (kind == QLatin1String("pan")) {
            // A window of half the range moved by a fiftieth of the range each frame, back and forth.
            const int place = i % 50 < 25 ? i % 50 : 50 - i % 50;
            const double from = x_min + span * static_cast<double>(place) / 50.0;
            change = [&, from] { zoom(QVariantList{from, from + span / 2}); };
        } else if (kind == QLatin1String("restyle")) {
            const char* property = mode == QLatin1String("map") ? "reversed" : "stackedReversed";
            change = [layer, property] { layer->setProperty(property, !layer->property(property).toBool()); };
        } else if (kind == QLatin1String("select")) {
            change = [layer, i, model] { layer->setProperty("current", (i * 37) % model->count()); };
        } else if (kind == QLatin1String("data")) {
            // Every dataset's points published again (the x axis placed anew: d and back where a calculation gives d,
            // else the same axis): each trace is reduced and drawn from scratch, as for a dataset that changed.
            change = [model] { model->setDSpacing(!model->dSpacing()); };
        } else if (kind == QLatin1String("rows")) {
            // The rows placed again (by file, by scan value): every dataset's row moves, its trace kept.
            change = [model] { model->setRowsByIndex(!model->rowsByIndex()); };
        } else {
            fail(QStringLiteral("step %1: no timed change '%2'").arg(steps_[current_].image, kind));
            return false;
        }
        const int built = layer->property("traceBuildCount").toInt();
        samples.push_back(frame_after(change));
        if (kind == QLatin1String("data") && mode == QLatin1String("stacked") &&
            layer->property("traceBuildCount").toInt() - built < model->count()) {
            fail(QStringLiteral("step %1: a data change rebuilt %2 of %3 traces")
                     .arg(steps_[current_].image)
                     .arg(layer->property("traceBuildCount").toInt() - built)
                     .arg(model->count()));
            return false;
        }
        // Each change from an idle window, so one frame's work does not run into the next change's.
        QThread::msleep(20);
        QCoreApplication::processEvents();
    }
    if (kind == QLatin1String("data")) {
        // What the data change republished: the points on d and back, or on the same axis.
        std::fprintf(stderr, "edi_app --demo: %s data changes %s\n", qPrintable(mode),
                     model->dAvailable() ? "alternate the x axis with d" : "republish the same axis (no d)");
    }
    record_samples(mode + QLatin1Char(' ') + kind, samples);
    return true;
}

bool DemoDriver::timed_slider(int count) {
    ProjectViewModel* project = open_project(window_);
    QQuickItem* slider = find(QStringLiteral("parameters.slider"), true);
    if (project == nullptr || slider == nullptr) {
        fail(QStringLiteral("step %1: no slider to move").arg(steps_[current_].image));
        return false;
    }
    const double from = slider->property("from").toDouble(), to = slider->property("to").toDouble();
    const double centre = slider->property("value").toDouble();
    std::vector<double> shown, calculated;
    for (int i = 0; i < count; ++i) {
        // Small steps either side of where the slider was, as a drag makes them.
        const double value = std::clamp(centre + (to - from) * 0.01 * static_cast<double>(i % 2 == 0 ? 1 : -1) *
                                                     static_cast<double>(1 + i % 5),
                                        from, to);
        QElapsedTimer clock;
        std::atomic<qint64> ended_ns{-1};
        const QMetaObject::Connection ended = connect(project, &ProjectViewModel::calculatingChanged, this, [&] {
            if (!project->calculating() && ended_ns < 0) {
                ended_ns = clock.nsecsElapsed();
            }
        });
        clock.start();
        shown.push_back(frame_after(
            [slider, value] {
                slider->setProperty("value", value);
                QMetaObject::invokeMethod(slider, "moved");
            },
            [&] { return ended_ns >= 0; }));
        disconnect(ended);
        calculated.push_back(ended_ns < 0 ? -1.0 : static_cast<double>(ended_ns.load()) / 1e6);
        QThread::msleep(20);
        QCoreApplication::processEvents();
    }
    record_samples(QStringLiteral("slider shown"), shown);
    record_samples(QStringLiteral("slider calculated"), calculated);
    return true;
}

void DemoDriver::fail(const QString& message) {
    std::fprintf(stderr, "edi_app --demo: %s\n", qPrintable(message));
    QCoreApplication::exit(1);
}

}  // namespace edi_app
