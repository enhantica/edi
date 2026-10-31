// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_GENERATED_CATEGORY_HPP
#define EDI_APP_GENERATED_CATEGORY_HPP

#include <QAbstractListModel>
#include <QObject>
#include <QPointer>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

#include "block_text.hpp"
#include "option_list_model.hpp"

namespace edi_app {

// A generated category's rows, each its values as written in the order of the category's names (`values`).
class GeneratedRows : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("A GeneratedCategory holds its rows")

   public:
    explicit GeneratedRows(QObject* parent = nullptr) : QAbstractListModel(parent) {}
    void setRows(QList<QStringList> rows);
    QString value(int row, int column) const { return rows_.value(row).value(column); }
    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

   private:
    QList<QStringList> rows_;
};

// A category no designed group shows, as a block's text holds it, for the group the app makes from the dictionary
// (edi ADR-0017 §3): its items' labels and units from the dictionary, its values as written, and an edit of one
// value as the block's text with it, which the Text tab's apply reads (ProjectViewModel::applyText).
class GeneratedCategory : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::BlockText* source READ source WRITE setSource NOTIFY sourceChanged)
    Q_PROPERTY(QString categoryId READ categoryId WRITE setCategoryId NOTIFY categoryIdChanged)
    Q_PROPERTY(bool loop READ loop NOTIFY loopChanged)
    // What the program or a data file supplies is shown, never edited.
    Q_PROPERTY(bool output READ output NOTIFY outputChanged)
    Q_PROPERTY(QStringList names READ names NOTIFY namesChanged)
    Q_PROPERTY(QStringList labels READ labels NOTIFY labelsChanged)
    Q_PROPERTY(QStringList units READ units NOTIFY unitsChanged)
    // The items the program writes, shown and never edited (the project's times and location).
    Q_PROPERTY(QStringList setByProgram READ setByProgram NOTIFY setByProgramChanged)
    // The rows, each its values in the order of `names`, and how many there are.
    Q_PROPERTY(edi_app::GeneratedRows* rows READ rows CONSTANT)
    Q_PROPERTY(int rowCount READ rowCount NOTIFY rowCountChanged)
    // Each item's control, from its dictionary type: "choice" (a selector), "flag", "number" or "text".
    Q_PROPERTY(QStringList kinds READ kinds NOTIFY kindsChanged)

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
    QStringList setByProgram() const { return set_by_program_; }
    GeneratedRows* rows() const { return rows_; }
    int rowCount() const { return rows_->rowCount(); }
    // The value at `column` of `names` in row `row`, as written; empty past the rows.
    Q_INVOKABLE QString value(int row, int column) const { return rows_->value(row, column); }
    QStringList kinds() const { return kinds_; }
    // The options of the item at `index` of `names`, a selector's; null for any other item.
    Q_INVOKABLE edi_app::OptionListModel* optionsAt(int index) const;

    // The block's text with one value replaced.
    Q_INVOKABLE QString editedText(int row, const QString& name, const QString& value) const;

   signals:
    void sourceChanged();
    void categoryIdChanged();
    void loopChanged();
    void outputChanged();
    void namesChanged();
    void labelsChanged();
    void unitsChanged();
    void setByProgramChanged();
    void rowCountChanged();
    void kindsChanged();

   private:
    void read();

    QPointer<BlockText> source_;
    QString id_;
    bool loop_ = false;
    bool output_ = false;
    QStringList names_, labels_, units_, set_by_program_, kinds_;
    GeneratedRows* rows_ = new GeneratedRows(this);
    QList<OptionListModel*> options_;  // one per item, null but for a selector
};

}  // namespace edi_app

#endif  // EDI_APP_GENERATED_CATEGORY_HPP
