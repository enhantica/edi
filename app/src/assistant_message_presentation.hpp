// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonObject>
#include <QMetaType>
#include <QString>
#include <QStringList>
#include <optional>

namespace edi_app::assistant_presentation {
// Original lightweight display fields only; never canonical history/detail JSON.
struct ActivityInput {
    QString kind, rowStatus, type, commandCategory, payloadStatus, nativeOutcomeStatus;
    bool decisionIsString = false, itemIdIsString = false;
    std::optional<QString> nativeLabel;
};
struct ActivityPresentation {
    QString caption, state, explanation, outcomeKey, nativeCaption;
    bool commandActivity = false, decisionActivity = false, summarizedActivity = false;
};
inline QString messageText(const char* source) {
    // Keep the source QML context, rather than translating under AppInfo/AVM.
    return QCoreApplication::translate("AssistantMessage", source);
}
inline ActivityPresentation presentActivity(const ActivityInput& in) {
    ActivityPresentation out;
    out.commandActivity = in.kind == "activity" && in.type == "commandExecution";
    out.decisionActivity = in.kind == "activity" && in.decisionIsString && in.itemIdIsString;
    out.summarizedActivity = out.decisionActivity || (in.kind == "activity" &&
        (in.type == "commandExecution" || in.type == "fileChange" || in.type == "webSearch" ||
         in.type == "mcpToolCall" || in.type == "dynamicToolCall" ||
         in.type == "collabAgentToolCall" || in.type == "plan" || in.type == "ediOutcome"));
    out.nativeCaption = in.nativeLabel ? *in.nativeLabel : messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Work on the current project"));
    if (in.kind == "error") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Assistant error"));
    else if (in.kind == "plan") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Review work plan"));
    else if (in.kind == "question") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Assistant question"));
    else if (in.kind == "tool") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Project action"));
    else if (in.kind == "trial") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Review refinement trial"));
    else if (out.decisionActivity) out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Review requested action"));
    else if (out.commandActivity) {
        if (in.commandCategory == "read") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Read files"));
        else if (in.commandCategory == "listFiles") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Listed files"));
        else if (in.commandCategory == "search") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Searched files"));
        else out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Ran command"));
    } else if (in.type == "dynamicToolCall") out.caption = out.nativeCaption;
    else if (in.type == "fileChange") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Update files"));
    else if (in.type == "webSearch") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Search the web"));
    else if (in.type == "mcpToolCall") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Use external tool"));
    else if (in.type == "collabAgentToolCall") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Coordinate assistant task"));
    else if (in.type == "plan") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Update work plan"));
    else if (in.type == "ediOutcome") out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Report project action"));
    else out.caption = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Perform assistant action"));

    if (out.commandActivity) {
        const bool settled = in.payloadStatus == "completed" || in.payloadStatus == "failed" ||
            in.payloadStatus == "declined" || in.payloadStatus == "interrupted";
        if (settled && in.rowStatus == in.payloadStatus) out.state = in.payloadStatus;
        else out.state = in.payloadStatus == "inProgress" && in.rowStatus == "in_progress"
            ? QStringLiteral("in_progress") : QStringLiteral("unconfirmed");
    } else if (in.nativeOutcomeStatus == "unconfirmed" || in.nativeOutcomeStatus == "applied_unconfirmed")
        out.state = QStringLiteral("unconfirmed");
    else if (in.rowStatus == "completed" || in.rowStatus == "failed" || in.rowStatus == "refused" ||
             in.rowStatus == "declined" || in.rowStatus == "interrupted" || in.rowStatus == "in_progress")
        out.state = in.rowStatus;
    else out.state = QStringLiteral("unconfirmed");

    // Native explanation precedence also applies to a command's corroborated state.
    if (in.nativeOutcomeStatus == "applied_unconfirmed")
        out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Changes were made, but completion could not be confirmed."));
    else if (in.nativeOutcomeStatus == "unconfirmed" || out.state == "unconfirmed")
        out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "The result could not be confirmed. Inspect the project before continuing."));
    else if (out.state == "completed") out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Completed"));
    else if (out.state == "failed") out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Failed"));
    else if (out.state == "refused") out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Refused"));
    else if (out.state == "declined") out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Declined"));
    else if (out.state == "interrupted") out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Stopped"));
    else if (out.state == "in_progress") out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "In progress"));
    else out.explanation = messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Result unavailable"));
    out.outcomeKey = out.state == "completed" ? QStringLiteral("success")
        : out.state == "failed" ? QStringLiteral("failed")
        : out.state == "refused" || out.state == "declined" ? QStringLiteral("refused")
        : out.state == "interrupted" ? QStringLiteral("stopped") : QStringLiteral("notConverged");
    return out;
}

