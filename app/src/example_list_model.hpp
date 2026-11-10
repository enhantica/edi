// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EXAMPLE_LIST_MODEL_HPP
#define EDI_APP_EXAMPLE_LIST_MODEL_HPP

#include <QHash>
#include <QVariantList>

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
    // The five selectors' values (purpose, fitting mode, sample form, probe, beam mode), all applied at once; changes
    // with every refresh, so the selectors' option lists follow the search and each other.
    Q_PROPERTY(int facetRevision READ facetRevision NOTIFY facetsChanged)
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
    int facetRevision() const { return facet_revision_; }
    // One selector's value, empty for all of them.
    Q_INVOKABLE QString facetFilter(const QString& key) const { return facet_filters_.value(key); }
    Q_INVOKABLE void setFacetFilter(const QString& key, const QString& value);
    // One selector's choices: "All …" first, then each value with how many entries the other filters leave have it.
    Q_INVOKABLE QVariantList facetOptions(const QString& key) const;
    Q_INVOKABLE void clearFacets();
   signals:
    void searchTextChanged();
    void filterPropertyChanged();
    void filterValueChanged();
    void facetsChanged();

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
    ExampleOptions properties_, options_;
    QString search_text_, filter_property_ = QStringLiteral("purpose"), filter_value_;
    QHash<QString, QString> facet_filters_;
    int facet_revision_ = 0;
    // Whether an entry passes the search and every facet filter but `except`'s.
    bool passes(const Entry& entry, const QStringList& words, const QString& except) const;
};
}  // namespace edi_app
#endif
