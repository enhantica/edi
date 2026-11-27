// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

// One row of the label registry (app/data/labels.tsv): a label's long form, a shorter one for a narrow place and a
// Font Awesome icon, the last two empty where there is none.
struct LabelForms {
    QString long_text;
    QString short_text;
    QString icon;
};

// A label's forms as QML reads them (Session.labelForms): the long form, the short one and the icon, each empty where
// there is none; all empty for a key without a label.
struct ShownLabel {
    Q_GADGET
    QML_VALUE_TYPE(shownLabel)
    Q_PROPERTY(QString longText MEMBER longText CONSTANT)
    Q_PROPERTY(QString shortText MEMBER shortText CONSTANT)
    Q_PROPERTY(QString icon MEMBER icon CONSTANT)

   public:
    QString longText;
    QString shortText;
    QString icon;
    bool operator==(const ShownLabel&) const = default;
};

// The row for `key` (an item's `category.name`, a variant's `uid@token`, an option's `uid=token`, a category's id, or a
// control's objectName), or nullptr. The table is read from the app's resources once.
const LabelForms* find_label_forms(const QString& key);
