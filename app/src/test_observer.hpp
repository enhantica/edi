// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_TEST_OBSERVER_HPP
#define EDI_APP_TEST_OBSERVER_HPP

#include <QStringList>
#include <optional>
#include <span>
#include <QVariantMap>
#include <QJsonValue>
#include <QStringView>
#include <QByteArray>

class QQmlApplicationEngine;

namespace edi_app {

// `edi_app --test-observer <action> [arguments]`: a system test drives the real app and reads what it
// observed, so tests reuse the CI-built app instead of compiling an instrumented copy. It runs only
// when EDI_TEST_OBSERVERS=1 and pytest's PYTEST_CURRENT_TEST are both set.
//
//   joint <project>   load the project, switch it to joint fitting, print one JSON line
//   scan-screen       open the cooling scan in the normal window, fit it and record what each frame
//                     drew; SCAN_SCREEN_MODE, SCAN_SCREEN_SETTINGS_ONLY, SCAN_SCREEN_SETTINGS_FILE,
//                     SCAN_SCREEN_OUTPUT and SCAN_SCREEN_FORCE_HIDE steer it
//
// Returns the exit code when main should stop (a refusal, or an action without a window), or nothing
// when main should go on to show the window.
std::optional<int> start_test_observer(const QStringList& arguments);
// The same refusal of an observer request outside a system test, read from argv before the
// application starts, so it names the request on any platform the app would refuse to start on.
std::optional<int> refuse_test_observer(int argc, char* argv[]);
// Called after configure_engine and after the QML load; they do nothing unless an observer with a
// window was started.
void configure_test_observer(QQmlApplicationEngine& engine);
void install_test_observer(QQmlApplicationEngine& engine);

enum class WorkReportBoundary { BeforeGrowth, AfterGrowth, Frozen, WriterHandoff,
    BeforeEncode, AfterEncode, Terminal, Released };
enum class WorkReportOwnerRole { OriginalNative, OriginalItems, OriginalProgress,
    OriginalTransport, PrimaryHistory, SupplementaryRow, FrozenExport, Encoding,
    WriterScratch, WorkerCapture, QueuedCallback, Receipt, ObserverScratch };
enum class WorkReportOwnerGroup { OriginalLive, ReportCurrent, ReportRetired, Observer };
struct WorkReportOwnerTag { WorkReportOwnerGroup group; QStringView owner_instance_id; const void* shared_backing; };
struct WorkReportBytesView { WorkReportOwnerRole role; WorkReportOwnerTag tag; const QByteArray* owner; };
struct WorkReportTextView { WorkReportOwnerRole role; WorkReportOwnerTag tag; const QString* owner; };
struct WorkReportJsonView { WorkReportOwnerRole role; WorkReportOwnerTag tag; const QJsonValue* owner; };
struct WorkReportContainerView { WorkReportOwnerRole role; WorkReportOwnerTag tag; const void* backing;
    quint64 size,capacity,element_size; };
struct WorkReportTestView {
    WorkReportBoundary boundary; QStringView scope_id,receipt_id;
    quint64 aggregate_limit,original_reserved,report_reserved,requested_growth;
    std::span<const WorkReportBytesView> bytes;
    std::span<const WorkReportTextView> texts;
    std::span<const WorkReportJsonView> json;
    std::span<const WorkReportContainerView> containers;
};
void observe_work_report_boundary(const WorkReportTestView&) noexcept;
QVariantMap work_report_test_observation();
enum class WorkReportFaultPoint { StageWrite, BeforeAtomicPublish, AfterAtomicPublishReadback, OldCandidateCleanup };
bool work_report_test_fault(WorkReportFaultPoint) noexcept;
}  // namespace edi_app

#endif  // EDI_APP_TEST_OBSERVER_HPP