// Qt6.11.2's positive Yarr \s population, separate from its edge-trim owner below.
// Work in UTF-16 units as the original UI did; all non-whitespace units stay literal.
inline bool isMessageWhitespace(QChar value) {
    const auto code = value.unicode();
    return (code >= 0x0009 && code <= 0x000d) || code == 0x0020 || code == 0x00a0 ||
        code == 0x1680 || (code >= 0x2000 && code <= 0x200a) || code == 0x2028 ||
        code == 0x2029 || code == 0x202f || code == 0x205f || code == 0x3000 || code == 0xfeff;
}
inline bool isMessageTrimWhitespace(QChar value) {
    // The original Qt String.prototype.trim: QChar::isSpace plus FEFF at the edges.
    return value.isSpace() || value.unicode() == 0xfeff;
}
inline QString singleLineText(const QString& value) {
    qsizetype first = 0, last = value.size();
    while (first < last && isMessageTrimWhitespace(value.at(first))) ++first;
    while (last > first && isMessageTrimWhitespace(value.at(last - 1))) --last;
    QString out;
    out.reserve(last - first);
    bool space = false;
    for (qsizetype i = first; i < last; ++i) {
        const QChar unit = value.at(i);
        if (isMessageWhitespace(unit)) {
            space = !out.isEmpty();
            continue;
        }
        if (space) out.append(QLatin1Char(' '));
        out.append(unit);
        space = false;
    }
    return out;
}

enum class WebActionKind { Missing, Invalid, Search, OpenPage, FindInPage, Other };
struct WebActionInput {
    WebActionKind kind = WebActionKind::Missing;
    QString query, fallbackQuery, url, pattern;
    bool queriesPresent = false;
    std::optional<QStringList> queries;
};
// Empty is a valid query needing the payload fallback; nullopt is an invalid query list.
inline std::optional<QString> webSearchQuery(const WebActionInput& in) {
    if (in.kind == WebActionKind::Missing) return QString();
    if (in.kind != WebActionKind::Search) return std::nullopt;
    const QString query = singleLineText(in.query);
    if (!query.isEmpty()) return query;
    if (!in.queriesPresent) return QString();
    if (!in.queries) return std::nullopt;
    QStringList nonempty;
    for (const QString& value : *in.queries) {
        const QString normalized = singleLineText(value);
        if (!normalized.isEmpty()) nonempty.append(normalized);
    }
    return nonempty.join(QStringLiteral(" · "));
}
inline QString presentWebSearch(const WebActionInput& in) {
    if (in.kind == WebActionKind::Missing || in.kind == WebActionKind::Search) {
        const auto query = webSearchQuery(in);
        if (!query) return {};
        const QString selected = query->isEmpty() ? singleLineText(in.fallbackQuery) : *query;
        return selected.isEmpty() ? QString() :
            messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Search the web for %1")).arg(selected);
    }
    const QString url = singleLineText(in.url);
    if (in.kind == WebActionKind::OpenPage)
        return url.isEmpty() ? QString() :
            messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Open web page %1")).arg(url);
    if (in.kind == WebActionKind::FindInPage) {
        const QString pattern = singleLineText(in.pattern);
        if (!url.isEmpty() && !pattern.isEmpty())
            return messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Find %1 on %2")).arg(pattern).arg(url);
        if (!pattern.isEmpty())
            return messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Find %1 on a web page")).arg(pattern);
        if (!url.isEmpty())
            return messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Find text on %1")).arg(url);
    }
    return {};
}

