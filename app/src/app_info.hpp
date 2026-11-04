// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_APP_INFO_HPP
#define EDI_APP_APP_INFO_HPP

#include <QColor>
#include <QDir>
#include <QFileInfo>
#include <QObject>
#include <QPoint>
#include <QString>
#include <QList>
#include <QStringList>
#include <QUrl>
#include <QtQml/qqmlregistration.h>

#include "example_list_model.hpp"

#include "edi/palette.hpp"

// How to cite the app (ADR-0063's Home link), read from the bundled CITATION.cff.
struct Citation {
    Q_GADGET
    QML_VALUE_TYPE(citation)
    Q_PROPERTY(QString text MEMBER text CONSTANT)
    Q_PROPERTY(QString bibtex MEMBER bibtex CONSTANT)
    Q_PROPERTY(QString doi MEMBER doi CONSTANT)
    Q_PROPERTY(QString doiUrl MEMBER doi_url CONSTANT)

   public:
    QString text;
    QString bibtex;
    QString doi;
    QString doi_url;
};

// One day's changes in What's new (ADR-0067): its date (YYYY-MM-DD) and its entries as Markdown, from the bundled
// changelog, the docs site's What's new page.
struct ChangeDay {
    Q_GADGET
    QML_VALUE_TYPE(changeDay)
    Q_PROPERTY(QString date MEMBER date CONSTANT)
    Q_PROPERTY(QString text MEMBER text CONSTANT)

   public:
    QString date;
    QString text;
};

// One written step of a tutorial (ADR-0064): what to do, on which page, the control it names and what should follow,
// and optionally the control that leads to it (`via`, such as a sidebar tab), pointed at while it is not on screen, and
// the condition that lets Next go on (`check`, TutorialPanel.holds).
struct TutorialStep {
    Q_GADGET
    QML_VALUE_TYPE(tutorialStep)
    Q_PROPERTY(QString text MEMBER text CONSTANT)
    // The callout's heading: what the step is about, in one to three words.
    Q_PROPERTY(QString title MEMBER title CONSTANT)
    Q_PROPERTY(QString page MEMBER page CONSTANT)
    Q_PROPERTY(QString target MEMBER target CONSTANT)
    Q_PROPERTY(QString expected MEMBER expected CONSTANT)
    Q_PROPERTY(QString via MEMBER via CONSTANT)
    Q_PROPERTY(QString check MEMBER check CONSTANT)
    // The step describes a tab, which it opens.
    Q_PROPERTY(bool open MEMBER open CONSTANT)
    // The step offers the tutorial's files (app/tutorials/files) to save.
    Q_PROPERTY(bool files MEMBER files CONSTANT)
    // The sidebar tab the step's control is on ("basic", "extras", "text" or "settings"), empty when the step does not
    // depend on one: its own `tab`, else the tab the last sidebar-tab step on the same page opened.
    Q_PROPERTY(QString tab MEMBER tab CONSTANT)
    // A step about a whole area that names nothing in it (the files step): its callout may sit over the area.
    Q_PROPERTY(bool coversTarget MEMBER coversTarget CONSTANT)

   public:
    QString text;
    QString page;
    QString target;
    QString expected;
    QString via;
    QString check;
    bool open = false;
    bool files = false;
    QString tab;
    QString title;
    bool coversTarget = false;
};

