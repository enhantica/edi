// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "assistant_message_presentation.hpp"
#include <QJsonArray>
#include <QJsonObject>
#include <QList>
#include <QSet>
#include <QString>

namespace edi_app::assistant_presentation {
// A step of the assistant that is done and went well. A pending, failed, refused or unconfirmed one, a question, a plan
// and an answered request stay rows of their own.
inline bool finishedStep(const QJsonObject& row) {
    if (row.value("kind") != "activity" || row.value("status") != "completed") return false;
    const auto payload = row.value("payload").toObject();
    const auto type = payload.value("type").toString();
    if (payload.value("decision").isString() || (type != "commandExecution" && type != "fileChange" && type != "webSearch" &&
        type != "mcpToolCall" && type != "dynamicToolCall" && type != "collabAgentToolCall")) return false;
    if (type == "commandExecution" && payload.value("status") != "completed") return false;
    const auto outcome = payload.value("nativeOutcome").toObject().value("status").toString();
    return outcome != "refused" && outcome != "failed" && outcome != "unconfirmed" && outcome != "applied_unconfirmed" && outcome != "partial";
}
// The rows the conversation shows: every run of two or more finished steps is one "steps" row, followed by its steps
// while its group (the run's first step) is in `open`. `finished` says which rows are finished steps. A closed row
// takes the id of its last step, so a notice shown after that step stays there.
inline QJsonArray foldSteps(const QJsonArray& rows, const QList<bool>& finished, const QSet<QString>& open) {
    QJsonArray shown;
    for (qsizetype i = 0; i < rows.size();) {
        auto end = i;
        while (end < rows.size() && finished.value(end)) ++end;
        if (end - i < 2) {
            shown.append(rows.at(i++));
            continue;
        }
        const auto first = rows.at(i).toObject();
        const auto group = first.value("id").toString();
        const bool unfolded = open.contains(group);
        // Each kind of step's icon once, in the order the kinds first appear (owner, 2026-11-28); every folded step
        // went well, so today that is one check. The count names how many steps there are.
        QJsonArray icons;
        for (auto step = i; step < end; ++step)
            if (const QJsonValue key = QStringLiteral("success"); !icons.contains(key)) icons.append(key);
        shown.append(QJsonObject{{"id", unfolded ? QString(QStringLiteral("steps/") + group) : rows.at(end - 1).toObject().value("id").toString()},
            {"kind", "steps"}, {"status", "completed"}, {"text", ""}, {"number", first.value("number")},
            {"payload", QJsonObject{{"type", "ediSteps"}, {"group", group}, {"open", unfolded}, {"icons", icons},
                                    {"count", static_cast<int>(end - i)}}}});
        if (unfolded) for (auto step = i; step < end; ++step) shown.append(rows.at(step));
        i = end;
    }
    return shown;
}
} // namespace edi_app::assistant_presentation
