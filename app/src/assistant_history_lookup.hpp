// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QString>

namespace edi_app::detail {
// Internal, non-owning acceleration for ONE synchronous history publication.
// The original array must remain unchanged until both lookup consumers finish.
// This finds the original first equality match; it grants no row/native authority.
class FirstHistoryRowLookup final {
 public:
    explicit FirstHistoryRowLookup(const QJsonArray& original, bool indexStrings = true)
        : original_(original) {
        if (!indexStrings) return; // Empty prospective publication needs no index.
        try {
            for (qsizetype i = 0; i < original_.size(); ++i) {
                const auto id = original_.at(i).toObject().value("id");
                if (id.isString()) {
                    const auto text = id.toString();
                    if (!first_string_.contains(text)) first_string_.insert(text, i);
                }
            }
            indexed_ = true;
        } catch (...) {
            // Optional allocation cannot become another publication precondition.
            first_string_.clear();
        }
    }
    FirstHistoryRowLookup(QJsonArray&&, bool = true) = delete;
    FirstHistoryRowLookup(const QJsonArray&&, bool = true) = delete;
    FirstHistoryRowLookup(const FirstHistoryRowLookup&) = delete;
    FirstHistoryRowLookup& operator=(const FirstHistoryRowLookup&) = delete;
    FirstHistoryRowLookup(FirstHistoryRowLookup&&) = delete;
    FirstHistoryRowLookup& operator=(FirstHistoryRowLookup&&) = delete;

    qsizetype first(const QJsonValue& id) const {
        if (indexed_ && id.isString()) {
            const auto found = first_string_.constFind(id.toString());
            return found == first_string_.cend() ? qsizetype(-1) : found.value();
        }
        // Preserve arbitrary/missing/typed IDs without string coercion.
        for (qsizetype i = 0; i < original_.size(); ++i)
            if (original_.at(i).toObject().value("id") == id) return i;
        return -1;
    }
 private:
    const QJsonArray& original_;
    QHash<QString, qsizetype> first_string_;
    bool indexed_ = false;
};
} // namespace edi_app::detail
