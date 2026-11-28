// SPDX-License-Identifier: BSD-3-Clause
#include "demo_driver.hpp"

#include "assistant_view_model.hpp"

#include <algorithm>
#include <array>

#include <QCoreApplication>
#include <QDirIterator>
#include <QElapsedTimer>
#include <QCryptographicHash>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QFont>
#include <QFontMetricsF>
#include <QGuiApplication>
#include <QJSValue>
#include <QRegularExpression>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QKeyEvent>
#include <QKeySequence>
#include <QMouseEvent>
#include <QPointer>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickItemGrabResult>
#include <QQuickWindow>
#include <QGlyphRun>
#include <QRawFont>
#include <QTextBlock>
#include <QTextDocument>
#include <QVector3D>
#include <QtGraphs/QAreaSeries>
#include <QtGraphs/QXYSeries>
#include <QtQuick/private/qquickrectangle_p.h>
#include <QtQuick/private/qquickrectangle_p_p.h>
#include <QtQuick/private/qquicktext_p_p.h>
#include <QScopeGuard>
#include <QThread>
#include <QTimer>
#include <QTextStream>
#include <QUrl>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <functional>
#include <system_error>

#include "analysis_view_model.hpp"
#include "background.hpp"
#include "crysta/project_output.hpp"
#include "edi/categories.hpp"
#include "edi/palette.hpp"
#include "app_info.hpp"
#include "edi/io.hpp"
#include "fit_view_model.hpp"
#include "parameter_item.hpp"
#include "parameter_table_model.hpp"
#include "pattern_chart_controller.hpp"
#include "project_view_model.hpp"
#include "scan_session.hpp"
#include "scan_view_model.hpp"
#include "session.hpp"
#include "ui_probe.hpp"
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

// The layout contract's numbers (ADR-0103), stated in the 14 px app font; a run in another font logs them unjudged.
constexpr double kContractFontPx = 14.0;
// W3 and W4: the sidebar goes to the bottom below 913 px, and at 913 px it is at the side.
constexpr int kSwitchWidthPx = 913;
// W4: Auto stops at all columns plus at most one column gap, 681 px.
constexpr double kAutoStopPx = 681.0;
// W5: the parameter table's name budget, the widest bundled example's name with its cell margins. Measured on the final
// build (the e58-names scenario logs each example's widest drawn name); this value is a placeholder until then.
constexpr double kNameBudgetPx = 171.0;
// T8: a number shows at most six significant digits, and a data table goes down to two (×10ⁿ), never fewer.
constexpr int kNumberDigitsMost = 6;
constexpr int kNumberDigitsLeast = 2;
// C1: a legend's datablock name over 20 characters may elide, in its middle; anything shorter shows whole.
constexpr qsizetype kLegendNameChars = 20;
// D1: a dialog is at most its content's width plus 2 em.
constexpr double kDialogSpareEm = 2.0;

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
    : QObject(parent), window_(window), output_dir_(output_dir), only_(only) {
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
        // A scan's Experiments group lists its datasets, which can push the group below the sidebar's fold.
        steps_.push_back({QStringLiteral("ex-") + id,
                          theme + start + open_example(id) + QStringList{experiment, basic, "uncover:" + group, group}});
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
    // The diagnostics view, from Preferences > Advanced, then both dialogs closed.
    steps_.push_back({"c13-10-diagnostics", {"key:Escape", "appBar.button.preferences", "preferences.tab.advanced",
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
    steps_.push_back({"t16-02-fit-running", {"statusBar.fit.button", "capture-now"}});
    steps_.push_back({"t16-03-fit-done", {"wait-fit"}});
    steps_.push_back({"t16-04-fit-results", {"statusBar.fit.outcome"}});
    // The parameters table after a fit at a desktop width, its results closed: Start, Value, s.u. and Change filled
    // (`--demo-only parameters-fitted`).
    steps_.push_back({"parameters-fitted", QStringList{"resize:1760x1000"} + start + open_example("pd-neut-cwl_cosio-d20") +
                                               QStringList{analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK"}});
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
    steps_.push_back({"t16-24-beer-analysis-fitted", {close, analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK"}});
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
    // The magnetic Co2SiO4 example at 2.3 K: the structure with its moment arrows.
    steps_.push_back({"magnetic-01-cosio-2k-moments", start + open_example("pd-neut-cwl_cosio-d20_2k")
                                                     + QStringList{"wait-fit", structure, basic}});
    // The magnetic groups of the 2.3 K example: Main, then Extra.
    steps_.push_back({"magnetic-03-main-groups",
                      start + open_example("pd-neut-cwl_cosio-d20_2k")
                          + QStringList{"wait-fit", structure, basic, "expand:group.space_group_magn",
                                        "expand:group.parent_propagation_vector", "expand:group.atom_site_moment"}});
    steps_.push_back({"magnetic-04-extra-groups",
                      start + open_example("pd-neut-cwl_cosio-d20_2k") + QStringList{"wait-fit", structure, extras}});
    // Its pattern: the nuclear and the magnetic Bragg tick rows.
    steps_.push_back({"magnetic-05-pattern-ticks",
                      start + open_example("pd-neut-cwl_cosio-d20_2k") + QStringList{"wait-fit", experiment, basic}});
    // The propagation vectors, and a vector the cell cannot carry refused with its reason.
    steps_.push_back({"magnetic-06-propagation-vectors",
                      start + open_example("pd-neut-cwl_cosio-d20_2k")
                          + QStringList{"wait-fit", structure, basic, "expand:group.parent_propagation_vector",
                                        "propagationVectors.append"}});
    // The magnetic space group alone: the BNS selector, the UNI symbol beside it, both inside the sidebar.
    steps_.push_back({"magnetic-07-space-group",
                      start + open_example("pd-neut-cwl_cosio-d20_2k")
                          + QStringList{"wait-fit", structure, basic, "expand:group.space_group_magn"}});
    // Extra's parent space group and atoms in the cell, each alone: dictionary labels, units only in the tooltips.
    steps_.push_back({"magnetic-08-parent-group",
                      start + open_example("pd-neut-cwl_cosio-d20_2k")
                          + QStringList{"wait-fit", structure, extras, "expand:group.parent_space_group"}});
    steps_.push_back({"magnetic-09-atoms-in-cell",
                      start + open_example("pd-neut-cwl_cosio-d20_2k")
                          + QStringList{"wait-fit", structure, extras, "expand:group.expanded_atom_site"}});
    // The Analysis page's Extra fit groups of a fitted example: the fit result's flags as titled fields, the start
    // values as a read-only table, and a generated calculated table without hover tint. Run only when asked
    // (`--demo-only fitgroups-`).
    if (only.startsWith(QLatin1String("fitgroups-"))) {
        const QStringList fitted = start + open_cli_project("pd-neut-tof_ncaf-wish")
                                   + QStringList{analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK",
                                                 analysis, extras};
        steps_.push_back({"fitgroups-1-result", fitted + QStringList{"expand:group.fit_result"}});
        steps_.push_back({"fitgroups-2-start-values", {"expand:group.fit_parameter"}});
        // A generated calculated table under the pointer: its rows take no hover tint.
        steps_.push_back({"fitgroups-3-bank-hover",
                          {"expand:group.fit_result_bank", "hover:generated.fit_result_bank.prof_r_factor.1"}});
    }
    // The Examples list filtered by the structure tag: only the magnetic examples.
    steps_.push_back({"magnetic-02-examples-filter",
                      start + QStringList{"appBar.tab.project", "sideBar.tab.basic", "examples.property",
                                          "choose:Structure", "examples.value", "choose:Magnetic structure (2)"}});
    // A scan's datasets as experiments: the bundled 162-file example, before any scan has been fitted.
    steps_.push_back({"t16-50-scan-experiment", start + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                                    + QStringList{experiment, basic, "expand:group.experiments"}});
    steps_.push_back({"t16-51-scan-list", {blocks}});
    steps_.push_back({"t16-52-scan-dataset-5", {"key:Escape", "show:experiments.list:4", "experiments.row.4"}});
    // A scan run from the app on the 162-file example: running (the S3 bar, Follow on), stopped part way,
    // continued to the end, and the Evolution tab after it.
    steps_.push_back({"t16-60-scan-ready", QStringList{"resize:1280x960"} + start
                                               + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                               + QStringList{analysis, basic}});
    steps_.push_back({"t16-61-scan-running", {"statusBar.fit.button", "wait-files:40", "capture-now"}});
    steps_.push_back({"t16-62-scan-stopped", {"statusBar.fit.button", "wait-fit"}});
    steps_.push_back({"t16-63-scan-continue", {"choose:OK"}});
    steps_.push_back({"t16-64-scan-done", {"statusBar.fit.button", "wait-fit"}});
    steps_.push_back({"t16-65-scan-evolution", {"choose:OK", "mainArea.tab.evolution"}});
    steps_.push_back({"t16-66-scan-experiment", {experiment, basic, "expand:group.experiments"}});
    // After the scan: the single mode (a setting: the results stay current); a single fit on the shown dataset makes
    // it the template dataset, tagged in the lists, and marks the results out of date on the status bar.
    steps_.push_back({"t16-67-single-mode", {analysis, extras, "expand:group.fitting_mode", "fittingMode.type",
                                              "choose:Single experiment", basic, "mainArea.tab.evolution"}});
    steps_.push_back({"t16-68-single-fit-on-dataset",
                      {"mainArea.tab.pattern", "statusBar.fit.button", "wait-fit"}});
    // The single fit's correlations are the fitted dataset's, shown on its Correlations tab.
    steps_.push_back({"t16-68b-single-fit-correlations", {"choose:OK", "mainArea.tab.correlations"}});
    steps_.push_back({"t16-69-template-dataset", {experiment, basic, "show:experiments.list:161"}});
    // The scan's buttons follow its fits (owner, 2026-10-06): all fitted, Start fitting is disabled and Reset fits
    // enabled; Reset clears them (Start again); a stop leaves Continue. The Evolution chart zooms to a dragged box
    // and resets with a right click; the Project page shortens a long dataset list.
    steps_.push_back({"t16-70-scan-all-fitted", QStringList{"resize:1280x960"} + start
                                                    + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                                    + QStringList{analysis, basic, "statusBar.fit.button",
                                                                  "wait-fit", "choose:OK"}});
    steps_.push_back({"t16-71-scan-reset", {"statusBar.fit.reset"}});
    steps_.push_back({"t16-72-scan-stopped-continue", {"statusBar.fit.button", "wait-files:40", "statusBar.fit.button", "wait-fit",
                                                        "choose:OK"}});
    steps_.push_back({"t16-73-evolution-zoomed", {"statusBar.fit.button", "wait-fit", "choose:OK",
                                                   "mainArea.tab.evolution",
                                                   "drag:evolution.pointer:0.2,0.1,0.6,0.9"}});
    steps_.push_back({"t16-74-evolution-reset", {"right-click:evolution.pointer"}});
    steps_.push_back({"t16-75-project-names", {"appBar.tab.project"}});
    // The Evolution tab while a fresh scan of the 324-file example runs: a point per fitted dataset as it completes,
    // the first parameter chosen, the marker on the dataset being fitted.
    steps_.push_back({"t16-76-home", {QStringLiteral("appBar.tab.home")}});
    steps_.push_back({"t16-77-evolution-mid-scan", start
                                                       + open_cli_project("pd-neut-cwl_cosio-d20_scan-324f")
                                                       + QStringList{analysis, basic,
                                                                     "mainArea.tab.evolution", "statusBar.fit.button",
                                                                     "wait-files:200", "capture-now"}});
    steps_.push_back({"t16-78-evolution-stopped", {"statusBar.fit.button", "wait-fit", "choose:OK"}});
    // A single crystal (Tb2Ti2O7 on HEiDi): the reflections chart and table on Experiment and Analysis, in both themes,
    // before and after a fit of its scale.
    steps_.push_back({"sc-01-tb2ti2o7-experiment-light",
                      QStringList{"resize:1280x768", "theme:light"} + start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                          + QStringList{experiment, basic}});
    steps_.push_back({"sc-02-tb2ti2o7-analysis-light", {analysis, basic}});
    steps_.push_back({"sc-03-tb2ti2o7-fit-results-light", {"statusBar.fit.button", "wait-fit"}});
    steps_.push_back({"sc-03b-tb2ti2o7-analysis-fitted-light", {"choose:OK"}});
    steps_.push_back({"sc-04-tb2ti2o7-analysis-dark", {"theme:dark"}});
    steps_.push_back({"sc-05-tb2ti2o7-experiment-dark", {experiment, basic}});
    steps_.push_back({"sc-05b-tb2ti2o7-reflections-dark", {extras, "expand:group.refln"}});
    // At this width the quantity is under More, opened and closed again by its button.
    const auto quantity = [](const QString& choice) {
        return QStringList{"singleCrystal.toolbar.more", "singleCrystal.toolbar.quantity.overflow", "choose:" + choice, "singleCrystal.toolbar.more"};
    };
    steps_.push_back({"sc-05c-tb2ti2o7-f-dark", QStringList{basic} + quantity("F")});
    steps_.push_back({"sc-05d-tb2ti2o7-narrow-dark", quantity("F²") + QStringList{"resize:960x768"}});
    steps_.push_back({"sc-05e-tb2ti2o7-narrow-light", {"theme:light"}});
    steps_.push_back({"sc-05f-tb2ti2o7-isotropic-extinction", QStringList{"resize:1280x768"} + start
                                                                  + QStringList{"appBar.tab.project", "open-cli-project:sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction"}
                                                                  + QStringList{analysis, basic, "statusBar.fit.button", "wait-fit"}});
    steps_.push_back({"sc-05g-tb2ti2o7-isotropic-extinction-fitted", {"choose:OK", experiment, basic, "expand:group.extinction"}});
    steps_.push_back({"sc-06-pr2nio4-experiment-light",
                      QStringList{"theme:light"} + start + open_example("sc-neut-cwl_pr2nio4-5c2")
                          + QStringList{experiment, basic}});
    steps_.push_back({"sc-07-pr2nio4-analysis-dark", {"theme:dark", analysis, basic}});
    steps_.push_back({"sc-07a-pr2nio4-fit-results-dark", {"statusBar.fit.button", "wait-fit"}});
    steps_.push_back({"sc-07a2-pr2nio4-fitted-dark", {"choose:OK"}});
    steps_.push_back({"sc-07a3-pr2nio4-correlations-dark", {"mainArea.tab.correlations"}});
    steps_.push_back({"sc-07b-pr2nio4-zoomed",
                      {"mainArea.tab.pattern", "drag:singleCrystal.pointer:0.05,0.6,0.4,0.95"}});
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
    const QStringList fit_sc{analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK"};
    const QStringList sc_report_steps{QStringLiteral("appBar.tab.report"), "reveal:report.singleCrystal"};
    steps_.push_back({"sccheck-01-tb2ti2o7-report-loaded",
                      QStringList{"resize:1280x768", "theme:light"} + start + open_example("sc-neut-cwl_tb2ti2o7-heidi")
                          + sc_report_steps});
    steps_.push_back({"sccheck-02-tb2ti2o7-report-fitted", fit_sc + sc_report_steps});
    steps_.push_back({"sccheck-03-pr2nio4-report-loaded", start + open_example("sc-neut-cwl_pr2nio4-5c2") + sc_report_steps});
    steps_.push_back({"sccheck-04-pr2nio4-report-fitted", fit_sc + sc_report_steps});
    steps_.push_back({"sccheck-05-pr2nio4-extinction-free-fitted",
                      QStringList{analysis, basic, "parameters.nameFilter", "type:extinction", "parameters.free.0", "parameters.free.1",
                                  "statusBar.fit.button", "wait-fit", "choose:OK"}});
    steps_.push_back({"sccheck-06-pr2nio4-extinction-fixed-refitted",
                      {"parameters.free.0", "parameters.free.1", "statusBar.fit.button", "wait-fit",
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
    steps_.push_back({"sccheck-10e-int-joint-fitted", {analysis, basic, "statusBar.fit.button", "wait-fit"}});
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
                                                                    + QStringList{experiment, basic, "mainArea.tab.stacked"}});
    steps_.push_back({"sccheck-15b-taurine-stacked-analysis", {analysis, basic, "mainArea.tab.stacked"}});
    steps_.push_back({"sccheck-15c-taurine-pattern-legend", {"mainArea.tab.pattern", "chart.toolbar.legend"}});
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
    steps_.push_back({"sccheck-12c-taurine-fitted", {analysis, basic, "statusBar.fit.button", "wait-fit"}});
    // The fit's cutoff (FullProf's Rmub 3), and the observed threshold above the reflection table switched to F.
    steps_.push_back({"sccheck-12d-taurine-fitted-reflections", {"choose:OK", extras, "expand:group.refine_ls"}});
    steps_.push_back({"sccheck-12e-taurine-observed-on-f",
                      {experiment, extras, "expand:group.refln", "reflns.thresholdBasis", "choose:F"}});
    // The aliases and constraints that share the first dataset's extinction, each id column as wide as its ids.
    steps_.push_back({"sccheck-12f-taurine-aliases", {analysis, extras, "expand:group.alias"}});
    steps_.push_back({"sccheck-12g-taurine-constraints", {"expand:group.constraint", "reveal:constraints.list"}});
    // At the 3 su cutoff: the reflection table's fit column and the chart's dimmed points, on both views.
    steps_.push_back({"sccheck-12h-taurine-fit-use", {experiment, extras, "expand:group.refln"}});
    steps_.push_back({"sccheck-12i-taurine-fit-use-stacked", {"mainArea.tab.stacked"}});
    // On F axes the weak reflections the cutoff leaves out spread away from the origin; then back to F².
    steps_.push_back({"sccheck-12j-taurine-fit-use-on-f",
                      {"mainArea.tab.pattern", "singleCrystal.toolbar.quantity", "choose:F"}});
    steps_.push_back({"sccheck-12k-taurine-back-on-f-squared", {"singleCrystal.toolbar.quantity", "choose:F²"}});
    // Stacked with the selected dataset highlighted (the default), a point's experiment and h k l on hover, a click
    // there selecting that experiment, then every experiment drawn alike with the selection bold in the legend.
    steps_.push_back({"sccheck-12l-taurine-stacked-highlight", {"mainArea.tab.stacked"}});
    steps_.push_back({"sccheck-12m-taurine-stacked-hover", {"hover:singleCrystal.pointer:0.12,0.86"}});
    steps_.push_back({"sccheck-12n-taurine-stacked-click-selects",
                      {"drag:singleCrystal.pointer:0.12,0.86,0.12,0.86", "hover:singleCrystal.pointer:0.12,0.86"}});
    steps_.push_back({"sccheck-12o-taurine-stacked-all-alike", {"singleCrystal.toolbar.highlight"}});
    steps_.push_back({"sccheck-12p-taurine-stacked-highlight-again", {"singleCrystal.toolbar.highlight"}});
    // The Tb2Ti2O7 verification project's scale-only fit, its scale shown in the parameter table.
    steps_.push_back({"sccheck-13-tb2ti2o7-basic-fitted", QStringList{"resize:1280x768"} + start
                                                              + QStringList{"appBar.tab.project", "open-cli-project:sc-neut-cwl_tb2ti2o7-heidi_basic"}
                                                              + QStringList{analysis, basic, "statusBar.fit.button", "wait-fit",
                                                                            "choose:OK", "parameters.nameFilter", "type:scale"}});
    // LiF is a verification project, which the app does not bundle (ADR-0031): it opens from the CLI projects.
    steps_.push_back({"t16-40-created-saved-reopened",
                      QStringList{"resize:1280x768"} + start
                          + QStringList{"appBar.tab.project", "open-cli-project:pd-xray-cwl_lif_single", experiment, basic, "expand:group.experiments",
                      "experiments.create", "save-as:created", "open-project:created", experiment, "mainArea.blocks.box",
                       "choose:experiment1 · experiment1.edi", text, "scroll-to:text.view:_data_range"}});
    // The Correlations tab: empty before a fit, the fitted matrix, a correlation level and a parameter
    // count typed into the toolbar, and a joint fit's two experiments.
    const QString correlations = QStringLiteral("mainArea.tab.correlations");
    steps_.push_back({"t17-01-correlations-empty",
                      QStringList{"resize:1280x768"} + start + open_example("pd-neut-cwl_cosio-d20")
                          + QStringList{analysis, basic, correlations}});
    steps_.push_back({"t17-02-correlations-fitted", {"statusBar.fit.button", "wait-fit", "choose:OK"}});
    steps_.push_back({"t17-03-correlations-ten", {"correlations.toolbar.parameters.number", "key:Ctrl+A", "type:10", "key:Return"}});
    steps_.push_back({"t17-04-correlations-level", {"correlations.toolbar.level.number", "key:Ctrl+A", "type:0.5", "key:Return"}});
    steps_.push_back({"t17-07-correlations-all", {"correlations.toolbar.parameters.number", "key:Ctrl+A", "type:43", "key:Return"}});
    steps_.push_back({"t17-05-beer-correlations", start + open_example("pd-neut-tof_ferrite-austenite-beer")
                                                      + QStringList{analysis, basic, "statusBar.fit.button", "wait-fit",
                                                                    "choose:OK", correlations}});
    steps_.push_back({"t17-06-beer-second-experiment", {"mainArea.blocks.down"}});
    // The main-view chart toolbars centred in one line (owner, 2026-10-11): the structure view and the pattern chart.
    steps_.push_back({"t17-08-structure-toolbar", {"appBar.tab.structure", basic}});
    steps_.push_back({"t17-09-pattern-toolbar", {analysis, "mainArea.tab.pattern"}});
    // The owner's app findings (2026-10-08): 9, Diagnostics' Show a button the Logging level box's size; 7, the sample
    // form and scattering type disabled while one choice is supported.
    steps_.push_back({"t17-20-diagnostics-show", {"appBar.button.preferences", "preferences.tab.advanced"}});
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
                                                      + QStringList{analysis, basic, "statusBar.fit.button", "wait-fit",
                                                                    "choose:OK", "mainArea.tab.correlations"}});
    steps_.push_back({"t17-41-scan-second-dataset", {"mainArea.blocks.up"}});
    steps_.push_back({"t17-42-scan-first-dataset", {"mainArea.blocks.up"}});
    // A save keeps every dataset's correlations in analysis.edi, and the reopened project shows them.
    steps_.push_back({"t17-43-scan-reopened", {"save-as:scan", "open-project:scan", analysis,
                                               "mainArea.tab.correlations"}});
    steps_.push_back({"t17-44-scan-reopened-other-dataset", {"mainArea.blocks.down"}});
    // Large intensities on the y axes in NumberText's scientific form, clear of the titles (owner, 2026-10-11): the
    // example's experiment loaded again with its scale raised, so the calculated pattern reaches about 1e9.
    steps_.push_back({"t17-50-axis-scientific",
                      QStringList{"key:Escape"} + start + open_example("pd-neut-cwl_lbco-hrpt")
                          + QStringList{experiment, basic,
                                        // NOLINTNEXTLINE(bugprone-suspicious-missing-comma): one step over two lines.
                                        "load-experiments:pd-neut-cwl_lbco-hrpt/project/experiments/"
                                        "hrpt.edi|data_hrpt=data_large|lbco 9()=lbco 30000000()",
                                        analysis, "mainArea.tab.pattern"}});
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
    // Clear returns to Home with no project (ADR-0017 §13).
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
    // Every Preferences tab in both themes, to check that each keeps the same two columns. Run only when asked
    // (`--demo-only prefs-`).
    if (only.startsWith(QLatin1String("prefs-"))) {
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString name = QStringLiteral("prefs-") + theme + QStringLiteral("-");
            steps_.push_back({name + "1-appearance", {"key:Escape", "theme:" + theme, "appBar.button.preferences",
                                                      "preferences.tab.appearance"}});
            steps_.push_back({name + "2-interface", {"preferences.tab.interface"}});
            steps_.push_back({name + "3-projects", {"preferences.tab.projects"}});
            steps_.push_back({name + "4-performance", {"preferences.tab.performance"}});
            steps_.push_back({name + "5-updates", {"preferences.tab.updates"}});
            steps_.push_back({name + "6-ai-assistance", {"preferences.tab.aiAssistance"}});
            steps_.push_back({name + "7-advanced", {"preferences.tab.advanced"}});
        }
    }
    // The one main view (the owner, 2026-11-10): its tabs kept from page to page, the sidebar changing beside it.
    // Run only when asked (`--demo-only mainview-`).
    if (only.startsWith(QLatin1String("mainview-"))) {
        steps_.push_back({"mainview-1-structure", QStringList{"resize:1480x900", "theme:light"} + start +
                                                      open_cli_project("pd-neut-cwl_cosio-d20_2k") +
                                                      QStringList{"appBar.tab.structure", basic}});
        steps_.push_back({"mainview-2-pattern", {"mainArea.tab.pattern"}});
        steps_.push_back({"mainview-3-experiment-keeps-pattern", {"appBar.tab.experiment", basic}});
        steps_.push_back({"mainview-4-analysis-structure", {"appBar.tab.analysis", basic, "mainArea.tab.structure"}});
        steps_.push_back({"mainview-5-analysis-correlations", {"mainArea.tab.correlations"}});
        steps_.push_back({"mainview-6-structure-keeps-correlations", {"appBar.tab.structure", basic}});
        steps_.push_back({"mainview-7-dark", {"theme:dark", "appBar.tab.analysis", "mainArea.tab.pattern"}});
    }
    // The Load and Save project menus with an imported project open, the file EDI_DEMO_IMPORT_PROJECT names (a .gpx,
    // .gsas.json or .pcr). Run only when asked (`--demo-only importsave-`).
    if (only.startsWith(QLatin1String("importsave-"))) {
        const QString imported = "open-project:" + qEnvironmentVariable("EDI_DEMO_IMPORT_PROJECT");
        steps_.push_back({"importsave-1-group", QStringList{"resize:1480x800", "theme:light"} + start +
                                                    QStringList{imported, "appBar.tab.project", basic,
                                                                "reveal:group.getStarted", "expand:group.getStarted"}});
        steps_.push_back({"importsave-2-load-menu", {"project.load"}});
        steps_.push_back({"importsave-3-save-menu", {"key:Escape", "project.saveAs"}});
        steps_.push_back({"importsave-4-save-menu-dark", {"key:Escape", "theme:dark", "project.saveAs"}});
    }
    // The one main view on a new empty project, its first visits and its kept tab, and after an example loads; then
    // frames taken while the pages slide,
    // where the divider beside the sidebar stays put (the owner, 2026-11-11). The new project is written under the
    // documents folder, so run it with a scratch HOME (`--demo-only mainview-empty-`).
    if (only.startsWith(QLatin1String("mainview-empty-"))) {
        steps_.push_back({"mainview-empty-1-structure",
                          QStringList{"resize:1280x768", "theme:light", "appBar.tab.home", "home.start", "appBar.tab.project", basic,
                                      "expand:group.getStarted", "project.create", "createProject.name", "type:sdc", "choose:OK",
                                      "appBar.tab.structure", basic}});
        steps_.push_back({"mainview-empty-2-structure-created", {"expand:group.structures", "structures.create"}});
        steps_.push_back({"mainview-empty-3-experiment-first-visit", {"appBar.tab.experiment", basic}});
        steps_.push_back({"mainview-empty-4-structure-keeps-pattern", {"appBar.tab.structure", basic}});
        steps_.push_back({"mainview-empty-5-example-structure",
                          QStringList{"appBar.button.save"} + start + open_example("pd-neut-cwl_cosio-d20_2k")
                              + QStringList{"appBar.tab.structure", basic}});
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString name = QStringLiteral("mainview-empty-slide-") + theme + QLatin1Char('-');
            const QStringList pages{"experiment", "analysis", "structure", "experiment"};
            steps_.push_back({name + "0-structure", {"theme:" + theme, "appBar.tab.structure"}});
            for (qsizetype i = 0; i < pages.size(); ++i) {
                const QString to = QString::number(i + 1) + "-to-" + pages[i];
                steps_.push_back({name + to + "-40ms", {"wait-settled", "appBar.tab." + pages[i], "capture-at:40"}});
                steps_.push_back({name + to + "-120ms", {"appBar.tab." + (i == 0 ? QStringLiteral("structure") : pages[i - 1]),
                                                         "wait-settled", "appBar.tab." + pages[i], "capture-at:120"}});
            }
        }
    }
    // Every built-in tutorial from its first step to its last by the status bar's Next alone, no other input (the
    // owner, 2026-11-11). Each ends with Discard, which gives the set-aside project back. Run only when asked
    // (`--demo-only tutorials-`, or `tutorials-<n>-` for one).
    if (only.startsWith(QLatin1String("tutorials-"))) {
        QStringList ids;
        if (QFile manifest(QStringLiteral(":/edi/tutorials/manifest.json")); manifest.open(QIODevice::ReadOnly)) {
            const QJsonDocument document = QJsonDocument::fromJson(manifest.readAll());
            const QJsonArray list = document.isObject() ? document.object().value(QStringLiteral("tutorials")).toArray() : document.array();
            for (const auto& tutorial : list) ids.append(tutorial.toObject().value(QStringLiteral("id")).toString());
        }
        steps_.push_back({"tutorials-00-start", QStringList{"resize:1280x768", "theme:light"}});
        for (qsizetype i = 0; i < ids.size(); ++i) {
            const QString name = QStringLiteral("tutorials-%1-%2").arg(i + 1, 2, 10, QLatin1Char('0')).arg(ids[i]);
            steps_.push_back({name, {"appBar.tab.home", "home.tutorials", QStringLiteral("show:tutorials.list:%1").arg(i),
                                     "tutorials.open." + ids[i], "tutorial-next-all"}});
            steps_.push_back({name + "-closed", {"tutorial-close"}});
        }
    }
    // The Tutorials dialog and the Examples list with the longest tag row in the catalogue, the Co2SiO4 2.3 K case,
    // at a desktop width and a narrow one, where its tags wrap instead of being cut short (`--demo-only tags-`).
    if (only.startsWith(QLatin1String("tags-"))) {
        const QString longest = QStringLiteral("pd-neut-cwl_cosio-d20_2k");
        const qsizetype row = ExampleListModel::bundledIds().indexOf(longest);
        // The Tutorials list is in the manifest's order, the Interface tour first.
        qsizetype tutorial = -1;
        if (QFile manifest(QStringLiteral(":/edi/tutorials/manifest.json")); manifest.open(QIODevice::ReadOnly)) {
            const QJsonArray list = QJsonDocument::fromJson(manifest.readAll()).object().value(QStringLiteral("tutorials")).toArray();
            for (qsizetype i = 0; i < list.size() && tutorial < 0; ++i)
                if (list[i].toObject().value(QStringLiteral("id")).toString() == longest) tutorial = i;
        }
        steps_.push_back({"tags-01-tutorials-wide", {"resize:1480x900", "theme:light", "appBar.tab.home", "home.tutorials",
                                                     QStringLiteral("show:tutorials.list:%1").arg(tutorial)}});
        steps_.push_back({"tags-02-tutorials-narrow", {"key:Escape", "resize:1000x760", "home.tutorials",
                                                       QStringLiteral("show:tutorials.list:%1").arg(tutorial)}});
        steps_.push_back({"tags-03-examples", QStringList{"key:Escape", "resize:1480x900", "appBar.tab.project", "sideBar.tab.basic",
                                                          "group.examples", QStringLiteral("show:examples.list:%1").arg(row)}});
    }
    // The documentation's concept figures, from the Co2SiO4 magnetic case, in both themes, each saved by Save image
    // (the owner, 2026-11-10). Run only when asked (`--demo-only concepts-`).
    if (only.startsWith(QLatin1String("concepts-"))) {
        // Opened and fitted once; the dark figures are the same fit in the other theme.
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString name = QStringLiteral("concepts-") + theme + QStringLiteral("-");
            const QStringList open = theme == QLatin1String("light")
                                         ? QStringList{"resize:1314x900"} + start + open_cli_project("pd-neut-cwl_cosio-d20_2k") +
                                               QStringList{"preference:chartIncludedOnly=true", "preference:patternMeasuredStyle=line", "theme:light", analysis, basic,
                                                           "statusBar.fit.button", "wait-fit", "choose:OK"}
                                         : QStringList{"theme:dark", analysis};
            steps_.push_back({name + "1-fit", open + QStringList{"mainArea.tab.pattern", "save-image:mainArea.saveImage|" + name + "refinement.png|2"}});
            steps_.push_back({name + "2-model", {structure, "mainArea.tab.structure",
                                                 "save-image:mainArea.saveImage|" + name + "model.png|2"}});
        }
        // The measured pattern alone: the fitted experiment's chart with every other curve hidden, as legend clicks
        // hide them, and so its residual and tick panes. Last, so the fitted figures come first.
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString name = QStringLiteral("concepts-") + theme + QStringLiteral("-");
            // The window shorter by the tick and residual panes, so the measured pattern's plot is the fitted one's
            // size: the two read as one chart growing.
            QStringList actions{"theme:" + theme, analysis, "mainArea.tab.pattern"};
            if (theme == QLatin1String("light")) {
                actions.append(QStringLiteral("resize:1314x709"));
                actions.append(QStringLiteral("preference:structureCurves=false"));
                actions.append(QStringLiteral("measured-only"));
            }
            actions.append("save-image:mainArea.saveImage|" + name + "pattern.png|2");
            steps_.push_back({name + "3-pattern", actions});
        }
    }
    // The sidebar's pins, empty tabs and Performance row, the structure view's atom view names, in both themes (the
    // owner, 2026-11-10). Run only when asked (`--demo-only sidebar-`).
    if (only.startsWith(QLatin1String("sidebar-"))) {
        const QString settings = QStringLiteral("sideBar.tab.settings");
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString name = QStringLiteral("sidebar-") + theme + QStringLiteral("-");
            const QStringList open = theme == QLatin1String("light")
                                         ? QStringList{"resize:1280x960"} + start + open_cli_project("pd-neut-cwl_lbco-hrpt_start-2")
                                         : QStringList{};
            steps_.push_back({name + "1-pinned", open + QStringList{"theme:" + theme, structure, basic, "expand:group.cell",
                                                                    "group.cell.pin", "expand:group.atom_site"}});
            steps_.push_back({name + "2-appearance", {extras, "expand:group.appearance"}});
            steps_.push_back({name + "3-empty-settings", {settings}});
            steps_.push_back({name + "4-performance", {"appBar.tab.experiment", settings, "expand:group.performance"}});
            steps_.push_back({name + "5-report-extra", {"appBar.tab.report", extras}});
            // Unpinned again, so the next theme starts as this one did.
            steps_.push_back({name + "6-unpinned", {structure, basic, "group.cell.pin"}});
        }
    }
    // An example from an online collection (ADR-0068), opened from the Examples list, the list searched down to the
    // rows that fit the sidebar. Run only when asked (`--demo-only collection-`), with EDI_ONLINE_SOURCES naming the
    // fixture collections under tests/fixtures/online_sources.
    if (only.startsWith(QLatin1String("collection-"))) {
        steps_.push_back({"collection-1-list", start + QStringList{"appBar.tab.project", basic, "examples.search", "type:HRPT"}});
        steps_.push_back({"collection-2-opened", {"examples.open.lbco-hrpt-project"}});
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
    // `e58-report`: the report's first structure and first pattern figures, after the bundled scan's fit, each brought
    // into view, so a figure drawn empty or without its calculated series shows.
    if (only.startsWith(QLatin1String("e58-report"))) {
        // EDI_DEMO_REPORT_CLI names another bundled project (the owner's TOF case, 2026-11-21).
        const QString cli = qEnvironmentVariable("EDI_DEMO_REPORT_CLI", QStringLiteral("pd-neut-cwl_cosio-d20_scan-3f"));
        const QStringList open = start + open_cli_project(cli) +
                                 QStringList{analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK"};
        // The report is built after the fit on a worker and its figures load a slice at a time: settled first.
        steps_.push_back({"e58-report-1-structure", QStringList{"resize:1280x960"} + open +
                                                        QStringList{"appBar.tab.report", "wait-settled",
                                                                    "assert-report-figures"}});
        steps_.push_back({"e58-report-2-pattern", {"reveal:report.pattern.0"}});
        // Brought into view again once the whole report has laid out (the first reveal can come before it scrolls).
        steps_.push_back({"e58-report-2b-structure", {"reveal:report.structure.0"}});
        // Left and shown again: a report built before the fit's last calculation reached the project shows here
        // whether it is ever built again.
        steps_.push_back({"e58-report-3-again", {"appBar.tab.analysis", "wait-settled", "appBar.tab.report",
                                                 "wait-settled", "assert-report-figures", "reveal:report.pattern.0"}});
        // Saved too, where EDI_DEMO_REPORT_DIR names, so the app's own report data can be read.
        if (const QString kept = qEnvironmentVariable("EDI_DEMO_REPORT_DIR"); !kept.isEmpty())
            steps_.push_back({"e58-report-4-saved", {"save-as:" + kept, "report.save"}});
    }
    if (only.startsWith(QLatin1String("report-scan-"))) {
        // EDI_DEMO_REPORT_PROJECT names a fitted scan to open instead of fitting the bundled one.
        const QString fitted = qEnvironmentVariable("EDI_DEMO_REPORT_PROJECT");
        const QStringList open =
            fitted.isEmpty() ? start + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f") +
                                   QStringList{analysis, basic, "statusBar.fit.button", "wait-fit",
                                               "choose:OK"}
                             : QStringList{"open-project:" + fitted};
        steps_.push_back({"report-scan-1-evolution", QStringList{"resize:1280x960"} + open +
                                                         QStringList{"appBar.tab.report", "reveal:report.evolution"}});
        // Saved where EDI_DEMO_REPORT_DIR names, so the report files outlive the run, else in the run's own folder.
        const QString kept = qEnvironmentVariable("EDI_DEMO_REPORT_DIR");
        steps_.push_back({"report-scan-2-saved", {"save-as:" + (kept.isEmpty() ? QStringLiteral("report-scan") : kept),
                                                  "report.writesPdf", "report.save"}});
    }
    // A scan opened from the file EDI_DEMO_SCAN_PROJECT names, its pages, then Fit and Reset, which stop the run when
    // disabled. Run only when asked (`--demo-only scan-open-`).
    // The scale check's GUI stall probe (EDI_STALL_PROBE): a series of joint fits, EDI_DEMO_SCAN_PROJECT, opened, its
    // Stacked and Map views shown, fitted to the end with each view in turn, then its Evolution. Run only when asked
    // (`--demo-only stall-`).
    // The synthetic 100-point series opened from the examples list (its collection entry downloaded), then shown on the
    // Experiment page with its views. Run only when asked (`--demo-only examplecheck-`).
    // The chart-consistency review's set: every chart view of the Experiment and Analysis pages for the series
    // EDI_DEMO_SCAN_PROJECT after its fit, then a single crystal's Pattern and Meas vs calc. Run only when asked
    // (`--demo-only review-`).
    // Each project of EDI_DEMO_PROJECT_LIST (comma-separated folders) opened, for its free and fixed counts in the status
    // bar (`--demo-only freecheck-`).
    if (only.startsWith(QLatin1String("freecheck-"))) {
        const QStringList folders = qEnvironmentVariable("EDI_DEMO_PROJECT_LIST").split(QLatin1Char(','), Qt::SkipEmptyParts);
        for (qsizetype i = 0; i < folders.size(); ++i) {
            QStringList actions;
            if (i == 0) actions << "resize:1480x800";
            actions << "open-project:" + folders[i] << analysis;
            steps_.push_back({QStringLiteral("freecheck-%1").arg(i + 1, 2, 10, QLatin1Char('0')), actions});
        }
    }
    // Map's More popup with its colour map box, on the synthetic series (`--demo-only mappopup-`).
    if (only.startsWith(QLatin1String("mappopup-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        steps_.push_back({"mappopup-1-open", {"resize:1480x800", "open-project:" + root + "pd-neut-tof_ncaf-wish-5bank_synthetic-100p/project",
                                              "appBar.tab.experiment", basic, "mainArea.tab.map", "scanView.map.toolbar.more"}});
        steps_.push_back({"mappopup-2-list", {"scanView.map.toolbar.colourMap.overflow"}});
    }
    // Every main-view tab after a scan's fit was stopped on Meas vs calc: the model, the charts and the table show the
    // last run followed, not the first (`--demo-only measfollow-`).
    if (only.startsWith(QLatin1String("measfollow-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        steps_.push_back({"measfollow-1-meascalc", {"resize:1480x800", "open-project:" + root + "pd-neut-cwl_cosio-d20_scan-213f/project",
                                                    analysis, basic, "mainArea.tab.measCalc", "statusBar.fit.button",
                                                    "wait-files:20", "statusBar.fit.button", "wait-fit"}});
        for (const QString& tab : {QStringLiteral("pattern"), QStringLiteral("correlations"), QStringLiteral("stacked"),
                                   QStringLiteral("map"), QStringLiteral("evolution"), QStringLiteral("structure")}) {
            steps_.push_back({"measfollow-2-" + tab, {"mainArea.tab." + tab}});
        }
    }
    // A scan's Experiments table, scrolled near its end, its dataset selector open, and Stacked zoomed on its rows
    // (`--demo-only exptable-`).
    if (only.startsWith(QLatin1String("exptable-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        const QString experimentTab = QStringLiteral("appBar.tab.experiment");
        steps_.push_back({"exptable-1-top", {"resize:1480x800", "open-project:" + root + "pd-neut-cwl_cosio-d20_scan-213f/project",
                                             experimentTab, basic}});
        steps_.push_back({"exptable-2-scrolled", {"show:experiments.list:205:0"}});
        steps_.push_back({"exptable-3-selector", {"mainArea.blocks.box"}});
        steps_.push_back({"exptable-4-stacked", {"key:Escape", "mainArea.tab.stacked"}});
        steps_.push_back({"exptable-5-stacked-zoomed", {"zoom-rows:stacked"}});
    }
    // Structure > Extra's generated tables, each opened from folded: every one shows its rows and columns
    // (`--demo-only collapsed-`).
    if (only.startsWith(QLatin1String("collapsed-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        const QString structureTab = QStringLiteral("appBar.tab.structure");
        // The tables get their rows while their groups are folded and off screen; only then are the groups opened.
        steps_.push_back({"collapsed-0-elsewhere", {"resize:1480x800", "open-project:" + root + "pd-neut-cwl_cosio-d20_2k/project",
                                                    structureTab, extras, "appBar.tab.experiment", "appBar.tab.analysis",
                                                    "appBar.tab.project"}});
        steps_.push_back({"collapsed-1-symop", {structureTab, extras, "expand:group.space_group_symop",
                                                "assert-table:generated.space_group_symop.list"}});
        steps_.push_back({"collapsed-2-atoms", {"expand:group.expanded_atom_site", "reveal:group.expanded_atom_site",
                                                "assert-table:generated.expanded_atom_site.list"}});
        steps_.push_back({"collapsed-3-moments", {"expand:group.expanded_atom_site_moment",
                                                  "reveal:group.expanded_atom_site_moment",
                                                  "assert-table:generated.expanded_atom_site_moment.list"}});
    }
    // A single project fitted, its parameter table after the fit (`--demo-only lbcofit-`).
    if (only.startsWith(QLatin1String("lbcofit-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        steps_.push_back({"lbcofit-1-table", {"resize:1480x800", "open-project:" + root + "pd-neut-cwl_lbco-hrpt/project",
                                              analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK"}});
        steps_.push_back({"lbcofit-2-alias-picker", {extras, "expand:group.alias", "reveal:group.alias", "alias.parameter.0"}});
    }
    // The moments table of a magnetic structure, with |M| and its angles (`--demo-only moments-`).
    if (only.startsWith(QLatin1String("moments-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        steps_.push_back({"moments-1-crystal-axes", {"resize:1480x800", "open-project:" + root + "pd-neut-cwl_cosio-d20_2k/project",
                                                     "appBar.tab.structure", basic, "expand:group.atom_site_moment",
                                                     "reveal:group.atom_site_moment"}});
    }
    // The series dialog for the synthetic example's files, grouped before it loads (`--demo-only seriesload-`).
    if (only.startsWith(QLatin1String("seriesload-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        steps_.push_back({"seriesload-1-dialog", {"resize:1480x800", "open-project:" + root + "pd-neut-tof_ncaf-wish/project",
                                                  "appBar.tab.experiment", basic,
                                                  "ask-series:" + root + "pd-neut-tof_ncaf-wish-5bank_synthetic-100p/project/data"}});
    }
    // The series fitted, captured before its result dialog is closed (`--demo-only fitcheck-`).
    if (only.startsWith(QLatin1String("fitcheck-"))) {
        steps_.push_back({"fitcheck-1-after-fit", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                                                   analysis, basic, "statusBar.fit.button", "wait-files:100", "wait-fit"}});
    }
    // Analysis > Structure on a single fit, a joint fit and a small series, each opened straight to it
    // (`--demo-only structcmp-`).
    if (only.startsWith(QLatin1String("structcmp-"))) {
        const QString root = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/";
        steps_.push_back({"structcmp-1-single", {"resize:1480x800", "open-project:" + root + "pd-neut-tof_ncaf-wish/project", analysis, basic, "mainArea.tab.structure"}});
        steps_.push_back({"structcmp-1b-single-table-later", {"mainArea.tab.pattern"}});
        steps_.push_back({"structcmp-2-joint", {"open-project:" + root + "pd-neut-tof_ncaf-wish-5bank_start-5/project", analysis, basic, "mainArea.tab.structure"}});
        steps_.push_back({"structcmp-3-series", {"open-project:" + root + "pd-neut-tof_ncaf-wish-5bank_scan-6p/project", analysis, basic, "mainArea.tab.structure"}});
    }
    // A saved, fitted series opened again: Analysis > Structure and the parameter table, then the Correlations of the
    // first run and of the last run fitted (`--demo-only reopensaved-`).
    if (only.startsWith(QLatin1String("reopensaved-"))) {
        const QString open = "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT");
        steps_.push_back({"reopensaved-1-structure", {"resize:1480x800", open, analysis, basic, "mainArea.tab.structure"}});
        steps_.push_back({"reopensaved-2-structure-page", {"appBar.tab.structure"}});
        steps_.push_back({"reopensaved-3-analysis-structure-again", {analysis, "mainArea.tab.pattern", "mainArea.tab.structure"}});
        steps_.push_back({"reopensaved-4-correlations-last", {"mainArea.tab.stacked", "mainArea.series.point.box", "type:p099", "choose:p099", "mainArea.tab.correlations"}});
        steps_.push_back({"reopensaved-5-evolution-picker", {"mainArea.tab.evolution", "evolution.parameters.box"}});
        steps_.push_back({"reopensaved-6-evolution-picker-cell", {"type:cell"}});
    }
    // The included range on a fitted series' Stacked and Map, both rows and every x (`--demo-only included-`).
    if (only.startsWith(QLatin1String("included-"))) {
        const QString open = "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT");
        steps_.push_back({"included-1-stacked-byrun-q-off", {"resize:1480x800", open, analysis, basic, "mainArea.tab.stacked",
                                                             "scanView.stacked.toolbar.xaxis", "choose:x: Q"}});
        steps_.push_back({"included-2-stacked-byrun-q-on", {"scanView.stacked.toolbar.includedRange"}});
        steps_.push_back({"included-3-stacked-bybank-q", {"scanView.stacked.toolbar.rows", "choose:Experiment"}});
        steps_.push_back({"included-5-stacked-byrun-d", {"scanView.stacked.toolbar.rows", "choose:File",
                                                          "scanView.stacked.toolbar.xaxis", "choose:x: d-spacing"}});
        steps_.push_back({"included-6-map-byrun-q", {"mainArea.tab.map", "scanView.map.toolbar.xaxis", "choose:x: Q"}});
        steps_.push_back({"included-7-map-bybank-q", {"scanView.map.toolbar.rows", "choose:Experiment"}});
    }
    if (only.startsWith(QLatin1String("review-"))) {
        const QString experimentTab = QStringLiteral("appBar.tab.experiment");
        // Before the fit: the Map on Q by bank (the owner's empty map, 2026-11-16), then back to d.
        steps_.push_back({"review-00a-prefit-map-bybank-q",
                          {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                           experimentTab, basic, "mainArea.tab.map", "scanView.map.toolbar.rows", "choose:Experiment",
                           "scanView.map.toolbar.xaxis", "choose:x: Q"}});
        steps_.push_back({"review-00-fitted",
                          {"scanView.map.toolbar.xaxis", "choose:x: d-spacing", "scanView.map.toolbar.rows", "choose:File",
                           analysis, basic, "statusBar.fit.button", "wait-files:100", "wait-fit", "choose:OK"}});
        steps_.push_back({"review-01-experiment-pattern", {experimentTab, basic, "mainArea.tab.pattern"}});
        steps_.push_back({"review-02-experiment-meascalc", {"mainArea.tab.measCalc"}});
        steps_.push_back({"review-03-experiment-stacked-byrun", {"mainArea.tab.stacked"}});
        steps_.push_back({"review-04-experiment-stacked-bybank", {"scanView.stacked.toolbar.rows", "choose:Experiment"}});
        steps_.push_back({"review-05-experiment-map-bybank", {"mainArea.tab.map"}});
        steps_.push_back({"review-05m-experiment-map-more", {"scanView.map.toolbar.more"}});
        steps_.push_back({"review-05n-experiment-map-more-closed", {"scanView.map.toolbar.more"}});
        steps_.push_back({"review-06-experiment-map-byrun", {"scanView.map.toolbar.rows", "choose:File"}});
        steps_.push_back({"review-06b-experiment-map-byrun-q", {"scanView.map.toolbar.xaxis", "choose:x: Q"}});
        steps_.push_back({"review-06c-experiment-map-bybank-q", {"scanView.map.toolbar.rows", "choose:Experiment"}});
        steps_.push_back({"review-06d-experiment-stacked-bybank-q", {"mainArea.tab.stacked"}});
        steps_.push_back({"review-06e-back-to-d", {"scanView.stacked.toolbar.xaxis", "choose:x: d-spacing",
                                                   "scanView.stacked.toolbar.rows", "choose:File"}});
        steps_.push_back({"review-07-analysis-pattern", {analysis, basic, "mainArea.tab.pattern"}});
        steps_.push_back({"review-08-analysis-meascalc", {"mainArea.tab.measCalc"}});
        steps_.push_back({"review-09-analysis-structure", {"mainArea.tab.structure"}});
        steps_.push_back({"review-10-analysis-evolution-shared", {"mainArea.tab.evolution"}});
        steps_.push_back({"review-11-analysis-evolution-perbank", {"evolution.toolbar.scope", "choose:Per experiment"}});
        steps_.push_back({"review-11a-perbank-picker", {"evolution.parameters.box"}});
        steps_.push_back({"review-11b-bank-filter", {"key:Escape", "evolution.toolbar.bank"}});
        steps_.push_back({"review-11c-bank-selector", {"key:Escape", "mainArea.series.bank.box"}});
        steps_.push_back({"review-11d-closed", {"key:Escape"}});
        steps_.push_back({"review-12-analysis-stacked", {"mainArea.tab.stacked"}});
        steps_.push_back({"review-13-analysis-map", {"mainArea.tab.map"}});
        steps_.push_back({"review-14-analysis-correlations", {"mainArea.tab.correlations"}});
        steps_.push_back({"review-14b-analysis-correlations-last-run",
                          {"mainArea.tab.stacked", "mainArea.series.point.box", "type:p099", "choose:p099", "mainArea.tab.correlations"}});
        steps_.push_back({"review-14c-correlations-other-run", {"mainArea.tab.stacked", "mainArea.series.point.box", "type:p050", "choose:p050", "mainArea.tab.correlations"}});
        steps_.push_back({"review-14d-evolution-picker-full-name", {"mainArea.tab.evolution", "evolution.toolbar.scope", "choose:Shared", "evolution.parameters.box", "type:fract"}});
        steps_.push_back({"review-14e-evolution-picker-short-name", {"key:Escape", "evolution.parameters.box", "type:biso"}});
    }
    // The source example opened twice, as Recent projects names it (a trailing separator): each opens a copy of its
    // own (`--demo-only reopen-`).
    if (only.startsWith(QLatin1String("reopen-"))) {
        const QString source = QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + "/pd-neut-tof_ncaf-wish-5bank_synthetic-100p/project/";
        steps_.push_back({"reopen-1-first", {"resize:1480x800", "open-project:" + source, "appBar.tab.experiment", basic}});
        steps_.push_back({"reopen-2-second", {"open-project:" + source, "appBar.tab.experiment", basic}});
    }
    // A single fit's results dialog, from a fresh start (`--demo-only fitdialog-`).
    if (only.startsWith(QLatin1String("fitdialog-"))) {
        steps_.push_back({"fitdialog-1-single", QStringList{"resize:1480x800", "home.start", "expand:group.examples"} +
                                                    open_example("pd-neut-cwl_lbco-hrpt") +
                                                    QStringList{analysis, basic, "statusBar.fit.button", "wait-fit"}});
    }
    // The review's single crystal, from a fresh start (`--demo-only reviewsc-`).
    if (only.startsWith(QLatin1String("reviewsc-"))) {
        steps_.push_back({"reviewsc-1-sc-pattern", QStringList{"resize:1480x800", "home.start", "expand:group.examples"} +
                                                       open_example("sc-neut-cwl_tb2ti2o7-heidi") +
                                                       QStringList{"appBar.tab.experiment", basic, "mainArea.tab.pattern"}});
        steps_.push_back({"reviewsc-2-sc-meascalc", {"mainArea.tab.measCalc"}});
    }
    if (only.startsWith(QLatin1String("examplecheck-"))) {
        steps_.push_back({"examplecheck-1-opened",
                          QStringList{"resize:1480x800", "home.start", "expand:group.examples"} +
                              open_example("pd-neut-tof_ncaf-wish-5bank_synthetic-100p")});
        steps_.push_back({"examplecheck-2-experiment", {"appBar.tab.experiment", basic}});
        steps_.push_back({"examplecheck-3-stacked", {"mainArea.tab.stacked"}});
    }
    // An experiment without data shows Load data… in its row: its menu, open, from a fresh start
    // (`--demo-only datamenu-`).
    if (only.startsWith(QLatin1String("datamenu-"))) {
        steps_.push_back({"datamenu-1-open", QStringList{"resize:1480x800", "home.start", "expand:group.examples"} +
                                                 open_example("pd-neut-cwl_lbco_simulation") +
                                                 QStringList{"appBar.tab.experiment", basic, "experiments.loadData.0"}});
    }
    // The GUI watchdog's scenarios (ADR-0102), run only when asked, each traced with EDI_UI_TRACE=1 for
    // tools/ci/gui_watchdog.py: `e58-pages` shows every page with the scan EDI_DEMO_SCAN_PROJECT open; `e58-banks` steps
    // through a copy of the five-bank NCAF set's experiments on Experiment and on Analysis; `e58-pattern` presses the
    // scan's next and previous dataset ten times each on both pages' Pattern, at the driver's 100 ms pace; `e58-series`
    // fits the series EDI_DEMO_SCAN_PROJECT to its end. A step's trace name is the measured step's; the steps before
    // the first named one only set the scenario up and are not measured.
    const auto named = [this](const QString& trace, int navigation = 0) {
        steps_.back().trace = trace;
        steps_.back().navigation = navigation;
    };
    if (only.startsWith(QLatin1String("e58-pages"))) {
        steps_.push_back({"e58-pages-00-opened", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT")}});
        const QStringList pages{"home", "project", "structure", "experiment", "analysis", "report", "experiment", "report",
                                "analysis"};
        for (qsizetype i = 0; i < pages.size(); ++i) {
            steps_.push_back({QStringLiteral("e58-pages-%1-page-%2").arg(i + 1, 2, 10, QLatin1Char('0')).arg(pages[i]),
                              {"appBar.tab." + pages[i]}});
            named("page-" + pages[i]);
        }
    }
    // `e58-fit`: numbers fitted to their typed columns, with the project EDI_DEMO_FIT_PROJECT open (long written tokens),
    // then a value cell edited across a resize and left.
    if (only.startsWith(QLatin1String("e58-fit"))) {
        const QString open = "open-project:" + qEnvironmentVariable("EDI_DEMO_FIT_PROJECT");
        // At the owner's window of about 1000 px (2026-11-21): the Examples list before a project, the fit's results
        // dialog, then the Analysis and Structure tables.
        // The Examples list scrolled to its end, as the owner saw rows 24 and 25 overlap (2026-11-21).
        steps_.push_back({"e58-fit-0-examples", {"resize:1000x900", "home.start", "expand:group.examples",
                                                 "wait-settled", "scroll-frames:examples.list",
                                                 "scroll-frames:examples.list", "scroll-frames:examples.list",
                                                 "wait-settled"}});
        steps_.push_back({"e58-fit-1-results", {"resize:1000x620", open, "appBar.tab.analysis", "mainArea.tab.pattern", "statusBar.fit.button",
                                                "wait-fit"}});
        steps_.push_back({"e58-fit-2-analysis", {"choose:OK"}});
        steps_.push_back({"e58-fit-3-structure", {"appBar.tab.structure", "expand:group.atom_site_aniso"}});
        steps_.push_back({"e58-fit-4-edit-resized", {"appBar.tab.analysis", "parameters.value.0", "resize:1600x900",
                                                     "resize:1000x620"}});
        steps_.push_back({"e58-fit-5-left", {"key:Tab"}});
    }
    // `e58-scan`: a large scan's Stacked and Map views, each read only as far as it shows (the owner, 2026-11-21).
    if (only == QLatin1String("e58-scan")) {
        steps_.push_back({"e58-scan-1-stacked", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                                                 "appBar.tab.analysis", "mainArea.tab.stacked", "wait-scan:stacked"}});
        steps_.push_back({"e58-scan-2-map", {"mainArea.tab.map", "wait-scan:map"}});
        steps_.push_back({"e58-scan-3-stacked-again", {"mainArea.tab.stacked", "wait-scan:stacked"}});
    }
    // `e58-widths`: the sidebar's width rule checked at many window widths: the
    // fitted joint project's Analysis and a scan's Structure with Atomic displacement, at every width EDI_WIDTHS lists.
    // `e58-expand`: every sidebar group of Structure, Experiment and Analysis, Main and Extra tabs, opened in turn and
    // timed frame by frame (the owner, 2026-11-23: lag, flicker and jumps in height on unfold), after a fit.
    if (only == QLatin1String("e58-expand")) {
        steps_.push_back({"e58-expand-0", {"preference:loggingLevel=Info", "resize:1496x900",
                                           "open-cli-project:" + qEnvironmentVariable("EDI_EXPAND_PROJECT", QStringLiteral("pd-neut-cwl_cosio-d20")),
                                           "wait-settled", "appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& page : {QStringLiteral("structure"), QStringLiteral("experiment"), QStringLiteral("analysis")})
            for (const QString& tab : {QStringLiteral("basic"), QStringLiteral("extras")}) {
                steps_.push_back({"e58-expand-" + page + "-" + tab, {"appBar.tab." + page, "sideBar.tab." + tab, "wait-settled", "expand-frames-all", "wait-settled"}});
                steps_.back().capture = false;
            }
    }
    // `e58-icons`: the sidebar's width icon and the groups' pins in light mode, at rest and pointed at (the owner,
    // 2026-11-23: text colour, a title icon's size, one centre line).
    if (only == QLatin1String("e58-icons")) {
        steps_.push_back({"e58-icons-1-structure", {"resize:1480x900", "theme:light", "open-cli-project:pd-neut-cwl_cosio-d20", "wait-settled",
                                                    "appBar.tab.structure", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-icons-2-width-hovered", {"hover:sideBar.width", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-icons-3-analysis", {"hover:appBar.tab.home", "appBar.tab.analysis", "wait-settled", "check-layout"}});
    }
    // `e58-case48`: the 2k example fitted, on Analysis at three window widths in Auto, then every page (the owner's case
    // 48, 2026-11-23: spare before Free with the sidebar wider than its table; legend labels cut).
    if (only == QLatin1String("e58-case48")) {
        steps_.push_back({"e58-case48-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k",
                                           "wait-settled", "appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled",
                                           "preference:patternLegendShown=true", "mainArea.tab.pattern", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-case48-meascalc", {"mainArea.tab.measCalc", "wait-settled", "check-layout"}});
        for (const QString& width : {QStringLiteral("1280"), QStringLiteral("1496"), QStringLiteral("1920")})
            steps_.push_back({"e58-case48-analysis-" + width, {"resize:" + width + "x900", "mainArea.tab.pattern", "wait-settled", "check-layout"}});
        for (const QString& page : {QStringLiteral("project"), QStringLiteral("structure"), QStringLiteral("experiment"), QStringLiteral("report"),
                                    QStringLiteral("analysis")})
            steps_.push_back({"e58-case48-page-" + page, {"resize:1496x900", "appBar.tab." + page, "wait-settled", "check-layout"}});
    }
    // `e58-dialogs`: the fit's results dialog, at the owner's window of about 1000 px and at 1496 px, the layout check
    // over it (D1: at most its content's width plus 2 em, every row and value whole).
    if (only == QLatin1String("e58-dialogs")) {
        steps_.push_back({"e58-dialogs-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled", "appBar.tab.analysis",
                                            "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& size : {QStringLiteral("1496x900"), QStringLiteral("1000x620")})
            steps_.push_back({"e58-dialogs-fit-results-" + size, {"resize:" + size, "wait-settled", "statusBar.fit.button", "wait-fit", "wait-settled", "check-layout", "choose:OK", "wait-settled"}});
    }
    // `e58-legend`: the 2k example fitted, every legend entry of the Analysis pattern switched off: nothing is drawn.
    if (only == QLatin1String("e58-legend")) {
        steps_.push_back({"e58-legend-1-shown", {"resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled", "appBar.tab.analysis",
                                                 "statusBar.fit.button", "wait-fit", "choose:OK", "preference:patternLegendShown=true",
                                                 "mainArea.tab.pattern", "wait-settled"}});
        steps_.push_back({"e58-legend-2-all-off", {"legend-hide-all:chart", "wait-settled", "check-hidden-series:chart"}});
        // The other kinds of series: the structure curves, and a time-of-flight pattern with its own Bragg rows.
        steps_.push_back({"e58-legend-3-curves", {"preference:structureCurves=true", "legend-hide-all:chart", "wait-settled", "check-hidden-series:chart"}});
        steps_.push_back({"e58-legend-4-tof", {"open-cli-project:pd-neut-tof_ncaf-wish", "wait-settled", "appBar.tab.analysis", "preference:patternLegendShown=true",
                                               "mainArea.tab.pattern", "wait-settled", "legend-hide-all:chart", "wait-settled", "check-hidden-series:chart"}});
    }
    // `e58-report-pdf`: a fitted scan's report saved, PDF included, right after the Report page first shows.
    if (only == QLatin1String("e58-report-pdf")) {
        const QString kept = qEnvironmentVariable("EDI_DEMO_REPORT_DIR");
        steps_.push_back({"e58-report-pdf-1-saved", QStringList{"resize:1280x960", "open-cli-project:pd-neut-cwl_cosio-d20_scan-3f", "wait-settled",
                                                                  "appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK",
                                                                  "save-as:" + kept, "appBar.tab.report", "report.writesPdf", "report.save", "wait-settled",
                                                                  "check-report-figures-saved"}});
    }
    // `e58-unfold`: each sidebar group opened in turn on the scan project, one named step per unfold, folded again
    // after (the owner, 2026-11-23: no unfold over 100 ms). EDI_UI_UNFOLD_INVENTORY lists the groups as JSON
    // [{"page", "tab", "group"}]; without it, the groups the example projects show.
    if (only.startsWith(QLatin1String("e58-unfold"))) {
        // `e58-unfold-pr`: the slowest few groups only, for a pull request's bound; `e58-unfold` every group, nightly.
        const bool representative = only == QLatin1String("e58-unfold-pr");
        QList<std::array<QString, 3>> inventory;
        const QJsonDocument declared = QJsonDocument::fromJson(qgetenv("EDI_UI_UNFOLD_INVENTORY"));
        for (const auto& entry : declared.array())
            inventory.append({entry[QStringLiteral("page")].toString(), entry[QStringLiteral("tab")].toString(), entry[QStringLiteral("group")].toString()});
        if (inventory.isEmpty() && representative) {
            const QList<std::pair<QString, QStringList>> slowest{
                {QStringLiteral("structure/basic"), {"atom_site"}},
                {QStringLiteral("structure/extras"), {"space_group_symop", "expanded_atom_site"}},
                {QStringLiteral("experiment/extras"), {"data", "refln"}},
                {QStringLiteral("analysis/extras"), {"fit_result_bank"}}};
            for (const auto& [where, groups] : slowest)
                for (const QString& group : groups) inventory.append({where.section(QLatin1Char('/'), 0, 0), where.section(QLatin1Char('/'), 1), "group." + group});
        }
        if (inventory.isEmpty()) {
            const QList<std::pair<QString, QStringList>> builtin{
                {QStringLiteral("structure/basic"), {"structures", "space_group", "cell", "atom_site", "atom_site_aniso"}},
                {QStringLiteral("structure/extras"), {"scattering_length", "geom", "space_group_symop", "expanded_atom_site", "appearance", "polyhedra"}},
                {QStringLiteral("experiment/basic"), {"experiments", "background", "instrument", "peak", "excluded_region", "linked_structure"}},
                {QStringLiteral("experiment/extras"), {"background_estimate", "peak", "absorption", "preferred_orientation", "scattering_source", "data", "refln"}},
                {QStringLiteral("analysis/extras"), {"minimizer", "fitting_mode", "alias", "constraint", "fit_parameter", "fit_result", "fit_result_bank", "fit_result_phase"}}};
            for (const auto& [where, groups] : builtin)
                for (const QString& group : groups) inventory.append({where.section(QLatin1Char('/'), 0, 0), where.section(QLatin1Char('/'), 1), "group." + group});
        }
        steps_.push_back({"e58-unfold-00-opened", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"), "wait-settled"}});
        steps_.back().capture = false;
        QString shown;
        int n = 0;
        for (const auto& [page, tab, group] : inventory) {
            if (page + "/" + tab != shown) {
                shown = page + "/" + tab;
                steps_.push_back({QStringLiteral("e58-unfold-%1-to-%2-%3").arg(++n, 3, 10, QLatin1Char('0')).arg(page, tab),
                                  {"appBar.tab." + page, "sideBar.tab." + tab, "wait-settled"}});
                steps_.back().capture = false;
            }
            steps_.push_back({QStringLiteral("e58-unfold-%1-%2-%3").arg(++n, 3, 10, QLatin1Char('0')).arg(page, group), {"unfold:" + group, "wait-settled"}});
            steps_.back().capture = false;
            named("unfold-" + page + "-" + group.mid(6));
            steps_.push_back({QStringLiteral("e58-unfold-%1-fold-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(group), {"fold:" + group, "wait-settled"}});
            steps_.back().capture = false;
        }
    }
    // `e58-stable`: every frame of each page switch (Analysis first) and of every group's unfold on every page, for the
    // joint fit and the cosio example: no table changes its columns, cells or height once shown (T6, T7).
    if (only == QLatin1String("e58-stable")) {
        const QList<std::pair<QString, QStringList>> groups{
            {QStringLiteral("structure/basic"), {"structures", "space_group", "cell", "atom_site", "atom_site_aniso"}},
            {QStringLiteral("structure/extras"), {"scattering_length", "geom", "space_group_symop", "expanded_atom_site"}},
            {QStringLiteral("experiment/basic"), {"experiments", "background", "instrument", "peak", "excluded_region", "linked_structure"}},
            {QStringLiteral("experiment/extras"), {"background_estimate", "absorption", "data", "refln"}},
            {QStringLiteral("analysis/basic"), {"parameters"}},
            {QStringLiteral("analysis/extras"), {"alias", "constraint", "fit_parameter", "fit_result_bank", "fit_result_phase"}}};
        int n = 0;
        for (const QString& project : {QStringLiteral("pd-neut-tof_ncaf-wish"), QStringLiteral("pd-neut-cwl_cosio-d20_2k")}) {
            steps_.push_back({QStringLiteral("e58-stable-%1-open-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(project),
                              {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:" + project, "appBar.tab.home", "wait-settled"}});
            steps_.back().capture = false;
            for (const QString& page : {QStringLiteral("analysis"), QStringLiteral("structure"), QStringLiteral("experiment"), QStringLiteral("project"), QStringLiteral("analysis")}) {
                steps_.push_back({QStringLiteral("e58-stable-%1-page-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(page), {"frames-stable:page:" + page, "wait-settled"}});
                steps_.back().capture = false;
            }
            for (const auto& [where, names] : groups) {
                steps_.push_back({QStringLiteral("e58-stable-%1-to-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(QString(where).replace(QLatin1Char('/'), QLatin1Char('-'))),
                                  {"appBar.tab." + where.section(QLatin1Char('/'), 0, 0), "wait-settled", "wait-settled", "sideBar.tab." + where.section(QLatin1Char('/'), 1), "wait-settled"}});
                steps_.back().capture = false;
                for (const QString& name : names) {
                    steps_.push_back({QStringLiteral("e58-stable-%1-unfold-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(name),
                                      {"fold:group." + name, "wait-settled", "frames-stable:unfold:group." + name, "wait-settled"}});
                    steps_.back().capture = false;
                }
            }
        }
    }
    // `e58-room`: T7's room on every sidebar tab of every page, each group opened alone and after another, in the three
    // projects the owner's cases came from (2026-11-24).
    if (only == QLatin1String("e58-room")) {
        int n = 0;
        for (const QString& project : {QStringLiteral("pd-neut-cwl_cosio-d20_scan-213f"), QStringLiteral("pd-neut-tof_ncaf-wish"), QStringLiteral("pd-neut-cwl_cosio-d20_2k")}) {
            steps_.push_back({QStringLiteral("e58-room-%1-open-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(project),
                              {"preference:loggingLevel=Info", "preference:autoCollapse=false", "resize:1496x900", "open-cli-project:" + project, "wait-settled"}});
            steps_.back().capture = false;
            for (const QString& where : {QStringLiteral("project/basic"), QStringLiteral("structure/basic"), QStringLiteral("structure/extras"), QStringLiteral("experiment/basic"),
                                         QStringLiteral("experiment/extras"), QStringLiteral("analysis/basic"), QStringLiteral("analysis/extras")}) {
                steps_.push_back({QStringLiteral("e58-room-%1-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(QString(where).replace(QLatin1Char('/'), QLatin1Char('-'))),
                                  {"appBar.tab." + where.section(QLatin1Char('/'), 0, 0), "wait-settled", "sideBar.tab." + where.section(QLatin1Char('/'), 1), "wait-settled", "room-tab"}});
                steps_.back().capture = false;
            }
        }
    }
    // `e58-rowheights`: T7 for the lists whose rows can be taller than the table's least row: the Examples list, whole
    // and filtered, the recent projects and an experiment name being edited, at three windows.
    if (only == QLatin1String("e58-rowheights")) {
        int n = 0;
        for (const QString& size : {QStringLiteral("1280x900"), QStringLiteral("1496x900"), QStringLiteral("1920x1080")}) {
            const auto shot = [this, &n, &size](const char* name, const QStringList& actions) {
                steps_.push_back({QStringLiteral("e58-rowheights-%1-%2-%3").arg(++n, 2, 10, QLatin1Char('0')).arg(QLatin1String(name), size), actions + QStringList{"wait-settled", "room-check"}});
            };
            shot("examples", QStringList{"preference:loggingLevel=Info", "preference:autoCollapse=false", "resize:" + size} + start + QStringList{"appBar.tab.project", basic, "wait-settled"});
            shot("examples-lbco", {"examples.search", "type:LBCO"});
            shot("examples-none", {"type:zzz"});
            shot("examples-again", {"examples.clearFilters"});
            shot("recent", QStringList{QStringLiteral("open-cli-project:") + (n < 8 ? "pd-neut-tof_ncaf-wish" : n < 16 ? "pd-neut-cwl_cosio-d20_2k" : "pd-neut-cwl_lbco-hrpt"), "appBar.tab.project", basic, "wait-settled", "expand:group.recentProjects"});
            shot("experiments", QStringList{"appBar.tab.experiment", basic, "wait-settled", "expand:group.experiments"});
            shot("experiments-rename", {"experiments.name.0"});
            steps_.push_back({QStringLiteral("e58-rowheights-%1-closed-%2").arg(++n, 2, 10, QLatin1Char('0')).arg(size), {"key:Escape", "close-project", "wait-settled"}});
            steps_.back().capture = false;
        }
    }
    // `e58-roomshots`: the owner's states of 2026-11-24 as captures, scan-213f's Structure and Experiment tabs, each
    // group alone and after another, and the Analysis table, the only table of its tab.
    if (only == QLatin1String("e58-roomshots")) {
        steps_.push_back({"e58-roomshots-0", {"preference:loggingLevel=Info", "preference:autoCollapse=false", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_scan-213f", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& where : {QStringLiteral("structure/basic"), QStringLiteral("structure/extras"), QStringLiteral("experiment/basic"), QStringLiteral("analysis/basic")})
            steps_.push_back({"e58-roomshots-" + QString(where).replace(QLatin1Char('/'), QLatin1Char('-')),
                              {"appBar.tab." + where.section(QLatin1Char('/'), 0, 0), "wait-settled", "sideBar.tab." + where.section(QLatin1Char('/'), 1), "wait-settled", where.startsWith(QLatin1String("analysis")) ? QStringLiteral("check-layout") : QStringLiteral("room-tab")}});
    }
    // `e58-figures`: the report's figures, each shown: its frame and paddings, and the four border lines of every pane at
    // several scroll positions; then the Pattern tab's panes.
    if (only == QLatin1String("e58-figures")) {
        steps_.push_back({"e58-figures-0-pattern", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.report", "wait-settled", "reveal:report.pattern.0", "wait-settled", "report-frames", "pane-borders", "report-scrolls"}});
        steps_.push_back({"e58-figures-1-structure", {"reveal:report.structure.0", "wait-settled"}});
        steps_.push_back({"e58-figures-2-pattern-tab", {"appBar.tab.experiment", "wait-settled", "pane-borders"}});
        steps_.push_back({"e58-figures-3-single-crystal", {"open-cli-project:sc-neut-cwl_tb2ti2o7-heidi", "appBar.tab.report", "wait-settled", "reveal:report.singleCrystal", "wait-settled", "report-frames", "pane-borders", "report-scrolls"}});
        steps_.push_back({"e58-figures-4-single-crystal-tab", {"appBar.tab.experiment", "wait-settled", "pane-borders"}});
        steps_.push_back({"e58-figures-5-scan", {"open-cli-project:pd-neut-cwl_cosio-d20_scan-3f", "appBar.tab.analysis", "wait-settled", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled"}});
        steps_.back().capture = false;
        // The report's charts are made a slice at a time.
        steps_.push_back({"e58-figures-5-evolution", {"appBar.tab.report", "wait-settled", "wait-settled", "wait-settled", "wait-settled", "wait-settled", "wait-settled", "reveal:report.evolution", "wait-settled", "wait-settled", "report-frames", "pane-borders", "report-scrolls"}});
        steps_.push_back({"e58-figures-6-evolution-tab", {"appBar.tab.analysis", "wait-settled", "mainArea.tab.evolution", "wait-settled", "pane-borders"}});
    }
    // `e58-evolution`: the Evolution toolbar's row against the selector row above it, for three parameters.
    if (only == QLatin1String("e58-evolution")) {
        steps_.push_back({"e58-evolution-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_scan-213f", "appBar.tab.analysis", "wait-settled", "mainArea.tab.evolution", "wait-settled", "evolution-row"}});
        steps_.back().capture = true;
        // The sidebar at the bottom too.
        for (const QString& size : {QStringLiteral("900x1000"), QStringLiteral("700x900")})
            steps_.push_back({"e58-evolution-" + size, {"resize:" + size, "wait-settled", "wait-settled", "evolution-row"}});
    }
    // `e58-scroll`: the parameter table scrolled fast in every width mode, its Free boxes held to their column in every
    // frame (the owner, 2026-11-23).
    if (only == QLatin1String("e58-scroll")) {
        steps_.push_back({"e58-scroll-0", {"preference:loggingLevel=Info", "resize:1496x700", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.analysis", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& width : {QStringLiteral("1280"), QStringLiteral("1496"), QStringLiteral("1920")})
            for (const QString& mode : {QStringLiteral("auto"), QStringLiteral("full"), QStringLiteral("bounds"), QStringLiteral("values"), QStringLiteral("compact")}) {
                steps_.push_back({"e58-scroll-" + mode + "-" + width, {"preference:sideBarWidthMode=" + mode, "resize:" + width + "x700", "wait-settled",
                                                                        "scroll-column-x:parameters.list:parameters.free.", "scroll-column-x:parameters.list:parameters.su."}});
                steps_.back().capture = false;
            }
    }
    // `e58-bottomchart`: the bottom layout's sidebar from page to page, before and after a fit, with one Bragg row and
    // with two, and before one for a scan with three, at five windows; its height moves with the window and the project
    // alone (W7).
    if (only == QLatin1String("e58-bottomchart")) {
        steps_.push_back({"e58-bottomchart-0", {"preference:loggingLevel=Info", "resize:860x1000"}});
        steps_.back().capture = false;
        const QString scanned = QStringLiteral("pd-xray-cwl_latp_scan-4f");
        for (const QString& project : {QStringLiteral("pd-neut-cwl_lbco-hrpt"), QStringLiteral("pd-neut-cwl_cosio-d20_2k"), scanned}) {
            const QString tag = project.section(QLatin1Char('-'), 2, 2);
            steps_.push_back({"e58-bottomchart-" + tag + "-open", {"resize:860x1000", "open-cli-project:" + project, "wait-settled"}});
            for (const QString& when : {QStringLiteral("before"), QStringLiteral("after")}) {
                if (when == QLatin1String("after")) {
                    if (project == scanned) break;
                    steps_.push_back({"e58-bottomchart-" + tag + "-fit", {"resize:860x1000", "appBar.tab.analysis", "wait-settled", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled"}});
                    steps_.back().capture = false;
                }
                for (const QString& size : {QStringLiteral("860x1000"), QStringLiteral("860x800"), QStringLiteral("700x900"), QStringLiteral("860x760"), QStringLiteral("900x1200")})
                    for (const QString& page : {QStringLiteral("project"), QStringLiteral("structure"), QStringLiteral("experiment"), QStringLiteral("analysis"), QStringLiteral("report")})
                        steps_.push_back({"e58-bottomchart-" + tag + "-" + when + "-" + size + "-" + page, {"resize:" + size, "appBar.tab." + page, "wait-settled", "wait-settled", "check-layout"}});
            }
        }
    }
    // `e58-moments`: the magnetic moments table of the cosio example at three windows, the layout check, and a derived
    // cell's popup (|M|: value only in the cell, full value and s.u. in the popup, Free disabled; the owner, 2026-11-23).
    if (only == QLatin1String("e58-moments")) {
        steps_.push_back({"e58-moments-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.structure",
                                            "wait-settled", "fold:group.structures", "fold:group.atom_site", "expand:group.atom_site_moment", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& width : {QStringLiteral("1280"), QStringLiteral("1496"), QStringLiteral("1920")})
            steps_.push_back({"e58-moments-" + width, {"resize:" + width + "x900", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-moments-popup", {"atomSiteMoment.modulus.0", "wait-settled", "check-layout", "check-popup:atomSiteMoment.modulus.0.popup.value"}});
        steps_.push_back({"e58-moments-popup-angle", {"key:Escape", "wait-settled", "atomSiteMoment.angle1.0", "wait-settled", "check-popup:atomSiteMoment.angle1.0.popup.value"}});
        // The spherical form: each value opens the popup, is typed there and committed by Enter.
        steps_.push_back({"e58-moments-spherical", {"key:Escape", "wait-settled", "atomSiteMoments.form", "choose:spherical", "wait-settled", "check-layout"}});
        for (const QString& k : {QStringLiteral("0"), QStringLiteral("1"), QStringLiteral("2")})
            steps_.push_back({"e58-moments-spherical-" + k, {"key:Escape", "wait-settled", "atomSiteMoment.form." + k + ".0", "wait-settled", "check-popup:atomSiteMoment.form." + k + ".0.popup.value"}});
        steps_.push_back({"e58-moments-spherical-typed", {"key:Escape", "wait-settled", "atomSiteMoment.form.0.0", "wait-settled", "key:Ctrl+A", "type:3.5", "key:Return", "wait-settled"}});
        steps_.push_back({"e58-moments-spherical-committed", {"key:Escape", "wait-settled"}});
        steps_.push_back({"e58-moments-fitted", {"appBar.tab.analysis", "wait-settled", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled", "appBar.tab.structure", "wait-settled",
                                                 "atomSiteMoment.form.1.0", "wait-settled", "check-popup:atomSiteMoment.form.1.0.popup.value"}});
    }
    // `e58-names`: every bundled example's Analysis page, its widest parameter name logged (the name budget, W5); the
    // scan and synthetic series, which download their data, are left out.
    if (only == QLatin1String("e58-names")) {
        steps_.push_back({"e58-names-0", {"preference:loggingLevel=Info", "preference:sideBarWidthMode=auto", "resize:1920x1080", "wait-settled",
                                          "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& id : ExampleListModel::bundledIds()) {
            if (id.contains(QLatin1String("scan")) || id.contains(QLatin1String("synthetic"))) continue;
            QStringList open = open_example(id);
            open.insert(2, QStringLiteral("expand:group.examples"));
            // The layout check at the Auto stop: W5's spare and name budget for this example.
            steps_.push_back({"e58-names-" + id, open + QStringList{"wait-settled", "appBar.tab.analysis", "wait-settled", "check-layout"}});
            steps_.back().capture = false;
        }
    }
    // `e58-contract`: the contract's variant states the layout sweep does not reach: the Auto width series (W3, W4), the
    // popup from a field and a cell, the unfold heights (T7).
    if (only == QLatin1String("e58-contract")) {
        steps_.push_back({"e58-contract-0", {"preference:loggingLevel=Info", "preference:sideBarWidthMode=auto", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.analysis", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-contract-typing", {"parameters.nameFilter", "wait-settled", "time-keys:length", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-contract-typed", {"parameters.clearFilters", "wait-settled"}});
        steps_.back().capture = false;
        // Every 40 px, and the switch width and the pixel below it (W3).
        QList<int> seriesWidths{900, kSwitchWidthPx - 1, kSwitchWidthPx};
        for (int width = 940; width <= 2000; width += 40) seriesWidths << width;
        for (const int width : seriesWidths) {
            steps_.push_back({QStringLiteral("e58-contract-series-%1").arg(width), {QStringLiteral("resize:%1x900").arg(width), "wait-settled", "series-point"}});
            steps_.back().capture = false;
        }
        steps_.push_back({"e58-contract-structure", {"resize:1496x1080", "appBar.tab.structure", "wait-settled", "fold:group.structures", "expand:group.cell", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-contract-popup-field", {"cell.length_a", "popup-time:cell.length_a.menu.popup.value", "time-keys:10.2", "key:Escape", "wait-settled"}});
        steps_.push_back({"e58-contract-unfold-adp", {"fold:group.cell", "wait-settled", "unfold-heights:group.atom_site_aniso", "wait-settled"}});
        steps_.push_back({"e58-contract-popup-cell", {"atomSiteAdp.iso.2", "popup-time:atomSiteAdp.iso.2.popup.value", "key:Escape", "wait-settled"}});
        steps_.push_back({"e58-contract-unfold-sites", {"fold:group.atom_site_aniso", "wait-settled", "unfold-heights:group.atom_site", "wait-settled"}});
        // The same field's popup after a fit: as wide as before it.
        steps_.push_back({"e58-contract-fit", {"appBar.tab.analysis", "wait-settled", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled",
                                               "appBar.tab.structure", "wait-settled", "fold:group.atom_site", "expand:group.cell", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-contract-popup-fitted", {"cell.length_a", "popup-time:cell.length_a.menu.popup.value", "key:Escape", "wait-settled"}});
    }
    // `e58-popups`: a click on a field row's field and on a table cell opens the parameter popup, its value focused.
    if (only == QLatin1String("e58-popups")) {
        steps_.push_back({"e58-popups-0", {"preference:loggingLevel=Info", "resize:1496x1080", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.structure", "wait-settled",
                                           "fold:group.structures", "expand:group.cell", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& field : {QStringLiteral("cell.length_a"), QStringLiteral("cell.length_b")})
            steps_.push_back({"e58-popups-" + field, {field, "wait-settled", "check-popup:" + field + ".menu.popup.value", "key:Escape", "wait-settled"}});
        steps_.push_back({"e58-popups-adp", {"fold:group.cell", "expand:group.atom_site_aniso", "wait-settled", "atomSiteAdp.iso.2", "wait-settled",
                                             "check-popup:atomSiteAdp.iso.2.popup.value", "key:Escape", "wait-settled"}});
        steps_.push_back({"e58-popups-experiment", {"appBar.tab.experiment", "wait-settled", "fold:group.experiments", "expand:group.peak", "expand:group.instrument", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& field : {QStringLiteral("instrument.calib_twotheta_offset")})
            steps_.push_back({"e58-popups-" + field, {field, "wait-settled", "check-popup:" + field + ".menu.popup.value", "key:Escape", "wait-settled"}});
    }
    // `e58-columns`: the displacement table's columns hold their widths while a type changes and a value is typed.
    if (only == QLatin1String("e58-columns")) {
        steps_.push_back({"e58-columns-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.structure", "wait-settled",
                                            "expand:group.atom_site_aniso", "wait-settled", "note-columns:atomSiteAdps.list"}});
        // The owner's case 80: the same table at a 1380 px window (the sidebar about 690 px), the whole layout check.
        steps_.push_back({"e58-columns-case80", {"resize:1380x900", "wait-settled", "check-layout", "resize:1496x900", "wait-settled", "note-columns:atomSiteAdps.list"}});
        steps_.push_back({"e58-columns-type", {"atomSiteAdp.type.0", "choose:Uani", "wait-settled", "check-columns:atomSiteAdps.list"}});
        steps_.push_back({"e58-columns-value", {"atomSiteAdp.iso.2", "wait-settled", "type:0.123456", "key:Return", "wait-settled", "check-columns:atomSiteAdps.list"}});
        // T6 also across a page switch and back, a fit, and a load of the same project.
        steps_.push_back({"e58-columns-page", {"appBar.tab.analysis", "wait-settled", "appBar.tab.structure", "wait-settled", "check-columns:atomSiteAdps.list"}});
        steps_.push_back({"e58-columns-fit", {"appBar.tab.analysis", "wait-settled", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled",
                                              "appBar.tab.structure", "wait-settled", "expand:group.atom_site_aniso", "wait-settled", "check-columns:atomSiteAdps.list"}});
        steps_.push_back({"e58-columns-reload", {"open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled", "appBar.tab.structure", "wait-settled",
                                                 "expand:group.atom_site_aniso", "wait-settled", "check-columns:atomSiteAdps.list"}});
    }
    // `e58-assistant`: the assistant panel open over the sidebar, at rest, at the contract's windows, in Auto and Compact.
    if (only == QLatin1String("e58-assistant")) {
        steps_.push_back({"e58-assistant-00", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_lbco-hrpt", "wait-settled", "appBar.tab.structure", "wait-settled", "assistant.toggle", "wait-settled"}});
        int n = 0;
        for (const QString& mode : {QStringLiteral("auto"), QStringLiteral("compact")})
            for (const QString& size : {QStringLiteral("1496x900"), QStringLiteral("1280x768"), QStringLiteral("1024x700")})
                steps_.push_back({QStringLiteral("e58-assistant-%1-%2-%3").arg(++n, 2, 10, QLatin1Char('0')).arg(mode, size),
                                  {"preference:sideBarWidthMode=" + mode, "resize:" + size, "wait-settled", "check-assistant-panel"}});
    }
    // `e58-experimentnames`: the Experiments table with an experiment without data beside one with data, for datablock
    // names of 11, 20 and 24 characters, in Auto and Compact, wide and at the narrowest, the layout check (T10: every name
    // whole, or cut in the middle by an ellipsis, never elsewhere) at each. The mode is in the frame's first word, as W1
    // holds within one mode.
    if (only == QLatin1String("e58-experimentnames")) {
        steps_.push_back({"e58-experimentnames-00-two", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_lbco-hrpt", "appBar.tab.experiment",
                                               "wait-settled", "expand:group.experiments", "experiments.create", "wait-settled"}});
        int n = 0;
        for (const QString& name : {QStringLiteral("experiment1"), QStringLiteral("experiment_high_temp"), QStringLiteral("experiment_high_temp_new")}) {
            steps_.push_back({QStringLiteral("e58-experimentnames-%1-name-%2").arg(++n, 2, 10, QLatin1Char('0')).arg(name.size()),
                              {"reveal:experiments.name.1", "wait-settled", "experiments.name.1", "wait-settled", "key:Ctrl+A", "type:" + name, "key:Return", "wait-settled",
                               "appBar.tab.structure", "wait-settled", "appBar.tab.experiment", "wait-settled", "reveal:experiments.name.1", "wait-settled"}});
            for (const QString& mode : {QStringLiteral("auto"), QStringLiteral("compact")})
                for (const QString& size : {QStringLiteral("1496x900"), QStringLiteral("1280x900"), QStringLiteral("1024x700")})
                    steps_.push_back({QStringLiteral("e58-experimentnames%1-%2-%3-%4").arg(mode).arg(++n, 2, 10, QLatin1Char('0')).arg(name.size()).arg(size),
                                      {"preference:sideBarWidthMode=" + mode, "resize:" + size, "wait-settled", "check-layout"}});
        }
    }
    // `e58-datablocks`: the Experiments table's name, file and value columns in a row never past the table, for a long
    // datablock name in an ordinary project beside an empty experiment, and in a scan.
    if (only == QLatin1String("e58-datablocks")) {
        int n = 0;
        QStringList projects{QStringLiteral("open-cli-project:pd-neut-cwl_lbco-hrpt"), QStringLiteral("open-cli-project:pd-neut-cwl_cosio-d20_scan-213f")};
        // A scan with several extract rules, where one is named.
        if (const QString many = qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"); !many.isEmpty()) projects << "open-project:" + many;
        for (const QString& project : projects) {
            const bool scan = !project.contains(QLatin1String("lbco"));
            QStringList open{"preference:loggingLevel=Info", "preference:sideBarWidthMode=auto", "resize:1496x900", project, "appBar.tab.experiment", "wait-settled", "expand:group.experiments"};
            if (!scan) open << "experiments.create";
            steps_.push_back({QStringLiteral("e58-datablocks-%1-open").arg(++n, 2, 10, QLatin1Char('0')),
                              open + QStringList{"wait-settled", "wait-settled"}});
            steps_.push_back({QStringLiteral("e58-datablocks-%1-named").arg(++n, 2, 10, QLatin1Char('0')),
                              {"resize:1496x920", "wait-settled", scan ? "experiments.name.0" : "experiments.name.1", "wait-settled", "key:Ctrl+A", "type:experiment_high_temp_new", "key:Return", "wait-settled"}});
            for (const QString& mode : {QStringLiteral("auto"), QStringLiteral("compact")})
                for (const QString& size : {QStringLiteral("1496x900"), QStringLiteral("1280x900"), QStringLiteral("1024x700"), QStringLiteral("700x900")})
                    steps_.push_back({QStringLiteral("e58-datablocks-%1-%2-%3-%4").arg(++n, 2, 10, QLatin1Char('0')).arg(scan ? "scan" : "project", mode, size),
                                      {"preference:sideBarWidthMode=" + mode, "resize:" + size, "wait-settled", "check-layout"}});
        }
    }
    // `e58-fields`: the cell and peak profile field rows in Compact and Auto at 1280 and 1496 px, no value cropped.
    if (only == QLatin1String("e58-fields")) {
        steps_.push_back({"e58-fields-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "appBar.tab.analysis", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& mode : {QStringLiteral("compact"), QStringLiteral("auto")})
            for (const QString& width : {QStringLiteral("1280"), QStringLiteral("1496")}) {
                steps_.push_back({"e58-fields-structure-" + mode + "-" + width, {"preference:sideBarWidthMode=" + mode, "resize:" + width + "x900", "appBar.tab.structure", "wait-settled", "unfold:group.cell", "wait-settled", "check-fields"}});
                steps_.push_back({"e58-fields-experiment-" + mode + "-" + width, {"appBar.tab.experiment", "wait-settled", "fold:group.experiments", "expand:group.peak", "wait-settled", "check-fields"}});
            }
    }
    // `e58-case59`: Auto and Full each one width per window size (the owner's case 59, 2026-11-23): at 1280, 1496 and
    // 1920 px the same on Home and Project with no project, on every page with one, and after a fit, to the pixel.
    if (only == QLatin1String("e58-case59")) {
        const QStringList modes{"auto", "full"};
        const QStringList widths{"1280", "1496", "1920"};
        steps_.push_back({"e58-case59-0", {"preference:loggingLevel=Info", "resize:1496x900", "appBar.tab.home", "wait-settled"}});
        steps_.back().capture = false;
        const auto pass = [&](const QString& when, const QStringList& pages, bool first) {
            for (const QString& mode : modes)
                for (const QString& width : widths) {
                    const QString key = mode + "-" + width;
                    QStringList actions{"preference:sideBarWidthMode=" + mode, "resize:" + width + "x900"};
                    for (const QString& page : pages) {
                        actions << "appBar.tab." + page << "wait-settled";
                        actions << ((first && page == pages.first()) ? "note-sidebar:" + key : "check-sidebar:" + key);
                    }
                    steps_.push_back({"e58-case59-" + when + "-" + key, actions});
                }
        };
        pass("no-project", {"home"}, true);
        steps_.push_back({"e58-case59-open", {"resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled"}});
        steps_.back().capture = false;
        const QStringList pages{"home", "project", "structure", "experiment", "analysis", "report"};
        pass("opened", pages, false);
        steps_.push_back({"e58-case59-fit", {"resize:1496x900", "appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled"}});
        steps_.back().capture = false;
        pass("fitted", pages, false);
    }
    // `e58-case50`: the sidebar's width in Full and in Auto at three window widths, on every page, before and after a
    // fit (the owner's case 50, 2026-11-23): Full one width on every page and unmoved by the fit; Auto unmoved by it.
    if (only == QLatin1String("e58-case50")) {
        const QStringList pages{"project", "structure", "experiment", "analysis", "report"};
        const QStringList modes{"full", "auto"};
        const QStringList widths{"1280", "1496", "1920"};
        steps_.push_back({"e58-case50-0", {"preference:loggingLevel=Info", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled"}});
        steps_.back().capture = false;
        const auto pass = [&](const QString& when) {
            for (const QString& mode : modes)
                for (const QString& width : widths) {
                    QStringList actions{"preference:sideBarWidthMode=" + mode, "resize:" + width + "x900"};
                    for (const QString& page : pages) {
                        const QString key = mode + "-" + width + "-" + page;
                        actions << "appBar.tab." + page << "wait-settled";
                        if (when == "before") {
                            actions << "note-sidebar:" + key;
                            // Full: every page as Analysis has it before the fit.
                            if (mode == "full" && page == "analysis") actions << "note-sidebar:full-" + width;
                        } else {
                            actions << "check-sidebar:" + key;
                        }
                        if (mode == "full") actions << "check-sidebar:full-" + width;
                    }
                    steps_.push_back({"e58-case50-" + when + "-" + mode + "-" + width, actions});
                }
        };
        pass("before");
        steps_.push_back({"e58-case50-fit", {"resize:1496x900", "appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled"}});
        steps_.back().capture = false;
        pass("after");
    }
    // `e58-resid`: the residual pane's title as the window gets shorter (the owner, 2026-11-23: "resid" when "meas −
    // calc" does not fit, never smaller or cut).
    if (only == QLatin1String("e58-resid")) {
        steps_.push_back({"e58-resid-0", {"resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled", "appBar.tab.analysis",
                                          "statusBar.fit.button", "wait-fit", "choose:OK", "mainArea.tab.pattern", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& height : {QStringLiteral("900"), QStringLiteral("700"), QStringLiteral("620")})
            steps_.push_back({"e58-resid-" + height, {"resize:1496x" + height, "wait-settled", "check-layout"}});
    }
    // `e58-prefit`: both example projects as opened, before any fit, on the Analysis page at three window widths
    // (the owner's case 47, 2026-11-23: values cut and columns crushed before a fit).
    if (only == QLatin1String("e58-prefit")) {
        steps_.push_back({"e58-prefit-0", {"preference:loggingLevel=Info", "resize:1280x900", "home.start", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& project : {QStringLiteral("pd-neut-cwl_cosio-d20"), QStringLiteral("pd-neut-cwl_cosio-d20_scan")}) {
            steps_.push_back({"e58-prefit-" + project + "-open", {"open-cli-project:" + project, "wait-settled", "appBar.tab.analysis", "wait-settled"}});
            steps_.back().capture = false;
            for (const QString& width : {QStringLiteral("1280"), QStringLiteral("1496"), QStringLiteral("1920")})
                steps_.push_back({"e58-prefit-" + project + "-" + width, {"resize:" + width + "x900", "wait-settled", "check-layout"}});
        }
    }
    if (only == QLatin1String("e58-widths")) {
        const QStringList widths = qEnvironmentVariable("EDI_WIDTHS").split(QLatin1Char(','), Qt::SkipEmptyParts);
        int n = 0;
        steps_.push_back({"e58-widths-0000-open-ncaf", {"preference:loggingLevel=Info", "resize:1280x900",
                                                        "open-cli-project:pd-neut-tof_ncaf-wish", "wait-settled",
                                                        "appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK"}});
        steps_.back().capture = false;
        for (const QString& width : widths)
            steps_.push_back({QStringLiteral("e58-widths-%1-ncaf-analysis-%2").arg(++n, 4, 10, QLatin1Char('0')).arg(width),
                              {"resize:" + width + "x900", "wait-settled", "check-layout"}});
        // A click on a parameter's number opens its popup (ADR-0103 decision 6).
        steps_.push_back({"e58-widths-0450-ncaf-parameter-popup", {"resize:1280x900", "wait-settled", "parameters.value.1", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-widths-0451-ncaf-parameter-popup-closed", {"key:Escape", "wait-settled"}});
        steps_.back().capture = false;
        // The structure renamed to a long name first, while its row is on screen (before every group expands): the
        // charts and the parameter table cut it in its middle at a fixed width (the owner, 2026-11-22).
        steps_.push_back({"e58-widths-0500-open-cosio", {"open-cli-project:pd-neut-cwl_cosio-d20_scan", "wait-settled",
                                                         "appBar.tab.structure", "expand:group.structures", "wait-settled",
                                                         "structures.name.0", "key:Ctrl+A", "type:strujnkjnkjnjcture_with_a_long_name1",
                                                         "key:Return", "wait-settled", "expand-all", "wait-settled",
                                                         // An anisotropic site: its tensor values have more digits (the owner, 2026-11-22).
                                                         "atomSiteAdp.type.0", "choose:Uani", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& width : widths)
            steps_.push_back({QStringLiteral("e58-widths-%1-cosio-structure-%2").arg(++n, 4, 10, QLatin1Char('0')).arg(width),
                              {"resize:" + width + "x900", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-widths-0949-cosio-atom-site-popup", {"resize:1280x900", "wait-settled", "atomSite.fractY.5", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-widths-0949-cosio-atom-site-popup-closed", {"key:Escape", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-widths-0950-cosio-adp-popup", {"resize:1280x900", "wait-settled", "atomSiteAdp.ani11.0", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-widths-0951-cosio-adp-popup-closed", {"key:Escape", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-widths-0961-cosio-long-name-pattern", {"appBar.tab.analysis", "mainArea.tab.pattern", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-widths-0962-cosio-long-name-structure", {"appBar.tab.structure", "mainArea.tab.pattern", "wait-settled", "check-layout"}});
    }
    // `e58-scrollbars`: right after a project opens and once settled, on each page: no scroll bar while the content
    // fits (the owner, 2026-11-22).
    if (only == QLatin1String("e58-scrollbars")) {
        steps_.push_back({"e58-scrollbars-0", {"preference:loggingLevel=Info", "resize:1480x900", "home.start", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-scrollbars-1-opening", {"open-cli-project:pd-neut-cwl_cosio-d20_scan", "appBar.tab.project", "check-layout"}});
        steps_.push_back({"e58-scrollbars-2-opened", {"wait-settled", "check-layout"}});
        for (const QString& page : {QStringLiteral("structure"), QStringLiteral("experiment"), QStringLiteral("analysis"), QStringLiteral("report")}) {
            steps_.push_back({"e58-scrollbars-3-" + page, {"appBar.tab." + page, "check-layout"}});
            steps_.push_back({"e58-scrollbars-4-" + page + "-settled", {"wait-settled", "check-layout"}});
        }
    }
    // `e58-feedback`: typing in the Help and feedback form with a long session's run log (the owner, 2026-11-22: the
    // window froze for about a minute per letter); each keystroke timed.
    // `e58-feedback-hover`: the form with a long session's run log and its preview shown, the pointer resting on each
    // of its controls: which tooltip holds the log (the owner, 2026-11-23: a 1434 x 16692 px shadow layer).
    if (only == QLatin1String("e58-feedback-hover")) {
        steps_.push_back({"e58-feedback-hover-1", {"preference:loggingLevel=Info", "preference:toolTipLevel=All", "resize:1280x800",
                                                   "log-fill:20000", "appBar.tab.home", "wait-settled", "home.feedback", "wait-settled",
                                                   "feedback.text", "type:the form froze", "feedback.preview", "wait-settled", "hover-all:feedback."}});
    }
    // `e58-feedback-sent`: the form's thanks once a message is sent, at two window widths (the owner, 2026-11-23: too
    // wide for one sentence).
    if (only == QLatin1String("e58-feedback-sent")) {
        for (const QString& width : {QStringLiteral("1280"), QStringLiteral("1920")}) {
            steps_.push_back({"e58-feedback-sent-" + width, {"resize:" + width + "x900", "appBar.tab.home", "wait-settled", "home.feedback",
                                                             "wait-settled", "set:feedback.form:lastStatus=201", "wait-settled", "check-layout"}});
            steps_.push_back({"e58-feedback-sent-" + width + "-closed", {"key:Escape", "wait-settled"}});
            steps_.back().capture = false;
        }
    }
    if (only == QLatin1String("e58-feedback")) {
        steps_.push_back({"e58-feedback-1-open", {"preference:loggingLevel=Info", "resize:1280x800", "log-fill:20000", "appBar.tab.home",
                                                  "wait-settled", "home.feedback", "wait-settled", "feedback.text"}});
        steps_.push_back({"e58-feedback-2-typed", {"time-keys:abcdefghijklmnopqrst", "wait-settled"}});
    }
    // `e58-examples`: the Examples list scrolled from its top to its end and back three times, each pass's frame gaps
    // logged (the owner, 2026-11-21: "not smooth when scrolling"; rows kept once made).
    if (only == QLatin1String("e58-examples")) {
        QStringList actions{"resize:1000x900", "home.start", "expand:group.examples", "wait-settled"};
        for (int pass = 0; pass < 6; ++pass) actions << "scroll-frames:examples.list";
        steps_.push_back({"e58-examples-1-scrolled", actions + QStringList{"wait-settled"}});
    }
    // `e58-reads`: the scan files each step reads (edi ADR-0102 rule 6): none with every scan view hidden, then Map's
    // pixel rows, then on a zoom only the rows newly shown, none again once hidden, and none on a return.
    if (only == QLatin1String("e58-reads")) {
        const QString box = QStringLiteral(":0.3,0.3,0.6,0.7");
        steps_.push_back({"e58-reads-1-hidden", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                                                "appBar.tab.analysis", "mainArea.tab.pattern", "wait-settled", "wait-settled",
                                                "wait-settled", "count-scan-reads:open-with-every-scan-view-hidden"}});
        steps_.push_back({"e58-reads-2-map", {"count-scan-reads:before-map", "mainArea.tab.map", "wait-scan:map",
                                             "count-scan-reads:map-shown"}});
        steps_.push_back({"e58-reads-3-zoom", {"drag:scanView.map.pointer" + box, "wait-scan:map", "count-scan-reads:map-zoomed"}});
        steps_.push_back({"e58-reads-4-hidden", {"mainArea.tab.pattern", "wait-settled", "wait-settled", "wait-settled",
                                                "count-scan-reads:map-hidden"}});
        steps_.push_back({"e58-reads-5-back", {"mainArea.tab.map", "wait-scan:map", "count-scan-reads:map-again"}});
    }
    // `e58-side`: the sidebar on Home, Project, Structure and Analysis at windows of 1000 and 930 px (the owner,
    // 2026-11-21: narrow on macOS), the cosio structure's Atom sites shown (its header hid the first row there).
    if (only == QLatin1String("e58-side")) {
        const QString project = qEnvironmentVariable("EDI_DEMO_ATOMS_CLI", QStringLiteral("pd-neut-cwl_cosio-d20_scan-3f"));
        steps_.push_back({"e58-side-0-open", {"preference:loggingLevel=Info", "resize:1000x620", "open-cli-project:" + project}});
        for (const QString& width : {QStringLiteral("1000"), QStringLiteral("930")}) {
            const QString size = "resize:" + width + "x620";
            steps_.push_back({"e58-side-" + width + "-1-home", {size, "appBar.tab.home", "wait-settled"}});
            steps_.push_back({"e58-side-" + width + "-2-project", {"appBar.tab.project", "wait-settled"}});
            steps_.push_back({"e58-side-" + width + "-3-structure", {"appBar.tab.structure", "expand:group.atom_site",
                                                                       "wait-settled", "reveal:group.atom_site"}});
            steps_.push_back({"e58-side-" + width + "-4-analysis", {"appBar.tab.analysis", "wait-settled"}});
        }
    }
    // `e58-bottom`: the Experiment page's tabs in the bottom-sidebar layout, where Stacked showed the Pattern chart.
    if (only == QLatin1String("e58-bottom")) {
        steps_.push_back({"e58-bottom-1", {"resize:700x900", "open-cli-project:pd-neut-cwl_cosio-d20_scan-3f", "appBar.tab.experiment", "wait-settled", "check-layout"}});
        // The Analysis sidebar below at two portrait sizes (the owner, 2026-11-23: no name filter, the reset in the
        // pickers' row, about half the height).
        steps_.push_back({"e58-bottom-1b-analysis-700", {"appBar.tab.analysis", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-bottom-1c-analysis-600", {"resize:600x1000", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-bottom-1d-back", {"resize:700x900", "appBar.tab.experiment", "wait-settled"}});
        steps_.back().capture = false;
        steps_.push_back({"e58-bottom-2-stacked", {"mainArea.tab.stacked", "wait-settled"}});
        steps_.push_back({"e58-bottom-3-meascalc", {"mainArea.tab.measCalc", "wait-settled"}});
        steps_.push_back({"e58-bottom-4-map", {"mainArea.tab.map", "wait-settled"}});
    }
    // `e58-zoom`: a box zoom on Meas vs calc, Stacked and Map, each taken partway (120 ms of the 250 ms move) and
    // settled: every chart moves to a zoom as the Pattern chart does (the owner, 2026-11-21).
    if (only == QLatin1String("e58-zoom")) {
        const QString box = QStringLiteral(":0.3,0.3,0.6,0.7");
        steps_.push_back({"e58-zoom-0-meascalc", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_FIT_PROJECT"),
                                                  "appBar.tab.analysis", "mainArea.tab.measCalc", "wait-settled"}});
        steps_.push_back({"e58-zoom-1-meascalc-mid", {"drag:measCalc.pointer" + box, "capture-at:120"}});
        steps_.push_back({"e58-zoom-2-meascalc-end", {"wait-settled"}});
        steps_.push_back({"e58-zoom-3-stacked", {"open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                                                 "appBar.tab.analysis", "mainArea.tab.stacked", "wait-scan:stacked"}});
        steps_.push_back({"e58-zoom-4-stacked-mid", {"drag:scanView.stacked.pointer" + box, "capture-at:120"}});
        steps_.push_back({"e58-zoom-5-stacked-end", {"wait-scan:stacked"}});
        steps_.push_back({"e58-zoom-6-map", {"mainArea.tab.map", "wait-scan:map"}});
        steps_.push_back({"e58-zoom-7-map-mid", {"drag:scanView.map.pointer" + box, "capture-at:120"}});
        steps_.push_back({"e58-zoom-8-map-end", {"wait-scan:map"}});
    }
    // `e58-states`: the contract's states the sweep does not reach (ADR-0103 "The states"): the 2k example after a fit
    // and then with a 24-character structure name, and the time-of-flight joint fit after its fit at the bottom windows
    // (the sweep fits it at the side only), each in every width mode and window, the layout check on four pages. The
    // frames are named as the sweep's, so the report reads their state from the name.
    if (only == QLatin1String("e58-states")) {
        const QStringList modes{"auto", "full", "bounds", "values", "compact"};
        const QStringList side{"1280x800", "1496x900", "1920x1080"}, bottom{"900x1000", "700x900"};
        const QStringList pages{"structure", "experiment", "analysis", "report"};
        int n = 0;
        const auto pass = [&](const QString& state, const QStringList& sizes) {
            for (const QString& mode : modes)
                for (const QString& size : sizes)
                    for (const QString& page : pages) {
                        steps_.push_back({QStringLiteral("e58-states-%1-%2-%3-%4-%5").arg(++n, 4, 10, QLatin1Char('0')).arg(state, mode, size, page),
                                          {"preference:sideBarWidthMode=" + mode, "resize:" + size, "appBar.tab." + page, "wait-settled", "expand-all", "wait-settled", "check-layout"}});
                        steps_.back().capture = false;
                    }
        };
        const QStringList fit{"appBar.tab.analysis", "wait-settled", "statusBar.fit.button", "wait-fit", "choose:OK", "wait-settled"};
        steps_.push_back({"e58-states-0000-open", QStringList{"preference:loggingLevel=Info", "preference:autoCollapse=false", "preference:patternLegendShown=true",
                                                              "preference:sideBarWidthMode=auto", "resize:1496x900", "open-cli-project:pd-neut-cwl_cosio-d20_2k", "wait-settled"} + fit});
        steps_.back().capture = false;
        pass("cosio-d20_2k+fitted", side + bottom);
        steps_.push_back({"e58-states-0000-renamed", {"preference:sideBarWidthMode=auto", "resize:1496x900", "appBar.tab.structure", "wait-settled", "expand:group.structures",
                                                      "structures.name.0", "key:Ctrl+A", "type:cosio_structure_renamed1", "key:Return", "wait-settled"}});
        steps_.back().capture = false;
        pass("cosio-d20_2k+name24", side + bottom);
        steps_.push_back({"e58-states-0000-tof", QStringList{"preference:sideBarWidthMode=auto", "resize:1496x900", "open-cli-project:pd-neut-tof_ncaf-wish", "wait-settled"} + fit});
        steps_.back().capture = false;
        pass("ncaf-wish+fitted", bottom);
    }
    // `e58-sweep`: every page, main-view tab and sidebar tab (its groups open) of each CLI project EDI_SWEEP_PROJECTS
    // names, at each window size EDI_SWEEP_SIZES names, every frame checked by check-layout (the owner, 2026-11-21: a
    // sweep inspected before the owner sees it). A check, not a test gate and not the documentation capture.
    if (only == QLatin1String("e58-sweep")) {
        const QJsonObject pages = QJsonDocument::fromJson(qgetenv("EDI_UI_TAB_INVENTORY")).object();
        const QStringList projects = qEnvironmentVariable("EDI_SWEEP_PROJECTS").split(QLatin1Char(','), Qt::SkipEmptyParts);
        const QStringList sizes = qEnvironmentVariable("EDI_SWEEP_SIZES").split(QLatin1Char(','), Qt::SkipEmptyParts);
        int n = 0;
        // Before any project: the Project page's Get started and Examples, the list at its top and at its end, at every
        // size (the owner, 2026-11-22: rows whose tags wrap overlapped, and no frame showed the list).
        for (const QString& size : sizes) {
            // Not skip_unavailable: that test looks for the first action as a control, which a resize is not.
            const auto shot = [&](const QString& name, const QStringList& actions) {
                steps_.push_back({QStringLiteral("e58-sweep-%1-noproject-%2-%3").arg(++n, 4, 10, QLatin1Char('0')).arg(size, name),
                                  actions + QStringList{"wait-settled", "check-layout"}});
            };
            // Home's Start once; later sizes are already on the Project page, the list taken back to its top.
            QStringList top = n == 0 ? QStringList{"home.start"} : QStringList{};
            top << "resize:" + size << "wait-settled" << "expand:group.examples" << "wait-settled"
                << "list-top:examples.list" << "wait-settled";
            shot("examples-top", top);
            shot("examples-end", {"list-end:examples.list", "wait-settled"});
            shot("get-started", {"expand:group.getStarted", "wait-settled"});
        }
        for (const QString& project : projects) {
            // Opened once: a CLI project's copy is made once per run.
            steps_.push_back({QStringLiteral("e58-sweep-%1-%2-open").arg(++n, 4, 10, QLatin1Char('0')).arg(project),
                              // Every group stays open as the next opens, so expand-all shows every table of a tab.
                              {"preference:loggingLevel=Info", "preference:autoCollapse=false", "open-cli-project:" + project, "wait-settled",
                               "check-messages"}});
            steps_.back().capture = false;
            // Every width the sidebar's button offers (the owner, 2026-11-22), Manual at a dragged width.
            const QStringList modes = qEnvironmentVariable("EDI_SWEEP_MODES", QStringLiteral("auto,full,bounds,values,compact,manual"))
                                          .split(QLatin1Char(','), Qt::SkipEmptyParts);
            for (const QString& mode : modes) {
            steps_.push_back({QStringLiteral("e58-sweep-%1-%2-mode-%3").arg(++n, 4, 10, QLatin1Char('0')).arg(project, mode),
                              {"preference:sideBarManualWidth=600", "preference:sideBarWidthMode=" + mode, "wait-settled"}});
            steps_.back().capture = false;
            for (const QString& size : sizes) {
                // The project's whole name after its kind, so the 2k example and the scan of the same sample are two
                // states of the report's matrix.
                const QString key = project.section(QLatin1Char('_'), 1, -1) + "-" + mode + "-" + size;
                steps_.push_back({QStringLiteral("e58-sweep-%1-%2-resize").arg(++n, 4, 10, QLatin1Char('0')).arg(key),
                                  {"resize:" + size, "wait-settled"}});
                steps_.back().capture = false;
                for (const QString& page : {QStringLiteral("home"), QStringLiteral("project"), QStringLiteral("structure"),
                                            QStringLiteral("experiment"), QStringLiteral("analysis"), QStringLiteral("report")}) {
                    const QJsonObject tabs = pages.value(page).toObject();
                    const QJsonArray main = tabs.value("main").toArray(), side = tabs.value("sidebar").toArray();
                    const auto frame = [&](const QString& name, const QStringList& actions) {
                        const QString image = QStringLiteral("e58-sweep-%1-%2-%3").arg(++n, 4, 10, QLatin1Char('0')).arg(key, name);
                        steps_.push_back({image, actions + QStringList{"expand-all", "wait-settled", "check-layout"}});
                        steps_.back().skip_unavailable = true;
                    };
                    frame(page, main.isEmpty() ? QStringList{"appBar.tab." + page}
                                               : QStringList{"appBar.tab." + page, "wait-settled", "wait-settled",
                                                             "main-tab-index:" + page + ":0", "wait-settled", "main-tab-index:" + page + ":0"});
                    // The width button's menu open, once per size (it is the same menu in every mode).
                    if (page == QLatin1String("analysis") && mode == modes.first()) {
                        const QString image = QStringLiteral("e58-sweep-%1-%2-width-menu").arg(++n, 4, 10, QLatin1Char('0')).arg(key);
                        steps_.push_back({image, {"sideBar.width", "wait-settled", "check-layout"}});
                        steps_.back().skip_unavailable = true;
                        steps_.push_back({image + "-closed", {"key:Escape", "wait-settled"}});
                        steps_.back().capture = false;
                    }
                    // EDI_SWEEP_SHORT: each page on its first main and sidebar tab only, for a quick look.
                    const bool brief = qEnvironmentVariableIsSet("EDI_SWEEP_SHORT");
                    // EDI_SWEEP_TABLES: the sidebar's tabs only, where every table is; the main view's tabs hold charts.
                    const bool tablesOnly = qEnvironmentVariableIsSet("EDI_SWEEP_TABLES");
                    for (qsizetype m = 1; !brief && !tablesOnly && m < main.size(); ++m)
                        frame(page + "-main-" + main[m].toObject().value("key").toString(), {main[m].toObject().value("object").toString()});
                    // Back to the first tab, unless the tab bar has scrolled it out of view (a finding the frames show).
                    if (main.size() > 1) {
                        steps_.push_back({QStringLiteral("e58-sweep-%1-%2-%3-back").arg(++n, 4, 10, QLatin1Char('0')).arg(key, page),
                                          {main[0].toObject().value("object").toString()}, {}, {}, {}, {}, false});
                        steps_.back().skip_unavailable = true;
                    }
                    for (qsizetype t = 1; !brief && t < side.size(); ++t)
                        frame(page + "-side-" + side[t].toObject().value("key").toString(), {side[t].toObject().value("object").toString()});
                    if (side.size() > 1) {
                        steps_.push_back({QStringLiteral("e58-sweep-%1-%2-%3-side-back").arg(++n, 4, 10, QLatin1Char('0')).arg(key, page),
                                          {side[0].toObject().value("object").toString()}, {}, {}, {}, {}, false});
                        steps_.back().skip_unavailable = true;
                    }
                }
            }
            }
            steps_.push_back({QStringLiteral("e58-sweep-%1-%2-mode-auto").arg(++n, 4, 10, QLatin1Char('0')).arg(project),
                              {"preference:sideBarWidthMode=auto", "wait-settled"}});
            steps_.back().capture = false;
            // A joint fit's Analysis page after the fit, where Start, s.u. and Change show, at the widths where the
            // sidebar takes its full width (the owner, 2026-11-22). Not the scan: its
            // sequential fit is too long for a sweep.
            if (project.contains(QLatin1String("ncaf"))) {
                steps_.push_back({QStringLiteral("e58-sweep-%1-%2-fit").arg(++n, 4, 10, QLatin1Char('0')).arg(project),
                                  {"appBar.tab.analysis", "statusBar.fit.button", "wait-fit", "choose:OK"}});
                steps_.back().capture = false;
                steps_.back().skip_unavailable = true;
                for (const QString& mode : modes) {
                    for (const QString& size : sizes) {
                        if (size.section(QLatin1Char('x'), 0, 0).toInt() < 1020) continue;
                        const QString key = project.section(QLatin1Char('_'), 1, -1) + "-" + mode + "-" + size;
                        steps_.push_back({QStringLiteral("e58-sweep-%1-%2-analysis-fitted").arg(++n, 4, 10, QLatin1Char('0')).arg(key),
                                          {"preference:sideBarWidthMode=" + mode, "appBar.tab.analysis", "resize:" + size, "wait-settled",
                                           "check-layout"}});
                        // The Extra tab after the fit: its start values and results exist only then.
                        steps_.push_back({QStringLiteral("e58-sweep-%1-%2-analysis-fitted-extras").arg(++n, 4, 10, QLatin1Char('0')).arg(key),
                                          {"sideBar.tab.extras", "wait-settled", "expand-all", "wait-settled", "check-layout"}});
                        steps_.back().skip_unavailable = true;
                        steps_.push_back({QStringLiteral("e58-sweep-%1-%2-analysis-fitted-main").arg(++n, 4, 10, QLatin1Char('0')).arg(key),
                                          {"sideBar.tab.basic"}, {}, {}, {}, {}, false});
                        steps_.back().skip_unavailable = true;
                    }
                }
                // The rows with the longest numbers (the time-of-flight calibration), filtered into view at 1280: how
                // a value too long for its column is written (the owner, 2026-11-22). Last, so the filter stays.
                steps_.push_back({QStringLiteral("e58-sweep-%1-%2-1280x800-analysis-fitted-calibration").arg(++n, 4, 10, QLatin1Char('0')).arg(project),
                                  {"preference:sideBarWidthMode=auto", "appBar.tab.analysis", "resize:1280x800", "wait-settled",
                                   "parameters.nameFilter", "type:calib_d_to_tof", "wait-settled", "check-layout"}});
            }
        }
    }
    // The sweep's end: the project closed, and the Project page before any project in each width mode, which keeps the
    // width it gives with a project (the owner, 2026-11-22).
    if (only == QLatin1String("e58-sweep")) {
        const QStringList modes = qEnvironmentVariable("EDI_SWEEP_MODES", QStringLiteral("auto,full,bounds,values,compact,manual"))
                                      .split(QLatin1Char(','), Qt::SkipEmptyParts);
        int m = 9000;
        steps_.push_back({"e58-sweep-8999-close-project", {"close-project", "wait-settled", "resize:1280x800", "wait-settled"}});
        steps_.back().capture = false;
        for (const QString& mode : modes)
            steps_.push_back({QStringLiteral("e58-sweep-%1-noproject-%2-1280x800").arg(++m).arg(mode),
                              {"preference:sideBarWidthMode=" + mode, "appBar.tab.home", "wait-settled", "home.start", "wait-settled", "check-layout"}});
        steps_.push_back({"e58-sweep-9099-mode-auto", {"preference:sideBarWidthMode=auto", "wait-settled"}});
        steps_.back().capture = false;
    }
    // `e58-tabs`: every page, then each of its main and sidebar tabs, as EDI_UI_TAB_INVENTORY declares them (the pages in
    // the app bar's order, each page's tabs in declaration order), with the scan EDI_DEMO_SCAN_PROJECT open.
    if (only.startsWith(QLatin1String("e58-tabs"))) {
        steps_.push_back({"e58-tabs-000-opened", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT")}});
        const QJsonObject pages = QJsonDocument::fromJson(qgetenv("EDI_UI_TAB_INVENTORY")).object();
        int n = 0;
        const auto add = [&](const QString& name, const QString& object) {
            // Captured a set time after the click: a view that keeps drawing while it loads (Map on a long scan) never
            // settles, and the trace, not the image, is what this scenario measures.
            steps_.push_back({QStringLiteral("e58-tabs-%1-%2").arg(++n, 3, 10, QLatin1Char('0')).arg(name), {object, "capture-now"}});
            named(name);
            steps_.back().skip_unavailable = true;
        };
        for (const QString& page : {QStringLiteral("home"), QStringLiteral("project"), QStringLiteral("structure"),
                                    QStringLiteral("experiment"), QStringLiteral("analysis"), QStringLiteral("report")}) {
            if (!pages.contains(page)) continue;
            add("page-" + page, "appBar.tab." + page);
            for (const char* area : {"main", "sidebar"}) {
                for (const auto& tab : pages.value(page).toObject().value(QString::fromLatin1(area)).toArray()) {
                    add(QStringLiteral("tab-%1-%2-%3").arg(QString::fromLatin1(area), page, tab.toObject().value("key").toString()),
                        tab.toObject().value("object").toString());
                }
            }
        }
    }
    if (only.startsWith(QLatin1String("e58-banks"))) {
        const QString banks = copy_cli_project(QStringLiteral("pd-neut-tof_ncaf-wish-5bank_start-5"), QDir(loaded_files_.path()));
        steps_.push_back({"e58-banks-00-opened", {"resize:1480x800", "open-project:" + banks, "appBar.tab.experiment"}});
        int n = 0;
        for (const QString& page : {QStringLiteral("experiment"), QStringLiteral("analysis")}) {
            for (const QString& direction : {QStringLiteral("next"), QStringLiteral("previous")}) {
                if (page == QLatin1String("analysis") && direction == QLatin1String("next"))
                    steps_.push_back({QStringLiteral("e58-banks-%1-to-analysis").arg(++n, 2, 10, QLatin1Char('0')), {"appBar.tab.analysis"}});
                for (int i = 0; i < 4; ++i) {
                    steps_.push_back({QStringLiteral("e58-banks-%1-%2-%3-%4").arg(++n, 2, 10, QLatin1Char('0')).arg(page, direction).arg(i),
                                      {direction == QLatin1String("next") ? "mainArea.blocks.down" : "mainArea.blocks.up"}});
                    named(QStringLiteral("%1-%2-%3").arg(page, direction).arg(i));
                }
            }
        }
    }
    if (only.startsWith(QLatin1String("e58-pattern"))) {
        steps_.push_back({"e58-pattern-00-opened", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                                                    "appBar.tab.experiment", "mainArea.tab.pattern"}});
        int n = 0;
        for (const QString& page : {QStringLiteral("experiment"), QStringLiteral("analysis")}) {
            for (const QString& direction : {QStringLiteral("next"), QStringLiteral("previous")}) {
                const bool next = direction == QLatin1String("next");
                if (page == QLatin1String("analysis") && next)
                    steps_.push_back({QStringLiteral("e58-pattern-%1-to-analysis").arg(++n, 2, 10, QLatin1Char('0')),
                                      {"appBar.tab.analysis", "mainArea.tab.pattern"}});
                // Ten presses on a 100 ms schedule (run_step), each without a capture or a wait.
                for (int i = 0; i < 10; ++i) {
                    steps_.push_back({QStringLiteral("e58-pattern-%1-%2-%3-%4").arg(++n, 2, 10, QLatin1Char('0')).arg(page, direction).arg(i),
                                      {next ? "mainArea.blocks.down" : "mainArea.blocks.up"}});
                    steps_.back().capture = false;
                    named(QStringLiteral("%1-%2-%3").arg(page, direction).arg(i), next ? 1 : -1);
                }
                steps_.push_back({QStringLiteral("e58-pattern-%1-%2-%3-settled").arg(++n, 2, 10, QLatin1Char('0')).arg(page, direction), {"wait-settled"}});
            }
        }
    }
    if (only.startsWith(QLatin1String("e58-series"))) {
        steps_.push_back({"e58-series-0-opened", {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                                                  analysis, basic, "mainArea.tab.pattern"}});
        steps_.push_back({"e58-series-1-fit-start", {"statusBar.fit.button", "capture-now"}});
        named(QStringLiteral("fit-start"));
        steps_.push_back({"e58-series-2-fit-running", {"wait-files:50", "capture-now"}});
        named(QStringLiteral("fit-running"));
        steps_.push_back({"e58-series-3-fit-ended", {"wait-fit"}});
        named(QStringLiteral("fit-ended"));
        steps_.push_back({"e58-series-4-end-settled", {"wait-settled"}});
        named(QStringLiteral("end-settled"));
    }
    if (only.startsWith(QLatin1String("stall-"))) {
        steps_.push_back({"stall-1-opened",
                          {"resize:1480x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT"),
                           "appBar.tab.experiment", basic}});
        steps_.push_back({"stall-2-stacked", {"mainArea.tab.stacked"}});
        steps_.push_back({"stall-3-map", {"mainArea.tab.map"}});
        steps_.push_back({"stall-4-fitting", {analysis, basic, "mainArea.tab.stacked", "statusBar.fit.button",
                                              "wait-files:30", "capture-now"}});
        steps_.push_back({"stall-5-fitting-map", {"mainArea.tab.map", "wait-files:65", "capture-now"}});
        steps_.push_back({"stall-6-fitted", {"mainArea.tab.evolution", "wait-files:100", "wait-fit"}});
    }
    if (only.startsWith(QLatin1String("scan-open-"))) {
        steps_.push_back({"scan-open-1-opened",
                          {"resize:1280x800", "open-project:" + qEnvironmentVariable("EDI_DEMO_SCAN_PROJECT")}});
        steps_.push_back({"scan-open-2-structure", {"appBar.tab.structure", basic}});
        steps_.push_back({"scan-open-3-experiment", {"appBar.tab.experiment", basic}});
        steps_.push_back({"scan-open-4-analysis", {analysis, basic}});
        steps_.push_back({"scan-open-5-fitting", {"statusBar.fit.button", "wait-files:5", "capture-now"}});
        steps_.push_back({"scan-open-6-stopped", {"statusBar.fit.button", "wait-fit"}});
        steps_.push_back({"scan-open-7-reset", {"statusBar.fit.reset"}});
        steps_.push_back({"scan-open-8-sequential",
                          {QStringLiteral("sideBar.tab.extras"), "expand:group.fitting_mode", "reveal:fittingMode.type", "fittingMode.type",
                           "choose:Sequential: each from the previous"}});
    }
    // The whole 213-file magnetic scan fitted from its first file, then its Evolution tab: the moments vanish near
    // 54 K, where a converged frame carries an undefined s.u. Run only when asked (`--demo-only scan213-`).
    if (only.startsWith(QLatin1String("scan213-"))) {
        steps_.push_back({"scan213-1-fitted",
                          QStringList{"resize:1280x960", "theme:light"} + start
                              + open_cli_project("pd-neut-cwl_cosio-d20_scan-213f")
                              + QStringList{analysis, basic, "statusBar.fit.button", "wait-fit", "choose:OK",
                                            "mainArea.tab.evolution"}});
    }
    // The parametric fit's Shared column on the 213-file scan: the fitting mode selector open, Parametric chosen, U, V
    // and W shared, the whole table, then saved and opened again. Run only when asked (`--demo-only parametric-`).
    if (only.startsWith(QLatin1String("parametric-"))) {
        steps_.push_back({"parametric-1-selector",
                          QStringList{"resize:1480x900", "theme:light"} + start
                              + open_cli_project("pd-neut-cwl_cosio-d20_scan-213f")
                              + QStringList{analysis, extras, "expand:group.fitting_mode", "reveal:fittingMode.type",
                                            "fittingMode.type"}});
        steps_.push_back({"parametric-2-chosen", {"choose:Parametric: all as one fit", basic}});
        steps_.push_back({"parametric-3-uvw-shared", {"parameters.nameFilter", "type:broad_gauss", "parameters.shared.0",
                                                      "parameters.shared.1", "parameters.shared.2"}});
        steps_.push_back({"parametric-4-table", {"parameters.nameFilter", "key:Ctrl+A", "key:Backspace"}});
        steps_.push_back({"parametric-5-reopened", {"save-as:parametric", "open-project:parametric", analysis, basic,
                                                    "parameters.nameFilter", "type:broad_gauss"}});
        steps_.push_back({"parametric-6-free-menu", {"parameters.nameFilter", "key:Ctrl+A", "key:Backspace",
                                                     "parameters.freeHeader"}});
        steps_.push_back({"parametric-7-shared-menu", {"key:Escape", "parameters.sharedHeader"}});
    }
    // A Parametric fit's views after it ends: the selected pattern with its calculated curve, Meas vs calc, Evolution
    // and the results window with one outcome, on the three-file scan with U, V and W shared. Run only when asked
    // (`--demo-only parametricfit-`).
    if (only.startsWith(QLatin1String("parametricfit-"))) {
        steps_.push_back({"parametricfit-1-ready",
                          QStringList{"resize:1480x900", "theme:light"} + start
                              + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                              + QStringList{analysis, extras, "expand:group.fitting_mode", "reveal:fittingMode.type",
                                            "fittingMode.type", "choose:Parametric: all as one fit", basic,
                                            "parameters.nameFilter", "type:broad_gauss", "parameters.shared.0",
                                            "parameters.shared.1", "parameters.shared.2", "parameters.nameFilter",
                                            "key:Ctrl+A", "key:Backspace"}});
        steps_.push_back({"parametricfit-2-pattern", {"statusBar.fit.button", "wait-fit", "choose:OK",
                                                      "mainArea.tab.pattern"}});
        steps_.push_back({"parametricfit-3-meas-calc", {"mainArea.tab.measCalc"}});
        steps_.push_back({"parametricfit-4-evolution", {"mainArea.tab.evolution"}});
        steps_.push_back({"parametricfit-5-results", {"statusBar.fit.outcome"}});
    }
    // A running fit's every Analysis chart tab at two iterations after the first, then its status bar and results
    // window: the 213-pattern Parametric example with U, V and W shared (`parametriclive-`) and the taurine in Joint
    // mode with x11, x22 and x33 shared (`jointlive-`, EDI_DEMO_JOINT_PROJECT). Run only when asked.
    if (only.startsWith(QLatin1String("parametriclive-")) || only.startsWith(QLatin1String("jointlive-"))) {
        const QStringList tabs{"structure", "pattern", "measCalc", "correlations", "stacked", "map", "evolution"};
        const auto every_tab = [this, &tabs](const QString& prefix, int iteration, QStringList first) {
            first << QStringLiteral("wait-iteration:%1").arg(iteration);
            for (const QString& tab : tabs) {
                first << "if-enabled:mainArea.tab." + tab << "capture-now";
                steps_.push_back({QStringLiteral("%1-it%2-%3").arg(prefix).arg(iteration).arg(tab), first});
                first.clear();
            }
        };
        const bool parametric = only.startsWith(QLatin1String("parametriclive-"));
        const QString prefix = parametric ? QStringLiteral("parametriclive") : QStringLiteral("jointlive");
        const QStringList opened = parametric
            ? QStringList{"resize:1920x1080", "theme:light"} + start + open_cli_project("pd-neut-cwl_cosio-d20_parametric") +
                  QStringList{"wait-settled", analysis}
            : QStringList{"resize:1920x1080", "theme:light"} + start +
                  QStringList{"open-project:" + qEnvironmentVariable("EDI_DEMO_JOINT_PROJECT"), "wait-settled", analysis};
        every_tab(prefix, 2, opened + QStringList{"statusBar.fit.button"});
        every_tab(prefix, 3, {});
        steps_.push_back({prefix + "-ended-status", {"wait-fit", "key:Escape", "mainArea.tab.pattern"}});
        steps_.push_back({prefix + "-ended-results", {"statusBar.fit.outcome"}});
    }
    // The sidebar's Auto and Full widths with the Shared column: the joint taurine and the
    // parametric CoSiO example, every column of the Parameters table shown, Change included. Run only when asked
    // (`--demo-only sidebarshared-`).
    if (only.startsWith(QLatin1String("sidebarshared-"))) {
        steps_.push_back({"sidebarshared-1-joint-auto",
                          QStringList{"resize:1920x1080", "theme:light"} + start
                              + QStringList{"open-project:" + qEnvironmentVariable("EDI_DEMO_JOINT_PROJECT"), analysis,
                                            basic, "sideBar.width", "sideBar.width.auto"}});
        steps_.push_back({"sidebarshared-2-joint-full", {"sideBar.width", "sideBar.width.full"}});
        steps_.push_back({"sidebarshared-3-parametric-full",
                          open_cli_project("pd-neut-cwl_cosio-d20_parametric") + QStringList{"wait-settled", analysis, basic}});
        steps_.push_back({"sidebarshared-4-parametric-auto", {"sideBar.width", "sideBar.width.auto"}});
    }
    // The Evolution additions on a series of joint fits, EDI_DEMO_WISH_PROJECT (a bank parameter tied the same for all
    // banks): the fit, the Shared section listing the tied parameter, and every bank's curves. Run only when asked
    // (`--demo-only evolutionshared-`).
    if (only.startsWith(QLatin1String("evolutionshared-"))) {
        steps_.push_back({"evolutionshared-2-fitted",
                          QStringList{"resize:1480x900", "theme:light"} + start
                              + QStringList{"open-project:" + qEnvironmentVariable("EDI_DEMO_WISH_PROJECT"), analysis,
                                            basic, "statusBar.fit.button", "wait-fit", "choose:OK",
                                            "mainArea.tab.evolution"}});
        steps_.push_back({"evolutionshared-3-shared-list", {"evolution.parameters"}});
        steps_.push_back({"evolutionshared-5-per-bank", {"key:Escape", "evolution.toolbar.scope", "choose:Per experiment"}});
    }
    // Shared in the bundled taurine joint fit: a structure parameter cannot be shared (one value for all experiments
    // already); then, in EDI_DEMO_TIED_PROJECT (the example as it was, its copies tied by constraints), Shared is
    // disabled on every copy and names the constraint. Run only when asked (`--demo-only jointtied-`).
    if (only.startsWith(QLatin1String("jointtied-"))) {
        steps_.push_back({"jointtied-1-structure",
                          QStringList{"resize:1480x900", "theme:light"} + start
                              + open_cli_project("sc-neut-tof_taurine-senju")
                              + QStringList{analysis, basic, "parameters.nameFilter", "type:adp_11"}});
        steps_.push_back({"jointtied-2-tied-before", {"open-project:" + qEnvironmentVariable("EDI_DEMO_TIED_PROJECT"), analysis,
                                                      basic, "parameters.nameFilter", "type:coefficient_11"}});
    }
    // Shared in a joint fit: the project EDI_DEMO_JOINT_PROJECT names (the taurine example with its extinction shared
    // instead of tied by constraints), its coefficients, one Free flag per shared group, the Shared menu, then saved and
    // opened again. Run only when asked (`--demo-only jointshared-`).
    if (only.startsWith(QLatin1String("jointshared-"))) {
        steps_.push_back({"jointshared-1-opened",
                          QStringList{"resize:1480x900", "theme:light"} + start
                              + QStringList{"open-project:" + qEnvironmentVariable("EDI_DEMO_JOINT_PROJECT"), analysis,
                                            basic, "parameters.nameFilter", "type:coefficient"}});
        steps_.push_back({"jointshared-2-free-group", {"parameters.free.7"}});
        steps_.push_back({"jointshared-3-unshared", {"parameters.free.7", "parameters.shared.2"}});
        steps_.push_back({"jointshared-4-menu", {"parameters.sharedHeader"}});
        steps_.push_back({"jointshared-5-reopened", {"key:Escape", "parameters.shared.2", "save-as:jointshared",
                                                     "open-project:jointshared", analysis, basic,
                                                     "parameters.nameFilter", "type:coefficient"}});
    }
    // The Shared column and the parameter colours: the joint taurine's shared extinction on the
    // Analysis page in both themes and both palettes, and a constrained project's Experiment page. Run only when asked
    // (`--demo-only sharedcolour-`).
    if (only.startsWith(QLatin1String("sharedcolour-"))) {
        const auto palette = [](const QString& name) {
            return QStringList{"appBar.button.preferences", "preferences.tab.appearance", "preferences.colours",
                               "choose:" + name, "choose:OK"};
        };
        steps_.push_back({"sharedcolour-1-main-light",
                          QStringList{"resize:1480x900", "theme:light"} + start
                              + QStringList{"open-project:" + qEnvironmentVariable("EDI_DEMO_JOINT_PROJECT"), analysis,
                                            basic, "parameters.nameFilter", "type:coefficient"}});
        steps_.push_back({"sharedcolour-2-main-dark", {"theme:dark"}});
        steps_.push_back({"sharedcolour-3-safe-dark", palette(QStringLiteral("Colour-blind safe"))});
        steps_.push_back({"sharedcolour-4-safe-light", {"theme:light"}});
        steps_.push_back({"sharedcolour-5-constrained-experiment",
                          palette(QStringLiteral("Main")) + QStringList{"open-project:" + qEnvironmentVariable("EDI_DEMO_TIED_PROJECT"),
                                                                 "appBar.tab.experiment", "experiments.name.1",
                                                                 "reveal:group.extinction", "expand:group.extinction"}});
    }
    // The Evolution tab of a scan before and after its fit, with the parameter list open. Run only when asked
    // (`--demo-only evolution-`).
    if (only.startsWith(QLatin1String("evolution-"))) {
        const QStringList scan = QStringList{"resize:1280x960", "theme:light"} + start
                                 + open_cli_project("pd-neut-cwl_cosio-d20_scan-162f")
                                 + QStringList{analysis, basic, "mainArea.tab.evolution"};
        steps_.push_back({"evolution-1-unfitted", scan});
        steps_.push_back({"evolution-2-unfitted-parameters", {"evolution.parameters"}});
        steps_.push_back({"evolution-3-fitted", {"key:Escape", "statusBar.fit.button", "wait-fit",
                                                 "choose:OK", "mainArea.tab.evolution"}});
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
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
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
    // The Structure, Report and Experiment pages' tables, the current structure's row marked, in both themes. Run only
    // when asked (`--demo-only tables-`).
    if (only.startsWith(QLatin1String("tables-"))) {
        steps_.push_back({"tables-1-structure-light",
                          QStringList{"resize:1280x960", "theme:light"} + start + open_example("pd-neut-tof_ferrite-austenite-beer")
                              + QStringList{"appBar.tab.structure", basic, "group.atom_site_aniso"}});
        steps_.push_back({"tables-2-structure-dark", {"theme:dark"}});
        steps_.push_back({"tables-3-report-dark", {"appBar.tab.report"}});
        steps_.push_back({"tables-4-report-light", {"theme:light"}});
        steps_.push_back({"tables-5-report-again", {"theme:light"}});
        // The Experiment page's measured data and background tables.
        steps_.push_back({"tables-6-data-light", {"appBar.tab.experiment", extras, "expand:group.data"}});
        steps_.push_back({"tables-7-data-dark", {"theme:dark"}});
        steps_.push_back({"tables-8-background-dark", {"expand:group.background"}});
        steps_.push_back({"tables-9-background-light", {"theme:light"}});
    }
    // The tables of two constant-wavelength examples, in both themes: measured data and background points on the
    // Experiment page, the experiments, the Analysis parameters and the atom sites. Run only when asked
    // (`--demo-only tablecheck-`).
    if (only.startsWith(QLatin1String("tablecheck-"))) {
        int n = 0;
        const auto name = [&n](const QString& what) {
            return QStringLiteral("tablecheck-%1-%2").arg(++n, 2, 10, QLatin1Char('0')).arg(what);
        };
        for (const QString& id : {QStringLiteral("pd-neut-cwl_y2o3-spodi"), QStringLiteral("pd-neut-cwl_lbco-hrpt")}) {
            const QString sample = id.section(QLatin1Char('_'), 1, 1).section(QLatin1Char('-'), 0, 0);
            steps_.push_back({name(sample + "-data-light"), QStringList{"resize:1280x960", "theme:light"} + start +
                                                                 open_example(id) +
                                                                 QStringList{experiment, extras, "expand:group.data"}});
            steps_.push_back({name(sample + "-data-dark"), {"theme:dark"}});
            steps_.push_back({name(sample + "-background-dark"), {basic, "expand:group.background"}});
            steps_.push_back({name(sample + "-background-light"), {"theme:light"}});
            steps_.push_back({name(sample + "-experiments-light"), {"expand:group.experiments"}});
            steps_.push_back({name(sample + "-parameters-light"), {analysis, basic, "expand:group.parameters"}});
            steps_.push_back({name(sample + "-parameters-dark"), {"theme:dark"}});
            steps_.push_back({name(sample + "-atom-sites-dark"), {"appBar.tab.structure", basic, "expand:group.atom_site"}});
            steps_.push_back({name(sample + "-atom-sites-light"), {"theme:light"}});
        }
    }
    // Every table of the app in the light theme, on an example that fills it, each image named after its table (the
    // owner, 2026-10-27). Run only when asked (`--demo-only tableshots-`).
    if (only.startsWith(QLatin1String("tableshots-"))) {
        const auto shot = [this](const QString& table, const QStringList& actions) {
            steps_.push_back({QStringLiteral("tableshots-") + table, actions});
        };
        shot("examples", QStringList{"resize:1280x960", "theme:light"} + start);
        shot("structures", start + open_example("pd-neut-tof_ferrite-austenite-beer") +
                               QStringList{structure, basic, "expand:group.structures"});
        shot("linked-structures", {experiment, basic, "expand:group.linked_structure"});
        shot("measured-data-two-structures", {extras, "expand:group.data"});
        shot("recent-projects", {"appBar.tab.project", basic, "expand:group.recentProjects"});
        shot("atom-sites", start + open_example("pd-neut-cwl_y2o3-spodi") + QStringList{structure, basic, "expand:group.atom_site"});
        shot("atomic-displacements", {"expand:group.atom_site_aniso"});
        shot("measured-data", {experiment, extras, "expand:group.data"});
        shot("measured-data-wide-window", {"resize:1920x1080"});
        shot("measured-data-small-window", {"resize:1100x760"});
        shot("background-points", {"resize:1280x960", basic, "expand:group.background"});
        shot("parameters", {analysis, basic, "expand:group.parameters"});
        shot("measured-data-lbco", start + open_example("pd-neut-cwl_lbco-hrpt") + QStringList{experiment, extras, "expand:group.data"});
        shot("background-points-lbco", {basic, "expand:group.background"});
        shot("excluded-regions", {"expand:group.excluded_region"});
        shot("experiments", start + open_example("pd-neut-tof_ncaf-wish") + QStringList{experiment, basic, "expand:group.experiments"});
        shot("joint-fit", {analysis, extras, "expand:group.joint_fit"});
        shot("background-terms", start + open_example("pd-neut-tof_cecoal-polaris") +
                                     QStringList{experiment, basic, "expand:group.background"});
        shot("aliases", start + open_example("pd-neut-cwl_cosio-d20") + QStringList{analysis, extras, "expand:group.alias"});
        shot("constraints", {"expand:group.constraint"});
        shot("single-crystal-reflections", start + open_example("sc-neut-tof_taurine-senju") +
                                               QStringList{experiment, extras, "expand:group.refln"});
        shot("scattering-lengths", open_cli_project("pd-neut-cwl_lab6-11b-echidna_basic") +
                                       QStringList{structure, extras, "expand:group.scattering_length"});
        shot("preferred-orientation", open_cli_project("pd-neut-cwl_lbco-hrpt_start-2") +
                                          QStringList{experiment, extras, "expand:group.preferred_orientation"});
        shot("reflections", start + open_example("pd-neut-cwl_lbco-hrpt") +
                                QStringList{experiment, extras, "expand:group.refln"});
        shot("fit-results", start + open_example("pd-neut-cwl_lbco-hrpt") +
                                QStringList{analysis, basic, "statusBar.fit.button", "wait-fit"});
        steps_.push_back({"tableshots-fit-results-closed", {"choose:OK"}});
        steps_.back().capture = false;
        // A scan's window keeps changing while its datasets load, so its step is captured unsettled.
        shot("sequential-extract", start + open_cli_project("pd-neut-cwl_cosio-d20_scan") +
                                       QStringList{analysis, extras, "expand:group.sequential_fit_extract", "capture-now"});
    }
    // Each structure's curve: the Analysis chart with the toolbar's switch on, in both themes, and the Experiment page's
    // data table with a column per structure. Run only when asked (`--demo-only curves-`).
    if (only.startsWith(QLatin1String("curves-"))) {
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
        steps_.push_back({"onechart-1-analysis-zoomed",
                          QStringList{"resize:1280x960", "theme:light"} + start + open_example("pd-neut-tof_ferrite-austenite-beer")
                              + QStringList{analysis, basic, "drag:chart.pointer:0.74,0.05,0.80,0.95", "chart.toolbar.structureCurves"}});
        steps_.push_back({"onechart-2-experiment", {experiment}});
        steps_.push_back({"onechart-3-structure-pattern", {"appBar.tab.structure", "mainArea.tab.pattern"}});
        steps_.push_back({"onechart-4-structure-view", {"mainArea.tab.structure"}});
        steps_.push_back({"onechart-5-analysis-again", {analysis, "chart.toolbar.structureCurves"}});
    }
    // The owner's first local test: latp_scan's three structures on the Experiment page, a zoom with each structure's
    // curve off, then the curves on and off again. Run only when asked (`--demo-only latp-`).
    if (only.startsWith(QLatin1String("latp-"))) {
        steps_.push_back({"latp-1-experiment", {"resize:1280x960", "theme:light", "open-cli-project:pd-xray-cwl_latp_scan-4f",
                                                experiment, basic}});
        steps_.push_back({"latp-2-zoomed", {"drag:chart.pointer:0.30,0.05,0.45,0.95"}});
        steps_.push_back({"latp-3-curves-on", {"chart.toolbar.structureCurves"}});
        steps_.push_back({"latp-4-curves-off", {"chart.toolbar.structureCurves"}});
        steps_.push_back({"latp-5-reset", {"chart.toolbar.reset"}});
    }
    // The Text tab on LBCO's structure, Editable and Everything, in both themes. Run only when asked
    // (`--demo-only texttab-`).
    if (only.startsWith(QLatin1String("texttab-"))) {
        steps_.push_back({"texttab-1-editable-light", QStringList{"resize:1280x960", "theme:light"} + start +
                                                          open_example("pd-neut-cwl_lbco-hrpt") +
                                                          QStringList{"appBar.tab.structure", text}});
        steps_.push_back({"texttab-2-editable-dark", {"theme:dark"}});
        steps_.push_back({"texttab-3-everything-dark", {"text.show", "choose:Everything"}});
        steps_.push_back({"texttab-4-everything-light", {"theme:light"}});
        steps_.push_back({"texttab-5-editable-again", {"text.show", "choose:Editable"}});
        // An edit not yet applied: the check button turns red.
        steps_.push_back({"texttab-6-edited-light", {"text.view", "type: "}});
        steps_.push_back({"texttab-7-edited-dark", {"theme:dark"}});
    }
    // Each page's Text tab at the supported minimum window size. Run only when asked (`--demo-only textmin-`).
    if (only.startsWith(QLatin1String("textmin-"))) {
        steps_.push_back({"textmin-1-project", QStringList{"resize:1024x640", "theme:light"} + start +
                                                   open_example("pd-neut-cwl_lbco-hrpt") +
                                                   QStringList{"appBar.tab.project", text}});
        steps_.push_back({"textmin-2-structure", {"appBar.tab.structure", text}});
        steps_.push_back({"textmin-3-experiment", {"appBar.tab.experiment", text}});
        steps_.push_back({"textmin-4-analysis", {"appBar.tab.analysis", text}});
        steps_.push_back({"textmin-5-report", {"appBar.tab.report", text}});
    }
    // The excluded ranges on Stacked and the Map, shown and hidden (the owner, 2026-10-27): NCAF's five banks. Run only
    // when asked (`--demo-only excluded-`).
    if (only.startsWith(QLatin1String("excluded-"))) {
        steps_.push_back({"excluded-1-stacked-shown", QStringList{"resize:1280x960", "theme:light"} + start +
                                                          open_example("pd-neut-tof_ncaf-wish") +
                                                          QStringList{"appBar.tab.experiment", "mainArea.tab.stacked"}});
        steps_.push_back({"excluded-2-stacked-hidden", {"scanView.stacked.toolbar.includedRange"}});
        steps_.push_back({"excluded-3-map-hidden", {"mainArea.tab.map"}});
        steps_.push_back({"excluded-4-map-shown", {"scanView.map.toolbar.includedRange"}});
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
                                                  + open_cli_project("pd-neut-cwl_cosio-d20_scan")
                                                  + QStringList{analysis, basic, "statusBar.fit.button",
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
                                                "mainArea.tab.pattern", "chart.toolbar.legend", "chart.legend.toggle"}});
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
                                              "mainArea.tab.pattern"}});
        steps_.push_back({"lines-2-stacked", {"mainArea.tab.stacked", "scanView.stacked.toolbar.spacing",
                                              "choose:Overlay", "wait-scan:stacked"}});
        // The same drawn by the painter, as a machine without a GPU draws it.
        steps_.push_back({"lines-3-stacked-painter", {"preference:scanRenderer=software", "wait-scan:stacked"}});
    }
    if (only.startsWith(QLatin1String("scanviews-"))) {
        steps_.push_back({"scanviews-01-stacked-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                            + open_cli_project("pd-neut-cwl_cosio-d20_scan")
                                                            + QStringList{analysis, basic, "mainArea.tab.stacked"}});
        steps_.push_back({"scanviews-02-map-light", {"mainArea.tab.map"}});
        steps_.push_back({"scanviews-03-map-light-stepped", {"scanView.map.toolbar.smooth"}});
        steps_.push_back({"scanviews-04-map-light-log-inferno",
                          {"scanView.map.toolbar.smooth", "scanView.map.toolbar.yscale", "choose:Log",
                           "scanView.map.toolbar.colourMap", "choose:Inferno"}});
        steps_.push_back({"scanviews-05-map-light-running", {"statusBar.fit.button", "wait-files:40",
                                                            "capture-now"}});
        steps_.push_back({"scanviews-06-stacked-light-running", {"mainArea.tab.stacked", "wait-files:60",
                                                                "capture-now"}});
        steps_.push_back({"scanviews-07-evolution-light-running", {"mainArea.tab.evolution", "wait-files:70",
                                                                  "capture-now"}});
        steps_.push_back({"scanviews-08-stacked-dark-running", {"theme:dark", "mainArea.tab.stacked",
                                                               "wait-files:80", "capture-now"}});
        steps_.push_back({"scanviews-09-map-dark-running", {"mainArea.tab.map", "wait-files:100", "capture-now"}});
        steps_.push_back({"scanviews-10-evolution-dark", {"wait-fit", "choose:OK", "mainArea.tab.evolution"}});
        steps_.push_back({"scanviews-11-map-dark-greys", {"mainArea.tab.map", "scanView.map.toolbar.colourMap",
                                                         "choose:Greys"}});
        steps_.push_back({"scanviews-12-map-dark-d-zoom", {"scanView.map.toolbar.xaxis", "choose:x: d-spacing",
                                                          "drag:scanView.map.pointer:0.05,0.2,0.45,0.7"}});
        steps_.push_back({"scanviews-13-stacked-dark-narrow-zoom", {"mainArea.tab.stacked",
                                                                   "scanView.stacked.toolbar.xaxis", "choose:2θ",
                                                                   "drag:scanView.stacked.pointer:0.40,0.02,0.46,0.6"}});
        steps_.push_back({"scanviews-14-stacked-dark-secondary-reset", {"right-click:scanView.stacked.pointer"}});
        steps_.push_back({"scanviews-15-stacked-dark-included-only", {"scanView.stacked.toolbar.includedRange"}});
        steps_.push_back({"scanviews-16-stacked-light-included-only", {"theme:light"}});
        steps_.push_back({"scanviews-17-map-light-included-only", {"mainArea.tab.map"}});
        steps_.push_back({"scanviews-17b-map-light-full-range", {"scanView.map.toolbar.includedRange"}});
        steps_.push_back({"scanviews-18-map-light-narrow-two-lines", {"resize:1000x960"}});
        steps_.push_back({"scanviews-19-joint-stacked-light-d",
                          {"resize:1280x960", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic,
                           "mainArea.tab.stacked", "scanView.stacked.toolbar.xaxis", "choose:x: d-spacing"}});
        steps_.push_back({"scanviews-20-joint-map-light-d", {"mainArea.tab.map"}});
        steps_.push_back({"scanviews-21-joint-map-dark-d", {"theme:dark"}});
        steps_.push_back({"scanviews-22-joint-stacked-dark-d", {"mainArea.tab.stacked"}});
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
                              + open_cli_project("pd-neut-cwl_cosio-d20_scan")
                              + QStringList{QStringLiteral("appBar.tab.experiment"), basic,
                                            "mainArea.tab.stacked"}});
        steps_.push_back({"colours-2-experiment-map-light", {"mainArea.tab.map"}});
        steps_.push_back({"colours-3-preferences", {"appBar.button.preferences", "preferences.tab.appearance"}});
        steps_.push_back({"colours-4-classic",
                          {"preferences.colours", "choose:Classic", "choose:OK", "mainArea.tab.pattern"}});
        steps_.push_back({"colours-5-dark", {"theme:dark"}});
        steps_.push_back({"colours-6-experiment-stacked-dark", {"mainArea.tab.stacked"}});
    }
    // The three-dataset test scan's Stacked view, its scan-value axis labelled only over the rows (the owner, 2026-10-22), in
    // both themes. Run only when asked (`--demo-only stackrange-`).
    if (only.startsWith(QLatin1String("stackrange-"))) {
        steps_.push_back({"stackrange-1-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                    + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                                                    + QStringList{analysis, basic, "mainArea.tab.stacked"}});
        steps_.push_back({"stackrange-2-dark", {"theme:dark"}});
        steps_.push_back({"stackrange-3-map-dark", {"mainArea.tab.map"}});
    }
    // The scan views' rows labelled by scan value, by file and, thinned, on cosio's 155 patterns; the Map's scale with a
    // tick per dataset by scan value, its bands labelled by file; a zoom bringing labels back; the three-dataset scan
    // with every label (the owner, 2026-10-22). Run only when asked (`--demo-only rowlabels-`).
    if (only.startsWith(QLatin1String("rowlabels-"))) {
        steps_.push_back({"rowlabels-01-stacked-value-light", QStringList{"resize:1280x960", "theme:light"} + start
                                                                  + open_cli_project("pd-neut-cwl_cosio-d20_scan")
                                                                  + QStringList{analysis, basic, "mainArea.tab.stacked"}});
        steps_.push_back({"rowlabels-01b-stacked-height-4x-light", {"scanView.stacked.toolbar.height", "choose:4×"}});
        steps_.push_back({"rowlabels-01c-stacked-height-2x-light", {"scanView.stacked.toolbar.height", "choose:2×"}});
        steps_.push_back({"rowlabels-02-map-value-ticks-light", {"mainArea.tab.map"}});
        steps_.push_back({"rowlabels-02b-map-bottom-zoom-light", {"drag:scanView.map.pointer:0.1,0.82,0.9,0.995"}});
        steps_.push_back({"rowlabels-02c-map-reset-light", {"right-click:scanView.map.pointer"}});
        steps_.push_back({"rowlabels-02d-map-dense-selected-light", {"drag:scanView.map.pointer:0.5,0.93,0.5,0.93"}});
        steps_.push_back({"rowlabels-02e-stacked-dense-selected-light", {"mainArea.tab.stacked"}});
        steps_.push_back({"rowlabels-03-map-file-light", {"mainArea.tab.map", "scanView.map.toolbar.rows", "choose:File"}});
        steps_.push_back({"rowlabels-04-stacked-file-light", {"mainArea.tab.stacked"}});
        steps_.push_back({"rowlabels-05-stacked-file-zoom-light", {"drag:scanView.stacked.pointer:0.1,0.55,0.9,0.85"}});
        steps_.push_back({"rowlabels-06-stacked-file-dark", {"theme:dark", "right-click:scanView.stacked.pointer"}});
        steps_.push_back({"rowlabels-07-stacked-value-dark", {"scanView.stacked.toolbar.rows", "choose:Temperature (K)"}});
        steps_.push_back({"rowlabels-08-map-value-dark", {"mainArea.tab.map"}});
        steps_.push_back({"rowlabels-09-three-stacked-light",
                          QStringList{"theme:light"} + open_cli_project("pd-neut-cwl_cosio-d20_scan-3f")
                              + QStringList{analysis, basic, "mainArea.tab.stacked"}});
        steps_.push_back({"rowlabels-10-three-map-dark", {"theme:dark", "mainArea.tab.map"}});
        steps_.push_back({"rowlabels-11-joint-stacked-datablock-light",
                          {"theme:light", "open-cli-project:pd-neut-tof_ncaf-wish-5bank_start-5", analysis, basic,
                           "mainArea.tab.stacked"}});
        steps_.push_back({"rowlabels-11b-joint-stacked-tof-reversed-light", {"scanView.stacked.toolbar.reverse"}});
        steps_.push_back({"rowlabels-12-joint-map-datablock-dark", {"theme:dark", "mainArea.tab.map"}});
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
                                                  + open_cli_project("pd-neut-cwl_cosio-d20_scan")
                                                  + QStringList{analysis, basic, "mainArea.tab.map",
                                                                "scanView.map.toolbar.yscale", "choose:Log"}});
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
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
        const QString stacked = QStringLiteral("mainArea.tab.stacked");
        const QString map = QStringLiteral("mainArea.tab.map");
        const QString pattern = QStringLiteral("mainArea.tab.pattern");
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
        const QString stacked = QStringLiteral("mainArea.tab.stacked");
        const QString map = QStringLiteral("mainArea.tab.map");
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
             "mainArea.tab.pattern", "chart.toolbar.includedRange"},
            {"fixes-21-3f-pattern-light", "chart.toolbar.includedRange"},
            {"fixes-22-heidi-correlations-light", "open-cli-project:sc-neut-cwl_tb2ti2o7-heidi_fit", analysis, basic,
             "mainArea.tab.correlations"},
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
    // The About window and its two popups, then How to cite and Diagnostics, in both themes. Run only when asked
    // (`--demo-only about-`).
    if (only.startsWith(QLatin1String("about-"))) {
        for (const QString& theme : {QStringLiteral("light"), QStringLiteral("dark")}) {
            const QString first = theme == QLatin1String("light") ? QStringLiteral("resize:1280x960") : QStringLiteral("key:Escape");
            steps_.push_back({"about-" + theme + "-1-window", {first, "theme:" + theme, "appBar.tab.home", "home.about"}});
            steps_.push_back({"about-" + theme + "-2-bsd", {"about.licence.BSD-3-Clause"}});
            steps_.push_back({"about-" + theme + "-3-third-party", {"key:Escape", "about.thirdParty"}});
            // The other information windows (InfoDialog): How to cite and Diagnostics.
            steps_.push_back({"about-" + theme + "-4-citation", {"key:Escape", "key:Escape", "home.cite"}});
            steps_.push_back({"about-" + theme + "-5-diagnostics", {"key:Escape", "appBar.button.preferences",
                                                                    "preferences.tab.advanced", "preferences.diagnostics"}});
            steps_.push_back({"about-" + theme + "-6-closed", {"key:Escape", "key:Escape"}});
        }
    }
    // One fit timed in the app: a prepared copy of the 213-pattern scan in Independent mode
    // (EDI_DEMO_INDEPENDENT_PROJECT) or of the Parametric example with U, V and W shared (EDI_DEMO_PARAMETRIC_PROJECT),
    // under the Cores for fitting preference in effect. Run one at a time (`--demo-only fittime-independent`).
    if (only.startsWith(QLatin1String("fittime-"))) {
        steps_.push_back({"fittime-independent", {"open-project:" + qEnvironmentVariable("EDI_DEMO_INDEPENDENT_PROJECT"),
                                                  "wait-settled", analysis, "timed-fit:213"}});
        steps_.push_back({"fittime-parametric", {"open-project:" + qEnvironmentVariable("EDI_DEMO_PARAMETRIC_PROJECT"),
                                                 "wait-settled", analysis, "timed-fit:213"}});
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
        QStringList views{"resize:1280x800", "open-cli-project:pd-neut-cwl_cosio-d20_scan-324f", analysis,
                          "mainArea.tab.stacked", "wait-scan:stacked"};
        for (const QString& mode : {QStringLiteral("stacked"), QStringLiteral("map")}) {
            if (mode == QLatin1String("map")) {
                views << "mainArea.tab.map" << "wait-scan:map";
            }
            views << "timed-frames:" + mode + ":zoom:40" << "timed-frames:" + mode + ":pan:50"
                  << "timed-frames:" + mode + ":restyle:20" << "timed-frames:" + mode + ":select:20"
                  << "timed-frames:" + mode + ":data:10" << "timed-frames:" + mode + ":rows:10";
        }
        steps_.push_back({"perf-views-324f", views});
        // A data change alone on the Stacked view, to profile it.
        steps_.push_back({"perf-data-324f", {"resize:1280x800", "open-cli-project:pd-neut-cwl_cosio-d20_scan-324f", analysis,
                                             "mainArea.tab.stacked", "wait-scan:stacked",
                                             "timed-frames:stacked:data:10"}});
        // The same with the Stacked lines on the GPU, chosen as a user chooses it in Performance.
        views.insert(1, QStringLiteral("preference:scanRenderer=gpu"));
        steps_.push_back({"perf-gpu-views-324f", views});
        const QStringList updates{"resize:1280x800", scan, analysis, "sideBar.tab.settings", "expand:group.patternUpdates",
                                  "analysis.patternUpdates"};
        for (const auto& [name, choice] : {std::pair{"every", "Every pattern, fit waits for the display"},
                                           std::pair{"catchup", "Every pattern, display catches up"},
                                           std::pair{"adaptive", "Adaptive"}}) {
            steps_.push_back({QStringLiteral("perf-fit-%1-pattern").arg(QLatin1String(name)),
                              updates + QStringList{QStringLiteral("choose:") + QLatin1String(choice), "mainArea.tab.pattern",
                                                    "timed-fit:162"}});
            steps_.push_back({QStringLiteral("perf-fit-%1-stacked").arg(QLatin1String(name)),
                              updates + QStringList{QStringLiteral("choose:") + QLatin1String(choice), "mainArea.tab.stacked",
                                                    "wait-scan:stacked", "timed-fit:162"}});
        }
        const QStringList lbco{"resize:1280x800", "open-cli-project:pd-neut-cwl_lbco-hrpt_start-4", analysis,
                               "sideBar.tab.basic", "mainArea.tab.pattern", "parameters.nameFilter",
                               "type:length_a"};
        steps_.push_back({"perf-slider-lbco-1-before-fit", lbco + QStringList{"timed-slider:30"}});
        // The same steps again and again with no fit: what a growing edit history alone costs.
        steps_.push_back({"perf-slidernofit-1", lbco + QStringList{"timed-slider:30"}});
        for (int batch = 2; batch <= 4; ++batch) {
            steps_.push_back({QStringLiteral("perf-slidernofit-%1").arg(batch), {"timed-slider:30"}});
        }
        steps_.push_back({"perf-slider-lbco-2-after-fit", {"statusBar.fit.button", "wait-fit", "choose:OK", "timed-slider:30"}});
        // Note 45 says "after the fits": four more, five in all, from where the slider left the model each time.
        QStringList fits;
        for (int fit = 0; fit < 4; ++fit) {
            fits << "statusBar.fit.button" << "wait-fit" << "choose:OK";
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
    if (documentation_ && !output_dir_.entryList(QStringList{"*.png", "*.webp", "manifest.json"}, QDir::Files).isEmpty()) {
        fail(QStringLiteral("documentation output must not contain an earlier capture"));
        return;
    }
    park_pointer();
    QTimer::singleShot(0, this, [this] { run_step(); });
}

void DemoDriver::run_step() {
    if (current_ == steps_.size()) {
        const int code = !documentation_ || saveDocumentationManifest("complete") ? 0 : 1;
        if (trace_complete(code)) return;
        QCoreApplication::exit(code);
        return;
    }
    documentation_skip_ = false;
    if (documentation_) {
        std::fprintf(stdout, "docs-capture: %s\n", qPrintable(steps_[current_].image));
        std::fflush(stdout);
    }
    const Step& step = steps_[current_];
    if (!step.trace.isEmpty()) trace_step_begin(step);
    action_ = 0;
    // Next and previous presses go out on a 100 ms schedule from the first of a run of them, as a held key would.
    if (step.navigation != 0) {
        if (!nav_clock_.isValid()) nav_clock_.start();
        const qint64 now = nav_clock_.elapsed();
        if (current_ == 0 || steps_[current_ - 1].navigation == 0) {
            nav_base_ = now;
            nav_index_ = 0;
        }
        const qint64 due = nav_base_ + qint64{100} * nav_index_++;
        QTimer::singleShot(static_cast<int>(std::max<qint64>(0, due - now)), Qt::PreciseTimer, this, [this] { next_action(); });
        return;
    }
    next_action();
}

QImage DemoDriver::grab() {
    // The window grab renders a frame on the GUI thread for the driver, not for the user: the GUI watchdog leaves it
    // out (ui_probe.hpp).
#if EDI_UI_INSTRUMENTATION
    const int id = ++tool_id_;
    trace_measurement(true, id, QStringLiteral("QQuickWindow::grabWindow"));
    QImage frame = window_.grabWindow();
    trace_measurement(false, id, QStringLiteral("QQuickWindow::grabWindow"));
    return frame;
#else
    return window_.grabWindow();
#endif
}

namespace {
ProjectViewModel* open_project(QQuickWindow& window);  // below
}  // namespace

#if EDI_UI_INSTRUMENTATION
void DemoDriver::trace_collect_tabs(QQuickItem* root) {
    std::function<void(QQuickItem*)> walk = [&](QQuickItem* item) {
        for (QQuickItem* child : item->childItems()) {
            const QString name = child->objectName();
            if (name.startsWith(QLatin1String("mainArea.")) && name.contains(QLatin1String(".tab.")) &&
                !view_tabs_.contains(child))
                view_tabs_.append(child);
            if (name.startsWith(QLatin1String("sideBar.tab.")) && !side_tabs_.contains(child)) side_tabs_.append(child);
            walk(child);
        }
    };
    walk(root);
}

void DemoDriver::trace_tab_inventory() {
    if (tab_inventory_sent_) return;
    QJsonObject pages;
    for (const QPointer<QQuickItem>& tab : page_tabs_) {
        if (!tab) continue;
        const QString page = tab->objectName().mid(11);
        QJsonArray main, sidebar;
        if (auto* loader = qvariant_cast<QQuickItem*>(tab->property("page")); loader != nullptr) {
            if (loader->property("status").toInt() != 1) return;  // a page still being built: not yet
            // A main view declares every tab button and shows the page's own set (its tabKeys, spelled as its allKeys):
            // only those are the page's tabs.
            std::function<void(QQuickItem*, const QStringList*)> walk = [&](QQuickItem* item, const QStringList* keys) {
                QStringList own;
                if (item->metaObject()->indexOfProperty("allKeys") >= 0) {
                    own = item->property("tabKeys").toStringList();
                    keys = &own;
                }
                for (QQuickItem* child : item->childItems()) {
                    const QString name = child->objectName();
                    const QString key = name.section(QLatin1Char('.'), -1);
                    if (name.startsWith(QLatin1String("mainArea.")) && name.contains(QLatin1String(".tab."))) {
                        const QString spelled = key.toLower();
                        if (keys == nullptr || keys->contains(spelled))
                            main.append(QJsonObject{{"key", keys != nullptr ? spelled : key}, {"object", name}});
                    }
                    if (name.startsWith(QLatin1String("sideBar.tab."))) sidebar.append(QJsonObject{{"key", key}, {"object", name}});
                    walk(child, keys);
                }
            };
            walk(loader, nullptr);
        }
        pages.insert(page, QJsonObject{{"main", main}, {"sidebar", sidebar}});
    }
    tab_inventory_sent_ = true;
    EDI_UI_TRACE("tab-inventory", {{"witness", "qml-tab-bars"}, {"pages", pages}});
}

void DemoDriver::trace_measurement(bool enter, int id, const QString& callback) {
    // The span marker and the callback witness of the driver's own work, at one instant (tools/ci/gui_watchdog.py).
    if (!ui_trace_on()) return;
    if (enter) {
        ui_trace_group({{"tool-begin", {{"id", id}, {"callback", callback}}},
                        {"measurement-enter", {{"id", id}, {"callback", callback}}}});
    } else {
        ui_trace_group({{"measurement-leave", {{"id", id}, {"callback", callback}}},
                        {"tool-end", {{"id", id}, {"callback", callback}}}});
    }
}

void DemoDriver::trace_step_begin(const Step& step) {
    if (!ui_trace_on()) return;
    if (!trace_begun_) {
        trace_begun_ = true;
        trace_scenario_ = only_.section(QLatin1Char('-'), 0, 1);
        trace_watch();  // the observers are in place before the first input
        EDI_UI_TRACE("begin", {{"scenario", trace_scenario_}});
    }
    // A step that only waits (a fit's progress) issues its wait as its action.
    if (step.navigation == 0 && !step.actions.isEmpty() && step.actions.first().startsWith(QLatin1String("wait-"))) {
        trace_issue(step.actions.first());
    }
    // The watchdog's control: EDI_UI_BLOCK_MS blocks the GUI thread once inside the measured steps, outside the
    // driver's own work, so a check that cannot see a blocked GUI thread is caught. Production never sets it.
    if (const int block = qEnvironmentVariableIntValue("EDI_UI_BLOCK_MS"); block > 0 && !blocked_) {
        blocked_ = true;
        EDI_UI_TRACE("block-begin", {{"ms", block}});
        QThread::msleep(static_cast<unsigned long>(block));
        EDI_UI_TRACE("block-end", {{"ms", block}});
    }
}

void DemoDriver::trace_issue(const QString& action) {
    if (!ui_trace_on()) return;
    const Step& step = steps_[current_];
    const QJsonObject now = trace_state();
    Pending pending;
    pending.request = ++request_id_;
    pending.name = step.trace;
    if (action.startsWith(QLatin1String("appBar.tab."))) {
        pending.page = action.mid(11);
    } else if ((action.startsWith(QLatin1String("mainArea.")) && action.contains(QLatin1String(".tab."))) ||
               action.startsWith(QLatin1String("sideBar.tab."))) {
        pending.object = action;
        // The button on screen now, the one the press reaches: Structure's and Analysis' tab bars both have a
        // mainArea.tab.structure, and a later lookup by name found the hidden page's, which never became checked.
        pending.button = find(action, true);
    } else if (action.startsWith(QLatin1String("mainArea.blocks."))) {
        pending.before = now.value(QStringLiteral("selection")).toInt();
        if (step.navigation != 0) {
            pending.direction = step.navigation > 0 ? QStringLiteral("next") : QStringLiteral("previous");
            FrameWatch watch;
            watch.request = pending.request;
            watch.chart = find_held(QStringLiteral("chart"), false);
            if (watch.chart) watch.controller = watch.chart->findChild<PatternChartController*>();
            if (watch.controller) watch.base = watch.controller->traceGeneration();
            frame_watches_.append(watch);
        }
    } else if (action == QLatin1String("statusBar.fit.button")) {
        pending.fit = QStringLiteral("start");
        fit_runs_at_start_ = fit_runs_;
        pending.runs = fit_runs_;
    } else if (action.startsWith(QLatin1String("wait-files"))) {
        pending.fit = QStringLiteral("running");
        pending.runs = fit_runs_at_start_;
    } else if (action == QLatin1String("wait-fit")) {
        pending.fit = QStringLiteral("ended");
    } else {
        pending.fit = QStringLiteral("settled");
    }
    pending_.push_back(pending);
    EDI_UI_TRACE("action", {{"request", pending.request}, {"name", step.trace}, {"command", action},
                            {"before_selection", now.value(QStringLiteral("selection"))}});
}

void DemoDriver::trace_issued(const Step&) {
    if (!ui_trace_on() || pending_.empty()) return;
    // The press's target is the selection it made, read from the model at once.
    const int dataset = trace_state().value(QStringLiteral("selection")).toInt();
    pending_.back().dataset = dataset;
    if (!frame_watches_.isEmpty() && frame_watches_.last().request == pending_.back().request)
        frame_watches_.last().dataset = dataset;
}

bool DemoDriver::trace_complete(int code) {
    if (!trace_begun_) return false;
    // The last steps' observations are written on a frame: a step that changes nothing on screen (the end of a run,
    // settled) draws none by itself, so frames are asked for until they are written, for at most 3 s.
    if (!pending_.empty() && complete_waits_ < 60) {
        ++complete_waits_;
        window_.requestUpdate();
        QTimer::singleShot(50, this, [this, code] {
            if (!trace_complete(code)) QCoreApplication::exit(code);
        });
        return true;
    }
    // The trace's last tick follows its end, so the measured interval is closed by a tick.
    EDI_UI_TRACE("complete", {{"scenario", trace_scenario_}});
    QTimer::singleShot(50, this, [code] { QCoreApplication::exit(code); });
    return true;
}

void DemoDriver::trace_watch() {
    if (watching_) {
        return;
    }
    watching_ = true;
    // The tab buttons are found once: reading their state is all a frame costs.
    std::function<void(QQuickItem*)> walk = [&](QQuickItem* item) {
        for (QQuickItem* child : item->childItems()) {
            if (child->objectName().startsWith(QLatin1String("appBar.tab."))) page_tabs_.append(child);
            walk(child);
        }
    };
    walk(window_.contentItem());
    trace_collect_tabs(window_.contentItem());
    input_identity_ = trace_input();
    if (ProjectViewModel* project = open_project(window_); project != nullptr) {
        // What was loaded, counted from the model: the patterns (a scan's datasets or the experiments), structures,
        // experiments and the current pattern's points.
        const edi::Project& core = project->project();
        int data_points = 0;
        if (const ExperimentViewModel* experiment = project->currentExperiment(); experiment != nullptr) {
            const auto& held = *core.experiments[experiment->tracePlace()];
            if (held.data) data_points = static_cast<int>(held.data->intensity_meas.size());
        }
        // A series' fitted points, a scan's datasets, or none; each holds one measured pattern per bank with data.
        const int banks = static_cast<int>(core.experiments.size());
        const int with_data = static_cast<int>(std::count_if(core.experiments.begin(), core.experiments.end(),
                                                             [](const auto& bank) { return bank->data.has_value(); }));
        const int series_points = project->property("seriesPointCount").toInt();
        const bool scan = project->scanTemplate() != nullptr;
        const int points = series_points > 0 ? series_points
                           : scan && project->experiments() != nullptr ? project->experiments()->rowCount() : 0;
        EDI_UI_TRACE("input", {{"identity", input_identity_}, {"input", input_identity_}, {"banks", banks},
                               {"measured", with_data > 0}, {"measured_banks", with_data},
                               {"points", points}, {"data_points", data_points},
                               {"structures", static_cast<int>(core.structures.size())}});
        if (FitViewModel* fit = project->fit(); fit != nullptr) {
            fit_running_ = fit->running();
            connect(fit, &FitViewModel::runningChanged, this, [this, fit] {
                fit_running_ = fit->running();
                if (fit_running_) ++fit_runs_;
            });
        }
    }
    connect(&window_, &QQuickWindow::afterAnimating, this, &DemoDriver::trace_frame);
    // At synchronisation the GUI thread waits, so the native state and the chart's geometry are read there and are
    // what the frame shows; the frame's swap then writes them, with the transitions published for it, at one instant.
    // Both run on the render thread: they are dropped before quitting, so none can run while the driver goes away.
    trace_sync_ = connect(&window_, &QQuickWindow::afterSynchronizing, this, [this] {
        const QJsonObject displayed = trace_state();
        QJsonArray frames, presented;
        // One observation a swap, so the swap's render names one request: a press's first frame comes first (it must
        // be the first swap after the press); a settled frame waits for the next swap, which checks it again.
        FrameWatch* chosen = nullptr;
        bool settling = false;
        for (FrameWatch& watch : frame_watches_) {
            if (watch.chart && !watch.first) {
                chosen = &watch;
                break;
            }
        }
        QString buffers;
        if (chosen == nullptr) {
            for (FrameWatch& watch : frame_watches_) {
                if (!watch.chart || !watch.presented || watch.settled || !watch.controller) continue;
                // Settled: the chart's current upload was made from the selected dataset's data, the series objects
                // hold that upload now (read back from them), and every measured point they draw is a point of the
                // selected data as the project holds it. The generation named is the one drawn.
                const PatternChartController* controller = watch.controller;
                if (controller->traceIdentity() != watch.native) continue;
                const QString held = controller->traceBufferIdentity();
                if (held.isEmpty() || held != controller->traceUploadIdentity()) continue;
                if (!trace_matches_expected(watch)) continue;
                chosen = &watch;
                settling = true;
                buffers = held;
                break;
            }
        }
        if (chosen != nullptr) {
            FrameWatch& watch = *chosen;
            QJsonObject frame = trace_geometry(watch.chart);
            frame.insert(QStringLiteral("request"), watch.request);
            if (!settling) {
                watch.first = true;
                frame.insert(QStringLiteral("phase"), QStringLiteral("first"));
                frames.append(frame);
            } else {
                watch.settled = true;
                watch.presentation.insert(QStringLiteral("generation"), static_cast<double>(watch.controller->traceGeneration()));
                watch.presentation.insert(QStringLiteral("upload_identity"), watch.controller->traceUploadIdentity());
                watch.presentation.insert(QStringLiteral("buffer_identity"), buffers);
                for (auto it = watch.presentation.begin(); it != watch.presentation.end(); ++it) frame.insert(it.key(), it.value());
                frame.insert(QStringLiteral("phase"), QStringLiteral("settled"));
                frames.append(frame);
                presented.append(watch.presentation);
            }
        }
        const std::lock_guard lock(trace_mutex_);
        synced_frame_ = ui_trace_frame_synced();
        synced_displayed_ = displayed;
        synced_transitions_ = std::exchange(published_transitions_, {});
        synced_frames_ = frames;
        synced_presented_ = presented;
    }, Qt::DirectConnection);
    trace_swap_ = connect(&window_, &QQuickWindow::frameSwapped, this, [this] {
        std::vector<std::pair<const char*, QJsonObject>> events;
        QJsonArray requests;
        {
            const std::lock_guard lock(trace_mutex_);
            for (const auto& value : std::exchange(synced_frames_, {})) {
                QJsonObject frame = value.toObject();
                requests.append(frame.value(QStringLiteral("request")));
                frame.insert(QStringLiteral("frame"), synced_frame_);
                frame.insert(QStringLiteral("witness"), QStringLiteral("afterSynchronizing/frameSwapped"));
                events.emplace_back("frame", frame);
            }
            QJsonObject render{{"frame", synced_frame_},
                               {"transitions", std::exchange(synced_transitions_, {})},
                               {"displayed", synced_displayed_}};
            // The request whose first or settled frame this is, and for a settled one its presentation (request,
            // input, dataset, generation, data and buffer identities), on the render itself.
            const QJsonArray presented = std::exchange(synced_presented_, {});
            // At most one observation a swap (above): its request, and a settled one's presentation.
            if (!requests.isEmpty()) render.insert(QStringLiteral("request"), requests.first());
            if (!presented.isEmpty()) {
                const QJsonObject shown = presented.first().toObject();
                for (auto it = shown.begin(); it != shown.end(); ++it) render.insert(it.key(), it.value());
            }
            events.emplace_back("render", render);
        }
        ui_trace_group(events);
    }, Qt::DirectConnection);
    connect(QCoreApplication::instance(), &QCoreApplication::aboutToQuit, this, [this] {
        disconnect(trace_sync_);
        disconnect(trace_swap_);
    });
}

QJsonObject DemoDriver::trace_geometry(QQuickItem* chart) const {
    // The pattern chart's three panes and its three axes (their titles), each a scene rectangle and whether it shows.
    static const std::pair<const char*, const char*> kEntries[] = {
        {"pattern", "chart.view.main"},  {"bragg", "chart.view.bragg"},      {"residual", "chart.view.residual"},
        {"x", "chart.title.x"},          {"intensity", "chart.title.y"},     {"residual-axis", "chart.title.residual"}};
    QJsonObject rects, shown;
    for (const auto& [name, object] : kEntries) {
        auto* item = chart->findChild<QQuickItem*>(QString::fromLatin1(object));
        const QRectF r = item != nullptr ? item->mapRectToScene(QRectF(0, 0, item->width(), item->height())) : QRectF();
        rects.insert(QString::fromLatin1(name), QJsonArray{r.x(), r.y(), r.width(), r.height()});
        shown.insert(QString::fromLatin1(name),
                     item != nullptr && item->isVisible() && item->opacity() > 0 && r.width() > 0 && r.height() > 0);
    }
    return {{"panes", QJsonArray{"pattern", "bragg", "residual"}}, {"axes", QJsonArray{"x", "intensity", "residual"}},
            {"geometry", rects}, {"visible", shown}};
}

QString DemoDriver::trace_input() {
    // The project's content, not its folder: an ordinary run and its control open copies in different places.
    const ProjectViewModel* project = open_project(window_);
    if (project == nullptr) return {};
    QCryptographicHash hash(QCryptographicHash::Sha256);
    QStringList files;
    QDirIterator it(QString::fromStdString(project->project().path), {QStringLiteral("*.edi")}, QDir::Files,
                    QDirIterator::Subdirectories);
    while (it.hasNext()) files.append(it.next());
    files.sort();
    const QDir root(QString::fromStdString(project->project().path));
    for (const QString& path : files) {
        QFile file(path);
        if (file.open(QIODevice::ReadOnly)) {
            hash.addData(root.relativeFilePath(path).toUtf8());
            hash.addData(file.readAll());
        }
    }
    return QString::fromLatin1(hash.result().toHex().left(16));
}

QJsonObject DemoDriver::trace_state() {
    QString page;
    for (const QPointer<QQuickItem>& tab : page_tabs_) {
        if (tab && tab->property("checked").toBool()) page = tab->objectName().mid(11);
    }
    // The shown page's selected main and sidebar tabs: checked, visible and on screen (another page's are off screen).
    const auto selected = [this](const QList<QPointer<QQuickItem>>& tabs) -> QJsonValue {
        for (const QPointer<QQuickItem>& tab : tabs) {
            if (tab && tab->property("checked").toBool() && tab->isVisible() && on_screen(tab))
                return tab->objectName().section(QLatin1Char('.'), -1);
        }
        return QJsonValue::Null;
    };
    const ProjectViewModel* project = open_project(window_);
    return {{"input", input_identity_}, {"page", page}, {"tab", selected(view_tabs_)}, {"sidebar_tab", selected(side_tabs_)},
            {"selection", project != nullptr ? project->property("currentExperimentIndex").toInt() : -1}};
}

QString DemoDriver::trace_native_identity() {
    // The selected pattern's measured data as the project holds them, read from the model, not from a chart: empty
    // while a scan's selected dataset is still being read.
    ProjectViewModel* project = open_project(window_);
    if (project == nullptr) return {};
    const ExperimentViewModel* experiment = project->currentExperiment();
    if (experiment == nullptr) return {};
    const int selection = project->property("currentExperimentIndex").toInt();
    if (project->scanTemplate() != nullptr && (project->traceAppliedDataset() != selection || !project->viewSettled()))
        return {};
    const std::uint64_t key = project->traceViewApplied() * 1000003u + static_cast<std::uint64_t>(selection + 1);
    if (native_cache_.first != key || native_cache_.second.isEmpty()) {
        const auto& held = *project->project().experiments[experiment->tracePlace()];
        native_cache_ = std::make_pair(key, held.data ? ui_trace_identity(&held.data->intensity_meas.get()) : QString());
    }
    return native_cache_.second;
}

void DemoDriver::trace_expect(FrameWatch& watch) {
    const PatternChartController* controller = watch.controller;
    if (controller == nullptr || watch.expected_generation == controller->traceGeneration()) return;
    ProjectViewModel* project = open_project(window_);
    const int place = controller->traceExperimentPlace();
    if (project == nullptr || place < 0) return;
    watch.expected.clear();
    watch.expected_presentation.reset();
    watch.expected_generation = controller->traceGeneration();
    // The selected data, captured from the project and presented with the chart's own view: what the chart should
    // draw for this upload.
    const edi::PatternSource source = edi::capture_pattern(project->project(), static_cast<std::size_t>(place), controller->traceAxis());
    edi::PatternPresentation presentation = edi::present_pattern(source, controller->traceView());
    for (const edi::PatternSeries& series : presentation.series) {
        if (series.kind != edi::SeriesKind::Measured) continue;
        for (const edi::PresentedPoint& point : series.points)
            if (std::isfinite(point.x) && std::isfinite(point.y)) watch.expected.append(QPointF(point.x, point.y));
    }
    watch.expected_presentation = std::move(presentation);
}

bool DemoDriver::trace_matches_expected(const FrameWatch& watch) const {
    // Every buffer the chart draws (lines, band edges and fills, bars, component areas and outlines, the measured marks
    // and their bars, in the representation shown) is the one the selected data give, and none is left from before.
    const PatternChartController* controller = watch.controller;
    return controller != nullptr && watch.expected_generation == controller->traceGeneration() && !watch.expected.isEmpty() &&
           watch.expected_presentation.has_value() && controller->traceMatches(*watch.expected_presentation);
}

void DemoDriver::trace_frame() {
    QJsonObject state = trace_state();
    const int selection = state.value(QStringLiteral("selection")).toInt();
    const QString native = trace_native_identity();
    // A press's dataset is presented once the chart has uploaded data whose content is that dataset's, as the project
    // holds it: an upload of anything else, or one made before the press, is not.
    for (FrameWatch& watch : frame_watches_) {
        if (watch.presented || !watch.controller || watch.dataset < 0) continue;
        if (watch.native.isEmpty() && selection == watch.dataset) watch.native = native;
        if (!watch.native.isEmpty() && watch.controller->traceGeneration() > watch.base &&
            watch.controller->traceIdentity() == watch.native && !watch.controller->traceUploadIdentity().isEmpty()) {
            watch.presented = true;
            watch.generation = watch.controller->traceGeneration();
            watch.upload = watch.controller->traceUploadIdentity();
            watch.presentation = {{"request", watch.request}, {"dataset", watch.dataset},
                                  {"generation", static_cast<double>(watch.controller->traceGeneration())},
                                  {"data_identity", watch.native}, {"input", input_identity_},
                                  {"upload_identity", watch.upload}};
            EDI_UI_TRACE("presented", watch.presentation);
        }
        if (watch.presented && !watch.settled && watch.controller) trace_expect(watch);
    }
    // The steps' actions, in order: each writes its state, its publication and then the step, once the native state
    // shows what it asked for.
    while (!pending_.empty()) {
        const Pending& pending = pending_.front();
        bool reached = false;
        // A press another press replaced before its dataset was read is written as it is now, superseded and with no
        // data identity: its dataset was never shown.
        bool superseded = false;
        if (!pending.page.isEmpty()) {
            reached = state.value(QStringLiteral("page")).toString() == pending.page;
        } else if (!pending.object.isEmpty()) {
            const QQuickItem* button = pending.button ? pending.button.data() : find_held(pending.object, false);
            reached = button != nullptr && button->property("checked").toBool();
        } else if (pending.dataset >= 0) {
            superseded = selection != pending.dataset;
            reached = superseded || !native.isEmpty();
        } else if (pending.before >= 0) {
            reached = selection != pending.before;
        } else if (pending.fit == QLatin1String("start") || pending.fit == QLatin1String("running")) {
            // A fit started since the press counts, even one already over: a blocked GUI thread (the watchdog's
            // control) can miss every frame of a short fit.
            reached = fit_running_ || fit_runs_ > pending.runs;
        } else if (!pending.fit.isEmpty()) {
            reached = !fit_running_;
        }
        if (!reached) break;
        const QString transition = QStringLiteral("t%1").arg(pending.request);
        QJsonObject reached_state = state;
        reached_state.insert(QStringLiteral("request"), pending.request);
        reached_state.insert(QStringLiteral("selected_object"), pending.object);
        if (!pending.page.isEmpty()) {
            // A page visit: its tab buttons are collected once it is built, and the inventory once every page is.
            for (const QPointer<QQuickItem>& tab : page_tabs_) {
                if (tab && tab->objectName() == QLatin1String("appBar.tab.") + pending.page) {
                    if (auto* loader = qvariant_cast<QQuickItem*>(tab->property("page")); loader != nullptr) trace_collect_tabs(loader);
                }
            }
            trace_tab_inventory();
        }
        reached_state.insert(QStringLiteral("transition"), transition);
        QJsonObject publication{{"transition", transition}, {"input", input_identity_}};
        if (superseded) {
            reached_state.insert(QStringLiteral("superseded"), true);
            publication.insert(QStringLiteral("superseded"), true);
        } else if (pending.dataset >= 0) {
            reached_state.insert(QStringLiteral("data_identity"), native);
            publication.insert(QStringLiteral("data_identity"), native);
        }
        if (!pending.fit.isEmpty()) {
            const ProjectViewModel* project = open_project(window_);
            const FitViewModel* fit = project != nullptr ? project->fit() : nullptr;
            reached_state.insert(QStringLiteral("fitting"), fit_running_);
            reached_state.insert(QStringLiteral("completed"), fit != nullptr ? fit->scanProcessed() : 0);
            reached_state.insert(QStringLiteral("run"), fit_runs_);
            publication.insert(QStringLiteral("run"), fit_runs_);
        }
        EDI_UI_TRACE("state", reached_state);
        {
            const std::lock_guard lock(trace_mutex_);
            published_transitions_.append(transition);
        }
        publication.insert(QStringLiteral("frame"), ui_trace_next_frame());
        EDI_UI_TRACE("transition-publication", publication);
        QJsonObject step{{"name", pending.name}, {"request", pending.request}};
        if (!pending.direction.isEmpty()) {
            step.insert(QStringLiteral("direction"), pending.direction);
            step.insert(QStringLiteral("dataset"), pending.dataset);
        }
        EDI_UI_TRACE("step", step);
        pending_.pop_front();
    }
}
#else
void DemoDriver::trace_step_begin(const Step&) {}
void DemoDriver::trace_issue(const QString&) {}
void DemoDriver::trace_issued(const Step&) {}
bool DemoDriver::trace_complete(int) { return false; }
#endif

namespace {
QString item_path(const QQuickItem* item);
bool awaiting_owner(const QQuickItem* item);
// Every item under `root` by the visual tree: a Loader's or a SwipeView's items need not be QObject children of it.
QList<QQuickItem*> visual_items(QQuickItem* root) {
    QList<QQuickItem*> out;
    QList<QQuickItem*> todo{root};
    while (!todo.isEmpty()) {
        QQuickItem* at = todo.takeLast();
        for (QQuickItem* child : at->childItems()) {
            out << child;
            todo << child;
        }
    }
    return out;
}
// Whether the item is in the shown page of every swipe view around it: a view keeps its other pages beside the shown one.
bool in_shown_tab(QQuickItem* item) {
    QList<const QQuickItem*> chain;
    for (QQuickItem* at = item; at != nullptr; at = at->parentItem()) {
        if (at->inherits("QQuickSwipeView") && !chain.contains(at->property("currentItem").value<QQuickItem*>())) return false;
        chain << at;
    }
    return true;
}
}  // namespace

// The assistant panel open and at rest: inside the window, and nothing it draws past its own edge.
void DemoDriver::check_assistant_panel() {
    QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
    if (!summary.open(QIODevice::Append | QIODevice::Text)) return;
    QTextStream line(&summary);
    QQuickItem* panel = nullptr;
    for (QQuickItem* item : visual_items(window_.contentItem()))
        if (item->objectName() == QLatin1String("assistant.panel") && item->isVisible() && item->width() > 0) panel = item;
    if (panel == nullptr) {
        line << steps_[current_].image << "\tW11:panel\tno open panel\n";
        return;
    }
    const QRectF box = panel->mapRectToScene(QRectF(0, 0, panel->width(), panel->height()));
    line << steps_[current_].image << "\tW11:checked\t" << qRound(box.left()) << ".." << qRound(box.right()) << " of " << window_.width() << '\n';
    if (box.left() < -1 || box.right() > window_.width() + 1 || box.bottom() > window_.height() + 1)
        line << steps_[current_].image << "\tW11:panel\tthe panel reaches " << qRound(box.right()) << " x " << qRound(box.bottom()) << " of " << window_.width() << " x "
             << window_.height() << '\n';
    for (QQuickItem* item : visual_items(panel)) {
        if (!item->isVisible() || !item->property("text").isValid() || item->property("text").toString().isEmpty()) continue;
        const QRectF at = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
        if (at.right() > box.right() + 1 || at.left() < box.left() - 1)
            line << steps_[current_].image << "\tW11:item\t" << item->objectName() << " '" << item->property("text").toString().left(24) << "' at " << qRound(at.left())
                 << ".." << qRound(at.right()) << ", panel " << qRound(box.left()) << ".." << qRound(box.right()) << '\n';
    }
}

void DemoDriver::check_pane_borders() {
    QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
    if (!summary.open(QIODevice::Append | QIODevice::Text)) return;
    QTextStream line(&summary);
    const QImage image = window_.grabWindow();
    const double scale = window_.devicePixelRatio();
    if (image.isNull()) return;
    int checked = 0;
    for (QQuickItem* item : visual_items(window_.contentItem())) {
        // Every chart view (Qt Graphs' have a plot area), the small panes too.
        if (!item->property("plotArea").isValid() || !item->isVisible() || !on_screen(item) || !in_shown_tab(item)) continue;
        const QRectF plot = item->property("plotArea").toRectF();
        if (plot.width() < 4 || plot.height() < 4) continue;
        QQuickItem* chart = nullptr;
        for (QQuickItem* up = item; up != nullptr && chart == nullptr; up = up->parentItem())
            if (up->property("colors").isValid()) chart = up;
        QObject* colors = chart != nullptr ? chart->property("colors").value<QObject*>() : nullptr;
        const QColor axis = colors != nullptr ? colors->property("chartAxis").value<QColor>() : QColor();
        if (!axis.isValid()) continue;
        const QRectF at = item->mapRectToScene(plot);
        // A single crystal's own plot, under the pattern chart drawn over it.
        if (chart->property("onAxis").toBool()) continue;
        // What of it shows: a pane scrolled partly out is checked where it is seen.
        QRectF seen(QPointF(0, 0), QSizeF(window_.width(), window_.height()));
        for (QQuickItem* up = item; up != nullptr; up = up->parentItem())
            if (up->clip()) seen = seen.intersected(up->mapRectToScene(up->clipRect()));
        // The colours its chart draws traces in.
        QList<QColor> traces;
        const auto add = [&traces](const QObject* drawn) {
            if (const QColor c = drawn->property("color").value<QColor>(); c.isValid() && !traces.contains(c)) traces << c;
        };
        for (QObject* drawn : chart->findChildren<QObject*>())
            if (drawn->inherits("QAbstractSeries")) add(drawn);
        for (QQuickItem* drawn : visual_items(chart))
            if (QByteArray(drawn->metaObject()->className()).contains("Layer")) add(drawn);
        const auto near = [&](double x, double y) {
            const int px = qBound(0, qRound(x * scale), image.width() - 1), py = qBound(0, qRound(y * scale), image.height() - 1);
            const QColor c = image.pixelColor(px, py);
            return std::abs(c.red() - axis.red()) + std::abs(c.green() - axis.green()) + std::abs(c.blue() - axis.blue()) < 90;
        };
        // A trace proven at the pixel: one or two of those colours drawn, at least a fifth opaque, over the line or the
        // background.
        const QColor ground = colors->property("chartBackground").value<QColor>();
        const auto traced = [&](double x, double y) {
            const int px = qRound(x * scale), py = qRound(y * scale);
            if (!image.valid(px, py)) return false;
            const auto parts = [](const QColor& c, const QColor& from) {
                return QVector3D(static_cast<float>(c.red() - from.red()), static_cast<float>(c.green() - from.green()), static_cast<float>(c.blue() - from.blue()));
            };
            const QColor c = image.pixelColor(px, py);
            for (const QColor& under : {axis, ground})
                for (const QColor& first : traces)
                    for (const QColor& second : traces) {
                        const QVector3D d = parts(c, under), l = parts(first, under), m = parts(second, under);
                        const float ll = QVector3D::dotProduct(l, l), lm = QVector3D::dotProduct(l, m), mm = QVector3D::dotProduct(m, m);
                        const float dl = QVector3D::dotProduct(d, l), dm = QVector3D::dotProduct(d, m), det = ll * mm - lm * lm;
                        if (ll < 900 || mm < 900) continue;
                        const float p = det < 1000 ? dl / ll : (dl * mm - dm * lm) / det, q = det < 1000 ? 0.0F : (dm * ll - dl * lm) / det;
                        if (p > -0.02F && q > -0.02F && p + q > 0.2F && p + q < 1.1F && (d - p * l - q * m).length() < 12) return true;
                    }
            return false;
        };
        // The share of a line's shown length drawn in the axis colour, within a pixel of it, leaving out where a trace
        // lies over it; -1: not in view.
        const auto share = [&](bool horizontal, double where) {
            int hit = 0, all = 0;
            const double from = std::max(horizontal ? at.left() : at.top(), horizontal ? seen.left() : seen.top()) + 1;
            const double to = std::min(horizontal ? at.right() : at.bottom(), horizontal ? seen.right() : seen.bottom()) - 1;
            if (where < (horizontal ? seen.top() : seen.left()) + 1 || where > (horizontal ? seen.bottom() : seen.right()) - 1) return -1.0;
            const int steps = static_cast<int>(std::ceil((to - from) * scale));
            for (int step = 0; step < steps; ++step) {
                const double t = from + step / scale;
                bool found = false;
                for (int half = -2; half <= 2 && !found; ++half) found = horizontal ? near(t, where + 0.5 * half) : near(where + 0.5 * half, t);
                if (!found && (horizontal ? traced(t, where) : traced(where, t))) continue;
                ++all;
                if (found) ++hit;
            }
            return all > 0 ? double(hit) / all : -1.0;
        };
        const QStringList sides{QStringLiteral("top"), QStringLiteral("bottom"), QStringLiteral("left"), QStringLiteral("right")};
        const QList<double> shares{share(true, at.top()), share(true, at.bottom() - 1.0 / scale), share(false, at.left()), share(false, at.right() - 1.0 / scale)};
        QString text;
        for (int i = 0; i < 4; ++i) text += shares[i] < 0 ? sides[i] + QStringLiteral(" not in view ") : QStringLiteral("%1 %2% ").arg(sides[i]).arg(qRound(shares[i] * 100));
        ++checked;
        const QString name = item->objectName().isEmpty() ? item_path(item) : item->objectName();
        line << steps_[current_].image << "\tW9:checked\t" << name << '\t' << text << '\n';
        for (int i = 0; i < 4; ++i)
            if (shares[i] >= 0 && shares[i] < 1.0) line << steps_[current_].image << "\tW9:pane-border\t" << name << '\t' << sides[i] << " line drawn " << qRound(shares[i] * 100) << "%, of " << text << '\n';
    }
    if (checked == 0) line << steps_[current_].image << "\tW9:pane-border\tno pane on screen to check\n";
}

void DemoDriver::check_report_figure(QQuickItem* figure, const QImage& drawn) {
    QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
    if (!summary.open(QIODevice::Append | QIODevice::Text) || drawn.isNull() || figure->width() < 1) return;
    QTextStream line(&summary);
    const QString name = figure->objectName(), frame = steps_[current_].image;
    // The border is the figure's sibling of its own size.
    QQuickItem* border = nullptr;
    for (QQuickItem* at = figure; at != nullptr && border == nullptr; at = at->parentItem()) {
        if (at->parentItem() == nullptr) break;
        for (QQuickItem* sibling : at->parentItem()->childItems())
            if (sibling != at && sibling->inherits("QQuickRectangle") && sibling->isVisible() && std::abs(sibling->width() - figure->width()) < 1 && std::abs(sibling->height() - figure->height()) < 1) border = sibling;
    }
    const QQuickPen* pen = border != nullptr ? static_cast<QQuickRectanglePrivate*>(QObjectPrivate::get(qobject_cast<QQuickRectangle*>(border)))->pen : nullptr;
    const bool edged = pen != nullptr && pen->isValid() && pen->width() > 0;
    const double scale = drawn.width() / figure->width();
    const QRgb back = drawn.pixel(drawn.width() / 2, static_cast<int>(2 * scale));
    const auto differs = [&](int x, int y) {
        const QRgb at = drawn.pixel(x, y);
        return std::abs(qRed(at) - qRed(back)) + std::abs(qGreen(at) - qGreen(back)) + std::abs(qBlue(at) - qBlue(back)) > 24;
    };
    int minX = drawn.width(), minY = drawn.height(), maxY = -1;
    for (int y = 0; y < drawn.height(); ++y)
        for (int x = 0; x < drawn.width(); ++x)
            if (differs(x, y)) {
                minX = std::min(minX, x);
                minY = std::min(minY, y);
                maxY = std::max(maxY, y);
            }
    // The right side at the plot's frame, half way down: an x tick's number may hang over the plot's end.
    int frameX = -1;
    for (int x = drawn.width() - 1; x >= 0 && frameX < 0; --x)
        if (differs(x, drawn.height() * 2 / 5)) frameX = x;
    const double top = minY / scale, leftSide = minX / scale, right = (drawn.width() - 1 - frameX) / scale, bottom = (drawn.height() - 1 - maxY) / scale;
    const QString padding = QStringLiteral("left %1 top %2 right %3 bottom %4").arg(leftSide, 0, 'f', 1).arg(top, 0, 'f', 1).arg(right, 0, 'f', 1).arg(bottom, 0, 'f', 1);
    line << frame << "\tW9:checked\t" << name << '\t' << padding << (edged ? ", border " : ", no border") << '\n';
    if (!edged) line << frame << "\tW9:border\t" << name << "\tno border around the figure\n";
    // One padding for every figure, the main area's margin; a structure's scene is drawn by the camera, so there its
    // buttons' distance from the top counts.
    QQmlEngine* engine = qmlEngine(figure);
    QObject* sizes = engine != nullptr ? engine->singletonInstance<QObject*>("edi.app", "AppSizes") : nullptr;
    const double wanted = sizes != nullptr ? sizes->property("mainAreaMargin").toDouble() : -1;
    const QList<double> counted = name.startsWith(QLatin1String("report.structure.")) ? QList<double>{top} : QList<double>{leftSide, top, right, bottom};
    for (const double side : counted)
        if (std::abs(side - wanted) > 1.0) {
            line << frame << "\tW9:padding\t" << name << '\t' << padding << ", each " << wanted << " wanted\n";
            break;
        }
}

// T7 (ADR-0103; the owner, 2026-11-24): every open sidebar table is drawn and shows all its rows, or whole rows and half
// the next (at least 2.5) when they do not fit; such a table leaves its column no room for another row; and a column
// scrolls only when one of its open tables is down to 2.5 rows.
void DemoDriver::check_table_room(QTextStream& line, const QString& frame, const QString& action) {
    QHash<QQuickItem*, QList<QQuickItem*>> byColumn;
    for (QQuickItem* table : visual_items(window_.contentItem())) {
        if (!table->property("roomRows").isValid() || !table->isVisible()) continue;
        if (table->property("onScreen").isValid() && !table->property("onScreen").toBool()) continue;
        QQuickItem* column = nullptr;
        bool open = true;
        for (QQuickItem* up = table->parentItem(); up != nullptr; up = up->parentItem()) {
            if (up->property("restingHeight").isValid() && up->property("collapsed").toBool()) open = false;
            if (up->inherits("QQuickFlickable") && up->property("childrenCount").isValid()) {
                column = up;
                break;
            }
        }
        if (open && column != nullptr) byColumn[column] << table;
    }
    for (auto it = byColumn.cbegin(); it != byColumn.cend(); ++it) {
        QQuickItem* column = it.key();
        const double spare = column->height() - column->property("contentHeight").toDouble();
        bool atFloor = false;
        for (QQuickItem* table : it.value()) {
            const QString name = item_path(table);
            auto* header = table->property("headerItem").value<QQuickItem*>();
            const double rowHeight = table->property("tableRowHeight").toDouble();
            const int count = table->property("count").toInt();
            // Counted in the rows' own heights (a row of wrapped lines is taller); a row not made has the table's height.
            QHash<int, double> made;
            for (const QQuickItem* row : table->property("contentItem").value<QQuickItem*>()->childItems())
                if (row->property("index").isValid() && row->isVisible() && row->property("listView").value<QQuickItem*>() == table)
                    made.insert(row->property("index").toInt(), row->height());
            const auto heightOf = [&](int row) { return made.value(row, rowHeight); };
            const double room = table->height() - (header != nullptr ? header->height() : 0.0);
            double rows = 0.0, filled = 0.0;
            if (rowHeight > 0) {
                int at = 0;
                for (; at < count && filled + heightOf(at) <= room + 0.01; ++at) filled += heightOf(at);
                rows = at + (room - filled) / heightOf(at);
            }
            const auto extent = std::minmax_element(made.cbegin(), made.cend());
            line << frame << "\tT7:checked\t" << name << '\t' << QString::number(rows, 'f', 2) << " of " << count << " rows shown, column spare "
                 << qRound(spare) << " px, " << room << " px for rows of "
                 << (made.isEmpty() ? QString::number(rowHeight) : QStringLiteral("%1 to %2 px").arg(*extent.first).arg(*extent.second)) << " (" << action << ")\n";
            if (table->opacity() < 0.99 || table->height() < 1) {
                line << frame << "\tT7:empty\t" << name << "\tnot drawn (opacity " << table->opacity() << ", height " << table->height() << ", measuring "
                     << table->property("measureRunning").toBool() << ", widths " << table->property("columnWidths").toStringList().join(QLatin1Char(',')) << ", room "
                     << table->property("roomShown").toDouble() << ")\n";
                continue;
            }
            const bool all = std::abs(rows - std::max(1, count)) < 0.05;
            const double half = rows - std::floor(rows);
            if (!all && (std::abs(half - 0.5) > 0.05 || rows < 2.45)) {
                line << frame << "\tT7:rows\t" << name << '\t' << QString::number(rows, 'f', 2) << " of " << count << " rows: neither all nor whole rows and a half\n";
                continue;
            }
            if (!all && std::abs(rows - 2.5) < 0.05) atFloor = true;
            // The next row whole: the half it shows and half the row after it, or its own rest when it is the last.
            const int next = int(rows);
            const double step = next + 1 < count ? (heightOf(next) + heightOf(next + 1)) / 2 : heightOf(next);
            if (!all && spare >= step - 0.5)
                line << frame << "\tT7:room\t" << name << '\t' << QString::number(rows, 'f', 2) << " of " << count << " rows with " << qRound(spare)
                     << " px of the column left\n";
        }
        if (spare < -0.5 && !atFloor)
            line << frame << "\tT7:scroll\t" << item_path(column) << "\tthe column scrolls (" << qRound(-spare) << " px over) with no table at 2.5 rows\n";
    }
}

void DemoDriver::next_action() {
    // A late callback of a step that ended already, after the last one.
    if (current_ >= steps_.size()) return;
    const Step& step = steps_[current_];
    if (documentation_skip_) {
        documentation_scenes_.append(QJsonObject{{"id", step.image}, {"page", step.page},
            {"sidebar", step.sidebar}, {"status", "skipped"}, {"reason", "sidebar tab is disabled"}});
        ++current_;
        run_step();
        return;
    }
    // A tab the app does not offer in this state (Correlations before a fit) cannot be shown: the step is skipped and
    // the trace says so, rather than the run stopping there.
    // A page still loading can offer a tab a moment later (Pattern once the experiments are listed), so the frame
    // settles once before a tab is taken as not offered.
    if (step.skip_unavailable && action_ == 0 && !step.actions.isEmpty()) {
        QQuickItem* item = find(step.actions.first(), false);
        const bool offered = item != nullptr && item->isVisible() && item->isEnabled() && on_screen(item);
        if (!offered && !availability_settled_) {
            availability_settled_ = true;
            settle_then([this] { next_action(); });
            return;
        }
        availability_settled_ = false;
        if (!offered) {
#if EDI_UI_INSTRUMENTATION
            ui_trace("step-skipped", QJsonObject{{"name", step.trace}, {"control", step.actions.first()},
                                                 {"reason", item == nullptr ? "missing" : !item->isVisible() ? "hidden" : !item->isEnabled() ? "disabled" : "off screen"}});
#endif
            ++current_;
            run_step();
            return;
        }
    }
    // capture-now captures a set time after the actions; capture-at:<ms> after that many milliseconds, to show an
    // animation partway.
    int unsettled_ms = step.actions.contains(QStringLiteral("capture-now")) ? kUnsettledCaptureMs : -1;
    for (const QString& each : step.actions) {
        if (each.startsWith(QLatin1String("capture-at:"))) unsettled_ms = each.mid(11).toInt();
    }
    const bool unsettled = unsettled_ms >= 0;
    if (action_ < step.actions.size()) {
        const QString& action = step.actions.at(action_);
        ++action_;
        if (documentation_) documentation_actions_.append(QJsonObject{{"scene", step.image}, {"action", action}});
        if (action == QLatin1String("capture-now") || action.startsWith(QLatin1String("capture-at:"))) {
            next_action();
            return;
        }
        // `popup-time:<editor>`: after `mark` and a click, waits frame by frame for the parameter popup's value editor to
        // show with the focus, at most a second; F2 its time from the mark (at most 100 ms), F3 its row's vertical
        // centres (the editor's and the docs link's equal +- 1 px).
        if (action.startsWith(QLatin1String("popup-time:"))) {
            const QString name = action.mid(11);
            const QString docsName = QString(name).replace(QLatin1String(".popup.value"), QLatin1String(".popup.docs"));
            auto link = std::make_shared<QMetaObject::Connection>();
            auto done = std::make_shared<bool>(false);
            *link = connect(&window_, &QQuickWindow::frameSwapped, this, [this, name, docsName, link, done] {
                if (*done) return;
                QQuickItem* editor = nullptr;
                QQuickItem* docs = nullptr;
                std::function<void(QQuickItem*)> look = [&](QQuickItem* item) {
                    for (QQuickItem* child : item->childItems()) {
                        if (child->objectName() == name) editor = child;
                        else if (child->objectName() == docsName) docs = child;
                        look(child);
                    }
                };
                look(window_.contentItem());
                const qint64 elapsed = popup_shown_ms_ >= 0 ? popup_shown_ms_ : mark_.isValid() ? mark_.elapsed() : -1;
                // Open: its first drawn frame; the focus is reported beside it.
                const bool shown = editor != nullptr && editor->isVisible();
                if (!shown && elapsed < 1000) {
                    window_.update();
                    return;
                }
                *done = true;
                disconnect(*link);
                QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                if (summary.open(QIODevice::Append | QIODevice::Text)) {
                    QTextStream line(&summary);
                    const QString frame = steps_[current_].image;
                    line << frame << "\tF2:checked\t" << name << '\t' << (shown ? QStringLiteral("open in %1 ms%2").arg(elapsed).arg(editor->hasActiveFocus() ? ", value focused" : ", value not focused") : QStringLiteral("not open")) << '\n';
                    if (!shown || elapsed > 100) line << frame << "\tF2:slow\t" << name << '\t' << (shown ? QStringLiteral("%1 ms, at most 100").arg(elapsed) : QStringLiteral("no popup in a second")) << '\n';
                    // The popup's row as wide before as after a fit: its grid, the editor's loader's parent.
                    if (shown && editor->parentItem() != nullptr && editor->parentItem()->parentItem() != nullptr)
                        line << frame << "\tF3:width\t" << name << '\t' << editor->parentItem()->parentItem()->width() << '\n';
                    if (shown && docs != nullptr) {
                        const double a = editor->mapToScene(QPointF(0, editor->height() / 2)).y();
                        const double b = docs->mapToScene(QPointF(0, docs->height() / 2)).y();
                        line << frame << "\tF3:checked\t" << name << "\tcentres " << a << ' ' << b << '\n';
                        if (std::abs(a - b) > 1.0) line << frame << "\tF3:centres\t" << name << "\teditor centre " << a << ", link " << b << '\n';
                    }
                }
                next_action();
            });
            window_.update();
            return;
        }
        // `frames-stable:unfold:<group>` or `frames-stable:page:<page>`: unfolds the group or switches to the page, then
        // every frame for 1.2 s reads each shown table: its height (T7), its column widths and its first row's cell
        // positions (T6). From a table's first shown frame none of them changes (the owner, 2026-11-23: a table drawn
        // in one layout then another while it opens, the parameter columns flicking once on a page switch).
        // `room-tab`: every collapsible group of the shown sidebar tab opened alone, then with the one before it, the T7
        // room check after each has settled (the owner, 2026-11-24: tables opening empty or with half their rows).
        if (action == QLatin1String("room-tab")) {
            QList<QPointer<QQuickItem>> groups;
            int offered = 0;
            for (QQuickItem* item : visual_items(window_.contentItem())) {
                if (!item->property("restingHeight").isValid() || !item->property("collapsible").toBool() || !item->isVisible()) continue;
                // Every page and sidebar tab is kept beside the shown one: only a group in the shown one counts.
                if (!in_shown_tab(item)) continue;
                ++offered;
                if (item->property("onScreen").isValid() && !item->property("onScreen").toBool()) continue;
                groups << item;
            }
            QString tab;
            for (QQuickItem* item : visual_items(window_.contentItem()))
                if (item->objectName().startsWith(QLatin1String("sideBar.tab.")) && item->property("checked").toBool() && item->isVisible() && on_screen(item))
                    tab = item->objectName();
            auto opened = std::make_shared<QStringList>();
            qWarning("room-tab: %lld groups", static_cast<long long>(groups.size()));
            auto steps = std::make_shared<QList<std::pair<int, bool>>>();
            for (int i = 0; i < groups.size(); ++i) {
                steps->append({i, true});
                if (i > 0) steps->append({i, false});
            }
            auto run = std::make_shared<std::function<void()>>();
            *run = [this, groups, steps, run, opened, offered, tab] {
                if (steps->isEmpty()) {
                    // The groups the step really opened, so a step that shows another tab's is seen.
                    if (QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY")); summary.open(QIODevice::Append | QIODevice::Text)) {
                        QTextStream line(&summary);
                        line << steps_[current_].image << "\tT7:checked\t" << tab << "\tgroups opened: " << opened->join(QLatin1Char(' ')) << '\n';
                        if (opened->isEmpty() && offered > 0)
                            line << steps_[current_].image << "\tT7:noopen\t" << tab << '\t' << offered << " collapsible groups, none opened\n";
                    }
                    // Released after this call returns: resetting the function while it runs would destroy it mid-call.
                    QTimer::singleShot(0, this, [run] { *run = nullptr; });
                    next_action();
                    return;
                }
                const auto [index, alone] = steps->takeFirst();
                for (int i = 0; i < groups.size(); ++i)
                    if (groups[i]) groups[i]->setProperty("collapsed", !(i == index || (!alone && i == index - 1)));
                QTimer::singleShot(1500, this, [this, groups, index, alone, run, opened] {
                    QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                    if (summary.open(QIODevice::Append | QIODevice::Text) && groups[index]) {
                        QTextStream line(&summary);
                        // The group really opened: a state that shows the page as it was is not a state.
                        if (groups[index]->property("collapsed").toBool() || groups[index]->height() < groups[index]->property("restingHeight").toDouble() - 1)
                            line << steps_[current_].image << "\tT7:noopen\t" << groups[index]->objectName() << '\t' << (alone ? "alone" : "after") << " the group did not open\n";
                        else if (!opened->contains(groups[index]->objectName()))
                            opened->append(groups[index]->objectName());
                        check_table_room(line, steps_[current_].image, QStringLiteral("%1 %2").arg(groups[index]->objectName(), alone ? QStringLiteral("alone") : QStringLiteral("after another")));
                    }
                    if (groups[index]) check_layout(QStringLiteral("%1-%2-%3").arg(steps_[current_].image, groups[index]->objectName(), alone ? QStringLiteral("alone") : QStringLiteral("after")));
                    if (groups[index] && steps_[current_].capture)
                        grab().save(output_dir_.filePath(QStringLiteral("%1-%2-%3.png").arg(steps_[current_].image, groups[index]->objectName(), alone ? QStringLiteral("alone") : QStringLiteral("after"))));
                    if (*run) (*run)();
                });
            };
            (*run)();
            return;
        }
        // `room-check`: the T7 room check of every open sidebar table as it is shown now.
        if (action == QLatin1String("room-check")) {
            if (QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY")); summary.open(QIODevice::Append | QIODevice::Text)) {
                QTextStream line(&summary);
                check_table_room(line, steps_[current_].image, action);
            }
            next_action();
            return;
        }
        // `pane-borders`: every chart pane that is shown has its four border lines in the window as drawn, at the place
        // the pane stands (W9). At each scroll position of the report page, as a page is read at any of them.
        if (action == QLatin1String("pane-borders")) {
            check_pane_borders();
            next_action();
            return;
        }
        if (action == QLatin1String("report-scrolls")) {
            QQuickItem* flick = nullptr;
            for (QQuickItem* item : visual_items(window_.contentItem()))
                if (item->inherits("QQuickFlickable") && item->isVisible() && item->property("contentHeight").toDouble() > 2000 && item->property("contentY").toDouble() > 0) flick = item;
            if (flick == nullptr) {
                fail(QStringLiteral("step %1: no report view").arg(steps_[current_].image));
                return;
            }
            auto tries = std::make_shared<QList<double>>(QList<double>{0.0, 0.25, 0.5, 0.75, 3.4, 11.6});
            const double from = flick->property("contentY").toDouble();
            auto run = std::make_shared<std::function<void()>>();
            *run = [this, flick, tries, run, from] {
                if (tries->isEmpty()) {
                    QTimer::singleShot(0, this, [run] { *run = nullptr; });
                    next_action();
                    return;
                }
                flick->setProperty("contentY", from + tries->takeFirst());
                QTimer::singleShot(350, this, [this, run] {
                    check_pane_borders();
                    if (*run) (*run)();
                });
            };
            (*run)();
            return;
        }
        // `report-frames`: every report figure is in a border of one width with the same padding on its four sides (the
        // owner, 2026-11-24): W9. The figure is grabbed as drawn; the padding is from the frame's inner edge to the
        // nearest pixel that is not the figure's background. A structure's scene is drawn by the camera, so only its
        // control buttons' distance from the top counts there, the same as the charts' padding.
        if (action == QLatin1String("report-frames")) {
            QList<QPointer<QQuickItem>> figures;
            for (QQuickItem* item : visual_items(window_.contentItem()))
                if (item->isVisible() && (item->objectName().startsWith(QLatin1String("report.pattern.")) || item->objectName().startsWith(QLatin1String("report.structure.")) ||
                                          item->objectName() == QLatin1String("report.singleCrystal") || item->objectName() == QLatin1String("report.evolution")))
                    figures << item;
            auto left = std::make_shared<int>(static_cast<int>(figures.size()));
            if (figures.isEmpty()) {
                fail(QStringLiteral("step %1: no report figure").arg(steps_[current_].image));
                return;
            }
            for (const QPointer<QQuickItem>& figure : figures) {
                const QSharedPointer<QQuickItemGrabResult> grab = figure->grabToImage();
                if (grab.isNull()) {
                    if (--*left == 0) next_action();
                    continue;
                }
                connect(grab.data(), &QQuickItemGrabResult::ready, this, [this, grab, figure, left] {
                    if (figure) check_report_figure(figure, grab->image());
                    if (--*left == 0) next_action();
                });
            }
            return;
        }
        // `evolution-row`: the Evolution chart's control row spans the selector row above it, whatever parameter is
        // chosen (the owner, 2026-11-24): W8, its left and right edges and its width the same for three selections.
        if (action == QLatin1String("evolution-row")) {
            QQuickItem* toolbar = find(QStringLiteral("evolution.toolbar"), true);
            QQuickItem* top = find(QStringLiteral("mainArea.blocks"), true);
            QQuickItem* picker = find(QStringLiteral("evolution.parameters"), true);
            if (toolbar == nullptr || top == nullptr || picker == nullptr) {
                fail(QStringLiteral("step %1: no evolution row, selector row or picker").arg(steps_[current_].image));
                return;
            }
            auto index = std::make_shared<int>(0);
            auto spans = std::make_shared<QStringList>();
            auto edges = std::make_shared<QList<QPair<double, double>>>();
            auto again = std::make_shared<std::function<void()>>();
            *again = [this, toolbar, top, picker, index, spans, edges, again, action] {
                // The selection moves with the picker's own signal; the row settles in the next frames.
                QMetaObject::invokeMethod(picker, "blockActivated", Q_ARG(int, *index * 6));
                QTimer::singleShot(700, this, [this, toolbar, top, index, spans, edges, again, action] {
                    double left = 1e9, right = -1e9;
                    for (QQuickItem* unit : visual_items(toolbar)) {
                        if (!unit->isVisible() || unit->parentItem() != toolbar || unit->width() < 1) continue;
                        const double x = unit->mapToScene(QPointF(0, 0)).x();
                        left = std::min(left, x);
                        right = std::max(right, x + unit->width());
                    }
                    const double topLeft = top->mapToScene(QPointF(0, 0)).x();
                    const double topRight = top->mapToScene(QPointF(top->width(), 0)).x();
                    edges->append({left, right});
                    QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                    if (summary.open(QIODevice::Append | QIODevice::Text)) {
                        QTextStream line(&summary);
                        const QString where = QStringLiteral("selection %1 row %2..%3, selector row %4..%5").arg(*index).arg(qRound(left)).arg(qRound(right)).arg(qRound(topLeft)).arg(qRound(topRight));
                        line << steps_[current_].image << "\tW8:checked\tevolution\t" << where << '\n';
                        if (std::abs(left - topLeft) > 1.0 || std::abs(right - topRight) > 1.0) line << steps_[current_].image << "\tW8:row\tevolution\t" << where << '\n';
                        if (edges->size() > 1 && (std::abs(edges->last().first - edges->first().first) > 1.0 || std::abs(edges->last().second - edges->first().second) > 1.0))
                            line << steps_[current_].image << "\tW8:moved\tevolution\t" << where << " against selection 0 " << qRound(edges->first().first) << ".." << qRound(edges->first().second) << '\n';
                    }
                    if (++*index >= 3) {
                        next_action();
                        return;
                    }
                    if (*again) (*again)();
                });
            };
            (*again)();
            return;
        }
        if (action.startsWith(QLatin1String("frames-stable:"))) {
            const QString how = action.section(QLatin1Char(':'), 1, 1), target = action.section(QLatin1Char(':'), 2);
            QQuickItem* scope = window_.contentItem();
            if (how == QLatin1String("unfold")) {
                QQuickItem* group = find(target, true);
                if (group == nullptr) {
                    // A group this project has not (preferred orientation of a time-of-flight experiment).
                    qWarning("frames-stable: no shown %s", qPrintable(target));
                    next_action();
                    return;
                }
                scope = group;
            }
            struct Seen {
                double height = 0.0;
                QString widths;
                QString cells;
            };
            auto clock = std::make_shared<QElapsedTimer>();
            auto first = std::make_shared<QHash<QQuickItem*, Seen>>();
            auto moved = std::make_shared<QStringList>();
            auto link = std::make_shared<QMetaObject::Connection>();
            QPointer<QQuickItem> guarded(scope);
            *link = connect(&window_, &QQuickWindow::afterSynchronizing, this, [guarded, first, moved] {
                if (!guarded) return;
                for (QQuickItem* table : guarded->findChildren<QQuickItem*>()) {
                    if (!table->inherits("QQuickListView") || !table->isVisible() || table->height() < 1 || !table->property("columnWidths").isValid()) continue;
                    bool shown = true;
                    for (const QQuickItem* at = table; at != nullptr && shown; at = at->parentItem()) shown = at->isVisible() && at->opacity() > 0.01;
                    if (!shown) continue;
                    const QString widths = table->property("columnWidths").toStringList().join(QLatin1Char(','));
                    QStringList cells;
                    if (QQuickItem* content = table->property("contentItem").value<QQuickItem*>(); content != nullptr) {
                        QQuickItem* row = nullptr;
                        for (QQuickItem* child : content->childItems())
                            if (child->isVisible() && child->height() > 1 && child != table->property("headerItem").value<QQuickItem*>() && (row == nullptr || child->y() < row->y())) row = child;
                        std::function<void(QQuickItem*)> walk = [&](QQuickItem* at) {
                            for (QQuickItem* child : at->childItems()) {
                                if (child->inherits("QQuickRow")) {
                                    for (QQuickItem* cell : child->childItems())
                                        if (cell->isVisible()) cells << QStringLiteral("%1+%2").arg(qRound(cell->x())).arg(qRound(cell->width()));
                                    return;
                                }
                                walk(child);
                            }
                        };
                        if (row != nullptr) walk(row);
                    }
                    const Seen now{table->height(), widths, cells.join(QLatin1Char(' '))};
                    if (!first->contains(table)) {
                        first->insert(table, now);
                        // First draw: a table is drawn from its first frame with its columns measured, so nothing moves
                        // after it shows (T7, and precedence 2).
                        if ((table->property("unfitted").toBool() || table->property("measureRunning").toBool()) && !awaiting_owner(table) && moved->size() < 12)
                            *moved << QStringLiteral("T7:first-draw\t%1 drawn before its columns were measured").arg(table->objectName());
                        continue;
                    }
                    const Seen& was = first->value(table);
                    if (moved->size() >= 12) continue;
                    if (std::abs(was.height - now.height) > 0.5)
                        *moved << QStringLiteral("T7\t%1 height %2 -> %3").arg(table->objectName()).arg(was.height).arg(now.height);
                    if (was.widths != now.widths)
                        *moved << QStringLiteral("T6\t%1 widths %2 -> %3").arg(table->objectName(), was.widths, now.widths);
                    else if (!was.cells.isEmpty() && !now.cells.isEmpty() && was.cells != now.cells)
                        *moved << QStringLiteral("T6\t%1 cells %2 -> %3").arg(table->objectName(), was.cells.left(120), now.cells.left(120));
                    if (moved->size() > 0 && moved->last().contains(table->objectName())) first->insert(table, now);
                }
            }, Qt::DirectConnection);
            auto swapped = std::make_shared<QMetaObject::Connection>();
            auto lastFrame = std::make_shared<qint64>(0);
            auto longest = std::make_shared<qint64>(0);
            auto done = std::make_shared<bool>(false);
            *swapped = connect(&window_, &QQuickWindow::frameSwapped, this, [this, clock, first, moved, link, swapped, action, lastFrame, longest, how, done] {
                // A frame queued before the disconnect still arrives: it must not go to the next action again.
                if (*done) return;
                // R2: the gap between two drawn frames while it opens (the first 600 ms), at most 33 ms.
                const qint64 now = clock->elapsed();
                if (how == QLatin1String("unfold") && now <= 600) *longest = std::max(*longest, now - *lastFrame);
                *lastFrame = now;
                if (clock->elapsed() < 1200) {
                    window_.update();
                    return;
                }
                *done = true;
                disconnect(*link);
                disconnect(*swapped);
                QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                if (summary.open(QIODevice::Append | QIODevice::Text)) {
                    QTextStream line(&summary);
                    const QString frame = steps_[current_].image;
                    line << frame << "\tT6:checked\t" << action << '\t' << first->size() << " tables, every frame for 1.2 s\n";
                    line << frame << "\tT7:checked\t" << action << '\t' << first->size() << " tables, every frame for 1.2 s\n";
                    if (how == QLatin1String("unfold")) {
                        line << frame << "\tR2:checked\t" << action << "\tlongest frame " << *longest << " ms\n";
                        if (*longest > 33) line << frame << "\tR2:frame\t" << action << '\t' << *longest << " ms between frames, at most 33\n";
                    }
                    for (const QString& what : *moved) {
                        const QString kind = what.section(QLatin1Char('\t'), 0, 0);
                        line << frame << '\t' << kind << (kind.contains(QLatin1Char(':')) ? "" : ":moved") << '\t' << action << '\t' << what.section(QLatin1Char('\t'), 1) << '\n';
                    }
                    check_table_room(line, frame, action);
                }
                next_action();
            });
            clock->start();
            if (how == QLatin1String("unfold")) scope->setProperty("collapsed", false);
            else click(QStringLiteral("appBar.tab.") + target);
            window_.update();
            return;
        }
        // `unfold-heights:<group>`: unfolds the group and, every frame for 1.2 s, reads the height of each table shown in
        // it: T7, a table's height from its first visible frame on never changes (no table growing row by row).
        if (action.startsWith(QLatin1String("unfold-heights:"))) {
            QQuickItem* group = find(action.mid(15), true);
            qWarning("unfold-heights: %s %s", qPrintable(action.mid(15)), group == nullptr ? "not found" : "found");
            if (group == nullptr) {
                fail(QStringLiteral("step %1: no group for '%2'").arg(step.image, action));
                return;
            }
            auto clock = std::make_shared<QElapsedTimer>();
            auto first = std::make_shared<QHash<QQuickItem*, double>>();
            auto moved = std::make_shared<QStringList>();
            auto link = std::make_shared<QMetaObject::Connection>();
            QPointer<QQuickItem> guarded(group);
            clock->start();
            group->setProperty("collapsed", false);
            *link = connect(&window_, &QQuickWindow::afterSynchronizing, this, [guarded, first, moved] {
                if (!guarded) return;
                for (QQuickItem* table : guarded->findChildren<QQuickItem*>()) {
                    if (!table->inherits("QQuickListView") || !table->isVisible() || table->height() < 1) continue;
                    if (!first->contains(table)) first->insert(table, table->height());
                    else if (std::abs(first->value(table) - table->height()) > 0.5 && moved->size() < 5)
                        *moved << QStringLiteral("%1 %2 -> %3").arg(table->objectName()).arg(first->value(table)).arg(table->height());
                }
            }, Qt::DirectConnection);
            auto swapped = std::make_shared<QMetaObject::Connection>();
            auto done = std::make_shared<bool>(false);
            *swapped = connect(&window_, &QQuickWindow::frameSwapped, this, [this, clock, first, moved, link, swapped, action, done] {
                // A frame queued before the disconnect still arrives: it must not go to the next action again.
                if (*done) return;
                if (clock->elapsed() < 1200) {
                    window_.update();
                    return;
                }
                *done = true;
                disconnect(*link);
                disconnect(*swapped);
                qWarning("unfold-heights: done, %lld tables", static_cast<long long>(first->size()));
                QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                if (summary.open(QIODevice::Append | QIODevice::Text)) {
                    QTextStream line(&summary);
                    line << steps_[current_].image << "\tT7:checked\t" << action << '\t' << first->size() << " tables\n";
                    for (const QString& what : *moved) line << steps_[current_].image << "\tT7:grew\t" << action << '\t' << what << '\n';
                }
                next_action();
            });
            window_.update();
            return;
        }
        // `scroll-column-x:<list>:<cell prefix>`: the list scrolled fast (120 px a frame) to its end and back, and at every
        // frame's sync, while the scene thread holds the items still, the x of every shown cell named `<prefix><row>`:
        // a column's cells share one x, so any other x is a row drawn off its column for a frame (the owner, 2026-11-23:
        // Free check boxes flickering left while scrolling).
        if (action.startsWith(QLatin1String("scroll-column-x:"))) {
            const QStringList parts = action.mid(QStringLiteral("scroll-column-x:").size()).split(QLatin1Char(':'));
            auto* list = parts.size() == 2 ? find(parts[0], false) : nullptr;
            if (list == nullptr || list->metaObject()->indexOfProperty("contentY") < 0) {
                fail(QStringLiteral("step %1: nothing to scroll for '%2'").arg(step.image, action));
                return;
            }
            const QString& prefix = parts[1];
            struct Samples {
                double first = -1.0;
                double worst = 0.0;
                long long cells = 0;
                long long frames = 0;
                long long off = 0;
                QString where;
                QString firstWidths;
            };
            auto samples = std::make_shared<Samples>();
            auto synced = std::make_shared<QMetaObject::Connection>();
            auto swapped = std::make_shared<QMetaObject::Connection>();
            auto turns = std::make_shared<int>(0);
            QPointer<QQuickItem> guarded(list);
            *synced = connect(&window_, &QQuickWindow::afterSynchronizing, this, [guarded, prefix, samples] {
                if (!guarded)
                    return;
                ++samples->frames;
                bool offThisFrame = false;
                std::function<void(QQuickItem*)> walk = [&](QQuickItem* item) {
                    for (QQuickItem* child : item->childItems()) {
                        if (child->objectName().startsWith(prefix) && child->isVisible()) {
                            const double x = child->mapToScene(QPointF(0, 0)).x();
                            ++samples->cells;
                            if (samples->first < 0)
                                samples->first = x;
                            else if (std::abs(x - samples->first) > 0.5) {
                                offThisFrame = true;
                                if (std::abs(x - samples->first) > samples->worst) {
                                    samples->worst = std::abs(x - samples->first);
                                    samples->where = QStringLiteral("%1 at %2, column %3").arg(child->objectName()).arg(x, 0, 'f', 1).arg(samples->first, 0, 'f', 1);
                                }
                            }
                            continue;
                        }
                        walk(child);
                    }
                };
                walk(guarded);
                // The first frame off its column: the table's columns then and as first seen, so the log names the moving one.
                const QString widths = guarded->property("columnWidths").toStringList().join(QLatin1Char(','));
                if (samples->firstWidths.isEmpty())
                    samples->firstWidths = widths;
                if (offThisFrame && samples->off == 0)
                    qWarning("scroll-column-x: first off frame %lld, columns %s, first %s, spare %.1f", samples->frames, qPrintable(widths),
                             qPrintable(samples->firstWidths), guarded->property("spareWidth").toDouble());
                if (offThisFrame)
                    ++samples->off;
            }, Qt::DirectConnection);
            const auto end_of = [list] {
                return list->property("contentHeight").toDouble() - list->height() + list->property("originY").toDouble();
            };
            *swapped = connect(&window_, &QQuickWindow::frameSwapped, this, [this, list, end_of, samples, synced, swapped, turns, action] {
                // A frame queued before the last turn's disconnect still arrives: it must not go to the next action again.
                if (*turns >= 2)
                    return;
                const bool down = *turns == 0;
                const double end = down ? end_of() : list->property("originY").toDouble();
                const double at = list->property("contentY").toDouble();
                if (down ? at >= end - 0.5 : at <= end + 0.5) {
                    if (++*turns < 2) {
                        window_.update();
                        return;
                    }
                    disconnect(*synced);
                    disconnect(*swapped);
                    qWarning("scroll-column-x: %s: %lld frames, %lld cells, %lld frames with a cell off its column, worst %.1f px%s%s",
                             qPrintable(action), samples->frames, samples->cells, samples->off, samples->worst,
                             samples->where.isEmpty() ? "" : ": ", qPrintable(samples->where));
                    if (samples->cells == 0 || samples->off > 0) {
                        QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                        if (summary.open(QIODevice::Append | QIODevice::Text))
                            QTextStream(&summary) << steps_[current_].image << "\tT6:scroll-column-x\t" << action << '\t'
                                                  << (samples->cells == 0 ? QStringLiteral("no cell sampled")
                                                                          : QStringLiteral("%1 of %2 frames drew a cell off its column, worst %3 px (%4)")
                                                                                .arg(samples->off).arg(samples->frames).arg(samples->worst, 0, 'f', 1).arg(samples->where))
                                                  << '\n';
                    }
                    next_action();
                    return;
                }
                list->setProperty("contentY", down ? std::min(end, at + 120.0) : std::max(end, at - 120.0));
                window_.update();
            });
            window_.update();
            return;
        }
        // `scroll-frames:<list>`: the list scrolled to its end (or, at its end, back to its top) a fixed step per drawn
        // frame, as a steady wheel scrolls it, then the frames' intervals logged: how smoothly it scrolls.
        if (action.startsWith(QLatin1String("scroll-frames:"))) {
            auto* list = find(action.mid(QStringLiteral("scroll-frames:").size()), false);
            if (list == nullptr || list->metaObject()->indexOfProperty("contentY") < 0) {
                fail(QStringLiteral("step %1: nothing to scroll for '%2'").arg(step.image, action));
                return;
            }
            auto clock = std::make_shared<QElapsedTimer>();
            auto intervals = std::make_shared<QList<qint64>>();
            auto link = std::make_shared<QMetaObject::Connection>();
            const auto end_of = [list] {
                return list->property("contentHeight").toDouble() - list->height() + list->property("originY").toDouble();
            };
            const double from = list->property("contentY").toDouble();
            const bool down = from < end_of() - 0.5;
            clock->start();
            auto done = std::make_shared<bool>(false);
            *link = connect(&window_, &QQuickWindow::frameSwapped, this, [this, list, clock, intervals, link, end_of, down, from, done] {
                // A frame queued before the disconnect still arrives: it must not go to the next action again.
                if (*done) return;
                intervals->append(clock->restart());
                const double end = down ? end_of() : list->property("originY").toDouble();
                const double at = list->property("contentY").toDouble();
                if (down ? at >= end - 0.5 : at <= end + 0.5) {
                    *done = true;
                    disconnect(*link);
                    QList<qint64> sorted = *intervals;
                    std::sort(sorted.begin(), sorted.end());
                    const auto over = [&sorted](qint64 limit) {
                        return static_cast<long long>(std::count_if(sorted.begin(), sorted.end(), [limit](qint64 ms) { return ms > limit; }));
                    };
                    // Both ends and the travel: a list with no range reaches its end at once and is no pass.
                    qWarning("scroll-frames: %s from %.0f to %.0f (travel %.0f px), %lld frames, over 16 ms %lld, over 33 ms %lld, "
                             "over 100 ms %lld, median %lld ms, longest %lld ms",
                          down ? "down" : "up", from, at, std::abs(at - from), static_cast<long long>(sorted.size()), over(16),
                          over(33), over(100),
                          sorted.isEmpty() ? 0LL : static_cast<long long>(sorted[sorted.size() / 2]),
                          sorted.isEmpty() ? 0LL : static_cast<long long>(sorted.last()));
                    next_action();
                    return;
                }
                list->setProperty("contentY", down ? std::min(end, at + 24.0) : std::max(end, at - 24.0));
                window_.update();
            });
            window_.update();
            return;
        }
        // `hover-all:<prefix>`: the pointer rests on each shown control whose name starts with the prefix, long enough
        // for its tooltip to open; every tooltip opened that holds a long text logs its control (ToolTip.qml).
        if (action.startsWith(QLatin1String("hover-all:"))) {
            const QString prefix = action.mid(10);
            auto targets = std::make_shared<QList<QPointer<QQuickItem>>>();
            for (QQuickItem* item : window_.contentItem()->findChildren<QQuickItem*>())
                if (item->objectName().startsWith(prefix) && item->isVisible() && item->width() > 1) targets->append(item);
            const auto overlay = window_.contentItem()->parentItem();
            if (overlay != nullptr)
                for (QQuickItem* item : overlay->findChildren<QQuickItem*>())
                    if (item->objectName().startsWith(prefix) && item->isVisible() && item->width() > 1 && !targets->contains(item)) targets->append(item);
            qWarning("hover-all: %lld controls named %s*", static_cast<long long>(targets->size()), qPrintable(prefix));
            // One slot per control, scheduled at once, then the next action.
            for (qsizetype n = 0; n < targets->size(); ++n) {
                QPointer<QQuickItem> item = targets->at(n);
                QTimer::singleShot(static_cast<int>(n) * 1300, this, [this, item] {
                    if (item.isNull() || !item->isVisible()) return;
                    const QPointF at = item->mapToScene(QPointF(item->width() / 2, item->height() / 2));
                    QMouseEvent move(QEvent::MouseMove, at, window_.mapToGlobal(at), Qt::NoButton, Qt::NoButton, Qt::NoModifier);
                    QCoreApplication::sendEvent(&window_, &move);
                });
            }
            QTimer::singleShot(static_cast<int>(targets->size()) * 1300 + 300, this, [this] { next_action(); });
            return;
        }
        // `expand-frames-all`: every group of the shown sidebar tab folded, then each opened in turn as a click opens
        // it, each frame's interval and the group's height logged for 1.5 s, and folded again: an unfold is one smooth
        // animation, no frame over 33 ms and no jump in height (the owner, 2026-11-23).
        if (action == QLatin1String("expand-frames-all")) {
            auto groups = std::make_shared<QList<QPointer<QQuickItem>>>();
            // By the item tree: a page's groups are made by loaders, outside the window's object tree.
            QList<QQuickItem*> all;
            std::function<void(QQuickItem*)> gather = [&all, &gather](QQuickItem* at) {
                for (QQuickItem* child : at->childItems()) {
                    all << child;
                    gather(child);
                }
            };
            gather(window_.contentItem());
            for (QQuickItem* group : all) {
                if (!group->objectName().startsWith(QLatin1String("group."))) continue;
                if (!group->property("folding").isValid() || !group->property("collapsible").toBool() || !group->isVisible())
                    continue;
                // On the shown page (the others lie beside the window) and tab (the others are transparent).
                bool shown = true;
                for (QQuickItem* at = group; at != nullptr; at = at->parentItem()) shown = shown && at->opacity() > 0.01;
                const QRectF at = group->mapRectToScene(QRectF(0, 0, group->width(), 1));
                if (shown && at.left() >= 0 && at.right() <= window_.width() + 1) groups->append(group);
            }
            qWarning("expand-frames: %lld groups", static_cast<long long>(groups->size()));
            for (const auto& group : *groups) group->setProperty("collapsed", true);
            // One 2.4 s slot per group, scheduled at once: opened at its start, logged and folded 1.5 s later.
            constexpr int slot = 2400;
            for (qsizetype n = 0; n < groups->size(); ++n) {
                QPointer<QQuickItem> group = groups->at(n);
                QTimer::singleShot(800 + static_cast<int>(n) * slot, this, [this, group] {
                    if (group.isNull()) return;
                    auto clock = std::make_shared<QElapsedTimer>(), total = std::make_shared<QElapsedTimer>();
                    auto intervals = std::make_shared<QList<qint64>>();
                    auto heights = std::make_shared<QList<double>>();
                    auto link = std::make_shared<QMetaObject::Connection>();
                    auto done = std::make_shared<bool>(false);
                    clock->start();
                    total->start();
                    group->setProperty("collapsed", false);
                    window_.update();
                    *link = connect(&window_, &QQuickWindow::frameSwapped, this, [this, group, clock, total, intervals, heights, link, done] {
                        // A frame already queued when the connection is dropped still arrives once.
                        if (*done) return;
                        intervals->append(clock->restart());
                        heights->append(group.isNull() ? 0.0 : group->height());
                        if (total->elapsed() < 1500 && !group.isNull()) { window_.update(); return; }
                        *done = true;
                        disconnect(*link);
                        QList<qint64> sorted = *intervals;
                        std::sort(sorted.begin(), sorted.end());
                        const auto over = [&sorted](qint64 limit) {
                            return static_cast<long long>(std::count_if(sorted.begin(), sorted.end(), [limit](qint64 ms) { return ms > limit; }));
                        };
                        // A smooth unfold only grows: a frame lower than the one before is a step back; the largest
                        // single step shows a jump.
                        int backs = 0;
                        double biggest = 0;
                        for (qsizetype i = 1; i < heights->size(); ++i) {
                            const double change = heights->at(i) - heights->at(i - 1);
                            if (change < -0.5) ++backs;
                            biggest = std::max(biggest, std::abs(change));
                        }
                        qWarning("expand-frames: %s, %lld frames, first %lld ms, over 33 ms %lld, longest %lld ms, height %.0f to %.0f, "
                                 "largest step %.0f px, steps back %d",
                                 qPrintable(group.isNull() ? QStringLiteral("?") : group->objectName()), static_cast<long long>(intervals->size()),
                                 intervals->isEmpty() ? 0LL : static_cast<long long>(intervals->first()), over(33),
                                 sorted.isEmpty() ? 0LL : static_cast<long long>(sorted.last()), heights->isEmpty() ? 0.0 : heights->first(),
                                 heights->isEmpty() ? 0.0 : heights->last(), biggest, backs);
                        if (!group.isNull()) group->setProperty("collapsed", true);
                    });
                });
            }
            QTimer::singleShot(800 + static_cast<int>(groups->size()) * slot + 300, this, [this] { next_action(); });
            return;
        }
        // The frame settles before the next action: a capture-now after it then shows an animation that starts there.
        if (action == QLatin1String("wait-settled")) {
            settle_then([this] { next_action(); });
            return;
        }
        if (action == QLatin1String("tutorial-close")) {
            QQuickItem* discard = find(QStringLiteral("tutorial.discard"), true);
            const bool offered = discard != nullptr && discard->isVisible() && on_screen(discard);
            if (!click(offered ? QStringLiteral("tutorial.discard") : QStringLiteral("statusBar.tutorial.stop"))) return;
            settle_then([this] { next_action(); });
            return;
        }
        if (action == QLatin1String("tutorial-next-all")) {
            tutorial_next_then([this] { settle_then([this] { next_action(); }); });
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
        // The scan files read so far, for the desk check of edi ADR-0102 rule 6: the total, the reads since the last
        // count, and the views' demand with how much of it is unread.
        if (action.startsWith(QLatin1String("count-scan-reads:"))) {
            static long long last = 0, last_list = 0;
            const long long now = scanFileReads().load(), list = listFileReads().load();
            ScanViewModel* model = nullptr;
            for (const QString& mode : {QStringLiteral("map"), QStringLiteral("stacked")}) {
                QQuickItem* layer = find(QStringLiteral("scanView.%1.layer").arg(mode), false);
                if (layer != nullptr && model == nullptr) model = layer->property("model").value<ScanViewModel*>();
            }
            qWarning("scan reads %s: views %lld total, %lld since the last count; demand %d, unread %d; lists %lld since the "
                     "last count", qPrintable(action.mid(17)), now, now - last, model ? model->demandSize() : -1,
                     model ? model->unreadDemanded() : -1, list - last_list);
            last = now;
            last_list = list;
            next_action();
            return;
        }
        if (action.startsWith(QLatin1String("wait-scan:"))) {
            wait_scan_then([this] { next_action(); }, action.mid(10));
            return;
        }
        // A running fit's iteration, for a capture made while it runs (capture-now).
        if (action.startsWith(QLatin1String("wait-iteration:"))) {
            wait_iteration_then([this] { next_action(); }, action.mid(15).toInt());
            return;
        }
        // The assistant answers at its own pace; the step waits until it has stopped working.
        if (action == QLatin1String("wait-assistant")) {
            wait_assistant_then([this] { settle_then([this] { next_action(); }); });
            return;
        }
        // A From web search or load runs on the network; the dialog says when it is done.
        if (action == QLatin1String("wait-online")) {
            wait_online_then([this] { settle_then([this] { next_action(); }); });
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
        const bool tab_button = (action.startsWith(QLatin1String("mainArea.")) && action.contains(QLatin1String(".tab."))) ||
                                action.startsWith(QLatin1String("sideBar.tab."));
        const bool issues = !step.trace.isEmpty() && (action.startsWith(QLatin1String("appBar.tab.")) ||
                                                      action.startsWith(QLatin1String("mainArea.blocks.")) ||
                                                      action == QLatin1String("statusBar.fit.button") || tab_button ||
                                                      action.startsWith(QLatin1String("unfold:")));
        if (issues) trace_issue(action);
        if (!perform(action)) {
            return;  // fail() has ended the run
        }
        if (issues && step.navigation != 0) {
            trace_issued(step);
            // The press is the step: the next one follows on its schedule, with no capture or wait in between.
            ++current_;
            run_step();
            return;
        }
        // A hover is what the step shows, so its pointer stays.
        if (!action.startsWith(QLatin1String("hover:"))) {
            park_pointer();
        }
        // What the action opened is drawn before the next; a step captured unsettled does not wait for it, nor
        // does an action a wait follows (a fit keeps the window changing until it ends).
        const bool waits = action_ < step.actions.size() && step.actions.at(action_).startsWith(QLatin1String("wait-"));
        // A capture-at right after the action times itself from the action.
        const bool captures = action_ < step.actions.size() && step.actions.at(action_).startsWith(QLatin1String("capture-at:"));
        if (unsettled || waits) {
            QTimer::singleShot(captures ? 0 : kSettleIntervalMs, this, [this] { next_action(); });
        } else {
            settle_then([this] { next_action(); });
        }
        return;
    }
    const auto save = [this] {
        // EDI_DEMO_NO_IMAGES: the checks alone, no frame saved (a long width series).
        if (!steps_[current_].capture || qEnvironmentVariableIsSet("EDI_DEMO_NO_IMAGES")) {
            ++current_;
            run_step();
            return;
        }
        // Every documentation screenshot is WebP at quality 85 (owner record 2026-11-10); other captures stay PNG.
        const bool webp = documentation_;
        const QString path = output_dir_.filePath(steps_[current_].image + (webp ? QStringLiteral(".webp") : QStringLiteral(".png")));
        // While traced, the image is written on a worker, so writing it is not the GUI thread's work.
        bool saved = true;
#if EDI_UI_INSTRUMENTATION
        if (ui_trace_on() && !webp) {
            // A copy of its own: the worker never shares image data with the GUI thread, which frees and replaces
            // previous_frame_ while the image is written.
            run_in_background([image = previous_frame_.copy(), path] { image.save(path); });
        } else
#endif
        {
            saved = webp ? previous_frame_.save(path, "WEBP", 85) : previous_frame_.save(path);
        }
        if (!saved) {
            fail(QStringLiteral("cannot write %1").arg(path));
            return;
        }
        if (documentation_) {
            QString error;
            if (!saveDocumentationFrame(path, &error)) {
                fail(error);
                return;
            }
        }
        ++current_;
        run_step();
    };
    if (unsettled) {
        QTimer::singleShot(unsettled_ms, this, [this, save] {
            previous_frame_ = grab();
            save();
        });
        return;
    }
    settle_then(save);
}

bool DemoDriver::tutorial_fit_check(QObject* panel, int step) {
    const TutorialStep current = panel->property("current").value<TutorialStep>();
    QQmlEngine* engine = qmlEngine(window_.contentItem());
    auto* session = engine != nullptr ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
    ProjectViewModel* project = session != nullptr ? session->project() : nullptr;
    if (step_checked_ != step) {
        step_checked_ = step;
        QStringList problems;
        // The title fits the popup's line (owner record 2026-11-11, item 10).
        if (QQuickItem* title = find(QStringLiteral("tutorial.title"), false); title != nullptr && title->property("truncated").toBool())
            problems << QStringLiteral("the title \"%1\" is cut short").arg(current.title);
        // No menu a step opened is left open when the next step starts, unless that step chooses in it.
        static const QStringList choosing{QStringLiteral("free-choice"), QStringLiteral("web-dialog"), QStringLiteral("menu-closed")};
        const bool chooses = std::any_of(choosing.cbegin(), choosing.cend(), [&current](const QString& kind) { return current.check.startsWith(kind); });
        for (QQuickItem* layer : window_.contentItem()->childItems()) {
            if (qstrcmp(layer->metaObject()->className(), "QQuickOverlay") != 0) continue;
            for (QQuickItem* item : layer->childItems()) {
                QObject* popup = item->parent();
                if (!chooses && popup != nullptr && popup->inherits("QQuickMenu") && popup->property("opened").toBool())
                    problems << QStringLiteral("a menu (%1) is still open").arg(popup->objectName().isEmpty() ? QString::fromLatin1(popup->metaObject()->className()) : popup->objectName());
            }
        }
        // A Free tick asks for a click that changes the box, and names the row as the table does.
        if (const auto tick = QRegularExpression(QStringLiteral("^(un)?tick:(.+)$")).match(current.check); tick.hasMatch() && project != nullptr) {
            if (panel->property("heldAtStart").toBool())
                problems << QStringLiteral("its Free box is already as the step asks");
            ParameterTableModel* table = project->parameters();
            const int parameter_role = table->roleNames().key("parameter"), path_role = table->roleNames().key("path");
            static const QRegularExpression bracket(QStringLiteral("\\[([^\\]]*)\\]"));
            for (int row = 0; row < table->rowCount(); ++row) {
                QString dotted = table->data(table->index(row, 0), path_role).toString();
                dotted.replace(bracket, QStringLiteral(".\\1"));
                if (dotted != tick.captured(2)) continue;
                const QObject* item = table->data(table->index(row, 0), parameter_role).value<QObject*>();
                const QString label = item->property("rowLabel").toString(), name = item->property("shortName").toString();
                const QString shown = label.isEmpty() ? name : label + u' ' + name;
                if (!current.text.contains(QStringLiteral("**%1**").arg(shown)))
                    problems << QStringLiteral("it names the row otherwise than the table's \"%1\"").arg(shown);
            }
        }
        for (const QString& problem : problems) {
            const QString text = QStringLiteral("step %1 (%2): %3").arg(step + 1).arg(current.title, problem);
            if (!qEnvironmentVariableIsSet("EDI_DEMO_REPORT_ONLY")) {
                fail(text);
                return false;
            }
            std::fprintf(stderr, "edi_app --demo: MISMATCH %s\n", qPrintable(text));
        }
    }
    if (!current.expectSites.isEmpty() && sites_reported_ != step && project != nullptr) {
        // A structure the tutorial built ends with the case's own sites: label, element and position.
        sites_reported_ = step;
        QStringList built;
        for (const auto& structure : project->project().structures)
            for (const auto& site : structure->atom_sites)
                built << QStringLiteral("%1 %2 %3 %4 %5")
                             .arg(QString::fromStdString(site->id.value()), QString::fromStdString(site->type_symbol.value()))
                             .arg(site->fract_x.value.get(), 0, 'f', 4)
                             .arg(site->fract_y.value.get(), 0, 'f', 4)
                             .arg(site->fract_z.value.get(), 0, 'f', 4);
        if (built != current.expectSites) {
            const QString problem = QStringLiteral("%1: the structure's sites are %2, not the case's %3")
                                        .arg(current.title, built.join(u", "), current.expectSites.join(u", "));
            if (!qEnvironmentVariableIsSet("EDI_DEMO_REPORT_ONLY")) {
                fail(problem);
                return false;
            }
            std::fprintf(stderr, "edi_app --demo: MISMATCH %s\n", qPrintable(problem));
        }
    }
    if (current.check != QLatin1String("fit-done")) return true;
    FitViewModel* fit = project != nullptr ? project->fit() : nullptr;
    if (project == nullptr || fit == nullptr) return true;
    const QString title = current.title;
    if (fit_free_reported_ != step && !fit->running()) {
        // Before Next presses Fit: the parameters the stage's steps left free.
        ParameterTableModel* table = project->parameters();
        const auto roles = table->roleNames();
        const int path_role = roles.key("path"), free_role = roles.key("free");
        QStringList free;
        for (int row = 0; row < table->rowCount(); ++row)
            if (table->data(table->index(row, 0), free_role).toBool()) free << table->data(table->index(row, 0), path_role).toString();
        free.sort();
        std::fprintf(stderr, "edi_app --demo: %s: %d free before the fit: %s\n", qPrintable(title), static_cast<int>(free.size()),
                     qPrintable(free.join(u' ')));
        fit_free_reported_ = step;
        fit_seen_running_ = false;
        if (const QString keep = qEnvironmentVariable("EDI_DEMO_KEEP_FIT_PROJECTS"); !keep.isEmpty()) {
            const QString id = panel->property("tutorial").value<Tutorial>().id;
            try { edi::save_project(project->project(), (keep + QStringLiteral("/%1-step-%2").arg(id).arg(step + 1)).toStdString()); }
            catch (const std::exception& error) { std::fprintf(stderr, "keep project: %s\n", error.what()); }
        }
        if (!current.expectFree.isEmpty()) {
            // A background freed whole is checked by every one of its points being free: the app and the
            // command line may label re-estimated points differently.
            const auto whole = [&current](const QString& name) {
                return std::any_of(current.expectWholeBackground.cbegin(), current.expectWholeBackground.cend(),
                                   [&name](const QString& prefix) { return name.startsWith(prefix); });
            };
            QStringList wanted;
            for (const QString& name : current.expectFree) if (!whole(name)) wanted << name;
            for (int row = 0; row < table->rowCount(); ++row) {
                const QString name = table->data(table->index(row, 0), path_role).toString();
                if (whole(name) && name.endsWith(QStringLiteral(".intensity"))) wanted << name;
            }
            wanted.sort();
            if (std::any_of(wanted.cbegin(), wanted.cend(), [&free](const QString& name) { return !free.contains(name); }) ||
                std::any_of(free.cbegin(), free.cend(), [&](const QString& name) {
                    return !wanted.contains(name) &&
                           std::none_of(current.expectWholeBackground.cbegin(), current.expectWholeBackground.cend(),
                                        [&name](const QString& prefix) { return name.startsWith(prefix); });
                })) {
                QStringList missing, extra;
                for (const QString& name : wanted) if (!free.contains(name)) missing << name;
                for (const QString& name : free) {
                    const bool outside = std::any_of(current.expectWholeBackground.cbegin(), current.expectWholeBackground.cend(),
                                                     [&name](const QString& prefix) { return name.startsWith(prefix); });
                    if (!wanted.contains(name) && !outside) extra << name;
                }
                const QString problem = QStringLiteral("%1: the free set differs from the stage's: missing %2; extra %3")
                                            .arg(title, missing.join(u' '), extra.join(u' '));
                // EDI_DEMO_REPORT_ONLY: list every mismatch of a replay instead of stopping at the first.
                if (!qEnvironmentVariableIsSet("EDI_DEMO_REPORT_ONLY")) {
                    fail(problem);
                    return false;
                }
                std::fprintf(stderr, "edi_app --demo: MISMATCH %s\n", qPrintable(problem));
            }
        }
    }
    if (fit->running()) fit_seen_running_ = true;
    if (fit_seen_running_ && !fit->running() && fit_result_reported_ != step && !fit->outcome().isEmpty()) {
        std::fprintf(stderr, "edi_app --demo: %s: %s after %s iterations, reduced chi2 %s, %s\n", qPrintable(title),
                     qPrintable(fit->outcome()), qPrintable(fit->iterations()), qPrintable(fit->goodnessOfFit()),
                     qPrintable(fit->elapsed()));
        fit_result_reported_ = step;
        if (current.expectChi2 >= 0) {
            const double pin = current.expectChi2;
            bool ok = false;
            // "35.86 → 9.88" or "1.19×10³ → 1.06×10³": the value the fit ended at is the last. A value shown with
            // a power of ten carries three significant digits, so it matches within half its last digit.
            static const QRegularExpression last(QStringLiteral(
                "([0-9]+)(?:\\.([0-9]+))?(?:\u00D710([\u207B]?)([\u2070\u00B9\u00B2\u00B3\u2074-\u2079]+))?\\D*$"));
            const auto match = last.match(fit->goodnessOfFit());
            double chi2 = 0.0;
            double tolerance = current.expectChi2Tolerance;
            if (match.hasMatch()) {
                const QString decimals = match.captured(2);
                chi2 = (match.captured(1) + u'.' + (decimals.isEmpty() ? QStringLiteral("0") : decimals)).toDouble(&ok);
                if (!match.captured(4).isEmpty()) {
                    static const QString digits = QStringLiteral("\u2070\u00B9\u00B2\u00B3\u2074\u2075\u2076\u2077\u2078\u2079");
                    int power = 0;
                    for (const QChar digit : match.captured(4)) power = power * 10 + static_cast<int>(digits.indexOf(digit));
                    if (!match.captured(3).isEmpty()) power = -power;
                    chi2 *= std::pow(10.0, power);
                    tolerance = std::max(tolerance, 0.5 * std::pow(10.0, power - static_cast<int>(decimals.size())));
                }
            }
            if (!ok || std::abs(chi2 - pin) > tolerance) {
                const QString problem = QStringLiteral("%1: reduced chi2 %2, not the pinned %3").arg(title, fit->goodnessOfFit()).arg(pin);
                if (!qEnvironmentVariableIsSet("EDI_DEMO_REPORT_ONLY")) {
                    fail(problem);
                    return false;
                }
                std::fprintf(stderr, "edi_app --demo: MISMATCH %s\n", qPrintable(problem));
            }
        }
    }
    return true;
}

void DemoDriver::tutorial_next_then(const std::function<void()>& next, int step, int waited_ms, int clicked_ms) {
    // A step that waits for a fit, a download or a save keeps Next off meanwhile; one that stays off this long cannot
    // be left by Next alone.
    constexpr int kPollMs = 250;
    constexpr int kStuckMs = 240000;
    QObject* panel = window_.findChild<QObject*>(QStringLiteral("tutorialPanel"));
    if (panel == nullptr || panel->property("tutorial").isNull()) {
        fail(QStringLiteral("step %1: no tutorial is running").arg(steps_[current_].image));
        return;
    }
    const int now = panel->property("step").toInt();
    const auto count = static_cast<int>(panel->property("steps").toList().size());
    const QVariant chosen = panel->property("tutorial");
    QString id = chosen.value<Tutorial>().id;
    if (id.isEmpty()) id = chosen.toMap().value(QStringLiteral("id")).toString();
    if (step >= 0 && now < step) {
        // Next alone must only go forward; a tutorial that steps back loops.
        fail(QStringLiteral("tutorial %1 went back from step %2 to %3 with only Next").arg(id).arg(step + 1).arg(now + 1));
        return;
    }
    if (now != step) {
        step = now;
        waited_ms = 0;
        clicked_ms = -1;
        std::fprintf(stderr, "edi_app --demo: tutorial %s at step %d of %d\n", qPrintable(id), now + 1, count);
        if (qEnvironmentVariableIsSet("EDI_DEMO_TRACE_LABELS")) {
            std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
                for (QQuickItem* child : parent->childItems()) {
                    if (child->objectName().startsWith(QLatin1String("atomSite.label.")) && child->isVisible())
                        std::fprintf(stderr, "trace step %d: %s text=%s y=%.0f\n", now + 1, qPrintable(child->objectName()),
                                     qPrintable(child->property("text").toString()), child->mapToScene(QPointF()).y());
                    walk(child);
                }
            };
            walk(window_.contentItem());
        }
    }
    // EDI_DEMO_STEP_SHOTS=<folder>: every step as it shows, once its callout has settled, into <folder>/<tutorial>/
    // as NNN.png, with steps.txt listing each step's number, title and text (the owner's capture-and-review loop,
    // 2026-11-11). Taken before Next is pressed; the step waits for it.
    if (const QString shots = qEnvironmentVariable("EDI_DEMO_STEP_SHOTS"); !shots.isEmpty() && shot_step_ != now) {
        // Still fading in or out (its opacity animates), or still finding its control.
        bool moving = panel->property("settling").toBool() || panel->property("revealing").toBool() ||
                      panel->property("opacity").toDouble() < 0.99;
        // A page still being built (the app bar's "Preparing this page…") is not the step's view yet.
        for (const char* tab : {"appBar.tab.project", "appBar.tab.structure", "appBar.tab.experiment", "appBar.tab.analysis", "appBar.tab.report"})
            if (QQuickItem* item = find(QString::fromLatin1(tab), false); item != nullptr && item->property("preparing").toBool()) moving = true;
        if (waited_ms < 1500 || (moving && waited_ms < 30000)) {
            QTimer::singleShot(kPollMs, this, [this, next, step, waited_ms, clicked_ms] { tutorial_next_then(next, step, waited_ms + kPollMs, clicked_ms); });
            return;
        }
        const TutorialStep shown = panel->property("current").value<TutorialStep>();
        QDir folder(shots);
        folder.mkpath(id);
        folder.cd(id);
        grab().save(folder.filePath(QStringLiteral("%1.png").arg(now + 1, 3, 10, QLatin1Char('0'))));
        if (QFile list(folder.filePath(QStringLiteral("steps.txt"))); list.open(QIODevice::Append | QIODevice::Text))
            list.write(QStringLiteral("%1\t%2\t%3\n").arg(now + 1, 3, 10, QLatin1Char('0')).arg(shown.title, shown.text).toUtf8());
        shot_step_ = now;
    }
    if (panel->property("atEnd").toBool()) {
        // Steps that were already done when the tutorial came to them: each asks for a click that changes nothing.
        // EDI_DEMO_NOOPS=<file> collects them as "<tutorial><tab><check>" for the generator to drop.
        const QStringList done = panel->property("doneOnArrival").toStringList();
        for (const QString& entry : done) {
            const QString check = entry.section(u'\t', 1);
            if (const QString file = qEnvironmentVariable("EDI_DEMO_NOOPS"); !file.isEmpty())
                if (QFile out(file); out.open(QIODevice::Append | QIODevice::Text)) out.write((id + u'\t' + check + u'\n').toUtf8());
            const QString text = QStringLiteral("tutorial %1 step %2 (%3) was already done when it came").arg(id, entry.section(u'\t', 0, 0), check);
            if (!qEnvironmentVariableIsSet("EDI_DEMO_REPORT_ONLY")) {
                fail(text);
                return;
            }
            std::fprintf(stderr, "edi_app --demo: MISMATCH %s\n", qPrintable(text));
        }
        qInfo().noquote() << QStringLiteral("edi_app --demo: tutorial %1: reached step %2 of %3 by Next alone")
                                 .arg(id).arg(now + 1).arg(count);
        next();
        return;
    }
    if (!tutorial_fit_check(panel, now)) return;
    QQuickItem* button = find(QStringLiteral("statusBar.tutorial.next"), false);
    const bool clickable = button != nullptr && button->isVisible() && button->isEnabled() &&
                           button->property("clickable").toBool() && on_screen(button);
    // One press per step, again only if the step has not moved a while after it.
    if (clickable && (clicked_ms < 0 || waited_ms - clicked_ms > 3000)) {
        click_item(button);
        clicked_ms = waited_ms;
    }
    if (waited_ms > kStuckMs) {
        // The window as it stands, beside the run's captures, to show where the tutorial stopped.
        grab().save(output_dir_.filePath(steps_[current_].image + QStringLiteral("-stuck.png")));
        fail(QStringLiteral("step %1: tutorial %2 stays at step %3 of %4: Next %5")
                 .arg(steps_[current_].image, id).arg(now + 1).arg(count)
                 .arg(clickable ? QStringLiteral("does not advance it") : QStringLiteral("is off")));
        return;
    }
    QTimer::singleShot(kPollMs, this, [this, next, step, waited_ms, clicked_ms] {
        tutorial_next_then(next, step, waited_ms + kPollMs, clicked_ms);
    });
}

void DemoDriver::wait_fit_then(const std::function<void()>& next, int waited_ms, int files) {
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

void DemoDriver::wait_iteration_then(const std::function<void()>& next, int iteration, int waited_ms) {
    QQmlEngine* engine = qmlEngine(window_.contentItem());
    auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
    const FitViewModel* fit = session != nullptr && session->project() != nullptr ? session->project()->fit() : nullptr;
    if (fit == nullptr || !fit->running() || fit->iterations().toInt() >= iteration) {
        next();
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the fit did not reach iteration %2 within %3 ms")
                 .arg(steps_[current_].image)
                 .arg(iteration)
                 .arg(kFitWaitMs));
        return;
    }
    QTimer::singleShot(kSettleIntervalMs, this, [this, next, iteration, waited_ms] {
        wait_iteration_then(next, iteration, waited_ms + kSettleIntervalMs);
    });
}

bool DemoDriver::perform(const QString& action) {
    if (documentation_) {
        if (auto handled = documentationAction(action)) return *handled;
    }
    // `uncover:` reveals a control only when none of it can be seen, so a page where it shows is captured as it is.
    // A control clicked only when it is there and enabled (a chart tab a running fit has not enabled yet): otherwise
    // the step goes on without it.
    if (action.startsWith(QLatin1String("if-enabled:"))) {
        QQuickItem* item = find(action.mid(11), false);
        if (item == nullptr || !item->isEnabled() || !item->isVisible()) {
            return true;
        }
        return perform(action.mid(11));
    }
    if (action.startsWith(QLatin1String("uncover:"))) {
        QQuickItem* item = find(action.mid(8), false);
        if (item != nullptr && on_screen(item)) {
            return true;
        }
        return perform(QStringLiteral("reveal:") + action.mid(8));
    }
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
        // `show:<view>:<row>:begin` puts the row at the top, whole, where Contain can leave it clipped.
        const int mode = parts.value(3) == QLatin1String("begin") ? 0 /* ListView.Beginning */ : 1 /* ListView.Contain */;
        QMetaObject::invokeMethod(view, "positionViewAtIndex", Q_ARG(int, parts.value(2).toInt()), Q_ARG(int, mode));
        return true;
    }
    if (action.startsWith(QLatin1String("choose:"))) {
        // The open popup's entry: a visible, enabled button-like item showing the text, or the text and a count in
        // brackets, as the parameter table's category filter lists "Background (10)".
        // A lower-case option token also finds its label, which starts with a capital (the label rule).
        const QString given = action.mid(7);
        const QString capital = given.isEmpty() ? given : given.left(1).toUpper() + given.mid(1);
        const auto shows = [&given, &capital](const QString& text) {
            for (const QString& wanted : {given, capital}) {
                if (text == wanted || (text.startsWith(wanted + QStringLiteral(" (")) && text.endsWith(QLatin1Char(')'))))
                    return true;
            }
            return false;
        };
        QList<QQuickItem*> candidates;
        std::function<void(QQuickItem*)> walk = [&](QQuickItem* parent) {
            for (QQuickItem* child : parent->childItems()) {
                if (child->isVisible() && child->isEnabled() && shows(child->property("text").toString()) &&
                    child->metaObject()->indexOfSignal("clicked()") >= 0) {
                    candidates.append(child);
                }
                walk(child);
            }
        };
        walk(window_.contentItem()->parentItem() != nullptr ? window_.contentItem()->parentItem()
                                                            : window_.contentItem());
        if (candidates.isEmpty()) {
            fail(QStringLiteral("step %1: no open entry shows '%2'").arg(steps_[current_].image, given));
            return false;
        }
        return click_item(candidates.last());
    }
    // `set:<name>:<property>=<value>`: an item's property set as a state to capture (a form's answer from a service
    // the demo does not reach).
    if (action.startsWith(QLatin1String("set:"))) {
        const QString rest = action.mid(4);
        // A dialog is a popup, not an item: looked for among every object.
        QObject* item = window_.contentItem()->findChild<QObject*>(rest.section(QLatin1Char(':'), 0, 0));
        if (item == nullptr && window_.contentItem()->parentItem() != nullptr)
            item = window_.contentItem()->parentItem()->findChild<QObject*>(rest.section(QLatin1Char(':'), 0, 0));
        const QString assignment = rest.section(QLatin1Char(':'), 1);
        if (item == nullptr || !assignment.contains(QLatin1Char('=')) ||
            !item->setProperty(qPrintable(assignment.section(QLatin1Char('='), 0, 0)), assignment.section(QLatin1Char('='), 1))) {
            fail(QStringLiteral("step %1: cannot %2").arg(steps_[current_].image, action));
            return false;
        }
        return true;
    }
    // `legend-hide-all:<chart>`: every entry of the chart's legend switched off, as clicks on each would; then
    // `check-hidden-series:<chart>` notes every series of that chart still drawing points (the owner, 2026-11-23: the
    // magnetic contribution stayed drawn with its entry off).
    if (action.startsWith(QLatin1String("legend-hide-all:")) || action.startsWith(QLatin1String("check-hidden-series:"))) {
        const QString name = action.section(QLatin1Char(':'), 1);
        QQuickItem* chart = find(name, true);
        QObject* controller = nullptr;
        if (chart != nullptr)
            for (QObject* child : chart->findChildren<QObject*>())
                if (QString::fromLatin1(child->metaObject()->className()).contains(QLatin1String("PatternChartController"))) { controller = child; break; }
        if (controller == nullptr) {
            fail(QStringLiteral("step %1: no chart controller for %2").arg(steps_[current_].image, action));
            return false;
        }
        if (action.startsWith(QLatin1String("legend-hide-all:"))) {
            QMetaObject::invokeMethod(controller, "hideAllButMeasured");
            QMetaObject::invokeMethod(controller, "toggleSeries", Q_ARG(QString, QStringLiteral("meas")));
            return true;
        }
        QFile file(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
        if (file.open(QIODevice::Append | QIODevice::Text)) {
            QTextStream out(&file);
            out << steps_[current_].image << "\tC2:checked\tchart\tevery series with its legend entry off\n";
            int drawn = 0;
            const auto finitePoints = [](const QXYSeries* series) {
                int finite = 0;
                for (const QPointF& point : series != nullptr ? series->points() : QList<QPointF>{})
                    finite += std::isfinite(point.x()) && std::isfinite(point.y()) ? 1 : 0;
                return finite;
            };
            // The filled kinds too (the measured and residual bands, a single crystal's bars, the structure curves): an
            // area draws its fill and border from its two edge lines, which are judged with it.
            QSet<const QXYSeries*> edges;
            for (QAreaSeries* area : chart->findChildren<QAreaSeries*>()) {
                edges << area->upperSeries() << area->lowerSeries();
                const int finite = finitePoints(area->upperSeries());
                const bool painted = area->color().alpha() > 0 || (area->borderColor().alpha() > 0 && area->borderWidth() > 0);
                if (area->isVisible() && painted && finite > 1) {
                    out << steps_[current_].image << "\tC2:legend-hidden-drawn\t" << area->objectName() << " area " << area->name() << '\t' << finite << " points\n";
                    ++drawn;
                }
            }
            for (QXYSeries* series : chart->findChildren<QXYSeries*>()) {
                if (edges.contains(series)) continue;
                const int finite = finitePoints(series);
                if (series->isVisible() && finite > 1) {
                    out << steps_[current_].image << "\tC2:legend-hidden-drawn\t" << series->objectName() << ' ' << series->name() << '\t' << finite << " points\n";
                    ++drawn;
                }
            }
            qWarning("check-hidden-series: %d series still drawn", drawn);
        }
        return true;
    }
    // `check-report-figures-saved`: the last report save was given a figure for every evolution chart, structure and
    // pattern of the preview's model (the owner, 2026-11-23: a PDF saved right after the first show must hold them).
    if (action == QLatin1String("check-report-figures-saved") || action.startsWith(QLatin1String("check-report-figures-saved:"))) {
        QObject* report = nullptr;
        for (QObject* object : window_.contentItem()->findChildren<QObject*>())
            if (QString::fromLatin1(object->metaObject()->className()).contains(QLatin1String("ReportViewModel"))) { report = object; break; }
        if (report == nullptr)
            if (QQuickItem* preview = find(QStringLiteral("report.preview"), false); preview != nullptr)
                report = preview->property("report").value<QObject*>();
        if (report == nullptr) {
            fail(QStringLiteral("step %1: no report view model").arg(steps_[current_].image));
            return false;
        }
        const QStringList saved = report->property("lastSavedFigures").toStringList();
        // A save asked for while the report was still building is made once it is built: waited for, up to 20 s.
        const int waited = action.section(QLatin1Char(':'), 1).toInt();
        if (saved.isEmpty() && waited < 20000) {
            --action_;
            steps_[current_].actions[action_] = QStringLiteral("check-report-figures-saved:%1").arg(waited + 250);
            QTimer::singleShot(250, this, [this] { next_action(); });
            return false;
        }
        const QVariantMap model = report->property("model").toMap();
        const qsizetype evolution = model.value(QStringLiteral("evolution")).toList().size();
        qsizetype savedEvolution = 0;
        for (const QString& name : saved) savedEvolution += name.startsWith(QLatin1String("evolution-")) ? 1 : 0;
        qWarning("check-report-figures-saved: %lld figures saved (%lld evolution of %lld): %s", static_cast<long long>(saved.size()),
                 static_cast<long long>(savedEvolution), static_cast<long long>(evolution), qPrintable(saved.join(QLatin1Char(' '))));
        QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
        if (savedEvolution < evolution && summary.open(QIODevice::Append | QIODevice::Text))
            QTextStream(&summary) << steps_[current_].image << "\treport-figures-missing\t" << savedEvolution << " of " << evolution << " evolution charts\n";
        return true;
    }
    // `note-sidebar:<key>` keeps the sidebar's width under a key; `check-sidebar:<key>` notes "sidebar-moved" when the
    // width now differs from it by more than a pixel (the owner, 2026-11-23: Full one width on every page, and no
    // width moved by a fit).
    if (action.startsWith(QLatin1String("note-sidebar:")) || action.startsWith(QLatin1String("check-sidebar:"))) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        QObject* sizes = engine != nullptr ? engine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
        const double width = sizes != nullptr ? sizes->property("sideBarWidth").toDouble() : -1.0;
        const QString key = action.section(QLatin1Char(':'), 1);
        qWarning("%s %s %.0f", action.startsWith(QLatin1String("note-sidebar:")) ? "note-sidebar" : "check-sidebar", qPrintable(key), width);
        if (action.startsWith(QLatin1String("note-sidebar:"))) {
            sidebar_widths_[key] = width;
            return true;
        }
        // Widths are whole pixels: any difference is a move (the owner's case 59: 0 px).
        if (sidebar_widths_.contains(key) && std::abs(sidebar_widths_.value(key) - width) > 0.5) {
            QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
            if (summary.open(QIODevice::Append | QIODevice::Text))
                QTextStream(&summary) << steps_[current_].image << (key.startsWith(QLatin1String("full")) ? "\tW2:sidebar-moved\t" : "\tW1:sidebar-moved\t") << key << '\t' << sidebar_widths_.value(key) << " -> " << width << '\n';
        }
        return true;
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
    // `list-end:<list>`: a list scrolled to its last row (the sweep's Examples frame, the owner, 2026-11-22).
    if (action.startsWith(QLatin1String("list-top:"))) {
        // At its top, checked: a frame named the top is one whose list is there.
        QQuickItem* view = find(action.mid(9), false);
        if (view == nullptr || !QMetaObject::invokeMethod(view, "positionViewAtBeginning") ||
            std::abs(view->property("contentY").toDouble() - view->property("originY").toDouble()) > 0.5) {
            fail(QStringLiteral("step %1: cannot scroll '%2' to its top").arg(steps_[current_].image, action.mid(9)));
            return false;
        }
        return true;
    }
    if (action.startsWith(QLatin1String("list-end:"))) {
        QQuickItem* view = find(action.mid(9), false);
        if (view == nullptr || !QMetaObject::invokeMethod(view, "positionViewAtEnd")) {
            fail(QStringLiteral("step %1: cannot scroll '%2' to its end").arg(steps_[current_].image, action.mid(9)));
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
    // `zoom-rows:<mode>`: the scan chart's y range halved around its middle, as a vertical zoom (the Stacked caption follows).
    if (action.startsWith(QLatin1String("zoom-rows:"))) {
        const QString mode = action.mid(QStringLiteral("zoom-rows:").size());
        QQuickItem* chart = find(QStringLiteral("scanView.") + mode, false);
        QQuickItem* layer = find(QStringLiteral("scanView.%1.layer").arg(mode), false);
        const double low = layer != nullptr ? layer->property("yMin").toDouble() : 0.0;
        const double high = layer != nullptr ? layer->property("yMax").toDouble() : 0.0;
        if (chart == nullptr || !(high > low) ||
            !QMetaObject::invokeMethod(chart, "setZoom", Q_ARG(QVariant, QVariant(QVariantList{})),
                                       Q_ARG(QVariant, QVariant(QVariantList{low + (high - low) / 4, high - (high - low) / 4})))) {
            fail(QStringLiteral("step %1: cannot zoom the %2 rows").arg(steps_[current_].image, mode));
            return false;
        }
        return true;
    }
    // `assert-table:<name>`: the table has rows and at least two columns with a width, as a table shown after its group
    // was opened must (a table made inside a folded group used to open as a blank strip).
    if (action.startsWith(QLatin1String("assert-table:"))) {
        const QString name = action.mid(QStringLiteral("assert-table:").size());
        QQuickItem* table = find(name, false);
        const int rows = table != nullptr ? table->property("count").toInt() : 0;
        int sized = 0;
        if (table != nullptr) {
            for (const QVariant& width : table->property("columnWidths").toList()) {
                sized += width.toDouble() > 1.0 ? 1 : 0;
            }
        }
        if (rows <= 0 || sized < 2) {
            fail(QStringLiteral("step %1: table '%2' shows %3 rows and %4 sized columns")
                     .arg(steps_[current_].image, name)
                     .arg(rows)
                     .arg(sized));
            return false;
        }
        return true;
    }
    // `assert-report-figures`: every figure of the report preview holds what the project does (figureGaps()).
    if (action == QLatin1String("assert-report-figures")) {
        QQuickItem* preview = find(QStringLiteral("report.preview"), false);
        QObject* report = preview != nullptr ? preview->property("report").value<QObject*>() : nullptr;
        QStringList gaps;
        if (report == nullptr || !QMetaObject::invokeMethod(report, "figureGaps", Q_RETURN_ARG(QStringList, gaps))) {
            fail(QStringLiteral("step %1: no report preview to check").arg(steps_[current_].image));
            return false;
        }
        if (!gaps.isEmpty()) {
            fail(QStringLiteral("step %1: report figures miss series: %2").arg(steps_[current_].image, gaps.join("; ")));
            return false;
        }
        return true;
    }
    // `ask-series:<folder>`: the datasets dialog for the folder's files as a series of joint fits.
    if (action.startsWith(QLatin1String("ask-series:"))) {
        const QDir folder(action.mid(QStringLiteral("ask-series:").size()));
        QVariantList files;
        for (const QString& name : folder.entryList(QDir::Files, QDir::Name)) {
            files.append(QUrl::fromLocalFile(folder.filePath(name)));
        }
        QQuickItem* group = find(QStringLiteral("group.experiments"), false);
        if (group == nullptr || files.isEmpty() ||
            !QMetaObject::invokeMethod(group, "askSeries", Q_ARG(QVariant, QVariant(files)))) {
            fail(QStringLiteral("step %1: no series dialog for %2").arg(steps_[current_].image, folder.path()));
            return false;
        }
        return true;
    }
    // `measured-only`: the shown pattern chart with every curve but the measured data hidden, as legend clicks hide them.
    if (action == QLatin1String("measured-only")) {
        QQuickItem* chart = find(QStringLiteral("chart"), false);
        if (chart == nullptr || !QMetaObject::invokeMethod(chart, "hideAllButMeasured")) {
            fail(QStringLiteral("step %1: no pattern chart to show measured data only").arg(steps_[current_].image));
            return false;
        }
        return true;
    }
    // `save-image:<button>|<file>[|<scale>]`: the shown Save image button's image, saved into the output folder as Save image
    // saves it (the toolbar left out), for documentation figures.
    if (action.startsWith(QLatin1String("save-image:"))) {
        const QString button = action.mid(11).section(QLatin1Char('|'), 0, 0);
        const QString file = action.section(QLatin1Char('|'), 1, 1);
        // An optional third part renders it that many times as large (documentation figures at twice the size).
        const double scale = action.section(QLatin1Char('|'), 2).isEmpty() ? 1.0 : action.section(QLatin1Char('|'), 2).toDouble();
        QQuickItem* item = find(button, false);
        if (item == nullptr || file.isEmpty() || scale <= 0.0 ||
            !QMetaObject::invokeMethod(item, "saveTo", Q_ARG(QVariant, QVariant(QUrl::fromLocalFile(output_dir_.filePath(file)))),
                                       Q_ARG(QVariant, QVariant(scale)))) {
            fail(QStringLiteral("step %1: %2 could not save an image").arg(steps_[current_].image, action));
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
    // `main-tab-index:<page>:<n>`: the page's main view on its tab n, set on the tab bar itself, so a tab the bar has
    // scrolled out of view is reached too (the sweep's frames each start from the first tab).
    if (action.startsWith(QLatin1String("main-tab-index:"))) {
        const QString page = action.section(QLatin1Char(':'), 1, 1);
        const int index = action.section(QLatin1Char(':'), 2).toInt();
        QQuickItem* host = find(QStringLiteral("workflow.%1.mainContent").arg(page), false);
        std::function<QQuickItem*(QQuickItem*)> bar = [&bar](QQuickItem* item) -> QQuickItem* {
            if (item->inherits("QQuickTabBar")) return item;
            for (QQuickItem* child : item->childItems()) {
                if (QQuickItem* found = bar(child)) return found;
            }
            return nullptr;
        };
        QQuickItem* tabs = host != nullptr ? bar(host) : nullptr;
        if (tabs == nullptr || !tabs->setProperty("currentIndex", index)) {
            fail(QStringLiteral("step %1: no main tab bar on '%2'").arg(steps_[current_].image, page));
            return false;
        }
        return true;
    }
    // `expand-all`: every collapsed group shown on the page opened.
    if (action == QLatin1String("expand-all")) {
        std::function<void(QQuickItem*)> open = [&open](QQuickItem* item) {
            if (!item->isVisible()) return;
            if (item->metaObject()->indexOfProperty("collapsed") >= 0 && item->property("collapsed").toBool() &&
                item->objectName().startsWith(QLatin1String("group.")))
                item->setProperty("collapsed", false);
            for (QQuickItem* child : item->childItems()) open(child);
        };
        open(window_.contentItem());
        return true;
    }
    // `check-layout`: the frame's text that is elided, runs out of its box, is cut by a clipping parent or lies over other
    // text, and list rows partly under their header, one line each to EDI_SWEEP_SUMMARY (frame, kind, item, text).
    if (action.startsWith(QLatin1String("time-keys:"))) {
        // Each character as its own key press, timed from the press to the end of its handling (the bindings it
        // starts included): a keystroke's cost on the GUI thread.
        for (const QChar character : action.mid(10)) {
            QElapsedTimer clock;
            clock.start();
            QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &press);
            QKeyEvent release(QEvent::KeyRelease, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &release);
            QCoreApplication::processEvents(QEventLoop::ExcludeUserInputEvents);
            qWarning("time-keys: '%s' took %lld ms", qPrintable(QString(character)), static_cast<long long>(clock.elapsed()));
            // R3: at most 16 ms a key.
            if (QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY")); summary.open(QIODevice::Append | QIODevice::Text)) {
                QTextStream line(&summary);
                line << steps_[current_].image << "\tR3:checked\tkey\t'" << character << "' " << clock.elapsed() << " ms\n";
                if (clock.elapsed() > 16) line << steps_[current_].image << "\tR3:slow\tkey\t'" << character << "' " << clock.elapsed() << " ms, at most 16\n";
            }
        }
        return true;
    }
    if (action.startsWith(QLatin1String("log-fill:"))) {
        // A long session's run log, line by line: what a feedback report attaches.
        const int lines = action.mid(9).toInt();
        for (int line = 0; line < lines; ++line)
            qInfo("log-fill: line %d of a long session's run log, padded to about a hundred characters ..........", line);
        return true;
    }
    if (action == QLatin1String("close-project")) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine != nullptr ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        if (session == nullptr) {
            fail(QStringLiteral("step %1: no session to close a project in").arg(steps_[current_].image));
            return false;
        }
        session->closeProject();
        return true;
    }
    if (action == QLatin1String("check-messages")) {
        // A clean start shows no message: any counted is a finding the sweep fails on (the owner, 2026-11-22).
        const QQuickItem* item = find(QStringLiteral("statusBar.warnings"), false);
        const QString count = item != nullptr ? item->property("valueText").toString() : QString();
        if (count.toInt() > 0) {
            qWarning("check-messages: %s messages after a clean start", qPrintable(count));
            // Each message, so a finding names what was raised.
            QQmlEngine* engine = qmlEngine(window_.contentItem());
            auto* session = engine != nullptr ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
            QAbstractItemModel* warnings = session != nullptr ? session->loadWarnings() : nullptr;
            if (warnings != nullptr) {
                const int role = warnings->roleNames().key("message");
                for (int row = 0; row < warnings->rowCount(); ++row)
                    qWarning("check-messages: %s", qPrintable(warnings->data(warnings->index(row, 0), role).toString()));
            }
            if (!qEnvironmentVariable("EDI_SWEEP_SUMMARY").isEmpty()) {
                QFile file(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                if (file.open(QIODevice::Append | QIODevice::Text))
                    QTextStream(&file) << steps_[current_].image << "\tmessages\tstatusBar.warnings\t" << count << '\n';
            }
        }
        return true;
    }
    if (action == QLatin1String("check-layout")) {
        check_layout(steps_[current_].image);
        return true;
    }
    if (action == QLatin1String("check-assistant-panel")) {
        check_assistant_panel();
        return true;
    }
    // `unfold:<group>` and `fold:<group>`: a group opened or closed as its title's click does; a group the open project
    // does not have is passed over (an unfold inventory lists every group a scenario may meet).
    if (action == QLatin1String("mark")) {
        mark_.start();
        return true;
    }
    // `series-point`: the Auto width series (W3, W4): the window, the sidebar's width and the parameter table's shown
    // columns at this window width.
    if (action == QLatin1String("series-point")) {
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        QObject* sizes = engine != nullptr ? engine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
        QQuickItem* parameters = find(QStringLiteral("parameters.list"), false);
        QStringList shown;
        if (parameters != nullptr)
            for (int column = 0; column < 9; ++column) {
                bool on = false;
                QMetaObject::invokeMethod(parameters, "shows", Q_RETURN_ARG(bool, on), Q_ARG(int, column));
                if (on) shown << QString::number(column);
            }
        QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
        if (!summary.open(QIODevice::Append | QIODevice::Text) || sizes == nullptr) return true;
        QTextStream line(&summary);
        const QString frame = steps_[current_].image;
        const bool below = sizes->property("sideBarBelow").toBool();
        const double width = sizes->property("sideBarWidth").toDouble();
        const double em = sizes->property("fontPixelSize").toDouble();
        const int window = window_.width();
        line << frame << "\tW:series\t" << window << '\t' << (below ? "below " : "side ") << width << " columns " << shown.join(QLatin1Char(','))
             << " spare " << (parameters != nullptr ? parameters->property("spareWidth").toDouble() : -1) << " gap " << em << '\n';
        if (std::abs(em - kContractFontPx) > 0.01) return true;
        const auto has = [&](int column) { return shown.contains(QString::number(column)); };
        // W3 at the switch width itself, against the ADR's 913 px: at the side there, at the bottom one pixel below.
        if (window == kSwitchWidthPx || window == kSwitchWidthPx - 1) {
            line << frame << "\tW3:checked\tswitch\twindow " << window << ", sidebar " << (below ? "below " : "side ") << width << " px, columns " << shown.join(QLatin1Char(',')) << '\n';
            if (window == kSwitchWidthPx - 1 && !below) line << frame << "\tW3:switch\tswitch\tat the side at " << window << " px, the bottom below " << kSwitchWidthPx << '\n';
            if (window == kSwitchWidthPx && (below || width > window / 2.0 + 0.5 || !(has(1) && has(3) && has(5))))
                line << frame << "\tW3:switch\tswitch\t" << (below ? "below" : "side") << ' ' << width << " px at " << window << ", at most half, columns " << shown.join(QLatin1Char(',')) << '\n';
        }
        if (!below) {
            // W4: Start, Min, Max and Change join in that order, each as soon as it fits, and with all of them Auto is at
            // most 681 px. The width never shrinks as the window grows (the series runs from narrow to wide).
            QString order;
            bool missing = false;
            for (const int column : {2, 7, 8, 6}) {
                if (!has(column)) missing = true;
                else if (missing) order = QStringLiteral("column %1 shown before an earlier one").arg(column);
            }
            const bool all = has(2) && has(6) && has(7) && has(8);
            static int lastWindow = 0;
            static double lastWidth = 0;
            line << frame << "\tW4:checked\tseries\twindow " << window << ", sidebar " << width << " px, " << (all ? QStringLiteral("all columns") : "columns " + shown.join(QLatin1Char(','))) << '\n';
            if (!order.isEmpty()) line << frame << "\tW4:order\tseries\t" << order << ", columns " << shown.join(QLatin1Char(',')) << '\n';
            if (all && width > kAutoStopPx + 0.5) line << frame << "\tW4:stop\tseries\t" << width << " px with all columns, at most " << kAutoStopPx << '\n';
            if (window > lastWindow && lastWindow > 0 && width < lastWidth - 0.5)
                line << frame << "\tW4:shrink\tseries\t" << lastWidth << " px at " << lastWindow << " -> " << width << " px at " << window << '\n';
            lastWindow = window;
            lastWidth = width;
        }
        return true;
    }
    // `check-popup:<editor>`: the parameter popup a click just opened shows its value editor, with the keyboard focus
    // (the owner, 2026-11-23: every field row and table cell opens the same popup).
    if (action.startsWith(QLatin1String("check-popup:"))) {
        const QString name = action.mid(12);
        // A popup's items are drawn in the window's overlay, a child of the content item.
        QQuickItem* editor = nullptr;
        std::function<void(QQuickItem*)> look = [&](QQuickItem* item) {
            for (QQuickItem* child : item->childItems()) {
                if (editor != nullptr)
                    return;
                if (child->objectName() == name)
                    editor = child;
                else
                    look(child);
            }
        };
        look(window_.contentItem());
        const bool ok = editor != nullptr && editor->isVisible() && editor->hasActiveFocus();
        qWarning("check-popup %s: %s", qPrintable(name), editor == nullptr ? "no popup" : ok ? "open, focused" : "open, not focused");
        if (!ok) {
            QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
            if (summary.open(QIODevice::Append | QIODevice::Text))
                QTextStream(&summary) << steps_[current_].image << "\tF2:popup\t" << name << '\t' << (editor == nullptr ? "no popup" : "not focused") << '\n';
        }
        // F3: the popup's inputs (the editor, s.u., Min, Max) one gap apart, and none wider than its text's room.
        if (editor != nullptr) {
            QQuickItem* grid = editor->parentItem();
            while (grid != nullptr && !grid->inherits("QQuickGrid")) grid = grid->parentItem();
            QList<QQuickItem*> inputs;
            if (grid != nullptr) {
                for (QQuickItem* child : visual_items(grid)) {
                    if (child->inherits("QQuickTextField") && child->isVisible() && child->parentItem() == grid) inputs << child;
                    if (child->inherits("QQuickLoader") && child->isVisible() && child->parentItem() == grid && child->property("active").toBool()) inputs << child;
                }
            }
            std::sort(inputs.begin(), inputs.end(), [](QQuickItem* l, QQuickItem* r) { return l->x() < r->x(); });
            QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
            if (summary.open(QIODevice::Append | QIODevice::Text)) {
                QTextStream line(&summary);
                QStringList gaps;
                for (qsizetype i = 1; i < inputs.size(); ++i) gaps << QString::number(inputs[i]->x() - inputs[i - 1]->x() - inputs[i - 1]->width(), 'f', 1);
                line << steps_[current_].image << "\tF3:checked\t" << name << "\tgaps " << gaps.join(QLatin1Char(',')) << '\n';
                for (qsizetype i = 1; i < gaps.size(); ++i)
                    if (std::abs(gaps[i].toDouble() - gaps[0].toDouble()) > 1.0)
                        line << steps_[current_].image << "\tF3:gap\t" << name << '\t' << gaps.join(QLatin1Char(',')) << " between inputs, not equal\n";
                for (QQuickItem* input : inputs) {
                    if (input->inherits("QQuickLoader")) input = input->property("item").value<QQuickItem*>();
                    // The value being typed scrolls in its input.
                    if (input == nullptr || !input->inherits("QQuickTextField") || input->property("cursorVisible").toBool()) continue;
                    const double room = input->width() - input->property("leftPadding").toDouble() - input->property("rightPadding").toDouble();
                    if (input->property("contentWidth").toDouble() > room + 0.5)
                        line << steps_[current_].image << "\tF3:crop\t" << name << '\t' << input->objectName() << " text " << input->property("contentWidth").toDouble() << " in " << room << '\n';
                }
            }
        }
        return true;
    }
    // `note-columns:<list>` keeps a table's column widths; `check-columns:<list>` reports any that moved since (the
    // owner, 2026-11-23: a value typed, a type changed or a fit never changes a column's width).
    if (action.startsWith(QLatin1String("note-columns:")) || action.startsWith(QLatin1String("check-columns:"))) {
        const QString name = action.section(QLatin1Char(':'), 1);
        QQuickItem* list = find(name, false);
        const QString widths = list == nullptr ? QString() : list->property("columnWidths").toStringList().join(QLatin1Char(','));
        qWarning("%s %s", qPrintable(action), qPrintable(widths));
        if (action.startsWith(QLatin1String("note-columns:"))) {
            column_widths_[name] = widths;
        } else if (QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY")); summary.open(QIODevice::Append | QIODevice::Text)) {
            QTextStream line(&summary);
            line << steps_[current_].image << "\tT6:checked\t" << name << '\t' << widths << '\n';
            if (column_widths_.value(name) != widths)
                line << steps_[current_].image << "\tT6:columns-moved\t" << name << '\t' << column_widths_.value(name) << " -> " << widths << '\n';
        }
        return true;
    }
    // `check-fields`: no shown parameter field draws its value wider than its room, the space left of its unit (the
    // owner, 2026-11-23: a field row drops digits, then wraps; it never crops a number).
    if (action == QLatin1String("check-fields")) {
        int fields = 0, cropped = 0;
        std::function<void(QQuickItem*)> walk = [&](QQuickItem* item) {
            for (QQuickItem* child : item->childItems()) {
                if (!child->isVisible())
                    continue;
                if (child->metaObject()->indexOfProperty("shownValue") >= 0 && child->metaObject()->indexOfProperty("room") >= 0 && on_screen(child)) {
                    ++fields;
                    const double room = child->property("room").toDouble();
                    const double drawn = child->property("contentWidth").toDouble();
                    if (room > 0 && drawn > room + 0.5) {
                        ++cropped;
                        QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
                        if (summary.open(QIODevice::Append | QIODevice::Text))
                            QTextStream(&summary) << steps_[current_].image << "\tF1:field-cropped\t" << child->objectName() << '\t'
                                                  << QStringLiteral("'%1' %2 px in %3 px").arg(child->property("text").toString()).arg(drawn, 0, 'f', 1).arg(room, 0, 'f', 1) << '\n';
                    }
                }
                walk(child);
            }
        };
        walk(window_.contentItem());
        // F1, one grid per group: every shown field of a group (a parameter or value field) has the same width and, like
        // its selectors, stands on the group's columns.
        QHash<QQuickItem*, QList<QQuickItem*>> byGroup;
        std::function<void(QQuickItem*)> gather = [&](QQuickItem* at) {
            for (QQuickItem* child : at->childItems()) {
                if (!child->isVisible()) continue;
                const QString type = QString::fromLatin1(child->metaObject()->className());
                if ((type.startsWith(QLatin1String("ParameterField")) || type.startsWith(QLatin1String("SelectorField")) || type.startsWith(QLatin1String("ValueField"))) &&
                    on_screen(child) && !child->objectName().contains(QLatin1String(".popup"))) {
                    QQuickItem* group = child->parentItem();
                    while (group != nullptr && !group->objectName().startsWith(QLatin1String("group."))) group = group->parentItem();
                    if (group != nullptr) byGroup[group] << child;
                    continue;
                }
                gather(child);
            }
        };
        gather(window_.contentItem());
        int grids = 0;
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        QObject* sizes = engine != nullptr ? engine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
        const double groupWidth = sizes != nullptr ? sizes->property("sideBarContentWidth").toDouble() : 0;
        for (auto it = byGroup.cbegin(); it != byGroup.cend(); ++it) {
            // The grid: the widest row of fields, or of selectors in a group without fields. Every field stands on one of
            // its columns; a selector starts and ends on them, spanning whole columns. Only a selector alone on its row
            // and as wide as the group stands outside, so its whole name shows; it starts on the grid.
            const auto isSelector = [](QQuickItem* field) { return QString::fromLatin1(field->metaObject()->className()).startsWith(QLatin1String("SelectorField")); };
            QMap<int, QList<QQuickItem*>> rows;
            bool fieldsHere = false;
            for (QQuickItem* field : it.value()) {
                rows[qRound(field->mapToScene(QPointF(0, 0)).y())] << field;
                fieldsHere = fieldsHere || !isSelector(field);
            }
            const auto full = [&](const QList<QQuickItem*>& row) { return row.size() == 1 && isSelector(row.first()) && groupWidth > 0 && row.first()->width() >= groupWidth - 0.5; };
            QList<QPair<double, double>> columns;
            for (const QList<QQuickItem*>& row : rows) {
                if (full(row) && rows.size() > 1) continue;
                QList<QPair<double, double>> spans;
                for (QQuickItem* field : row)
                    if (!fieldsHere || !isSelector(field)) {
                        const double left = field->mapToScene(QPointF(0, 0)).x();
                        spans << qMakePair(left, left + field->width());
                    }
                if (spans.size() > columns.size()) columns = spans;
            }
            QSet<int> widths;
            QStringList off;
            for (const QList<QQuickItem*>& row : rows)
                for (QQuickItem* field : row) {
                    const double left = field->mapToScene(QPointF(0, 0)).x(), right = left + field->width();
                    const bool starts = std::any_of(columns.cbegin(), columns.cend(), [&](const auto& c) { return std::abs(c.first - left) <= 0.5; });
                    const bool ends = std::any_of(columns.cbegin(), columns.cend(), [&](const auto& c) { return std::abs(c.second - right) <= 0.5; });
                    if (!isSelector(field)) widths.insert(qRound(field->width()));
                    if (!columns.isEmpty() && (!starts || (!ends && !full(row)))) off << QStringLiteral("%1 %2+%3").arg(field->objectName()).arg(qRound(left)).arg(qRound(field->width()));
                }
            ++grids;
            if (widths.size() > 1 || !off.isEmpty())
                if (QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY")); summary.open(QIODevice::Append | QIODevice::Text))
                    QTextStream(&summary) << steps_[current_].image << "\tF1:grid\t" << it.key()->objectName() << '\t' << widths.size() << " field widths, off the grid: "
                                          << off.join(QLatin1String(", ")) << '\n';
        }
        qWarning("check-fields: %d fields, %d cropped, %d groups' grids", fields, cropped, grids);
        if (QFile summary(qEnvironmentVariable("EDI_SWEEP_SUMMARY")); summary.open(QIODevice::Append | QIODevice::Text))
            QTextStream(&summary) << steps_[current_].image << "\tF1:checked\tfields\t" << fields << " fields, " << cropped << " cropped\n";
        return true;
    }
    if (action.startsWith(QLatin1String("unfold:")) || action.startsWith(QLatin1String("fold:"))) {
        const bool open = action.startsWith(QLatin1String("unfold:"));
        // The shown one: a hidden tab may hold a group of the same name (a category's Extras part).
        if (QQuickItem* group = find(action.section(QLatin1Char(':'), 1), true); group != nullptr && group->isVisible())
            group->setProperty("collapsed", !open);
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
            QFile source(QString::fromUtf8(EDI_CLI_PROJECTS_DIR) + u'/' + resource);
            if (!source.open(QIODevice::ReadOnly)) {
                fail(QStringLiteral("step %1: no example file %2").arg(steps_[current_].image, resource));
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
    if (const auto tick = QRegularExpression(QStringLiteral("^(un)?tick:(.+)$")).match(action); tick.hasMatch()) {
        // One parameter's Free box set in its own row, as the built-in tutorial's step does.
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine != nullptr ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        ProjectViewModel* project = session != nullptr ? session->project() : nullptr;
        ParameterItem* found = nullptr;
        // The plan names a row as the table's path does (`linked_structures[hs]`); compared with dots on both sides.
        QString wanted = tick.captured(2);
        wanted.replace(QRegularExpression(QStringLiteral("\\[([^\\]]*)\\]")), QStringLiteral(".\\1"));
        if (project != nullptr) {
            ParameterTableModel* table = project->parameters();
            const int parameter_role = table->roleNames().key("parameter"), path_role = table->roleNames().key("path");
            static const QRegularExpression bracket(QStringLiteral("\\[([^\\]]*)\\]"));
            for (int row = 0; row < table->rowCount() && found == nullptr; ++row) {
                QString dotted = table->data(table->index(row, 0), path_role).toString();
                dotted.replace(bracket, QStringLiteral(".\\1"));
                if (dotted == wanted)
                    found = qobject_cast<ParameterItem*>(table->data(table->index(row, 0), parameter_role).value<QObject*>());
            }
        }
        if (found == nullptr || !project->setParametersFree({found}, tick.captured(1).isEmpty())) {
            fail(QStringLiteral("step %1: cannot set the Free box of '%2'").arg(steps_[current_].image, tick.captured(2)));
            return false;
        }
        return true;
    }
    return click(action);
}

QQuickItem* DemoDriver::find(const QString& object_name, bool must_be_usable) {
    // Looking a control up walks every item of the window for the driver, not for the user: like the grab, the GUI
    // watchdog leaves it out (ui_probe.hpp). The click that follows is the user's and stays measured.
#if EDI_UI_INSTRUMENTATION
    const int id = ++tool_id_;
    trace_measurement(true, id, QStringLiteral("DemoDriver::find"));
    QQuickItem* found = locate(object_name, must_be_usable);
    trace_measurement(false, id, QStringLiteral("DemoDriver::find"));
    return found;
#else
    return locate(object_name, must_be_usable);
#endif
}

QQuickItem* DemoDriver::locate(const QString& object_name, bool must_be_usable) {
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
    // A page's tab names repeat on other pages (Structure's and Analysis' mainArea.tab.structure), and while pages
    // slide the new one is not yet on screen: a tab is looked for on the page its app-bar tab has checked.
    if ((object_name.startsWith(QLatin1String("mainArea.")) && object_name.contains(QLatin1String(".tab."))) ||
        object_name.startsWith(QLatin1String("sideBar.tab."))) {
        QQuickItem* page = nullptr;
        for (QQuickItem* tab : window_.findChildren<QQuickItem*>()) {
            if (tab->objectName().startsWith(QLatin1String("appBar.tab.")) && tab->property("checked").toBool()) {
                page = qvariant_cast<QQuickItem*>(tab->property("page"));
                break;
            }
        }
        if (page != nullptr) {
            QList<QQuickItem*> on_page;
            for (QQuickItem* match : matches) {
                if (page->isAncestorOf(match)) on_page.append(match);
            }
            if (!on_page.isEmpty()) matches = on_page;
        }
    }
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
    QRectF shown = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()))
                       .intersected(QRectF(QPointF(0, 0), QSizeF(window_.width(), window_.height())));
    for (QQuickItem* ancestor = item->parentItem(); ancestor != nullptr && !shown.isEmpty();
         ancestor = ancestor->parentItem()) {
        if (ancestor->clip()) {
            shown = shown.intersected(ancestor->mapRectToScene(ancestor->clipRect()));
        }
    }
    return !shown.isEmpty();
}

QQuickItem* DemoDriver::find_held(const QString& object_name, bool must_be_usable) {
    // A press of a held key repeats on one control: the one found last, while it can still take the press, rather than
    // a walk of every item in the window at each press, which made the presses themselves the slowest part.
    QPointer<QQuickItem>& held = held_items_[object_name];
    if (held && held->isVisible() && (!must_be_usable || held->isEnabled()) && on_screen(held)) return held;
    held = find(object_name, must_be_usable);
    return held;
}

bool DemoDriver::click(const QString& object_name) {
    QQuickItem* item = current_ < steps_.size() && steps_[current_].navigation != 0 ? find_held(object_name, true)
                                                                                   : find(object_name, true);
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
    // F2 times a popup from the click itself: every frame for a second after it, the first that draws a parameter
    // popup's value editor (popup-time reports it; the driver's own wait before its next action is not counted).
    mark_.start();
    popup_shown_ms_ = -1;
    // Only for a step that times a popup: the watch walks the window's items every frame, and on every click it held
    // the GUI thread through the responsiveness gates' scenarios.
    const bool timesPopup = current_ < steps_.size() &&
                            std::any_of(steps_[current_].actions.cbegin(), steps_[current_].actions.cend(),
                                        [](const QString& a) { return a.startsWith(QLatin1String("popup-time:")); });
    if (timesPopup) {
    auto watch = std::make_shared<QMetaObject::Connection>();
    *watch = connect(&window_, &QQuickWindow::frameSwapped, this, [this, watch] {
        std::function<bool(QQuickItem*)> shows = [&](QQuickItem* at) {
            for (QQuickItem* child : at->childItems()) {
                if (child->objectName().endsWith(QLatin1String(".popup.value")) && child->isVisible()) return true;
                if (shows(child)) return true;
            }
            return false;
        };
        if (shows(window_.contentItem())) popup_shown_ms_ = mark_.elapsed();
        if (popup_shown_ms_ >= 0 || mark_.elapsed() > 1000) disconnect(*watch);
        else window_.update();
    });
    }
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

void DemoDriver::settle_then(const std::function<void()>& next) {
    settle_attempts_ = 0;
    preparing_attempts_ = 0;
    previous_frame_ = QImage();
    auto poll = std::make_shared<std::function<void()>>();
    *poll = [this, next, poll] {
        // A calculation in flight will change the page when it is published (edi ADR-0020): the frame is
        // settled only once the project has no calculation in flight or owed.
        QQmlEngine* engine = qmlEngine(window_.contentItem());
        auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
        const bool calculating =
            session != nullptr && session->project() != nullptr && session->project()->calculating();
        // An example fetched from an online collection opens once its download lands (ADR-0068).
        const bool opening = session != nullptr && session->openingExample();
        // A page still being made after a project opened keeps its tab disabled, which no frame shows.
        bool preparing = false;
        // The app bar's tabs live as long as the window: found once, not by a walk of every item at each poll.
        static const QString kTabs[] = {QStringLiteral("appBar.tab.structure"), QStringLiteral("appBar.tab.experiment"),
                                        QStringLiteral("appBar.tab.analysis"), QStringLiteral("appBar.tab.report")};
        for (const QString& tab : kTabs) {
            QPointer<QQuickItem>& item = app_bar_tabs_[tab];
            if (!item) item = find(tab, false);
            preparing = preparing || (item && item->property("preparing").toBool());
        }
        const QImage frame = grab();
#if EDI_UI_INSTRUMENTATION
        const int compare = ++tool_id_;
        trace_measurement(true, compare, QStringLiteral("compare-images"));
#endif
        const bool same = !previous_frame_.isNull() && frame == previous_frame_;
#if EDI_UI_INSTRUMENTATION
        trace_measurement(false, compare, QStringLiteral("compare-images"));
#endif
        if (!calculating && !opening && !preparing && same) {
            next();
            return;
        }
        const int max_attempts = documentation_ && documentation_workflow_ != "creation"
                                     ? kSettleMaxAttempts * 10 : kSettleMaxAttempts;
        // A large scan's pages take longer to prepare than any animation runs: the bound starts when they are ready.
        if (preparing && ++preparing_attempts_ <= kSettleMaxAttempts * 20) {
            settle_attempts_ = 0;
        }
        if (++settle_attempts_ > max_attempts) {
            // The last two frames, to see what kept changing.
            previous_frame_.save(output_dir_.filePath(steps_[current_].image + QStringLiteral("-unsettled-a.png")));
            frame.save(output_dir_.filePath(steps_[current_].image + QStringLiteral("-unsettled-b.png")));
            fail(QStringLiteral("step %1 did not settle within %2 ms (%3)")
                     .arg(steps_[current_].image)
                     .arg(kSettleIntervalMs * max_attempts)
                     .arg(calculating ? QStringLiteral("a calculation is in flight")
                          : opening   ? QStringLiteral("an example is being fetched")
                          : preparing ? QStringLiteral("a workflow page is preparing")
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
    const QString mode = project->analysis() != nullptr ? project->analysis()->fittingMode() : QString();
    if (mode != QLatin1String("sequential") && mode != QLatin1String("independent") && mode != QLatin1String("parametric")) {
        return QStringLiteral("the scan does not run in a scan mode");
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

void DemoDriver::idle_then(const std::function<void()>& next, int waited_ms) {
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

void DemoDriver::drawn_then(const std::function<void()>& next, int waited_ms) {
    ProjectViewModel* project = open_project(window_);
    if (project == nullptr || project->fit() == nullptr || !project->fit()->catchingUp()) {
        idle_then(next);
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the display did not catch up").arg(steps_[current_].image));
        return;
    }
    QTimer::singleShot(kIdlePollMs, this, [this, next, waited_ms] { drawn_then(next, waited_ms + kIdlePollMs); });
}

void DemoDriver::timed_fit_then(const std::function<void()>& next, int files, int stop_after) {
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
    connections->push_back(connect(fit, &FitViewModel::resultsUnreadable, this, [refusal, finish](const QString& reason) {
        *refusal = QStringLiteral("the fit ran but its results could not be read: ") + reason;
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

namespace {

QString item_path(const QQuickItem* item) {
    QStringList parts;
    for (const QQuickItem* at = item; at != nullptr && parts.size() < 3; at = at->parentItem()) {
        if (!at->objectName().isEmpty()) parts.prepend(at->objectName());
    }
    const QString type = QString::fromLatin1(item->metaObject()->className()).section(QLatin1Char('_'), 0, 0);
    return (parts.isEmpty() ? QStringLiteral("?") : parts.join(QLatin1Char('/'))) + QLatin1Char(':') + type;
}

// A line's glyphs where they are drawn: their ink, or their advance box.
QRectF line_rect(const QTextLine& line, bool ink) {
    if (!ink) return line.naturalTextRect();
    QRectF all;
    for (const QGlyphRun& run : line.glyphRuns()) {
        const QRawFont font = run.rawFont();
        const QList<quint32> glyphs = run.glyphIndexes();
        const QList<QPointF> positions = run.positions();
        for (qsizetype i = 0; i < std::min(glyphs.size(), positions.size()); ++i)
            if (const QRectF glyph = font.boundingRect(glyphs[i]); !glyph.isEmpty()) all |= glyph.translated(positions[i]);
    }
    return all;
}

// What a text item draws, in its own coordinates, from the layout it draws: an elided text's shown part, a rich text's
// subscripts. Null when nothing is drawn.
QRectF text_rect(QQuickItem* item, bool ink) {
    QRectF all;
    if (auto* text = qobject_cast<QQuickText*>(item); text != nullptr) {
        QQuickTextPrivate* d = QQuickTextPrivate::get(text);
        const auto aligned = [](double room, double size, int alignment, int centre, int end) {
            return alignment == centre ? (room - size) / 2 : alignment == end ? room - size : 0.0;
        };
        const double height = d->layedOutTextRect.height() + d->lineHeightOffset();
        const double top = text->topPadding() + aligned(d->availableHeight(), height, text->vAlign(), QQuickText::AlignVCenter, QQuickText::AlignBottom);
        const double width = d->richText ? d->layedOutTextRect.width() : d->lineWidth;
        const QPointF at(text->leftPadding() + aligned(d->availableWidth(), width, text->effectiveHAlign(), QQuickText::AlignHCenter, QQuickText::AlignRight), top);
        if (d->richText) {
            const QTextDocument* document = d->extra.isAllocated() ? d->extra->doc : nullptr;
            if (document == nullptr) return {};
            for (QTextBlock block = document->begin(); block.isValid(); block = block.next())
                for (int i = 0; i < block.layout()->lineCount(); ++i)
                    all |= line_rect(block.layout()->lineAt(i), ink).translated(document->documentLayout()->blockBoundingRect(block).topLeft());
        } else {
            const int whole = std::min(d->layout.lineCount(), d->lineCount - (d->elideLayout ? 1 : 0));
            for (int i = 0; i < whole; ++i) all |= line_rect(d->layout.lineAt(i), ink);
            if (d->elideLayout)
                for (int i = 0; i < d->elideLayout->lineCount(); ++i) all |= line_rect(d->elideLayout->lineAt(i), ink);
        }
        return all.isEmpty() ? QRectF() : all.translated(at);
    }
    if (item->inherits("QQuickTextInput")) {
        const QString shown = item->property("displayText").toString();
        if (shown.trimmed().isEmpty()) return {};
        const QFontMetricsF metrics(item->property("font").value<QFont>());
        const double left = item->property("leftPadding").toDouble();
        const double room = item->width() - left - item->property("rightPadding").toDouble();
        const double width = metrics.horizontalAdvance(shown);
        const int alignment = item->property("effectiveHorizontalAlignment").toInt();
        const double x = width >= room ? left
                         : (alignment & int(Qt::AlignRight)) != 0   ? left + room - width
                         : (alignment & int(Qt::AlignHCenter)) != 0 ? left + (room - width) / 2
                                                                    : left;
        const QRectF drawn = ink ? metrics.tightBoundingRect(shown) : QRectF(0, -metrics.ascent(), width, metrics.height());
        // A wider text scrolls inside its field.
        return drawn.translated(x, item->baselineOffset()).intersected(QRectF(left - 1, -item->height(), room + 2, item->height() * 3));
    }
    return {};
}

// What an item and its children draw, in the scene: texts, painted rectangles and borders, pictures. Null when nothing.
QRectF drawn_rect(QQuickItem* item, bool ink) {
    if (!item->isVisible() || item->opacity() < 0.01) return {};
    QRectF all;
    if (item->inherits("QQuickText") || item->inherits("QQuickTextInput")) {
        // A transparent text (a cut input under its shortened label) draws nothing.
        if (const QRectF text = item->property("color").value<QColor>().alpha() > 0 ? text_rect(item, ink) : QRectF(); !text.isEmpty()) all = item->mapRectToScene(text);
    } else if (auto* rectangle = qobject_cast<QQuickRectangle*>(item); rectangle != nullptr) {
        // Read, never made: border() gives a rectangle a pen it had not, which then painted a label's transparent
        // background black in the next frame.
        const QQuickPen* pen = static_cast<QQuickRectanglePrivate*>(QObjectPrivate::get(rectangle))->pen;
        const bool edged = pen != nullptr && pen->isValid() && pen->width() > 0 && pen->color().alpha() > 0;
        if (rectangle->color().alpha() > 0 || edged) all = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
    } else if ((item->flags() & QQuickItem::ItemHasContents) != 0) {
        all = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
    }
    for (QQuickItem* child : item->childItems())
        if (const QRectF part = drawn_rect(child, ink); !part.isEmpty()) all |= part;
    if (item->clip()) all = all.intersected(item->mapRectToScene(item->clipRect()));
    return all.isEmpty() ? QRectF() : all;
}

}  // namespace

namespace {
// The characters a text shows besides its ellipsis, as drawn.
int kept_characters(QQuickItem* item) {
    auto* text = qobject_cast<QQuickText*>(item);
    if (text == nullptr) return 0;
    QQuickTextPrivate* d = QQuickTextPrivate::get(text);
    QString drawn;
    const int whole = std::min(d->layout.lineCount(), d->lineCount - (d->elideLayout ? 1 : 0));
    for (int i = 0; i < whole; ++i) drawn += d->layout.text().mid(d->layout.lineAt(i).textStart(), d->layout.lineAt(i).textLength());
    if (d->elideLayout) drawn += d->elideLayout->text();
    return static_cast<int>(drawn.size() - drawn.count(QChar(0x2026)));
}

QString without_tags(QString text) { return text.remove(QRegularExpression(QStringLiteral("<[^>]*>"))).trimmed(); }

bool icon_font(const QQuickItem* item) {
    return item->property("font").value<QFont>().family().contains(QLatin1String("Awesome"), Qt::CaseInsensitive);
}

// The words a control draws inside `root`, left to right, icons left out; `cut` is set when one is elided or runs past
// the root's right edge.
QString drawn_words(QQuickItem* root, bool* cut) {
    if (root == nullptr) return QString();
    QList<QQuickItem*> pieces;
    for (QQuickItem* item : visual_items(root))
        if (item->inherits("QQuickText") && item->isVisible() && item->opacity() > 0.01 && !icon_font(item) &&
            !item->property("text").toString().trimmed().isEmpty())
            pieces << item;
    std::sort(pieces.begin(), pieces.end(), [root](QQuickItem* a, QQuickItem* b) { return a->mapToItem(root, QPointF()).x() < b->mapToItem(root, QPointF()).x(); });
    QStringList words;
    for (QQuickItem* piece : pieces) {
        words << without_tags(piece->property("text").toString());
        const double right = piece->mapToItem(root, QPointF(piece->property("contentWidth").toDouble(), 0)).x();
        if (piece->property("truncated").toBool() || right > root->width() + 0.5) *cut = true;
    }
    return words.join(QLatin1Char(' '));
}

// The right end of the widest name a parameter table's shown rows hold, uncut, from its cell's left edge: the name
// column is the second, after the row number when that shows.
double widest_drawn_name(QQuickItem* list) {
    const QVariantList widths = list->property("columnWidths").toList();
    auto* content = list->property("contentItem").value<QQuickItem*>();
    if (widths.size() < 2 || content == nullptr) return 0;
    const qsizetype at = widths[0].toDouble() > 0.5 ? 1 : 0;
    double widest = 0;
    for (QQuickItem* row : content->childItems()) {
        if (!row->isVisible() || row->height() <= 1 || row == list->property("headerItem").value<QQuickItem*>()) continue;
        QQuickItem* cells = nullptr;
        for (QQuickItem* item : visual_items(row))
            if (item->inherits("QQuickRow") && item->isVisible()) {
                cells = item;
                break;
            }
        if (cells == nullptr) continue;
        QList<QQuickItem*> shown;
        for (QQuickItem* cell : cells->childItems())
            if (cell->isVisible() && cell->width() > 0.5) shown << cell;
        std::sort(shown.begin(), shown.end(), [](QQuickItem* a, QQuickItem* b) { return a->x() < b->x(); });
        if (shown.size() <= at) continue;
        for (QQuickItem* piece : QList<QQuickItem*>{shown[at]} + visual_items(shown[at]))
            if (piece->inherits("QQuickText") && piece->isVisible() && !piece->property("text").toString().trimmed().isEmpty())
                widest = std::max(widest, piece->mapToItem(shown[at], QPointF(piece->implicitWidth(), 0)).x());
    }
    return widest;
}

// Two layouts wait for the owner's decision on columns that do not fit: a scan's row with six extract columns in
// Compact (the Experiments table) and the expanded atom sites in Compact and Fit values. The table checks added with
// the declared numbers leave them out until that decision, so they report only what the owner has ruled on.
bool awaiting_owner(const QQuickItem* item) {
    const QQuickItem* table = item;
    while (table != nullptr && !(table->inherits("QQuickListView") && table->objectName().endsWith(QLatin1String(".list")))) table = table->parentItem();
    if (table == nullptr) return false;
    QQmlEngine* engine = qmlEngine(table);
    QObject* preferences = engine != nullptr ? engine->singletonInstance<QObject*>("edi.app", "Preferences") : nullptr;
    const QString mode = preferences != nullptr ? preferences->property("sideBarWidthMode").toString() : QString();
    if (table->objectName() == QLatin1String("experiments.list")) return mode == QLatin1String("compact");
    if (table->objectName() == QLatin1String("generated.expanded_atom_site.list")) return mode == QLatin1String("compact") || mode == QLatin1String("values");
    return false;
}

// A number's significant digits as shown: its mantissa's digits from the first that is not zero, an s.u. in brackets
// and a power of ten left out. -1 for a text that does not start with a number.
int significant_digits(const QString& shown) {
    static const QRegularExpression mantissa(QStringLiteral(R"(^\s*[-+\x{2212}]?(\d*\.?\d+))"));
    const QRegularExpressionMatch match = mantissa.match(without_tags(shown));
    if (!match.hasMatch()) return -1;
    QString digits = match.captured(1).remove(QLatin1Char('.'));
    while (digits.startsWith(QLatin1Char('0'))) digits.remove(0, 1);
    return static_cast<int>(digits.size());
}

// The texts the user gave the open project: datablock, row and alias names, expressions, file names, its title; and the
// folders of the recent projects.
QSet<QString> user_texts(QQmlEngine* engine, const ProjectViewModel* project) {
    QSet<QString> texts;
    const auto add = [&texts](const QString& text) {
        if (!text.trimmed().isEmpty()) texts.insert(text.trimmed());
    };
    if (project != nullptr) {
        const edi::Project& core = project->project();
        add(QString::fromStdString(core.metadata.name));
        add(QString::fromStdString(core.metadata.title));
        add(QString::fromStdString(core.path));
        for (const auto& structure : core.structures) {
            add(QString::fromStdString(structure->name.value()));
            for (const auto& site : structure->atom_sites) add(QString::fromStdString(site->id.value()));
        }
        for (const auto& experiment : core.experiments) {
            add(QString::fromStdString(experiment->name.value()));
            add(QFileInfo(QString::fromStdString(experiment->data_file)).fileName());
        }
        for (const auto& alias : core.aliases) add(QString::fromStdString(alias->id.value()));
        for (const auto& constraint : core.constraints) {
            add(QString::fromStdString(constraint->id.value()));
            add(QString::fromStdString(constraint->expression.value()));
        }
        // A scan's files, and the rows parameters belong to (a background point's ID).
        for (int row = 0; row < project->experiments()->count(); ++row) {
            add(project->experiments()->text(row, QStringLiteral("name")));
            add(project->experiments()->text(row, QStringLiteral("file")));
        }
        for (int row = 0; row < project->parameters()->count(); ++row) add(project->parameters()->text(row, QStringLiteral("rowLabel")));
    }
    if (QObject* recent = engine != nullptr ? engine->singletonInstance<QObject*>("edi.app", "RecentProjects") : nullptr; recent != nullptr)
        if (auto* rows = recent->property("rows").value<QAbstractItemModel*>(); rows != nullptr) {
            const QHash<int, QByteArray> roles = rows->roleNames();
            for (auto role = roles.cbegin(); role != roles.cend(); ++role)
                if (role.value() == "path" || role.value() == "label")
                    for (int row = 0; row < rows->rowCount(); ++row) add(rows->data(rows->index(row, 0), role.key()).toString());
        }
    return texts;
}

// The owner's GUI contract (ADR-0103 decisions 3, 4, 6 and 7): each finding of the layout check is reported under the
// rule it breaks. N1-N10 are the contract's "never" list in its order: N1 a fixed label cut, N2 text under a control,
// N3 sibling controls overlapping, N4 a sideways scroll bar, N5 a scroll bar with nothing to scroll, N6 a width change
// after a project is shown, N7 a table growing row by row, N8 a cell at another column's x, N9 a unit in bold, N10 a
// header repeating its group's title.
QString contract_rule(const QString& kind, const QString& path, const QString& text) {
    const bool header = path.contains(QLatin1String("HeaderLabel")) || path.contains(QLatin1String("Header"));
    const bool number = path.contains(QLatin1String("ParameterCell")) || path.contains(QLatin1String("NumberLabel")) ||
                        path.contains(QLatin1String("CellLabel")) || path.contains(QLatin1String("ParameterField"));
    if (kind == QLatin1String("clipped") || kind == QLatin1String("only-dots") || kind == QLatin1String("overflow"))
        return header ? QStringLiteral("T9") : number ? QStringLiteral("T8") : QStringLiteral("N1");
    if (kind == QLatin1String("elided")) return QStringLiteral("T10");
    if (kind == QLatin1String("header-cut")) return QStringLiteral("T9");
    if (kind == QLatin1String("number-cut")) return QStringLiteral("T8");
    if (kind == QLatin1String("label-cut")) return header ? QStringLiteral("T9") : QStringLiteral("N1");
    if (kind == QLatin1String("value-short") || kind == QLatin1String("column-cut") || kind == QLatin1String("digits-most") ||
        kind == QLatin1String("digits-least"))
        return QStringLiteral("T8");
    if (kind == QLatin1String("combo-gap")) return QStringLiteral("F4");
    if (kind == QLatin1String("overlap")) return QStringLiteral("N3");
    if (kind == QLatin1String("under-header")) return QStringLiteral("N2");
    if (kind == QLatin1String("scrollbar-fits")) return QStringLiteral("T12");
    if (kind == QLatin1String("tooltip-tall") || kind == QLatin1String("dialog-wide")) return QStringLiteral("D1");
    if (kind == QLatin1String("icon-colour") || kind == QLatin1String("icon-size") || kind == QLatin1String("width-icon")) return QStringLiteral("I1");
    if (kind == QLatin1String("legend-cut") || kind == QLatin1String("legend-name")) return QStringLiteral("C1");
    if (kind == QLatin1String("resid-title")) return QStringLiteral("C3");
    if (kind == QLatin1String("below-border") || kind == QLatin1String("side-border") || kind == QLatin1String("below-filters")) return QStringLiteral("W7");
    if (kind == QLatin1String("table-rule")) {
        if (text.contains(QLatin1String(" px after '"))) return QStringLiteral("T1");
        if (text.startsWith(QLatin1String("unit font"))) return text.contains(QLatin1String("bold")) ? QStringLiteral("N9") : QStringLiteral("T2");
        if (text.startsWith(QLatin1String("unit "))) return QStringLiteral("T2");
        if (text.startsWith(QLatin1String("trailing control"))) return QStringLiteral("T3");
        if (text.startsWith(QLatin1String("column ")) && text.contains(QLatin1String("over its content"))) return QStringLiteral("T4");
        if (text.startsWith(QLatin1String("scrolls sideways"))) return QStringLiteral("N4");
        return QStringLiteral("T9");
    }
    return QString();
}
}  // namespace

void DemoDriver::check_layout(const QString& frame) {
    // No summary asked for: an ordinary demo run. One asked for but not writable fails the run, so a check that wrote
    // nothing never reads as one that found nothing.
    if (qEnvironmentVariableIsEmpty("EDI_SWEEP_SUMMARY")) return;
    QFile file(qEnvironmentVariable("EDI_SWEEP_SUMMARY"));
    if (!file.open(QIODevice::Append | QIODevice::Text)) {
        fail(QStringLiteral("layout check at %1: cannot write %2").arg(frame, file.fileName()));
        return;
    }
    QTextStream out(&file);
    int hits = 0;
    const auto note = [&](const QString& kind, const QQuickItem* item, const QString& text) {
        const QString path = item_path(item);
        const QString rule = contract_rule(kind, path, text);
        out << frame << '\t' << (rule.isEmpty() ? kind : rule + QLatin1Char(':') + kind) << '\t' << path << '\t'
            << QString(text).replace(QLatin1Char('\n'), QLatin1Char(' ')).left(400) << '\n';
        ++hits;
    };
    struct Shown {
        QQuickItem* item = nullptr;
        QRectF rect;  // painted text, in the window
        QRectF clip;  // what the clipping parents leave of the window
    };
    std::vector<Shown> texts;
    std::vector<std::pair<const QQuickItem*, double>> sideTables;  // a shown sidebar table and its spare
    // By the item tree: pages are made by loaders, outside the window's object tree.
    const std::function<QQuickItem*(QQuickItem*, const QString&)> itemNamed = [&itemNamed](QQuickItem* at, const QString& name) -> QQuickItem* {
        for (QQuickItem* child : at->childItems()) {
            if (child->objectName() == name) return child;
            if (QQuickItem* deeper = itemNamed(child, name)) return deeper;
        }
        return nullptr;
    };
    const QRectF window(0, 0, window_.width(), window_.height());
    // Read once a text is found elided: a scan's rows are many.
    std::optional<QSet<QString>> given;
    const auto userText = [&](const QString& text) {
        if (!given) given = user_texts(qmlEngine(window_.contentItem()), open_project(window_));
        const QString plain = without_tags(text);
        // A line of several parts is the user's when each part is.
        const QStringList parts = plain.split(QStringLiteral(" · "), Qt::SkipEmptyParts);
        return given->contains(plain) || (!parts.isEmpty() && std::all_of(parts.cbegin(), parts.cend(), [&](const QString& part) { return given->contains(part.trimmed()); }));
    };
    // The item whose clip cuts a drawn text, or null. Text cut by a scrolling view's own edge, in a direction the view
    // scrolls, is half scrolled out and shows whole when scrolled to: what that view leaves is then held by the clips
    // around the view.
    const auto cutBy = [&window](QQuickItem* text, QRectF seen) -> QQuickItem* {
        for (QQuickItem* at = text; at != nullptr; at = at->parentItem()) {
            if (!at->clip()) continue;
            const QRectF room = at->mapRectToScene(at->clipRect());
            // A swipe view's list turns pages, it does not scroll one.
            if (at->inherits("QQuickFlickable") && (at->parentItem() == nullptr || !at->parentItem()->inherits("QQuickSwipeView"))) {
                if (at->property("contentHeight").toDouble() > at->height() + 0.5) {
                    seen.setTop(std::max(seen.top(), room.top()));
                    seen.setBottom(std::min(seen.bottom(), room.bottom()));
                }
                if (at->property("contentWidth").toDouble() > at->width() + 0.5) {
                    seen.setLeft(std::max(seen.left(), room.left()));
                    seen.setRight(std::min(seen.right(), room.right()));
                }
                if (seen.width() <= 0 || seen.height() <= 0) return nullptr;
            }
            if (!room.adjusted(-0.5, -0.5, 0.5, 0.5).contains(seen)) return at;
        }
        return window.adjusted(-0.5, -0.5, 0.5, 0.5).contains(seen) ? nullptr : text;
    };
    // `clip` is what every clipping parent leaves.
    std::function<void(QQuickItem*, const QRectF&, double)> walk = [&](QQuickItem* item, const QRectF& clip, double opacity) {
        opacity *= item->opacity();
        if (!item->isVisible() || opacity < 0.01) return;
        const QRectF box = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
        const QRectF inner = item->clip() ? clip.intersected(box) : clip;
        const bool text = item->inherits("QQuickText"), input = item->inherits("QQuickTextInput");
        // An icon is a glyph named by its text in the icon font: never a label to read.
        const bool icon = (text || input) && item->property("font").value<QFont>().family().contains(QLatin1String("Awesome"), Qt::CaseInsensitive);
        if ((text || input) && !icon && !item->property("text").toString().trimmed().isEmpty() && item->width() > 0) {
            const QString value = item->property("text").toString();
            const double content = item->property("contentWidth").toDouble();
            const double height = item->property("contentHeight").toDouble();
            const QRectF painted = item->mapRectToScene(QRectF(0, std::max(0.0, (item->height() - height) / 2),
                                                               std::min(content, item->width()), std::min(height, item->height())));
            // Only what shows: a page or tab off screen (its view clips it) is not in the frame. A table's text counts
            // below the sidebar's fold too: its cut is the same when scrolled to.
            if (inner.intersects(painted) ||
                (text && box.width() > 0 && item->property("truncated").toBool() && item_path(item).contains(QLatin1String(".list/")))) {
                // Cut down to its ellipsis alone: nothing of the text is left to read (the owner, 2026-11-22).
                if (text && item->property("truncated").toBool() && content < item->property("font").value<QFont>().pixelSize() * 1.5)
                    note("only-dots", item, value);
                else if (text && item->property("truncated").toBool()) {
                    // A title shows whole, a structure's name as one too (T9); a number is never cut (T8, ADR-0103 decision
                    // 4); text the user gave elides in its middle, keeping ten characters, and only while its table has no
                    // spare (T10); any other text is a fixed label, in a table too (N1).
                    static const QRegularExpression numeric(QStringLiteral(R"(^[-−+]?[0-9.,]+([eE×][-−+0-9⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)?( ?\S{0,4})?$)"));
                    bool title = false;
                    double spare = 0;
                    for (const QQuickItem* at = item->parentItem(); at != nullptr; at = at->parentItem()) {
                        title = title || QString::fromLatin1(at->metaObject()->className()).startsWith(QLatin1String("ListViewHeader"));
                        if (!at->inherits("QQuickListView") || !at->property("fillerWidth").isValid()) continue;
                        spare = std::max(at->property("fillerWidth").toDouble(), at->property("spareWidth").toDouble());
                        break;
                    }
                    if (title) {
                        note(QStringLiteral("header-cut"), item, value);
                    } else if (userText(value)) {
                        const int kept = kept_characters(item);
                        const bool middle = item->property("elide").toInt() == Qt::ElideMiddle;
                        if (!middle || kept < 10 || spare > 1.0)
                            note(QStringLiteral("elided"), item, QStringLiteral("%1 (%2, %3 characters kept, its table's spare %4 px)").arg(value, middle ? QStringLiteral("middle") : QStringLiteral("not in its middle")).arg(kept).arg(qRound(spare)));
                    } else if (numeric.match(value.trimmed()).hasMatch()) {
                        note(QStringLiteral("number-cut"), item, value);
                    } else {
                        note(QStringLiteral("label-cut"), item, value);
                    }
                }
                else if (content > item->width() + 1.0 && (input || item->property("wrapMode").toInt() == 0) && item->property("color").value<QColor>().alpha() > 0) note("overflow", item, value);
                if (inner.intersects(painted)) {
                    // Only the glyphs' ink counts: an empty descent or line gap cut off takes nothing seen.
                    const QRectF ink = text_rect(item, true);
                    const QRectF seen = ink.isEmpty() ? QRectF() : item->mapRectToScene(ink).adjusted(1, 1, -1, -1);
                    if (QQuickItem* cutter = seen.width() > 0 && seen.height() > 0 ? cutBy(item, seen) : nullptr; cutter != nullptr)
                        note("clipped", item, QStringLiteral("%1 (ink %2,%3 %4x%5 cut by %6)").arg(value).arg(seen.x(), 0, 'f', 1).arg(seen.y(), 0, 'f', 1)
                                                  .arg(seen.width(), 0, 'f', 1).arg(seen.height(), 0, 'f', 1).arg(item_path(cutter)));
                    texts.push_back({item, painted, inner});
                }
            }
        }
        // F4: in every combo box, and on a tab with an arrow, the last glyph drawn ends at least 0.25 em before the arrow,
        // a shortened or custom line too. A button's label fits between its paddings, beside its icon; a tab without an
        // arrow has none to keep clear of, its text is checked as any text is.
        const bool combo = item->inherits("QQuickComboBox"), tab = item->inherits("QQuickTabButton");
        if ((combo || item->inherits("QQuickAbstractButton")) && inner.intersects(box) && item->width() > 1) {
            const double em = item->property("font").value<QFont>().pixelSize();
            QString shown = without_tags(combo ? item->property("displayText").toString() : item->property("text").toString());
            auto* arrow = item->property("indicator").value<QQuickItem*>();
            auto* label = item->property("contentItem").value<QQuickItem*>();
            if (combo || tab) {
                const QRectF drawn = label != nullptr ? drawn_rect(label, true) : QRectF();
                const QRectF mark = arrow != nullptr ? drawn_rect(arrow, true) : QRectF();
                if (!drawn.isEmpty() && !mark.isEmpty() && mark.left() - drawn.right() < em * 0.25 - 0.5)
                    note("combo-gap", item, QStringLiteral("'%1' ends %2 px before its arrow, at least %3").arg(shown).arg(mark.left() - drawn.right(), 0, 'f', 1).arg(em * 0.25, 0, 'f', 1));
            } else if (!shown.isEmpty()) {
                const QFontMetricsF metrics(item->property("font").value<QFont>());
                double room = item->width() - item->property("leftPadding").toDouble() - item->property("rightPadding").toDouble();
                // A label under its icon has the button's whole width.
                if (item->property("display").toInt() != 3 && !item->property("fontIcon").toString().isEmpty()) {
                    // The icon drawn and the gap after it, 1.5 em where the icon is not a text of its own.
                    double iconRoom = em * 1.5;
                    if (label != nullptr)
                        for (const QQuickItem* inside : visual_items(label))
                            if (inside->isVisible() && inside->property("text").toString() == item->property("fontIcon").toString() &&
                                inside->property("font").value<QFont>().family().contains(QLatin1String("Awesome"), Qt::CaseInsensitive))
                                iconRoom = label->property("glyphPadding").isValid() ? label->property("glyphPadding").toDouble()
                                                                                     : inside->implicitWidth() + item->property("spacing").toDouble();
                    room -= iconRoom;
                }
                if (metrics.horizontalAdvance(shown) > room + 0.5)
                    note("combo-gap", item, QStringLiteral("'%1' %2 px in %3 px").arg(shown).arg(qRound(metrics.horizontalAdvance(shown))).arg(qRound(room)));
            }
        }
        // A scroll bar drawn while its view's content fits: it shows only while the content overflows (the owner,
        // 2026-11-22: the Project page's bar showed for seconds after opening).
        if (item->inherits("QQuickScrollBar") && item->property("size").toDouble() >= 0.999 && inner.intersects(box)) {
            auto* handle = item->property("contentItem").value<QQuickItem*>();
            if (opacity * (handle != nullptr ? handle->opacity() : 1.0) > 0.05 && handle != nullptr && handle->isVisible())
                note("scrollbar-fits", item, QString());
        }
        // A parameter's value shown with fewer digits than written while its table shows every column (the owner,
        // 2026-11-23: digits drop only when the column cannot hold them).
        if (item->property("valueText").isValid() && item->property("shownValue").isValid() &&
            item->property("shownValue").toString() != item->property("valueText").toString()) {
            for (const QQuickItem* at = item->parentItem(); at != nullptr; at = at->parentItem())
                if (at->property("droppedColumns").isValid()) {
                    if (at->property("droppedColumns").toList().isEmpty())
                        note("value-short", item, item->property("shownValue").toString() + " for " + item->property("valueText").toString());
                    break;
                }
        }
        // T8 in a table's number cell: at most six significant digits, and when digits drop, never fewer than two. The
        // full form is the cell's own spelling before it is fitted (a parameter's value text, a number as written).
        if (item->property("shownValue").isValid() && (item->property("valueText").isValid() || item->property("numeric").toBool()) &&
            inner.intersects(box) && !awaiting_owner(item)) {
            const QQuickItem* table = item->parentItem();
            while (table != nullptr && !(table->inherits("QQuickListView") && table->objectName().endsWith(QLatin1String(".list")))) table = table->parentItem();
            const QString shown = item->property("shownValue").toString();
            const QString full = item->property(item->property("valueText").isValid() ? "valueText" : "written").toString();
            const int digits = significant_digits(shown), fullDigits = significant_digits(full);
            if (table != nullptr && digits > kNumberDigitsMost)
                note("digits-most", item, QStringLiteral("'%1' %2 significant digits, at most %3").arg(shown).arg(digits).arg(kNumberDigitsMost));
            if (table != nullptr && digits >= 0 && shown != full && digits < kNumberDigitsLeast && fullDigits >= kNumberDigitsLeast)
                note("digits-least", item, QStringLiteral("'%1' for '%2', %3 significant digits, at least %4").arg(shown, full).arg(digits).arg(kNumberDigitsLeast));
        }
        // A chart legend reads whole (the owner, 2026-11-23): a series' own label is never cut, and a datablock's name
        // only when it is longer than the legend's budget.
        if (item->objectName() == QLatin1String("chart.legend.entry") && item->property("fullWidth").toDouble() > item->width() + 0.5) {
            const QString named = item->property("named").toString();
            if (named.isEmpty() || named.size() <= kLegendNameChars)
                note("legend-cut", item, QStringLiteral("%1 cut to %2 of %3 px").arg(item->property("label").toString()).arg(qRound(item->width()))
                                             .arg(qRound(item->property("fullWidth").toDouble())));
            // A long name is the only piece cut, in its middle, and the whole label shows on hover.
            if (!named.isEmpty() && named.size() > kLegendNameChars) {
                QStringList wrong;
                for (QQuickItem* piece : visual_items(item)) {
                    if (!piece->inherits("QQuickText") || !piece->isVisible() || icon_font(piece) || !piece->property("truncated").toBool()) continue;
                    const QString drawnText = without_tags(piece->property("text").toString());
                    if (drawnText != named) wrong << QStringLiteral("'%1' cut").arg(drawnText);
                    else if (piece->property("elide").toInt() != int(Qt::ElideMiddle)) wrong << QStringLiteral("the name not cut in its middle");
                }
                bool hover = false;
                for (QObject* child : item->findChildren<QObject*>())
                    hover = hover || (QString::fromLatin1(child->metaObject()->className()).contains(QLatin1String("ToolTip")) &&
                                      child->property("text").toString().contains(named));
                if (!hover) wrong << QStringLiteral("no tooltip with the whole name");
                if (!wrong.isEmpty()) note("legend-name", item, QStringLiteral("%1: %2").arg(item->property("label").toString(), wrong.join(QLatin1String(", "))));
            }
        }
        // The residual pane's title: the standard size, "meas − calc" or "resid", whole (the owner, 2026-11-23).
        if (item->objectName() == QLatin1String("chart.title.residual") && item->isVisible() && inner.intersects(box)) {
            QQmlEngine* titleEngine = qmlEngine(item);
            QObject* titleSizes = titleEngine != nullptr ? titleEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
            const int standard = titleSizes != nullptr ? qRound(titleSizes->property("fontPixelSize").toDouble()) : 0;
            QString plain = item->property("text").toString();
            plain.remove(QRegularExpression(QStringLiteral("<[^>]*>")));
            const bool known = plain.contains(QLatin1String("calc")) || plain == QLatin1String("resid");
            if (item->property("font").value<QFont>().pixelSize() != standard || !known || item->property("truncated").toBool())
                note("resid-title", item, QStringLiteral("'%1' at %2 px (standard %3)%4").arg(plain).arg(item->property("font").value<QFont>().pixelSize())
                                               .arg(standard).arg(item->property("truncated").toBool() ? ", cut" : ""));
        }
        // The sidebar below the main view is parted from it by a border along its top, full width (the owner,
        // 2026-11-23).
        if (item->objectName().endsWith(QLatin1String(".manualSidebar")) && inner.intersects(box)) {
            QQmlEngine* borderEngine = qmlEngine(item);
            QObject* borderSizes = borderEngine != nullptr ? borderEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
            if (borderSizes != nullptr && borderSizes->property("sideBarBelow").toBool()) {
                const QString page = item->objectName().section(QLatin1Char('.'), 1, 1);
                QQuickItem* border = itemNamed(window_.contentItem(), QStringLiteral("workflow.%1.belowBorder").arg(page));
                const QRectF line = border != nullptr ? border->mapRectToScene(QRectF(0, 0, border->width(), border->height())) : QRectF();
                const QRectF host = item->parentItem() != nullptr ? item->parentItem()->mapRectToScene(QRectF(0, 0, item->parentItem()->width(), 1)) : box;
                if (border == nullptr || !border->isVisible() || line.height() < 0.5 || line.height() > 1.5 || line.width() < host.width() - 1.0 || std::abs(line.top() - host.top()) > 1.0)
                    note("below-border", item, QStringLiteral("border %1").arg(border == nullptr ? QStringLiteral("missing") : QStringLiteral("%1x%2 at %3").arg(line.width()).arg(line.height()).arg(line.top())));
            } else if (borderSizes != nullptr && item->parentItem() != nullptr) {
                // At the side, the base's border beside the sidebar shows.
                const double thickness = borderSizes->property("borderThickness").toDouble();
                bool shown = false;
                for (QQuickItem* child : item->parentItem()->childItems())
                    shown = shown || (child != item && child->isVisible() && std::abs(child->width() - thickness) < 0.5 && child->height() > 1);
                if (!shown) note("side-border", item, QStringLiteral("no border beside the sidebar"));
            }
        }
        // The bottom layout's Analysis sidebar: no name filter, the reset at the end of the pickers' row, and at most
        // about half the window's height (the owner, 2026-11-23; less where the chart needs it, W7).
        if (item->objectName() == QLatin1String("workflow.analysis.manualSidebar") && inner.intersects(box)) {
            QQmlEngine* belowEngine = qmlEngine(item);
            QObject* belowSizes = belowEngine != nullptr ? belowEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
            if (belowSizes != nullptr && belowSizes->property("sideBarBelow").toBool()) {
                QQuickItem* nameFilter = itemNamed(window_.contentItem(), QStringLiteral("parameters.nameFilter"));
                QQuickItem* reset = itemNamed(window_.contentItem(), QStringLiteral("parameters.clearFiltersBelow"));
                QQuickItem* picker = itemNamed(window_.contentItem(), QStringLiteral("parameters.datablock"));
                if (nameFilter != nullptr && nameFilter->isVisible()) note("below-filters", nameFilter, QStringLiteral("name filter shown"));
                if (reset == nullptr || !reset->isVisible() ||
                    (picker != nullptr && std::abs(reset->mapRectToScene(QRectF(0, 0, 1, 1)).top() - picker->mapRectToScene(QRectF(0, 0, 1, 1)).top()) > 1.0))
                    note("below-filters", item, QStringLiteral("reset not in the pickers' row"));
                const double share = (item->parentItem() != nullptr ? item->parentItem()->height() : box.height()) / window_.height();
                if (share > 0.6) note("below-filters", item, QStringLiteral("sidebar %1 % of the window's height").arg(qRound(share * 100)));
            }
        }
        // D1: a dialog is at most its content's width plus 2 em; its rows and values are read as every text is (N1, T8).
        if (item->inherits("QQuickPopupItem") && item->isVisible() && item->parent() != nullptr &&
            QString::fromLatin1(item->parent()->metaObject()->className()).contains(QLatin1String("Dialog"))) {
            const QObject* dialog = item->parent();
            QQmlEngine* dialogEngine = qmlEngine(item);
            QObject* dialogSizes = dialogEngine != nullptr ? dialogEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
            const double em = dialogSizes != nullptr ? dialogSizes->property("fontPixelSize").toDouble() : 14.0;
            const double content = std::max({dialog->property("implicitContentWidth").toDouble(), dialog->property("implicitHeaderWidth").toDouble(),
                                             dialog->property("implicitFooterWidth").toDouble()});
            const double room = dialog->property("availableWidth").toDouble();
            out << frame << "\tD1:checked\t" << item_path(item) << "\tdialog " << room << " px for content " << content << " px\n";
            if (content > 0 && room > content + kDialogSpareEm * em + 0.5)
                note("dialog-wide", item, QStringLiteral("%1 px for content %2 px, at most %3 em more").arg(room).arg(content).arg(kDialogSpareEm));
        }
        // D1: a tooltip has at most 12 lines and stays inside the window (the owner, 2026-11-23: one held a whole log).
        if (item->inherits("QQuickPopupItem") && item->isVisible() &&
            QString::fromLatin1(item->parent() != nullptr ? item->parent()->metaObject()->className() : "").contains(QLatin1String("ToolTip"))) {
            const QRectF tip = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
            const double lineHeight = QFontMetricsF(item->parent()->property("font").value<QFont>()).lineSpacing();
            const int lines = lineHeight > 0 ? int(std::round((item->height() - item->property("topPadding").toDouble() - item->property("bottomPadding").toDouble()) / lineHeight)) : 0;
            if (lines > 12 || !QRectF(0, 0, window_.width(), window_.height()).adjusted(-0.5, -0.5, 0.5, 0.5).contains(tip))
                note("tooltip-tall", item, QStringLiteral("%1 lines, %2x%3 at %4,%5 in a %6x%7 window").arg(lines).arg(qRound(tip.width())).arg(qRound(tip.height()))
                                              .arg(qRound(tip.x())).arg(qRound(tip.y())).arg(window_.width()).arg(window_.height()));
        }
        // The sidebar's width icon centred on the groups' pins' vertical line (the owner, 2026-11-23).
        if (item->objectName().endsWith(QLatin1String(".pin")) && item->width() > 0) {
            if (auto* widthIcon = window_.contentItem()->findChild<QQuickItem*>(QStringLiteral("sideBar.width")); widthIcon != nullptr && widthIcon->isVisible()) {
                const double pinCentre = item->mapRectToScene(QRectF(0, 0, item->width(), 1)).center().x();
                const double iconCentre = widthIcon->mapRectToScene(QRectF(0, 0, widthIcon->width(), 1)).center().x();
                if (std::abs(pinCentre - iconCentre) > 1.0 && std::abs(pinCentre - iconCentre) < 200.0)
                    note("width-icon", item, QStringLiteral("pin centre %1, width icon centre %2").arg(pinCentre, 0, 'f', 1).arg(iconCentre, 0, 'f', 1));
            }
            // Both in the text colour at a title icon's size, unless pinned or pointed at (the owner, 2026-11-23).
            QQmlEngine* iconEngine = qmlEngine(item);
            QObject* colors = iconEngine != nullptr ? iconEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Colors") : nullptr;
            QObject* sizes = iconEngine != nullptr ? iconEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
            if (colors != nullptr && sizes != nullptr) {
                const QColor textColour = colors->property("themeForeground").value<QColor>();
                const QColor accent = colors->property("themeAccent").value<QColor>();
                const QColor hovered = colors->property("themeForegroundHovered").value<QColor>();
                const int size = qRound(sizes->property("fontPixelSize").toDouble());
                QList<QQuickItem*> icons{item};
                if (auto* widthIcon = window_.contentItem()->findChild<QQuickItem*>(QStringLiteral("sideBar.width")); widthIcon != nullptr && widthIcon->isVisible())
                    icons << widthIcon;
                for (QQuickItem* iconItem : icons) {
                    const QColor colour = iconItem->property("color").value<QColor>();
                    if (colour != textColour && colour != accent && colour != hovered)
                        note("icon-colour", iconItem, QStringLiteral("%1, text colour %2").arg(colour.name(), textColour.name()));
                    if (iconItem->property("font").value<QFont>().pixelSize() != size)
                        note("icon-size", iconItem, QStringLiteral("%1 px, title icons %2").arg(iconItem->property("font").value<QFont>().pixelSize()).arg(size));
                }
            }
        }
        // A control shrinks, never vanishes: one shown under an em wide has collapsed (the owner, 2026-11-22).
        if ((item->inherits("QQuickComboBox") || item->inherits("QQuickAbstractButton")) && inner.intersects(box) &&
            item->width() < QFontMetricsF(item->property("font").value<QFont>()).height() && item->height() > 1)
            note("collapsed", item, item->property("displayText").toString() + item->property("text").toString());
        // A table's cell past its list's right edge is cut there (the owner, 2026-11-22: no column cut in any width).
        // Every shown table, on screen or scrolled out of the sidebar's view: its rows exist either way, and a rule broken
        // below the fold is still broken (the owner, 2026-11-22: tables the check did not cover).
        // A table on a page not shown lies outside the window sideways (or under a page in front); one scrolled below
        // the sidebar's fold overlaps the window's columns and its page is the one shown.
        if (item->inherits("QQuickListView") && item->width() > 1 && item->objectName().endsWith(QLatin1String(".list")) &&
            box.right() > window.left() && box.left() < window.right() && clip.intersects(QRectF(box.left(), clip.top(), box.width(), clip.height())) &&
            item->window() != nullptr) {
            auto* content = item->property("contentItem").value<QQuickItem*>();
            double right = box.left();
            int cells = 0;
            QStringList firstRow;  // the first visible row's cells, left edge and width, beside the header's
            for (QQuickItem* row : content != nullptr ? content->childItems() : QList<QQuickItem*>{}) {
                if (!row->isVisible() || row->height() <= 1 || !inner.intersects(row->mapRectToScene(QRectF(0, 0, row->width(), row->height()))))
                    continue;
                int shown = 0;
                for (QQuickItem* cell : row->childItems()) {
                    // A row's background and its mouse area span the row, not a column.
                    if (!cell->isVisible() || cell->width() <= 1 || cell->inherits("QQuickRectangle") || cell->inherits("QQuickMouseArea"))
                        continue;
                    ++shown;
                    const QRectF at = cell->mapRectToScene(QRectF(0, 0, cell->width(), cell->height()));
                    if (cells == 0 && firstRow.isEmpty() && cell->inherits("QQuickRow")) {
                        for (QQuickItem* piece : cell->childItems()) {
                            if (!piece->isVisible()) continue;
                            const QRectF part = piece->mapRectToScene(QRectF(0, 0, piece->width(), piece->height()));
                            firstRow << QStringLiteral("%1+%2").arg(qRound(part.left() - box.left())).arg(qRound(part.width()));
                        }
                    }
                    right = std::max(right, at.right());
                    if (at.right() > box.right() + 1.0) {
                        note("column-cut", cell, QStringLiteral("cell to %1, list to %2").arg(at.right()).arg(box.right()));
                        break;
                    }
                }
                cells = std::max(cells, shown);
            }
            // Each table's width, its rows' widest reach and how many cells a row shows: the widths a row states.
            // The header's cells, left to right: each column's width as drawn.
            QStringList heads;
            if (auto* header = item->property("headerItem").value<QQuickItem*>(); header != nullptr) {
                std::function<void(QQuickItem*)> cellsOf = [&](QQuickItem* parent) {
                    QList<QQuickItem*> children = parent->childItems();
                    std::sort(children.begin(), children.end(), [](QQuickItem* a, QQuickItem* b) { return a->x() < b->x(); });
                    for (QQuickItem* child : children) {
                        if (!child->isVisible() || child->width() < 1) continue;
                        if (child->metaObject()->indexOfProperty("text") >= 0 || child->childItems().isEmpty())
                            heads << QStringLiteral("%1=%2@%3").arg(child->property("text").toString().left(8)).arg(qRound(child->width()))
                                         .arg(qRound(child->mapRectToScene(QRectF(0, 0, 1, 1)).left() - box.left()));
                        else if (heads.size() < 20)
                            cellsOf(child);
                    }
                };
                cellsOf(header);
            }
            // A sidebar table's spare: its width less its content's (Parameters' own full width, else the column model's).
            for (const QQuickItem* at = item; at != nullptr; at = at->parentItem())
                if (at->objectName().endsWith(QLatin1String(".manualSidebar"))) {
                    const double natural = item->property("allColumnsWidth").isValid() ? item->property("allColumnsWidth").toDouble()
                                                                                      : item->property("naturalWidth").toDouble();
                    if (natural > 0) sideTables.push_back({item, item->width() - natural});
                    break;
                }
            note("table", item, QStringLiteral("width %1, rows reach %2, %3 cells, window %4, header %5, row %6")
                                    .arg(box.width()).arg(right - box.left()).arg(cells).arg(window_.width()).arg(heads.join(QLatin1Char(' ')), firstRow.join(QLatin1Char(' '))));
            // The shared column model's rules, per table (ADR-0103 decision 4; the owner, 2026-11-22): every finding
            // is a "table-rule" line naming the table, the window width and the column.
            const auto rule = [&](const QString& what, int column) {
                note("table-rule", item, QStringLiteral("%1 at column %2, window %3").arg(what).arg(column).arg(window_.width()));
            };
            // T5: columns of one parameter kind are equally wide, to the pixel; T11: the row number shows. Each writes a
            // "checked" line, so a table that passes is seen to have been checked.
            {
                const QVariantList kinds = item->property("columnKinds").toList();
                const QVariantList widths = item->property("columnWidths").toList();
                if (!kinds.isEmpty() && kinds.size() == widths.size()) {
                    QHash<QString, double> first;
                    int compared = 0;
                    QStringList unequal;
                    QStringList missing;
                    bool index = false;
                    const int filler = item->property("fillerIndex").isValid() ? item->property("fillerIndex").toInt() : -1;
                    for (qsizetype c = 0; c < kinds.size(); ++c) {
                        const QString kind = kinds[c].toString();
                        if (kind == QLatin1String("index")) index = widths[c].toDouble() > 0.5;
                        if (kind != QLatin1String("value") && kind != QLatin1String("uncertainty") && kind != QLatin1String("change") &&
                            kind != QLatin1String("displacement") && kind != QLatin1String("number"))
                            continue;
                        // The filler holds the table's spare after its content (T4), so it is not compared with its peers
                        // here (below, against its kind, where it has peers); drawn at no width it is missing all the same,
                        // peers or not (a table's only uncertainty column can be its filler).
                        if (c == filler) {
                            if (widths[c].toDouble() < 0.5) missing << QStringLiteral("%1 filler column %2").arg(kind).arg(c);
                            continue;
                        }
                        if (item->property("kindFloors").isValid() && !item->property("kindFloors").toBool())
                            continue;
                        // A column declared by its kind but drawn at no width was squeezed out, not compared: a failure.
                        // (A column hidden on purpose is declared by a number, not a kind.)
                        if (widths[c].toDouble() < 0.5) {
                            missing << QStringLiteral("%1 column %2").arg(kind).arg(c);
                            continue;
                        }
                        ++compared;
                        if (!first.contains(kind))
                            first.insert(kind, widths[c].toDouble());
                        else if (std::abs(first.value(kind) - widths[c].toDouble()) > 0.5)
                            unequal << QStringLiteral("%1 column %2 is %3, the first %4").arg(kind).arg(c).arg(widths[c].toDouble()).arg(first.value(kind));
                    }
                    // The filler too: the part of it before the spare is its kind's reserve, as wide as the other columns of
                    // that kind (T5); only the rest is spare (T4).
                    const QVariantList reserves = item->property("fittedWidths").toList();
                    if (filler >= 0 && filler < kinds.size() && filler < reserves.size() && first.contains(kinds[filler].toString()) && !awaiting_owner(item)) {
                        const QString kind = kinds[filler].toString();
                        out << frame << "\tT5:checked\t" << item_path(item) << "\tfiller column " << filler << " reserves " << reserves[filler].toDouble() << " px, its kind "
                            << first.value(kind) << " px\n";
                        if (std::abs(reserves[filler].toDouble() - first.value(kind)) > 0.5)
                            out << frame << "\tT5:filler\t" << item_path(item) << '\t' << kind << " filler column " << filler << " reserves " << reserves[filler].toDouble()
                                << " px, the other " << kind << " columns " << first.value(kind) << " px\n";
                        // What it is drawn at counts too: a filler squeezed below its kind's width (the spare gone negative) shows
                        // a cut value whatever it reserves.
                        if (filler < widths.size() && widths[filler].toDouble() < first.value(kind) - 0.5)
                            out << frame << "\tT5:filler\t" << item_path(item) << '\t' << kind << " filler column " << filler << " drawn at "
                                << widths[filler].toDouble() << " px, the other " << kind << " columns " << first.value(kind) << " px\n";
                    }
                    if (!missing.isEmpty() && !awaiting_owner(item))
                        out << frame << "\tT5:missing\t" << item_path(item) << '\t' << missing.join(QStringLiteral(", ")) << " drawn at no width\n";
                    // A table with no sized number column has nothing for T5 to compare: say so rather than pass it.
                    if (first.isEmpty())
                        out << frame << "\tT5:inapplicable\t" << item_path(item) << '\t'
                            << (item->property("kindFloors").isValid() && !item->property("kindFloors").toBool() ? "columns not at their kind's width" : "no sized column of a number kind")
                            << '\n';
                    else
                        out << frame << "\tT5:checked\t" << item_path(item) << '\t' << first.size() << " kinds, " << compared << " columns\n";
                    // T12: a table whose rows are taller than it shows its scroll bar.
                    if (item->property("contentHeight").toDouble() > item->height() + 0.5 && item->property("scrollBarPolicy").toInt() != int(Qt::ScrollBarAlwaysOn))
                        out << frame << "\tT12:no-bar\t" << item_path(item) << "\tcontent " << item->property("contentHeight").toDouble() << " px in " << item->height() << " px, no scroll bar\n";
                    // N10: no header repeats its group's title ("ADP type" under "Atomic displacement" says "Type").
                    QString title;
                    for (const QQuickItem* at = item; at != nullptr && title.isEmpty(); at = at->parentItem())
                        if (at->objectName().startsWith(QLatin1String("group.")) && at->property("title").isValid()) title = at->property("title").toString();
                    const QString titleWord = title.section(QLatin1Char(' '), 0, 0).toLower();
                    out << frame << "\tN10:checked\t" << item_path(item) << "\tgroup '" << title << "'\n";
                    if (auto* header = item->property("headerItem").value<QQuickItem*>(); header != nullptr && titleWord.size() > 2)
                        for (QQuickItem* cell : header->findChildren<QQuickItem*>())
                            if (cell->isVisible() && cell->property("text").toString().section(QLatin1Char(' '), 0, 0).toLower() == titleWord)
                                out << frame << "\tN10:repeats\t" << item_path(item) << "\theader '" << cell->property("text").toString() << "' under '" << title << "'\n";
                    // T1 to T4 and T9 write their receipts where they measure (below), never here.
                    for (const QString& line : unequal) out << frame << "\tT5:unequal\t" << item_path(item) << '\t' << line << '\n';
                    if (kinds.contains(QStringLiteral("index"))) {
                        out << frame << "\tT11:checked\t" << item_path(item) << "\trow number " << (index ? "shown" : "missing") << '\n';
                        if (!index) out << frame << "\tT11:missing\t" << item_path(item) << "\tthe row-number column has no width\n";
                    }
                }
            }
            const auto rowOf = [](QQuickItem* root) -> QQuickItem* {
                std::function<QQuickItem*(QQuickItem*)> find = [&](QQuickItem* at) -> QQuickItem* {
                    for (QQuickItem* child : at->childItems()) {
                        if (child->inherits("QQuickRow") && child->isVisible()) return child;
                        if (QQuickItem* deeper = find(child)) return deeper;
                    }
                    return nullptr;
                };
                return root != nullptr ? find(root) : nullptr;
            };
            const auto shownCells = [](QQuickItem* row) {
                QList<QQuickItem*> list;
                if (row == nullptr) return list;
                for (QQuickItem* child : row->childItems())
                    if (child->isVisible() && child->width() > 0.5) list << child;
                std::sort(list.begin(), list.end(), [](QQuickItem* a, QQuickItem* b) { return a->x() < b->x(); });
                // A table's columns never overlap: an item laid over them (a row's highlight, spanning from its left) is
                // not a column, and of two that overlap the wider is dropped.
                for (qsizetype i = 0; i + 1 < list.size();) {
                    if (list[i + 1]->x() < list[i]->x() + list[i]->width() - 1.0)
                        list.removeAt(list[i]->width() >= list[i + 1]->width() ? i : i + 1);
                    else
                        ++i;
                }
                return list;
            };
            QQuickItem* headerRow = rowOf(item->property("headerItem").value<QQuickItem*>());
            QQuickItem* firstContent = nullptr;
            for (QQuickItem* row : content != nullptr ? content->childItems() : QList<QQuickItem*>{}) {
                if (row == item->property("headerItem").value<QQuickItem*>() || !row->isVisible() || row->height() <= 1) continue;
                firstContent = rowOf(row);
                if (firstContent != nullptr) break;
            }
            const QList<QQuickItem*> heads2 = shownCells(headerRow), cells2 = shownCells(firstContent);
            if (item->property("scrollsSideways").toBool()) rule(QStringLiteral("scrolls sideways"), -1);
            // T9: a title starts with a capital letter, but a symbol written as science writes it and a structure's own
            // name, read from the project.
            int titlesRead = 0;
            for (QQuickItem* head : heads2) {
                static const QSet<QString> symbols{
                    QStringLiteral("b"), QStringLiteral("d"), QStringLiteral("h"), QStringLiteral("k"), QStringLiteral("l"), QStringLiteral("x"),
                    QStringLiteral("y"), QStringLiteral("z"), QStringLiteral("h k l"), QStringLiteral("s.u."), QStringLiteral("θ"), QStringLiteral("φ"),
                    QStringLiteral("ϕ"), QStringLiteral("λ"), QStringLiteral("χ²"), QStringLiteral("sin θ/λ"), QStringLiteral("cRp"), QStringLiteral("cRwp"),
                    // March-Dollase: the coefficient and the random fraction.
                    QStringLiteral("r"), QStringLiteral("f rand")};
                const QString title = without_tags(head->property("text").toString());
                if (!title.isEmpty()) ++titlesRead;
                if (title.isEmpty() || !title.at(0).isLower()) continue;
                // Its unit aside: "b (fm)".
                if (symbols.contains(QString(title).remove(QRegularExpression(QStringLiteral(R"(\s*\([^()]*\)$)"))))) continue;
                if (const ProjectViewModel* project = open_project(window_); project != nullptr && head->property("uid").toString().isEmpty()) {
                    const auto& structures = project->project().structures;
                    if (std::any_of(structures.begin(), structures.end(), [&](const auto& structure) { return QString::fromStdString(structure->name.value()) == title; })) continue;
                }
                out << frame << "\tT9:capital\t" << item_path(item) << "\theader '" << title << "' starts with a small letter\n";
            }
            if (titlesRead > 0) out << frame << "\tT9:checked\t" << item_path(item) << '\t' << titlesRead << " header titles\n";
            // T4: the spare (a column wider than its kind's reserve, fittedWidths) is one block, in the column just before
            // the trailing controls, or the last one where there are none. The parameter table places its own (W5).
            qsizetype spareColumn = -1;  // the last content column, which may hold the spare
            if (!(item->property("kindFloors").isValid() && !item->property("kindFloors").toBool())) {
                const QVariantList ruled = item->property("columnWidths").toList(), reserved = item->property("fittedWidths").toList();
                const QVariantList columnsNow = item->property("columns").toList();
                const QVariantList kinds = item->property("columnKinds").toList();
                if (!ruled.isEmpty() && ruled.size() == reserved.size()) {
                    // The last content column: an absent column (no width) and a trailing control come after it. A mark is
                    // content. A table without kinds (Experiments) is read from its first row: a button is a control.
                    QList<qsizetype> wide;
                    for (qsizetype i = 0; i < ruled.size(); ++i)
                        if (ruled[i].toDouble() >= 0.5) wide << i;
                    const bool mapped = !cells2.isEmpty() && cells2.size() == wide.size();
                    const auto control = [&](qsizetype at) {
                        if (kinds.size() == ruled.size()) return kinds[wide[at]].toString().startsWith(QLatin1String("control"));
                        return mapped && cells2[at]->property("fontIcon").isValid();
                    };
                    qsizetype last = wide.size() - 1;
                    while (last > 0 && control(last)) --last;
                    // A mark right before the controls stands with them (the recent projects' status, the owner, 2026-10-27).
                    while (last > 0 && last < wide.size() - 1 && kinds.size() == ruled.size() && kinds[wide[last]].toString() == QLatin1String("mark")) --last;
                    const qsizetype lastData = wide.isEmpty() ? -1 : wide[last];
                    spareColumn = lastData;
                    QStringList spare;
                    for (qsizetype i = 0; i < ruled.size(); ++i)
                        if (columnsNow.value(i).toDouble() == -1 && ruled[i].toDouble() > 0.5 && reserved[i].toDouble() > 0.5 && ruled[i].toDouble() - reserved[i].toDouble() > 1.0 && i != lastData)
                            spare << QStringLiteral("column %1 %2 px over its reserve").arg(i).arg(qRound(ruled[i].toDouble() - reserved[i].toDouble()));
                    out << frame << "\tT4:checked\t" << item_path(item) << '\t' << ruled.size() << " columns, spare in column " << lastData << " only"
                        << (kinds.size() == ruled.size() || mapped ? "" : " (no row to read)") << '\n';
                    for (const QString& line : spare) out << frame << "\tT4:spare\t" << item_path(item) << '\t' << line << '\n';
                }
            }
            // T1: the content of two neighbouring columns is 1 em +- 1 px apart, the row number, a mark and a control
            // included, each at its own content's edge: what the header and the rows draw, and for a number its kind's
            // typical value (T5), in every column of that kind alike. Only an identified empty spare block (T4) is left out
            // of a gap, and a unit's gap is T2's.
            // A table whose rows are still to be measured has not given its cells their margins: there is nothing to measure.
            const bool unmeasured = item->property("unfitted").toBool() || item->property("refitting").toBool() || item->property("measureRunning").toBool();
            // Deferred, never a pass: the report shows the state as not measured until a settled frame measures it.
            if (unmeasured) out << frame << "\tT1:deferred\t" << item_path(item) << "\tnot measured yet, no gaps read\n";
            int pairs = 0;  // neighbouring columns whose gap was measured
            if (!cells2.isEmpty() && !unmeasured) {
                QQmlEngine* gapEngine = qmlEngine(item);
                QObject* gapSizes = gapEngine != nullptr ? gapEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
                const double oneEm = gapSizes != nullptr ? gapSizes->property("fontPixelSize").toDouble() : 14.0;
                const QVariantList widthsNow = item->property("columnWidths").toList(), fittedNow = item->property("fittedWidths").toList();
                const QVariantList declared = item->property("columns").toList(), kindsNow = item->property("columnKinds").toList();
                const QVariantList typesNow = item->property("columnTypes").toList();
                const auto modelOf = [&](qsizetype shownIndex) {
                    for (qsizetype i = 0, shown = 0; i < widthsNow.size(); ++i)
                        if (widthsNow[i].toDouble() > 0.5 && shown++ == shownIndex) return int(i);
                    return -1;
                };
                const auto kindAt = [&](int m) {
                    const QVariantList& list = kindsNow.isEmpty() ? typesNow : kindsNow;
                    const QString kind = m >= 0 && m < list.size() && list[m].typeId() == QMetaType::QString ? list[m].toString() : QString();
                    return kind.isEmpty() && kindsNow.isEmpty() && m > 0 ? item->property("defaultColumnType").toString() : kind;
                };
                // The typical value each kind of number reserves; the parameter table has its own.
                const bool parameterTable = item->property("typicalValue").isValid();
                const auto typical = [&](const QString& kind) {
                    if (kind == QLatin1String("value")) return parameterTable ? QStringLiteral("-0.00000") : QStringLiteral("-0.0000");
                    if (kind == QLatin1String("uncertainty")) return parameterTable ? QStringLiteral("0.00000") : QStringLiteral("0.0000");
                    if (kind == QLatin1String("change")) return parameterTable ? QStringLiteral("100.0% \u2191") : QStringLiteral("999.9%\u2191");
                    if (kind == QLatin1String("displacement")) return QStringLiteral("0.0000");
                    if (kind == QLatin1String("number")) return parameterTable ? QStringLiteral("-inf") : kindsNow.isEmpty() ? QStringLiteral("-0.0000000") : QStringLiteral("-00000.00");
                    return QString();
                };
                // The item whose padding is the cell's margin: the cell, or the text in it.
                const auto padded = [](QQuickItem* cell) -> QQuickItem* {
                    if (cell->property("rightPadding").isValid()) return cell;
                    for (QQuickItem* inside : visual_items(cell))
                        if (inside->isVisible() && (inside->inherits("QQuickText") || inside->inherits("QQuickTextInput"))) return inside;
                    return cell;
                };
                struct Column {
                    int model = -1;
                    QString kind;
                    double left = 0, right = 0;  // the content drawn, or its kind's typical value
                    double farthest = 0;         // where its content may end on rows out of view
                    double boxRight = 0;
                    double spare = 0;            // an identified empty block after its content
                    bool drawn = false;
                };
                const qsizetype shownCount = cells2.size();
                std::vector<Column> columns(static_cast<std::size_t>(shownCount));
                const auto take = [&](const QList<QQuickItem*>& drawn) {
                    if (drawn.size() != shownCount) return;
                    for (qsizetype c = 0; c < shownCount; ++c) {
                        const QRectF part = drawn_rect(drawn[c], false);
                        if (part.isEmpty()) continue;
                        Column& column = columns[static_cast<std::size_t>(c)];
                        column.left = column.drawn ? std::min(column.left, part.left()) : part.left();
                        column.right = column.drawn ? std::max(column.right, part.right()) : part.right();
                        column.drawn = true;
                    }
                };
                take(heads2);
                std::vector<Column> heading = columns;
                int rowsTaken = 0;
                for (QQuickItem* row : content->childItems()) {
                    if (row == item->property("headerItem").value<QQuickItem*>() || !row->isVisible() || row->height() <= 1) continue;
                    if (QQuickItem* cellsRow = rowOf(row); cellsRow != nullptr) {
                        take(shownCells(cellsRow));
                        ++rowsTaken;
                    }
                }
                const bool everyRow = rowsTaken >= item->property("count").toInt();
                // The widest title of each kind's columns: they are equally wide (T5).
                QHash<QString, double> widestTitle;
                for (qsizetype c = 0; c < shownCount; ++c) {
                    const Column& title = heading[static_cast<std::size_t>(c)];
                    const QString kind = kindAt(modelOf(c));
                    if (title.drawn) widestTitle[kind] = std::max(widestTitle.value(kind), title.right - title.left);
                }
                const int filler = item->property("fillerIndex").isValid() ? item->property("fillerIndex").toInt() : -1;
                const double ownSpare = item->property("spareWidth").toDouble();
                const bool ordered = fittedNow.size() == widthsNow.size();
                for (qsizetype c = 0; c < shownCount; ++c) {
                    Column& column = columns[static_cast<std::size_t>(c)];
                    QQuickItem* cell = cells2[c];
                    QQuickItem* margin = padded(cell);
                    const int m = column.model = modelOf(c);
                    column.kind = kindAt(m);
                    const double boxLeft = cell->mapToScene(QPointF(0, 0)).x();
                    column.boxRight = cell->mapToScene(QPointF(cell->width(), 0)).x();
                    const double innerLeft = boxLeft + margin->property("leftPadding").toDouble(), innerRight = column.boxRight - margin->property("rightPadding").toDouble();
                    // A column with nothing drawn in it is measured at its cell's margins.
                    if (!column.drawn) {
                        column.left = innerLeft;
                        column.right = innerRight;
                    }
                    // A change's first text is its arrow, in the icon font.
                    const QFont font = column.kind == QLatin1String("change") && heads2[c]->property("font").isValid() ? heads2[c]->property("font").value<QFont>() : margin->property("font").isValid() ? margin->property("font").value<QFont>() : item->property("font").value<QFont>();
                    if (const QString sample = typical(column.kind); !sample.isEmpty()) {
                        QFont plain = font;
                        plain.setBold(parameterTable && column.kind == QLatin1String("value"));
                        const double reserve = std::min(std::max(QFontMetricsF(plain).horizontalAdvance(sample), kindsNow.isEmpty() ? 0.0 : widestTitle.value(column.kind)), innerRight - innerLeft);
                        // Its end is the column's margin: a letter's overhang ("inf") reaches past it.
                        column.left = std::min(column.left, std::min(column.right, innerRight) - reserve);
                    } else if (column.kind == QLatin1String("index") || (c == 0 && cell->property("marksCurrentRow").toBool())) {
                        // The widest row number, bold as the current row's is, on rows out of view too.
                        QFont bold = font;
                        bold.setBold(true);
                        const double widest = QFontMetricsF(bold).horizontalAdvance(QString::number(std::max(1, item->property("count").toInt())));
                        // T11: the column shows its widest row number whole inside its margins, not only some width.
                        if (column.kind == QLatin1String("index") && !awaiting_owner(item)) {
                            out << frame << "\tT11:checked\t" << item_path(item) << "\trow " << item->property("count").toInt() << ' ' << widest << " px in "
                                << innerRight - innerLeft << " px\n";
                            if (widest > innerRight - innerLeft + 0.5)
                                out << frame << "\tT11:narrow\t" << item_path(item) << "\trow number " << item->property("count").toInt() << " needs " << widest
                                    << " px, the column holds " << innerRight - innerLeft << '\n';
                        }
                        const int alignment = cell->property("horizontalAlignment").toInt();
                        column.left = (alignment & int(Qt::AlignRight)) != 0 ? innerRight - widest : (alignment & int(Qt::AlignHCenter)) != 0 ? (innerLeft + innerRight - widest) / 2 : innerLeft;
                        column.right = column.left + widest;
                    }
                    // An input keeps room for the bold its text takes while it is edited and for the caret (T6): that room is
                    // its content. So is a selector's own column, sized from its options.
                    const bool selector = m >= 0 && m < kindsNow.size() && kindsNow[m].typeId() != QMetaType::QString;
                    if (typical(column.kind).isEmpty() && (selector || cell->inherits("QQuickTextInput"))) {
                        // A text being edited scrolls inside its margins.
                        if (cell->inherits("QQuickTextInput")) column.right = std::min(column.right, innerRight);
                        for (QQuickItem* row : content->childItems()) {
                            if (row == item->property("headerItem").value<QQuickItem*>() || !row->isVisible() || row->height() <= 1) continue;
                            QQuickItem* cellsRow = rowOf(row);
                            const QList<QQuickItem*> rowCells = cellsRow != nullptr ? shownCells(cellsRow) : QList<QQuickItem*>{};
                            if (rowCells.size() != shownCount) continue;
                            QQuickItem* editor = rowCells[c];
                            if (selector) {
                                for (QQuickItem* inside : visual_items(editor))
                                    if (inside->inherits("QQuickComboBox") && inside->isVisible()) column.right = std::max(column.right, innerRight);
                            } else if (!editor->property("readOnly").toBool()) {
                                QFont bold = editor->property("font").value<QFont>();
                                bold.setBold(true);
                                const QFontMetricsF metrics(bold);
                                column.right = std::max(column.right, std::min(innerRight, innerLeft + metrics.horizontalAdvance(editor->property("text").toString()) + metrics.averageCharWidth()));
                            }
                        }
                    }
                    // A column of numbers of its own making declares what it reserves (a scan's values), as T5 does by kind.
                    if (m >= 0 && kindsNow.isEmpty() && heads2[c]->property("reservedWidth").isValid())
                        for (QQuickItem* inside : visual_items(cell))
                            if (inside->property("number").isValid()) column.left = std::min(column.left, boxLeft + inside->parentItem()->parentItem()->x());
                    // A unit keeps its widest's room, where it is drawn, whatever the rows show (T5).
                    if (column.kind == QLatin1String("unit") && parameterTable) {
                        if (!column.drawn) column.left = boxLeft - item->property("unitPull").toDouble();
                        column.right = std::max(column.drawn ? column.right : column.left, column.left + QFontMetricsF(font).horizontalAdvance(QStringLiteral("deg\u00b2")));
                    }
                    column.farthest = column.right;
                    const bool control = column.kind == QLatin1String("control") || column.kind == QLatin1String("mark") || column.kind == QLatin1String("index");
                    if (!everyRow && !control && typical(column.kind).isEmpty() && ordered && m >= 0)
                        column.farthest = std::max(column.right, std::min(innerRight, innerLeft + fittedNow[m].toDouble() - margin->property("leftPadding").toDouble() - margin->property("rightPadding").toDouble()));
                    // The parameter table's name keeps the name budget, whatever the names shown (W5).
                    if (column.kind == QLatin1String("name") && item->property("nameContent").isValid())
                    {
                        const double cellMargin = cell->property("cellMargin").toDouble(), nameEnd = column.boxRight - cellMargin;
                        column.right = std::max(column.right, boxLeft + std::min(cell->width(), item->property("nameContent").toDouble()) - cellMargin);
                        // It may hold up to one column spacing more (the owner, 2026-11-23), which is spare.
                        if (nameEnd - column.right < item->property("columnSpacing").toDouble() + 1.5) column.right = std::max(column.right, nameEnd);
                        column.farthest = column.right;
                    }
                    // The spare the spare column holds past its reserve, less any content that reaches into it.
                    if (m >= 0 && m == filler && ordered && m < declared.size() && declared[m].toDouble() == -1) {
                        const double held = widthsNow[m].toDouble() - fittedNow[m].toDouble() - item->property("autoColumnPadding").toDouble();
                        if (held > 0.5) column.spare = std::max(0.0, held - std::max(0.0, column.farthest - (column.boxRight - held)));
                    }
                }
                const double spacing = cells2.first()->parentItem() != nullptr ? cells2.first()->parentItem()->property("spacing").toDouble() : 0.0;
                const Column* previous = nullptr;
                double between = 0;  // an empty spare column passed since `previous`
                for (const Column& column : columns) {
                    // The parameter table's spare is a column of its own, empty.
                    if (!column.drawn && column.model >= 0 && ownSpare > 0.5 && std::abs(widthsNow[column.model].toDouble() - ownSpare) < 1.0) {
                        between += widthsNow[column.model].toDouble() + spacing;
                        continue;
                    }
                    if (previous != nullptr && column.kind != QLatin1String("unit")) {
                        ++pairs;
                        const double widest = column.left - previous->right - previous->spare - between, least = column.left - previous->farthest - previous->spare - between;
                        if (least > oneEm + 1.0 || widest < oneEm - 1.0)
                            out << frame << "\tT1:gap\t" << item_path(item) << '\t' << QStringLiteral("%1 px between columns %2 and %3 (%4, %5), 1 em is %6")
                                                                                            .arg(least > oneEm + 1.0 ? least : widest, 0, 'f', 1).arg(previous->model).arg(column.model)
                                                                                            .arg(previous->kind.isEmpty() ? QStringLiteral("fixed") : previous->kind, column.kind.isEmpty() ? QStringLiteral("fixed") : column.kind).arg(oneEm) << '\n';
                    }
                    previous = &column;
                    between = 0;
                }
                if (pairs > 0) out << frame << "\tT1:checked\t" << item_path(item) << '\t' << pairs << " gaps measured\n";
            }
            // A settled table that measured no gap is either one with no pair to measure or one whose cells were not read:
            // the second is unsampled, which the report never takes as a pass.
            if (!unmeasured && pairs == 0) {
                qsizetype shownColumns = 0;
                for (const QVariant& width : item->property("columnWidths").toList())
                    if (width.toDouble() > 0.5) ++shownColumns;
                if (shownColumns == 0) shownColumns = std::max(heads2.size(), cells2.size());
                const int rows = item->property("count").toInt();
                if (rows == 0 || shownColumns < 2)
                    out << frame << "\tT1:inapplicable\t" << item_path(item) << '\t' << (rows == 0 ? "no rows" : "one column") << '\n';
                else if (cells2.size() == shownColumns)
                    out << frame << "\tT1:inapplicable\t" << item_path(item) << "\tonly a unit or the spare beside a column\n";
                else
                    out << frame << "\tT1:unsampled\t" << item_path(item) << '\t' << rows << " rows, " << shownColumns << " columns, " << cells2.size()
                        << " cells read\n";
            }
            if (!heads2.isEmpty() && !cells2.isEmpty()) {
                if (heads2.size() != cells2.size()) {
                    const auto geometry = [&](const QList<QQuickItem*>& measured) {
                        QStringList parts;
                        for (QQuickItem* cell : measured)
                            parts << QStringLiteral("%1+%2").arg(qRound(cell->mapRectToScene(QRectF(0, 0, 1, 1)).left() - box.left())).arg(qRound(cell->width()));
                        return parts.join(QLatin1Char(' '));
                    };
                    rule(QStringLiteral("header has %1 cells (%2), row %3 (%4)").arg(heads2.size()).arg(geometry(heads2)).arg(cells2.size()).arg(geometry(cells2)), -1);
                }
                const auto alignmentOf = [](QQuickItem* cell) {
                    const int value = cell->property("horizontalAlignment").isValid() ? cell->property("horizontalAlignment").toInt() : -1;
                    constexpr int horizontal = static_cast<int>(Qt::AlignLeft) | static_cast<int>(Qt::AlignRight) | static_cast<int>(Qt::AlignHCenter);
                    return value < 0 ? -1 : (value & horizontal);
                };
                for (qsizetype c = 0; c < std::min(heads2.size(), cells2.size()); ++c) {
                    const QRectF h = heads2[c]->mapRectToScene(QRectF(0, 0, heads2[c]->width(), 1));
                    const QRectF r = cells2[c]->mapRectToScene(QRectF(0, 0, cells2[c]->width(), 1));
                    if (std::abs(h.left() - r.left()) > 1.0 || std::abs(h.width() - r.width()) > 1.0)
                        rule(QStringLiteral("header %1+%2 vs cell %3+%4").arg(qRound(h.left() - box.left())).arg(qRound(h.width()))
                                 .arg(qRound(r.left() - box.left())).arg(qRound(r.width())), int(c));
                    const int ha = alignmentOf(heads2[c]), ra = alignmentOf(cells2[c]);
                    // Text against text: a container cell (a name's icon line, a check box's holder) lays itself out.
                    if (ha >= 0 && ra >= 0 && ha != ra && !heads2[c]->property("text").toString().isEmpty() && cells2[c]->property("text").isValid())
                        rule(QStringLiteral("header '%1' aligned %2, cell %3 aligned %4").arg(heads2[c]->property("text").toString(), QString::number(ha),
                                                                                            cells2[c]->objectName().isEmpty() ? QString::fromLatin1(cells2[c]->metaObject()->className()) : cells2[c]->objectName(),
                                                                                            QString::number(ra)), int(c));
                    // A title ends (or starts) where its column's values do, whatever the texts: their margins are equal.
                    if (ha >= 0 && ha == ra && !heads2[c]->property("text").toString().isEmpty() && cells2[c]->property("text").isValid() &&
                        heads2[c]->property("rightPadding").isValid() && cells2[c]->property("rightPadding").isValid()) {
                        const char* side = (ha & static_cast<int>(Qt::AlignRight)) != 0 ? "rightPadding" : (ha & static_cast<int>(Qt::AlignLeft)) != 0 ? "leftPadding" : nullptr;
                        if (side != nullptr && std::abs(heads2[c]->property(side).toDouble() - cells2[c]->property(side).toDouble()) > 1.0)
                            rule(QStringLiteral("header '%1' margin %2, cell margin %3").arg(heads2[c]->property("text").toString())
                                     .arg(heads2[c]->property(side).toDouble()).arg(cells2[c]->property(side).toDouble()), int(c));
                    }
                }
                // A trailing control (a check box or a button) sits at the table's right edge.
                QQuickItem* last = cells2.last();
                const bool control = last->inherits("QQuickAbstractButton") || last->property("checked").isValid() ||
                                     last->property("fontIcon").isValid();
                // The row's own right edge, less its padding and a shown vertical scroll bar.
                QQuickItem* rowItem = firstContent->parentItem() != nullptr ? firstContent->parentItem() : item;
                const double barWidth = 0.0;
                const double edge = std::min(box.right() - item->property("borderThickness").toDouble(),
                                             rowItem->mapRectToScene(QRectF(0, 0, rowItem->width(), 1)).right()) -
                                    item->property("rowPadding").toDouble() - barWidth;
                if (!control && last->mapRectToScene(QRectF(0, 0, last->width(), 1)).right() > edge + 1.0)
                    rule(QStringLiteral("row ends at %1, past the table edge %2")
                             .arg(qRound(last->mapRectToScene(QRectF(0, 0, last->width(), 1)).right() - box.left())).arg(qRound(edge - box.left())), int(cells2.size() - 1));
                // Its box, which its insets draw smaller than its cell.
                const double controlRight = last->mapRectToScene(QRectF(0, 0, last->width(), 1)).right() - last->property("rightInset").toDouble();
                if (control)
                    out << frame << "\tT3:checked\t" << item_path(item) << "\t1 trailing control, ends at " << qRound(controlRight - box.left()) << ", edge "
                        << qRound(edge - box.left()) << '\n';
                if (control && std::abs(controlRight - edge) > 1.0)
                    rule(QStringLiteral("trailing control ends at %1, table edge %2")
                             .arg(qRound(controlRight - box.left())).arg(qRound(edge - box.left())), int(cells2.size() - 1));
                // Where a cell's text or parts start and end.
                const auto contentOf = [](QQuickItem* cell) -> std::pair<double, double> {
                    const QRectF at = cell->mapRectToScene(QRectF(0, 0, cell->width(), 1));
                    if (cell->property("contentWidth").isValid() && cell->property("horizontalAlignment").isValid() &&
                        cell->property("text").isValid()) {
                        if (cell->property("text").toString().trimmed().isEmpty()) return {0.0, -1.0};
                        const double textWidth = std::min(cell->property("contentWidth").toDouble(), cell->width());
                        const double leftPad = cell->property("leftPadding").toDouble(), rightPad = cell->property("rightPadding").toDouble();
                        const int alignment = cell->property("horizontalAlignment").toInt();
                        const double start = (alignment & static_cast<int>(Qt::AlignRight)) != 0 ? at.right() - rightPad - textWidth
                                             : (alignment & static_cast<int>(Qt::AlignHCenter)) != 0 ? at.left() + (at.width() - textWidth) / 2
                                                                                                      : at.left() + leftPad;
                        return {start, start + textWidth};
                    }
                    double start = at.right(), end = at.left();
                    for (QQuickItem* child : cell->childItems()) {
                        if (!child->isVisible() || child->width() < 1) continue;
                        const QRectF part = child->mapRectToScene(QRectF(0, 0, child->width(), 1));
                        start = std::min(start, part.left());
                        end = std::max(end, part.right());
                    }
                    return end > start ? std::pair<double, double>{start, end} : std::pair<double, double>{at.left(), at.right()};
                };
                // Two neighbouring header titles read apart: at least half an em between their texts (the owner,
                // 2026-11-23: "Change Min Max" touching).
                {
                    const double least = heads2.first()->property("font").value<QFont>().pixelSize() * 0.5;
                    double previousEnd = -1e9;
                    QString previousText;
                    for (qsizetype c = 0; c < heads2.size(); ++c) {
                        if (!heads2[c]->property("text").isValid() || heads2[c]->property("text").toString().trimmed().isEmpty()) continue;
                        const auto [start, end] = contentOf(heads2[c]);
                        if (end < start) continue;
                        if (start - previousEnd < least - 0.5)
                            rule(QStringLiteral("header '%1' %2 px after '%3', at least %4").arg(heads2[c]->property("text").toString())
                                     .arg(start - previousEnd, 0, 'f', 1).arg(previousText).arg(least, 0, 'f', 1), int(c));
                        previousEnd = end;
                        previousText = heads2[c]->property("text").toString();
                    }
                }
                // A unit one space after its value, in the value's font (the owner, 2026-11-23).
                int unitsRead = 0;
                for (QQuickItem* row : content != nullptr ? content->childItems() : QList<QQuickItem*>{}) {
                    QQuickItem* cellsRow = rowOf(row);
                    if (cellsRow == nullptr || row == item->property("headerItem").value<QQuickItem*>()) continue;
                    const QList<QQuickItem*> rowCells = shownCells(cellsRow);
                    for (qsizetype c = 1; c < rowCells.size(); ++c) {
                        if (!rowCells[c]->objectName().contains(QLatin1String(".units."))) continue;
                        const auto valueAt = contentOf(rowCells[c - 1]), unitAt = contentOf(rowCells[c]);
                        if (valueAt.second < valueAt.first || unitAt.second < unitAt.first) continue;
                        const QFont unitFont = rowCells[c]->property("font").value<QFont>(), valueFont = rowCells[c - 1]->property("font").value<QFont>();
                        const double space = QFontMetricsF(unitFont).horizontalAdvance(QLatin1Char(' '));
                        if (std::abs(unitAt.first - valueAt.second - space) > 1.0)
                            rule(QStringLiteral("unit %1 px after its value, one space is %2 (value '%3' %4+%5 content %6 pad %7, unit at %8)")
                                     .arg(unitAt.first - valueAt.second, 0, 'f', 1).arg(space, 0, 'f', 1)
                                     .arg(rowCells[c - 1]->property("text").toString())
                                     .arg(rowCells[c - 1]->mapRectToScene(QRectF(0, 0, 1, 1)).left(), 0, 'f', 1).arg(rowCells[c - 1]->width(), 0, 'f', 1)
                                     .arg(rowCells[c - 1]->property("contentWidth").toDouble(), 0, 'f', 1).arg(rowCells[c - 1]->property("rightPadding").toDouble(), 0, 'f', 1)
                                     .arg(unitAt.first, 0, 'f', 1), int(c));
                        ++unitsRead;
                        // The value's size, never bold (the owner, 2026-11-23).
                        if (unitFont.pixelSize() != valueFont.pixelSize() || unitFont.bold())
                            rule(QStringLiteral("unit font %1 px%2, value %3 px%4").arg(unitFont.pixelSize()).arg(unitFont.bold() ? " bold" : "")
                                     .arg(valueFont.pixelSize()).arg(valueFont.bold() ? " bold" : ""), int(c));
                        break;
                    }
                }
                if (unitsRead > 0) {
                    out << frame << "\tN9:checked\t" << item_path(item) << '\t' << unitsRead << " units\n";
                    out << frame << "\tT2:checked\t" << item_path(item) << '\t' << unitsRead << " units\n";
                }
                // The kind model: every column at its content width (its header or widest value), the spare only in the
                // last data column, before the controls (the owner, 2026-11-23).
                const QVariantList kinds = item->property("columnKinds").toList();
                const QVariantList widths = item->property("columnWidths").toList();
                const QVariantList fitted = item->property("fittedWidths").toList();
                if (!kinds.isEmpty() && widths.size() == kinds.size()) {
                    for (qsizetype index = 0, shown = 0; index < widths.size(); ++index) {
                        if (widths[index].toDouble() <= 0.5) continue;
                        const qsizetype c = shown++;
                        const QString kind = kinds[index].typeId() == QMetaType::QString ? kinds[index].toString() : QString();
                        // A unit's column is narrower than the unit by the pull that draws it one space after its value.
                        if (kind.isEmpty() || kind == QLatin1String("index") || kind == QLatin1String("control") || kind == QLatin1String("mark") ||
                            kind == QLatin1String("unit") ||
                            index == spareColumn || index >= fitted.size())
                            continue;
                        // A name may hold up to one column spacing of spare (the owner, 2026-11-23).
                        const double allowance = kind == QLatin1String("name") ? 3.0 + item->property("columnSpacing").toDouble() : 3.0;
                        // A table that sizes its empty columns as a fitted value reads (Parameters) holds them at that.
                        double floorWidth = fitted[index].toDouble();
                        if ((kind == QLatin1String("value") || kind == QLatin1String("uncertainty")) && item->property("typicalValue").isValid())
                            floorWidth = std::max(floorWidth, std::ceil(item->property("typicalValue").toDouble()));
                        // Its name keeps the name budget (W5), and its bounds, one kind, are equally wide (T5).
                        if (kind == QLatin1String("name") && item->property("nameContent").isValid())
                            floorWidth = std::max(floorWidth, std::ceil(item->property("nameContent").toDouble()));
                        if (kind == QLatin1String("number") && item->property("typicalValue").isValid())
                            for (qsizetype other = 0; other < kinds.size() && other < fitted.size(); ++other)
                                if (kinds[other].toString() == kind) floorWidth = std::max(floorWidth, fitted[other].toDouble());
                        if (kind == QLatin1String("change") && item->property("typicalChange").isValid())
                            floorWidth = std::max(floorWidth, std::ceil(item->property("typicalChange").toDouble()));
                        if (widths[index].toDouble() > floorWidth + allowance)
                            rule(QStringLiteral("column %1 px over its content %2").arg(qRound(widths[index].toDouble())).arg(qRound(floorWidth)), int(c));
                    }
                }
            }
        }
        // A list's rows that start above the bottom of its header and end below it are partly hidden under it.
        if (item->inherits("QQuickListView") && inner.intersects(box)) {
            auto* header = item->property("headerItem").value<QQuickItem*>();
            auto* content = item->property("contentItem").value<QQuickItem*>();
            if (header != nullptr && content != nullptr && header->isVisible() && header->height() > 1) {
                const double bottom = header->mapRectToScene(QRectF(0, 0, header->width(), header->height())).bottom();
                for (QQuickItem* row : content->childItems()) {
                    if (row == header || !row->isVisible() || row->height() <= 1) continue;
                    const QRectF at = row->mapRectToScene(QRectF(0, 0, row->width(), row->height()));
                    if (at.top() < bottom - 1.0 && at.bottom() > bottom + 1.0 && at.top() >= box.top() - at.height())
                        note("under-header", row, QStringLiteral("row at %1, header to %2").arg(at.top()).arg(bottom));
                }
            }
        }
        for (QQuickItem* child : item->childItems()) walk(child, inner, opacity);
    };
    walk(window_.contentItem(), window, 1.0);
    // The sidebar no longer stops at a page's tables: Auto is one width per window size (the owner, 2026-11-23), so a
    // narrower page shows spare; case 59 checks the width itself (note-sidebar, check-sidebar).
    (void)sideTables;
    // The text and control rules run over every shown item of every frame.
    for (const char* rule : {"T8", "T9", "T10", "T12", "N1", "N2", "N3", "N4", "F4", "I1", "C1", "C3", "D1"})
        out << frame << '\t' << rule << ":checked\tframe\tevery shown item\n";
    // The sidebar rules measured once per frame (ADR-0103 decision 3): its width for W1/W2 (the report compares the
    // pages of one state), W5 the spare before Free at the Auto stop, W6 Compact's columns and filter combos, W7 the
    // bottom layout's height. Each writes its measurement, so a pass shows its number.
    if (QQmlEngine* sizesEngine = qmlEngine(window_.contentItem()); sizesEngine != nullptr) {
        QObject* sizes = sizesEngine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes");
        QObject* preferences = sizesEngine->singletonInstance<QObject*>("edi.app", "Preferences");
        QObject* appSizes = sizesEngine->singletonInstance<QObject*>("edi.app", "AppSizes");
        if (sizes != nullptr && preferences != nullptr && appSizes != nullptr) {
            const QString mode = preferences->property("sideBarWidthMode").toString();
            const bool below = sizes->property("sideBarBelow").toBool();
            const double width = sizes->property("sideBarWidth").toDouble();
            // One column gap is 1 em (T1).
            const double gap = sizes->property("fontPixelSize").toDouble();
            out << frame << "\tW:width\t" << mode << '\t' << (below ? "below " : "side ") << width << " window " << window_.width() << 'x' << window_.height() << '\n';
            // W2: Full is edi main's distance, from the window's right edge to the Experiment button's centre, now.
            if (mode == QLatin1String("full") && !below) {
                const double main = appSizes->property("sideBarMainWidth").toDouble();
                out << frame << "\tW2:checked\tfull\t" << width << " px, edi main's rule " << main << " px\n";
                if (main > 0 && std::abs(main - width) > 0.5) out << frame << "\tW2:rule\tfull\t" << width << " px, edi main's rule " << main << " px\n";
            }
            if (below) {
                // The page shown: a workflow page that is current, else Home, the one page without a sidebar.
                QQuickItem* page = nullptr;
                for (QQuickItem* at : visual_items(window_.contentItem()))
                    if (!at->property("pageName").toString().isEmpty() && at->property("sideBarBelow").isValid() && at->property("current").toBool() && at->isVisible()) page = at;
                QQuickItem* home = itemNamed(window_.contentItem(), QStringLiteral("workflow.home.mainContent"));
                if (page == nullptr) {
                    if (home == nullptr || !on_screen(home)) out << frame << "\tW7:no-page\tsidebar\tno page is shown\n";
                } else {
                    const QString name = QStringLiteral("workflow.%1.sidebarHost").arg(page->property("pageName").toString());
                    QQuickItem* side = itemNamed(page, name);
                    const bool there = side != nullptr && side->isVisible() && side->height() > 1 && on_screen(side);
                    const double height = there ? side->height() : 0;
                    const double share = window_.height() > 0 ? height / window_.height() : 0;
                    out << frame << "\tW7:checked\t" << name << '\t' << QString::number(share * 100, 'f', 1) << " % of the window\n";
                    if (!there) {
                        out << frame << "\tW7:no-sidebar\t" << name << "\tthe page shows no sidebar\n";
                    } else {
                        // At most 70 % of its page.
                        if (const double pageHeight = side->parentItem()->height(); pageHeight > 0 && height > pageHeight * 0.7 + 0.5)
                            out << frame << "\tW7:page\t" << name << '\t' << QString::number(100 * height / pageHeight, 'f', 1) << " % of its page, at most 70 %\n";
                        if (share > 0.52)
                            out << frame << "\tW7:height\t" << name << '\t' << QString::number(share * 100, 'f', 1) << " % of the window, at most 50 % +- 2 %\n";
                        // Below half it gives way to the chart: the main pane's 120 px and the residual's 40 px, with the
                        // project's most Bragg rows (1.5 em each and half an em, a gap on both sides), and no more.
                        const ProjectViewModel* project = open_project(window_);
                        const int rows = project != nullptr ? project->patternBraggRows() : 0;
                        const double em = sizes->property("fontPixelSize").toDouble();
                        const double panes = 160 + em * (rows > 0 ? 0.5 + 1.5 * rows + 2 : 1);
                        // Around the panes: the tab bar 3 em, the selector 3.5, the toolbar and its gaps 5.5, the axis and its title 5.
                        const double need = panes + em * 17;
                        const double pageHeight = side->parentItem()->height(), left = pageHeight - need;
                        const double wanted = left >= em * 14 ? std::min({pageHeight * 0.7, window_.height() * 0.5, left}) : std::min(pageHeight * 0.7, window_.height() * 0.5);
                        if (std::abs(height - wanted) > 2.0)
                            out << frame << "\tW7:chart\t" << name << '\t' << height << " px, " << wanted << " px with " << rows << " Bragg rows\n";
                        // The panes themselves, on a page that shows the pattern.
                        for (QQuickItem* pane : visual_items(window_.contentItem())) {
                            const bool main = pane->objectName() == QLatin1String("chart.view.main"), residual = pane->objectName() == QLatin1String("chart.view.residual");
                            if ((!main && !residual) || !pane->isVisible() || !on_screen(pane) || left < em * 14) continue;
                            const double plot = pane->property("plotArea").toRectF().height();
                            out << frame << "\tW7:checked\t" << pane->objectName() << '\t' << plot << " px\n";
                            if (plot < (main ? 119 : 39)) out << frame << "\tW7:pane\t" << pane->objectName() << '\t' << plot << " px, at least " << (main ? 120 : 40) << '\n';
                        }
                        // It moves with the window and the project's Bragg rows alone, never with the page or a fit (W1).
                        static QHash<QString, double> held;
                        const QString key = QStringLiteral("%1x%2 %3 %4").arg(window_.width()).arg(window_.height()).arg(project != nullptr ? project->name() : QString()).arg(rows);
                        if (held.contains(key) && std::abs(held.value(key) - height) > 0.5)
                            out << frame << "\tW7:moved\t" << name << '\t' << held.value(key) << " -> " << height << " px\n";
                        held.insert(key, height);
                    }
                }
            }
            QQuickItem* parameters = itemNamed(window_.contentItem(), QStringLiteral("parameters.list"));
            if (parameters != nullptr && parameters->isVisible() && on_screen(parameters) && !below) {
                const auto shows = [&](int column) {
                    bool shown = false;
                    QMetaObject::invokeMethod(parameters, "shows", Q_RETURN_ARG(bool, shown), Q_ARG(int, column));
                    return shown;
                };
                if (mode == QLatin1String("auto")) {
                    const double spare = parameters->property("spareWidth").toDouble();
                    const bool stopped = shows(2) && shows(6) && shows(7) && shows(8);
                    out << frame << "\tW5:checked\tparameters\tspare " << spare << " px, all columns " << (stopped ? "shown" : "not all shown") << '\n';
                    if (stopped && spare > gap + 0.5)
                        out << frame << "\tW5:spare\tparameters\t" << spare << " px before Free, at most " << gap << '\n';
                    // Against the ADR's numbers: a sidebar at the Auto stop shows every column, and the name column ends at
                    // the name budget, holding at most one column spacing more (T4 measures the name against it). The
                    // names are read as drawn, uncut, in the rows shown.
                    if (std::abs(gap - kContractFontPx) < 0.01) {
                        const double nameDrawn = widest_drawn_name(parameters);
                        const QVariantList columnWidths = parameters->property("columnWidths").toList();
                        const double nameColumn = columnWidths.size() > 1 ? columnWidths[1].toDouble() : 0;
                        const double margin = appSizes->property("tableCellMargin").toDouble();
                        const double spacing = parameters->property("columnSpacing").toDouble();
                        out << frame << "\tW5:checked\tparameters\tsidebar " << width << " px, name column " << nameColumn << " px, widest drawn name "
                            << nameDrawn << " px, budget " << kNameBudgetPx << " px\n";
                        if (!stopped && width >= kAutoStopPx - 0.5)
                            out << frame << "\tW5:stop\tparameters\t" << width << " px, at the stop " << kAutoStopPx << ", not every column shown\n";
                        if (nameDrawn > kNameBudgetPx + 0.5)
                            out << frame << "\tW5:name\tparameters\ta name drawn to " << nameDrawn << " px, past the budget " << kNameBudgetPx << '\n';
                        if (stopped && (nameColumn < kNameBudgetPx + margin - 0.5 || nameColumn > kNameBudgetPx + margin + spacing + 0.5))
                            out << frame << "\tW5:name-spare\tparameters\tname column " << nameColumn << " px, the budget and its margin " << kNameBudgetPx + margin
                                << " px plus at most " << spacing << '\n';
                    }
                }
                if (mode == QLatin1String("compact")) {
                    QObject* group = parameters;
                    while (group != nullptr && !group->property("pickerRowNeed").isValid()) group = group->parent();
                    const double need = group != nullptr ? group->property("pickerRowNeed").toDouble() : -1;
                    const double room = sizes->property("sideBarContentWidth").toDouble();
                    const bool columns = shows(1) && shows(3) && shows(5) && !shows(4);
                    out << frame << "\tW6:checked\tparameters\tcolumns " << (columns ? "Name Value s.u. Free" : "other") << ", pickers need " << need << " in " << room << '\n';
                    if (!columns || need < 0 || need > room + 0.5)
                        out << frame << "\tW6:compact\tparameters\tcolumns " << (columns ? "right" : "wrong") << ", pickers need " << need << " px in " << room << '\n';
                    // The three pickers' default texts whole, as the boxes draw them ("All categories (58)"), not as the
                    // app computes its need. Another choice may give way to a shorter form, with its tooltip.
                    for (const char* name : {"parameters.datablock", "parameters.category", "parameters.variability"}) {
                        QQuickItem* picker = itemNamed(window_.contentItem(), QString::fromLatin1(name));
                        if (picker == nullptr || !picker->isVisible() || picker->property("currentIndex").toInt() != 0) continue;
                        bool cut = false;
                        const QString drawn = drawn_words(picker->property("contentItem").value<QQuickItem*>(), &cut);
                        const QString whole = without_tags(picker->property("displayText").toString());
                        out << frame << "\tW6:checked\t" << name << "\t'" << drawn << "' for '" << whole << "'\n";
                        if (cut || !QString(drawn).remove(QLatin1Char(' ')).contains(QString(whole).remove(QLatin1Char(' '))))
                            out << frame << "\tW6:picker\t" << name << "\t'" << drawn << "' drawn for '" << whole << '\'' << (cut ? ", cut" : "") << '\n';
                    }
                }
            }
        }
    }
    // The Home wordmark's two words are one logo, set tight, not two controls (N3).
    const auto oneLogo = [](const QQuickItem* a, const QQuickItem* b) {
        const QQuickItem* logo = a->parentItem();
        if (logo == nullptr || logo != b->parentItem()) return false;
        const auto* first = logo->property("prefixItem").value<QQuickItem*>();
        const auto* second = logo->property("suffixItem").value<QQuickItem*>();
        return first != nullptr && second != nullptr && ((a == first && b == second) || (a == second && b == first));
    };
    // A popup (a menu, a tooltip) lies over the page by design: only texts on the same layer can overlap.
    const auto inPopup = [](const QQuickItem* item) {
        for (const QQuickItem* at = item; at != nullptr; at = at->parentItem())
            if (at->inherits("QQuickOverlay") || at->inherits("QQuickPopupItem")) return true;
        return false;
    };
    for (std::size_t i = 0; i < texts.size(); ++i) {
        for (std::size_t j = i + 1; j < texts.size(); ++j) {
            const QRectF both = texts[i].rect.intersected(texts[j].rect).intersected(texts[i].clip).intersected(texts[j].clip);
            if (both.width() > 2 && both.height() > 2 && !texts[i].item->isAncestorOf(texts[j].item) &&
                !texts[j].item->isAncestorOf(texts[i].item) && !oneLogo(texts[i].item, texts[j].item) &&
                inPopup(texts[i].item) == inPopup(texts[j].item))
                note("overlap", texts[i].item, texts[i].item->property("text").toString() + " | " + texts[j].item->property("text").toString());
        }
    }
    // The sidebar's width at this window width (the style's Sizes.sideBarWidth), for the width rule's table.
    QQmlEngine* engine = qmlEngine(window_.contentItem());
    QObject* sizes = engine != nullptr ? engine->singletonInstance<QObject*>("EasyApplication.Gui.Style", "Sizes") : nullptr;
    out << frame << "\tframe\t" << hits << " hits\twindow " << window_.width() << ", sidebar "
        << (sizes != nullptr ? sizes->property("sideBarWidth").toDouble() : -1.0) << '\n';
}

void DemoDriver::wait_scan_then(const std::function<void()>& next, const QString& mode, int waited_ms) {
    QQuickItem* layer = find(QStringLiteral("scanView.%1.layer").arg(mode), false);
    auto* model = layer != nullptr ? layer->property("model").value<ScanViewModel*>() : nullptr;
    // Read once nothing the view shows is waiting (the views read only what they show), and still so a moment later:
    // a view laid out again asks for other rows.
    const bool read = model != nullptr && model->count() > 0 && model->loaded() > 0 && model->pending() == 0;
    if (read && !scan_read_once_) {
        scan_read_once_ = true;
        QTimer::singleShot(kSettleIntervalMs * 3, this,
                           [this, next, mode, waited_ms] { wait_scan_then(next, mode, waited_ms + kSettleIntervalMs * 3); });
        return;
    }
    scan_read_once_ = read;
    if (read) {
        scan_read_once_ = false;
        qWarning("wait-scan %s: %d of %d patterns read after %d ms", qPrintable(mode), model->loaded(), model->count(),
                 waited_ms);
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

void DemoDriver::wait_assistant_then(const std::function<void()>& next, int waited_ms, int idle_polls) {
#if !EDI_APP_ASSISTANT
    // A build without the assistant has no turn to wait for.
    (void)waited_ms;
    (void)idle_polls;
    next();
#else
    QQmlEngine* engine = qmlEngine(window_.contentItem());
    auto* session = engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
    auto* assistant = session ? session->assistant() : nullptr;
    const QString state = assistant ? assistant->state() : QString();
    // Two quiet polls in a row: a turn can pause between its steps.
    const bool quiet = assistant != nullptr && state != QLatin1String("agent_active") && state != QLatin1String("connecting");
    idle_polls = quiet ? idle_polls + 1 : 0;
    if (idle_polls >= 4) {
        std::fprintf(stderr, "docs-capture: assistant %s after %d ms\n", qPrintable(state), waited_ms);
        next();
        return;
    }
    if (waited_ms > 20 * 60 * 1000) {
        fail(QStringLiteral("step %1: the assistant was still working after 20 minutes").arg(steps_[current_].image));
        return;
    }
    QTimer::singleShot(500, this, [this, next, waited_ms, idle_polls] {
        wait_assistant_then(next, waited_ms + 500, idle_polls);
    });
#endif
}

void DemoDriver::wait_online_then(const std::function<void()>& next, int waited_ms) {
    QObject* dialog = window_.findChild<QObject*>(QStringLiteral("onlineLoad"));
    auto* search = dialog != nullptr ? dialog->property("search").value<QObject*>() : nullptr;
    if (search != nullptr && !search->property("busy").toBool()) {
        next();
        return;
    }
    if (waited_ms > kFitWaitMs) {
        fail(QStringLiteral("step %1: the From web search did not finish").arg(steps_[current_].image));
        return;
    }
    QTimer::singleShot(kSettleIntervalMs, this,
                       [this, next, waited_ms] { wait_online_then(next, waited_ms + kSettleIntervalMs); });
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
    // Held, as a drag holds the slider, and released after the last step.
    project->setAdjusting(true);
    const auto release = qScopeGuard([project] { project->setAdjusting(false); });
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
    if (documentation_) {
        grab().save(output_dir_.filePath("failure.png"));
        saveDocumentationManifest("failed", message);
    }
    std::fprintf(stderr, "edi_app --demo: %s\n", qPrintable(message));
    QCoreApplication::exit(1);
}

}  // namespace edi_app
