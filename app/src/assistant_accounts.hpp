// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <optional>
#include <QJsonObject>
#include <QList>
#include <QString>
#include "assistant_provider.hpp"

namespace edi_app {

/// One assistant account as edi records it (ADR-0108 §8). Nothing in it comes from inside the runtime's home.
struct AssistantAccountRecord {
    QString id;  ///< a UUID edi created, never derived from the e-mail
    AssistantProviderId provider = AssistantProviderId::ChatGpt;
    QString home;  ///< the config home edi created; empty for the default ChatGPT login
    QString email, plan, host;

    AssistantAccountRef ref() const { return {provider, id, home, host}; }
    QJsonObject toJson() const;
    static std::optional<AssistantAccountRecord> fromJson(AssistantProviderId provider, const QJsonObject& value);
    bool operator==(const AssistantAccountRecord&) const = default;
};

/// The account list in edi's settings file: `Assistant/Providers/<provider>/accounts` as
/// `{version: 1, accounts: [...]}` and `Assistant/activeAccount` as `<provider>/<id>`. Account homes live under
/// `<AppLocalData>/assistant/accounts/<provider>/<id>`; edi creates them empty and never opens anything inside.
class AssistantAccounts {
public:
    /// `settingsPath` is edi's settings file; `accountsRoot` the folder that holds the account homes.
    AssistantAccounts(QString settingsPath, QString accountsRoot);

    /// `<AppLocalData>/assistant/accounts`.
    static QString defaultAccountsRoot();

    /// The provider's accounts in their saved order. Throws when the stored list is not valid.
    QList<AssistantAccountRecord> accounts(AssistantProviderId provider) const;
    std::optional<AssistantAccountRecord> find(AssistantProviderId provider, const QString& id) const;
    /// The first ChatGPT account, which runs with the default login (`home` empty), if recorded.
    std::optional<AssistantAccountRecord> defaultChatGpt() const;

    /// A new account with a fresh id and an empty owner-only home. The record is not saved until `save`.
    AssistantAccountRecord create(AssistantProviderId provider, const QString& host = {}) const;
    /// The record for the default ChatGPT login (`home` empty), not saved until `save`.
    AssistantAccountRecord createDefaultChatGpt() const;
    /// Insert or replace by id. Throws when the settings file cannot be written.
    void save(const AssistantAccountRecord& record);
    /// Drop the record (not its home).
    void remove(AssistantProviderId provider, const QString& id);

    /// The active account, or nothing when none is chosen or it no longer exists.
    std::optional<AssistantAccountRecord> active() const;
    void setActive(AssistantProviderId provider, const QString& id);

    /// True when `home` is an account home this store created, inside the accounts root.
    bool ownsHome(const QString& home) const;
    /// Delete an account home edi created. Refuses anything outside the accounts root.
    bool removeHome(const QString& home) const;

private:
    QString settings_path_, accounts_root_;
    void store(AssistantProviderId provider, const QList<AssistantAccountRecord>& records);
};

/// Parse `chatgpt`, `claude` or `copilot`.
std::optional<AssistantProviderId> assistant_provider_from_key(const QString& key);

}  // namespace edi_app
