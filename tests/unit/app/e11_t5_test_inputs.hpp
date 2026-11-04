// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QByteArray>
#include <QDir>
#include <QFileInfo>
#include <QString>
#include <stdexcept>

#include "edi/version.hpp"

// The ordinary app-test caller selects native. A historical source phase must
// still be explicitly requested and must match its compiled phase adapter.
namespace e11_test_inputs {
inline QByteArray phase(const char* variable) {
    const auto value = qEnvironmentVariableIsSet(variable) ? qgetenv(variable)
                                                          : QByteArrayLiteral("native");
    if (value != "native" && value != "original")
        throw std::runtime_error("Selected test phase must be native or original");
    return value;
}

inline QString sourceRoot(const char* variable) {
    const auto root = qEnvironmentVariableIsSet(variable)
        ? QString::fromUtf8(qgetenv(variable))
        : QFileInfo(QString::fromUtf8(__FILE__)).absoluteDir().absoluteFilePath(QStringLiteral("../../.."));
    if (root.isEmpty() || !QDir::isAbsolutePath(root) || !QFileInfo(root).isDir()
        || !QFileInfo(QDir(root).filePath(QStringLiteral("pixi.toml"))).isFile())
        throw std::runtime_error("Selected source root must be the actual absolute repository root");
    return QFileInfo(root).canonicalFilePath();
}

inline QByteArray sourceRevision(const char* variable) {
    // Keep the runner's full dirty/clean build marker in its ordinary output.
    // This field is the source revision, not a clean-build attestation.
    const auto value = qEnvironmentVariableIsSet(variable)
        ? qgetenv(variable) : QByteArray(edi::build_commit()).left(40);
    if (value.size() != 40)
        throw std::runtime_error("Selected source revision must be a full Git SHA");
    for (const auto byte : value)
        if (!((byte >= '0' && byte <= '9') || (byte >= 'a' && byte <= 'f')))
            throw std::runtime_error("Selected source revision must be a lowercase full Git SHA");
    return value;
}
}  // namespace e11_test_inputs
