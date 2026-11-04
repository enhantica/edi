// SPDX-License-Identifier: BSD-3-Clause
#pragma once
// The assistant's fixed-shape values as QML reads them, typed (ADR-0015 §2). Each keeps the field names the panel
// already used; an empty value stands for "none" (no pending question, no plan, no known account).
#include <QJsonArray>
#include <QJsonObject>
#include <QList>
#include <QMetaType>
#include <QObject>
#include <QPointer>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <memory>

namespace edi_app {

struct ManualControlGesture;

// The proof that a manual press began on a control (beginManualControlInput), handed back to its completion. Only
// that completion reads it.
struct AssistantManualControlToken {
    Q_GADGET
    QML_VALUE_TYPE(manualControlToken)
    Q_PROPERTY(bool valid READ valid CONSTANT)

   public:
    std::shared_ptr<ManualControlGesture> gesture;
    bool valid() const { return gesture != nullptr; }
    bool operator==(const AssistantManualControlToken& other) const { return gesture == other.gesture; }
};

// What submitting a draft did: its `status` ("admitted", "waiting" or "unconfirmed") and the new row's id.
struct AssistantDraftAdmission {
    Q_GADGET
    QML_VALUE_TYPE(draftAdmission)
    Q_PROPERTY(QString status MEMBER status CONSTANT)
    Q_PROPERTY(QString row_id MEMBER row_id CONSTANT)

   public:
    QString status, row_id;
    bool operator==(const AssistantDraftAdmission&) const = default;
};

struct AssistantQuestionOption {
    Q_GADGET
    QML_VALUE_TYPE(questionOption)
    Q_PROPERTY(QString id MEMBER id CONSTANT)
    Q_PROPERTY(QString label MEMBER label CONSTANT)
    Q_PROPERTY(QString description MEMBER description CONSTANT)

   public:
    QString id, label, description;
    bool operator==(const AssistantQuestionOption&) const = default;
};

// The question the assistant waits on; no `question_id` when there is none.
struct AssistantPendingQuestion {
    Q_GADGET
    QML_VALUE_TYPE(pendingQuestion)
    Q_PROPERTY(QString question_id MEMBER question_id CONSTANT)
    Q_PROPERTY(QString text MEMBER text CONSTANT)
    Q_PROPERTY(QList<edi_app::AssistantQuestionOption> options MEMBER options CONSTANT)
    Q_PROPERTY(QString recommended MEMBER recommended CONSTANT)
    Q_PROPERTY(bool allow_free_text MEMBER allow_free_text CONSTANT)
    Q_PROPERTY(QString draftText MEMBER draftText CONSTANT)

   public:
    QString question_id, text, recommended, draftText;
    QList<AssistantQuestionOption> options;
    bool allow_free_text = false;
    bool operator==(const AssistantPendingQuestion&) const = default;

    static AssistantPendingQuestion fromJson(const QJsonObject& source) {
        AssistantPendingQuestion question;
        question.question_id = source.value("question_id").toString();
        question.text = source.value("text").toString();
        question.recommended = source.value("recommended").toString();
        question.draftText = source.value("draftText").toString();
        question.allow_free_text = source.value("allow_free_text").toBool();
        for (const auto& value : source.value("options").toArray()) {
            const auto option = value.toObject();
            question.options.append({option.value("id").toString(), option.value("label").toString(),
                                     option.value("description").toString()});
        }
        return question;
    }
};

struct AssistantPlanGroup {
    Q_GADGET
    QML_VALUE_TYPE(planGroup)
    Q_PROPERTY(QString id MEMBER id CONSTANT)
    Q_PROPERTY(QStringList paths MEMBER paths CONSTANT)

   public:
    QString id;
    QStringList paths;
    bool operator==(const AssistantPlanGroup&) const = default;
};

// A plan's budget; `defined` is false when the plan states none.
struct AssistantPlanBudget {
    Q_GADGET
    QML_VALUE_TYPE(planBudget)
    Q_PROPERTY(bool defined MEMBER defined CONSTANT)
    Q_PROPERTY(double max_trials MEMBER max_trials CONSTANT)
    Q_PROPERTY(double max_iterations MEMBER max_iterations CONSTANT)
    Q_PROPERTY(double max_elapsed_ms MEMBER max_elapsed_ms CONSTANT)

