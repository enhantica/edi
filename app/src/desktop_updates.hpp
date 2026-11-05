// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QNetworkAccessManager>
#include <QString>
#include <QUrl>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

/// Managed desktop release availability and maintenance-tool launch (ADR-0072).
class DesktopUpdates : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(bool managed READ managed CONSTANT)
    Q_PROPERTY(bool checking READ checking NOTIFY changed)
    Q_PROPERTY(bool available READ available NOTIFY changed)
    Q_PROPERTY(QString availableVersion READ availableVersion NOTIFY changed)
    Q_PROPERTY(QVariantList availableChanges READ availableChanges NOTIFY changed)
    Q_PROPERTY(QString status READ status NOTIFY changed)

public:
    /// Use the installed maintenance tool and bundled distribution policy.
    explicit DesktopUpdates(QObject* parent = nullptr);
    /// Construct against an explicit installed identity and transport; the caller owns the parent.
    DesktopUpdates(QString version, QString maintenance, QList<QUrl> feeds, bool automatic,
                   QObject* parent = nullptr);
    /// Whether this is an installed, numbered native release with an executable maintenance tool.
    bool managed() const { return managed_; }
    /// Whether a bounded metadata request is in progress.
    bool checking() const { return checking_; }
    /// Whether the recorded available release is newer than the running release.
    bool available() const { return !available_version_.isEmpty(); }
    /// The validated available calendar identity, or an empty string.
    QString availableVersion() const { return available_version_; }
    /// The latest human-readable check or launch result.
    QVariantList availableChanges() const { return available_changes_; }
    QString status() const { return status_; }
    /// Check metadata independently of optional notification preferences; ignore overlapping requests.
    Q_INVOKABLE void checkNow(bool manual = false);
    /// Launch the fixed installed updater; call only after the existing unsaved-work guard succeeds.
    Q_INVOKABLE bool startUpdate();
    Q_INVOKABLE bool startMaintenance();
    /// Compare validated calendar versions numerically; invalid identities are never newer.
    Q_INVOKABLE bool newerVersion(const QString& candidate, const QString& previous) const;
    /// Bundled release notes through the running release, newest first; malformed history yields none.
    Q_INVOKABLE QVariantList releaseChanges() const;

signals:
    void changed();
    void checkFinished(bool manual);

private:
    void fetchNext();
    QNetworkAccessManager network_;
    QString version_;
    QString maintenance_;
    QList<QUrl> feeds_;
    qsizetype next_feed_ = 0;
    bool managed_ = false;
    bool checking_ = false;
    bool manual_ = false;
    QVariantList available_changes_;
    QString available_version_;
    QString status_;
};

/// Read validated notes through current, or all releases when current is empty; invalid input sets validity false.
QVariantList release_changes(const QByteArray& content, const QString& current, bool* valid = nullptr,
                             bool allow_preview = false);

}  // namespace edi_app
