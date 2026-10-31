// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EDI_TEXT_HIGHLIGHTER_HPP
#define EDI_APP_EDI_TEXT_HIGHLIGHTER_HPP

#include <QColor>
#include <QObject>
#include <QPointer>
#include <QQuickTextDocument>
#include <QSyntaxHighlighter>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

class EdiTextRules;

/// Colours a Text tab's `.edi` text as easydiffraction's coloured CIF does (the owner, 2026-10-25; edi ADR-0017 §7):
/// datablock names, plain item names, a loop's column names and `loop_`, each in its colour. The colours come from
/// the theme (AppColors); the text itself is never changed.
class EdiTextHighlighter : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickTextDocument* document READ document WRITE setDocument NOTIFY documentChanged)
    Q_PROPERTY(QColor datablockColor MEMBER datablock_ NOTIFY datablockColorChanged)
    Q_PROPERTY(QColor itemColor MEMBER item_ NOTIFY itemColorChanged)
    Q_PROPERTY(QColor loopColumnColor MEMBER loop_column_ NOTIFY loopColumnColorChanged)
    Q_PROPERTY(QColor loopColor MEMBER loop_ NOTIFY loopColorChanged)

   public:
    explicit EdiTextHighlighter(QObject* parent = nullptr);
    QQuickTextDocument* document() const { return document_; }
    void setDocument(QQuickTextDocument* document);

    /// The colour the token at `position` of `text` takes, or an invalid colour where nothing is coloured.
    Q_INVOKABLE QColor colorAt(const QString& text, int position) const;

   signals:
    void documentChanged();
    void colorsChanged();
    void datablockColorChanged();
    void itemColorChanged();
    void loopColumnColorChanged();
    void loopColorChanged();

   private:
    friend class EdiTextRules;
    QPointer<QQuickTextDocument> document_;
    EdiTextRules* rules_ = nullptr;
    QColor datablock_;
    QColor item_;
    QColor loop_column_;
    QColor loop_;
};

/// The highlighter proper, on the document's QTextDocument.
class EdiTextRules : public QSyntaxHighlighter {
   public:
    EdiTextRules(QTextDocument* document, const EdiTextHighlighter& colors);
    /// The colour of the first token of `line`, after a line in state `previous` (1: a loop's keys), and the
    /// state the line leaves: a datablock name, `loop_`, a loop column name or an item name.
    static QColor token_color(const QString& line, int previous, const EdiTextHighlighter& colors, int& state);

   protected:
    void highlightBlock(const QString& text) override;

   private:
    const EdiTextHighlighter& colors_;
};

}  // namespace edi_app

#endif  // EDI_APP_EDI_TEXT_HIGHLIGHTER_HPP
