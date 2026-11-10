// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QSettings>
#include <QStringList>
#include "engine_setup.hpp"

namespace edi_app::test {
inline void assistant_defaults() {
    const auto path = settings_file_path();
    if (path.isEmpty()) qFatal("Configure the test engine before its assistant settings");
    QSettings settings(path, QSettings::IniFormat);
    const QString key = QStringLiteral("Assistant/Providers/chatgpt/selection");
    if (!settings.contains(key))
        settings.setValue(key, QStringList{QStringLiteral("gpt-6-luna"), QStringLiteral("medium")});
    settings.sync();
    if (settings.status() != QSettings::NoError) qFatal("Assistant test settings could not be written");
}
}
