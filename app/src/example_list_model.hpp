// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EXAMPLE_LIST_MODEL_HPP
#define EDI_APP_EXAMPLE_LIST_MODEL_HPP

#include <QHash>

#include "row_table_model.hpp"

namespace edi_app {
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
    explicit ExampleListModel(QObject* parent);
    static QStringList bundledIds();
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
        QStringList tags, tag_icons;
        QHash<QString, QStringList> values;
    };
    void refresh();
    QList<Entry> entries_;
    ExampleOptions properties_, options_;
    QString search_text_, filter_property_ = QStringLiteral("purpose"), filter_value_;
};
}  // namespace edi_app
#endif
