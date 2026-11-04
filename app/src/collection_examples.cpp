// SPDX-License-Identifier: BSD-3-Clause
#include "collection_examples.hpp"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QLoggingCategory>

#include <stdexcept>

#include "edi/online_index.hpp"
#include "online_fetch.hpp"
#include "online_sources.hpp"

namespace edi_app {
namespace {
Q_LOGGING_CATEGORY(lcCollection, "edi.collection")

QString tag(const char* family, const std::string& value) {
    return value.empty() ? QString() : QString::fromLatin1(family) + u':' + QString::fromStdString(value);
}

}  // namespace

CollectionExamples::CollectionExamples(OnlineSourcesModel* sources, QObject* parent) : QObject(parent), sources_(sources) {
    if (sources_) connect(sources_, &OnlineSourcesModel::sourcesChanged, this, &CollectionExamples::refresh);
    refresh();
}

CollectionExamples::~CollectionExamples() = default;

void CollectionExamples::refresh() {
    const int generation = ++generation_;
    items_.clear();
    known_.clear();
    emit itemsChanged();
    if (!sources_) return;
    for (const OnlineSourcesModel::Source& source : sources_->sourcesFor(QStringLiteral("project"))) {
        const QString base = sources_->urlOf(source.id);
        const QString sourceId = source.id, sourceName = source.name;
        fetch_url(this, network_, joined_url(base, QStringLiteral("index.json")),
                  [this, generation, base, sourceId, sourceName](const QByteArray& bytes, const QString& error, bool) {
                      if (generation != generation_) return;
                      if (!error.isEmpty()) {
                          qCInfo(lcCollection, "examples from %s not read: %s", qPrintable(sourceName), qPrintable(error));
                          return;
                      }
                      edi::online::Index index;
                      try {
                          index = edi::online::parse_index(bytes.toStdString());
                      } catch (const std::exception& problem) {
                          qCInfo(lcCollection, "examples from %s not read: %s", qPrintable(sourceName), problem.what());
                          return;
                      }
                      for (const edi::online::Entry& entry : index.entries) {
                          if (entry.kind != "project" || entry.files.empty()) continue;
                          ExampleListModel::Item item;
                          item.id = QStringLiteral("collection/") + sourceId + u'/' + QString::fromStdString(entry.id);
                          item.title = QString::fromStdString(entry.name.empty() ? entry.id : entry.name);
                          // The origin column as the bundled rows show it, instrument @ facility; the source when
                          // the entry names neither.
                          const QString instrument = QString::fromStdString(entry.instrument);
                          const QString facility = QString::fromStdString(entry.facility);
                          item.origin = instrument.isEmpty() ? facility
                                        : facility.isEmpty() ? instrument
                                                             : instrument + QStringLiteral(" @ ") + facility;
                          if (item.origin.isEmpty()) item.origin = sourceName;
                          item.detail = QString::fromStdString(entry.description);
                          const std::string technique = entry.technique;
                          const std::string form = technique.find("single") != std::string::npos ? "single crystal" : technique.empty() ? "" : "powder";
                          const std::string mode = technique.find("time") != std::string::npos ? "time-of-flight" : technique.empty() ? "" : "constant wavelength";
                          for (const QString& t : {tag("sampleForm", form), tag("beamMode", mode), tag("probe", entry.radiation),
                                                  tag("facilities", entry.facility), tag("instruments", entry.instrument)})
                              if (!t.isEmpty()) item.tags.append(t);
                          item.tags.append(QStringLiteral("source:") + sourceName);
                          known_.insert(item.id, {base, QString::fromStdString(entry.files.front().path), item.title});
                          items_.append(item);
                      }
                      emit itemsChanged();
                  });
    }
}

void CollectionExamples::fetchProject(const QString& id, ProjectDone done) {
    const auto it = known_.constFind(id);
    if (it == known_.constEnd()) {
        done({}, tr("No collection example named '%1'").arg(id));
        return;
    }
    const Known known = *it;
    fetch_url(this, network_, joined_url(known.source, known.path), [this, known, done](const QByteArray& bytes, const QString& error, bool) {
        if (!error.isEmpty()) {
            done({}, error);
            return;
        }
        if (!downloads_) downloads_ = std::make_unique<QTemporaryDir>();
        if (!downloads_->isValid()) {
            done({}, tr("No temporary folder for the download"));
            return;
        }
        QDir folder(downloads_->path());
        QString sub = QString::number(QDateTime::currentMSecsSinceEpoch(), 36);
        int n = 0;
        while (folder.exists(sub)) sub += QString::number(++n);
        folder.mkdir(sub);
        const QString path = folder.filePath(sub + u'/' + QFileInfo(known.path).fileName());
        QFile out(path);
        if (!out.open(QIODevice::WriteOnly) || out.write(bytes) != bytes.size()) {
            done({}, tr("The download could not be written to %1").arg(path));
            return;
        }
        out.close();
        done(QUrl::fromLocalFile(path), {});
    });
}

}  // namespace edi_app
