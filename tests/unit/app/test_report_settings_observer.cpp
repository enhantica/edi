// SPDX-License-Identifier: BSD-3-Clause
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>
#include <QtTest/qtestkeyboard.h>

#include <QAnimationDriver>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QDir>
#include <QDirIterator>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QElapsedTimer>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QJSEngine>
#include <QJSValue>
#include <QJsonDocument>
#include <QKeyEvent>
#include <QLoggingCategory>
#include <QMetaProperty>
#include <QMimeData>
#include <QMutex>
#include <QMutexLocker>
#include <QPainter>
#include <QPdfWriter>
#include <QPointer>
#include <QProcess>
#include <QProcessEnvironment>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQmlError>
#include <QQmlIncubationController>
#include <QQmlIncubator>
#include <QQuickItem>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QScopeGuard>
#include <QScreen>
#include <QSet>
#include <QSettings>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTextLayout>
#include <QTextStream>
#include <QUrl>
#include <QVariantMap>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <initializer_list>
#include <memory>
#include <mutex>
#include <sstream>
#include <thread>
#include <utility>
#include <vector>

#include "edi/fit_job.hpp"
#include "engine_setup.hpp"
#include "fit_view_model.hpp"
#include "measured_layer.hpp"
#include "project_view_model.hpp"
#include "scan_session.hpp"
#include "session.hpp"

namespace {
// Only this normal app-test carrier installs this existing process-wide observer.
// A callback owns its state lease; it never reads a GUI QObject on the worker.
struct ScanStopHold {
    std::mutex mutex;
    std::condition_variable changed;
    std::thread::id ownerThread;
    std::thread::id workerThread;
    std::string file;
    std::vector<std::pair<std::string, double>> starts;
    std::vector<std::string> expectedFiles;
    std::string expectedIdentity;
    unsigned long long generation = 0;
    int entered = 0;
    int exited = 0;
    bool blocked = false;
    bool released = false;
    bool expired = false;
};
std::mutex scan_stop_registry_mutex;
std::shared_ptr<ScanStopHold> scan_stop_registered;
unsigned long long scan_stop_generation = 0;

void observe_scan_stop_file(const std::string& file,
                            const std::vector<std::pair<std::string, double>>& starts) {
    std::shared_ptr<ScanStopHold> hold;
    {
        const std::lock_guard lock(scan_stop_registry_mutex);
        hold = scan_stop_registered;
    }
    if (!hold) return;
    std::unique_lock lock(hold->mutex);
    ++hold->entered;
    if (hold->entered != 1 || hold->released) {
        ++hold->exited;
        return;
    }
    hold->workerThread = std::this_thread::get_id();
    hold->file = file;
    hold->starts = starts;
    if (hold->workerThread == hold->ownerThread) {
        // Never block the GUI even if an incorrectly configured worker reaches us.
        hold->expired = true;
        ++hold->exited;
        return;
    }
    hold->blocked = true;
    // Existing completion bound, solely a fatal deadlock guard, not a success wait.
    const auto safety = std::chrono::steady_clock::now() + std::chrono::milliseconds(12000);
    if (!hold->changed.wait_until(lock, safety, [&] { return hold->released; }))
        hold->expired = true;
    hold->blocked = false;
    ++hold->exited;
}

QString scan_stop_thread_name(std::thread::id id) {
    std::ostringstream text;
    text << id;
    return QString::fromStdString(text.str());
}

QMutex report_console_mutex;
QVariantList report_console_messages;
std::atomic<QtMessageHandler> report_previous_handler{nullptr};
void report_console_handler(QtMsgType type, const QMessageLogContext& context, const QString& message) {
    if ((type == QtWarningMsg || type == QtCriticalMsg) &&
        ((message.contains("Binding loop detected") && message.contains("plotWidth")) ||
         message.contains("window doesn't exist"))) {
        QMutexLocker guard(&report_console_mutex);
        report_console_messages.append(QVariantMap{
            {"severity", type == QtCriticalMsg ? "critical" : "warning"},
            {"category", QString::fromUtf8(context.category ? context.category : "")},
            {"text", message}});
    }
    if (const auto previous = report_previous_handler.load()) previous(type, context, message);
}
}

// Public Qt clock: rendering and machine load cannot skip an observed tween step.
class AcceptanceAnimationDriver : public QAnimationDriver {
public:
    void advance() override {} // Only the gate advances the clock.
    qint64 elapsed() const override { return milliseconds_; }
    void step(int milliseconds) { milliseconds_ += milliseconds; advanceAnimation(); }
protected:
    void start() override { milliseconds_ = 0; QAnimationDriver::start(); }
private:
    qint64 milliseconds_ = 0;
};

class ReportSettingsProof : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool webAvailable READ webAvailable CONSTANT)
    Q_PROPERTY(QString webExportError READ webExportError)
