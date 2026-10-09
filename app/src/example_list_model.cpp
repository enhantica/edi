// SPDX-License-Identifier: BSD-3-Clause
#include "example_list_model.hpp"

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <algorithm>

namespace edi_app {
namespace {
const QString unknown = QStringLiteral("__unknown__");
const QStringList keys{"purpose",        "fittingMode", "facilities", "instruments",
                       "sampleForm",     "beamMode",    "probe",      "scatteringType",
                       "dimensionality", "polarisation"};
const QStringList titles{"Purpose",        "Fitting mode", "Facilities", "Instruments",
                         "Sample form",    "Beam mode",    "Probe",      "Scattering type",
                         "Dimensionality", "Polarisation"};
const QStringList allTitles{"All purposes",     "All fitting modes",    "All facilities",
                            "All instruments",  "All sample forms",     "All beam modes",
                            "All probes",       "All scattering types", "All dimensionalities",
                            "All polarisations"};
QString normalize(const QString& text) {
    return text.normalized(QString::NormalizationForm_KD).toCaseFolded();
}
QString label(const QString& value) {
    if (value == unknown) return ExampleListModel::tr("Not specified");
    if (value == QLatin1String("__not_applicable__"))
        return ExampleListModel::tr("Not applicable");
    if (value == QLatin1String("refinement")) return ExampleListModel::tr("Rietveld refinement");
    if (value == QLatin1String("simulation")) return ExampleListModel::tr("Simulation");
    QString result = value;
    if (!result.isEmpty()) result[0] = result[0].toUpper();
    return result;
}
QStringList strings(const QJsonArray& array) {
    QStringList result;
    for (const auto& item : array) result.append(item.toString());
    return result;
}
QString tag(const QString& value) {
    static const QHash<QString, QString> tags{
        {"powder", "pd"},         {"single crystal", "sc"}, {"neutron", "neut"},
        {"x-ray", "xray"},        {"xray", "xray"},         {"constant wavelength", "cwl"},
        {"time-of-flight", "tof"}};
    return tags.value(value, label(value));
}
}  // namespace

QStringList ExampleListModel::bundledIds() {
    QFile index(QStringLiteral(":/edi/examples/index.txt"));
    if (!index.open(QIODevice::ReadOnly | QIODevice::Text)) return {};
    return QString::fromUtf8(index.readAll()).split(QLatin1Char('\n'), Qt::SkipEmptyParts);
}
ExampleListModel::ExampleListModel(QObject* parent)
    : RowTableModel(
          {"exampleId", "name", "description", "sample", "origin", "detail", "tagLabels"}, parent),
      properties_({"value", "title"}, this),
      options_({"value", "title", "matchingCount"}, this) {
    QList<Row> properties;
    for (qsizetype i = 0; i < keys.size(); ++i)
        properties.append(
            {reinterpret_cast<const void*>(i + 1), {keys[i], tr(qPrintable(titles[i]))}});
    properties_.publish(properties);
    QFile file(QStringLiteral(":/edi/examples/metadata.json"));
    if (!file.open(QIODevice::ReadOnly)) qFatal("Bundled example metadata is missing");
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll());
    if (document.object().value("schema").toInt() != 1)
        qFatal("Invalid bundled example metadata schema");
    const auto catalog = document.object().value("examples").toObject();
    for (const auto& id : bundledIds()) {
        const auto metadata = catalog.value(id).toObject();
        if (metadata.isEmpty()) qFatal("Bundled example has no metadata: %s", qPrintable(id));
        Entry entry;
        entry.id = id;
        entry.sample = strings(metadata.value("samples").toArray()).join(QStringLiteral(" / "));
        entry.origin = metadata.value("origin").toString();
        entry.detail = metadata.value("detail").toString();
        entry.search = id + " " + entry.sample + " " + entry.origin + " " + entry.detail + " " +
                       strings(metadata.value("searchAliases").toArray()).join(' ');
        const auto values = metadata.value("values").toObject();
        for (const auto& key : keys) {
            QStringList data;
            for (QString value : strings(values.value(key).toArray())) {
                value = value.trimmed();
                if (value.isEmpty()) value = unknown;
                if (!data.contains(value)) data.append(value);
                entry.search += " " + value + " " + label(value);
            }
            if (data.isEmpty()) data.append(unknown);
            entry.values.insert(key, data);
        }
        for (const auto& purpose : entry.values.value("purpose"))
            entry.tags.append(label(purpose));
        for (const auto& mode : entry.values.value("fittingMode"))
            if (mode != unknown) entry.tags.append(label(mode));
        for (const QString& key : {QStringLiteral("sampleForm"), QStringLiteral("probe"),
                                   QStringLiteral("beamMode"), QStringLiteral("scatteringType")})
            for (const auto& value : entry.values.value(key))
                if (value != unknown && !entry.tags.contains(tag(value)))
                    entry.tags.append(tag(value));
        entry.search = normalize(entry.search + " " + entry.tags.join(' '));
        entries_.append(entry);
    }
    refresh();
}
QStringList ExampleListModel::propertyValues(const QString& id, const QString& property) const {
    for (const auto& entry : entries_)
        if (entry.id == id) return entry.values.value(property);
    return {};
}
void ExampleListModel::setSearchText(const QString& value) {
    if (search_text_ == value) return;
    search_text_ = value;
    refresh();
    emit searchTextChanged();
}
void ExampleListModel::setFilterProperty(const QString& value) {
    if (!keys.contains(value) || filter_property_ == value) return;
    filter_property_ = value;
    const bool changed = !filter_value_.isEmpty();
    filter_value_.clear();
    refresh();
    emit filterPropertyChanged();
    if (changed) emit filterValueChanged();
}
void ExampleListModel::setFilterValue(const QString& value) {
    if (filter_value_ == value) return;
    if (!value.isEmpty()) {
        bool valid = false;
        for (const auto& entry : entries_)
            valid |= entry.values.value(filter_property_).contains(value);
        if (!valid) return;
    }
    filter_value_ = value;
    refresh();
    emit filterValueChanged();
}
void ExampleListModel::refresh() {
    const auto words = normalize(search_text_)
                           .split(QRegularExpression(QStringLiteral("\\s+")), Qt::SkipEmptyParts);
    QHash<QString, int> counts;
    int total = 0;
    QList<Row> rows;
    for (qsizetype i = 0; i < entries_.size(); ++i) {
        const auto& entry = entries_[i];
        const auto values = entry.values.value(filter_property_);
        for (const auto& value : values)
            if (!counts.contains(value)) counts.insert(value, 0);
        if (!std::all_of(words.begin(), words.end(),
                         [&](const QString& word) { return entry.search.contains(word); }))
            continue;
        ++total;
        for (const auto& value : values) ++counts[value];
        if (!filter_value_.isEmpty() && !values.contains(filter_value_)) continue;
        rows.append(
            {reinterpret_cast<const void*>(i + 1),
             {entry.id, entry.sample + QStringLiteral(" · ") + entry.origin,
              entry.tags.join(QStringLiteral(" · ")) + QStringLiteral(" · ") + entry.detail,
              entry.sample, entry.origin, entry.detail, entry.tags}});
    }
    QStringList choices = counts.keys();
    std::sort(choices.begin(), choices.end(), [](const QString& a, const QString& b) {
        return label(a).localeAwareCompare(label(b)) < 0;
    });
    QList<Row> options{{reinterpret_cast<const void*>(1),
                        {QString(),
                         tr(qPrintable(allTitles[keys.indexOf(filter_property_)])) +
                             QStringLiteral(" (%1)").arg(total),
                         total}}};
    for (qsizetype i = 0; i < choices.size(); ++i)
        options.append({reinterpret_cast<const void*>(i + 2),
                        {choices[i],
                         label(choices[i]) + QStringLiteral(" (%1)").arg(counts.value(choices[i])),
                         counts.value(choices[i])}});
    options_.publish(options);
    setTableRows(rows);
}
}  // namespace edi_app
