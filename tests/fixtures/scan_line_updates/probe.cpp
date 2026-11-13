// SPDX-License-Identifier: BSD-3-Clause
#include "scan_lines.hpp"
#include "scan_draw_rows.hpp"
#include <set>
#include <numeric>

#include <QGuiApplication>
#include <QSGGeometryNode>
#include <QtTest/QtTest>
#include <limits>

class Lines : public edi_app::ScanLines {
public:
    QSGNode* sync(QSGNode* old) { return updatePaintNode(old, nullptr); }
};

class LineUpdates : public QObject {
    Q_OBJECT
private slots:
    void screenLimitedStackedRows() {
        const std::vector<double> rows{0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
        const auto full = edi_app::stacked_draw_rows(rows, 0.5, 0, 12, 600, 5, {});
        QCOMPARE(full.size(), rows.size());
        const auto dense = edi_app::stacked_draw_rows(rows, 0.5, 0, 12, 36, 5, {});
        QCOMPARE(dense, (std::vector<std::size_t>{11, 6, 5, 0}));
        const auto selected = edi_app::stacked_draw_rows(rows, 0.5, 0, 12, 36, 7, {});
        QCOMPARE(selected, (std::vector<std::size_t>{11, 7, 6, 0}));
        const auto zoom = edi_app::stacked_draw_rows(rows, 0.5, 4, 6, 36, 5, {});
        QCOMPARE(zoom, (std::vector<std::size_t>{6, 5, 4}));
        const auto hidden = edi_app::stacked_draw_rows(rows, 0.5, 0, 12, 36, 5, std::vector<int>{0, 5, 11});
        QVERIFY(std::find(hidden.begin(), hidden.end(), 5) == hidden.end());
        QVERIFY(std::find(hidden.begin(), hidden.end(), 0) == hidden.end());
        const auto overlay = edi_app::stacked_draw_rows(std::vector<double>(20, 0), 1, 0, 1, 36, 10, {});
        QVERIFY(overlay.size() <= 4);
        QVERIFY(std::find(overlay.begin(), overlay.end(), 10) != overlay.end());
        QVERIFY(edi_app::stacked_draw_rows(rows, 1, 0, 1, 0, 1, {}).empty());
        const double nan = std::numeric_limits<double>::quiet_NaN();
        QCOMPARE(edi_app::stacked_draw_rows(std::vector<double>{nan, 0, 1}, 1, 0, 1, 600, 0, {}),
                 (std::vector<std::size_t>{2, 1}));
    }
    void mapUsesOriginalPixelBands() {
        const std::vector<double> rows{0, 1};
        const std::vector<edi::ScanRowSpan> spans{{-0.5, 0.5}, {0.5, 1.5}};
        const auto stepped = edi_app::map_pixel_rows(rows, spans, -0.5, 1.5, 8, false);
        const auto smooth = edi_app::map_pixel_rows(rows, spans, -0.5, 1.5, 8, true);
        QCOMPARE(stepped.size(), std::size_t{8});
        QCOMPARE(stepped[3].band, std::size_t{1});
        QCOMPARE(stepped[3].lower, std::size_t{1});
        QCOMPARE(smooth[3].band, std::size_t{1});
        QCOMPARE(smooth[3].lower, std::size_t{0});
        QCOMPARE(smooth[3].upper, std::size_t{1});
        QCOMPARE(smooth[3].share, 0.75);
        QCOMPARE(smooth[4].share, 0.25);
        const auto outside = edi_app::map_pixel_rows(rows, spans, -2, 2, 4, true);
        QCOMPARE(outside.back().band, edi_app::MapPixelRow::none);
        const std::vector<double> unsorted{1, 0};
        const auto reordered = edi_app::map_pixel_rows(unsorted,
            std::vector<edi::ScanRowSpan>{{0.5, 1.5}, {-0.5, 0.5}}, -0.5, 1.5, 8, true);
        QCOMPARE(reordered[3].band, std::size_t{0});
        QCOMPARE(reordered[3].lower, std::size_t{1});
        QCOMPARE(reordered[3].share, 0.75);
        const auto zoom = edi_app::map_pixel_rows(rows, spans, 0.8, 1.2, 3, true);
        for (const auto& row : zoom) {
            QCOMPARE(row.band, std::size_t{1});
            QCOMPARE(row.lower, std::size_t{1});
            QCOMPARE(row.upper, std::size_t{1});
        }
        QVERIFY(edi_app::map_pixel_rows(rows, spans, 1, 0, 3, true).empty());
    }
    void keepUnchangedGroups() {
        Lines lines;
        lines.setHeight(100);
        lines.setTraces(std::vector<Lines::Trace>(130, {{0, 1, 2}, {0, 1, 0}}));
        lines.setStyles(std::vector<Lines::Style>(130));
        QScopedPointer<QSGNode> root(lines.sync(nullptr));
        auto* first = static_cast<QSGGeometryNode*>(root->firstChild()->nextSibling());
        auto* middle = static_cast<QSGGeometryNode*>(first->nextSibling());
        auto* last = static_cast<QSGGeometryNode*>(middle->nextSibling());
        auto* firstGeometry = first->geometry();
        auto* middleGeometry = middle->geometry();
        auto* lastGeometry = last->geometry();
        QCOMPARE(firstGeometry->vertexCount(), 64 * 2 * 4);
        const float gap = std::numeric_limits<float>::quiet_NaN();
        lines.setTrace(65, {{0, 1, gap, 3, 4}, {0, 1, gap, 1, 0}});
        QCOMPARE(lines.sync(root.data()), root.data());
        QCOMPARE(first->geometry(), firstGeometry);
        QVERIFY(middle->geometry() != middleGeometry);
        QCOMPARE(last->geometry(), lastGeometry);
        QCOMPARE(middle->geometry()->vertexCount(), 64 * 2 * 4);
        middleGeometry = middle->geometry();
        lines.setStyles(std::vector<Lines::Style>(130, {0.4, 0.2, Qt::red}));
        lines.setYMin(-2);
        lines.setYMax(3);
        lines.sync(root.data());
        QCOMPARE(first->geometry(), firstGeometry);
        QCOMPARE(middle->geometry(), middleGeometry);
        QCOMPARE(last->geometry(), lastGeometry);
        lines.setActive(false);
        lines.setTrace(0, {{0, 1}, {1, 2}});
        lines.sync(root.data());
        QCOMPARE(first->geometry(), firstGeometry);
        lines.setActive(true);
        lines.sync(root.data());
        QVERIFY(first->geometry() != firstGeometry);
        QCOMPARE(first->geometry()->vertexCount(), (63 * 2 + 1) * 4);
        QCOMPARE(middle->geometry(), middleGeometry);
        QCOMPARE(last->geometry(), lastGeometry);
        QVERIFY_EXCEPTION_THROWN(lines.setTrace(130, {}), std::out_of_range);
        root.reset();
        root.reset(lines.sync(nullptr));
        first = static_cast<QSGGeometryNode*>(root->firstChild()->nextSibling());
        QCOMPARE(first->geometry()->vertexCount(), (63 * 2 + 1) * 4);
    }
    void resizeAndReplace() {
        Lines lines;
        lines.setTraces(std::vector<Lines::Trace>(67, {{0, 1}, {0, 1}}));
        lines.setStyles(std::vector<Lines::Style>(65));
        QScopedPointer<QSGNode> root(lines.sync(nullptr));
        auto* first = static_cast<QSGGeometryNode*>(root->firstChild()->nextSibling());
        auto* last = static_cast<QSGGeometryNode*>(first->nextSibling());
        auto* unchanged = first->geometry();
        QCOMPARE(last->geometry()->vertexCount(), 4);
        lines.setStyles(std::vector<Lines::Style>(67));
        lines.sync(root.data());
        QCOMPARE(first->geometry(), unchanged);
        QCOMPARE(last->geometry()->vertexCount(), 12);
        lines.setStyles(std::vector<Lines::Style>(64));
        lines.sync(root.data());
        QCOMPARE(root->childCount(), 2);
        lines.setStyles(std::vector<Lines::Style>(67));
        lines.sync(root.data());
        QCOMPARE(root->childCount(), 3);
        lines.setTraces(std::vector<Lines::Trace>(67, {{0, 1, 2}, {0, 1, 0}}));
        lines.sync(root.data());
        QVERIFY(first->geometry() != unchanged);
        QCOMPARE(first->geometry()->vertexCount(), 64 * 2 * 4);
        lines.setTraces({});
        lines.sync(root.data());
        QCOMPARE(root->childCount(), 1);
    }
};

int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    LineUpdates tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "probe.moc"
