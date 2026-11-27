// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_providers.hpp"
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
