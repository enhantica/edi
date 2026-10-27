// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_GENERATED_CATEGORY_HPP
#define EDI_APP_GENERATED_CATEGORY_HPP

#include <QObject>
#include <QPointer>
#include <QStringList>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>

#include "block_text.hpp"

namespace edi_app {

// A category no designed group shows, as a block's text holds it, for the group the app makes from the dictionary
// (edi ADR-0017 §3): its items' labels and units from the dictionary, its values as written, and an edit of one
// value as the block's text with it, which the Text tab's apply reads (ProjectViewModel::applyText).
class GeneratedCategory : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::BlockText* source READ source WRITE setSource NOTIFY sourceChanged)
    Q_PROPERTY(QString categoryId READ categoryId WRITE setCategoryId NOTIFY categoryIdChanged)
    Q_PROPERTY(bool loop READ loop NOTIFY changed)
    // What the program or a data file supplies is shown, never edited.
    Q_PROPERTY(bool output READ output NOTIFY changed)
    Q_PROPERTY(QStringList names READ names NOTIFY changed)
    Q_PROPERTY(QStringList labels READ labels NOTIFY changed)
    Q_PROPERTY(QStringList units READ units NOTIFY changed)
    // A list of rows, each a list of values in the order of `names`.
    Q_PROPERTY(QVariantList rows READ rows NOTIFY changed)

   public:
    explicit GeneratedCategory(QObject* parent = nullptr);

    BlockText* source() const { return source_; }
    void setSource(BlockText* source);
    QString categoryId() const { return id_; }
    void setCategoryId(const QString& id);
    bool loop() const { return loop_; }
    bool output() const { return output_; }
    QStringList names() const { return names_; }
    QStringList labels() const { return labels_; }
    QStringList units() const { return units_; }
    QVariantList rows() const { return rows_; }

    // The block's text with one value replaced.
    Q_INVOKABLE QString editedText(int row, const QString& name, const QString& value) const;

   signals:
    void sourceChanged();
    void categoryIdChanged();
    void changed();

   private:
    void read();

    QPointer<BlockText> source_;
    QString id_;
    bool loop_ = false;
    bool output_ = false;
    QStringList names_, labels_, units_;
    QVariantList rows_;
};

}  // namespace edi_app

#endif  // EDI_APP_GENERATED_CATEGORY_HPP
