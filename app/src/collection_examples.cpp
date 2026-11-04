// SPDX-License-Identifier: BSD-3-Clause
#include "collection_examples.hpp"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QLoggingCategory>

#include <stdexcept>
#include <utility>

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
    failed_.clear();
    projects_ = 0;
    emit itemsChanged();
    // Every enabled source, once, whatever kinds it holds: the tutorials take a structure and a pattern, the
    // Examples list the projects.
    QList<OnlineSourcesModel::Source> sources;
    if (sources_)
        for (const char* kind : {"project", "structure", "experiment", "data"})
            for (const OnlineSourcesModel::Source& source : sources_->sourcesFor(QString::fromLatin1(kind)))
                if (std::none_of(sources.cbegin(), sources.cend(), [&source](const OnlineSourcesModel::Source& s) { return s.id == source.id; }))
                    sources.append(source);
    pending_ = static_cast<int>(sources.size());
    updateNotice();
    if (pending_ == 0) settle();
    for (const OnlineSourcesModel::Source& source : sources) {
        const QStringList bases = sources_->urlsOf(source.id);
        const QString sourceName = source.name;
        fetch_from(this, network_, bases, QStringLiteral("index.json"),
                  [this, generation, bases, sourceName](const QByteArray& bytes, const QString& error, bool) {
                      if (generation != generation_) return;
                      --pending_;
                      edi::online::Index index;
                      try {
                          if (!error.isEmpty()) throw std::runtime_error(error.toStdString());
                          index = edi::online::parse_index(bytes.toStdString());
                      } catch (const std::exception& problem) {
                          qCInfo(lcCollection, "collection %s not read: %s", qPrintable(sourceName), problem.what());
                          failed_.append(sourceName + QStringLiteral(": ") + QString::fromUtf8(problem.what()));
                          updateNotice();
                          if (pending_ == 0) settle();
                          return;
                      }
                      const QStringList bundled = ExampleListModel::bundledIds();
                      for (const edi::online::Entry& entry : index.entries) {
                          if (entry.files.empty()) continue;
                          const QString id = QString::fromStdString(entry.id);
                          if (known_.contains(id)) continue;  // the first source holding an id serves it
                          const edi::online::File& file = entry.files.front();
                          known_.insert(id, {bases, QString::fromStdString(file.path), QString::fromStdString(entry.kind), file.bytes,
                                             QString::fromStdString(file.sha256)});
                          if (entry.kind != "project") continue;
                          ++projects_;
                          if (bundled.contains(id)) continue;  // a catalogue row already stands for it
                          ExampleListModel::Item item;
                          item.id = id;
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
                          items_.append(item);
                      }
                      updateNotice();
                      emit itemsChanged();
                      if (pending_ == 0) settle();
                  });
    }
}

void CollectionExamples::updateNotice() {
    QString notice;
    if (pending_ == 0 && projects_ == 0)
        notice = failed_.isEmpty()
                     ? tr("No online source holds example projects; enable or add one in Preferences")
                     : tr("The example projects can't be downloaded. %1").arg(failed_.join(QStringLiteral("; ")));
    if (notice == notice_) return;
    notice_ = notice;
    emit noticeChanged();
}

// Every request that waited for the sources to be read gets its answer, in order; a request made while they run
// joins the next round.
void CollectionExamples::settle() {
    const QList<std::function<void()>> waiting = std::exchange(waiting_, {});
    for (const std::function<void()>& then : waiting) then();
}

void CollectionExamples::whenRead(const QString& id, std::function<void()> then) {
    if (known_.contains(id)) {
        then();
        return;
    }
    waiting_.append(std::move(then));
    if (pending_ == 0) refresh();
}

QString CollectionExamples::fileName(const QString& id) const {
    const auto it = known_.constFind(id);
    return it == known_.constEnd() ? QString() : QFileInfo(it->path).fileName();
}

void CollectionExamples::fetchBytes(const QString& id, BytesDone done, FetchProgress progress) {
    const auto it = known_.constFind(id);
    if (it == known_.constEnd()) {
        done({}, tr("No online source that answered holds '%1'").arg(id));
        return;
    }
    const Known known = *it;
    const QPointer<CollectionExamples> receiver(this);
    if (progress) progress(0, known.bytes);
    if (!receiver) return;
    fetch_from(this, network_, known.sources, known.path, [known, done](const QByteArray& bytes, const QString& error, bool) {
        if (!error.isEmpty()) {
            done({}, error);
            return;
        }
        // The index's size and digest, when it states them, before the file is used.
        const QString problem = content_problem(bytes, known.bytes, known.sha256, QFileInfo(known.path).fileName());
        if (!problem.isEmpty()) {
            done({}, problem);
            return;
        }
        done(bytes, {});
    }, [progress, expected = known.bytes](qint64 received, qint64 total) {
        if (progress) progress(received, total > 0 ? total : expected);
    });
}

void CollectionExamples::fetchProject(const QString& id, ProjectDone done, FetchProgress progress) {
    const QString name = fileName(id);
    fetchBytes(id, [this, name, done](const QByteArray& bytes, const QString& error) {
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
        const QString path = folder.filePath(sub + u'/' + name);
        QFile out(path);
        if (!out.open(QIODevice::WriteOnly) || out.write(bytes) != bytes.size()) {
            done({}, tr("The download could not be written to %1").arg(path));
            return;
        }
        out.close();
        done(QUrl::fromLocalFile(path), {});
    }, std::move(progress));
}

}  // namespace edi_app