public:
    explicit ReportSettingsProof(QQmlEngine* engine) : engine_(engine) {}
    // Public Qt text layout, using the rendered label's own font and available width.
    // The QML gate checks its line count against the actual label before reading line text.
    Q_INVOKABLE QVariantList tooltipTextLines(QObject* label, bool word, bool anywhere) const {
        QVariantList result;
        if (label == nullptr || !label->property("font").canConvert<QFont>()) {
            return result;
        }
        const QString text = label->property("text").toString();
        QTextLayout layout(text, label->property("font").value<QFont>());
        QTextOption option;
        option.setWrapMode(word && anywhere ? QTextOption::WrapAtWordBoundaryOrAnywhere
                           : word ? QTextOption::WordWrap
                           : anywhere ? QTextOption::WrapAnywhere : QTextOption::NoWrap);
        option.setUseDesignMetrics(true);
        layout.setTextOption(option);
        layout.beginLayout();
        for (;;) {
            QTextLine line = layout.createLine();
            if (!line.isValid()) {
                break;
            }
            line.setLineWidth(label->property("width").toDouble() - label->property("leftPadding").toDouble()
                              - label->property("rightPadding").toDouble());
            result.append(QVariantMap{{QStringLiteral("text"), text.mid(line.textStart(), line.textLength()).trimmed()},
                                      {QStringLiteral("width"), line.naturalTextWidth()}});
        }
        layout.endLayout();
        return result;
    }
    using QObject::QObject;
    ~ReportSettingsProof() override {
        releaseScanStop();
        // If a failed case still owns real work, keep the registry reserved rather
        // than allowing a new generation to borrow an in-flight callback.
        clearScanStop();
    }
    Q_INVOKABLE bool armScanStop(QObject* object) {
#if EDI_WORKER_OWNER_THREAD
        Q_UNUSED(object);
        return false;  // Blocking is unsupported on an owner-thread worker.
#else
        auto* project = qobject_cast<edi_app::ProjectViewModel*>(object);
        auto* session = project ? qobject_cast<edi_app::Session*>(project->parent()) : nullptr;
        if (!project || !session || session->project() != project || !project->scan() ||
            !project->fit() || project->fit()->nativeRunning() || !project->scanSession() ||
            scan_stop_hold_)
            return false;
        const auto* scan = project->scanSession();
        if (scan->datasets().files.empty() || scan->run().invalid ||
            !scan->run().outcome.isEmpty())
            return false;
        auto hold = std::make_shared<ScanStopHold>();
        hold->ownerThread = std::this_thread::get_id();
        hold->expectedFiles = scan->datasets().files;
        const auto* originalTemplate = project->scanTemplate();
        hold->expectedIdentity = edi_app::ScanSession::templateIdentity(
            originalTemplate ? *originalTemplate : project->project());
        if (hold->expectedIdentity.empty()) return false;
        {
            const std::lock_guard lock(scan_stop_registry_mutex);
            if (scan_stop_registered) return false;
            hold->generation = ++scan_stop_generation;
            scan_stop_hold_ = hold;
            scan_stop_project_ = project;
            scan_stop_registered = hold;
            edi::set_scan_file_start_observer(observe_scan_stop_file);
        }
        return true;
#endif
    }
    Q_INVOKABLE QVariantMap scanStopFacts(QObject* object) const {
        const auto hold = scan_stop_hold_;
        QVariantMap facts{{"armed", bool(hold)}, {"ready", false}};
        if (!hold) return facts;
        const auto* project = scan_stop_project_.data();
        const auto* session =
            project ? qobject_cast<edi_app::Session*>(project->parent()) : nullptr;
        const bool current =
            project && object == project && session && session->project() == project;
        const bool nativeRunning = project && project->fit() && project->fit()->nativeRunning();
        const std::lock_guard lock(hold->mutex);
        const bool fileOwned = std::find(hold->expectedFiles.begin(), hold->expectedFiles.end(),
                                         hold->file) != hold->expectedFiles.end();
        const bool distinctThread = hold->workerThread != hold->ownerThread;
        const bool ready = current && nativeRunning && hold->entered == 1 && hold->exited == 0 &&
                           hold->blocked && !hold->released && !hold->expired && distinctThread &&
                           !hold->file.empty() && fileOwned && !hold->starts.empty();
        QVariantList starts;
        for (const auto& [name, value] : hold->starts)
            starts.append(QVariantMap{{"name", QString::fromStdString(name)}, {"value", value}});
        facts.insert("ready", ready);
        facts.insert("generation", QString::number(hold->generation));
        facts.insert("owner_current", current);
        facts.insert("native_running", nativeRunning);
        facts.insert("entered", hold->entered);
        facts.insert("exited", hold->exited);
        facts.insert("blocked", hold->blocked);
        facts.insert("released", hold->released);
        facts.insert("expired", hold->expired);
        facts.insert("distinct_thread", distinctThread);
        facts.insert("owner_thread", scan_stop_thread_name(hold->ownerThread));
        facts.insert("worker_thread", scan_stop_thread_name(hold->workerThread));
        facts.insert("file", QString::fromStdString(hold->file));
        facts.insert("file_owned", fileOwned);
        facts.insert("starts", starts);
        facts.insert("expected_identity", QString::fromStdString(hold->expectedIdentity));
        if (current && project->scanSession()) {
            const auto& run = project->scanSession()->run();
            facts.insert("run_identity", QString::fromStdString(run.identity));
            facts.insert("run_identity_matches",
                         !run.identity.empty() && run.identity == hold->expectedIdentity);
            facts.insert("run_outcome", run.outcome);
            facts.insert("run_invalid", run.invalid);
            facts.insert("run_error", run.error);
        }
        return facts;
    }
    Q_INVOKABLE bool scanStopReady(QObject* object) const {
        return scanStopFacts(object).value("ready").toBool();
    }
    Q_INVOKABLE void releaseScanStop() {
        const auto hold = scan_stop_hold_;
        if (!hold) return;
        {
            const std::lock_guard lock(scan_stop_registry_mutex);
            if (scan_stop_registered == hold) edi::set_scan_file_start_observer(nullptr);
        }
        {
            const std::lock_guard lock(hold->mutex);
            hold->released = true;
        }
        hold->changed.notify_all();
    }
    Q_INVOKABLE bool clearScanStop() {
        const auto hold = scan_stop_hold_;
        if (!hold) return true;
        // This never releases a live hold: the negative must not alter its premise.
        {
            const std::lock_guard lock(hold->mutex);
            if (!hold->released || hold->blocked || hold->entered != hold->exited || hold->expired)
                return false;
        }
        if (scan_stop_project_ && scan_stop_project_->fit()->nativeRunning()) return false;
        {
            const std::lock_guard lock(scan_stop_registry_mutex);
            if (scan_stop_registered != hold) return false;
            edi::set_scan_file_start_observer(nullptr);
            scan_stop_registered.reset();
        }
        scan_stop_hold_.reset();
        scan_stop_project_.clear();
        return true;
    }
    bool webAvailable() const { return true; }
    QString webExportError() const { return web_export_error_; }
    Q_INVOKABLE QObject* creationDialog(QObject* root) const {
        if (!root) return nullptr;
        for (auto* object : root->findChildren<QObject*>())
            if (object->metaObject()->indexOfProperty("projectName") >= 0 &&
                object->metaObject()->indexOfProperty("projectParentDirectory") >= 0)
                return object;
        return nullptr;
    }
    // Capability-only seam: compile the application's actual resource unchanged
    // except for the native/browser availability operand. No path/state output
    // is supplied by this observer, and this is not a browser-download proof.
    Q_INVOKABLE QObject* webExport(QQuickItem* parent, QObject* report, QObject* preview) const {
        auto* engine = parent ? qmlEngine(parent) : nullptr;
        web_export_error_.clear();
        if (!engine) { web_export_error_ = "Actual parent has no QML engine"; return nullptr; }
        const QUrl origin("qrc:/qt/qml/edi/app/qml/Pages/Report/ExportGroup.qml");
        QFile file(":/qt/qml/edi/app/qml/Pages/Report/ExportGroup.qml");
        if (!file.open(QIODevice::ReadOnly)) { web_export_error_ = "Actual resource cannot be read: " + file.fileName(); return nullptr; }
        auto source = file.readAll();
        source.replace("import edi.app", "import edi.app\nimport ReportAcceptance 1.0 as Platform");
        source.replace("WebFiles.available", "Platform.SettingsProof.webAvailable");
        QQmlComponent component(engine);
        component.setData(source, origin);
        auto* object = component.createWithInitialProperties({
            {"report", QVariant::fromValue(report)}, {"preview", QVariant::fromValue(preview)}},
            engine->rootContext());
        if (!object) {
            QStringList errors;
            for (const auto& error : component.errors()) errors.append(error.toString());
            web_export_error_ = "Actual Export resource creation at " + origin.toString() + ": " + errors.join("; ");
            return nullptr;
        }
        object->setParent(parent);
        QQmlEngine::setObjectOwnership(object, QQmlEngine::JavaScriptOwnership);
        if (auto* item = qobject_cast<QQuickItem*>(object)) item->setParentItem(parent);
        return object;
    }
    Q_INVOKABLE QVariantList tooltipObjects(QObject* root) const {
        QVariantList result;
        QSet<QObject*> visited;
        std::vector<QObject*> pending{root};
        while (!pending.empty()) {
            auto* object = pending.back();
            pending.pop_back();
            if (!object || visited.contains(object)) continue;
            visited.insert(object);
            if (object->property("opened").isValid()) result.append(QVariant::fromValue(object));
            for (auto* child : object->children()) pending.push_back(child);
            if (auto* item = qobject_cast<QQuickItem*>(object))
                for (auto* child : item->childItems()) pending.push_back(child);
            if (auto* window = qobject_cast<QQuickWindow*>(object)) pending.push_back(window->contentItem());
        }
        return result;
    }
    Q_INVOKABLE bool tooltipOwnedBy(QObject* tooltip, QObject* source) const {
        if (!tooltip || !source) return false;
        for (auto* owner = tooltip->parent(); owner; owner = owner->parent())
            if (owner == source) return true;
        return false;
    }
    Q_INVOKABLE QObject* tooltipPlatformMain(QQuickItem* context, bool web, bool disk) const {
        auto* engine = context ? qmlEngine(context) : nullptr;
        if (!engine) return nullptr;
        const QUrl origin("qrc:/qt/qml/edi/app/qml/Main.qml");
        QFile file(":/qt/qml/edi/app/qml/Main.qml");
        if (!file.open(QIODevice::ReadOnly)) return nullptr;
        auto source = file.readAll();
        // Availability operands alone select the real dialog's platform branches.
        source.replace("WebFiles.available", web ? "true" : "false");
        source.replace("WebStorage.diskAccess", disk ? "true" : "false");
        QQmlComponent component(engine);
        component.setData(source, origin);
        auto* object = component.createWithInitialProperties({{"visible", true}, {"width", 1280}, {"height", 720}}, engine->rootContext());
        if (!object) {
            for (const auto& error : component.errors()) qWarning().noquote() << error.toString();
            return nullptr;
        }
        object->setParent(context);
        QQmlEngine::setObjectOwnership(object, QQmlEngine::JavaScriptOwnership);
        return object;
    }
    Q_INVOKABLE QVariantMap htmlFigureFacts(const QString& html) const {
        const QRegularExpression shared("const sharedSites = sites => \\{[\\s\\S]*?\n  \\};");
        const QRegularExpression legend("const legend = document.createElement\\('div'\\);[\\s\\S]*?figure.appendChild\\(legend\\);");
        const auto s = shared.match(html), l = legend.match(html);
        if (!s.hasMatch() || !l.hasMatch()) return {{"error", "Actual HTML must reach its shared-site and legend producers"}};
        auto code = repoText("tests/unit/app/ReportHtmlProof.js");
        code.replace("/* ACTUAL_SHARED_SITE_FUNCTION */", s.captured());
        code.replace("/* ACTUAL_LEGEND */", l.captured());
        QJSEngine engine;
        const auto result = engine.evaluate(code);
        if (result.isError()) return {{"error", result.toString()}};
        return QJsonDocument::fromJson(result.toString().toUtf8()).toVariant().toMap();
    }
    Q_INVOKABLE QString repoText(const QString& relative) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()); root.cd("../../..");
        QFile file(root.filePath(relative));
        return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()) : QString{};
    }
    Q_INVOKABLE QVariantMap fileFacts(const QUrl& location, const QString& relative) const {
        if (!localDirectory(location))
            return {{"error", "An absolute local directory URL is required"}};
        QFile file(QDir(location.toLocalFile()).filePath(relative));
        const QFileInfo info(file);
        const bool regular = info.isFile() && !info.isSymLink();
        const bool readable = regular && file.open(QIODevice::ReadOnly);
        QVariantMap facts{{"exists", info.exists() || info.isSymLink()},
                          {"regular", regular},
                          {"readable", readable}};
        if (!readable) {
            facts.insert("error", "The project file cannot be opened as a regular file");
            return facts;
        }
        const auto bytes = file.readAll();
        if (file.error() != QFileDevice::NoError) {
            facts.insert("error", "The project file cannot be read");
            return facts;
        }
        facts.insert("sha256",
                     QString::fromLatin1(
                         QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex()));
        facts.insert("bytes", bytes.size());
        facts.insert("modified", info.lastModified().toMSecsSinceEpoch());
        return facts;
    }
    Q_INVOKABLE QUrl childUrl(const QUrl& location, const QString& relative) const {
        if (!absoluteLocalFileUrl(location)) return {};
        return QUrl::fromLocalFile(QDir(location.toLocalFile()).filePath(relative));
    }
    Q_INVOKABLE QVariantMap htmlModel(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {{"error", "Expected an absolute local-file URL"}};
        QFile file(location.toLocalFile());
        if (!file.open(QIODevice::ReadOnly)) return {{"error", "Actual HTML report cannot be opened"}};
        const auto html = QString::fromUtf8(file.readAll());
        const QRegularExpression script("<script[^>]*id=[\"']edi-report-model[\"'][^>]*>([\\s\\S]*?)</script>");
        const auto match = script.match(html);
        if (!match.hasMatch()) return {{"error", "Actual saved HTML has no report-model JSON script"}};
        QJsonParseError error;
        const auto document = QJsonDocument::fromJson(match.captured(1).toUtf8(), &error);
        if (error.error != QJsonParseError::NoError) return {{"error", error.errorString()}};
        return document.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap pdfImageColours(const QUrl& location, const QStringList& colours) const {
        if (!absoluteLocalFileUrl(location)) return {{"error", "Expected an absolute local-file URL"}};
        QFile file(location.toLocalFile());
        if (!file.open(QIODevice::ReadOnly)) return {{"error", "Actual saved PDF cannot be opened"}};
        const auto pdf = QString::fromLatin1(file.readAll());
        const QRegularExpression objects("(\\d+)\\s+0\\s+obj\\b([\\s\\S]*?)endobj");
        auto iterator = objects.globalMatch(pdf);
        std::vector<QColor> targets;
        QVariantMap counts, verticalRuns;
        for (const auto& text : colours) {
            targets.emplace_back(text);
            counts.insert(text, 0);
            verticalRuns.insert(text, 0);
        }
        int images = 0;
        while (iterator.hasNext()) {
            const auto object = iterator.next().captured(2);
            if (!object.contains(QRegularExpression("/Subtype\\s*/Image\\b"))) continue;
            if (object.contains("/DeviceGray")) continue; // alpha masks are not colour figures
            const int start = object.indexOf("stream"), end = object.lastIndexOf("endstream");
            if (start < 0 || end <= start) return {{"error", "Actual PDF image lacks its stream"}};
            auto bytes = object.mid(start + 6, end - start - 6).toLatin1();
            if (bytes.startsWith("\r\n")) bytes.remove(0, 2);
            else if (bytes.startsWith('\n')) bytes.remove(0, 1);
            if (bytes.endsWith("\r\n")) bytes.chop(2);
            else if (bytes.endsWith('\n')) bytes.chop(1);
            QImage image;
            if (object.left(start).contains("/DCTDecode")) image = QImage::fromData(bytes, "JPEG");
            else if (object.left(start).contains("/FlateDecode")) {
                const auto width = QRegularExpression("/Width\\s+(\\d+)").match(object).captured(1).toInt();
                const auto height = QRegularExpression("/Height\\s+(\\d+)").match(object).captured(1).toInt();
                if (width <= 0 || height <= 0 || !object.contains("/DeviceRGB") ||
                    !object.contains(QRegularExpression("/BitsPerComponent\\s+8\\b")))
                    return {{"error", "PDF colour observer requires an eight-bit RGB image"}};
                const auto size = quint32(width) * quint32(height) * 3;
                QByteArray framed;
                for (int shift : {24, 16, 8, 0}) framed.append(char((size >> shift) & 255));
                framed.append(bytes);
                const auto raw = qUncompress(framed);
                if (raw.size() != size) return {{"error", "PDF colour image has unexpected decoded bytes"}};
                image = QImage(reinterpret_cast<const uchar*>(raw.constData()), width, height, width * 3, QImage::Format_RGB888).copy();
            } else return {{"error", "PDF colour observer refuses an unsupported image codec"}};
            if (image.isNull()) return {{"error", "Actual PDF colour image did not decode"}};
            ++images;
            std::vector<std::vector<int>> runs(targets.size(), std::vector<int>(image.width(), 0));
            for (int y = 0; y < image.height(); ++y) for (int x = 0; x < image.width(); ++x) {
                const auto actual = image.pixelColor(x, y);
                for (std::size_t i = 0; i < targets.size(); ++i) {
                    const auto target = targets[i];
                    // A fixed five encoded-channel bound allows JPEG quantisation;
                    // source-palette correctness is tested separately, exactly.
                    if (std::max({std::abs(actual.red()-target.red()), std::abs(actual.green()-target.green()), std::abs(actual.blue()-target.blue())}) <= 5) {
                        counts[colours[int(i)]] = counts[colours[int(i)]].toInt() + 1;
                        ++runs[i][x];
                        verticalRuns[colours[int(i)]] = std::max(verticalRuns[colours[int(i)]].toInt(), runs[i][x]);
                    } else {
                        runs[i][x] = 0;
                    }
                }
            }
        }
        return {{"images", images}, {"counts", counts}, {"maxVerticalRun", verticalRuns}};
    }
    Q_INVOKABLE QVariantMap pdfFacts(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {{"error", "Expected an absolute local-file URL"}};
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        const auto python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {{"error", "PDF observer requires the runner's Python"}};
        QProcess process;
        process.start(python, {root.filePath("ReportPdf.py"), location.toLocalFile()});
        if (!process.waitForFinished(10000)) { process.kill(); return {{"error", "PDF observer did not finish"}}; }
        const auto json = QJsonDocument::fromJson(process.readAllStandardOutput());
        if (json.isNull()) return {{"error", QString::fromUtf8(process.readAllStandardError())}};
        return json.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap htmlEvolutionFacts(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {{"error", "Expected an absolute local-file URL"}};
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        root.cd("../../..");
        const auto python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {{"error", "Browser observer requires the runner's Python"}};
        QProcess process;
        process.start(python, {root.filePath("tests/fixtures/report_evolution/observe_browser.py"), location.toLocalFile()});
        // The browser observer allows 60 s for startup/frames and up to 6 s for child cleanup.
        if (!process.waitForFinished(70000)) { process.kill(); process.waitForFinished(1000); return {{"error", "Actual HTML browser did not finish"}}; }
        const auto json = QJsonDocument::fromJson(process.readAllStandardOutput());
        if (json.isNull()) return {{"error", QString::fromUtf8(process.readAllStandardError())}};
        return json.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap reportHtmlMatrices(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {{"error", "Expected an absolute local-file URL"}};
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        root.cd("../../..");
        const auto python = QStandardPaths::findExecutable("python");
        if (python.isEmpty()) return {{"error", "Report surface observer needs Python"}};
        QProcess process;
        auto environment = QProcessEnvironment::systemEnvironment();
        // Local app diagnostics use the task engine's consumer artifact when
        // present. A replay can explicitly select its sealed matching artifact.
        QString extension = environment.value("EDI_REPORT_ACCEPTANCE_EXTENSION_DIR");
        if (extension.isEmpty() && QDir(root.filePath("build/ci-consumer/python/edi")).exists())
            extension = root.filePath("build/ci-consumer/python/edi");
        if (!extension.isEmpty()) environment.insert("EDI_EXTENSION_DIR", extension);
        environment.insert("PYTHONPATH", root.filePath("lib") + QDir::listSeparator() +
                           root.path() + QDir::listSeparator() + environment.value("PYTHONPATH"));
        process.setProcessEnvironment(environment);
        process.start(python, {root.filePath("tests/fixtures/report_effective_template/observe_html.py"), location.toLocalFile()});
        if (!process.waitForFinished(25000)) { process.kill(); return {{"error", "Python and CLI HTML observers did not finish"}}; }
        const auto json = QJsonDocument::fromJson(process.readAllStandardOutput());
        if (json.isNull()) return {{"error", QString::fromUtf8(process.readAllStandardError())}};
        return json.toVariant().toMap();
    }
    Q_INVOKABLE QVariantMap pdfWitness() {
        auto directory = std::make_unique<QTemporaryDir>(QDir::tempPath() + "/edi-pdf-proof-XXXXXX");
        if (!directory->isValid()) return {{"error", "PDF witness has no temporary directory"}};
        const auto file = QDir(directory->path()).filePath("independent.pdf");
        {
            QPdfWriter writer(file);
            writer.setResolution(72);
            writer.setPageSize(QPageSize(QPageSize::A4));
            writer.setPageMargins(QMarginsF(25, 25, 25, 25), QPageLayout::Millimeter);
            QPainter painter(&writer);
            QFont font("PT Sans"); font.setPointSizeF(10.04); painter.setFont(font);
            painter.drawText(QPointF(0, 20), "Short name lbco_hrpt_s2");
            QImage image(8, 8, QImage::Format_RGB32); image.fill(Qt::blue);
            painter.drawImage(QRectF(0, 40, 40, 40), image);
            painter.fillRect(QRectF(0, 100, 20, 20), QColor("#4575b4"));
            painter.fillRect(QRectF(20, 100, 20, 20), QColor("#d73027"));
            painter.fillRect(QRectF(40, 100, 20, 20), QColor("#ffffff"));
            painter.drawText(QPointF(220, 690), "1");
            writer.newPage();
            painter.drawText(QPointF(0, 20), "Second page");
            painter.drawText(QPointF(220, 690), "2");
        }
        auto result = pdfFacts(QUrl::fromLocalFile(file));
        result.insert("url", QUrl::fromLocalFile(file));
        directories_.push_back(std::move(directory));
        return result;
    }
    Q_INVOKABLE bool beginAnimationClock() {
        if (animation_driver_) return false;
        animation_driver_ = std::make_unique<AcceptanceAnimationDriver>();
        animation_driver_->install();
        return true;
    }
    Q_INVOKABLE bool stepAnimationClock(int milliseconds) {
        if (!animation_driver_ || milliseconds <= 0) return false;
        animation_driver_->step(milliseconds);
        return true;
    }
    Q_INVOKABLE void endAnimationClock() {
        if (!animation_driver_) return;
        animation_driver_->uninstall();
        animation_driver_.reset();
    }
    Q_INVOKABLE bool beginConsoleCapture() const {
        const auto previous = qInstallMessageHandler(report_console_handler);
        if (previous != report_console_handler) report_previous_handler.store(previous);
        QMutexLocker guard(&report_console_mutex);
        report_console_messages.clear();
        return report_previous_handler.load() != nullptr;
    }
    Q_INVOKABLE QVariantList consoleMessages() const {
        QMutexLocker guard(&report_console_mutex);
        return report_console_messages;
    }
    Q_INVOKABLE void qualifyConsoleCapture() const {
        QTest::ignoreMessage(QtWarningMsg, "Binding loop detected for property \"plotWidth\"");
        qWarning("Binding loop detected for property \"plotWidth\"");
        QTest::ignoreMessage(QtCriticalMsg, "window doesn't exist.");
        const QLoggingCategory graphs("qt.graphs2d");
        qCCritical(graphs, "window doesn't exist.");
    }
    Q_INVOKABLE bool type(QObject* object, const QString& text) const {
        auto* field = qobject_cast<QQuickItem*>(object);
        if (!field || !field->window() || field->window()->activeFocusItem() != field) return false;
        if (!QMetaObject::invokeMethod(field, "selectAll")) return false;
        QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, text);
        QKeyEvent release(QEvent::KeyRelease, 0, Qt::NoModifier, text);
        QCoreApplication::sendEvent(field->window(), &press);
        QCoreApplication::sendEvent(field->window(), &release);
        return field->property("text").toString() == text;
    }
    Q_INVOKABLE bool key(QObject* object, int key) const {
        auto* field = qobject_cast<QQuickItem*>(object);
        if (!field || !field->window()) return false;
        QTest::keyClick(field->window(), static_cast<Qt::Key>(key), Qt::NoModifier, 0);
        return true;
    }
    Q_INVOKABLE QVariantList points(QObject* object) const {
        const auto* layer = qobject_cast<edi_app::MeasuredLayer*>(object);
        if (!layer) return {};
        QVariantList result;
        for (const auto& point : layer->points()) result.append(QVariantMap{{"x", point.x()}, {"y", point.y()}});
        return result;
    }
    Q_INVOKABLE bool publishScanSummary(QObject* object, double seconds = 9.0) const {
        auto* project = qobject_cast<edi_app::ProjectViewModel*>(object);
        if (!project) return false;
        edi_app::ScanSummary summary;
        summary.files = 162;
        summary.fitted = 162;
        summary.ok = 160;
        summary.failed = 2;
        summary.chi_min = 12.34;
        summary.chi_max = 23.45;
        summary.seconds = seconds;
        summary.outcome = "success";
        project->fit()->showScan(summary, true);
        return true;
    }
    Q_INVOKABLE QVariantMap screen() const {
        const auto screen = QGuiApplication::primaryScreen();
        if (!screen) return {};
        const auto bounds = screen->availableGeometry();
        return {{"x", bounds.x()}, {"y", bounds.y()}, {"width", bounds.width()}, {"height", bounds.height()}};
    }
    Q_INVOKABLE QUrl emptyDirectory() {
        auto directory = std::make_unique<QTemporaryDir>(QDir::tempPath() + "/edi-empty-XXXXXX");
        if (!directory->isValid()) return {};
        const auto result = QUrl::fromLocalFile(directory->path());
        directories_.push_back(std::move(directory));
        return result;
    }
    Q_INVOKABLE QUrl copyProject(const QUrl& input) {
        if (!absoluteLocalFileUrl(input)) return {};
        auto directory = std::make_unique<QTemporaryDir>(QDir::tempPath() + "/edi-settings-XXXXXX");
        if (!directory->isValid()) return {};
        QDir source(input.toLocalFile());
        if (!source.exists()) return {};
        QDirIterator files(source.absolutePath(), QDir::AllEntries | QDir::NoDotAndDotDot, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const auto from = files.next();
            const auto to = QDir(directory->path()).filePath(source.relativeFilePath(from));
            if (QFileInfo(from).isDir()) { if (!QDir().mkpath(to)) return {}; }
            else if (!QFile::copy(from, to)) return {};
        }
        const auto result = QUrl::fromLocalFile(directory->path());
        directories_.push_back(std::move(directory));
        return result;
    }
    static bool localDirectory(const QUrl& project) {
        return absoluteLocalFileUrl(project) && QFileInfo(project.toLocalFile()).isDir();
    }
    Q_INVOKABLE QVariantMap fileObservation(const QUrl& project, const QString& relative) const {
        if (!localDirectory(project)) return {{"error", "An absolute local directory URL is required"}};
        const auto path = QDir(project.toLocalFile()).absoluteFilePath(relative);
        if (!QFileInfo::exists(path)) return {{"exists", false}, {"path", path}};
        QFile file(path);
        if (!QFileInfo(path).isFile() || !file.open(QIODevice::ReadOnly))
            return {{"error", "The project file cannot be opened"}, {"path", path}};
        const auto bytes = file.readAll();
        if (file.error() != QFileDevice::NoError)
            return {{"error", "The project file cannot be read"}, {"path", path}};
        return {{"exists", true}, {"path", path}, {"text", QString::fromUtf8(bytes)},
                {"base64", QString::fromLatin1(bytes.toBase64())}};
    }
    Q_INVOKABLE QString text(const QUrl& project, const QString& relative) const {
        const auto observed = fileObservation(project, relative);
        if (observed.contains("error") || !observed.value("exists").toBool()) {
            if (auto* engine = qjsEngine(this))
                engine->throwError(QStringLiteral("SettingsProof.text: %1 (%2)")
                    .arg(observed.value("error", "The project file is missing").toString(), relative));
            return {};
        }
        return observed.value("text").toString();
    }
    Q_INVOKABLE QVariantMap projectBytes(const QUrl& project) const {
        if (!localDirectory(project)) return {{"error", "An absolute local directory URL is required"}};
        const QDir root(project.toLocalFile());
        if (!root.exists()) return {{"error", "The saved project directory is missing"}};
        QVariantMap result;
        QDirIterator files(root.absolutePath(), QDir::Files | QDir::Hidden, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            QFile file(files.next());
            if (!file.open(QIODevice::ReadOnly)) return {{"error", "A saved project file cannot be read"}};
            auto bytes = file.readAll();
            if (file.error() != QFileDevice::NoError) return {{"error", "A saved project file cannot be read"}};
            const auto relative = root.relativeFilePath(file.fileName());
            if (relative == QStringLiteral("project.edi")) {
                QString record = QString::fromUtf8(bytes);
                record.replace(QRegularExpression(QStringLiteral("(?m)^(_metadata\\.(?:created|last_modified)[ \\t]+)[^\\r\\n]+")),
                               QStringLiteral("\\1<CLOCK>"));
                bytes = record.toUtf8();
            }
            result.insert(relative, QString::fromLatin1(bytes.toBase64()));
        }
        return result;
    }
    Q_INVOKABLE bool write(const QUrl& project, const QString& relative, const QString& text) const {
        if (!localDirectory(project)) return false;
        QFile file(QDir(project.toLocalFile()).filePath(relative));
        if (!QDir().mkpath(QFileInfo(file).absolutePath())) return false;
        return file.open(QIODevice::WriteOnly | QIODevice::Truncate) && file.write(text.toUtf8()) == text.toUtf8().size() && file.flush();
    }
    Q_INVOKABLE bool remove(const QUrl& project, const QString& relative) const {
        if (!localDirectory(project)) return false;
        return QFile::remove(QDir(project.toLocalFile()).filePath(relative));
    }
    Q_INVOKABLE QUrl copyProjectArchive(const QUrl& source, bool readOnly = false) {
        if (!absoluteLocalFileUrl(source)) return {};
        const QUrl root = emptyDirectory();
        if (!absoluteLocalFileUrl(root) || !QFileInfo(root.toLocalFile()).isDir()) return {};
        const QString path = QDir(root.toLocalFile()).filePath("opened.zip");
        if (!QFile::copy(source.toLocalFile(), path)) return {};
        if (readOnly) {
            const auto read = QFile::ReadOwner | QFile::ReadGroup | QFile::ReadOther;
            if (!QFile::setPermissions(path, read) ||
                !QFile::setPermissions(root.toLocalFile(),
                                       read | QFile::ExeOwner | QFile::ExeGroup | QFile::ExeOther))
                return {};
        }
        return QUrl::fromLocalFile(path);
    }
    Q_INVOKABLE bool archiveLocationWritable(const QUrl& archive) const {
        if (!absoluteLocalFileUrl(archive)) return false;
        return QFileInfo(archive.toLocalFile()).isWritable() ||
               QFileInfo(QFileInfo(archive.toLocalFile()).absolutePath()).isWritable();
    }
    Q_INVOKABLE QVariantList projectFileDialogs(QObject* root, bool folder) const {
        QVariantList result;
        if (!root) return result;
        const char* selected = folder ? "selectedFolder" : "selectedFile";
        for (auto* object : root->findChildren<QObject*>())
            if (object->inherits(folder ? "QQuickFolderDialog" : "QQuickFileDialog") &&
                object->metaObject()->indexOfProperty(selected) >= 0 &&
                object->property("visible").toBool())
                result.append(QVariant::fromValue(object));
        return result;
    }
    Q_INVOKABLE QVariantMap projectDialogFacts(QObject* dialog) const {
        if (!dialog) return {};
        return {{"type", QString::fromLatin1(dialog->metaObject()->className())},
                {"systemFolder", dialog->inherits("QQuickFolderDialog")},
                {"systemFile", dialog->inherits("QQuickFileDialog")},
                {"acceptLabel", dialog->property("acceptLabel")},
                {"options", dialog->property("options")},
                {"fileMode", dialog->property("fileMode")}};
    }
    Q_INVOKABLE bool chooseProjectLocation(QObject* dialog, const QUrl& location,
                                           bool folder) const {
        if (!dialog || !dialog->property("visible").toBool()) return false;
        const char* selected = folder ? "selectedFolder" : "selectedFile";
        if (!dialog->setProperty(selected, location) ||
            dialog->property(selected).toUrl() != location)
            return false;
        const bool accepted = QMetaObject::invokeMethod(dialog, "accepted", Qt::DirectConnection);
        QMetaObject::invokeMethod(dialog, "close", Qt::DirectConnection);
        return accepted;
    }
    Q_INVOKABLE bool dropProject(QObject* object, const QUrl& location) const {
        auto* window = qobject_cast<QQuickWindow*>(object);
        if (!window) return false;
        QMimeData mime;
        mime.setUrls({location});
        const QPoint point(window->width() / 2, window->height() / 2);
        QDragEnterEvent enter(point, Qt::CopyAction, &mime, Qt::LeftButton, Qt::NoModifier);
        QCoreApplication::sendEvent(window, &enter);
        if (!enter.isAccepted()) return false;
        QDropEvent drop(QPointF(point), Qt::CopyAction, &mime, Qt::LeftButton, Qt::NoModifier);
        QCoreApplication::sendEvent(window, &drop);
        return drop.isAccepted();
    }
    Q_INVOKABLE QString projectArchiveBytes(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {};
        QFile file(location.toLocalFile());
        return file.open(QIODevice::ReadOnly) ? QString::fromLatin1(file.readAll().toBase64())
                                              : QString();
    }
    Q_INVOKABLE QVariantMap projectFolderBytes(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {};
        QVariantMap result;
        QDir root(location.toLocalFile());
        QDirIterator files(root.absolutePath(), QDir::Files | QDir::Hidden,
                           QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const QString name = files.next();
            QFile file(name);
            if (!file.open(QIODevice::ReadOnly)) return {};
            result.insert(root.relativeFilePath(name),
                          QString::fromLatin1(file.readAll().toBase64()));
        }
        return result;
    }
    Q_INVOKABLE QString localPath(const QUrl& location) const {
        return absoluteLocalFileUrl(location) ? location.toLocalFile() : QString();
    }
    Q_INVOKABLE QVariantMap palette(bool safe) const { return paletteForScheme(safe ? "colourBlindSafe" : "default"); }
    Q_INVOKABLE QVariantMap paletteForScheme(const QString& scheme) const {
        QDir root(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath());
        root.cd("../../..");
        QDir directory(root.filePath("data/palettes"));
        QVariantMap output;
        for (const auto& name : directory.entryList({"*.tsv"}, QDir::Files, QDir::Name)) {
            QString stem = QFileInfo(name).completeBaseName().toLower(), wanted = scheme.toLower();
            stem.remove(QRegularExpression("[^a-z]")); wanted.remove(QRegularExpression("[^a-z]"));
            if (stem != wanted) continue;
            QFile file(directory.filePath(name));
            if (!file.open(QIODevice::ReadOnly)) continue;
            QTextStream stream(&file);
            const auto header = stream.readLine().split('\t');
            QVariantList pattern, structure, gradient;
            while (!stream.atEnd()) {
                const auto cells = stream.readLine().split('\t');
                if (cells.size() != header.size()) continue;
                QVariantMap row;
                for (qsizetype index = 0; index < cells.size(); ++index) row.insert(header[index], cells[index]);
                if (row.value("role") == "pattern") pattern.append(row);
                if (row.value("role") == "structure") structure.append(row);
                if (row.value("role") == "gradient") gradient.append(row);
            }
            output.insert("pattern", pattern);
            output.insert("structure", structure);
            if (!gradient.isEmpty()) output.insert("gradient", gradient);
            return output;
        }
        return output;
    }
    Q_INVOKABLE QString fileName(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {};
        return QFileInfo(location.toLocalFile()).fileName();
    }
    Q_INVOKABLE QString parentName(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {};
        return QFileInfo(QFileInfo(location.toLocalFile()).absolutePath()).fileName();
    }
    Q_INVOKABLE bool temporary(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return false;
        return QFileInfo(location.toLocalFile()).absoluteFilePath().startsWith(QDir::tempPath() + '/');
    }
    Q_INVOKABLE QUrl legacy(const QUrl& location) const {
        if (!absoluteLocalFileUrl(location)) return {};
        QDir root = QFileInfo(location.toLocalFile()).absoluteDir();
        if (root.dirName() == "EasyScience") root.cdUp();
        return QUrl::fromLocalFile(root.filePath("settings.ini"));
    }
    Q_INVOKABLE void erase(const QUrl& location, const QString& group, const QString& key) const {
        if (!absoluteLocalFileUrl(location)) return;
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        settings.remove(key);
        settings.sync();
    }
    Q_INVOKABLE QVariantMap settingFacts(const QUrl& location, const QString& group, const QString& key) const {
        if (!absoluteLocalFileUrl(location)) return {{"error", "Expected an absolute local-file URL"}};
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        const auto value = settings.value(key);
        return {{"file", location.toLocalFile()}, {"group", group}, {"key", key},
                {"type", QString::fromUtf8(value.typeName() ? value.typeName() : "invalid")},
                {"value", value}, {"list", value.toStringList()}};
    }
    Q_INVOKABLE QVariant value(const QUrl& location, const QString& group, const QString& key) const {
        if (!absoluteLocalFileUrl(location)) return {};
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        return settings.value(key);
    }
    Q_INVOKABLE void seed(const QUrl& location, const QString& group, const QString& key, const QVariant& value) const {
        if (!absoluteLocalFileUrl(location)) return;
        QSettings settings(location.toLocalFile(), QSettings::IniFormat);
        settings.beginGroup(group);
        settings.setValue(key, value);
        settings.sync();
    }
    Q_INVOKABLE QVariantMap archiveCreationFailureProof(const QUrl& source, const QUrl& owned) {
        if (!absoluteLocalFileUrl(source) || !QFileInfo(source.toLocalFile()).isFile() ||
            !absoluteLocalFileUrl(owned) || !QFileInfo(owned.toLocalFile()).isDir())
            return {{"error", "Actual owned source and directory are required"}};
        const QString blocked = QDir(owned.toLocalFile()).filePath("blocked-temp-parent");
        const QString output = QDir(owned.toLocalFile()).filePath("opened.zip");
        if (QFileInfo::exists(blocked) || QFileInfo::exists(output))
            return {{"error", "The owned failure witness must start with absent destinations"}};
        QFile blocker(blocked);
        const QByteArray blockerBytes("owned-blocker");
        if (!blocker.open(QIODevice::WriteOnly) ||
            blocker.write(blockerBytes) != blockerBytes.size())
            return {{"error", "The owned non-directory temporary parent could not be armed"}};
        blocker.close();
        struct EnvironmentEntry {
            const char* name;
            bool set;
            QByteArray value;
        };
        std::vector<EnvironmentEntry> saved;
        for (const char* name : {"TMPDIR", "TMP", "TEMP"})
            saved.push_back({name, qEnvironmentVariableIsSet(name), qgetenv(name)});
        const QString previous = QDir::currentPath();
        bool environmentRestored = true, cwdRestored = false;
        QVariantMap facts;
        {
            const auto restore = qScopeGuard([&] {
                for (const auto& entry : saved) {
                    const bool ok =
                        entry.set ? qputenv(entry.name, entry.value) : qunsetenv(entry.name);
                    environmentRestored = ok && environmentRestored;
                }
                cwdRestored = QDir::setCurrent(previous);
            });
            if (!QDir::setCurrent(owned.toLocalFile()))
                return {
                    {"error", "The owned archive ambient-directory witness could not be armed"}};
            for (const auto& entry : saved)
                if (!qputenv(entry.name, blocked.toUtf8()))
                    return {{"error", "The owned temporary-parent failure could not be armed"}};
            facts.insert("temporaryParentArmed",
                         QDir::cleanPath(QDir::tempPath()) == QDir::cleanPath(blocked));
            if (!facts["temporaryParentArmed"].toBool())
                return {{"error",
                         "This actual Qt platform did not select the owned temporary parent"}};
            facts.insert("creatorActuallyFailed", emptyDirectory().isEmpty());
            if (!facts["creatorActuallyFailed"].toBool())
                return {{"error", "The actual temporary-directory creator did not refuse"}};
            facts.insert("archiveCopyRefused", copyProjectArchive(source).isEmpty());
            facts.insert("noAmbientArchive", !QFileInfo::exists(output));
        }
        facts.insert("environmentRestored", environmentRestored);
        facts.insert("cwdRestored", cwdRestored && QDir::currentPath() == previous);
        return facts;
    }
    Q_INVOKABLE QVariantMap localRootBoundaryProof(const QUrl& owned) {
        if (!absoluteLocalFileUrl(owned) || !QDir(owned.toLocalFile()).exists())
            return {{"error", "The boundary proof requires its actual owned directory"}};
        const QString previous = QDir::currentPath();
        bool restored = false;
        QVariantList rows;
        {
            if (!QDir::setCurrent(owned.toLocalFile()))
                return {{"error", "The owned ambient-directory control could not be armed"}};
            const auto restore = qScopeGuard([&] { restored = QDir::setCurrent(previous); });
            const std::vector<std::pair<QString, QUrl>> roots{
                {"empty", QUrl()},
                {"plain-absolute", QUrl(owned.toLocalFile())},
                {"relative", QUrl("relative-root")},
                {"relative-file", QUrl("file:.")},
                {"https", QUrl("https://invalid.invalid/root")},
                {"qrc", QUrl("qrc:/not-a-local-file")},
                {"query", QUrl(owned.toString() + "?not-a-path")},
                {"fragment", QUrl(owned.toString() + "#not-a-path")}};
            for (const auto& [name, root] : roots) {
                const QString marker = QStringLiteral("e11-root-sentinel.txt");
                const QByteArray expected("independent-owned-sentinel");
                QFile actual(QDir(owned.toLocalFile()).filePath(marker));
                if (!actual.open(QIODevice::WriteOnly | QIODevice::Truncate) ||
                    actual.write(expected) != expected.size())
                    return {{"error", "The independent ambient sentinel could not be written"}};
                actual.close();
                QVariantMap row{{"name", name},
                                {"emptyText", fileObservation(root, marker).contains("error")},
                                {"emptyFacts", fileFacts(root, marker).contains("error")},
                                {"noChild", childUrl(root, marker).isEmpty()},
                                {"projectRefusal", projectBytes(root).contains("error")},
                                {"emptyFolder", projectFolderBytes(root).isEmpty()},
                                {"noCopy", copyProject(root).isEmpty()},
                                {"writeRefused", !write(root, marker, "CORRUPTION")},
                                {"removeRefused", !remove(root, marker)}};
                row.insert("sameBytes",
                           actual.open(QIODevice::ReadOnly) && actual.readAll() == expected);
                rows.append(row);
            }
            const QUrl remote("file://nonlocal.invalid/owned-root");
            rows.append(QVariantMap{{"name", "nonlocal-file-authority"},
                                    {"emptyText", fileObservation(remote, "sentinel").contains("error")},
                                    {"emptyFacts", fileFacts(remote, "sentinel").contains("error")},
                                    {"noChild", childUrl(remote, "sentinel").isEmpty()},
                                    {"projectRefusal", projectBytes(remote).contains("error")},
                                    {"emptyFolder", projectFolderBytes(remote).isEmpty()}});
            QFile ini("owned.ini");
            const QByteArray expectedIni("[owned]\nkey=original\n");
            if (!ini.open(QIODevice::WriteOnly | QIODevice::Truncate) ||
                ini.write(expectedIni) != expectedIni.size())
                return {{"error", "The independent settings sentinel could not be armed"}};
            ini.close();
            const QUrl relativeIni("file:owned.ini");
            QVariantMap settings{
                {"name", "relative-settings"},
                {"noValue", !value(relativeIni, "owned", "key").isValid()},
                {"settingsRefusal", settingFacts(relativeIni, "owned", "key").contains("error")},
                {"noLegacy", legacy(relativeIni).isEmpty()},
                {"noParent", parentName(relativeIni).isEmpty()},
                {"noName", fileName(relativeIni).isEmpty()},
                {"notTemporary", !temporary(relativeIni)},
                {"noLocalPath", localPath(relativeIni).isEmpty()}};
            seed(relativeIni, "owned", "key", "CORRUPTION");
            erase(relativeIni, "owned", "key");
            settings.insert("sameBytes",
                            ini.open(QIODevice::ReadOnly) && ini.readAll() == expectedIni);
            rows.append(settings);
        }
        return {{"rows", rows}, {"cwdRestored", restored && QDir::currentPath() == previous}};
    }
    Q_INVOKABLE QVariantMap incubationOwnership(QObject* context, bool destroyFirst) const {
        auto* caller = qmlEngine(context);
        auto* original = caller ? caller->incubationController() : nullptr;
        auto* originalObject = dynamic_cast<QObject*>(original);
        if (!caller || !original || !originalObject)
            return {{"error", "The existing configured caller/controller is unavailable"}};
        QPointer<QQmlEngine> callerGuard(caller);
        QPointer<QObject> originalGuard(originalObject);
        bool restored = false;
        const auto restoreCaller = [&] {
            if (restored) return;
            if (callerGuard && originalGuard) {
                // Test cleanup only, AFTER all measured engines/jobs are gone.
                // Force a real setter transition even if the old forward field
                // still aliases the shared controller whose private link moved.
                callerGuard->setIncubationController(nullptr);
                callerGuard->setIncubationController(original);
            }
            restored = true;
        };
        const auto callerCleanup = qScopeGuard(restoreCaller);
        QVariantMap facts;
        try {
            struct Job {
                QQmlComponent component;
                QQmlIncubator incubation{QQmlIncubator::Asynchronous};
                bool started = false;
                int queued = 0;
                explicit Job(QQmlEngine& engine) : component(&engine) {
                    component.setData("import QtQml; QtObject { property int answer: 6 * 7 }",
                                      QUrl("file:///actual-configured-incubation.qml"));
                    if (component.isReady()) component.create(incubation, engine.rootContext());
                    started = incubation.isLoading();
                    if (auto* controller = engine.incubationController())
                        queued = controller->incubatingObjectCount();
                }
                ~Job() {
                    QObject* ready = incubation.object();
                    incubation.clear();  // Aborts pending work; does not delete Ready objects.
                    delete ready;
                }
                QVariantMap snapshot() const {
                    QStringList errors;
                    for (const auto& error : component.errors()) errors.append(error.toString());
                    for (const auto& error : incubation.errors()) errors.append(error.toString());
                    auto* object = incubation.object();
                    return {{"started_loading", started},
                            {"queued_at_start", queued},
                            {"status", int(incubation.status())},
                            {"ready", incubation.isReady()},
                            {"answer", object ? object->property("answer") : QVariant{}},
                            {"errors", errors}};
                }
            };
            const auto waitJobs = [](std::initializer_list<Job*> jobs) {
                QElapsedTimer deadline;
                deadline.start();
                for (;;) {
                    bool pending = false;
                    for (const auto* job : jobs) pending = pending || job->incubation.isLoading();
                    if (!pending || deadline.elapsed() >= 5000) return;
                    QTest::qWait(10);  // Existing restart carrier's bound/event-loop primitive.
                }
            };
            const auto belongsTo = [](const QObject* object, const QObject* engine) {
                for (auto* current = object; current; current = current->parent())
                    if (current == engine) return true;
                return false;
            };
            auto first = std::make_unique<QQmlEngine>();
            edi_app::configure_engine(*first);
            auto* a = first->incubationController();
            QPointer<QObject> aObject(dynamic_cast<QObject*>(a));
            facts["a_present"] = a != nullptr;
            facts["a_engine_owned"] = aObject && belongsTo(aObject, first.get());
            auto beforeB = std::make_unique<Job>(*first);
            auto second = std::make_unique<QQmlEngine>();
            edi_app::configure_engine(*second);
            auto* b = second->incubationController();
            QPointer<QObject> bObject(dynamic_cast<QObject*>(b));
            facts["b_present"] = b != nullptr;
            const bool distinct = a && b && a != b;
            facts["distinct_controllers"] = distinct;
            facts["a_forward_after_b"] = first->incubationController() == a;
            facts["b_engine_owned"] = bObject && belongsTo(bObject, second.get());
            const bool independent =
                distinct && aObject && bObject && belongsTo(aObject, first.get()) &&
                belongsTo(bObject, second.get()) && first->incubationController() == a &&
                second->incubationController() == b;
            facts["independent_live_ownership"] = independent;
            auto duringB = std::make_unique<Job>(*first);
            auto bWork = std::make_unique<Job>(*second);
            waitJobs({beforeB.get(), duringB.get(), bWork.get()});
            facts["a_queued_before_b"] = beforeB->snapshot();
            facts["a_work_with_b"] = duringB->snapshot();
            facts["b_work"] = bWork->snapshot();
            beforeB.reset();
            duringB.reset();
            bWork.reset();
            auto& survivor = destroyFirst ? second : first;
            auto& victim = destroyFirst ? first : second;
            auto* survivingController = destroyFirst ? b : a;
            QPointer<QObject> survivingObject = destroyFirst ? bObject : aObject;
            QPointer<QObject> victimObject = destroyFirst ? aObject : bObject;
            victim.reset();
            facts["destroyed_engine_controller_deleted"] = victimObject.isNull();
            facts["survivor_controller_alive"] = !survivingObject.isNull();
            facts["survivor_forward_after_destroy"] =
                survivor->incubationController() == survivingController;
            facts["survivor_owner_after_destroy"] =
                survivingObject && belongsTo(survivingObject, survivor.get());
            if (survivingController && survivingObject &&
                survivor->incubationController() == survivingController) {
                auto afterDestroy = std::make_unique<Job>(*survivor);
                waitJobs({afterDestroy.get()});
                facts["survivor_work_after_destroy"] = afterDestroy->snapshot();
                afterDestroy.reset();
                survivor->setIncubationController(nullptr);
                facts["explicit_detach_forward_null"] =
                    survivor->incubationController() == nullptr;
                facts["detached_owner_still_alive"] = !survivingObject.isNull();
                // No controller.engine() getter is queried, here or anywhere else.
                facts["detached_count"] = survivingController->incubatingObjectCount();
                survivor->setIncubationController(survivingController);
                facts["explicit_reattach_forward"] =
                    survivor->incubationController() == survivingController;
                auto reattached = std::make_unique<Job>(*survivor);
                waitJobs({reattached.get()});
                facts["reattached_work"] = reattached->snapshot();
                reattached.reset();
            }
            survivor.reset();
            facts["both_controller_lifetimes_ended"] = aObject.isNull() && bObject.isNull();
            // No getter is called on either destroyed measured engine/controller.
        } catch (const std::exception& error) {
            facts["error"] = QString::fromUtf8(error.what());
        }
        restoreCaller();
        facts["caller_restored"] =
            callerGuard && originalGuard && callerGuard->incubationController() == original;
        return facts;
    }
    Q_INVOKABLE QVariantMap restart(const QString& source) const {
        auto* controller = engine_->incubationController();
        // The fresh engine borrows the app's controller; return it to the test host afterwards.
        const auto restore = qScopeGuard([this, controller] {
            engine_->setIncubationController(controller);
        });
        QQmlEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData(source.toUtf8(), QUrl("file:///report-settings-restart.qml"));
        std::unique_ptr<QObject> object(component.create());
        QVariantMap result;
        if (!object) {
            QStringList errors;
            for (const auto& error : component.errors()) errors.append(error.toString());
            result.insert("error", errors.join('\n'));
            return result;
        }
        // A fresh production page may first finish its real calculation. The
        // optional readiness property is observation only; callers without it
        // keep the original synchronous snapshot behavior.
        if (object->metaObject()->indexOfProperty("acceptanceReady") >= 0) {
            QElapsedTimer deadline;
            deadline.start();
            while (!object->property("acceptanceReady").toBool() && deadline.elapsed() < 5000)
                QTest::qWait(10);
            if (!object->property("acceptanceReady").toBool())
                return {{"error", "The fresh production engine did not finish its declared setup"}};
        }
        const auto meta = object->metaObject();
        for (int index = QObject::staticMetaObject.propertyCount(); index < meta->propertyCount(); ++index) {
            const auto property = meta->property(index);
            auto value = property.read(object.get());
            if (value.metaType().flags().testFlag(QMetaType::PointerToQObject)) continue;
            if (value.metaType() == QMetaType::fromType<QJSValue>()) value = value.value<QJSValue>().toVariant();
            result.insert(QString::fromUtf8(property.name()), value);
        }
        return result;
    }
private:
    static bool absoluteLocalFileUrl(const QUrl& url) {
        return url.isValid() && url.isLocalFile() && url.host().isEmpty() && !url.hasQuery() &&
               !url.hasFragment() && QDir::isAbsolutePath(url.toLocalFile());
    }
    std::shared_ptr<ScanStopHold> scan_stop_hold_;
    QPointer<edi_app::ProjectViewModel> scan_stop_project_;
    QQmlEngine* engine_;
    mutable QString web_export_error_;
    std::unique_ptr<AcceptanceAnimationDriver> animation_driver_;
    std::vector<std::unique_ptr<QTemporaryDir>> directories_;
};

static void register_report_settings_proof() {
    qmlRegisterSingletonType<ReportSettingsProof>("ReportAcceptance", 1, 0, "SettingsProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new ReportSettingsProof(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(register_report_settings_proof)
#include "test_report_settings_observer.moc"
