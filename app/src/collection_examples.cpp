// SPDX-License-Identifier: BSD-3-Clause
#include "collection_examples.hpp"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QLoggingCategory>
#include <QUrl>

#include <stdexcept>
#include <utility>

#include "edi/online_fetch.hpp"
#include "edi/online_index.hpp"
#include "online_fetch.hpp"
#include "online_sources.hpp"

namespace edi_app {
namespace {
Q_LOGGING_CATEGORY(lcCollection, "edi.collection")

// COD is read through its search service and publishes no collection index (edi ADR-0068); only a COD source pointed
// at a folder is read as a collection. Asking COD for an index fails everywhere, and in the browser the request is
// refused outright.
bool cod_service(const OnlineSourcesModel& sources, const QString& id) {
    const QUrl url(sources.urlOf(id));
    return sources.isCod(id) && !url.isLocalFile() && url.scheme() != QStringLiteral("file");
}
}  // namespace

CollectionExamples::CollectionExamples(OnlineSourcesModel* sources, QObject* parent) : QObject(parent), sources_(sources) {
    if (sources_) connect(sources_, &OnlineSourcesModel::sourcesChanged, this, &CollectionExamples::refresh);
    refresh();
}

CollectionExamples::~CollectionExamples() = default;

void CollectionExamples::refresh() {
    const int generation = ++generation_;
    known_.clear();
    failed_.clear();
    projects_ = 0;
    // Every enabled source, once, whatever kinds it holds: the tutorials take a structure and a pattern, the
    // Examples list the projects.
    QList<OnlineSourcesModel::Source> sources;
    if (sources_)
        for (const char* kind : {"project", "structure", "experiment", "data"})
            for (const OnlineSourcesModel::Source& source : sources_->sourcesFor(QString::fromLatin1(kind)))
                if (std::none_of(sources.cbegin(), sources.cend(), [&source](const OnlineSourcesModel::Source& s) { return s.id == source.id; }) &&
                    !cod_service(*sources_, source.id))
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
                      for (const edi::online::Entry& entry : index.entries) {
                          if (entry.files.empty()) continue;
                          const QString id = QString::fromStdString(entry.id);
                          if (known_.contains(id)) continue;  // the first source holding an id serves it
                          const edi::online::File& file = entry.files.front();
                          known_.insert(id, {bases, QString::fromStdString(file.path), QString::fromStdString(entry.kind), file.bytes,
                                             QString::fromStdString(file.sha256)});
                          if (entry.kind != "project") continue;
                          ++projects_;
                      }
                      updateNotice();
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
    if (it == known_.constEnd()) return {};
    edi::online::File file;
    file.path = it->path.toStdString();
    return QString::fromStdString(edi::online::file_name(file));
}

void CollectionExamples::fetchBytes(const QString& id, BytesDone done, FetchProgress progress) {
    const auto it = known_.constFind(id);
    if (it == known_.constEnd()) {
        done({}, tr("No online source that answered holds '%1'").arg(id));
        return;
    }
    if (progress) progress(0, it->bytes);
    fetchPaired(id, it->sources, 0, false, std::move(done), std::move(progress));
}

// The file and the index it is checked against come from the same location, the index read in this operation: the
// first location that answers serves both, the next only after an outage, so a file from the online collection is
// never checked against the bundled copy's index or against an index read before the collection moved on. A file that
// still disagrees with that index (a publication between the two reads) is read once more, index first.
void CollectionExamples::fetchPaired(const QString& id, const QStringList& bases, int at, bool retried, BytesDone done,
                                     FetchProgress progress) {
    if (at >= bases.size()) {
        done({}, tr("No online source that answered holds '%1'").arg(id));
        return;
    }
    const QString base = bases.at(at);
    const auto url = [](const QString& base, const QString& path) {
        QUrl out(QString::fromStdString(edi::online::location_url(base.toStdString(), path.toStdString())));
        return out.scheme().isEmpty() ? QUrl::fromLocalFile(out.toString()) : out;
    };
    const QPointer<CollectionExamples> receiver(this);
    fetch_url(this, network_, url(base, QStringLiteral("index.json")),
              [receiver, id, bases, at, retried, done, progress, base, url](const QByteArray& bytes, const QString& error, bool unreachable) {
        if (!receiver) return;
        if (!error.isEmpty()) {
            if (unreachable && at + 1 < bases.size()) receiver->fetchPaired(id, bases, at + 1, retried, done, progress);
            else done({}, error);
            return;
        }
        edi::online::File file;
        try {
            const edi::online::Index index = edi::online::parse_index(bytes.toStdString());
            const edi::online::Entry* entry = edi::online::find(index, id.toStdString());
            if (entry == nullptr || entry->files.empty()) {
                done({}, tr("No online source that answered holds '%1'").arg(id));
                return;
            }
            file = entry->files.front();
        } catch (const std::exception& problem) {
            done({}, QString::fromUtf8(problem.what()));
            return;
        }
        const QString path = QString::fromStdString(file.path);
        const QString name = QString::fromStdString(edi::online::file_name(file));
        const auto it = receiver->known_.find(id);
        if (it != receiver->known_.end()) {
            it->path = path;
            it->bytes = file.bytes;
            it->sha256 = QString::fromStdString(file.sha256);
        }
        fetch_url(receiver, receiver->network_, url(base, path),
                  [receiver, id, bases, at, retried, done, progress, file, name](const QByteArray& bytes, const QString& error, bool unreachable) {
            if (!receiver) return;
            if (!error.isEmpty()) {
                if (unreachable && at + 1 < bases.size()) receiver->fetchPaired(id, bases, at + 1, retried, done, progress);
                else done({}, error);
                return;
            }
            const QString problem = content_problem(bytes, file.bytes, QString::fromStdString(file.sha256), name);
            if (problem.isEmpty()) done(bytes, {});
            else if (!retried) receiver->fetchPaired(id, bases, at, true, done, progress);
            else done({}, problem);
        }, [progress, expected = file.bytes](qint64 received, qint64 total) {
            if (progress) progress(received, total > 0 ? total : expected);
        });
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
