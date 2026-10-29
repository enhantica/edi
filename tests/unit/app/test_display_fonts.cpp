// SPDX-License-Identifier: BSD-3-Clause
// Inspect actual Qt shaping; an installed system face is never evidence of coverage.
#include "assistant_markdown.hpp"
#include <QCoreApplication>
#include <QDebug>
#include <QFontMetricsF>
#include <QFontInfo>
#include <QMap>
#include <QSizeF>
#include <QVector>
#include <QImage>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QTextBlock>
#include <QTextDocument>
#include <QtTest/qtestcase.h>
#include <algorithm>
#include <cmath>
#include <memory>
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
    Q_INVOKABLE QVariantMap assistantRendererFontUnits(QQuickItem* host, const QString& family) const {
        // Qt's two font units are alternatives: a pixel font reports an unset
        // point size. Never manufacture a point size from that sentinel.
        QTest::failOnWarning(QRegularExpression(QStringLiteral("^QFont::setPointSizeF:.*")));
        QStringList errors;
        QJsonArray facts;
        const auto require = [&](bool ok, const QString& message) {
            if (!ok) errors.append(message);
        };
        auto* engine = qmlEngine(this);
        require(engine && host && host->window(), QStringLiteral("Original Qt Quick test host/window must be exposed before renderer characterization"));
        if (!errors.isEmpty()) return {{"ok",false},{"error",errors.join('\n')}};
        const QString source = QString::fromUtf8(
            "# Heading\n\n**Bold** body and `inline-code`.\n\n"
            "```text\nfixed β 23\n```\n\n"
            "Inline $x^2$ remains native. Scaled $x \\circ y$ also remains native.\n\n| Name | Value |\n| --- | --- |\n| cell | $a+b$ |\n| sum | $\\sum_{i=1}^{3} a_i$ |\n");
        struct Geometry { QVector<QSizeF> images,ink; QVector<qreal> quantum; qreal bodyHeight=0; };
        QMap<QString,Geometry> previousByMode,pixelByZoom;
        for (const auto& mode : {QStringLiteral("default"),QStringLiteral("pixel"),QStringLiteral("point"),QStringLiteral("equivalent-point")}) {
            for (const qreal zoom : {qreal(0.7),qreal(1),qreal(1.25)}) {
                if (mode == "default" && zoom != 1) continue;
                QQmlComponent component(engine);
                component.setData("import QtQuick\nimport edi.app\nAssistantMessage { width: 640; kind: \"assistant\"; text: \"\" }\n",
                                  QUrl(QStringLiteral("qrc:/tests/OriginalAssistantFontUnits.qml")));
                std::unique_ptr<QObject> row(component.create());
                const auto stage = mode+QStringLiteral("/%1: ").arg(zoom);
                if (!row) { errors.append(stage+component.errorString()); continue; }
                auto* item = qobject_cast<QQuickItem*>(row.get());
                if (!item) { errors.append(stage+QStringLiteral("Original message is not a Qt Quick item")); continue; }
                item->setParentItem(host);
                const auto presentations = row->findChildren<edi_app::AssistantMarkdown*>();
                require(presentations.size()==1,stage+QStringLiteral("Exactly one original public renderer owns the ordinary reply"));
                if (presentations.size()!=1) continue;
                auto* renderer = presentations.front();
                auto* editor = renderer->editor();
                require(editor && editor->window()==host->window(),stage+QStringLiteral("Original TextEdit and renderer keep the current host window"));
                if (!editor) continue;
                if (mode != "default") {
                    QFont input(family);
                    if (mode == "pixel") input.setPixelSize(qRound(16*zoom));
                    else if (mode == "point") input.setPointSizeF(11.5*zoom);
                    else {
                        QFont originalPixel(family);originalPixel.setPixelSize(qRound(16*zoom));
                        // Independent Qt resolved font information supplies the
                        // equivalent unit, never the renderer adapter under test.
                        const QFontInfo pixelInfo(originalPixel);
                        require(pixelInfo.pointSizeF()>0,stage+QStringLiteral("Qt resolves the actual pixel input to an available positive point equivalent"));
                        if (pixelInfo.pointSizeF()<=0) continue;
                        input.setPointSizeF(pixelInfo.pointSizeF());
                        require(QFontInfo(input).pixelSize()==pixelInfo.pixelSize(),
                                stage+QStringLiteral("Qt itself confirms both inputs resolve to the same effective pixel size"));
                    }
                    require(editor->setProperty("font",input),stage+QStringLiteral("The normal public editor font property accepts this valid Qt font"));
                }
                const auto body = editor->property("font").value<QFont>();
                require(renderer->bodyFont()==body,stage+QStringLiteral("The renderer retains the original editor font binding"));
                if (mode=="pixel") require(body.pixelSize()>0 && body.pointSizeF()<0,stage+QStringLiteral("The pixel font sentinel premise is actually reached"));
                if (mode=="point" || mode=="equivalent-point") require(body.pointSizeF()>0 && body.pixelSize()<0,stage+QStringLiteral("The fractional point font premise is actually reached"));
                require(row->setProperty("text",source),stage+QStringLiteral("The ordinary assistant message accepts the immutable reply source"));
                auto* quick = renderer->document();
                auto* document = quick ? quick->textDocument() : nullptr;
                require(document,stage+QStringLiteral("The original renderer has the actual TextEdit document"));
                if (!document) continue;
                require(renderer->source()==source && renderer->selectedSource(0,document->characterCount()-1)==source,
                        stage+QStringLiteral("Font rendering never rewrites the original Markdown/TeX copy source"));
                // In pinned9e9 circ has only a Standard "o" entry, scale0.7.
                // getProps(Unicode) falls back to that Standard entry; the
                // current font's real ASCII-o glyph prevents fallback switching.
                const auto raw=QRawFont::fromFont(body);
                require(raw.isValid() && raw.supportsCharacter('o'),
                        stage+QStringLiteral("The actual source face supplies pinned circ's Standard o glyph, establishing its non-unit symbol-scaling premise"));
                const QStringList expectedFormula{QStringLiteral("$x^2$"),QStringLiteral("$x \\circ y$"),
                    QStringLiteral("$a+b$"),QStringLiteral("$\\sum_{i=1}^{3} a_i$")};
                Geometry geometry;QJsonArray imageFacts;
                int images=0,code=0,headings=0;quint64 bytes=0;bool bold=false;
                for (auto block=document->begin();block.isValid();block=block.next()) {
                    if (block.blockFormat().headingLevel()>0) ++headings;
                    for (auto it=block.begin();!it.atEnd();++it) {
                        const auto fragment=it.fragment();if (!fragment.isValid()) continue;
                        const auto format=fragment.charFormat();
                        if (fragment.text().contains("Bold")) bold=bold || format.font().bold();
                        if (fragment.text().contains("inline-code") || fragment.text().contains(QString::fromUtf8("fixed β 23"))) {
                            ++code;
                            const auto font=format.font().resolve(document->defaultFont());
                            const auto height=QFontMetricsF(font).height();
                            require(font.fixedPitch() && std::isfinite(height) && height>0,
                                    stage+QStringLiteral("Actual inline/fenced code has a valid positive fixed-pitch Qt font"));
                            require(body.pixelSize()>0 ? font.pixelSize()>0 : font.pointSizeF()>0,
                                    stage+QStringLiteral("Code respects the original positive pixel/point unit instead of an unset opposite-unit sentinel"));
                        }
                        if (!format.isImageFormat()) continue;
                        ++images;
                        require(images<=expectedFormula.size() && renderer->selectedSource(fragment.position(),fragment.position()+fragment.length())==expectedFormula.value(images-1),
                                stage+QStringLiteral("Each measured native image corresponds to the same immutable original formula occurrence"));
                        const auto image=qvariant_cast<QImage>(document->resource(QTextDocument::ImageResource,QUrl(format.toImageFormat().name())));
                        require(!image.isNull() && image.width()>0 && image.height()>0,
                                stage+QStringLiteral("Both original formula occurrences have available native image resources"));
                        bytes+=static_cast<quint64>(image.sizeInBytes());
                        const auto dpr=image.devicePixelRatio();
                        require(std::isfinite(dpr) && dpr>0,stage+QStringLiteral("The real formula resource has a positive finite device-pixel ratio"));
                        const QSizeF logical(format.toImageFormat().width(),format.toImageFormat().height());
                        require(std::isfinite(logical.width()) && std::isfinite(logical.height()) && logical.width()>0 && logical.height()>0,
                                stage+QStringLiteral("Actual native document geometry is finite, positive and uses logical units"));
                        require(logical==image.deviceIndependentSize(),stage+QStringLiteral("The original QTextImageFormat consumes the actual resource in its device-independent units"));
                        geometry.images.append(logical);geometry.quantum.append(dpr>0 ? 1/dpr : 0);
                        // The resource canvas includes transparent padding for
                        // Qt Quick's baseline. Equivalence/scale concern actual
                        // painted glyphs, not that independent padding policy.
                        const bool scanBounded=image.sizeInBytes()>0 && image.sizeInBytes()<=2097152;
                        require(scanBounded,stage+QStringLiteral("The original small formula's actual resource fits the independent capacity before an ink scan"));
                        QRect ink;
                        if(scanBounded)for(int y=0;y<image.height();++y)for(int x=0;x<image.width();++x)
                            if(image.pixelColor(x,y).alpha()!=0)ink=ink.united(QRect(x,y,1,1));
                        const bool inkAvailable=!ink.isEmpty() && std::isfinite(dpr) && dpr>0;
                        require(inkAvailable,stage+QStringLiteral("The actual native formula contains nontransparent painted glyphs"));
                        if(inkAvailable)geometry.ink.append(QSizeF(ink.width()/dpr,ink.height()/dpr));
                        imageFacts.append(QJsonObject{{"source",expectedFormula.value(images-1)},{"width",logical.width()},
                            {"height",logical.height()},{"resource_dpr",dpr},{"pixel_rounding_quantum",dpr>0 ? 1/dpr : 0},
                            {"ink_available",inkAvailable},{"ink_pixels",QJsonArray{ink.x(),ink.y(),ink.width(),ink.height()}}});
                    }
                }
                require(images==4 && code>=2 && headings==1 && bold,
                        stage+QStringLiteral("Font-unit changes preserve both original formulas plus circ/sum, inline/fenced code, heading and independent bold text"));
                require(bytes>0 && bytes<=2097152,
                        stage+QStringLiteral("Small ordinary formulas retain the original independently anchored two-MiB resource capacity"));
                const QFontMetricsF metrics(body);
                require(std::isfinite(metrics.height()) && metrics.height()>0,stage+QStringLiteral("The actual source font resolves to finite positive Qt metrics"));
                geometry.bodyHeight=metrics.height();
                require(geometry.ink.size()==geometry.images.size(),stage+QStringLiteral("Every original native resource supplies its own measured ink geometry, never a fabricated absent-image default"));
                if (previousByMode.contains(mode)) {
                    const auto& previous=previousByMode[mode];
                    require(geometry.bodyHeight>previous.bodyHeight,stage+QStringLiteral("The chosen real body-size inputs genuinely have increasing resolved Qt metrics"));
                    require(geometry.images.size()==previous.images.size(),stage+QStringLiteral("Font comparison keeps the complete same original formula inventory"));
                    require(geometry.ink.size()==previous.ink.size(),stage+QStringLiteral("Font comparison retains complete original painted formula membership"));
                    for (qsizetype i=0;i<std::min(geometry.ink.size(),previous.ink.size());++i) {
                        // One physical pixel per independent raster edge; no
                        // semantic relationship is imposed on baseline padding.
                        const auto rounding=std::max(geometry.quantum[i],previous.quantum[i]);
                        require(geometry.ink[i].width()>previous.ink[i].width()+rounding &&
                                geometry.ink[i].height()+rounding>=previous.ink[i].height(),
                                stage+QStringLiteral("Every original native formula responds meaningfully to actual body-size growth; a universal fixed positive math font cannot pass"));
                    }
                }
                previousByMode[mode]=geometry;
                const auto key=QString::number(zoom,'g',16);
                if (mode=="pixel") pixelByZoom[key]=geometry;
                if (mode=="equivalent-point") {
                    require(pixelByZoom.contains(key),stage+QStringLiteral("The actual equivalent pixel render is retained before comparing point input"));
                    if (pixelByZoom.contains(key)) {
                        const auto& pixel=pixelByZoom[key];
                        require(pixel.images.size()==geometry.images.size(),stage+QStringLiteral("Equivalent units retain all original formula occurrences"));
                        require(pixel.ink.size()==geometry.ink.size(),stage+QStringLiteral("Equivalent units retain all actual original painted formula occurrences"));
                        for (qsizetype i=0;i<std::min(pixel.ink.size(),geometry.ink.size());++i) {
                            const auto rounding=2*std::max(pixel.quantum[i],geometry.quantum[i]);
                            require(std::abs(pixel.ink[i].width()-geometry.ink[i].width())<=rounding &&
                                    std::abs(pixel.ink[i].height()-geometry.ink[i].height())<=rounding,
                                    stage+QStringLiteral("Qt-equivalent point/pixel fonts preserve actual painted native dimensions within two independent one-physical-pixel raster roundings"));
                        }
                    }
                }
                const QJsonObject fact{{"mode",mode},{"zoom",zoom},{"body_pixel_size",body.pixelSize()},
                    {"body_point_size",body.pointSizeF()},{"height",metrics.height()},{"formula_images",images},
                    {"resource_bytes",static_cast<qint64>(bytes)},{"same_window",editor->window()==host->window()},
                    {"image_geometry",imageFacts},{"circ_source_face_has_o",raw.isValid() && raw.supportsCharacter('o')},
                    {"document_plain_text",document->toPlainText()},
                    {"document_text_width",document->textWidth()},{"editor_width",editor->width()},{"editor_height",editor->height()},
                    {"row_width",item->width()},{"row_height",item->height()},
                    {"observation_stage","synchronous original font/text setters before a new-row frame/polish qualification"}};
                facts.append(fact);
                qInfo().noquote()<<"OriginalAssistantFontUnits"<<QJsonDocument(fact).toJson(QJsonDocument::Compact);
            }
        }
        return {{"ok",errors.isEmpty()},{"error",errors.join('\n')},{"facts",facts.toVariantList()}};
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
