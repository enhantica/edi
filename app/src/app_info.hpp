// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_APP_INFO_HPP
#define EDI_APP_APP_INFO_HPP

#include <QColor>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

// What the app says about itself — its name, version and links. The only source of the identity the user
// sees; the base's own fallback (gui-components ProjectConfig.js) is never shown.
class ApplicationInfo : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(QString name READ name CONSTANT)
    Q_PROPERTY(QString namePrefixForLogo READ namePrefixForLogo CONSTANT)
    Q_PROPERTY(QString nameSuffixForLogo READ nameSuffixForLogo CONSTANT)
    Q_PROPERTY(QString version READ version CONSTANT)
    Q_PROPERTY(QString releaseDate READ releaseDate CONSTANT)
    Q_PROPERTY(QString homepageUrl READ homepageUrl CONSTANT)
    Q_PROPERTY(QString docsUrl READ docsUrl CONSTANT)
    Q_PROPERTY(QString issuesUrl READ issuesUrl CONSTANT)
    Q_PROPERTY(QString contactUrl READ contactUrl CONSTANT)
    Q_PROPERTY(QString licenseUrl READ licenseUrl CONSTANT)
    Q_PROPERTY(QString appLicenseUrl READ appLicenseUrl CONSTANT)
    Q_PROPERTY(QString noticesUrl READ noticesUrl CONSTANT)
    Q_PROPERTY(QStringList componentNames READ componentNames CONSTANT)
    Q_PROPERTY(QStringList componentLicences READ componentLicences CONSTANT)
    Q_PROPERTY(QStringList componentUses READ componentUses CONSTANT)
    Q_PROPERTY(QString description READ description CONSTANT)
    Q_PROPERTY(QString copyrightHolder READ copyrightHolder CONSTANT)
    Q_PROPERTY(QString developerYearsFrom READ developerYearsFrom CONSTANT)
    Q_PROPERTY(QString developerYearsTo READ developerYearsTo CONSTANT)
    // The element symbols of the core's element table, H to Og: what an atom-type picker lists.
    Q_PROPERTY(QStringList elementSymbols READ elementSymbols CONSTANT)
    // The Develop preference's engine thread counts: whether this build can run fills on several threads
    // (the single-thread web build cannot), and the largest count it offers.
    Q_PROPERTY(bool engineThreadsSelectable READ engineThreadsSelectable CONSTANT)
    Q_PROPERTY(int engineThreadsMaximum READ engineThreadsMaximum CONSTANT)

   public:
    explicit ApplicationInfo(QObject* parent = nullptr) : QObject(parent) {}

    QString name() const { return QStringLiteral("EasyDiffraction"); }
    QString namePrefixForLogo() const { return QStringLiteral("easy"); }
    QString nameSuffixForLogo() const { return QStringLiteral("diffraction"); }
    // The demo mode's images are a regression pin compared across commits, so they show a fixed
    // identity instead of the build's version and date.
    static void useDemoIdentity();
    static bool demoIdentity();
    QString version() const;
    QString releaseDate() const;
    QString homepageUrl() const { return QStringLiteral("https://easydiffraction.org"); }
    QString docsUrl() const { return QStringLiteral("https://docs.easydiffraction.org/app/"); }
    QString issuesUrl() const { return QStringLiteral("https://github.com/enhantica/edi/issues"); }
    QString contactUrl() const { return QStringLiteral("https://easydiffraction.org/#contact"); }
    // The licence texts are bundled in the app's resources, so the About window shows them without a network:
    // the source code's (BSD 3-Clause), the distributed app's (GPL-3.0: it links Qt Graphs and Qt Quick 3D;
    // ADR-0015 §6), and the notices of every component the app links or bundles.
    QString licenseUrl() const { return QStringLiteral("qrc:/LICENSE"); }
    QString appLicenseUrl() const { return QStringLiteral("qrc:/app/DISTRIBUTION-LICENSE.md"); }
    QString noticesUrl() const { return QStringLiteral("qrc:/THIRD-PARTY-NOTICES"); }
    // The components the notices list, in their order: their names, licences and uses, index for index.
    QStringList componentNames() const { return componentColumn(0); }
    QStringList componentLicences() const { return componentColumn(1); }
    QStringList componentUses() const { return componentColumn(2); }
    // The text of a bundled licence resource (one of the URLs above); empty for any other URL.
    Q_INVOKABLE QString licenceText(const QString& url) const;
    // The diagnostics view's text (the owner, 2026-10-06): the platform and browser, the build flavour and why it
    // was chosen (web), threads, the Qt version and graphics backend, edi's and crysta's versions with the crysta
    // SDK commit, and the feature switches; one "name: value" line each, to read and to copy.
    Q_INVOKABLE QString diagnostics() const;
    // Puts `text` on the clipboard (the web build's needs the click that asks for it).
    Q_INVOKABLE void copyText(const QString& text) const;
    bool engineThreadsSelectable() const;
    // Twice the cores the platform reports, at least 16 and at most 64: a browser may report fewer cores
    // than the machine has (Brave reports 4 of an M2's 12), so a larger count can still be tried.
    int engineThreadsMaximum() const;
    // Sets the engine's thread count for every fill: 0 for Auto, else that many threads.
    Q_INVOKABLE void setEngineThreads(int count) const;
    // Where a link inside the bundled licence text at `from` leads, resolved against that text's own location
    // (the app notice's "../COPYING" is qrc:/COPYING): the URL when it is one of the bundled licence texts above,
    // empty for anything else, so a link opens only what licenceText reads.
    Q_INVOKABLE QString licenceLinkTarget(const QString& from, const QString& link) const;

   private:
    // One column of the notices' "Components" list: 0 the name, 1 the licence, 2 the use.
    static QStringList componentColumn(int column);

   public:
    QString description() const;
    // The holder of the copyright in edi's source (LICENSE), named in the About dialog.
    QString copyrightHolder() const { return QStringLiteral("Enhantica contributors"); }
    // The About dialog's copyright years, as easydiffractionbeta's (Gui/Globals/Configs.qml): from the
    // EasyDiffraction project's first year to the current release's.
    QString developerYearsFrom() const { return QStringLiteral("2019"); }
    QString developerYearsTo() const { return QStringLiteral("2026"); }
    // ADR-0017 §8, ADR-0022 §4: an element's colour from a type symbol — the core table's colour of
    // edi::element_of(typeSymbol) in `scheme` ("jmol" or "vesta", the structure view's) — or `fallback` for an
    // element the table does not have. The app holds no element colour of its own.
    QStringList elementSymbols() const;
    Q_INVOKABLE QColor elementColor(const QString& typeSymbol, const QColor& fallback,
                                    const QString& scheme = QStringLiteral("jmol")) const;
};

#endif  // EDI_APP_APP_INFO_HPP
