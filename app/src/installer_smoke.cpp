// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QImageReader>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QSvgRenderer>
#include <QTemporaryDir>
#include <QTimer>
#include <cmath>
#include <stdexcept>

#include "build_version.hpp"
#include "codex_agent.hpp"
#include "desktop_updates.hpp"
#include "edi/io.hpp"

void start_installer_smoke(QQuickWindow& window, const QString& output) {
    QTimer::singleShot(1500, &window, [&window, output] {
        QJsonObject report{
            {"schema", "edi.installer-smoke/1"}, {"qt", qVersion()}, {"passed", false}};
        try {
            if (!QDir().mkpath(output))
                throw std::runtime_error("Cannot create smoke output directory");
            const auto version = QString::fromUtf8(edi_app::app_version());
            report.insert("app_version", version);
            static const QRegularExpression calendar(
                QStringLiteral(R"(\A[0-9]{4}\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)\z)"));
            if (calendar.match(version).hasMatch()) {
                QFile history(QStringLiteral(":/edi/releases.json"));
                if (!history.open(QIODevice::ReadOnly))
                    throw std::runtime_error("Bundled release history is missing");
                const auto bytes = history.readAll();
                bool valid = false;
                const auto entries = edi_app::release_changes(bytes, version, &valid);
                if (!valid || entries.isEmpty() ||
                    entries.first().toMap().value("version").toString() != version)
                    throw std::runtime_error(
                        "Bundled release history does not contain this application release");
                report.insert(
                    "release_history_sha256",
                    QString::fromLatin1(
                        QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex()));
            }
            for (const auto& name :
                 {QStringLiteral("App.svg"), QStringLiteral("AssistantSpinner.svg")}) {
                const auto path = QStringLiteral(":/qt/qml/edi/app/resources/logo/") + name;
                QSvgRenderer vector(path);
                QImageReader reader(path);
                if (!vector.isValid() || reader.read().isNull())
                    throw std::runtime_error(
                        (QStringLiteral("Bundled SVG image cannot be decoded: ") + name +
                         QStringLiteral(": ") + reader.errorString())
                            .toStdString());
            }
            report.insert("svg_images", true);
            QTemporaryDir project_dir;
            if (!project_dir.isValid())
                throw std::runtime_error("Cannot create smoke project directory");
            const QString resource = QStringLiteral(":/edi/installer-smoke/");
            QDirIterator files(resource, QDir::Files, QDirIterator::Subdirectories);
            while (files.hasNext()) {
                const auto source = files.next();
                const auto target = project_dir.filePath(source.mid(resource.size()));
                if (!QDir().mkpath(QFileInfo(target).path()) || !QFile::copy(source, target))
                    throw std::runtime_error("Cannot unpack embedded smoke project");
            }
            auto project = edi::load_project(project_dir.path().toStdString());
            project.calculate();
            const auto& values = project.experiments[0]->data->intensity_calc;
            if (values.empty()) throw std::runtime_error("Engine returned an empty pattern");
            double sum = 0;
            const auto& status = project.experiments[0]->data->calc_status;
            if (status.size() != values.size())
                throw std::runtime_error("Engine returned incomplete status");
            for (std::size_t i = 0; i < values.size(); ++i) {
                if (status[i] == "excl") continue;
                const auto value = values[i];
                if (!std::isfinite(value))
                    throw std::runtime_error("Engine returned non-finite intensity");
                sum += std::abs(value);
            }
            if (!(sum > 0)) throw std::runtime_error("Engine returned a zero pattern");
            report.insert("calculated_points", static_cast<qint64>(values.size()));
            const auto helper = edi_app::CodexAgent::executable();
            if (helper.isEmpty())
                throw std::runtime_error("Bundled assistant runtime is unavailable");
            QProcess process;
            process.start(helper, {QStringLiteral("--version")});
            if (!process.waitForStarted(5000) || !process.waitForFinished(10000) ||
                process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0)
                throw std::runtime_error("Bundled assistant runtime did not start");
            report.insert("assistant",
                          QString::fromUtf8(process.readAllStandardOutput()).trimmed());
            const auto image = window.grabWindow();
            if (image.isNull() || !image.save(QDir(output).filePath("window.png")))
                throw std::runtime_error("Application did not render a window");
            report.insert("passed", true);
        } catch (const std::exception& error) {
            report.insert("error", QString::fromUtf8(error.what()));
        }
        QFile receipt(QDir(output).filePath("result.json"));
        const auto bytes = QJsonDocument(report).toJson();
        const bool written =
            receipt.open(QIODevice::WriteOnly) && receipt.write(bytes) == bytes.size();
        receipt.close();
        QCoreApplication::exit(written && report.value("passed").toBool() ? 0 : 1);
    });
}
