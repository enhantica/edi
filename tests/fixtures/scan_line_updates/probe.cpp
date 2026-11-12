// SPDX-License-Identifier: BSD-3-Clause
#include "scan_lines.hpp"

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
