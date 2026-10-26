// SPDX-License-Identifier: BSD-3-Clause
// Passive object/font inventory and private copies; no chart rules or font oracle.
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QMap>
#include <QQuickItem>
#include <QSet>
#include <QTemporaryDir>
#include <QUrl>
#include <QtQml/qqml.h>
#include <memory>
#include <vector>

class ChartFontProbe : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
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
