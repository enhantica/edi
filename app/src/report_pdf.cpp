// SPDX-License-Identifier: BSD-3-Clause
#include "report_pdf.hpp"

#include <QAbstractTextDocumentLayout>
#include <QBuffer>
#include <QFont>
#include <QImage>
#include <QMarginsF>
#include <QPageLayout>
#include <QPageSize>
#include <QPainter>
#include <QPdfWriter>
#include <QTextBlock>
#include <QTextCursor>
#include <QTextDocument>
#include <QTextFrame>
#include <QTextTable>
#include <QUrl>
#include <exception>
#include <string>

#include "edi/report_html.hpp"

namespace edi_app {

namespace {

// The page is laid out at 1800 to the inch, where the body's 10.04 pt is a whole number of pixels (251): Qt sets a font
// in whole pixels, so at 96 to the inch the body would be 13 px, 9.75 pt. The text stays vector and the figures keep
// their own resolution in the file.
constexpr int kDpi = 1800;
constexpr double kMarginMm = 25.0;
constexpr double kBodyPoints = 10.04;
// The figure's frame, its table's borders and edge, in the HTML's px: the figure is that much narrower than the column.
constexpr double kFigureFrame = 3.0;

// How many of the device's pixels the document gives one px of its HTML. Qt takes a px as one dot of the screen's
// logical resolution, 1/96 inch on Linux and Windows but 1/72 inch on macOS, where figures sized in 96ths ran a third
// past the column; so it is measured on this device, from one image of a known width.
double documentPixel(QPaintDevice* device) {
    QTextDocument probe;
    probe.documentLayout()->setPaintDevice(device);
    probe.setDocumentMargin(0);
    QImage dot(1, 1, QImage::Format_ARGB32);
    dot.fill(Qt::transparent);
    probe.addResource(QTextDocument::ImageResource, QUrl(QStringLiteral("dot")), dot);
    probe.setHtml(QStringLiteral("<img src=\"dot\" width=\"100\">"));
    return probe.documentLayout()->documentSize().width() / 100.0;
}

// Where pages break: a figure, or a table shorter than a third of a page, is kept whole, on the next page if it does not
// fit, and a heading never ends its page: one whose next block starts on a later page moves there too, taking along what moved
// below it, and so does a heading right above it. Each move lays the document out again, so the walk starts over
// after it.
void breakPages(QTextDocument& document, double page_height) {
    QAbstractTextDocumentLayout* layout = document.documentLayout();
    const auto page_at = [&](double y) { return static_cast<int>(y / page_height); };
    const auto page_of = [&](const QTextBlock& block) { return page_at(layout->blockBoundingRect(block).top()); };
    for (int pass = 0; pass < document.blockCount(); ++pass) {
        bool moved = false;
        for (QTextFrame* frame : document.rootFrame()->childFrames()) {
            auto* table = qobject_cast<QTextTable*>(frame);
            const QRectF box = layout->frameBoundingRect(frame);
            QTextFrameFormat format = frame->frameFormat();
            // A figure is its table's one cell, kept whole at any height a page holds.
            const bool figure = table != nullptr && table->rows() == 1 && table->columns() == 1;
            if (table == nullptr || box.height() >= (figure ? page_height : page_height / 3) ||
                (format.pageBreakPolicy() & QTextFormat::PageBreak_AlwaysBefore) != 0 ||
                page_at(box.top()) == page_at(box.bottom() - 1)) {
                continue;
            }
            format.setPageBreakPolicy(QTextFormat::PageBreak_AlwaysBefore);
            frame->setFrameFormat(format);
            moved = true;
            break;
        }
        if (moved) {
            continue;
        }
        for (QTextBlock block = document.begin(); block.isValid() && block.next().isValid(); block = block.next()) {
            QTextBlockFormat format = block.blockFormat();
            if (format.headingLevel() == 0 || (format.pageBreakPolicy() & QTextFormat::PageBreak_AlwaysBefore) != 0 ||
                page_of(block.next()) <= page_of(block)) {
                continue;
            }
            format.setPageBreakPolicy(QTextFormat::PageBreak_AlwaysBefore);
            QTextCursor(block).setBlockFormat(format);
            // A heading or a table right below that moved already follows this heading onto the new page.
            QTextBlockFormat next = block.next().blockFormat();
            if (next.headingLevel() != 0) {
                next.setPageBreakPolicy(QTextFormat::PageBreak_Auto);
                QTextCursor(block.next()).setBlockFormat(next);
            }
            if (QTextTable* table = QTextCursor(block.next()).currentTable()) {
                QTextFrameFormat table_format = table->frameFormat();
                table_format.setPageBreakPolicy(QTextFormat::PageBreak_Auto);
                table->setFrameFormat(table_format);
            }
            moved = true;
            break;
        }
        if (!moved) {
            return;
        }
    }
}

}  // namespace

QByteArray reportPdf(const edi::ReportModel& model, const QHash<QString, QImage>& figures, const QString& fontFamily) {
    QByteArray bytes;
    QBuffer buffer(&bytes);
    if (!buffer.open(QIODevice::WriteOnly)) {
        return {};
    }
    QPdfWriter writer(&buffer);
    writer.setResolution(kDpi);
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize::A4), QPageLayout::Portrait,
                                     QMarginsF(kMarginMm, kMarginMm, kMarginMm, kMarginMm), QPageLayout::Millimeter));
    writer.setTitle(QString::fromStdString(model.title.empty() ? model.name : model.title));
    writer.setCreator(QStringLiteral("EasyDiffraction"));
    const QRectF body = writer.pageLayout().paintRectPixels(kDpi);

    QFont font(fontFamily);
    font.setPointSizeF(kBodyPoints);
    QTextDocument document;
    document.documentLayout()->setPaintDevice(&writer);
    document.setUseDesignMetrics(true);
    document.setDocumentMargin(0);
    document.setDefaultFont(font);
    document.setPageSize(body.size());
    for (auto it = figures.cbegin(); it != figures.cend(); ++it) {
        document.addResource(QTextDocument::ImageResource, QUrl(it.key()), it.value());
    }
    try {
        const double column = body.width() / documentPixel(&writer);
        document.setHtml(QString::fromStdString(edi::report_static_html(model, column - kFigureFrame)));
    } catch (const std::exception&) {
        return {};
    }
    breakPages(document, body.height());

    QPainter painter;
    if (!painter.begin(&writer)) {
        return {};
    }
    const double margin = kMarginMm / 25.4 * kDpi;
    for (int page = 0; page < document.pageCount(); ++page) {
        if (page > 0) {
            writer.newPage();
        }
        painter.save();
        painter.translate(0, -page * body.height());
        document.drawContents(&painter, QRectF(0, page * body.height(), body.width(), body.height()));
        painter.restore();
        painter.setFont(font);
        painter.drawText(QRectF(0, body.height(), body.width(), margin), Qt::AlignCenter, QString::number(page + 1));
    }
    painter.end();
    return bytes;
}

}  // namespace edi_app
