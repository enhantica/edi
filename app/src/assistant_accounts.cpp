// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_accounts.hpp"
#include <stdexcept>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QSettings>
#include <QStandardPaths>
#include <QUuid>

namespace edi_app {

namespace {
QString accounts_key(AssistantProviderId provider) {
    return QStringLiteral("Assistant/Providers/%1/accounts").arg(assistant_provider_key(provider));
}
constexpr auto active_key = "Assistant/activeAccount";

}  // namespace

std::optional<AssistantProviderId> assistant_provider_from_key(const QString& key) {
    for (const auto id : {AssistantProviderId::ChatGpt, AssistantProviderId::Claude, AssistantProviderId::Copilot})
        if (assistant_provider_key(id) == key) return id;
    return std::nullopt;
}

QJsonObject AssistantAccountRecord::toJson() const {
    return {{"id", id}, {"provider", assistant_provider_key(provider)}, {"home", home},
            {"email", email}, {"plan", plan}, {"host", host}};
}

std::optional<AssistantAccountRecord> AssistantAccountRecord::fromJson(AssistantProviderId provider,
                                                                      const QJsonObject& value) {
    // id is required; the other fields may be absent but never of another type.
    if (!value.value("id").isString()) return std::nullopt;
    for (const auto* field : {"provider", "home", "email", "plan", "host"}) {
        const auto member = value.value(QLatin1StringView(field));
        if (!member.isUndefined() && !member.isString()) return std::nullopt;
    }
    if (value.contains("provider") && value.value("provider").toString() != assistant_provider_key(provider))
        return std::nullopt;
    AssistantAccountRecord record{value.value("id").toString(), provider, value.value("home").toString(),
                                  value.value("email").toString(), value.value("plan").toString(),
                                  value.value("host").toString()};
    // The id names a folder and a settings key, so it is one plain path segment.
    static const QRegularExpression safe(QStringLiteral("^[A-Za-z0-9._-]{1,64}$"));
    if (!safe.match(record.id).hasMatch() || record.id == QLatin1String(".") || record.id == QLatin1String(".."))
        return std::nullopt;
    // Only the default ChatGPT login runs without a home of its own.
    if (record.home.isEmpty() && provider != AssistantProviderId::ChatGpt) return std::nullopt;
    return record;
}

AssistantAccounts::AssistantAccounts(QString settingsPath, const QString& accountsRoot)
    : settings_path_(std::move(settingsPath)), accounts_root_(QDir::cleanPath(accountsRoot)) {}

QString AssistantAccounts::defaultAccountsRoot() {
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    return base.isEmpty() ? QString() : QDir::cleanPath(base + QStringLiteral("/assistant/accounts"));
}

QList<AssistantAccountRecord> AssistantAccounts::accounts(AssistantProviderId provider) const {
    if (settings_path_.isEmpty()) return {};
    const QSettings settings(settings_path_, QSettings::IniFormat);
    const auto bytes = settings.value(accounts_key(provider)).toByteArray();
    if (settings.status() != QSettings::NoError) throw std::runtime_error("The assistant accounts could not be read");
    if (bytes.isEmpty()) return {};
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(bytes, &error);
    if (error.error != QJsonParseError::NoError || !document.isObject() ||
        document.object().value("version") != 1 || !document.object().value("accounts").isArray())
        throw std::runtime_error("The saved assistant accounts are not valid");
    QList<AssistantAccountRecord> result;
    for (const auto& value : document.object().value("accounts").toArray()) {
        auto record = AssistantAccountRecord::fromJson(provider, value.toObject());
        if (!record) throw std::runtime_error("The saved assistant accounts are not valid");
        for (const auto& other : result)
            if (other.id == record->id) throw std::runtime_error("The saved assistant accounts are not valid");
        result.append(*record);
    }
    return result;
}

std::optional<AssistantAccountRecord> AssistantAccounts::find(AssistantProviderId provider, const QString& id) const {
    for (const auto& record : accounts(provider))
        if (record.id == id) return record;
    return std::nullopt;
}

std::optional<AssistantAccountRecord> AssistantAccounts::defaultChatGpt() const {
    for (const auto& record : accounts(AssistantProviderId::ChatGpt))
        if (record.home.isEmpty()) return record;
    return std::nullopt;
}

AssistantAccountRecord AssistantAccounts::create(AssistantProviderId provider, const QString& host) const {
    if (accounts_root_.isEmpty()) throw std::runtime_error("The assistant account folder is unavailable");
    AssistantAccountRecord record;
    record.id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    record.provider = provider;
    record.host = host;
    record.home = QDir::cleanPath(accounts_root_ + QLatin1Char('/') + assistant_provider_key(provider) +
                                  QLatin1Char('/') + record.id);
    if (!QDir().mkpath(record.home)) throw std::runtime_error("The assistant account folder could not be created");
    // Owner-only, like edi's other app-local assistant folders; the runtime keeps its login here.
    QFile::setPermissions(record.home, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
    return record;
}

AssistantAccountRecord AssistantAccounts::createDefaultChatGpt() const {
    AssistantAccountRecord record;
    record.id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    record.provider = AssistantProviderId::ChatGpt;
    return record;
}

void AssistantAccounts::store(AssistantProviderId provider, const QList<AssistantAccountRecord>& records) {
    if (settings_path_.isEmpty()) throw std::runtime_error("The local settings store is unavailable");
    QJsonArray list;
    for (const auto& record : records) list.append(record.toJson());
    const auto bytes = QJsonDocument(QJsonObject{{"version", 1}, {"accounts", list}}).toJson(QJsonDocument::Compact);
    QSettings settings(settings_path_, QSettings::IniFormat);
    settings.setValue(accounts_key(provider), bytes);
    settings.sync();
    if (settings.status() != QSettings::NoError) throw std::runtime_error("The assistant account could not be saved");
}

void AssistantAccounts::save(const AssistantAccountRecord& record) {
    auto records = accounts(record.provider);
    bool replaced = false;
    for (auto& existing : records)
        if (existing.id == record.id) {
            existing = record;
            replaced = true;
        }
    if (!replaced) records.append(record);
    store(record.provider, records);
}

void AssistantAccounts::remove(AssistantProviderId provider, const QString& id) {
    auto records = accounts(provider);
    records.removeIf([&](const AssistantAccountRecord& record) { return record.id == id; });
    store(provider, records);
}

std::optional<AssistantAccountRecord> AssistantAccounts::active() const {
    if (settings_path_.isEmpty()) return std::nullopt;
    const QSettings settings(settings_path_, QSettings::IniFormat);
    const auto value = settings.value(QLatin1StringView(active_key)).toString();
    const auto slash = value.indexOf(QLatin1Char('/'));
    if (slash <= 0) return std::nullopt;
    const auto provider = assistant_provider_from_key(value.left(slash));
    if (!provider) return std::nullopt;
    return find(*provider, value.mid(slash + 1));
}

void AssistantAccounts::setActive(AssistantProviderId provider, const QString& id) {
    if (settings_path_.isEmpty()) throw std::runtime_error("The local settings store is unavailable");
    QSettings settings(settings_path_, QSettings::IniFormat);
    settings.setValue(QLatin1StringView(active_key), assistant_provider_key(provider) + QLatin1Char('/') + id);
    settings.sync();
    if (settings.status() != QSettings::NoError) throw std::runtime_error("The active assistant account could not be saved");
}

bool AssistantAccounts::ownsHome(const QString& home) const {
    if (home.isEmpty() || accounts_root_.isEmpty()) return false;
    const auto root = QFileInfo(accounts_root_).canonicalFilePath();
    const QFileInfo entry(QDir::cleanPath(home));
    if (root.isEmpty() || entry.isSymLink()) return false;
    const auto actual = entry.canonicalFilePath();
    if (actual.isEmpty()) return false;
    // A home is <root>/<provider>/<id>.
    const QFileInfo parent(QFileInfo(actual).path());
    return parent.path() == root && assistant_provider_from_key(parent.fileName()).has_value();
}

bool AssistantAccounts::removeHome(const QString& home) const {
    if (!ownsHome(home)) return false;
    return QDir(home).removeRecursively();
}

}  // namespace edi_app
