// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QString>

// A dictionary name shown as a field label or column header: crysta writes most names in lower case ("sample form",
// "min"), and every app label starts with a capital. A first word whose case is part of its meaning stays as written:
// a one-letter symbol (b, d, h, x), anything with a digit, dot, capital or non-ASCII letter (s.u., cRp, χ², λ), and sin.
inline QString label_case(const QString& name) {
    qsizetype end = 0;
    while (end < name.size() && name[end] != u' ' && name[end] != u'(') ++end;
    const QString word = name.left(end);
    if (word == QStringLiteral("id")) return QStringLiteral("ID") + name.mid(end);
    if (word.size() < 2 || word == QStringLiteral("sin")) return name;
    for (const QChar c : word) {
        if (!(c >= u'a' && c <= u'z') && c != u'-') return name;
    }
    return name.left(1).toUpper() + name.mid(1);
}