// A built-in tutorial, as app/tutorials/manifest.json gives it (ADR-0064).
struct Tutorial {
    Q_GADGET
    QML_VALUE_TYPE(tutorial)
    Q_PROPERTY(QString id MEMBER id CONSTANT)
    Q_PROPERTY(QString title MEMBER title CONSTANT)
    Q_PROPERTY(QString description MEMBER description CONSTANT)
    Q_PROPERTY(QString project MEMBER project CONSTANT)
    Q_PROPERTY(QString start MEMBER start CONSTANT)
    Q_PROPERTY(QStringList completion MEMBER completion CONSTANT)
    Q_PROPERTY(QString stop MEMBER stop CONSTANT)
    Q_PROPERTY(QList<TutorialStep> steps MEMBER steps CONSTANT)
    // Its chips in the Tutorials list, as the Examples list draws them (tagChip).
    Q_PROPERTY(QStringList tagLabels MEMBER tag_labels CONSTANT)
    Q_PROPERTY(QStringList tagIcons MEMBER tag_icons CONSTANT)
    Q_PROPERTY(QStringList tagColors MEMBER tag_colors CONSTANT)
    Q_PROPERTY(QStringList tagDarkColors MEMBER tag_dark_colors CONSTANT)

   public:
    QString id;
    QString title;
    QString description;
    QString project;
    QString start;
    QStringList completion;
    QString stop;
    QList<TutorialStep> steps;
    QStringList tag_labels, tag_icons, tag_colors, tag_dark_colors;
    // Its tags as the manifest gives them, "family:value".
    QStringList tags;
};

