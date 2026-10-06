// SPDX-License-Identifier: BSD-3-Clause
#include "app_info.hpp"

#include "app_build_info.hpp"
#include "edi/structure_scene.hpp"

#include <QFile>
#include <QStringList>
#include <QUrl>

namespace {
bool g_demo_identity = false;

// The bundled resource behind a licence URL the About window offers; empty for any other URL.
QString bundled_resource(const QString& url) {
    for (const char* name : {"LICENSE", "COPYING", "THIRD-PARTY-NOTICES", "app/DISTRIBUTION-LICENSE.md"}) {
        if (url == QStringLiteral("qrc:/") + QLatin1String(name)) {
            return QStringLiteral(":/") + QLatin1String(name);
        }
    }
    return {};
}

QString read_resource(const QString& path) {
    QFile file(path);
    if (path.isEmpty() || !file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}
}  // namespace

void ApplicationInfo::useDemoIdentity() { g_demo_identity = true; }

bool ApplicationInfo::demoIdentity() { return g_demo_identity; }

QString ApplicationInfo::version() const {
    return g_demo_identity ? QStringLiteral("demo") : QStringLiteral(EDI_APP_VERSION);
}

QString ApplicationInfo::releaseDate() const {
    return g_demo_identity ? QStringLiteral("demo build") : QStringLiteral(EDI_APP_DATE);
}

QString ApplicationInfo::description() const {
    return tr("EasyDiffraction is a software for calculating diffraction patterns based on structural models and "
              "refining their parameters against experimental data.");
}

QString ApplicationInfo::licenceText(const QString& url) const { return read_resource(bundled_resource(url)); }

QString ApplicationInfo::licenceLinkTarget(const QString& from, const QString& link) const {
    const QString target = QUrl(from).resolved(QUrl(link)).toString();
    return bundled_resource(from).isEmpty() || bundled_resource(target).isEmpty() ? QString() : target;
}

// The notices' "Components" list: from its heading to the next, one "- name | licence: X | use" line each.
QStringList ApplicationInfo::componentColumn(int column) {
    QStringList values;
    bool inList = false;
    const QStringList lines = read_resource(QStringLiteral(":/THIRD-PARTY-NOTICES")).split(QLatin1Char('\n'));
    for (qsizetype i = 0; i < lines.size(); ++i) {
        const QString& line = lines[i];
        const bool heading = i + 1 < lines.size() && lines[i + 1].startsWith(QLatin1String("---"));
        if (heading) {
            if (inList) {
                break;
            }
            inList = line.trimmed() == QLatin1String("Components");
            continue;
        }
        const QStringList cells = line.split(QLatin1String(" | "));
        if (!inList || !line.startsWith(QLatin1String("- ")) || cells.size() != 3) {
            continue;
        }
        const QString cell = cells[column].trimmed();
        values.append(column == 0 ? cell.mid(2) : column == 1 ? QString(cell).remove(QLatin1String("licence: ")) : cell);
    }
    return values;
}

QColor ApplicationInfo::elementColor(const QString& typeSymbol, const QColor& fallback, const QString& scheme) const {
    const edi::ColorScheme colors = scheme == QLatin1String("vesta") ? edi::ColorScheme::Vesta : edi::ColorScheme::Jmol;
    const edi::ElementColor found = edi::element_color(edi::element_of(typeSymbol.toStdString()), colors);
    return found.known ? QColor(found.color.r, found.color.g, found.color.b) : fallback;
}
