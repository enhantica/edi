// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_markdown.hpp"

#include <QImage>
#include <QGuiApplication>
#include <QClipboard>
#include <QMimeData>
#include <QTextDocumentFragment>
#include <QPainter>
#include <QQuickWindow>
#include <QScopeGuard>
#include <QTextImageFormat>
#include <QUuid>
#include <QEvent>
#include <QHash>
#include <limits>
#include <memory>
#ifdef EDI_HAS_NATIVE_MATH
#include <jkqtmathtext/jkqtmathtext.h>
#include <jkqtmathtext/jkqtmathtexttools.h>
#include <mutex>
#endif
#include <QAbstractTextDocumentLayout>
#include <QSGSimpleRectNode>
#include "edi/assistant_limits.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <QFontMetricsF>
#include <QFontInfo>
#include <optional>
#include <utility>
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
// Only the image format font changes. The native formula image and body font
// retain their original sizes; Qt Quick uses this format font's actual descent.
struct MathPlacementFont { QFont font; qreal descent=0; };
std::optional<MathPlacementFont> mathPlacementFont(const QFont& original,qreal requiredDescent) {
    if(!std::isfinite(requiredDescent) || requiredDescent<0)return std::nullopt;
    // Qt 6.11.2 documents an unsigned-16-bit pixel-size domain. Its
    // FreeType path also computes pixelSize * 64 * stretch in signed int.
    constexpr int qtPixelLimit=std::numeric_limits<quint16>::max();
    const auto pixelLimit=std::min(qtPixelLimit,std::numeric_limits<int>::max()/64/std::max(100,original.stretch()));
    if(pixelLimit<=0)return std::nullopt;
    auto pixels=original.pixelSize();
    if(pixels==-1) {
        // fontDpi reads metadata without resolving an engine. Bound Qt's own
        // point-size conversion BEFORE QFontInfo can request native metrics.
        const auto points=original.pointSizeF(),dpi=QFontMetricsF(original).fontDpi();
        if(!std::isfinite(points) || points<=0 || !std::isfinite(dpi) || dpi<=0)return std::nullopt;
        const auto requested=points*dpi/72;
        if(!std::isfinite(requested) || requested<0 || requested>pixelLimit+1)return std::nullopt;
        const auto rounded=std::floor(requested*100+0.5)/100;
        if(rounded<0.5 || rounded>=pixelLimit+0.5)return std::nullopt;
        pixels=QFontInfo(original).pixelSize();
    }
    if(pixels<=0 || pixels>pixelLimit)return std::nullopt;
    auto measure=[&](int size)->std::optional<MathPlacementFont> {
        if(size<=0 || size>pixelLimit)return std::nullopt;
        auto font=original;font.setPixelSize(size);
        const auto descent=QFontMetricsF(font).descent();
        if(!std::isfinite(descent) || descent<=0)return std::nullopt;
        return MathPlacementFont{font,descent};
    };
    auto candidate=measure(pixels);
    if(!candidate)return std::nullopt;
    if(candidate->descent>=requiredDescent)return candidate;
    int lower=pixels,upper=pixels;
    std::optional<MathPlacementFont> covering;
    // Bracket within the supported API/engine domain, before native metric
    // calls. No proportional metric estimate or out-of-domain clamp is a proof.
    for(int step=0;step<std::numeric_limits<quint16>::digits;++step) {
        const auto next=upper>pixelLimit/2?pixelLimit:upper*2;
        if(next<=upper)break;
        upper=next;candidate=measure(upper);
        if(!candidate)return std::nullopt;
        if(candidate->descent>=requiredDescent){covering=std::move(candidate);break;}
        lower=upper;
    }
    if(!covering)return std::nullopt;
    // Keep an actually measured covering candidate at every step. Correctness
    // does not assume font metrics are proportional or globally monotonic.
    for(int step=0;step<std::numeric_limits<quint16>::digits && upper-lower>1;++step) {
        const auto middle=lower+(upper-lower)/2;
        candidate=measure(middle);
        if(candidate && candidate->descent>=requiredDescent){upper=middle;covering=std::move(candidate);}
        else lower=middle;
    }
    return covering;
}
struct MathSpan { QString token,literal,formula;bool display=false; };
struct MathSource { QString markdown;std::vector<MathSpan> spans; };
bool escapedAt(QStringView text,qsizetype at) {
    qsizetype slashes=0;while(at>0 && text[--at]==u'\\')++slashes;return slashes%2;
}
MathSource captureMath(QStringView source) {
    MathSource result;const auto nonce=QUuid::createUuid().toString(QUuid::Id128);
    QChar fence;qsizetype fenceLength=0;
    for(qsizetype i=0;i<source.size();) {
        const bool lineStart=i==0 || source[i-1]==u'\n';
        if(lineStart) {
            qsizetype first=i;while(first<source.size() && source[first]==u' ')++first;
            const auto end=source.indexOf(u'\n',i);const auto lineEnd=end<0?source.size():end+1;
            const auto marker=first<source.size()?source[first]:QChar{};
            qsizetype count=0;while(first+count<source.size() && source[first+count]==marker)++count;
            if(first-i<=3 && (marker==u'`' || marker==u'~') && count>=3) {
                if(fence.isNull()){fence=marker;fenceLength=count;}
                else if(fence==marker && count>=fenceLength && source.mid(first+count,lineEnd-first-count).trimmed().isEmpty()){fence=QChar{};fenceLength=0;}
                result.markdown+=source.mid(i,lineEnd-i);i=lineEnd;continue;
            }
            if(!fence.isNull() || (first-i>=4 || marker==u'\t')) {
                result.markdown+=source.mid(i,lineEnd-i);i=lineEnd;continue;
            }
        }
        // Reference identities must reach Qt unchanged at EVERY occurrence:
        // full/collapsed/shortcut references and image labels use the same rule.
        // Leave bracket labels literal rather than inventing per-occurrence IDs.
        if(source[i]==u'[' && !escapedAt(source,i)) {
            qsizetype end=i+1;int depth=1;
            for(;end<source.size();++end) {
                if(escapedAt(source,end))continue;
                if(source[end]==u'[')++depth;
                else if(source[end]==u']' && --depth==0)break;
            }
            if(end<source.size()) {result.markdown+=source.mid(i,end-i);i=end;continue;}
        }
        // Keep actual inline link/image destinations untouched. Qt still parses
        // their escapes, nesting and optional titles from the original bytes.
        if(source[i]==u']' && !escapedAt(source,i) && i+1<source.size() && source[i+1]==u'(') {
            qsizetype end=i+2;int depth=1;QChar quote;
            for(;end<source.size();++end) {
                if(escapedAt(source,end))continue;
                if(!quote.isNull()){if(source[end]==quote)quote=QChar{};continue;}
                if(end==i+2 && source[end]==u'<'){quote=u'>';continue;}
                if((source[end]==u'"' || source[end]==u'\'') && end>i+2 && source[end-1].isSpace()){quote=source[end];continue;}
                if(source[end]==u'(')++depth;
                if(source[end]==u')'){if(--depth==0){++end;break;}}
            }
            result.markdown+=source.mid(i,end-i);i=end;continue;
        }
        if(source[i]==u']' && !escapedAt(source,i) && i+1<source.size() && source[i+1]==u':') {
            const auto end=source.indexOf(u'\n',i);const auto lineEnd=end<0?source.size():end+1;
            result.markdown+=source.mid(i,lineEnd-i);i=lineEnd;continue;
        }
        if(source[i]==u'`' && !escapedAt(source,i)) {
            qsizetype count=1;while(i+count<source.size() && source[i+count]==u'`')++count;
            // An unmatched opener is literal, not ownership of every later paragraph.
            qsizetype close=i+count;
            for(;close<source.size();) {
                if(source[close]==u'\n') {auto next=close+1;while(next<source.size() && (source[next]==u' ' || source[next]==u'\t'))++next;
                    if(next==source.size() || source[next]==u'\n')break;
                }
                if(source[close]!=u'`'){++close;continue;}
                qsizetype run=1;while(close+run<source.size() && source[close+run]==u'`')++run;
                if(run==count)break;close+=run;
            }
            if(close<source.size() && source[close]==u'`') {
                result.markdown+=source.mid(i,close+count-i);i=close+count;continue;
            }
            result.markdown+=source.mid(i,count);i+=count;continue;
        }
        if(escapedAt(source,i)){result.markdown+=source[i++];continue;}
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
        qsizetype unfinishedEnd=source.size();
        if(end<0)for(auto newline=source.indexOf(u'\n',i);newline>=0;newline=source.indexOf(u'\n',newline+1)) {
            auto next=newline+1;while(next<source.size() && (source[next]==u' ' || source[next]==u'\t'))++next;
            if(next==source.size() || source[next]==u'\n'){unfinishedEnd=newline;break;}
        }
        const auto consumed=end<0?unfinishedEnd-i:end+closing.size()-i;
        const auto formula=end<0?QString():source.mid(i+opening,end-i-opening).toString();
        const auto token=QStringLiteral("EdiMath")+nonce+QString::number(result.spans.size());
        result.spans.push_back({token,source.mid(i,consumed).toString(),formula,display});
        result.markdown+=token;
        i+=consumed;
    }
    return result;
}
// This is a conservative parser-stack eligibility boundary, not a TeX parser
// or a limit on messages/work. Each recursive grammar entrance consumes a brace,
// instruction, script marker, bracket or math delimiter in the pinned parser.
// Count all such tokens (even escaped ones) before native parse/tree/layout.
// Large or structurally costly expressions remain complete literal source.
bool nativeMathEligible(QStringView formula) {
    constexpr qsizetype maxPresentationUnits=4096, maxRecursiveSyntax=64;
    if(formula.size()>maxPresentationUnits)return false;
    qsizetype syntax=0;
    for(const auto c:formula)if(c==u'\\' || c==u'{' || c==u'}' || c==u'[' || c==u']' || c==u'^' || c==u'_' || c==u'$')
        if(++syntax>maxRecursiveSyntax)return false;
    return true;
}
QString restoreMathTokens(QString value,const MathSource& captured) {
    for(const auto& span:captured.spans)value.replace(span.token,span.literal);
    return value;
}
#ifdef EDI_HAS_NATIVE_MATH
class NativeMathText final : public JKQTMathText {
    static QObject* initializeBundledFallback() {
        // The upstream constructor estimates every font, including Fraktur,
        // before useXITS(). Avoid an unavailable generic-family lookup there.
        auto family=JKQTMathTextFontSpecifier::getXITSFamilies().mathFontName();
        // Its first lookup may register bundled fonts after taking its family
        // snapshot. Re-read only that initially empty snapshot before construction.
        if(family.isEmpty())family=JKQTMathTextFontSpecifier::getXITSFamilies().mathFontName();
        const std::lock_guard<std::mutex> lock(s_mutex);
        if(!family.isEmpty() && init_fracturFont==QStringLiteral("fraktur"))init_fracturFont=family;
        return nullptr;
    }
 public:
    NativeMathText():JKQTMathText(initializeBundledFallback()){}
};
#endif
class PassiveDocument final : public QTextDocument {
 public:
    struct Picture {QImage image;qreal descent=0;};
    explicit PassiveDocument(QObject* parent) : QTextDocument(parent),nonce_(QUuid::createUuid().toString(QUuid::Id128)) {setUndoRedoEnabled(false);}
    void beginMath() {
        for(const auto& url:resources_)addResource(ImageResource,url,QVariant::fromValue(QImage{}));
        resources_.clear();nextPictures_.clear();newBytes_=0;resourceBytes_=0;
    }
    void endMath(){pictures_.swap(nextPictures_);nextPictures_.clear();}
    QUrl install(const QImage& image) {
        const auto bytes=static_cast<quint64>(image.sizeInBytes());
        if(image.isNull() || bytes==0 || bytes>edi::assistant::Limits::ui_history_bytes-resourceBytes_)return {};
        const QUrl url("edi-generated-math:"+nonce_+"/"+QString::number(resources_.size()));
        // Track/charge before Qt installation: even a failed optional install
        // remains bounded and its exact resource is retired on the next render.
        resources_.append(url);resourceBytes_+=bytes;
        addResource(ImageResource,url,image);return url;
    }
    Picture picture(const QString& formula,const QFont& font,const QColor& color,qreal dpr) {
#ifdef EDI_HAS_NATIVE_MATH
        if(!nativeMathEligible(formula))return {};
        const auto key=font.toString()+QChar(0)+QString::number(color.rgba())+QChar(0)+QString::number(dpr,'g',16)+QChar(0)+formula;
        if(nextPictures_.contains(key))return nextPictures_.value(key);
        if(pictures_.contains(key)) {const auto result=pictures_.value(key);nextPictures_.insert(key,result);return result;}
        quint64 retained=newBytes_;for(auto it=pictures_.cbegin();it!=pictures_.cend();++it)retained+=static_cast<quint64>(it.value().image.sizeInBytes());
        constexpr auto capacity=edi::assistant::Limits::ui_history_bytes;
        QImage probe(1,1,QImage::Format_ARGB32_Premultiplied);probe.setDevicePixelRatio(dpr);
        probe.setDotsPerMeterX(96*(10000/254));probe.setDotsPerMeterY(96*(10000/254));
        // The pinned symbol scaler uses QFont::pointSizeF(), even for fonts
        // requested in pixels. Supply equivalent native points on THIS device,
        // never the pixel font's -1 point-size sentinel or a guessed base size.
        qreal points=font.pointSizeF();
        if(!std::isfinite(points) || points<=0) {
            const qreal pixels=font.pixelSize()>0?font.pixelSize():QFontMetricsF(font,&probe).height();
            const qreal dpi=probe.logicalDpiY();
            if(!std::isfinite(pixels) || pixels<=0 || !std::isfinite(dpi) || dpi<=0)return {};
            points=pixels*72.0/dpi; // Typographic points per inch; preserve the original logical pixel size.
        }
        if(!std::isfinite(points) || points<=0)return {};
        NativeMathText math;math.useXITS(); // Genuine mathematical-symbol fallback.
        math.useAnyUnicode(font.family(),font.family());
        math.setFontOption(JKQTMathText::BaseFontBold,font.bold());
        math.setFontOption(JKQTMathText::BaseFontItalic,font.italic());
        math.setFontPointSize(points);math.setFontColor(color);
        if(!math.parse("$"+formula+"$") || math.hadErrors() || !math.getErrorList().isEmpty())return {};
        QPainter painter(&probe);double width=0,ascent=0,descent=0,strike=0;math.getSizeDetail(painter,width,ascent,descent,strike);painter.end();
        const auto pixelsWide=std::ceil(width+2)*dpr,pixelsHigh=std::ceil(ascent+descent+2)*dpr;
        if(!std::isfinite(pixelsWide) || !std::isfinite(pixelsHigh) || pixelsWide<=0 || pixelsHigh<=0 ||
            pixelsWide>std::numeric_limits<int>::max() || pixelsHigh>std::numeric_limits<int>::max() ||
            retained>capacity || pixelsWide*pixelsHigh*4>static_cast<double>(capacity-retained))return {};
        Picture result;
        result.image=QImage(QSize(static_cast<int>(std::ceil(pixelsWide)),static_cast<int>(std::ceil(pixelsHigh))),QImage::Format_ARGB32_Premultiplied);
        if(result.image.isNull())return {};
        result.image.setDevicePixelRatio(dpr);result.image.setDotsPerMeterX(probe.dotsPerMeterX());result.image.setDotsPerMeterY(probe.dotsPerMeterY());
        result.image.fill(Qt::transparent);
        QPainter output(&result.image);output.setRenderHints(QPainter::Antialiasing|QPainter::TextAntialiasing|QPainter::SmoothPixmapTransform);
        math.draw(output,1,ascent+1,false);output.end(); // Actual measured native baseline, no centering roundoff.
        if(math.hadErrors() || !math.getErrorList().isEmpty())return {};
        result.descent=result.image.deviceIndependentSize().height()-(ascent+1);
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
    quint64 newBytes_=0,resourceBytes_=0;
};
}
AssistantMarkdown::AssistantMarkdown(QQuickItem* parent)
    : QQuickItem(parent), callback_context_(std::make_unique<QObject>()) {
    setFlag(ItemHasContents, true);
    setAcceptedMouseButtons(Qt::NoButton);
    setZ(-1);
#ifndef __EMSCRIPTEN__
    if(auto* clipboard=QGuiApplication::clipboard())connect(clipboard,&QClipboard::changed,callback_context_.get(),[this](QClipboard::Mode mode){restoreClipboardSource(static_cast<int>(mode));});
#endif
    connect(this,&QQuickItem::windowChanged,callback_context_.get(),[this](QQuickWindow* next) {
        if(observed_window_)observed_window_->removeEventFilter(this);
        observed_window_=next;if(next)next->installEventFilter(this);
        ++presentation_revision_;render();
    });
}
AssistantMarkdown::~AssistantMarkdown() {
    if (observed_window_) observed_window_->removeEventFilter(this);
    // QQuickItem teardown can emit windowChanged after the derived members are gone.
    // Destroying the private context retires every past/current owned functor and queued call.
    callback_context_.reset();
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
        // Optional shading/rules do not own the parsed document or math.
        // Keep its original text/formats/resources when only the overlay fails.
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
quint64 AssistantMarkdown::beginPropertyNotification(const QString& name, const QVariant& before) {
    if (!property_notifications_.contains(name)) property_notifications_[name] = before;
    const QString versionKey = name + QStringLiteral("/notification-version");
    const auto publication = property_notifications_.value(versionKey).toULongLong() + quint64(1);
    property_notifications_[versionKey] = publication;
    return publication;
}
void AssistantMarkdown::completePropertyNotification(const QString& name, quint64 publication,
                                                      const QVariant& value, void (AssistantMarkdown::*signal)()) {
    const QString versionKey = name + QStringLiteral("/notification-version");
    if (property_notifications_.value(versionKey).toULongLong() != publication
        || property_notifications_.value(name) == value) return;
    property_notifications_[name] = value;
    property_notifications_[versionKey] = publication + quint64(1);
    (this->*signal)();
}
QQuickTextDocument* AssistantMarkdown::document() const { return target_; }
QString AssistantMarkdown::source() const { return source_; }
bool AssistantMarkdown::markdown() const { return markdown_; }
QColor AssistantMarkdown::textColor() const {return text_color_;}
void AssistantMarkdown::setTextColor(const QColor& color) {
    if(text_color_==color)return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("textColor", QVariant::fromValue(text_color_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("textColor", publication,
            QVariant::fromValue(notifyReceiver->text_color_), &AssistantMarkdown::textColorChanged);
    });
text_color_=color;++presentation_revision_;render();
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
        else result+=cursor.selectedText().replace(QChar::ParagraphSeparator,u'\n').replace(QChar::LineSeparator,u'\n');
    }
    return result;
}
QQuickItem* AssistantMarkdown::editor() const {return editor_;}
void AssistantMarkdown::setEditor(QQuickItem* editor) {
    if (editor_ == editor) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("editor", QVariant::fromValue(editor_.data()));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("editor", publication,
            QVariant::fromValue(notifyReceiver->editor_.data()), &AssistantMarkdown::editorChanged);
    });
    QObject::disconnect(editor_destroyed_);
    if (!notifyReceiver || property_notifications_.value("editor/notification-version").toULongLong() != publication) return;
    editor_ = editor;
    const auto destroyedConnection = editor ? connect(editor, &QObject::destroyed, callback_context_.get(), [this, originalTarget = QPointer<QQuickItem>(editor)] {
        if (editor_ != originalTarget) return;
        const auto destroyedPublication = beginPropertyNotification("editor", QVariant::fromValue(editor_.data()));
        completePropertyNotification("editor", destroyedPublication, QVariant::fromValue(editor_.data()), &AssistantMarkdown::editorChanged);
    }) : QMetaObject::Connection{};
    if (!notifyReceiver || property_notifications_.value("editor/notification-version").toULongLong() != publication) {
        QObject::disconnect(destroyedConnection);
        return;
    }
    editor_destroyed_ = destroyedConnection;
}
void AssistantMarkdown::restoreClipboardSource(int requestedMode) noexcept {
#ifndef __EMSCRIPTEN__
    if(copying_ || !editor_ || !document_)return;
    const auto mode=static_cast<QClipboard::Mode>(requestedMode);
    if(mode!=QClipboard::Clipboard && mode!=QClipboard::Selection)return;
    const QPointer<AssistantMarkdown> receiver(this);const QPointer<QQuickItem> editor(editor_);const QPointer<QTextDocument> document(document_);
    const auto revision=presentation_revision_;
    try {
        const int start=editor->property("selectionStart").toInt(),end=editor->property("selectionEnd").toInt();
        if(start<0 || end<=start || end>=document->characterCount())return;
        const auto current=[&]{return receiver && editor && document && receiver->editor_==editor && receiver->document_==document &&
            receiver->presentation_revision_==revision && editor->property("selectionStart").toInt()==start && editor->property("selectionEnd").toInt()==end;};
        auto* clipboard=QGuiApplication::clipboard();if(!clipboard)return;
        if((mode==QClipboard::Clipboard && !clipboard->ownsClipboard()) || (mode==QClipboard::Selection && !clipboard->ownsSelection()))return;
        const QPointer<const QMimeData> original(clipboard->mimeData(mode));if(!original || !original->hasText() || !original->hasHtml())return;
        const auto plain=original->text();if(!current() || !original || clipboard->mimeData(mode)!=original)return;
        const auto html=original->html();if(!current() || !original || clipboard->mimeData(mode)!=original)return;
        QTextCursor selection(document);selection.setPosition(start);selection.setPosition(end,QTextCursor::KeepAnchor);
        const QTextDocumentFragment fragment(selection);
        if(plain!=fragment.toPlainText())return;
        bool formula=false;
        for(int i=start;i<end;++i) {QTextCursor cell(document);cell.setPosition(i);cell.setPosition(i+1,QTextCursor::KeepAnchor);const auto format=cell.charFormat();
            if(!format.hasProperty(mathSourceProperty))continue;
            if(!format.isImageFormat() || !html.contains(format.toImageFormat().name().toHtmlEscaped()))return;
            formula=true;
        }
        if(!formula || !current())return;
        // Preserve native selection HTML structure, replacing only our image
        // objects with their original TeX. Other MIME formats/modes stay native.
        QTextDocument copied;QTextCursor copiedCursor(&copied);copiedCursor.insertFragment(fragment);
        for(;;) {auto image=copied.find(QString(QChar::ObjectReplacementCharacter));if(image.isNull())break;
            const auto format=image.charFormat();if(!format.hasProperty(mathSourceProperty))break;
            image.insertText(format.stringProperty(mathSourceProperty),QTextCharFormat{});
        }
        auto data=std::make_unique<QMimeData>();
        const auto formats=original->formats();
        for(const auto& format:formats)if(format!="text/plain" && format!="text/html" && format!="text/markdown") {
            if(!current() || !original || clipboard->mimeData(mode)!=original)return;
            const auto bytes=original->data(format);if(!current() || !original || clipboard->mimeData(mode)!=original)return;
            data->setData(format,bytes);
        }
        data->setText(selectedSource(start,end));data->setHtml(copied.toHtml());
        if(!current() || !original || clipboard->mimeData(mode)!=original)return;
        copying_=true;clipboard->setMimeData(data.release(),mode);
        if(receiver)receiver->copying_=false;
    }catch(...) {if(receiver)receiver->copying_=false;}
#else
    Q_UNUSED(requestedMode);
#endif
}
QColor AssistantMarkdown::accentColor() const { return accent_color_; }
void AssistantMarkdown::setAccentColor(const QColor& color) {
    if (accent_color_ == color) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("accentColor", QVariant::fromValue(accent_color_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("accentColor", publication,
            QVariant::fromValue(notifyReceiver->accent_color_), &AssistantMarkdown::accentColorChanged);
    });

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
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("bodyFont", QVariant::fromValue(body_font_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("bodyFont", publication,
            QVariant::fromValue(notifyReceiver->body_font_), &AssistantMarkdown::bodyFontChanged);
    });

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
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("monoFontFamily", QVariant::fromValue(mono_font_family_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("monoFontFamily", publication,
            QVariant::fromValue(notifyReceiver->mono_font_family_), &AssistantMarkdown::monoFontFamilyChanged);
    });

    mono_font_family_ = family;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableBorderColor(const QColor& color) {
    if (table_border_color_ == color) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("tableBorderColor", QVariant::fromValue(table_border_color_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("tableBorderColor", publication,
            QVariant::fromValue(notifyReceiver->table_border_color_), &AssistantMarkdown::tableBorderColorChanged);
    });

    table_border_color_ = color;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableBaseColor(const QColor& color) {
    if (table_base_color_ == color) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("tableBaseColor", QVariant::fromValue(table_base_color_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("tableBaseColor", publication,
            QVariant::fromValue(notifyReceiver->table_base_color_), &AssistantMarkdown::tableBaseColorChanged);
    });

    table_base_color_ = color;
    ++presentation_revision_;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableShadeColor(const QColor& color) {
    if (table_shade_color_ == color) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("tableShadeColor", QVariant::fromValue(table_shade_color_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("tableShadeColor", publication,
            QVariant::fromValue(notifyReceiver->table_shade_color_), &AssistantMarkdown::tableShadeColorChanged);
    });

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
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("document", QVariant::fromValue(target_.data()));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("document", publication,
            QVariant::fromValue(notifyReceiver->target_.data()), &AssistantMarkdown::documentChanged);
    });
    QObject::disconnect(target_destroyed_);
    if (!notifyReceiver || property_notifications_.value("document/notification-version").toULongLong() != publication) return;
    target_ = target;
    const auto destroyedConnection = target ? connect(target, &QObject::destroyed, callback_context_.get(), [this, originalTarget = QPointer<QQuickTextDocument>(target)] {
        if (target_ != originalTarget) return;
        const auto destroyedPublication = beginPropertyNotification("document", QVariant::fromValue(target_.data()));
        completePropertyNotification("document", destroyedPublication, QVariant::fromValue(target_.data()), &AssistantMarkdown::documentChanged);
    }) : QMetaObject::Connection{};
    if (!notifyReceiver || property_notifications_.value("document/notification-version").toULongLong() != publication) {
        QObject::disconnect(destroyedConnection);
        return;
    }
    target_destroyed_ = destroyedConnection;
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
    connect(replacement, &QTextDocument::contentsChanged, callback_context_.get(), [this,replacement] {
        if (document_ == replacement) polish();
    });
    const QPointer<QAbstractTextDocumentLayout> layout(replacement->documentLayout());
    if (!receiver || !original || receiver->target_ != original || receiver->document_ != replacement || receiver->presentation_revision_ != revision || !layout) return;
    connect(layout, &QAbstractTextDocumentLayout::update, callback_context_.get(), [this,replacement](const QRectF&) {
        if (document_ == replacement) polish();
    });
    render();
}
void AssistantMarkdown::setSource(const QString& source) {
    if (source_ == source) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("source", QVariant::fromValue(source_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("source", publication,
            QVariant::fromValue(notifyReceiver->source_), &AssistantMarkdown::sourceChanged);
    });

    source_ = source;
    ++presentation_revision_;
    render();
}
void AssistantMarkdown::setMarkdown(bool markdown) {
    if (markdown_ == markdown) return;
    const QPointer<AssistantMarkdown> notifyReceiver(this);
    const auto publication = beginPropertyNotification("markdown", QVariant::fromValue(markdown_));
    const auto changedNotice = qScopeGuard([notifyReceiver, publication] {
        if (notifyReceiver) notifyReceiver->completePropertyNotification("markdown", publication,
            QVariant::fromValue(notifyReceiver->markdown_), &AssistantMarkdown::markdownChanged);
    });

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
    MathSource captured;bool parsed=false;
    const auto restoreMetadata=[&] {
        struct Metadata {int position,length;QTextCharFormat format;};
        std::vector<Metadata> metadata;
        for(auto block=document->begin();block.isValid();block=block.next())for(auto it=block.begin();!it.atEnd();++it) {
            const auto fragment=it.fragment();if(!fragment.isValid())continue;
            auto format=fragment.charFormat();bool changed=false;
            const auto properties=format.properties();
            for(auto property=properties.cbegin();property!=properties.cend();++property) {
                if(property.value().metaType().id()==QMetaType::QString) {
                    const auto original=property.value().toString();const auto restored=restoreMathTokens(original,captured);
                    if(original!=restored){format.setProperty(property.key(),restored);changed=true;}
                } else if(property.value().metaType().id()==QMetaType::QStringList) {
                    auto values=property.value().toStringList();const auto original=values;
                    for(auto& value:values)value=restoreMathTokens(value,captured);
                    if(values!=original){format.setProperty(property.key(),values);changed=true;}
                }
            }
            if(changed)metadata.push_back({fragment.position(),fragment.length(),format});
        }
        for(const auto& value:metadata) {QTextCursor target(document);target.setPosition(value.position);target.setPosition(value.position+value.length,QTextCursor::KeepAnchor);
            target.setCharFormat(value.format);if(!current())return;}
    };
    try {
        math_text_width_=document->textWidth();
        auto* passive=static_cast<PassiveDocument*>(document.data());passive->beginMath();
        if (!markdown_) { document->setPlainText(source_);passive->endMath(); return; }
        captured=captureMath(source_);
        document->setMarkdown(captured.markdown, QTextDocument::MarkdownFeatures(QTextDocument::MarkdownDialectGitHub) | QTextDocument::MarkdownNoHTML);
        if (!current()) return;
        // Qt owns Markdown semantics. Tokens in href/title/reference metadata
        // are restored there, never installed as formulas or changed destinations.
        restoreMetadata();if(!current())return;
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
        // Optional recovery may preserve this document only after all authored
        // image objects have been stripped under the original passive policy.
        parsed=true;
        const auto dpr=window()?window()->effectiveDevicePixelRatio():qreal(1);
        for(const auto& span:captured.spans) {
            auto slot=document->find(span.token);if(slot.isNull())continue;
            try {
            const auto originalFormat=slot.charFormat();const auto blockFormat=slot.blockFormat();
            // Only an exact standalone token owns its whole original block.
            // Mixed content/whitespace keeps the existing soft-line canvas path.
            const bool centeredBlock=span.display && slot.block().text()==span.token;
            const bool code=originalFormat.fontFixedPitch() || blockFormat.hasProperty(QTextFormat::BlockCodeLanguage) || blockFormat.hasProperty(QTextFormat::BlockCodeFence);
            const auto picture=span.formula.isEmpty() || code?PassiveDocument::Picture{}:passive->picture(span.formula,document->defaultFont(),text_color_.isValid()?text_color_:QColor(Qt::black),dpr);
            if(!current())return;
            if(picture.image.isNull())slot.insertText(span.literal,originalFormat);
            else {
                const auto logical=picture.image.deviceIndependentSize();auto available=std::max(qreal(1),document->textWidth());
                // The original Qt line owns list indentation and table/quote width.
                (void)document->documentLayout()->blockBoundingRect(slot.block());if(!current())return;
                if(const auto* layout=slot.block().layout()) {
                    const auto line=layout->lineForTextPosition(slot.selectionStart()-slot.block().position());
                    if(line.isValid() && line.width()>0)available=std::min(available,line.width());
                }
                const auto scale=logical.width()>available?available/logical.width():qreal(1);
                const auto descent=picture.descent*scale;
                const auto placement=mathPlacementFont(document->defaultFont(),descent);
                if(!current())return;
                if(!placement){slot.insertText(span.literal,originalFormat);if(!current())return;continue;}
                const auto& placementFont=placement->font;
                const auto fontDescent=placement->descent;
                // Qt Quick ImageObject uses imageHeight - FORMAT font descent.
                // Pad/paint the image so that this supported baseline is the actual
                // measured formula baseline, including width scaling and DPR rounding.
                const auto width=std::ceil((span.display && !centeredBlock?available:logical.width()*scale)*dpr),height=std::ceil((logical.height()*scale+fontDescent-descent)*dpr);
                if(!std::isfinite(width) || !std::isfinite(height) || width<=0 || height<=0 ||
                    width>std::numeric_limits<int>::max() || height>std::numeric_limits<int>::max() || width*height*4>edi::assistant::Limits::ui_history_bytes) {
                    slot.insertText(span.literal,originalFormat);continue;
                }
                QImage aligned(QSize(static_cast<int>(width),static_cast<int>(height)),QImage::Format_ARGB32_Premultiplied);
                if(aligned.isNull()){slot.insertText(span.literal,originalFormat);continue;}
                aligned.setDevicePixelRatio(dpr);aligned.fill(Qt::transparent);
                const auto size=aligned.deviceIndependentSize();const auto top=size.height()-fontDescent-(logical.height()-picture.descent)*scale;
                QPainter painter(&aligned);painter.setRenderHint(QPainter::SmoothPixmapTransform);
                painter.drawImage(QRectF(span.display && !centeredBlock?(size.width()-logical.width()*scale)/2:0,top,logical.width()*scale,logical.height()*scale),picture.image);painter.end();
                const auto resource=passive->install(aligned);
                if(resource.isEmpty()){slot.insertText(span.literal,originalFormat);continue;}
                QTextImageFormat image;image.merge(originalFormat);image.setFont(placementFont);image.setName(resource.toString());
                image.setWidth(size.width());image.setHeight(size.height());
                image.setProperty(mathSourceProperty,span.literal);image.setProperty(QTextFormat::ImageAltText,span.literal);
                image.setVerticalAlignment(QTextCharFormat::AlignBaseline);
                const auto imagePosition=slot.selectionStart();slot.insertImage(image);
                if(!current())return;
                if(centeredBlock) {
                    // Keep this same paragraph/list item/cell/quote and all its
                    // other properties. Qt centers the tight image without a
                    // full-line transparent raster or extra source-copy objects.
                    auto centered=blockFormat;centered.setAlignment(Qt::AlignHCenter);
                    slot.setBlockFormat(centered);if(!current())return;
                } else if(span.display) {
                    // Soft line boundaries preserve ONE original paragraph/list
                    // item/heading/cell/quote. Centering is inside the image's
                    // original line-width canvas, not cloned semantic blocks.
                    QTextCursor display(document);display.setPosition(imagePosition);
                    if(display.position()>display.block().position()) {
                        display.insertText(QString(QChar::LineSeparator),originalFormat);if(!current())return;
                    }
                    display.setPosition(display.position()+1);
                    if(display.position()<display.block().position()+display.block().length()-1) {
                        display.insertText(QString(QChar::LineSeparator),originalFormat);if(!current())return;
                    }
                }
            }
            } catch (...) {
                if(!current())return;
                // Failure before insertion affects only this original span.
                // An already inserted image and its source mapping remain owned.
                auto literal=document->find(span.token);
                if(!literal.isNull())literal.insertText(span.literal,literal.charFormat());
            }
            if(!current())return;
        }
        passive->endMath();
        try {formatPresentation();}catch(...) {} // Optional style does not replace semantic content.
    } catch (...) {
        if (!current()) return;
        if(parsed)try {
            // A wider optional-stage failure must resolve every remaining token,
            // while keeping already admitted images and unrelated Qt Markdown.
            restoreMetadata();if(!current())return;
            for(const auto& span:captured.spans)for(;;) {
                auto slot=document->find(span.token);if(slot.isNull())break;
                slot.insertText(span.literal,slot.charFormat());if(!current())return;
            }
            static_cast<PassiveDocument*>(document.data())->endMath();
            try {formatPresentation();}catch(...) {}
            return;
        }catch(...) {if(!current())return;}
        // Only unsafe semantic construction/recovery falls back to full source.
        try {
            auto* passive=static_cast<PassiveDocument*>(document.data());passive->beginMath();passive->endMath();
            document->setPlainText(source_);
        } catch (...) {}
    }
}
} // namespace edi_app