   public:
    bool defined = false;
    double max_trials = 0, max_iterations = 0, max_elapsed_ms = 0;
    bool operator==(const AssistantPlanBudget&) const = default;
};

struct AssistantPlanObjective {
    Q_GADGET
    QML_VALUE_TYPE(planObjective)
    Q_PROPERTY(double absolute_tolerance MEMBER absolute_tolerance CONSTANT)
    Q_PROPERTY(double relative_tolerance MEMBER relative_tolerance CONSTANT)

   public:
    double absolute_tolerance = 0, relative_tolerance = 0;
    bool operator==(const AssistantPlanObjective&) const = default;
};

// The plan waiting for approval; no `plan_id` when there is none.
struct AssistantPendingPlan {
    Q_GADGET
    QML_VALUE_TYPE(pendingPlan)
    Q_PROPERTY(QString plan_id MEMBER plan_id CONSTANT)
    Q_PROPERTY(QString summary MEMBER summary CONSTANT)
    Q_PROPERTY(QList<edi_app::AssistantPlanGroup> groups MEMBER groups CONSTANT)
    Q_PROPERTY(edi_app::AssistantPlanBudget budget MEMBER budget CONSTANT)
    Q_PROPERTY(edi_app::AssistantPlanObjective objective MEMBER objective CONSTANT)

   public:
    QString plan_id, summary;
    QList<AssistantPlanGroup> groups;
    AssistantPlanBudget budget;
    AssistantPlanObjective objective;
    bool operator==(const AssistantPendingPlan&) const = default;

    static AssistantPendingPlan fromJson(const QJsonObject& source) {
        AssistantPendingPlan plan;
        plan.plan_id = source.value("plan_id").toString();
        plan.summary = source.value("summary").toString();
        for (const auto& value : source.value("groups").toArray()) {
            const auto group = value.toObject();
            QStringList paths;
            for (const auto& path : group.value("paths").toArray()) paths.append(path.toString());
            plan.groups.append({group.value("id").toString(), paths});
        }
        if (source.value("budget").isObject()) {
            const auto budget = source.value("budget").toObject();
            plan.budget = {true, budget.value("max_trials").toDouble(), budget.value("max_iterations").toDouble(),
                           budget.value("max_elapsed_ms").toDouble()};
        }
        const auto objective = source.value("objective").toObject();
        plan.objective = {objective.value("absolute_tolerance").toDouble(),
                          objective.value("relative_tolerance").toDouble()};
        return plan;
    }
};

// The signed-in account the runtime reports; empty when none is known.
struct AssistantAccount {
    Q_GADGET
    QML_VALUE_TYPE(assistantAccount)
    Q_PROPERTY(QString email MEMBER email CONSTANT)
    Q_PROPERTY(QString planType MEMBER planType CONSTANT)

   public:
    QString email, planType;
    bool operator==(const AssistantAccount&) const = default;

    static AssistantAccount fromJson(const QJsonObject& source) {
        return {source.value("email").toString(), source.value("planType").toString()};
    }
};

// What creating a project did (Session::createProjectWithOutcome), and the project and replacement it was made against,
// so a later step can tell whether that creation is still the current one.
struct ProjectCreationResult {
    Q_GADGET
    QML_VALUE_TYPE(projectCreationResult)
    Q_PROPERTY(bool success MEMBER success CONSTANT)
    Q_PROPERTY(bool current MEMBER current CONSTANT)
    Q_PROPERTY(QString error MEMBER error CONSTANT)
    Q_PROPERTY(bool saved MEMBER saved CONSTANT)
    Q_PROPERTY(QString path MEMBER path CONSTANT)
    Q_PROPERTY(QObject* owner READ ownerObject CONSTANT)
    Q_PROPERTY(bool has_owner MEMBER has_owner CONSTANT)
    Q_PROPERTY(QString replacement MEMBER replacement CONSTANT)

   public:
    bool success = false, current = false, saved = false, has_owner = false;
    QString error, path, replacement;
    QPointer<QObject> owner;
    QObject* ownerObject() const { return owner.data(); }
    bool operator==(const ProjectCreationResult& other) const {
        return success == other.success && current == other.current && saved == other.saved && has_owner == other.has_owner &&
               error == other.error && path == other.path && replacement == other.replacement && owner == other.owner;
    }
};

}  // namespace edi_app
