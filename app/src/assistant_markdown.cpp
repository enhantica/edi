// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_markdown.hpp"

#include <QImage>
#include <QPainter>
#include <QQuickWindow>
#include <QTextImageFormat>
#include <QUuid>
#include <QEvent>
#include <QHash>
#include <limits>
#ifdef EDI_HAS_NATIVE_MATH
#include <jkqtmathtext/jkqtmathtext.h>
#endif
#include <QAbstractTextDocumentLayout>
#include <QSGSimpleRectNode>
#include "edi/assistant_limits.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <QFontMetricsF>
#include <QTextBlock>
#include <QTextList>
#include <QTextTable>
#include <QTextOption>
#include <vector>
#include <QTextCursor>
#include <QTextDocument>
#include <QTextFormat>
#include <QVariant>

namespace edi_app {
namespace {
constexpr int mathSourceProperty=QTextFormat::UserProperty+4056;
struct MathSpan { QString token,literal,formula;bool display=false; };
struct MathSource { QString markdown;std::vector<MathSpan> spans; };
bool escapedAt(QStringView text,qsizetype at) {
    qsizetype slashes=0;while(at>0 && text[--at]==u'\\')++slashes;return slashes%2;
}
MathSource captureMath(QStringView source) {
    MathSource result;const auto nonce=QUuid::createUuid().toString(QUuid::Id128);
    QChar fence;qsizetype fenceLength=0,inlineTicks=0;
    for(qsizetype i=0;i<source.size();) {
        const bool lineStart=i==0 || source[i-1]==u'\n';
        if(lineStart) {
            qsizetype first=i;while(first<source.size() && source[first]==u' ')++first;
            const auto end=source.indexOf(u'\n',i);const auto lineEnd=end<0?source.size():end+1;
            const auto marker=first<source.size()?source[first]:QChar{};
            qsizetype count=0;while(first+count<source.size() && source[first+count]==marker)++count;
            if(!inlineTicks && first-i<=3 && (marker==u'`' || marker==u'~') && count>=3) {
                if(fence.isNull()){fence=marker;fenceLength=count;}
                else if(fence==marker && count>=fenceLength && source.mid(first+count,lineEnd-first-count).trimmed().isEmpty()){fence=QChar{};fenceLength=0;}
                result.markdown+=source.mid(i,lineEnd-i);i=lineEnd;continue;
            }
            if(!fence.isNull() || (!inlineTicks && (first-i>=4 || marker==u'\t'))) {
                result.markdown+=source.mid(i,lineEnd-i);i=lineEnd;continue;
            }
        }
        if(source[i]==u'`' && !escapedAt(source,i)) {
            qsizetype count=1;while(i+count<source.size() && source[i+count]==u'`')++count;
            if(!inlineTicks)inlineTicks=count;else if(inlineTicks==count)inlineTicks=0;
            result.markdown+=source.mid(i,count);i+=count;continue;
        }
        if(inlineTicks || escapedAt(source,i)){result.markdown+=source[i++];continue;}
        qsizetype opening=0;QString closing;bool display=false;
        if(source[i]==u'\\' && i+1<source.size() && (source[i+1]==u'(' || source[i+1]==u'[')) {
            opening=2;display=source[i+1]==u'[';closing=display?QStringLiteral("\\]"):QStringLiteral("\\)");
        }else if(source[i]==u'$' && i+1<source.size()) {
            display=source[i+1]==u'$';opening=display?2:1;closing=display?QStringLiteral("$$"):QStringLiteral("$");
            if(!display && source[i+1].isSpace()){result.markdown+=source[i++];continue;}
        }
        if(!opening){result.markdown+=source[i++];continue;}
        qsizetype end=source.indexOf(closing,i+opening);
        while(end>=0 && (escapedAt(source,end) || (opening==1 && (source[end-1].isSpace() || (end+1<source.size() && source[end+1].isDigit())))))end=source.indexOf(closing,end+closing.size());
        if(end<0 && opening==1){result.markdown+=source[i++];continue;}
        const auto consumed=end<0?source.size()-i:end+closing.size()-i;
        const auto formula=end<0?QString():source.mid(i+opening,end-i-opening).toString();
        const auto token=QStringLiteral("EdiMath")+nonce+QString::number(result.spans.size());
        result.spans.push_back({token,source.mid(i,consumed).toString(),formula,display});
        if(display && !result.markdown.endsWith(u'\n'))result.markdown+='\n';
        result.markdown+=token;
        if(display)result.markdown+='\n';
        i+=consumed;
    }
    return result;
}
class PassiveDocument final : public QTextDocument {
 public:
    struct Picture {QImage image;qreal descent=0;};
    explicit PassiveDocument(QObject* parent) : QTextDocument(parent),nonce_(QUuid::createUuid().toString(QUuid::Id128)) {setUndoRedoEnabled(false);}
    void beginMath() {
        for(const auto& url:resources_)addResource(ImageResource,url,QVariant::fromValue(QImage{}));
        resources_.clear();nextPictures_.clear();newBytes_=0;
    }
    void endMath(){pictures_.swap(nextPictures_);nextPictures_.clear();}
    QUrl install(const QImage& image) {
        const QUrl url("edi-generated-math:"+nonce_+"/"+QString::number(resources_.size()));
        addResource(ImageResource,url,image);resources_.append(url);return url;
    }
    Picture picture(const QString& formula,const QFont& font,const QColor& color,qreal dpr) {
#ifdef EDI_HAS_NATIVE_MATH
        const auto key=font.toString()+QChar(0)+QString::number(color.rgba())+QChar(0)+QString::number(dpr,'g',16)+QChar(0)+formula;
        if(nextPictures_.contains(key))return nextPictures_.value(key);
        if(pictures_.contains(key)) {const auto result=pictures_.value(key);nextPictures_.insert(key,result);return result;}
        quint64 retained=newBytes_;for(auto it=pictures_.cbegin();it!=pictures_.cend();++it)retained+=static_cast<quint64>(it.value().image.sizeInBytes());
        constexpr auto capacity=edi::assistant::Limits::ui_history_bytes;
        JKQTMathText math;math.useXITS();
        // A pixel-sized body font is the original editor's source of scale.
        math.setFontSizePixels(font.pixelSize()>0?font.pixelSize():QFontMetricsF(font).height());math.setFontColor(color);
        if(!math.parse("$"+formula+"$"))return {};
        QImage probe(1,1,QImage::Format_ARGB32_Premultiplied);probe.setDevicePixelRatio(dpr);
        probe.setDotsPerMeterX(96*(10000/254));probe.setDotsPerMeterY(96*(10000/254));
        QPainter painter(&probe);double width=0,ascent=0,descent=0,strike=0;math.getSizeDetail(painter,width,ascent,descent,strike);painter.end();
        const auto pixelsWide=std::ceil(width+2)*dpr,pixelsHigh=std::ceil(ascent+descent+2)*dpr;
        if(!std::isfinite(pixelsWide) || !std::isfinite(pixelsHigh) || pixelsWide<=0 || pixelsHigh<=0 ||
            pixelsWide>std::numeric_limits<int>::max() || pixelsHigh>std::numeric_limits<int>::max() ||
            retained>capacity || pixelsWide*pixelsHigh*4>static_cast<double>(capacity-retained))return {};
        Picture result{math.drawIntoImage(false,Qt::transparent,1,dpr),descent+1};
        if(result.image.isNull())return {};
        newBytes_+=static_cast<quint64>(result.image.sizeInBytes());nextPictures_.insert(key,result);return result;
#else
        Q_UNUSED(formula);Q_UNUSED(font);Q_UNUSED(color);Q_UNUSED(dpr);return {};
#endif
    }
 protected:
    QVariant loadResource(int,const QUrl&) override {
        // Generated resources are inserted only after all authored images are stripped.
        // No URI prefix or resource-provider fallback authorizes a file/network load.
        return QVariant::fromValue(QImage{});
    }
 private:
    QString nonce_;QList<QUrl> resources_;
    QHash<QString,Picture> pictures_,nextPictures_;
    quint64 newBytes_=0;
};
}
AssistantMarkdown::AssistantMarkdown(QQuickItem* parent) : QQuickItem(parent) {
    setFlag(ItemHasContents, true);
    setAcceptedMouseButtons(Qt::NoButton);
    setZ(-1);
    connect(this,&QQuickItem::windowChanged,this,[this](QQuickWindow* next) {
        if(observed_window_)observed_window_->removeEventFilter(this);
        observed_window_=next;if(next)next->installEventFilter(this);
        ++presentation_revision_;render();
    });
}
bool AssistantMarkdown::eventFilter(QObject* object,QEvent* event) {
    if(object==observed_window_ && event->type()==QEvent::DevicePixelRatioChange) {++presentation_revision_;render();}
    return false;
}
void AssistantMarkdown::geometryChange(const QRectF& next, const QRectF& previous) {
    QQuickItem::geometryChange(next, previous);
    polish();
}
void AssistantMarkdown::updatePolish() {
    const QPointer<AssistantMarkdown> receiver(this);
    const QPointer<QTextDocument> document(document_);
    const auto revision = presentation_revision_;
    if (!document) { decorations_.clear(); update(); return; }
    if(markdown_ && math_text_width_!=document->textWidth()) {++presentation_revision_;render();return;}
    const auto current = [&] { return receiver && document && receiver->document_ == document && receiver->presentation_revision_ == revision; };
    try {
        std::size_t count = 0;
        QTextTable* previous = nullptr;
        const auto limit = edi::assistant::Limits::ui_history_bytes - sizeof(QSGNode);
        constexpr auto nodeBytes = sizeof(QSGSimpleRectNode) + 4*sizeof(QSGGeometry::Point2D);
        for (auto block = document->begin(); block.isValid(); block = block.next()) {
            auto* table = QTextCursor(block).currentTable();
            if (!table || table == previous) continue;
            previous = table;
            const auto rows = static_cast<std::size_t>(table->rows());
            if (rows > (limit/sizeof(Decoration)-4)/2 || count > limit/sizeof(Decoration)-(rows*2+4))
                throw std::length_error("Table presentation exceeds its existing UI capacity");
            count += rows*2+4;
        }
        const auto maximum = std::max(decoration_high_water_,count);
        if (maximum > limit/nodeBytes || count > (limit-maximum*nodeBytes)/sizeof(Decoration) ||
            decorations_.capacity() > (limit-maximum*nodeBytes-count*sizeof(Decoration))/sizeof(Decoration))
            throw std::length_error("Table presentation exceeds its existing UI capacity");
        std::vector<Decoration> next;
        next.reserve(count);
        const QPointer<QAbstractTextDocumentLayout> layout(document->documentLayout());
        if (!current() || !layout) return;
        previous = nullptr;
        for (auto block = document->begin(); block.isValid(); block = block.next()) {
            auto* table = QTextCursor(block).currentTable();
            if (!table || table == previous) continue;
            previous = table;
            const auto frame = layout->frameBoundingRect(table);
            if (!current() || !layout) return; // Native layout may synchronously publish document size.
            // Qt's table frame origin is the first cell's padded content
            // origin. Its percentage width already includes both cell edges.
            const auto inset = table->cellAt(0,0).format().toTableCellFormat().leftPadding();
            const auto rowLeft = frame.left() - inset;
            const auto headerRows = table->format().headerRowCount();
            qreal previousTop = 0, previousBottom = 0, tableTop = 0;
            int previousRow = -1;
            const auto appendRow = [&](int row, qreal top, qreal bottom) {
                if (bottom <= top) return;
                const auto shade=(row < headerRows || (row-headerRows)%2 == 1)?table_shade_color_:table_base_color_;
                if (shade.isValid())next.push_back({QRectF(rowLeft,top,frame.width(),bottom-top).intersected(boundingRect()),shade});
                if (table_border_color_.isValid() && row+1 < table->rows())
                    next.push_back({QRectF(rowLeft,bottom-0.5,frame.width(),0.5).intersected(boundingRect()),table_border_color_});
            };
            for (int row = 0; row < table->rows(); ++row) {
                qreal top = frame.bottom(), bottom = frame.top();
                for (int column = 0; column < table->columns(); ++column) {
                    const auto cell = table->cellAt(row,column);
                    if (cell.row() != row) continue;
                    const auto first = cell.firstCursorPosition().block();
                    const auto last = cell.lastCursorPosition().block();
                    const auto firstRect = layout->blockBoundingRect(first);
                    if (!current() || !layout) return;
                    const auto lastRect = layout->blockBoundingRect(last);
                    if (!current() || !layout) return;
                    const auto format = cell.format().toTableCellFormat();
                    top = std::min(top,firstRect.top()-format.topPadding());
                    bottom = std::max(bottom,lastRect.bottom()+format.bottomPadding());
                }
                if (bottom <= top) continue;
                // Native cell origins already include their padding. Adjacent
                // row origins are the shared boundaries, including Qt's border
                // rounding; block margins must not be charged a second time.
                if (previousRow >= 0) appendRow(previousRow,previousTop,top);
                else tableTop=top;
                previousRow = row; previousTop = top; previousBottom = bottom;
            }
            if (previousRow >= 0) {
                appendRow(previousRow,previousTop,previousBottom);
                if(table_border_color_.isValid()) {
                    constexpr qreal rule=0.5; // Retain the original chat table rule thickness.
                    const auto height=previousBottom-tableTop;
                    for(const auto& edge:{QRectF(rowLeft,tableTop,frame.width(),rule),
                        QRectF(rowLeft,previousBottom-rule,frame.width(),rule),
                        QRectF(rowLeft,tableTop,rule,height),QRectF(rowLeft+frame.width()-rule,tableTop,rule,height)})
                        next.push_back({edge.intersected(boundingRect()),table_border_color_});
                }
            }
        }
        if (!current() || !layout) return;
        decorations_.swap(next);
        decoration_high_water_ = maximum;
        update();
    } catch (...) {
        if (!current()) return;
        decorations_.clear(); update();
        // Preserve the complete original as literal text when decoration cannot be admitted.
        try { document->setPlainText(source_); } catch (...) {}
    }
}
QSGNode* AssistantMarkdown::updatePaintNode(QSGNode* old, UpdatePaintNodeData*) {
    auto* root = old;
    try {
        if (!root) root = new QSGNode;
        auto* node = root->firstChild();
        for (const auto& decoration : decorations_) {
            auto* rectangle = node ? static_cast<QSGSimpleRectNode*>(node) : new QSGSimpleRectNode;
            if (!node) root->appendChildNode(rectangle);
            rectangle->setRect(decoration.rect);
            rectangle->setColor(decoration.color);
            node = rectangle->nextSibling();
        }
        while (node) { auto* next = node->nextSibling(); root->removeChildNode(node); delete node; node = next; }
        return root;
    } catch (...) {
        // This callback owns the complete node tree, including any rectangles
        // attached before allocation failed. The original editor stays intact;
        // never access its GUI-thread document from the rendering callback.
        delete root;
        return nullptr;
    }
}
QQuickTextDocument* AssistantMarkdown::document() const { return target_; }
QString AssistantMarkdown::source() const { return source_; }
bool AssistantMarkdown::markdown() const { return markdown_; }
QColor AssistantMarkdown::textColor() const {return text_color_;}
void AssistantMarkdown::setTextColor(const QColor& color) {
    if(text_color_==color)return;text_color_=color;++presentation_revision_;render();
}
QString AssistantMarkdown::selectedSource(int start,int end) const {
    const QPointer<QTextDocument> document(document_);if(!document)return {};
    start=std::clamp(start,0,document->characterCount()-1);end=std::clamp(end,0,document->characterCount()-1);
    if(end<start)std::swap(start,end);
    if(start==0 && end==document->characterCount()-1)return source_;
    QString result;
    for(int i=start;i<end;++i) {
        QTextCursor cursor(document);cursor.setPosition(i);cursor.setPosition(i+1,QTextCursor::KeepAnchor);
        const auto format=cursor.charFormat();
        if(format.hasProperty(mathSourceProperty))result+=format.stringProperty(mathSourceProperty);
        else result+=cursor.selectedText().replace(QChar::ParagraphSeparator,u'\n');
    }
    return result;
}
QColor AssistantMarkdown::accentColor() const { return accent_color_; }
void AssistantMarkdown::setAccentColor(const QColor& color) {
    if (accent_color_ == color) return;
    accent_color_ = color;
    ++presentation_revision_;
    if (document_ && markdown_) {
        try { formatPresentation(); } catch (...) {}
    }
}
QFont AssistantMarkdown::bodyFont() const { return body_font_; }
QString AssistantMarkdown::monoFontFamily() const { return mono_font_family_; }
QColor AssistantMarkdown::tableBorderColor() const { return table_border_color_; }
QColor AssistantMarkdown::tableShadeColor() const { return table_shade_color_; }
QColor AssistantMarkdown::tableBaseColor() const { return table_base_color_; }
void AssistantMarkdown::setBodyFont(const QFont& font) {
    if (body_font_set_ && body_font_ == font) return;
    body_font_ = font; body_font_set_ = true;
    ++presentation_revision_;
    if (document_) {
        const QPointer<AssistantMarkdown> receiver(this);
        const QPointer<QTextDocument> document(document_);
        const auto revision = presentation_revision_;
        document->setDefaultFont(font);
        if (!receiver || !document || receiver->document_ != document || receiver->presentation_revision_ != revision) return;
        if (markdown_) render();
    }
}
void AssistantMarkdown::setMonoFontFamily(const QString& family) {
    if (mono_font_family_ == family) return;
    mono_font_family_ = family;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableBorderColor(const QColor& color) {
    if (table_border_color_ == color) return;
    table_border_color_ = color;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableBaseColor(const QColor& color) {
    if (table_base_color_ == color) return;
    table_base_color_ = color;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableShadeColor(const QColor& color) {
    if (table_shade_color_ == color) return;
    table_shade_color_ = color;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::formatPresentation() {
    const QPointer<AssistantMarkdown> receiver(this);
    const QPointer<QTextDocument> document(document_);
    const auto revision = presentation_revision_;
    if (!document) return;
    const auto current = [&] { return receiver && document && receiver->document_ == document && receiver->presentation_revision_ == revision; };
    auto option = document->defaultTextOption();
    option.setWrapMode(QTextOption::WrapAtWordBoundaryOrAnywhere);
    document->setDefaultTextOption(option);
        if (!current()) return;
    const auto body_font = document->defaultFont();
    const QFontMetricsF body_metrics(body_font);
    const qreal line = body_metrics.height();
    auto mono_font = body_font;
    // Both names come from actual bundled EA Fonts, never a platform fixed font.
    mono_font.setFamilies({mono_font_family_.isEmpty() ? body_font.family() : mono_font_family_});
    mono_font.setFixedPitch(true);
    const qreal mono_x = QFontMetricsF(mono_font).xHeight();
    const qreal scale = mono_x > 0 && body_metrics.xHeight() > 0 ? body_metrics.xHeight() / mono_x : 1;
    if (body_font.pixelSize() > 0) mono_font.setPixelSize(std::max(1, qRound(body_font.pixelSize() * scale)));
    else if (body_font.pointSizeF() > 0) mono_font.setPointSizeF(body_font.pointSizeF() * scale);
    document->setIndentWidth(line * 1.25);
        if (!current()) return;
    // QTextDocument retains the semantic list/code/table structure. Relax only
    // parsed no-wrap block presentation, never inject characters into content.
    std::vector<std::pair<int, int>> anchors, code;
    std::vector<QTextTable*> tables;
    for (auto block = document->begin(); block.isValid(); block = block.next()) {
        auto format = block.blockFormat();
        format.setNonBreakableLines(false);
        const bool listed = block.textList() != nullptr;
        format.setTopMargin(listed && block.previous().textList() == block.textList() ? 0 : line * 0.25);
        format.setBottomMargin(listed && block.next().textList() == block.textList() ? 0 : line * 0.4);
        QTextCursor cursor(block);
        cursor.setBlockFormat(format);
        if (!current()) return;
        if (auto* table = cursor.currentTable(); table && std::find(tables.begin(), tables.end(), table) == tables.end()) tables.push_back(table);
        for (auto it = block.begin(); !it.atEnd(); ++it) {
            const auto fragment = it.fragment();
            if (!fragment.isValid()) continue;
            if (fragment.charFormat().isAnchor()) anchors.emplace_back(fragment.position(), fragment.length());
            if (format.hasProperty(QTextFormat::BlockCodeLanguage) || fragment.charFormat().fontFixedPitch())
                code.emplace_back(fragment.position(), fragment.length());
        }
    }
    for (const auto& [position, length] : code) {
        QTextCursor cursor(document);
        cursor.setPosition(position); cursor.setPosition(position + length, QTextCursor::KeepAnchor);
        auto format = cursor.charFormat();
        format.setFontFamilies(mono_font.families()); format.setFontFixedPitch(true);
        format.clearProperty(QTextFormat::FontSizeAdjustment);
        if (mono_font.pixelSize() > 0) {
            format.clearProperty(QTextFormat::FontPointSize);
            format.setProperty(QTextFormat::FontPixelSize, mono_font.pixelSize());
        } else {
            format.clearProperty(QTextFormat::FontPixelSize); format.setFontPointSize(mono_font.pointSizeF());
        }
        cursor.setCharFormat(format);
        if (!current()) return;
    }
    // The original report uses horizontal rules and restrained row shading.
    // Reply tables add breathing room and keep every column left aligned.
    for (auto* table : tables) {
        auto format = table->format();
        // These tables come exclusively from setMarkdown(MarkdownNoHTML).
        // Markdown tables have one header row; Qt marks TH text bold but does
        // not populate QTextTableFormat::headerRowCount itself.
        format.setHeaderRowCount(1);
        format.setWidth(QTextLength(QTextLength::PercentageLength, 100));
        format.setCellSpacing(0); format.setCellPadding(0); format.setBorderCollapse(true);
        format.setBorder(0); format.setBorderStyle(QTextFrameFormat::BorderStyle_None);
        format.setTopMargin(line * 0.6); format.setBottomMargin(line * 0.6);
        if (table_border_color_.isValid()) format.setBorderBrush(table_border_color_);
        table->setFormat(format);
        if (!current()) return;
        for (int r = 0; r < table->rows(); ++r) for (int column = 0; column < table->columns(); ++column) {
            auto cell = table->cellAt(r, column);
            if (cell.row() != r || cell.column() != column) continue; // Keep parsed merged-cell semantics.
            auto cell_format = cell.format().toTableCellFormat();
            cell_format.setBorder(0); cell_format.setTopPadding(line * 0.3); cell_format.setBottomPadding(line * 0.3);
            cell_format.setLeftPadding(line * 0.5); cell_format.setRightPadding(line * 0.5);
            if (table_shade_color_.isValid() && (r < format.headerRowCount() || (r - format.headerRowCount()) % 2 == 1))
                cell_format.setBackground(table_shade_color_);
            else if(table_base_color_.isValid())cell_format.setBackground(table_base_color_);
            else cell_format.clearBackground();
            cell.setFormat(cell_format);
        if (!current()) return;
            // Qt imports Markdown's column alignment into each block. The
            // Assistant deliberately presents every header/value left aligned.
            const auto end = cell.lastCursorPosition().position();
            for (auto block = cell.firstCursorPosition().block(); block.isValid() && block.position() <= end; block = block.next()) {
                auto block_format = block.blockFormat();
                block_format.setAlignment(Qt::AlignLeft);
                // Cell padding alone owns the space above and below table text.
                block_format.setTopMargin(0); block_format.setBottomMargin(0);
                QTextCursor cursor(block); cursor.setBlockFormat(block_format);
                if (!current()) return;
            }
        }
    }
    polish();
    if (!accent_color_.isValid()) return;
    QTextCharFormat accent;
    accent.setForeground(accent_color_);
    for (const auto& [position, length] : anchors) {
        QTextCursor cursor(document);
        cursor.setPosition(position);
        cursor.setPosition(position + length, QTextCursor::KeepAnchor);
        cursor.mergeCharFormat(accent);
        if (!current()) return;
    }
}
void AssistantMarkdown::setDocument(QQuickTextDocument* target) {
    if (target_ == target) return;
    target_ = target;
    ++presentation_revision_;
    document_ = nullptr;
    decorations_.clear(); update();
    if (!target) return;
    // QQuickTextDocument retains no ownership. Parent the replacement to that
    // actual editor wrapper, so it outlives this binding helper and cannot dangle
    // if delegates are reused or the helper is destroyed before the editor.
    auto* replacement = new PassiveDocument(target);
    if (const auto* previous = target->textDocument()) {
        replacement->setDefaultFont(previous->defaultFont());
        replacement->setDefaultTextOption(previous->defaultTextOption());
        replacement->setDocumentMargin(previous->documentMargin());
        replacement->setTextWidth(previous->textWidth());
    }
    if (body_font_set_) replacement->setDefaultFont(body_font_);
    const QPointer<AssistantMarkdown> receiver(this);
    const QPointer<QQuickTextDocument> original(target);
    const auto revision = presentation_revision_;
    target->setTextDocument(replacement);
    if (!receiver || !original || receiver->target_ != original || receiver->presentation_revision_ != revision) return;
    document_ = replacement;
    connect(replacement, &QTextDocument::contentsChanged, this, [this,replacement] {
        if (document_ == replacement) polish();
    });
    const QPointer<QAbstractTextDocumentLayout> layout(replacement->documentLayout());
    if (!receiver || !original || receiver->target_ != original || receiver->document_ != replacement || receiver->presentation_revision_ != revision || !layout) return;
    connect(layout, &QAbstractTextDocumentLayout::update, this, [this,replacement](const QRectF&) {
        if (document_ == replacement) polish();
    });
    render();
}
void AssistantMarkdown::setSource(const QString& source) {
    if (source_ == source) return;
    source_ = source;
    ++presentation_revision_;
    render();
}
void AssistantMarkdown::setMarkdown(bool markdown) {
    if (markdown_ == markdown) return;
    markdown_ = markdown;
    ++presentation_revision_;
    render();
}
void AssistantMarkdown::render() noexcept {
    const QPointer<AssistantMarkdown> receiver(this);
    const QPointer<QTextDocument> document(document_);
    const auto revision = presentation_revision_;
    if (!document) return;
    const auto current = [&] { return receiver && document && receiver->document_ == document && receiver->presentation_revision_ == revision; };
    try {
        math_text_width_=document->textWidth();
        auto* passive=static_cast<PassiveDocument*>(document.data());passive->beginMath();
        if (!markdown_) { document->setPlainText(source_);passive->endMath(); return; }
        const auto captured=captureMath(source_);
        document->setMarkdown(captured.markdown, QTextDocument::MarkdownFeatures(QTextDocument::MarkdownDialectGitHub) | QTextDocument::MarkdownNoHTML);
        if (!current()) return;
        // Qt owns Markdown parsing. Replace only its parsed image objects with
        // literal alternative text; no URI is fetched or second HTML parse made.
        QTextCursor cursor(document);
        for (;;) {
            auto image = document->find(QString(QChar::ObjectReplacementCharacter), cursor);
            if (image.isNull()) break;
            cursor = image;
            if (!image.charFormat().isImageFormat()) continue;
            const auto alternative = image.charFormat().stringProperty(QTextFormat::ImageAltText);
            image.insertText(alternative, QTextCharFormat{});
            if (!current()) return;
            cursor = image;
        }
        const auto dpr=window()?window()->effectiveDevicePixelRatio():qreal(1);
        for(const auto& span:captured.spans) {
            auto slot=document->find(span.token);if(slot.isNull())continue;
            const auto picture=span.formula.isEmpty()?PassiveDocument::Picture{}:passive->picture(span.formula,document->defaultFont(),text_color_.isValid()?text_color_:QColor(Qt::black),dpr);
            if(!current())return;
            if(picture.image.isNull())slot.insertText(span.literal,QTextCharFormat{});
            else {
                const auto logical=picture.image.deviceIndependentSize();const auto available=std::max(qreal(1),document->textWidth());
                const auto scale=logical.width()>available?available/logical.width():qreal(1);
                QTextImageFormat image;image.merge(slot.charFormat());image.setName(passive->install(picture.image).toString());
                image.setWidth(logical.width()*scale);image.setHeight(logical.height()*scale);
                image.setProperty(mathSourceProperty,span.literal);image.setProperty(QTextFormat::ImageAltText,span.literal);
                image.setVerticalAlignment(QTextCharFormat::AlignBaseline);
                image.setBaselineOffset(-100*picture.descent*scale/std::max(qreal(1),QFontMetricsF(document->defaultFont()).height()));
                slot.insertImage(image);
                if(span.display){auto format=slot.blockFormat();format.setAlignment(Qt::AlignHCenter);slot.setBlockFormat(format);}
            }
            if(!current())return;
        }
        passive->endMath();
        formatPresentation();
    } catch (...) {
        if (!current()) return;
        // Preserve the complete original as literal text on presentation failure.
        try {
            auto* passive=static_cast<PassiveDocument*>(document.data());passive->beginMath();passive->endMath();
            document->setPlainText(source_);
        } catch (...) {}
    }
}
} // namespace edi_app
