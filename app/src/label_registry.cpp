// SPDX-License-Identifier: BSD-3-Clause
#include "label_registry.hpp"

#include <QFile>
#include <QHash>
#include <QLoggingCategory>
#include <QStringList>

namespace {

Q_LOGGING_CATEGORY(lcLabels, "edi.labels")

QHash<QString, LabelForms> read_registry() {
    QHash<QString, LabelForms> rows;
    QFile file(QStringLiteral(":/edi/labels.tsv"));
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qCWarning(lcLabels, "the label registry could not be read");
        return rows;
    }
    const QStringList lines = QString::fromUtf8(file.readAll()).split(QLatin1Char('\n'));
    // The first line names the columns.
    for (qsizetype i = 1; i < lines.size(); ++i) {
        if (lines[i].isEmpty()) continue;
        const QStringList cells = lines[i].split(QLatin1Char('\t'));
        if (cells.size() != 4) {
            qCWarning(lcLabels, "labels.tsv line %lld has %lld cells, not 4", static_cast<long long>(i + 1),
                      static_cast<long long>(cells.size()));
            continue;
        }
        rows.insert(cells[0], {cells[1], cells[2], cells[3]});
    }
    return rows;
}

}  // namespace

const LabelForms* find_label_forms(const QString& key) {
    static const QHash<QString, LabelForms> rows = read_registry();
    const auto found = rows.constFind(key);
    return found == rows.constEnd() ? nullptr : &found.value();
}
