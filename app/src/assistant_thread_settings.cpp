// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_thread_settings.hpp"

#include <QDir>

namespace edi_app {

QString comparable_path(const QString& path, bool windows) {
    QString out = path;
    if (windows) {
        out.replace(QLatin1Char('\\'), QLatin1Char('/'));
        // The long-path form a canonicalised Windows path comes back in.
        if (out.startsWith(QLatin1String("//?/UNC/"), Qt::CaseInsensitive))
            out = QStringLiteral("//") + out.mid(8);
        else if (out.startsWith(QLatin1String("//?/")))
            out = out.mid(4);
    }
    out = QDir::cleanPath(out);
    return windows ? out.toCaseFolded() : out;
}

bool same_path(const QJsonValue& actual, const QString& expected, bool windows) {
    return actual.isString() && !expected.isEmpty() &&
           comparable_path(actual.toString(), windows) == comparable_path(expected, windows);
}

QString readonly_sandbox_mismatch(const QJsonValue& value, QStringList* extra) {
    if (!value.isObject()) return QStringLiteral("sandbox");
    const QJsonObject policy = value.toObject();
    if (policy.value(QLatin1String("type")) != QLatin1String("readOnly")) return QStringLiteral("sandbox.type");
    const QJsonValue network = policy.value(QLatin1String("networkAccess"));
    if (!network.isBool() || network.toBool()) return QStringLiteral("sandbox.networkAccess");
    if (extra != nullptr) {
        for (const QString& key : policy.keys())
            if (key != QLatin1String("type") && key != QLatin1String("networkAccess")) extra->append(key);
    }
    return {};
}

QString thread_settings_mismatch(const QJsonObject& actual, const ThreadSettingsWanted& wanted, const QString& effortKey,
                                 const QString& sandboxKey, QStringList* extra, bool windows) {
    if (!same_path(actual.value(QLatin1String("cwd")), wanted.workspace, windows)) return QStringLiteral("cwd");
    if (actual.value(QLatin1String("modelProvider")) != QLatin1String("openai")) return QStringLiteral("modelProvider");
    if (actual.value(QLatin1String("model")) != wanted.model) return QStringLiteral("model");
    if (actual.value(effortKey) != wanted.effort) return QStringLiteral("effort");
    if (actual.value(QLatin1String("approvalPolicy")) != QLatin1String("never")) return QStringLiteral("approvalPolicy");
    if (actual.value(QLatin1String("approvalsReviewer")) != QLatin1String("user"))
        return QStringLiteral("approvalsReviewer");
    return readonly_sandbox_mismatch(actual.value(sandboxKey), extra);
}

const char* thread_policy_code(const QString& field) {
    if (field == QLatin1String("cwd")) return "THREAD_POLICY_CWD";
    if (field == QLatin1String("modelProvider")) return "THREAD_POLICY_PROVIDER";
    if (field == QLatin1String("model")) return "THREAD_POLICY_MODEL";
    if (field == QLatin1String("effort")) return "THREAD_POLICY_EFFORT";
    if (field == QLatin1String("approvalPolicy")) return "THREAD_POLICY_APPROVAL";
    if (field == QLatin1String("approvalsReviewer")) return "THREAD_POLICY_REVIEWER";
    if (field == QLatin1String("sandbox")) return "THREAD_POLICY_SANDBOX";
    if (field == QLatin1String("sandbox.type")) return "THREAD_POLICY_SANDBOX_TYPE";
    if (field == QLatin1String("sandbox.networkAccess")) return "THREAD_POLICY_SANDBOX_NETWORK";
    return "THREAD_POLICY";
}

}  // namespace edi_app