// What the app says about itself — its name, version and links. The only source of the identity the user
// sees; the base's own fallback (gui-components ProjectConfig.js) is never shown.
class ApplicationInfo : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(QString name READ name CONSTANT)
    Q_PROPERTY(QString namePrefixForLogo READ namePrefixForLogo CONSTANT)
    Q_PROPERTY(QString nameSuffixForLogo READ nameSuffixForLogo CONSTANT)
    Q_PROPERTY(QString version READ version CONSTANT)
    Q_PROPERTY(QString releaseDate READ releaseDate CONSTANT)
    Q_PROPERTY(QString homepageUrl READ homepageUrl CONSTANT)
    Q_PROPERTY(QString docsUrl READ docsUrl CONSTANT)
    // The documentation's release notes, Home's What's new.
    Q_PROPERTY(QString changesUrl READ changesUrl CONSTANT)
    Q_PROPERTY(QString issuesUrl READ issuesUrl CONSTANT)
    Q_PROPERTY(QString contactUrl READ contactUrl CONSTANT)
    Q_PROPERTY(QString licenseUrl READ licenseUrl CONSTANT)
    Q_PROPERTY(QString appLicenseUrl READ appLicenseUrl CONSTANT)
    Q_PROPERTY(QString copyingUrl READ copyingUrl CONSTANT)
    Q_PROPERTY(QString noticesUrl READ noticesUrl CONSTANT)
    Q_PROPERTY(edi_app::ExampleListModel* tutorialCatalogue READ tutorialCatalogue CONSTANT)
    // edi's own licences, as the About window names them: their SPDX identifiers and their bundled texts, index for
    // index.
    Q_PROPERTY(QStringList appLicenceIds READ appLicenceIds CONSTANT)
    Q_PROPERTY(QStringList appLicenceUrls READ appLicenceUrls CONSTANT)
    Q_PROPERTY(QStringList componentNames READ componentNames CONSTANT)
    Q_PROPERTY(QStringList componentVersions READ componentVersions CONSTANT)
    Q_PROPERTY(QStringList componentLicences READ componentLicences CONSTANT)
    Q_PROPERTY(QStringList componentUses READ componentUses CONSTANT)
    Q_PROPERTY(QString description READ description CONSTANT)
    Q_PROPERTY(QString copyrightHolder READ copyrightHolder CONSTANT)
    Q_PROPERTY(QString developerYearsFrom READ developerYearsFrom CONSTANT)
    Q_PROPERTY(QString developerYearsTo READ developerYearsTo CONSTANT)
    // The element symbols of the core's element table, H to Og: what an atom-type picker lists.
    Q_PROPERTY(QStringList elementSymbols READ elementSymbols CONSTANT)
    // The Performance preferences' thread counts: whether this build can run fills on several threads
    // (a browser without WebAssembly threads cannot), and the largest count it offers.
    Q_PROPERTY(bool engineThreadsSelectable READ engineThreadsSelectable CONSTANT)
    Q_PROPERTY(int engineThreadsMaximum READ engineThreadsMaximum CONSTANT)
    // The most scan files fitted at once: the cores the platform reports.
    Q_PROPERTY(int scanWorkersMaximum READ scanWorkersMaximum CONSTANT)

   public:
    // Made with the window's QML, in the app and in its tests alike: installs the log of what the user does with the
    // controls (UserActionLog, edi ADR-0062).
    explicit ApplicationInfo(QObject* parent = nullptr);

    QString name() const { return QStringLiteral("EasyDiffraction"); }
    QString namePrefixForLogo() const { return QStringLiteral("easy"); }
    QString nameSuffixForLogo() const { return QStringLiteral("diffraction"); }
    // The demo mode's images are a regression pin compared across commits, so they show a fixed
    // identity instead of the build's version and date.
    static void useDemoIdentity();
    static bool demoIdentity();
    QString version() const;
    QString releaseDate() const;
    QString homepageUrl() const { return QStringLiteral("https://easydiffraction.org"); }
    QString docsUrl() const { return QStringLiteral("https://enhantica.github.io/edi/"); }
    QString changesUrl() const { return QStringLiteral("https://enhantica.github.io/edi/changelog/"); }
    QString issuesUrl() const { return QStringLiteral("https://github.com/enhantica/edi/issues"); }
    QString contactUrl() const { return QStringLiteral("https://easydiffraction.org/#contact"); }
    // The licence texts are bundled in the app's resources, so the About window shows them without a network:
    // the source code's (BSD 3-Clause), the distributed app's (GPL-3.0: it links Qt Graphs and Qt Quick 3D;
    // ADR-0015 §6), and the notices of every component the app links or bundles.
    QString licenseUrl() const { return QStringLiteral("qrc:/LICENSE"); }
    QString appLicenseUrl() const { return QStringLiteral("qrc:/app/DISTRIBUTION-LICENSE.md"); }
    QString copyingUrl() const { return QStringLiteral("qrc:/COPYING"); }
    QString noticesUrl() const { return QStringLiteral("qrc:/THIRD-PARTY-NOTICES"); }
    QStringList appLicenceIds() const { return {QStringLiteral("BSD-3-Clause"), QStringLiteral("GPL-3.0-only")}; }
    QStringList appLicenceUrls() const { return {licenseUrl(), copyingUrl()}; }
    // The components this build carries, from DEPENDENCIES.md's column for its surface (the desktop or the web app), in
    // that file's order: their names, versions (empty when none is given), licences and uses, index for index.
    QStringList componentNames() const { return componentColumn(0); }
    QStringList componentVersions() const { return componentColumn(3); }
    QStringList componentLicences() const { return componentColumn(1); }
    QStringList componentUses() const { return componentColumn(2); }
    // The licence text the notices give for the component at `index` in the lists above, without its indent;
    // empty for an index out of range.
    Q_INVOKABLE QString componentLicenceText(int index) const;
    // The text of a bundled licence resource (one of the URLs above); empty for any other URL.
    Q_INVOKABLE QString licenceText(const QString& url) const;
    // The diagnostics view's text (the owner, 2026-10-06): the platform and browser, the build flavour and why it
    // was chosen (web), threads, the Qt version and graphics backend, edi's and crysta's versions with the crysta
    // SDK commit, and the feature switches; one "name: value" line each, to read and to copy.
    Q_INVOKABLE QString diagnostics() const;
    // Puts `text` on the clipboard (the web build's needs the click that asks for it).
    Q_INVOKABLE void copyText(const QString& text) const;
    // How to cite the app, from the bundled CITATION.cff, the one place its citation is kept.
    Q_INVOKABLE Citation citation() const;
    // The built-in tutorials (app/tutorials/manifest.json), in its order.
    Q_INVOKABLE QList<Tutorial> tutorials() const;
    // The same tutorials as a list the Examples filters filter: by text and by the values of their tags.
    edi_app::ExampleListModel* tutorialCatalogue();
    // Writes the tutorials' files (app/tutorials/files: lbco.cif, hrpt.xye) into `folder`; in the browser each goes to
    // the browser to download instead. False if one could not be written.
    Q_INVOKABLE bool saveTutorialFiles(const QUrl& folder) const;
    // The same files in a temporary folder of their own, for Next on a step that loads one: a folder on the disk, or in
    // the browser's memory, where its file chooser puts the files it opens. The folder as a local-file URL, as that
    // chooser hands its files on; empty if one could not be written.
    Q_INVOKABLE QUrl stageTutorialFiles() const;
    // What's new, newest first: the dated sections of the bundled changelog (website/surfaces/docs/changelog.md).
    Q_INVOKABLE QList<ChangeDay> changes() const;
    bool engineThreadsSelectable() const;
    // Twice the cores the platform reports, at least 16 and at most 64: a browser may report fewer cores
    // than the machine has (Brave reports 4 of an M2's 12), so a larger count can still be tried.
    int engineThreadsMaximum() const;
    // Sets the engine's thread count for every fill: 0 for Auto, else that many threads.
    Q_INVOKABLE void setEngineThreads(int count) const;
    int scanWorkersMaximum() const;
    // Sets how many files of a scan are fitted at once (edi/threading.hpp set_scan_workers).
    Q_INVOKABLE void setScanWorkers(int count) const;
    // Writes the settings file to the browser's storage at once (engine_setup.hpp store_settings_now).
    Q_INVOKABLE void storeSettings() const;
    // Where a link inside the bundled licence text at `from` leads, resolved against that text's own location
    // (the app notice's "../COPYING" is qrc:/COPYING): the URL when it is one of the bundled licence texts above,
    // empty for anything else, so a link opens only what licenceText reads.
    Q_INVOKABLE QString licenceLinkTarget(const QString& from, const QString& link) const;

   private:
    // One column of the notices' "Components" list: 0 the name, 1 the licence, 2 the use, 3 the version.
    static QStringList componentColumn(int column);
    edi_app::ExampleListModel* tutorial_catalogue_ = nullptr;

   public:
    QString description() const;
    // The holder of the copyright in edi's source (LICENSE), named in the About dialog.
    QString copyrightHolder() const { return QStringLiteral("EasyScience contributors"); }
    // The About dialog's copyright years, as easydiffractionbeta's (Gui/Globals/Configs.qml): from the
    // EasyDiffraction project's first year to the current release's.
    QString developerYearsFrom() const { return QStringLiteral("2019"); }
    QString developerYearsTo() const { return QStringLiteral("2026"); }
    // ADR-0017 §8, ADR-0022 §4: an element's colour from a type symbol — the core table's colour of
    // edi::element_of(typeSymbol) in `scheme` ("jmol" or "vesta", the structure view's) — or `fallback` for an
    // element the table does not have. The app holds no element colour of its own.
    QStringList elementSymbols() const;
    // The colour at `position` in the palette `scheme` (a token of edi::colour_scheme_from_name, data/palettes; another
    // reads as edi::colour_scheme_or_default does), `count` one past the last position in use, in the theme:
    // edi::figure_colour. The calculated curve's colour in the palette and theme: edi::role_colour.
    Q_INVOKABLE QColor figureColour(const QString& scheme, int position, int count, bool dark) const;
    Q_INVOKABLE QColor calculationColour(const QString& scheme, bool dark) const;
    // How many colours a palette lists (edi::kPaletteColourCount), and whether it keeps its first two for experiments.
    Q_PROPERTY(int paletteColourCount READ paletteColourCount CONSTANT)
    int paletteColourCount() const { return static_cast<int>(edi::kPaletteColourCount); }
    Q_INVOKABLE bool reservesExperimentColours(const QString& scheme) const;
    // A local file's path as the app shows it, and the URL of the folder it is in (the Preferences' settings file).
    Q_INVOKABLE QString localPath(const QUrl& file) const { return QDir::toNativeSeparators(file.toLocalFile()); }
    Q_INVOKABLE QUrl folderOf(const QUrl& file) const {
        return QUrl::fromLocalFile(QFileInfo(file.toLocalFile()).absolutePath());
    }
    // The palettes' tokens and their titles, in the order Preferences lists them (edi::colour_scheme_names), and the
    // token a stored preference stands for (edi::colour_scheme_or_default).
    Q_PROPERTY(QStringList colourSchemes READ colourSchemes CONSTANT)
    Q_PROPERTY(QStringList colourSchemeTitles READ colourSchemeTitles CONSTANT)
    QStringList colourSchemes() const;
    QStringList colourSchemeTitles() const;
    Q_INVOKABLE QString colourSchemeOrDefault(const QString& scheme) const;
    // The scan views' colour maps (edi::scan_colour_map_names, edi ADR-0041), and the one a stored name stands for:
    // itself when listed, else Blue-Red.
    Q_PROPERTY(QStringList scanColourMaps READ scanColourMaps CONSTANT)
    QStringList scanColourMaps() const;
    Q_INVOKABLE QString scanColourMapOrDefault(const QString& name) const;
    // A colour choice's title: a palette's or a map's (edi::scan_colour_map_title).
    Q_INVOKABLE QString scanColourTitle(const QString& choice) const;
    // The Map's directions (edi::scan_map_direction_names) and their titles, the one a stored name stands for (Auto for
    // another), and whether `map` is drawn inverted in `direction` on `background` in the theme
    // (edi::scan_map_inverted).
    Q_PROPERTY(QStringList scanMapDirections READ scanMapDirections CONSTANT)
    Q_PROPERTY(QStringList scanMapDirectionTitles READ scanMapDirectionTitles CONSTANT)
    QStringList scanMapDirections() const;
    QStringList scanMapDirectionTitles() const;
    Q_INVOKABLE QString scanMapDirectionOrDefault(const QString& name) const;
    Q_INVOKABLE bool scanMapInverted(const QString& map, const QString& direction, const QColor& background,
                                     bool dark) const;
    // The Stacked spacing steps (edi::stacked_spacing_names) and their titles, and a step's s (Wide's for another
    // name).
    Q_PROPERTY(QStringList stackedSpacings READ stackedSpacings CONSTANT)
    Q_PROPERTY(QStringList stackedSpacingTitles READ stackedSpacingTitles CONSTANT)
    QStringList stackedSpacings() const;
    QStringList stackedSpacingTitles() const;
    Q_INVOKABLE double stackedSpacingShare(const QString& name) const;
    // `stops` colours sampled evenly along a map in the theme, from its low end to its high end, inverted when
    // `inverted`: a colour bar's gradient.
    Q_INVOKABLE QList<QColor> scanColourStops(const QString& map, bool dark, bool inverted, int stops = 16) const;
    // Where a window of `width` x `height` kept at `x`, `y` opens: there when that point is on a connected screen, else
    // centred on the primary screen's available area (a screen unplugged since).
    Q_INVOKABLE QPoint onScreenPosition(int x, int y, int width, int height) const;
    Q_INVOKABLE QColor elementColor(const QString& typeSymbol, const QColor& fallback,
                                    const QString& scheme = QStringLiteral("jmol")) const;
    // `colour` as drawn flat on any of `backgrounds`: its lightness moved to 2:1 contrast on each, its hue kept (edi
    // ADR-0047).
    Q_INVOKABLE QColor readableColour(const QColor& colour, const QList<QColor>& backgrounds) const;
};

#endif  // EDI_APP_APP_INFO_HPP
