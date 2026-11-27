// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_providers.hpp"
#include <stdexcept>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include "claude_runtime_config.hpp"
#include "copilot_runtime_config.hpp"
#include "assistant_accounts.hpp"
#include "assistant_runtime_translator.hpp"
#include "claude_session.hpp"
#include "copilot_session.hpp"
#include "codex_agent.hpp"

namespace edi_app {

QString assistant_provider_key(AssistantProviderId id) {
    switch (id) {
        case AssistantProviderId::ChatGpt: return QStringLiteral("chatgpt");
        case AssistantProviderId::Claude: return QStringLiteral("claude");
        case AssistantProviderId::Copilot: return QStringLiteral("copilot");
    }
    return {};
}

QString assistant_provider_name(AssistantProviderId id) {
    switch (id) {
        case AssistantProviderId::ChatGpt: return QStringLiteral("ChatGPT");
        case AssistantProviderId::Claude: return QStringLiteral("Claude");
        case AssistantProviderId::Copilot: return QStringLiteral("GitHub Copilot");
    }
    return {};
}

QString assistant_provider_company(AssistantProviderId id) {
    switch (id) {
        case AssistantProviderId::ChatGpt: return QStringLiteral("OpenAI");
        case AssistantProviderId::Claude: return QStringLiteral("Anthropic");
        case AssistantProviderId::Copilot: return QStringLiteral("GitHub");
    }
    return {};
}

namespace {
QString development_override(const char* variable) {
    if (!qEnvironmentVariableIsSet(variable)) return {};
    const QFileInfo file(qEnvironmentVariable(variable));
    // An explicit developer composition, never a silent fallback to another runtime.
    if (!file.isAbsolute() || !file.isFile() || !file.isExecutable())
        throw std::runtime_error("The explicit development agent executable is unavailable");
    return file.absoluteFilePath();
}
// The bundled runtime when its package was staged and its identity file names this build's pin, else empty.
QString bundled_runtime(const char* runtime, bool available, const char* buildAppDir, const char* buildDir,
                        const char* installRelative, const char* version, const char* entrypoint) {
    if (!available) return {};
    const auto app = QDir::cleanPath(QCoreApplication::applicationDirPath());
    const auto root = app == QDir::cleanPath(QString::fromUtf8(buildAppDir))
                          ? QString::fromUtf8(buildDir)
                          : QDir(app).absoluteFilePath(QString::fromUtf8(installRelative));
    QFile identity(root + QStringLiteral("/edi-runtime.json"));
    if (!identity.open(QIODevice::ReadOnly) || identity.size() > 64 * 1024) return {};
    QJsonParseError error;
    const auto parsed = QJsonDocument::fromJson(identity.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !parsed.isObject()) return {};
    const auto metadata = parsed.object();
    if (metadata.value("runtime") != QLatin1StringView(runtime) || metadata.value("version") != QLatin1StringView(version) ||
        metadata.value("entrypoint") != QString::fromUtf8(entrypoint))
        return {};
    const auto executable = root + QLatin1Char('/') + QString::fromUtf8(entrypoint);
    const QFileInfo file(executable);
    return file.isFile() && file.isExecutable() ? executable : QString();
}
}  // namespace

QString assistant_provider_executable(AssistantProviderId id) {
    switch (id) {
        case AssistantProviderId::ChatGpt: return CodexAgent::executable();
        case AssistantProviderId::Claude:
            if (qEnvironmentVariableIsSet("EDI_CLAUDE_DEVELOPMENT_EXECUTABLE"))
                return development_override("EDI_CLAUDE_DEVELOPMENT_EXECUTABLE");
            return bundled_runtime("claude", EDI_CLAUDE_RUNTIME_AVAILABLE, EDI_CLAUDE_BUILD_APP_DIR,
                                   EDI_CLAUDE_RUNTIME_BUILD_DIR, EDI_CLAUDE_INSTALL_RELATIVE,
                                   EDI_CLAUDE_RUNTIME_VERSION, EDI_CLAUDE_RUNTIME_ENTRYPOINT);
        case AssistantProviderId::Copilot:
            if (qEnvironmentVariableIsSet("EDI_COPILOT_DEVELOPMENT_EXECUTABLE"))
                return development_override("EDI_COPILOT_DEVELOPMENT_EXECUTABLE");
            return bundled_runtime("copilot", EDI_COPILOT_RUNTIME_AVAILABLE, EDI_COPILOT_BUILD_APP_DIR,
                                   EDI_COPILOT_RUNTIME_BUILD_DIR, EDI_COPILOT_INSTALL_RELATIVE,
                                   EDI_COPILOT_RUNTIME_VERSION, EDI_COPILOT_RUNTIME_ENTRYPOINT);
    }
    return {};
}

bool assistant_provider_available(AssistantProviderId id) noexcept {
    try {
        return !assistant_provider_executable(id).isEmpty();
    } catch (...) {
        return false;
    }
}

std::unique_ptr<AssistantProvider> make_assistant_provider(const AssistantAccountRef& account, QObject* parent,
                                                           std::shared_ptr<const void> releaseOwner) {
    switch (account.provider) {
        case AssistantProviderId::ChatGpt: return std::make_unique<CodexAgent>(parent, std::move(releaseOwner));
        case AssistantProviderId::Claude: {
            if (!assistant_provider_available(AssistantProviderId::Claude)) return nullptr;
            auto session = std::make_unique<ClaudeSession>();
            session->setAccountRecord(account.email, {});
            AssistantRuntimeLaunch launch;
            launch.account = account;
            launch.environment = QProcessEnvironment::systemEnvironment();
            launch.toolTimeoutMs = assistant_tool_timeout_ms;
            return std::make_unique<AssistantRuntimeTranslator>(AssistantProviderId::Claude, std::move(session),
                                                                std::move(launch), parent, std::move(releaseOwner));
        }
        case AssistantProviderId::Copilot: {
            if (!assistant_provider_available(AssistantProviderId::Copilot)) return nullptr;
            AssistantRuntimeLaunch launch;
            launch.account = account;
            launch.environment = QProcessEnvironment::systemEnvironment();
            launch.toolTimeoutMs = assistant_tool_timeout_ms;
            return std::make_unique<AssistantRuntimeTranslator>(AssistantProviderId::Copilot,
                                                                std::make_unique<CopilotSession>(AssistantAccounts::defaultAccountsRoot()), std::move(launch),
                                                                parent, std::move(releaseOwner));
        }
    }
    return nullptr;
}

}  // namespace edi_app
