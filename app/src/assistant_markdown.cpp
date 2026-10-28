// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_markdown.hpp"

#include <QImage>
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
class PassiveDocument final : public QTextDocument {
 public:
    explicit PassiveDocument(QObject* parent) : QTextDocument(parent) { setUndoRedoEnabled(false); }
 protected:
    QVariant loadResource(int, const QUrl&) override {
        // A VALID empty image prevents QTextDocument::resource from falling
        // through to either the per-document or global resource provider. Never
        // invoke the base loader: it can resolve local files, data URLs or parents.
        return QVariant::fromValue(QImage{});
    }
};
}
AssistantMarkdown::AssistantMarkdown(QQuickItem* parent) : QQuickItem(parent) {
    setFlag(ItemHasContents, true);
    setAcceptedMouseButtons(Qt::NoButton);
    setZ(-1);
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
        if (markdown_) try { formatPresentation(); } catch (...) {}
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
        if (!markdown_) { document->setPlainText(source_); return; }
        document->setMarkdown(source_, QTextDocument::MarkdownFeatures(QTextDocument::MarkdownDialectGitHub) | QTextDocument::MarkdownNoHTML);
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
        formatPresentation();
    } catch (...) {
        if (!current()) return;
        // Preserve the complete original as literal text on presentation failure.
        try { document->setPlainText(source_); } catch (...) {}
    }
}
} // namespace edi_app
