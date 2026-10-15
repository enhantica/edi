// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_markdown.hpp"

#include <QImage>
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
void AssistantMarkdown::formatPresentation() {
    if (!document_) return;
    auto option = document_->defaultTextOption();
    option.setWrapMode(QTextOption::WrapAtWordBoundaryOrAnywhere);
    document_->setDefaultTextOption(option);
    const qreal line = QFontMetricsF(document_->defaultFont()).height();
    document_->setIndentWidth(line * 1.25);
    // QTextDocument retains the semantic list/code/table structure. Relax only
    // parsed no-wrap block presentation, never inject characters into content.
    std::vector<std::pair<int, int>> anchors;
    for (auto block = document_->begin(); block.isValid(); block = block.next()) {
        auto format = block.blockFormat();
        format.setNonBreakableLines(false);
        const bool listed = block.textList() != nullptr;
        format.setTopMargin(listed && block.previous().textList() == block.textList() ? 0 : line * 0.25);
        format.setBottomMargin(listed && block.next().textList() == block.textList() ? 0 : line * 0.4);
        QTextCursor cursor(block);
        cursor.setBlockFormat(format);
        if (auto* table = cursor.currentTable()) {
            auto table_format = table->format();
            table_format.setWidth(QTextLength(QTextLength::PercentageLength, 100));
            table->setFormat(table_format);
        }
        for (auto it = block.begin(); !it.atEnd(); ++it) {
            const auto fragment = it.fragment();
            if (fragment.isValid() && fragment.charFormat().isAnchor())
                anchors.emplace_back(fragment.position(), fragment.length());
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
