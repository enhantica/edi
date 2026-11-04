// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_GENERATED_CATEGORY_HPP
#define EDI_APP_GENERATED_CATEGORY_HPP

#include <QAbstractListModel>
#include <QHash>
#include <QObject>
#include <QQmlListProperty>
#include <QList>
#include <QVariantMap>
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
// One item of a loop as a cell: its `name`, its `column` in `names` and its `kind`.
struct GeneratedCell {
    Q_GADGET
    QML_VALUE_TYPE(generatedCell)
    Q_PROPERTY(QString name MEMBER name CONSTANT)
    Q_PROPERTY(int column MEMBER column CONSTANT)
    Q_PROPERTY(QString kind MEMBER kind CONSTANT)

   public:
    QString name;
    int column = 0;
    QString kind;
    bool operator==(const GeneratedCell&) const = default;
};

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
    // Each item's options, in the order of `names`: a selector's, null for any other item. An item keeps its options
    // across reads, so a selector showing them keeps them while the text changes.
    Q_PROPERTY(QQmlListProperty<edi_app::OptionListModel> options READ options NOTIFY optionsChanged)
    // A loop's cells, one per item in the order of `names`: its `name`, `column` and `kind`.
    Q_PROPERTY(QList<edi_app::GeneratedCell> cells READ cells NOTIFY cellsChanged)

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
    QQmlListProperty<OptionListModel> options() { return {this, &options_}; }
    QList<GeneratedCell> cells() const;

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
    void optionsChanged();
    void cellsChanged();

   private:
    QVariantMap property_notifications_;
    quint64 notification_publication_ = 0;
    void read();

    QPointer<BlockText> source_;
    QString id_;
    bool loop_ = false;
    bool output_ = false;
    QStringList names_, labels_, units_, set_by_program_, kinds_;
    GeneratedRows* rows_ = new GeneratedRows(this);
    QList<OptionListModel*> options_;  // one per item, null but for a selector
    QHash<QString, OptionListModel*> options_by_uid_;  // every selector's options, made once per item
};

}  // namespace edi_app

#endif  // EDI_APP_GENERATED_CATEGORY_HPP
