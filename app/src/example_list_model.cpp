// SPDX-License-Identifier: BSD-3-Clause
#include "example_list_model.hpp"

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <algorithm>

#include "edi/display.hpp"

namespace edi_app {
namespace {
const QString unknown = QStringLiteral("__unknown__");
const QStringList keys{"purpose",        "fittingMode",  "facilities", "instruments",
                       "sampleForm",     "beamMode",     "probe",      "scatteringType",
                       "dimensionality", "polarisation", "structure"};
const QStringList titles{"Purpose",        "Fitting mode", "Facilities", "Instruments",
                         "Sample form",    "Beam mode",    "Probe",      "Scattering type",
                         "Dimensionality", "Polarisation", "Structure"};
const QStringList allTitles{"All purposes",     "All fitting modes",    "All facilities",
                            "All instruments",  "All sample forms",     "All beam modes",
                            "All probes",       "All scattering types", "All dimensionalities",
                            "All polarisations", "All structures"};
const QJsonObject& tagRegistry() {
    static const auto registry = [] {
        QFile file(QStringLiteral(":/edi/examples/tags.json"));
        if (!file.open(QIODevice::ReadOnly)) qFatal("Bundled tag registry is missing");
        QJsonParseError error;
        const auto result = QJsonDocument::fromJson(file.readAll(), &error).object();
        if (error.error != QJsonParseError::NoError || result.value("schema").toInt() != 1)
            qFatal("Invalid tag registry");
        return result;
    }();
    return registry;
}
QJsonObject tagDefinition(const QString& family, const QString& value) {
    return tagRegistry().value("tags").toObject().value(family).toObject().value(value).toObject();
}
QString normalize(const QString& text) {
    return text.normalized(QString::NormalizationForm_KD).toCaseFolded();
}
QString label(const QString& value) {
    if (value == unknown) return ExampleListModel::tr("Not specified");
    if (value == QLatin1String("__not_applicable__"))
        return QString::fromStdString(edi::option_label("experiment_type.polarisation", "."));
    if (value == QLatin1String("refinement")) return ExampleListModel::tr("Fitting");
    if (value == QLatin1String("simulation")) return ExampleListModel::tr("Simulation");
    if (value == QLatin1String("crystal")) return ExampleListModel::tr("Crystal structure");
    if (value == QLatin1String("magnetic")) return ExampleListModel::tr("Magnetic structure");
    if (value == QLatin1String("1d"))
        return QString::fromStdString(edi::option_label("experiment_type.dimensionality", "1d"));
    QString result = value;
    if (!result.isEmpty()) result[0] = result[0].toUpper();
    return result;
}
// An example's title is its sample and origin; an item's, its title alone.
QString entryTitle(const QString& sample, const QString& origin) {
    return origin.isEmpty() ? sample : sample + QStringLiteral(" · ") + origin;
}
const QStringList roles{"exampleId", "name",     "description", "sample",    "origin",
                        "detail",    "tagLabels", "tagIcons",   "tagColors", "tagDarkColors"};
QStringList strings(const QJsonArray& array) {
    QStringList result;
    for (const auto& item : array) result.append(item.toString());
    return result;
}
}  // namespace

TagChip tagChip(const QString& family, const QString& value, const QString& fallback) {
    const auto definition = tagDefinition(family, value);
    const auto tones = tagRegistry().value("tones").toObject();
    const auto tone = tones.value(definition.value("tone").toString("neutral")).toObject();
    return {definition.value("label").toString(fallback), definition.value("glyph").toString(),
            tone.value("light").toString(), tone.value("dark").toString()};
}

QStringList ExampleListModel::bundledIds() {
    QFile index(QStringLiteral(":/edi/examples/index.txt"));
    if (!index.open(QIODevice::ReadOnly | QIODevice::Text)) return {};
    return QString::fromUtf8(index.readAll()).split(QLatin1Char('\n'), Qt::SkipEmptyParts);
}
void ExampleListModel::publishProperties() {
    QList<Row> properties;
    for (qsizetype i = 0; i < keys.size(); ++i)
        properties.append(
            {reinterpret_cast<const void*>(i + 1), {keys[i], tr(qPrintable(titles[i]))}});
    properties_.publish(properties);
}
void ExampleListModel::addTag(Entry& entry, const QString& family, const QString& value,
                              const QString& fallback) {
    const TagChip chip = tagChip(family, value, fallback);
    if (entry.tags.contains(chip.label)) return;
    entry.tags.append(chip.label);
    entry.tag_icons.append(chip.glyph);
    entry.tag_colors.append(chip.light);
    entry.tag_dark_colors.append(chip.dark);
}
ExampleListModel::ExampleListModel(const QList<Item>& items, QObject* parent)
    : RowTableModel(roles, parent),
      properties_({"value", "title"}, this),
      options_({"value", "title", "matchingCount"}, this) {
    publishProperties();
    for (const Item& item : items) addItem(item);
    refresh();
}
void ExampleListModel::addItem(const Item& item) {
    Entry entry;
    entry.id = item.id;
    entry.sample = item.title;
    entry.origin = item.origin;
    entry.detail = item.detail;
    entry.search = item.id + " " + item.title + " " + item.origin + " " + item.detail;
    for (const QString& tag : item.tags) {
        const qsizetype colon = tag.indexOf(QLatin1Char(':'));
        const QString family = colon < 0 ? QString() : tag.left(colon);
        const QString value = tag.mid(colon + 1).trimmed();
        addTag(entry, family, value, value);
        if (!keys.contains(family)) continue;
        QStringList& data = entry.values[family];
        if (!data.contains(value)) data.append(value);
        entry.search += " " + value + " " + label(value);
    }
    for (const auto& key : keys)
        if (entry.values.value(key).isEmpty()) entry.values.insert(key, {unknown});
    entry.search = normalize(entry.search + " " + entry.tags.join(' '));
    entries_.append(entry);
}
void ExampleListModel::replaceItems(const QList<Item>& items) {
    entries_.removeIf([this](const Entry& entry) { return added_ids_.contains(entry.id); });
    added_ids_.clear();
    for (const Item& item : items) {
        const bool present = std::any_of(entries_.cbegin(), entries_.cend(), [&item](const Entry& entry) { return entry.id == item.id; });
        if (present) continue;
        addItem(item);
        added_ids_.insert(item.id);
    }
    refresh();
}
ExampleListModel::ExampleListModel(QObject* parent)
    : RowTableModel(roles, parent),
      properties_({"value", "title"}, this),
      options_({"value", "title", "matchingCount"}, this) {
    publishProperties();
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
        for (const QString& key : {QStringLiteral("purpose"), QStringLiteral("fittingMode"),
                                   QStringLiteral("sampleForm"), QStringLiteral("probe"),
                                   QStringLiteral("beamMode"), QStringLiteral("scatteringType"),
                                   QStringLiteral("structure")})
            for (const auto& value : entry.values.value(key))
                if (value != unknown) addTag(entry, key, value, label(value));
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
QString ExampleListModel::titleOf(const QString& id) const {
    for (const auto& entry : entries_) {
        if (entry.id == id) {
            return entryTitle(entry.sample, entry.origin);
        }
    }
    return {};
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
             {entry.id, entryTitle(entry.sample, entry.origin),
              entry.tags.join(QStringLiteral(" · ")) + QStringLiteral(" · ") + entry.detail,
              entry.sample, entry.origin, entry.detail, entry.tags, entry.tag_icons, entry.tag_colors, entry.tag_dark_colors}});
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
