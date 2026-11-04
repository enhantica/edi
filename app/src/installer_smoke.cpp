// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QQuickWindow>
#include <QTemporaryDir>
#include <QTimer>
#include <cmath>
#include <stdexcept>
#include "codex_agent.hpp"
#include "edi/io.hpp"

void start_installer_smoke(QQuickWindow& window, const QString& output) {
    QTimer::singleShot(1500, &window, [&window, output] {
        QJsonObject report{{"schema", "edi.installer-smoke/1"}, {"qt", qVersion()}, {"passed", false}};
        try {
            if (!QDir().mkpath(output)) throw std::runtime_error("Cannot create smoke output directory");
            QTemporaryDir project_dir;
            if (!project_dir.isValid()) throw std::runtime_error("Cannot create smoke project directory");
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
            if (status.size() != values.size()) throw std::runtime_error("Engine returned incomplete status");
            for (std::size_t i = 0; i < values.size(); ++i) {
                if (status[i] == "excl") continue;
                const auto value = values[i];
                if (!std::isfinite(value)) throw std::runtime_error("Engine returned non-finite intensity");
                sum += std::abs(value);
            }
            if (!(sum > 0)) throw std::runtime_error("Engine returned a zero pattern");
            report.insert("calculated_points", static_cast<qint64>(values.size()));
            const auto helper = edi_app::CodexAgent::executable();
            if (helper.isEmpty()) throw std::runtime_error("Bundled assistant runtime is unavailable");
            QProcess process;
            process.start(helper, {QStringLiteral("--version")});
            if (!process.waitForStarted(5000) || !process.waitForFinished(10000) ||
                process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0)
                throw std::runtime_error("Bundled assistant runtime did not start");
            report.insert("assistant", QString::fromUtf8(process.readAllStandardOutput()).trimmed());
            const auto image = window.grabWindow();
            if (image.isNull() || !image.save(QDir(output).filePath("window.png")))
                throw std::runtime_error("Application did not render a window");
            report.insert("passed", true);
        } catch (const std::exception& error) {
            report.insert("error", QString::fromUtf8(error.what()));
        }
        QFile receipt(QDir(output).filePath("result.json"));
        const auto bytes = QJsonDocument(report).toJson();
        const bool written = receipt.open(QIODevice::WriteOnly) && receipt.write(bytes) == bytes.size();
        receipt.close();
        QCoreApplication::exit(written && report.value("passed").toBool() ? 0 : 1);
    });
}
