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
// These concrete actions form the default official-agent advertisement.
// Strict compatibility dispatch is separate from this names/specification list.
// Names-only discovery never constructs registry-backed schemas.
QJsonArray assistant_native_tool_names();
// Callback-free preflight over borrowed registered tokens. Caller reserves this
// simultaneous preparation role before building the full catalogue. No cache.
quint64 assistant_native_tool_specs_preparation_bytes();
QJsonArray assistant_native_tool_specs();
bool assistant_native_tool(const QString& name);
QString assistant_native_purpose(const QJsonObject& arguments, const QString& action = {});
QString assistant_native_description(const QString& action, const QString& code = {});
std::optional<edi::Edit> assistant_native_edit(edi::Project& project, const QString& name, const QJsonObject& arguments, std::vector<std::pair<std::string, bool>>& beforeFlags);
struct NativeBackgroundInput { edi::ExperimentBase* experiment = nullptr; edi::BackgroundPointInput input; bool names=false; };
NativeBackgroundInput assistant_native_background(edi::Project&, const QJsonObject&);
void assistant_native_arguments(const QString& name, const QJsonObject& arguments);
} // namespace edi_app
