// SPDX-License-Identifier: BSD-3-Clause
// Inspect actual Qt shaping; an installed system face is never evidence of coverage.
#include <QCoreApplication>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QFont>
#include <QFontDatabase>
#include <QGlyphRun>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRawFont>
#include <QTextLayout>
#include <QtQml/qqml.h>

class DisplayFontProof : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QString characters(const QString& family) const {
        const QString root = QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath())
                                 .absoluteFilePath("../../..");
        QFile file(root + "/data/display-glyphs.json");
        if (!file.open(QIODevice::ReadOnly)) return {};
        const auto document = QJsonDocument::fromJson(file.readAll());
        if (!document.isObject()) return {};
        QString text;
        for (const auto value : document.object().value("characters").toArray()) {
            const auto row = value.toObject();
            if (row.value("font").toString() == family)
                text += row.value("char").toString();
        }
        if (family == "PT Sans") {
            // Every digit ParameterItem's subscript formatter can generate.
            for (ushort code = 0x2080; code <= 0x2089; ++code) text += QChar(code);
        }
        return text;
    }
    Q_INVOKABLE QStringList failures(const QString& text, const QString& family, int weight, const QString& styleName, int expectedFaceWeight) const {
        QList<QByteArray> packaged;
        QDirIterator files(":/qt/qml/EasyApplication/Gui/Resources/Fonts", QDir::Files,
                           QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const QString path = files.next();
            if (!path.endsWith(".ttf") && !path.endsWith(".otf")) continue;
            QRawFont font(path, 16);
            if (font.isValid()) packaged.append(fingerprint(font));
        }
        QStringList errors;
        if (packaged.isEmpty()) return {"No packaged font resources were loaded"};
        QFont selected(family);
        selected.setPixelSize(16);
        selected.setWeight(static_cast<QFont::Weight>(weight));
        if (!styleName.isEmpty()) selected.setStyleName(styleName);
        for (const auto code : text.toUcs4()) {
            const char32_t point = static_cast<char32_t>(code);
            const QString character = QString::fromUcs4(&point, 1);
            QTextLayout layout(character, selected);
            layout.beginLayout();
            auto line = layout.createLine();
            if (line.isValid()) line.setLineWidth(1000);
            layout.endLayout();
            const auto runs = layout.glyphRuns();
            bool present = false;
            for (const auto& run : runs) {
                const auto font = run.rawFont();
                const auto indexes = run.glyphIndexes();
                if (!font.isValid() || !font.supportsCharacter(code) || indexes.isEmpty()
                    || indexes.contains(0) || !packaged.contains(fingerprint(font))
                    || faceWeight(font) != expectedFaceWeight) {
                    errors.append(QString("U+%1 selected %2 but shaped with unbundled/missing %3")
                                      .arg(code, 4, 16, QLatin1Char('0')).arg(family, font.familyName())
                                      + QString(" (physical weight %1, requested %2, style %3)")
                                            .arg(faceWeight(font)).arg(font.weight()).arg(font.styleName()));
                } else {
                    present = true;
                }
            }
            if (!present) errors.append(QString("U+%1 has no bundled rendering glyph")
                                           .arg(code, 4, 16, QLatin1Char('0')));
        }
        return errors;
    }
    Q_INVOKABLE QString unbundledFamily() const {
        // Plant an application-loaded face outside the packaged resource bytes.
        // Generic "monospace" may legitimately resolve to a bundled face on CI.
        QFile source(":/qt/qml/EasyApplication/Gui/Resources/Fonts/PT_Sans/PTSans-Regular.ttf");
        if (!source.open(QIODevice::ReadOnly)) return {};
        auto bytes = source.readAll();
        bytes.replace("PT Sans", "TZProbe");
        const char before[] = {'\0','P','\0','T','\0',' ','\0','S','\0','a','\0','n','\0','s'};
        const char after[] = {'\0','T','\0','Z','\0','P','\0','r','\0','o','\0','b','\0','e'};
        bytes.replace(QByteArray(before, sizeof(before)), QByteArray(after, sizeof(after)));
        const int id = QFontDatabase::addApplicationFontFromData(bytes);
        const auto names = QFontDatabase::applicationFontFamilies(id);
        return names.isEmpty() ? QString() : names.constFirst();
    }
private:
    static int faceWeight(const QRawFont& font) {
        const auto table = font.fontTable("OS/2");
        return table.size() < 6 ? -1 : static_cast<unsigned char>(table[4]) * 256
                                           + static_cast<unsigned char>(table[5]);
    }
    static QByteArray fingerprint(const QRawFont& font) {
        QByteArray result;
        // Compare physical tables; Qt can report the request's weight/style for a
        // correctly selected face. Include identity and outlines, not only cmap.
        for (const char* tag : {"cmap", "head", "maxp", "OS/2", "name", "glyf", "CFF ", "CFF2", "hmtx"}) {
            const auto table = font.fontTable(tag);
            result += QByteArray::number(table.size()) + ':' + table;
        }
        return result;
    }
};
static void register_display_fonts() {
    qmlRegisterType<DisplayFontProof>("DisplayFontTests", 1, 0, "DisplayFontProof");
}
Q_COREAPP_STARTUP_FUNCTION(register_display_fonts)
#include "test_display_fonts.moc"
