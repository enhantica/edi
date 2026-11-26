// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QString>

// One row of the label registry (app/data/labels.tsv): a label's long form, a shorter one for a narrow place and a
// Font Awesome icon, the last two empty where there is none.
struct LabelForms {
    QString long_text;
    QString short_text;
    QString icon;
};

// The row for `key` (an item's `category.name`, a variant's `uid@token`, an option's `uid=token`, a category's id, or a
// control's objectName), or nullptr. The table is read from the app's resources once.
const LabelForms* find_label_forms(const QString& key);
