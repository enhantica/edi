// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_providers.hpp"
#include <stdexcept>
#include <QFileInfo>
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
}  // namespace

QString assistant_provider_executable(AssistantProviderId id) {
    switch (id) {
        case AssistantProviderId::ChatGpt: return CodexAgent::executable();
        case AssistantProviderId::Claude: return development_override("EDI_CLAUDE_DEVELOPMENT_EXECUTABLE");
        case AssistantProviderId::Copilot: return development_override("EDI_COPILOT_DEVELOPMENT_EXECUTABLE");
    }
    return {};
}

bool assistant_provider_available(AssistantProviderId id) noexcept {
    try {
        return !assistant_provider_executable(id).isEmpty() && id == AssistantProviderId::ChatGpt;
    } catch (...) {
        return false;
    }
}

std::unique_ptr<AssistantProvider> make_assistant_provider(const AssistantAccountRef& account, QObject* parent,
                                                           std::shared_ptr<const void> releaseOwner) {
    switch (account.provider) {
        case AssistantProviderId::ChatGpt: return std::make_unique<CodexAgent>(parent, std::move(releaseOwner));
        case AssistantProviderId::Claude:
        case AssistantProviderId::Copilot: return nullptr;
    }
    return nullptr;
}

}  // namespace edi_app
