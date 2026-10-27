// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QObject>
#include <QJsonArray>
#include <QJsonObject>
#include <QVariantMap>
#include <QString>
#include <QAnyStringView>
#include <cstdint>
#include <functional>
#include <memory>

namespace edi_app {
class AssistantViewModel;
// Immutable native launch configuration; no provider or mutable test fields.
struct AssistantWorkReportOptions { bool automatic = true; };

bool work_report_next_serial(std::uint64_t current, std::uint64_t& next) noexcept;
const QJsonObject& work_report_serial_refusal();
const QVariantMap& work_report_serial_variant();
const QVariantMap& work_report_capacity_variant();
QJsonObject work_report_missing(const char* reason = "not_observed");
QJsonObject work_report_observed(const QJsonValue& value, const char* source = "native", const QString& row = {});
QJsonObject work_report_receipt_coverage(const QString& reason = QStringLiteral("none"));
QJsonObject work_report_empty_document();

struct AssistantWorkReportCoverage { bool known=false; quint64 retained=0,excluded=0; };

struct AssistantWorkReportSnapshot {
    QJsonObject document;
    QString scope;
    quint64 revision = 0;
};

// One local file writer. This is not a provider/controller or scientific actor.
// The build callback is synchronous and must perform original-owner checks and
// bound the actual encoded artifact before handing it to the writer.
class AssistantWorkReports final {
public:
    explicit AssistantWorkReports(AssistantWorkReportOptions, AssistantViewModel* owner) noexcept;
    ~AssistantWorkReports();
    void closeOwner() noexcept;
    bool tryInitialize() noexcept;
    std::shared_ptr<const void> releaseOwner() const noexcept;
    bool available() const noexcept;
    bool automatic() const noexcept;
    bool collecting() const noexcept;
    void enableManualCollection() noexcept;
    const QString& scope() const noexcept;
    quint64 revision() const noexcept;
    bool exhausted() const noexcept;
    void changed() noexcept;
    void retireScope() noexcept;
    // Retire only live storage identity; retain conversation evidence/attempt.
    bool bindStorageRoot(QStringView) noexcept;
    void missEvidence() noexcept;
    void missedAutomaticCapture() noexcept;
    quint64 missedAutomaticCaptures() const noexcept;
    bool coverageUnknown() const noexcept;
    bool ownsScope(QAnyStringView) const noexcept;
    QJsonObject stamp(const QString& attempt = {}) const;
    QString newEvent();
    QString beginAttempt();
    const QString& attempt() const noexcept;
    QVariantMap receipt() const;
    // An exhausted ID has no fabricated correlation token. No accepted worker
    // or artifact can originate from that immediate refusal.
    QVariantMap capture(bool automaticTrigger, AssistantWorkReportCoverage counts,QStringView storageRoot,
        const std::function<AssistantWorkReportSnapshot(quint64)>& build,const QString& expectedScope,quint64 expectedRevision,bool projectionBlocked);
    bool artifactCurrent(const QJsonObject&,QStringView storageRoot) const noexcept;
private:
    struct Control;
    const AssistantWorkReportOptions options_;
    AssistantViewModel* const owner_;
    bool collection_requested_=false,unavailable_evidence_=false;
    std::uint64_t unavailable_captures_=0;
    std::shared_ptr<Control> control_;
    static void settleCompletion(const std::shared_ptr<Control>&) noexcept;
    void present(const QJsonObject&,const QVariantMap&);
    QVariantMap immediate(const QJsonObject&);
};
} // namespace edi_app