inline bool nonblankLiteral(const QString& value) {
    for (const QChar unit : value) if (!isMessageTrimWhitespace(unit)) return true;
    return false;
}
// Opaque value metadata preserves the native carrier through QVariant-based QML calls.
struct HumanActivitySnapshot {
    Q_GADGET
public:
    QJsonObject payload;
    QString text, provenance;
    QString rowId, kind, status;
};
struct HumanActivityInput {
    QString kind, caption, text, provenance;
    QJsonObject payload;
    bool commandActivity = false, decisionActivity = false;
    std::optional<QString> nativeLabel, nativeDescription, nativeErrorDescription;
};
inline QString suppliedDescription(const QJsonObject& payload) {
    for (const auto* field : {"purpose", "description"})
        if (payload.value(field).isString()) return payload.value(field).toString();
    return payload.value("arguments").toObject().value("purpose").toString();
}
inline bool nativeDescriptionPlaceholder(const HumanActivityInput& in) {
    const auto supplied = suppliedDescription(in.payload);
    return in.payload.value("type") == "dynamicToolCall" &&
        (supplied == "Edi native action" || supplied == QStringLiteral("Edi native action: ") + (in.payload.value("tool").isUndefined() ? QStringLiteral("undefined") : in.payload.value("tool").toString()));
}
inline QString humanWebCaption(const QJsonObject& payload) {
    WebActionInput input;
    const auto value = payload.value("action");
    if (!value.isUndefined() && !value.isNull()) {
        if (!value.isObject()) return {};
        const auto action = value.toObject();
        const auto type = action.value("type");
        input.kind = type == "search" ? WebActionKind::Search : type == "openPage" ? WebActionKind::OpenPage :
            type == "findInPage" ? WebActionKind::FindInPage : WebActionKind::Other;
        input.query = action.value("query").toString();
        input.url = action.value("url").toString();
        input.pattern = action.value("pattern").toString();
        const auto queries = action.value("queries");
        input.queriesPresent = !queries.isUndefined() && !queries.isNull();
        if (queries.isArray()) {
            QStringList strings;
            for (const auto& query : queries.toArray()) {
                if (!query.isString()) return {};
                strings.append(query.toString());
            }
            input.queries = std::move(strings);
        }
    }
    input.fallbackQuery = payload.value("query").toString();
    return presentWebSearch(input);
}
inline QString activityHumanDescription(const HumanActivityInput& in) {
    if (nativeDescriptionPlaceholder(in)) return in.nativeLabel.value_or(presentActivity({}).nativeCaption);
    const auto supplied = suppliedDescription(in.payload);
    if (nonblankLiteral(supplied)) return supplied;
    if (in.payload.value("type") == "webSearch") return humanWebCaption(in.payload);
    return in.commandActivity ? in.payload.value("commandDescription").toString() : QString();
}
inline bool humanTextProducer(const HumanActivityInput& in) {
    return in.kind == "error" || in.kind == "plan" || in.kind == "question" || in.kind == "tool" || in.kind == "trial" ||
        (in.decisionActivity && in.payload.value("type").isUndefined());
}
inline void appendHumanLine(QStringList& lines, const QString& value) {
    if (nonblankLiteral(value) && !lines.contains(value)) lines.append(value);
}
inline QStringList humanDescriptionLines(const HumanActivityInput& in) {
    QStringList lines;
    const auto description = activityHumanDescription(in);
    if (nonblankLiteral(description) && singleLineText(description) != in.caption) appendHumanLine(lines, description);
    if (humanTextProducer(in) && singleLineText(in.text) != in.caption) appendHumanLine(lines, in.text);
    return lines;
}
inline bool needsHumanFallback(const HumanActivityInput& in, const QStringList& lines) {
    for (const auto& line : lines) if (singleLineText(line).size() > in.caption.size()) return false;
    return true;
}
inline QString humanOutcomeMessage(const HumanActivityInput& in) {
    const auto outcome = in.payload.value("nativeOutcome").toObject();
    if (outcome.value("message").isString()) return outcome.value("message").toString();
    return in.payload.value("error").toObject().value("message").toString();
}
inline QString humanOutcomeCode(const HumanActivityInput& in) {
    const auto outcome = in.payload.value("nativeOutcome").toObject();
    for (const auto* field : {"action_error", "code"})
        if (outcome.value(field).isString()) return outcome.value(field).toString();
    return in.payload.value("code").toString();
}
inline QString fullHumanDescription(const HumanActivityInput& in, QStringList lines) {
    if (needsHumanFallback(in, lines)) {
        if (in.payload.value("type") == "dynamicToolCall" && in.nativeDescription) appendHumanLine(lines, *in.nativeDescription);
        else if (in.payload.value("type") == "webSearch")
            appendHumanLine(lines, messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Find or read public sources relevant to the current task.")));
        else if (in.commandActivity)
            appendHumanLine(lines, messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Use the reported operation to support the current task.")));
        else appendHumanLine(lines, messageText(QT_TRANSLATE_NOOP("AssistantMessage", "Carry out the requested assistant action for the current task.")));
    }
    appendHumanLine(lines, in.provenance);
    const auto message = humanOutcomeMessage(in);
    appendHumanLine(lines, message);
    if (humanTextProducer(in)) appendHumanLine(lines, in.payload.value("message").toString());
    if (!nonblankLiteral(message) && humanOutcomeCode(in) == "project_required" && in.nativeErrorDescription)
        appendHumanLine(lines, *in.nativeErrorDescription);
    return lines.join(QLatin1Char('\n'));
}
inline QString humanCopyText(const QString& caption, const QString& full) {
    return caption == full ? full : caption + QLatin1Char('\n') + full;
}
} // namespace edi_app::assistant_presentation


Q_DECLARE_METATYPE(edi_app::assistant_presentation::HumanActivitySnapshot)
