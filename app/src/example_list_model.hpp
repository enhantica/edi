// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EXAMPLE_LIST_MODEL_HPP
#define EDI_APP_EXAMPLE_LIST_MODEL_HPP

#include <QHash>
#include <QSet>

#include "row_table_model.hpp"

namespace edi_app {

// A tag's chip as the Examples list draws it (app/examples/tags.json): its label, its icon glyph and its colour in the
// light and the dark palette. A family or value the registry does not have gets a neutral chip labelled `fallback`.
struct TagChip {
    QString label, glyph, light, dark;
};
TagChip tagChip(const QString& family, const QString& value, const QString& fallback);
class ExampleOptions : public RowTableModel {
   public:
    explicit ExampleOptions(const QStringList& roles, QObject* parent)
        : RowTableModel(roles, parent) {}
    void publish(const QList<Row>& rows) { setTableRows(rows); }
};

// Bundled, curated metadata, filtered without changing the identity of an example.
class ExampleListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to the session")
    Q_PROPERTY(QString searchText READ searchText WRITE setSearchText NOTIFY searchTextChanged)
    Q_PROPERTY(QString filterProperty READ filterProperty WRITE setFilterProperty NOTIFY
                   filterPropertyChanged)
    Q_PROPERTY(QString filterValue READ filterValue WRITE setFilterValue NOTIFY filterValueChanged)
    Q_PROPERTY(edi_app::RowTableModel* filterProperties READ filterProperties CONSTANT)
    Q_PROPERTY(edi_app::RowTableModel* filterOptions READ filterOptions CONSTANT)
   public:
    // A catalogue entry that is not a bundled example (a tutorial, ADR-0064): its id, title and description, and its
    // tags as "family:value", which give its chips, in their order, and its values for the filters.
    struct Item {
        QString id, title, detail, origin;
        QStringList tags;
    };
    // The bundled examples.
    explicit ExampleListModel(QObject* parent);
    // Other items, filtered as the examples are.
    ExampleListModel(const QList<Item>& items, QObject* parent);
    static QStringList bundledIds();
    /// Replace the rows an earlier call added by `items`, built as the items constructor builds them; an item
    /// whose id a row already carries is not added twice.
    void replaceItems(const QList<Item>& items);
    // A bundled example's title, its sample and origin as the list shows them; empty for an unknown id.
    QString titleOf(const QString& id) const;
    QString searchText() const { return search_text_; }
    QString filterProperty() const { return filter_property_; }
    QString filterValue() const { return filter_value_; }
    RowTableModel* filterProperties() { return &properties_; }
    RowTableModel* filterOptions() { return &options_; }
    void setSearchText(const QString& value);
    void setFilterProperty(const QString& value);
    void setFilterValue(const QString& value);
    Q_INVOKABLE QStringList propertyValues(const QString& exampleId,
                                           const QString& property) const;
   signals:
    void searchTextChanged();
    void filterPropertyChanged();
    void filterValueChanged();

   private:
    struct Entry {
        QString id, sample, origin, detail, search;
        QStringList tags, tag_icons, tag_colors, tag_dark_colors;
        QHash<QString, QStringList> values;
    };
    void publishProperties();
    // Adds a chip for `family`'s `value`, once.
    static void addTag(Entry& entry, const QString& family, const QString& value, const QString& fallback);
    void refresh();
    void addItem(const Item& item);
    QList<Entry> entries_;
    QSet<QString> added_ids_;
    ExampleOptions properties_, options_;
    QString search_text_, filter_property_ = QStringLiteral("purpose"), filter_value_;
};
}  // namespace edi_app
#endif
