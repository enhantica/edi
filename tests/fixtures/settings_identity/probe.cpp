// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <cstdio>

namespace edi_app {
#include "settings_provider.inc"
}

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    if (argc != 3) return 2;
    const QString root = QString::fromLocal8Bit(argv[1]);
    const QString scenario = QString::fromLocal8Bit(argv[2]);
    QCoreApplication::setOrganizationName(edi_app::settings_organisation());
    QCoreApplication::setApplicationName("EasyDiffraction");
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, root);
    const QString legacy = QSettings(QSettings::IniFormat, QSettings::UserScope,
                                    "EasyScience", "EasyDiffraction").fileName();
    const QString current = edi_app::settings_store_path();
    if (scenario != "no-legacy") {
        QSettings old(legacy, QSettings::IniFormat);
        old.setValue("edi/feedbackName", QString::fromUtf8("Zoë Example"));
        old.setValue("edi/feedbackEmail", "zoe@example.invalid");
        old.setValue("edi/toolTipDelay", 1739);
        old.setValue("edi/autoCollapse", false);
        old.sync();
    }
    if (scenario == "populated") {
        QSettings store(current, QSettings::IniFormat);
        store.setValue("destination-only", 2718);
        store.sync();
    }
    if (scenario == "zero-byte") {
        QDir().mkpath(QFileInfo(current).absolutePath());
        QFile file(current);
        if (!file.open(QIODevice::WriteOnly)) return 3;
    }
    if (scenario == "fresh") edi_app::use_fresh_settings();
    edi_app::migrate_legacy_settings();
    if (scenario == "repeat") {
        { QSettings old(legacy, QSettings::IniFormat); old.setValue("edi/toolTipDelay", 999); old.sync(); }
        { QSettings store(current, QSettings::IniFormat); store.setValue("edi/feedbackName", "Current User"); store.sync(); }
        edi_app::migrate_legacy_settings();
    }
    const QSettings store(current, QSettings::IniFormat);
    const QSettings old(legacy, QSettings::IniFormat);
    QJsonObject values;
    for (const auto& key : store.allKeys()) values[key] = QJsonValue::fromVariant(store.value(key));
    for (const auto& key : {QString("edi/toolTipDelay"), QString("destination-only")}) {
        if (store.contains(key)) values[key] = store.value(key).toInt();
    }
    if (store.contains("edi/autoCollapse")) values["edi/autoCollapse"] = store.value("edi/autoCollapse").toBool();
    QJsonObject result{{"organisation", edi_app::settings_organisation()},
                       {"values", values}, {"legacy_exists", QFileInfo::exists(legacy)},
                       {"legacy_name", old.value("edi/feedbackName").toString()},
                       {"current_exists", QFileInfo::exists(current)}};
    const auto bytes = QJsonDocument(result).toJson(QJsonDocument::Compact);
    std::fwrite(bytes.constData(), 1, bytes.size(), stdout);
}
