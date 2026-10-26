// SPDX-License-Identifier: BSD-3-Clause
// Passive object/font inventory and private copies; no chart rules or font oracle.
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QMap>
#include <QJsonArray>
#include <QJsonDocument>
#include <QQuickItem>
#include <QSet>
#include <QTemporaryDir>
#include <QUrl>
#include <QtQml/qqml.h>
#include <memory>
#include <vector>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
EM_JS_DEPS(chart_font_observation, "$UTF8ToString");
#endif

class ChartFontProbe : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QVariantList cases() const {
        QString path = QStringLiteral(":/chart-fonts/tests/fixtures/chart_fonts/cases.json");
        if (!QFile::exists(path))
            path = QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath())
                       .absoluteFilePath("../../fixtures/chart_fonts/cases.json");
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) return {};
        const QVariantList all = QJsonDocument::fromJson(file.readAll()).array().toVariantList();
#ifdef __EMSCRIPTEN__
        const QString selected = QString::fromUtf8(emscripten_run_script_string(
            "new URLSearchParams(window.location.search).get('chart') || ''"));
        if (!selected.isEmpty()) {
            QVariantList result;
            for (const QVariant& row : all)
                if (row.toMap().value("tag").toString() == selected) result.append(row);
            return result;
        }
#endif
        return all;
    }
    Q_INVOKABLE void publish(const QVariantMap& observation) const {
#ifdef __EMSCRIPTEN__
        const QByteArray json = QJsonDocument::fromVariant(observation).toJson(QJsonDocument::Compact);
        EM_ASM({ window.__chartFontObservation = JSON.parse(UTF8ToString($0)); }, json.constData());
#else
        Q_UNUSED(observation);
#endif
    }
    Q_INVOKABLE QVariantList objects(QObject* root) const {
        QVariantList result;
        QSet<QObject*> seen;
        const auto visit = [&](auto&& self, QObject* object) -> void {
            if (!object || seen.contains(object)) return;
            seen.insert(object);
            result.append(QVariant::fromValue(object));
            for (QObject* child : object->children()) self(self, child);
            if (const auto* item = qobject_cast<QQuickItem*>(object))
                for (QQuickItem* child : item->childItems()) self(self, child);
        };
        visit(visit, root);
        return result;
    }
    Q_INVOKABLE bool nativeText(QObject* object) const {
        return object && (object->inherits("QQuickText") || object->inherits("QQuickTextInput"));
    }
    Q_INVOKABLE QUrl project(const QString& kind) {
        const QMap<QString, QString> projects{
            {"powder", "tests/fixtures/loop_parameter_ids/line-segment"},
            {"single", "docs/user/cli/sc-neut-cwl_pr2nio4-5c2_fit/project"},
            {"scan", "tests/fixtures/report_evolution/project"},
            {"correlations", "tests/fixtures/correlations/polynomial-3"}};
        if (!projects.contains(kind)) return {};
        const QString relative = projects.value(kind);
        const QString bundled = QStringLiteral(":/chart-fonts/") + relative;
        const QString source = QFile::exists(bundled + "/project.edi") ? bundled
            : QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../../" + relative);
        if (!QFile::exists(source + "/project.edi")) return {};
        auto directory = std::make_unique<QTemporaryDir>();
        if (!directory->isValid()) return {};
        QDirIterator files(source, QDir::Files, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const QString from = files.next();
            const QString to = QDir(directory->path()).filePath(QDir(source).relativeFilePath(from));
            if (!QDir().mkpath(QFileInfo(to).absolutePath()) || !QFile::copy(from, to)) return {};
        }
        const QUrl url = QUrl::fromLocalFile(directory->path());
        projects_.push_back(std::move(directory));
        return url;
    }
private:
    std::vector<std::unique_ptr<QTemporaryDir>> projects_;
};

static void register_chart_font_probe() {
    qmlRegisterType<ChartFontProbe>("ChartFontAcceptance", 1, 0, "ChartFontProbe");
}
Q_COREAPP_STARTUP_FUNCTION(register_chart_font_probe)
#include "test_chart_fonts.moc"
