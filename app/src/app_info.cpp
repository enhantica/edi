// SPDX-License-Identifier: BSD-3-Clause
#include "app_info.hpp"

#include <QMap>
#include <QJsonArray>

#include "app_build_info.hpp"
#include "build_version.hpp"
#include "example_list_model.hpp"
#include "user_action_log.hpp"
#include "web_files.hpp"
#include "engine_setup.hpp"
#include "edi/palette.hpp"
#include "edi/scan_views.hpp"
#include "edi/structure_scene.hpp"
#include "edi/threading.hpp"

#include <QClipboard>
#include <QDir>
#include <QFile>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QScreen>
#include <QStandardPaths>
#include <QSGRendererInterface>
#include <QStringList>
#include <QSysInfo>
#include <QThread>
#include <QUrl>
#include <QtGlobal>
#include <algorithm>
#include <cmath>
#include <string_view>

#ifdef _OPENMP
#include <omp.h>
#endif
#ifdef Q_OS_WASM
#include <emscripten/val.h>
#endif

namespace {
bool g_demo_identity = false;

// The bundled resource behind a licence URL the About window offers; empty for any other URL.
QString bundled_resource(const QString& url) {
    for (const char* name : {"LICENSE", "COPYING", "THIRD-PARTY-NOTICES", "app/DISTRIBUTION-LICENSE.md"}) {
        if (url == QStringLiteral("qrc:/") + QLatin1String(name)) {
            return QStringLiteral(":/") + QLatin1String(name);
        }
    }
    return {};
}

QString read_resource(const QString& path) {
    QFile file(path);
    if (path.isEmpty() || !file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}
}  // namespace

ApplicationInfo::ApplicationInfo(QObject* parent) : QObject(parent) { edi_app::UserActionLog::install(); }

void ApplicationInfo::useDemoIdentity() { g_demo_identity = true; }

bool ApplicationInfo::demoIdentity() { return g_demo_identity; }

QString ApplicationInfo::version() const {
    return g_demo_identity ? QStringLiteral("demo") : QString::fromUtf8(edi_app::app_version());
}

QString ApplicationInfo::releaseDate() const {
    return g_demo_identity ? QStringLiteral("demo build") : QString::fromUtf8(edi_app::app_date());
}

QString ApplicationInfo::description() const {
    return tr("EasyDiffraction is a software for calculating diffraction patterns based on structural models and "
              "refining their parameters against experimental data.");
}

QList<Tutorial> ApplicationInfo::tutorials() const {
    const auto read = [](const QString& name) {
        return QJsonDocument::fromJson(read_resource(QStringLiteral(":/edi/tutorials/") + name).toUtf8());
    };
    const auto text = [](const QJsonObject& object, const char* key) {
        return object.value(QLatin1String(key)).toString();
    };
    const auto step = [&text](const QJsonObject& object, const QString& page) {
        // A step's own page, else its tour page's: a step opening a page shows on the page before it.
        return TutorialStep{text(object, "text"),
                            object.contains(QStringLiteral("page")) ? text(object, "page") : page,
                            text(object, "target"),
                            text(object, "expected"),
                            text(object, "via"),
                            text(object, "check"),
                            object.value(QStringLiteral("open")).toBool(),
                            object.value(QStringLiteral("files")).toBool(),
                            text(object, "tab"),
                            text(object, "title"),
                            object.value(QStringLiteral("coversTarget")).toBool()};
    };
    // A step without its own tab is on the tab the last sidebar-tab step on its page opened, so it sets up the same
    // context on Next, Back or a jump.
    const auto placeOnTabs = [](QList<TutorialStep>& steps) {
        const QString prefix = QStringLiteral("sideBar.tab.");
        QString page;
        QString tab;
        for (TutorialStep& step : steps) {
            if (step.page != page) {
                page = step.page;
                tab.clear();
            }
            if (step.target.startsWith(prefix)) {
                tab = step.target.mid(prefix.size());
                continue;
            }
            if (step.tab.isEmpty()) {
                step.tab = tab;
            }
        }
    };
    QList<Tutorial> tutorials;
    for (const QJsonValue& entry : read(QStringLiteral("manifest.json")).object().value(QStringLiteral("tutorials")).toArray()) {
        const QJsonObject object = entry.toObject();
        Tutorial tutorial{text(object, "id"),      text(object, "title"), text(object, "description"),
                          text(object, "project"), text(object, "start"), {},
                          text(object, "stop"),    {}};
        for (const QJsonValue& choice : object.value(QStringLiteral("completion")).toArray()) {
            tutorial.completion.append(choice.toString());
        }
        for (const QJsonValue& value : object.value(QStringLiteral("steps")).toArray()) {
            tutorial.steps.append(step(value.toObject(), {}));
        }
        // "family:value", as the examples' tags; a family the registry does not have is a neutral chip of the value.
        for (const QJsonValue& value : object.value(QStringLiteral("tags")).toArray()) {
            const QString tag = value.toString();
            tutorial.tags.append(tag);
            const qsizetype colon = tag.indexOf(QLatin1Char(':'));
            const QString family = colon < 0 ? QString() : tag.left(colon);
            const QString name = tag.mid(colon + 1);
            const edi_app::TagChip chip = edi_app::tagChip(family, name, name);
            tutorial.tag_labels.append(chip.label);
            tutorial.tag_icons.append(chip.glyph);
            tutorial.tag_colors.append(chip.light);
            tutorial.tag_dark_colors.append(chip.dark);
        }
        // A tour's steps are their own file, one list per page (app/tutorials/tour.json), for other uses to share.
        if (object.contains(QStringLiteral("tour"))) {
            for (const QJsonValue& page : read(text(object, "tour")).object().value(QStringLiteral("pages")).toArray()) {
                for (const QJsonValue& value : page.toObject().value(QStringLiteral("steps")).toArray()) {
                    tutorial.steps.append(step(value.toObject(), text(page.toObject(), "page")));
                }
            }
        }
        placeOnTabs(tutorial.steps);
        tutorials.append(tutorial);
    }
    return tutorials;
}

edi_app::ExampleListModel* ApplicationInfo::tutorialCatalogue() {
    if (tutorial_catalogue_ == nullptr) {
        QList<edi_app::ExampleListModel::Item> items;
        for (const Tutorial& tutorial : tutorials()) {
            items.append({tutorial.id, tutorial.title, tutorial.description, tutorial.tags});
        }
        tutorial_catalogue_ = new edi_app::ExampleListModel(items, this);
    }
    return tutorial_catalogue_;
}

namespace {

// A changelog given to a test run through EDI_CHANGELOG_JSON: JSON text or a file holding it, either a list of
// entries or an object with `entries`; each entry has a `date` and a `text`, or a `changes` list of lines.
QList<ChangeDay> injected_changes(const QByteArray& given) {
    QByteArray json = given.trimmed();
    if (!json.startsWith('[') && !json.startsWith('{')) {
        QFile file(QString::fromLocal8Bit(given));
        json = file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray();
    }
    const QJsonDocument document = QJsonDocument::fromJson(json);
    const QJsonArray entries =
        document.isArray() ? document.array() : document.object().value(QStringLiteral("entries")).toArray();
    QList<ChangeDay> days;
    for (const QJsonValue& value : entries) {
        const QJsonObject entry = value.toObject();
        QString text = entry.value(QStringLiteral("text")).toString();
        for (const QJsonValue& change : entry.value(QStringLiteral("changes")).toArray()) {
            text += QStringLiteral("- ") + change.toString() + QLatin1Char('\n');
        }
        days.append(ChangeDay{entry.value(QStringLiteral("date")).toString(), text});
    }
    return days;
}

}  // namespace

namespace {

// Writes the tutorials' files into `folder`, made if missing, or hands each to the browser to download.
bool write_tutorial_files(const QString& folder, bool download) {
    const QDir source(QStringLiteral(":/edi/tutorials/files"));
    if (!download && !QDir().mkpath(folder)) {
        return false;
    }
    bool saved = true;
    for (const QString& name : source.entryList(QDir::Files)) {
        QFile file(source.filePath(name));
        if (!file.open(QIODevice::ReadOnly)) {
            saved = false;
            continue;
        }
        const QByteArray data = file.readAll();
        if (download) {
            saved = edi_app::WebFiles::download(data, name) && saved;
            continue;
        }
        QFile written(QDir(folder).filePath(name));
        saved = written.open(QIODevice::WriteOnly | QIODevice::Truncate) && written.write(data) == data.size() && saved;
    }
    return saved;
}

}  // namespace

bool ApplicationInfo::saveTutorialFiles(const QUrl& folder) const {
    const bool download = edi_app::WebFiles::available();
    return write_tutorial_files(download ? QString() : folder.toLocalFile(), download);
}

QUrl ApplicationInfo::stageTutorialFiles() const {
    const QString folder = QDir(QStandardPaths::writableLocation(QStandardPaths::TempLocation))
                               .filePath(QStringLiteral("easydiffraction-tutorial"));
    return write_tutorial_files(folder, false) ? QUrl::fromLocalFile(folder) : QUrl();
}

QList<ChangeDay> ApplicationInfo::changes() const {
    QList<ChangeDay> days;
    const QByteArray given = qgetenv("EDI_CHANGELOG_JSON");
    if (!given.isEmpty()) {
        days = injected_changes(given);
    }
    // A `## YYYY-MM-DD` heading starts a day; its lines up to the next heading are its entries.
    static const QRegularExpression heading(QStringLiteral("^## (\\d{4}-\\d{2}-\\d{2})\\s*$"));
    const QString bundled = given.isEmpty() ? read_resource(QStringLiteral(":/edi/changelog.md")) : QString();
    for (const QString& line : bundled.split(QLatin1Char('\n'))) {
        const QRegularExpressionMatch match = heading.match(line);
        if (match.hasMatch()) {
            days.append(ChangeDay{match.captured(1), {}});
        } else if (line.startsWith(QLatin1String("## "))) {
            days.append(ChangeDay{});  // an undated section belongs to no day
        } else if (!days.isEmpty()) {
            days.last().text += line + QLatin1Char('\n');
        }
    }
    days.removeIf([](const ChangeDay& day) { return day.date.isEmpty(); });
    for (ChangeDay& day : days) {
        day.text = day.text.trimmed();
    }
    std::sort(days.begin(), days.end(), [](const ChangeDay& a, const ChangeDay& b) { return a.date > b.date; });
    return days;
}

Citation ApplicationInfo::citation() const {
    // The top-level `key: "value"` lines and the authors' names of a CITATION.cff; nothing else is read.
    QMap<QString, QString> fields;
    QStringList authors;
    for (const QString& raw : read_resource(QStringLiteral(":/CITATION.cff")).split(QLatin1Char('\n'))) {
        const QString line = raw.trimmed();
        const auto value = [&](qsizetype colon) {
            QString text = line.mid(colon + 1).trimmed();
            if (text.size() >= 2 && text.startsWith(QLatin1Char('"')) && text.endsWith(QLatin1Char('"'))) {
                text = text.mid(1, text.size() - 2);
            }
            return text;
        };
        if (line.startsWith(QLatin1String("- name:"))) {
            authors.append(value(line.indexOf(QLatin1Char(':'))));
        } else if (!raw.startsWith(QLatin1Char(' ')) && !line.startsWith(QLatin1Char('#'))) {
            const qsizetype colon = line.indexOf(QLatin1Char(':'));
            if (colon > 0) {
                fields.insert(line.left(colon), value(colon));
            }
        }
    }
    const QString year = fields.value(QStringLiteral("date-released")).left(4);
    const QString doi = fields.value(QStringLiteral("doi"));
    const QString doi_url = doi.isEmpty() ? QString() : QStringLiteral("https://doi.org/") + doi;
    const QString title = fields.value(QStringLiteral("title"));
    const QString version = fields.value(QStringLiteral("version"));
    const QString who = authors.join(QStringLiteral(", "));
    const QString text = QStringLiteral("%1 (%2). %3 (version %4) [Computer software]. %5")
                             .arg(who, year, title, version, doi_url);
    const QString bibtex = QStringLiteral("@software{easydiffraction,\n  author = {{%1}},\n  title = {%2},\n"
                                          "  year = {%3},\n  version = {%4},\n  doi = {%5},\n  url = {%6}\n}")
                               .arg(who, title, year, version, doi, doi_url);
    return {text, bibtex, doi, doi_url};
}

QString ApplicationInfo::licenceText(const QString& url) const { return read_resource(bundled_resource(url)); }

QString ApplicationInfo::licenceLinkTarget(const QString& from, const QString& link) const {
    const QString target = QUrl(from).resolved(QUrl(link)).toString();
    return bundled_resource(from).isEmpty() || bundled_resource(target).isEmpty() ? QString() : target;
}

// DEPENDENCIES.md's component rows this build carries: every table under the header `Component | Version | Licence |
// Desktop app | Web app | Python package | CLI | In edi`, a row whose cell for this build's surface is not empty or
// "—". A surface's own version, in brackets in its cell, replaces the Version column's.
QStringList ApplicationInfo::componentColumn(int column) {
#ifdef Q_OS_WASM
    constexpr int kSurface = 4;
#else
    constexpr int kSurface = 3;
#endif
    static const QStringList kHeader{"Component", "Version", "Licence", "Desktop app", "Web app", "Python package", "CLI",
                                     "In edi"};
    const auto cells_of = [](const QString& line) {
        QStringList cells = line.trimmed().split(QLatin1Char('|'));
        cells.removeFirst();
        cells.removeLast();
        for (QString& cell : cells) {
            cell = cell.trimmed();
        }
        return cells;
    };
    QStringList values;
    bool inTable = false;
    for (const QString& line : read_resource(QStringLiteral(":/DEPENDENCIES.md")).split(QLatin1Char('\n'))) {
        if (!line.startsWith(QLatin1Char('|'))) {
            inTable = false;
            continue;
        }
        const QStringList cells = cells_of(line);
        if (cells.value(0) == QLatin1String("Component")) {
            inTable = cells == kHeader;
            continue;
        }
        if (!inTable || cells.size() != kHeader.size() || cells[0].startsWith(QLatin1String("---"))) {
            continue;
        }
        const QString& carried = cells[kSurface];
        if (carried.isEmpty() || carried == QStringLiteral("\u2014")) {
            continue;
        }
        switch (column) {
            case 0: values.append(cells[0]); break;
            case 1: values.append(cells[2]); break;
            case 2: values.append(cells[7]); break;
            default: {
                static const QRegularExpression kOwnVersion(QStringLiteral("\\(([0-9][0-9A-Za-z.]*)\\)"));
                const QRegularExpressionMatch own = kOwnVersion.match(carried);
                values.append(own.hasMatch() ? own.captured(1) : cells[1]);
            }
        }
    }
    return values;
}

// The notices' "## <name>" section of a component: its indented licence text, the indent removed.
QString ApplicationInfo::componentLicenceText(int index) const {
    const QStringList names = componentNames();
    if (index < 0 || index >= names.size()) {
        return {};
    }
    const QStringList lines = read_resource(QStringLiteral(":/THIRD-PARTY-NOTICES")).split(QLatin1Char('\n'));
    const QString heading = QStringLiteral("## ") + names[index];
    QStringList text;
    bool inSection = false;
    for (const QString& line : lines) {
        if (line.startsWith(QLatin1Char('#'))) {
            if (inSection) {
                break;
            }
            inSection = line == heading;
            continue;
        }
        if (inSection && (text.size() > 0 || line.startsWith(QLatin1String("    ")))) {
            text.append(line.startsWith(QLatin1String("    ")) ? line.mid(4) : line);
        }
    }
    while (!text.isEmpty() && text.last().trimmed().isEmpty()) {
        text.removeLast();
    }
    return text.join(QLatin1Char('\n'));
}

QStringList ApplicationInfo::elementSymbols() const {
    QStringList symbols;
    for (const edi::ElementStyle& style : edi::element_style_table()) {
        symbols.append(QString::fromStdString(style.symbol));
    }
    return symbols;
}

namespace {
edi::ColourScheme colour_scheme(const QString& name) { return edi::colour_scheme_or_default(name.toStdString()); }
}  // namespace

QColor ApplicationInfo::figureColour(const QString& scheme, int position, int count, bool dark) const {
    return QColor(QString::fromStdString(edi::figure_colour(colour_scheme(scheme),
                                                            static_cast<std::size_t>(std::max(position, 0)),
                                                            static_cast<std::size_t>(std::max(count, 1)), dark)));
}

QColor ApplicationInfo::calculationColour(const QString& scheme, bool dark) const {
    return QColor(
        QString::fromStdString(edi::role_colour(colour_scheme(scheme), edi::ChartRole::TotalCalculation, dark)));
}

bool ApplicationInfo::reservesExperimentColours(const QString& scheme) const {
    return edi::reserves_experiment_colours(colour_scheme(scheme));
}

QPoint ApplicationInfo::onScreenPosition(int x, int y, int width, int height) const {
    const QList<QScreen*> screens = QGuiApplication::screens();
    for (const QScreen* screen : screens) {
        if (screen->virtualGeometry().contains(x, y)) {
            return {x, y};
        }
    }
    const QScreen* primary = QGuiApplication::primaryScreen();
    if (primary == nullptr) {
        return {x, y};
    }
    const QRect area = primary->availableGeometry();
    return {area.x() + std::max(0, (area.width() - width) / 2), area.y() + std::max(0, (area.height() - height) / 2)};
}

QStringList ApplicationInfo::colourSchemes() const {
    QStringList names;
    for (const std::string_view name : edi::colour_scheme_names()) {
        names.append(QString::fromUtf8(name.data(), static_cast<qsizetype>(name.size())));
    }
    return names;
}

QStringList ApplicationInfo::colourSchemeTitles() const {
    QStringList titles;
    for (const std::string_view name : edi::colour_scheme_names()) {
        const std::string_view title = edi::colour_scheme_title(colour_scheme(QString::fromUtf8(name.data(), static_cast<qsizetype>(name.size()))));
        titles.append(QString::fromUtf8(title.data(), static_cast<qsizetype>(title.size())));
    }
    return titles;
}

QString ApplicationInfo::colourSchemeOrDefault(const QString& scheme) const {
    const std::string_view name = edi::colour_scheme_names()[static_cast<std::size_t>(colour_scheme(scheme))];
    return QString::fromUtf8(name.data(), static_cast<qsizetype>(name.size()));
}

QStringList ApplicationInfo::scanColourMaps() const {
    QStringList names;
    for (const std::string& name : edi::scan_colour_map_names()) {
        names.append(QString::fromStdString(name));
    }
    return names;
}

QString ApplicationInfo::scanColourMapOrDefault(const QString& name) const {
    const std::vector<std::string>& names = edi::scan_colour_map_names();
    return std::find(names.begin(), names.end(), name.toStdString()) != names.end() ? name : QStringLiteral("blue-red");
}

QString ApplicationInfo::scanColourTitle(const QString& choice) const {
    const std::optional<edi::ColourScheme> scheme = edi::colour_scheme_from_name(choice.toStdString());
    if (scheme) {
        const std::string_view title = edi::colour_scheme_title(*scheme);
        return QString::fromUtf8(title.data(), static_cast<qsizetype>(title.size()));
    }
    return QString::fromStdString(edi::scan_colour_map_title(choice.toStdString()));
}

QStringList ApplicationInfo::stackedSpacings() const {
    QStringList names;
    for (const std::string& name : edi::stacked_spacing_names()) {
        names.append(QString::fromStdString(name));
    }
    return names;
}

QStringList ApplicationInfo::stackedSpacingTitles() const {
    QStringList titles;
    for (const std::string& name : edi::stacked_spacing_names()) {
        titles.append(QString::fromStdString(edi::stacked_spacing_title(edi::stacked_spacing_or_default(name))));
    }
    return titles;
}

double ApplicationInfo::stackedSpacingShare(const QString& name) const {
    return edi::stacked_spacing_share(edi::stacked_spacing_or_default(name.toStdString()));
}

QStringList ApplicationInfo::scanMapDirections() const {
    QStringList names;
    for (const std::string& name : edi::scan_map_direction_names()) {
        names.append(QString::fromStdString(name));
    }
    return names;
}

QStringList ApplicationInfo::scanMapDirectionTitles() const {
    QStringList titles;
    for (const std::string& name : edi::scan_map_direction_names()) {
        titles.append(QString::fromStdString(edi::scan_map_direction_title(edi::scan_map_direction_or_default(name))));
    }
    return titles;
}

QString ApplicationInfo::scanMapDirectionOrDefault(const QString& name) const {
    const edi::ScanMapDirection direction = edi::scan_map_direction_or_default(name.toStdString());
    return QString::fromStdString(edi::scan_map_direction_names()[static_cast<std::size_t>(direction)]);
}

bool ApplicationInfo::scanMapInverted(const QString& map, const QString& direction, const QColor& background,
                                      bool dark) const {
    return edi::scan_map_inverted(edi::scan_colour_map_or_default(map.toStdString()),
                                  edi::scan_map_direction_or_default(direction.toStdString()),
                                  background.name(QColor::HexRgb).toStdString(), dark);
}

QList<QColor> ApplicationInfo::scanColourStops(const QString& map, bool dark, bool inverted, int stops) const {
    const std::vector<edi::ScanMapColour> table =
        edi::scan_colour_map_table(edi::scan_colour_map_or_default(map.toStdString()), dark);
    QList<QColor> out;
    const int count = std::max(stops, 2);
    for (int i = 0; i < count; ++i) {
        const auto at = static_cast<std::size_t>(
            std::lround(static_cast<double>(i) / (count - 1) * static_cast<double>(table.size() - 1)));
        const edi::ScanMapColour& colour = table[inverted ? table.size() - 1 - at : at];
        out.append(QColor(colour.r, colour.g, colour.b));
    }
    return out;
}

QColor ApplicationInfo::elementColor(const QString& typeSymbol, const QColor& fallback, const QString& scheme) const {
    const edi::ColorScheme colors = scheme == QLatin1String("vesta") ? edi::ColorScheme::Vesta : edi::ColorScheme::Jmol;
    const edi::ElementColor found = edi::element_color(edi::element_of(typeSymbol.toStdString()), colors);
    return found.known ? QColor(found.color.r, found.color.g, found.color.b) : fallback;
}

QColor ApplicationInfo::readableColour(const QColor& colour, const QList<QColor>& backgrounds) const {
    // A translucent background is taken as opaque: what shows through it is the same theme's background.
    std::vector<std::string> hexes;
    for (const QColor& background : backgrounds) {
        hexes.push_back(background.name(QColor::HexRgb).toStdString());
    }
    return QColor(QString::fromStdString(edi::readable_colour(colour.name(QColor::HexRgb).toStdString(), hexes)));
}

namespace {

QString graphics_api(QSGRendererInterface::GraphicsApi api) {
    switch (api) {
        case QSGRendererInterface::Software: return QStringLiteral("software");
        case QSGRendererInterface::OpenGL: return QStringLiteral("OpenGL");
        case QSGRendererInterface::Direct3D11: return QStringLiteral("Direct3D 11");
        case QSGRendererInterface::Direct3D12: return QStringLiteral("Direct3D 12");
        case QSGRendererInterface::Vulkan: return QStringLiteral("Vulkan");
        case QSGRendererInterface::Metal: return QStringLiteral("Metal");
        case QSGRendererInterface::Null: return QStringLiteral("none");
        default: return QStringLiteral("other (%1)").arg(static_cast<int>(api));
    }
}

}  // namespace

QString ApplicationInfo::diagnostics() const {
    QStringList lines;
    const auto add = [&lines](const QString& name, const QString& value) { lines.append(name + QStringLiteral(": ") + value); };
    add(QStringLiteral("EasyDiffraction"),
        QString::fromUtf8(edi_app::app_version()) + QStringLiteral(" (") + QString::fromUtf8(edi_app::app_date()) +
            QStringLiteral(")"));
    add(QStringLiteral("crysta"), QStringLiteral(EDI_APP_CRYSTA_VERSION));
    add(QStringLiteral("crysta SDK commit"), QStringLiteral(EDI_APP_CRYSTA_COMMIT));
    add(QStringLiteral("Platform"), QSysInfo::prettyProductName() + QStringLiteral(" (") + QSysInfo::currentCpuArchitecture() +
                                        QStringLiteral(", ") + QSysInfo::kernelType() + QStringLiteral(" ") +
                                        QSysInfo::kernelVersion() + QStringLiteral(")"));
    add(QStringLiteral("Qt"), QString::fromLatin1(qVersion()) + QStringLiteral(", platform plugin ") +
                                  QGuiApplication::platformName());
    QString graphics = QStringLiteral("no window yet");
    for (QWindow* window : QGuiApplication::topLevelWindows()) {
        if (auto* quick = qobject_cast<QQuickWindow*>(window); quick != nullptr && quick->rendererInterface() != nullptr) {
            graphics = graphics_api(quick->rendererInterface()->graphicsApi());
            break;
        }
    }
    add(QStringLiteral("Graphics backend"), graphics);
    add(QStringLiteral("Threads (ideal)"), QString::number(QThread::idealThreadCount()));
#ifdef _OPENMP
    add(QStringLiteral("Threads (OpenMP team)"), QString::number(omp_get_max_threads()));
#else
    add(QStringLiteral("Threads (OpenMP team)"), QStringLiteral("no OpenMP"));
#endif
    // The engine's own report: which backend its parallel fill runs on, with how many threads, and SIMD.
    const edi::EngineThreading engine = edi::engine_threading();
    add(QStringLiteral("Engine backend"), QString::fromLatin1(engine.backend));
    const int threads = edi::engine_threads_setting();
    add(QStringLiteral("Threads per calculation (preference)"), threads > 0 ? QString::number(threads) : QStringLiteral("Auto"));
    add(QStringLiteral("Parallel fits in a scan (preference)"), QString::number(edi::scan_workers_setting()));
    add(QStringLiteral("Engine workers"), QString::number(engine.workers));
    add(QStringLiteral("WebAssembly SIMD"), engine.wasm_simd ? QStringLiteral("on") : QStringLiteral("off"));
#ifdef Q_OS_WASM
    using emscripten::val;
    const val window = val::global("window");
    const val navigator = val::global("navigator");
    add(QStringLiteral("Browser"), QString::fromStdString(navigator["userAgent"].as<std::string>()));
    add(QStringLiteral("Browser cores (hardwareConcurrency)"),
        QString::number(navigator["hardwareConcurrency"].isNumber() ? navigator["hardwareConcurrency"].as<int>() : 0));
    add(QStringLiteral("crossOriginIsolated"), window["crossOriginIsolated"].as<bool>() ? QStringLiteral("yes") : QStringLiteral("no"));
    add(QStringLiteral("SharedArrayBuffer"), window["SharedArrayBuffer"].isUndefined() ? QStringLiteral("absent") : QStringLiteral("present"));
    add(QStringLiteral("Service worker controls the page"),
        !navigator["serviceWorker"].isUndefined() && !navigator["serviceWorker"]["controller"].isNull() ? QStringLiteral("yes") : QStringLiteral("no"));
    // What the start page chose and why (app/web/index.html records it).
    const val info = window["ediBuildInfo"];
    if (info.isUndefined() || info.isNull()) {
        add(QStringLiteral("Build"), QStringLiteral("unknown (the start page recorded nothing)"));
    } else {
        const QJsonObject recorded =
            QJsonDocument::fromJson(QByteArray::fromStdString(val::global("JSON").call<std::string>("stringify", info))).object();
        for (auto it = recorded.begin(); it != recorded.end(); ++it) {
            add(QStringLiteral("Build ") + it.key(), it.value().isString() ? it.value().toString()
                                                    : it.value().isBool() ? (it.value().toBool() ? QStringLiteral("yes") : QStringLiteral("no"))
                                                    : QString::fromUtf8(QJsonDocument(QJsonObject{{QStringLiteral("v"), it.value()}}).toJson(QJsonDocument::Compact)));
        }
    }
#ifdef __EMSCRIPTEN_PTHREADS__
    add(QStringLiteral("Build flavour"), QStringLiteral("multithreaded (WebAssembly threads)"));
#else
    add(QStringLiteral("Build flavour"), QStringLiteral("single-threaded (no WebAssembly threads)"));
#endif
#else
    add(QStringLiteral("Build flavour"), QStringLiteral("desktop, multithreaded"));
#endif
    return lines.join(QLatin1Char('\n'));
}

void ApplicationInfo::copyText(const QString& text) const { QGuiApplication::clipboard()->setText(text); }

bool ApplicationInfo::engineThreadsSelectable() const {
    return std::string_view(edi::engine_threading().backend) != "serial";
}

int ApplicationInfo::engineThreadsMaximum() const { return std::clamp(2 * QThread::idealThreadCount(), 16, 64); }

void ApplicationInfo::setEngineThreads(int count) const { edi::set_engine_threads(count); }

int ApplicationInfo::scanWorkersMaximum() const { return std::max(1, QThread::idealThreadCount()); }

void ApplicationInfo::setScanWorkers(int count) const { edi::set_scan_workers(count); }

void ApplicationInfo::storeSettings() const { edi_app::store_settings_now(); }
