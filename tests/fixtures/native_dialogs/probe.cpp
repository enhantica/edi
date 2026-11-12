// SPDX-License-Identifier: BSD-3-Clause
#include "native_dialog.hpp"
#include "native_dialog_helper.hpp"
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QProcess>
#include <QSignalSpy>
#include <QTest>
#include <cstdio>
#include <cstring>
using namespace edi_app;

namespace {
void write(const QJsonObject& message) {
    const auto bytes = QJsonDocument(message).toJson(QJsonDocument::Compact) + '\n';
    std::fwrite(bytes.constData(), 1, static_cast<std::size_t>(bytes.size()), stdout);
    std::fflush(stdout);
}
int fake() {
    char request[65536];
    if (!std::fgets(request, sizeof request, stdin)) return 2;
    const auto object = QJsonDocument::fromJson(request).object();
    const auto scenario = object.value("title").toString();
    if (scenario == "hang") { std::getc(stdin); return 0; }
    write({{"schema", 1}, {"event", "ready"}});
    if (scenario == "hold") { std::getc(stdin); return 0; }
    if (scenario == "bad") { std::puts("not JSON"); return 0; }
    if (scenario == "reject") { write({{"schema", 1}, {"event", "rejected"}}); return 0; }
    QJsonArray files;
    files.append(scenario == "nonlocal" ? "https://example.org/file" : "file:///tmp/name%20with%20spaces.xy");
    if (object.value("mode").toInt() == NativeFileDialog::OpenFiles) files.append("file:///tmp/%CE%B1.xy");
    const QJsonObject accepted{{"schema", 1}, {"event", "accepted"}, {"files", files}, {"currentFolder", "file:///tmp"}};
    write(accepted);
    if (scenario == "duplicate") write(accepted);
    if (scenario == "late") { std::getc(stdin); return 0; }
    return scenario == "failed" ? 3 : 0;
}
}
class DialogChecks : public QObject {
    Q_OBJECT
private slots:
    void validSelection() {
        NativeDialogs broker(QCoreApplication::applicationFilePath(), {"--fake"}, 1000);
        NativeFileDialog picker;
        picker.setProperty("fileMode", NativeFileDialog::OpenFiles);
        QSignalSpy accepted(&picker, &NativeFileDialog::accepted);
        QSignalSpy rejected(&picker, &NativeFileDialog::rejected);
        broker.open(&picker);
        QTRY_COMPARE(accepted.count(), 1);
        QCOMPARE(rejected.count(), 0);
        QCOMPARE(picker.property("selectedFiles").value<QList<QUrl>>(),
                 (QList<QUrl>{QUrl::fromLocalFile("/tmp/name with spaces.xy"), QUrl::fromLocalFile(QString::fromUtf8("/tmp/α.xy"))}));
        QVERIFY(!broker.busy());
        QVERIFY(!picker.visible());
        QVERIFY(broker.error().isEmpty());
    }
    void rejection_data() {
        QTest::addColumn<QString>("scenario");
        QTest::newRow("bad JSON") << "bad";
        QTest::newRow("nonlocal") << "nonlocal";
        QTest::newRow("duplicate") << "duplicate";
        QTest::newRow("exit failure after reply") << "failed";
        QTest::newRow("native cancel") << "reject";
    }
    void rejection() {
        QFETCH(QString, scenario);
        NativeDialogs broker(QCoreApplication::applicationFilePath(), {"--fake"}, 1000);
        NativeFileDialog picker;
        picker.setProperty("title", scenario);
        QSignalSpy accepted(&picker, &NativeFileDialog::accepted), rejected(&picker, &NativeFileDialog::rejected);
        broker.open(&picker);
        QTRY_COMPARE(rejected.count(), 1);
        QCOMPARE(accepted.count(), 0);
        QVERIFY(!picker.property("selectedFile").toUrl().isValid());
        QCOMPARE(broker.error().isEmpty(), scenario == "reject");
    }
    void cancel_data() {
        QTest::addColumn<QString>("scenario");
        QTest::newRow("before panel opens") << "hang";
        QTest::newRow("after panel opens") << "hold";
        QTest::newRow("answer held until successful exit") << "late";
    }
    void cancel() {
        QFETCH(QString, scenario);
        NativeDialogs broker(QCoreApplication::applicationFilePath(), {"--fake"}, 1000);
        NativeFileDialog picker;
        picker.setProperty("title", scenario);
        QSignalSpy accepted(&picker, &NativeFileDialog::accepted), rejected(&picker, &NativeFileDialog::rejected);
        int pulses = 0;
        QTimer pulse;
        connect(&pulse, &QTimer::timeout, this, [&] { ++pulses; });
        pulse.start(1);
        broker.open(&picker);
        QTRY_VERIFY(pulses > 3);
        QVERIFY(broker.busy());
        broker.cancel();
        QCOMPARE(rejected.count(), 1);
        QCOMPARE(accepted.count(), 0);
        QVERIFY(!broker.busy());
        broker.open(&picker);
        broker.cancel();
        QCOMPARE(rejected.count(), 2);
        QCOMPARE(accepted.count(), 0);
    }
    void timeout() {
        NativeDialogs broker(QCoreApplication::applicationFilePath(), {"--fake"}, 50);
        NativeFileDialog picker;
        picker.setProperty("title", "hang");
        QSignalSpy rejected(&picker, &NativeFileDialog::rejected);
        broker.open(&picker);
        QTRY_COMPARE(rejected.count(), 1);
        QVERIFY(!broker.busy());
        QVERIFY(!broker.error().isEmpty());
    }
    void missingHelper() {
        NativeDialogs broker("/does/not/exist", {}, 1000);
        NativeFileDialog picker;
        QSignalSpy rejected(&picker, &NativeFileDialog::rejected);
        broker.open(&picker);
        QTRY_COMPARE(rejected.count(), 1);
        QVERIFY(!broker.busy());
    }
    void overlappingRequestRejected() {
        NativeDialogs broker(QCoreApplication::applicationFilePath(), {"--fake"}, 1000);
        NativeFileDialog first, second;
        first.setProperty("title", "hang");
        QSignalSpy rejected(&second, &NativeFileDialog::rejected);
        broker.open(&first);
        broker.open(&second);
        QCOMPARE(rejected.count(), 1);
        QVERIFY(first.visible());
        QVERIFY(broker.busy());
        broker.cancel();
    }
    void ownerDestroyed() {
        NativeDialogs broker(QCoreApplication::applicationFilePath(), {"--fake"}, 1000);
        auto* picker = new NativeFileDialog;
        picker->setProperty("title", "hang");
        broker.open(picker);
        delete picker;
        QVERIFY(!broker.busy());
        NativeFileDialog another;
        broker.open(&another);
        QSignalSpy accepted(&another, &NativeFileDialog::accepted);
        QTRY_COMPARE(accepted.count(), 1);
    }
    void parentPipeClosed() {
        QProcess helper;
        QByteArray output;
        connect(&helper, &QProcess::readyReadStandardOutput, this, [&] { output += helper.readAllStandardOutput(); });
        helper.start(QCoreApplication::applicationFilePath(), {"--native-dialog-helper"});
        QTRY_COMPARE(helper.state(), QProcess::Running);
        helper.write("{\"schema\":1,\"mode\":0,\"directory\":false,\"title\":\"Fixture\",\"acceptLabel\":\"\",\"defaultSuffix\":\"\",\"nameFilters\":[],\"currentFolder\":\"file:///tmp\",\"selectedFile\":\"\"}\n");
        QTRY_VERIFY_WITH_TIMEOUT(output.contains("ready"), 5000);
        helper.closeWriteChannel();
        QTRY_COMPARE(helper.state(), QProcess::NotRunning);
        QCOMPARE(helper.exitCode(), 0);
    }
};
int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "--fake") == 0) return fake();
    if (argc == 2 && std::strcmp(argv[1], "--native-dialog-helper") == 0) return native_dialog_helper_main(argc, argv);
    QCoreApplication app(argc, argv);
    DialogChecks checks;
    return QTest::qExec(&checks, argc, argv);
}
#include "probe.moc"
