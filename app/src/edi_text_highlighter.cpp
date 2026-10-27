// SPDX-License-Identifier: BSD-3-Clause
#include "edi_text_highlighter.hpp"

#include <QTextCharFormat>
#include <QRegularExpression>
#include <QTextDocument>

namespace edi_app {

namespace {
constexpr int kOutsideLoop = 0;
constexpr int kLoopKeys = 1;  // after `loop_`, while its column names are listed
constexpr int kTextField = 2;  // inside a `;` text field

int token_length(const QString& line) {
    const qsizetype end = line.indexOf(QRegularExpression(QStringLiteral("\\s")));
    return static_cast<int>(end < 0 ? line.size() : end);
}
}  // namespace

EdiTextHighlighter::EdiTextHighlighter(QObject* parent) : QObject(parent) {
    connect(this, &EdiTextHighlighter::colorsChanged, this, [this] {
        if (rules_ != nullptr) {
            rules_->rehighlight();
        }
    });
}

void EdiTextHighlighter::setDocument(QQuickTextDocument* document) {
    if (document == document_) {
        return;
    }
    delete rules_;
    rules_ = nullptr;
    document_ = document;
    if (document_ != nullptr && document_->textDocument() != nullptr) {
        rules_ = new EdiTextRules(document_->textDocument(), *this);
    }
    emit documentChanged();
}

QColor EdiTextHighlighter::colorAt(const QString& text, int position) const {
    int state = kOutsideLoop;
    qsizetype start = 0;
    for (const QString& line : text.split(QLatin1Char('\n'))) {
        const int previous = state;
        const QColor color = EdiTextRules::token_color(line, previous, *this, state);
        if (position >= start && position < start + token_length(line)) {
            return color;
        }
        start += line.size() + 1;
    }
    return {};
}

EdiTextRules::EdiTextRules(QTextDocument* document, const EdiTextHighlighter& colors)
    : QSyntaxHighlighter(document), colors_(colors) {}

QColor EdiTextRules::token_color(const QString& line, int previous, const EdiTextHighlighter& colors, int& state) {
    if (previous == kTextField) {
        state = line.startsWith(QLatin1Char(';')) ? kOutsideLoop : kTextField;
        return {};
    }
    if (line.startsWith(QLatin1Char(';'))) {
        state = kTextField;
        return {};
    }
    if (line.startsWith(QStringLiteral("data_"))) {
        state = kOutsideLoop;
        return colors.datablock_;
    }
    if (line.trimmed() == QStringLiteral("loop_")) {
        state = kLoopKeys;
        return colors.loop_;
    }
    if (line.startsWith(QLatin1Char('_'))) {
        state = previous == kLoopKeys ? kLoopKeys : kOutsideLoop;
        return previous == kLoopKeys ? colors.loop_column_ : colors.item_;
    }
    state = kOutsideLoop;
    return {};
}

void EdiTextRules::highlightBlock(const QString& text) {
    int state = kOutsideLoop;
    const int previous = previousBlockState() < 0 ? kOutsideLoop : previousBlockState();
    const QColor color = token_color(text, previous, colors_, state);
    setCurrentBlockState(state);
    if (color.isValid()) {
        QTextCharFormat format;
        format.setForeground(color);
        setFormat(0, token_length(text), format);
    }
}

}  // namespace edi_app
