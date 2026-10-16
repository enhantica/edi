// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_markdown.hpp"

#include <QImage>
#include <algorithm>
#include <cmath>
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
AssistantMarkdown::AssistantMarkdown(QObject* parent) : QObject(parent) {}
QQuickTextDocument* AssistantMarkdown::document() const { return target_; }
QString AssistantMarkdown::source() const { return source_; }
bool AssistantMarkdown::markdown() const { return markdown_; }
QColor AssistantMarkdown::accentColor() const { return accent_color_; }
void AssistantMarkdown::setAccentColor(const QColor& color) {
    if (accent_color_ == color) return;
    accent_color_ = color;
    if (document_ && markdown_) {
        try { formatPresentation(); } catch (...) {}
    }
}
QFont AssistantMarkdown::bodyFont() const { return body_font_; }
QString AssistantMarkdown::monoFontFamily() const { return mono_font_family_; }
QColor AssistantMarkdown::tableBorderColor() const { return table_border_color_; }
QColor AssistantMarkdown::tableShadeColor() const { return table_shade_color_; }
void AssistantMarkdown::setBodyFont(const QFont& font) {
    if (body_font_set_ && body_font_ == font) return;
    body_font_ = font; body_font_set_ = true;
    if (document_) {
        document_->setDefaultFont(font);
        if (markdown_) try { formatPresentation(); } catch (...) {}
    }
}
void AssistantMarkdown::setMonoFontFamily(const QString& family) {
    if (mono_font_family_ == family) return;
    mono_font_family_ = family;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableBorderColor(const QColor& color) {
    if (table_border_color_ == color) return;
    table_border_color_ = color;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::setTableShadeColor(const QColor& color) {
    if (table_shade_color_ == color) return;
    table_shade_color_ = color;
    if (document_ && markdown_) try { formatPresentation(); } catch (...) {}
}
void AssistantMarkdown::formatPresentation() {
    if (!document_) return;
    auto option = document_->defaultTextOption();
    option.setWrapMode(QTextOption::WrapAtWordBoundaryOrAnywhere);
    document_->setDefaultTextOption(option);
    const auto body_font = document_->defaultFont();
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
    document_->setIndentWidth(line * 1.25);
    // QTextDocument retains the semantic list/code/table structure. Relax only
    // parsed no-wrap block presentation, never inject characters into content.
    std::vector<std::pair<int, int>> anchors, code;
    std::vector<QTextTable*> tables;
    for (auto block = document_->begin(); block.isValid(); block = block.next()) {
        auto format = block.blockFormat();
        format.setNonBreakableLines(false);
        const bool listed = block.textList() != nullptr;
        format.setTopMargin(listed && block.previous().textList() == block.textList() ? 0 : line * 0.25);
        format.setBottomMargin(listed && block.next().textList() == block.textList() ? 0 : line * 0.4);
        QTextCursor cursor(block);
        cursor.setBlockFormat(format);
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
        QTextCursor cursor(document_);
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
    }
    // Existing report_html.cpp: thin outside/header rules, zero vertical
    // padding, 6pt horizontal spacing at 20.4pt line height, shaded header/even rows.
    for (auto* table : tables) {
        auto format = table->format();
        // These tables come exclusively from setMarkdown(MarkdownNoHTML).
        // Markdown tables have one header row; Qt marks TH text bold but does
        // not populate QTextTableFormat::headerRowCount itself.
        format.setHeaderRowCount(1);
        format.setWidth(QTextLength(QTextLength::PercentageLength, 100));
        format.setCellSpacing(0); format.setCellPadding(0); format.setBorderCollapse(true);
        format.setBorder(0.5); format.setBorderStyle(QTextFrameFormat::BorderStyle_Solid);
        if (table_border_color_.isValid()) format.setBorderBrush(table_border_color_);
        table->setFormat(format);
        for (int r = 0; r < table->rows(); ++r) for (int column = 0; column < table->columns(); ++column) {
            auto cell = table->cellAt(r, column);
            if (cell.row() != r || cell.column() != column) continue; // Keep parsed merged-cell semantics.
            auto cell_format = cell.format().toTableCellFormat();
            cell_format.setBorder(0); cell_format.setTopPadding(0); cell_format.setBottomPadding(0);
            cell_format.setLeftPadding(line * 6 / 20.4); cell_format.setRightPadding(line * 6 / 20.4);
            if (r + cell.rowSpan() == format.headerRowCount()) {
                cell_format.setBottomBorder(0.5); cell_format.setBottomBorderStyle(QTextFrameFormat::BorderStyle_Solid);
                if (table_border_color_.isValid()) cell_format.setBottomBorderBrush(table_border_color_);
            }
            if (table_shade_color_.isValid() && (r < format.headerRowCount() || (r - format.headerRowCount()) % 2 == 1))
                cell_format.setBackground(table_shade_color_);
            else cell_format.clearBackground();
            cell.setFormat(cell_format);
        }
    }
    if (!accent_color_.isValid()) return;
    QTextCharFormat accent;
    accent.setForeground(accent_color_);
    for (const auto& [position, length] : anchors) {
        QTextCursor cursor(document_);
        cursor.setPosition(position);
        cursor.setPosition(position + length, QTextCursor::KeepAnchor);
        cursor.mergeCharFormat(accent);
    }
}
void AssistantMarkdown::setDocument(QQuickTextDocument* target) {
    if (target_ == target) return;
    target_ = target;
    document_ = nullptr;
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
    target->setTextDocument(replacement);
    document_ = replacement;
    render();
}
void AssistantMarkdown::setSource(const QString& source) {
    if (source_ == source) return;
    source_ = source;
    render();
}
void AssistantMarkdown::setMarkdown(bool markdown) {
    if (markdown_ == markdown) return;
    markdown_ = markdown;
    render();
}
void AssistantMarkdown::render() noexcept {
    if (!document_) return;
    try {
        if (!markdown_) { document_->setPlainText(source_); return; }
        document_->setMarkdown(source_, QTextDocument::MarkdownFeatures(QTextDocument::MarkdownDialectGitHub) | QTextDocument::MarkdownNoHTML);
        // Qt owns Markdown parsing. Replace only its parsed image objects with
        // literal alternative text; no URI is fetched or second HTML parse made.
        QTextCursor cursor(document_);
        for (;;) {
            auto image = document_->find(QString(QChar::ObjectReplacementCharacter), cursor);
            if (image.isNull()) break;
            cursor = image;
            if (!image.charFormat().isImageFormat()) continue;
            const auto alternative = image.charFormat().stringProperty(QTextFormat::ImageAltText);
            image.insertText(alternative, QTextCharFormat{});
            cursor = image;
        }
        formatPresentation();
    } catch (...) {
        // Formatting failure cannot alter canonical history or manufacture a
        // provider result. Preserve the exact original as literal text if possible.
        try { document_->setPlainText(source_); } catch (...) {}
    }
}
} // namespace edi_app
