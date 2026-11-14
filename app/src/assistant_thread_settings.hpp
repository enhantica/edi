// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_ASSISTANT_THREAD_SETTINGS_HPP
#define EDI_APP_ASSISTANT_THREAD_SETTINGS_HPP

#include <QJsonObject>
#include <QJsonValue>
#include <QString>
#include <QStringList>

namespace edi_app {

// Checks of the settings the agent reports for a thread against the ones the app asked for. Windows replies spell
// the same folder differently (backslashes, a \\?\ prefix, another drive-letter case) and add fields to the sandbox
// object, so paths compare as paths and the sandbox by its two fields that matter.

#ifdef Q_OS_WIN
inline constexpr bool kWindowsPaths = true;
#else
inline constexpr bool kWindowsPaths = false;
#endif

// A path as compared: forward slashes, no \\?\ prefix, cleaned, case-folded on Windows.
QString comparable_path(const QString& path, bool windows = kWindowsPaths);
// Whether the agent's `actual` (a string) names the folder `expected`.
bool same_path(const QJsonValue& actual, const QString& expected, bool windows = kWindowsPaths);

// Empty when `value` is a read-only sandbox without network access; otherwise the field that differs ("sandbox",
// "sandbox.type" or "sandbox.networkAccess"). Keys beyond those two are allowed and go to `extra`.
QString readonly_sandbox_mismatch(const QJsonValue& value, QStringList* extra = nullptr);

// What the app asked for.
struct ThreadSettingsWanted {
    QString workspace;
    QString model;
    QString effort;
};

// Empty when `actual` matches `wanted` with the never-ask, user-reviewed, read-only policy; otherwise the first field
// that differs. `effortKey` and `sandboxKey` are the reply's names for them ("reasoningEffort" and "sandbox" in a
// thread/start or thread/resume reply, "effort" and "sandboxPolicy" in thread/settings/updated).
QString thread_settings_mismatch(const QJsonObject& actual, const ThreadSettingsWanted& wanted, const QString& effortKey,
                                 const QString& sandboxKey, QStringList* extra = nullptr,
                                 bool windows = kWindowsPaths);

// The diagnostic code for a mismatching field: THREAD_POLICY_CWD, THREAD_POLICY_SANDBOX and so on; THREAD_POLICY
// for an empty or unknown field. A static string, as the reply handler keeps codes as const char*.
const char* thread_policy_code(const QString& field);

}  // namespace edi_app

#endif
