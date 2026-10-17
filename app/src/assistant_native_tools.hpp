// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QJsonObject>
#include <QString>
#include <optional>
#include <string>
#include <vector>
#include "edi/edit.hpp"
namespace edi_app {
// Only these concrete implemented actions are registered with the official agent.
QJsonArray assistant_native_tool_specs();
bool assistant_native_tool(const QString& name);
QString assistant_native_purpose(const QJsonObject& arguments);
std::optional<edi::Edit> assistant_native_edit(edi::Project& project, const QString& name, const QJsonObject& arguments, std::vector<std::pair<std::string, bool>>& beforeFlags);
struct NativeBackgroundInput { edi::ExperimentBase* experiment = nullptr; edi::BackgroundPointInput input; };
NativeBackgroundInput assistant_native_background(edi::Project&, const QJsonObject&);
void assistant_native_arguments(const QString& name, const QJsonObject& arguments);
} // namespace edi_app
