// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QAbstractListModel>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

/// The online sources a Load ▸ From web… popup can search (ADR-0068): the Preferences table rows. Three are built
/// in (COD and EasyDiffraction's collection on GitHub and its mirror); the user adds, edits, disables or removes
/// others, and the table persists in the app's settings.
///
/// Tests and demos point a source at local files instead of the network: `--online-source <id>=<url>` on the
/// command line (repeatable) or `EDI_ONLINE_SOURCES=<id>=<url>;<id>=<url>` in the environment, where the URL is
/// typically `file:///…` to a folder holding `index.json` and the files it names. An override lasts for the run
/// and is never stored.
class OnlineSourcesModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the session")
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    enum Role { IdRole = Qt::UserRole + 1, NameRole, UrlRole, KindsRole, BuiltinRole, EnabledRole, OverriddenRole };
    Q_ENUM(Role)

    struct Source {
        QString id, name, url;
        QStringList kinds;
        bool builtin = false;
        bool enabled = true;
        QString override;  ///< the URL from the command line or environment, empty when none
    };

    explicit OnlineSourcesModel(QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = {}) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    /// The enabled sources offering `kind` (structure, experiment or data): a list of {id, name}.
    Q_INVOKABLE QVariantList sourcesFor(const QString& kind) const;
    /// The URL in force for a source, its override first; empty for an unknown id.
    Q_INVOKABLE QString urlOf(const QString& id) const;
    Q_INVOKABLE QString nameOf(const QString& id) const;
    Q_INVOKABLE QStringList kindsOf(const QString& id) const;
    /// Whether a source is COD, searched through its query service rather than an index file.
    Q_INVOKABLE bool isCod(const QString& id) const;

    /// Add a source to edit; its id is made from the name.
    Q_INVOKABLE void add();
    Q_INVOKABLE void remove(const QString& id);
    Q_INVOKABLE void setEnabled(const QString& id, bool enabled);
    Q_INVOKABLE void setName(const QString& id, const QString& name);
    Q_INVOKABLE void setUrl(const QString& id, const QString& url);
    Q_INVOKABLE void setKinds(const QString& id, const QStringList& kinds);

    const QList<Source>& sources() const { return sources_; }

signals:
    void countChanged();
    void sourcesChanged();

private:
    int indexOf(const QString& id) const;
    void load();
    void store() const;
    void applyOverrides();
    void changed(int row);

    QList<Source> sources_;
};

}  // namespace edi_app
