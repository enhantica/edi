// SPDX-License-Identifier: BSD-3-Clause
#include "scan_session.hpp"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFuture>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaObject>
#include <QPointer>
#include <QtConcurrent/QtConcurrentRun>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string_view>

#include "edi/io.hpp"

namespace edi_app {
namespace {

namespace fs = std::filesystem;

fs::path analysis_dir(const edi::Project& project) { return fs::path(project.path) / "analysis"; }

const char* const kResultFiles[] = {"results.csv", "results-provenance.csv", "scan-run.json"};

std::optional<std::string>* slot(ScanSession::Files& files, int which) {
    return which == 0 ? &files.results : which == 1 ? &files.provenance : &files.run;
}

// A file's bytes; nullopt when it does not exist; throws when it exists and cannot be read.
std::optional<std::string> read_file(const fs::path& path) {
    std::error_code error;
    if (!fs::exists(path, error)) {
        if (error) {
            throw std::runtime_error("cannot tell whether " + path.string() + " exists: " + error.message());
        }
        return std::nullopt;
    }
    std::ifstream input(path, std::ios::binary);
    std::string bytes((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (!input && !input.eof()) {
        throw std::runtime_error("cannot read " + path.string());
    }
    return bytes;
}

// Writes `text` to `path` whole, through a sibling that is renamed over it; or removes `path` for nullopt.
void put_file(const fs::path& path, const std::optional<std::string>& text) {
    std::error_code error;
    if (!text) {
        fs::remove(path, error);
        if (error) {
            throw std::runtime_error("cannot remove " + path.string() + ": " + error.message());
        }
        return;
    }
    const fs::path staged = path.string() + ".edi-staged";
    {
        std::ofstream output(staged, std::ios::binary | std::ios::trunc);
        output << *text;
        output.close();
        if (!output) {
            fs::remove(staged, error);
            throw std::runtime_error("cannot write " + staged.string());
        }
    }
    fs::rename(staged, path, error);
    if (error) {
        fs::remove(staged, error);
        throw std::runtime_error("cannot replace " + path.string());
    }
}

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> cells(1);
    for (const char character : line) {
        if (character == ',') {
            cells.emplace_back();
        } else if (character != '\r') {
            cells.back() += character;
        }
    }
    return cells;
}

}  // namespace

ScanSession::ScanSession(QObject* parent) : QObject(parent) {}

ScanSession::~ScanSession() { stopMetadata(); }

QString ScanSession::load(const edi::Project& project) {
    stopMetadata();
    try {
        datasets_ = edi::scan_datasets(project);
    } catch (const std::exception& refusal) {
        datasets_ = {};
        places_.clear();
        index_ = {};
        return QString::fromUtf8(refusal.what());
    }
    places_ = edi::scan_places(datasets_);
    metadata_.assign(datasets_.files.size(), std::nullopt);
    asked_.assign(datasets_.files.size(), false);
    wanted_.clear();
    source_ = std::make_shared<const edi::Project>(project);
    run_ = {};
    try {
        if (const std::optional<std::string> bytes = read_file(analysis_dir(project) / "scan-run.json")) {
            const QJsonObject object = QJsonDocument::fromJson(QByteArray::fromStdString(*bytes)).object();
            run_.identity = object.value(QStringLiteral("template")).toString().toStdString();
            run_.seconds = object.value(QStringLiteral("seconds")).toDouble(-1.0);
            run_.outcome = object.value(QStringLiteral("outcome")).toString();
            run_.last_single = object.value(QStringLiteral("last")).toString() == QLatin1String("single");
        }
    } catch (const std::exception&) {
        run_ = {};  // no readable provenance: the results are taken as the template's
    }
    return reindex(project);
}

QString ScanSession::reindex(const edi::Project& project) {
    index_ = edi::index_scan_results(project, datasets_);
    return QString::fromStdString(index_.error);
}

int ScanSession::place(const std::string& file) const {
    const auto found = places_.find(file);
    return found == places_.end() ? -1 : static_cast<int>(found->second);
}

int ScanSession::addRow(const edi::Project& project, const std::vector<std::string>& cells, QString& error) {
    if (!index_.error.empty()) {
        error = QString::fromStdString(index_.error);
        return -1;
    }
    if (index_.header.empty()) {
        // The run's first row: the header is on disk now, before it.
        reindex(project);
        const int dataset = cells.size() == index_.header.size() ? place(edi::scan_row_file(index_, cells)) : -1;
        if (!index_.error.empty() || dataset < 0 || index_.rows[static_cast<std::size_t>(dataset)].offset < 0) {
            error = index_.error.empty() ? QStringLiteral("analysis/results.csv does not hold the row just written")
                                         : QString::fromStdString(index_.error);
            return -1;
        }
        return dataset;
    }
    try {
        auto [dataset, row] = edi::scan_row_facts(project, places_, index_, cells);
        if (index_.rows[dataset].offset >= 0) {
            return static_cast<int>(dataset);  // indexed already, when the run's first row caught up with the file
        }
        // crysta appends the cells joined by commas and a line break: the row starts where the file ended.
        std::int64_t length = 1;
        for (const std::string& cell : cells) {
            length += static_cast<std::int64_t>(cell.size()) + 1;
        }
        row.offset = index_.end;
        index_.end += length - 1;
        index_.rows[dataset] = std::move(row);
        ++index_.fitted;
        return static_cast<int>(dataset);
    } catch (const std::exception& refusal) {
        error = QString::fromUtf8(refusal.what());
        return -1;
    }
}

std::vector<std::string> ScanSession::row(const edi::Project& project, int dataset) const {
    if (dataset < 0 || dataset >= static_cast<int>(index_.rows.size()) || index_.rows[dataset].offset < 0) {
        return {};
    }
    std::vector<std::string> cells = edi::read_scan_row(project, index_.rows[dataset].offset);
    const std::string& expected = datasets_.files[static_cast<std::size_t>(dataset)];
    if (cells.size() != index_.header.size() || edi::scan_row_file(index_, cells) != expected) {
        throw std::invalid_argument("analysis/results.csv changed under the app: the row for '" + expected +
                                    "' is no longer where it was");
    }
    return cells;
}

QString ScanSession::outcome(int dataset, int max_iterations) const {
    if (dataset < 0 || dataset >= static_cast<int>(index_.rows.size()) || index_.rows[dataset].offset < 0) {
        return {};
    }
    const edi::ScanResultIndex::Row& row = index_.rows[dataset];
    if (row.converged) {
        return QStringLiteral("success");
    }
    return row.iterations >= max_iterations ? QStringLiteral("maxIterations") : QStringLiteral("noStep");
}

void ScanSession::column(const edi::Project& project, const std::string& name,
                         const std::function<void(int, double, double)>& visit) const {
    std::size_t value_column = 0, uncertainty_column = 0;
    bool found = false;
    for (const edi::ScanParameterColumns& parameter : index_.parameters) {
        if (parameter.name == name) {
            value_column = parameter.value;
            uncertainty_column = parameter.uncertainty;
            found = true;
        }
    }
    if (!found || !index_.error.empty()) {
        return;
    }
    std::ifstream input(analysis_dir(project) / "results.csv", std::ios::binary);
    std::string line;
    if (!std::getline(input, line)) {
        return;
    }
    std::int64_t offset = input.tellg();
    while (offset < index_.end && std::getline(input, line) && !input.eof()) {
        offset = input.tellg();
        const std::vector<std::string> cells = split(line);
        if (cells.size() != index_.header.size()) {
            continue;
        }
        const int dataset = place(edi::scan_row_file(index_, cells));
        double value = 0.0, uncertainty = 0.0;
        if (dataset >= 0 && edi::parse_scan_number(cells[value_column], value) &&
            edi::parse_scan_number(cells[uncertainty_column], uncertainty)) {
            visit(dataset, value, uncertainty);
        }
    }
}

QString ScanSession::writeRun(const edi::Project& project, const Run& run) {
    run_ = run;
    QJsonObject object{{QStringLiteral("template"), QString::fromStdString(run.identity)},
                       {QStringLiteral("outcome"), run.outcome},
                       {QStringLiteral("last"), run.last_single ? QStringLiteral("single") : QStringLiteral("scan")}};
    if (run.seconds >= 0.0) {
        object.insert(QStringLiteral("seconds"), run.seconds);
    }
    try {
        fs::create_directories(analysis_dir(project));
        put_file(analysis_dir(project) / "scan-run.json", QJsonDocument(object).toJson().toStdString());
    } catch (const std::exception& refusal) {
        return QString::fromUtf8(refusal.what());
    }
    return {};
}

std::string ScanSession::templateIdentity(const edi::Project& project) {
    // The name, title and description (project.edi) and the run settings (the fitting mode and the minimizer's
    // bounds) are not the template: changing them leaves the results current.
    QCryptographicHash hash(QCryptographicHash::Sha256);
    for (const auto& [path, body] : edi::project_edi_files(project)) {
        if (path == "project.edi") {
            continue;
        }
        hash.addData(QByteArrayView(path.data(), static_cast<qsizetype>(path.size())));
        hash.addData(QByteArrayView("\0", 1));
        std::size_t start = 0;
        while (start < body.size()) {
            const std::size_t end = std::min(body.find('\n', start), body.size());
            const std::string_view line(body.data() + start, end - start);
            if (!line.starts_with("_fitting_mode.") && !line.starts_with("_minimizer.")) {
                hash.addData(QByteArrayView(line.data(), static_cast<qsizetype>(line.size())));
                hash.addData(QByteArrayView("\n", 1));
            }
            start = end + 1;
        }
    }
    return hash.result().toHex().toStdString();
}

QString ScanSession::takeFiles(const edi::Project& project, Files& taken) {
    const fs::path directory = analysis_dir(project);
    taken = {};
    try {
        for (int which = 0; which < 3; ++which) {
            *slot(taken, which) = read_file(directory / kResultFiles[which]);
        }
    } catch (const std::exception& refusal) {
        return QString::fromUtf8(refusal.what());
    }
    int removed = 0;
    try {
        for (; removed < 3; ++removed) {
            put_file(directory / kResultFiles[removed], std::nullopt);
        }
    } catch (const std::exception& refusal) {
        // What was removed goes back, so a refused start leaves the results as they were.
        for (int which = 0; which < removed; ++which) {
            try {
                put_file(directory / kResultFiles[which], *slot(taken, which));
            } catch (const std::exception&) {
            }
        }
        return QString::fromUtf8(refusal.what());
    }
    return {};
}

QString ScanSession::putFiles(const edi::Project& project, const Files& files) {
    const fs::path directory = analysis_dir(project);
    Files current;
    try {
        fs::create_directories(directory);
        for (int which = 0; which < 3; ++which) {
            *slot(current, which) = read_file(directory / kResultFiles[which]);
        }
    } catch (const std::exception& refusal) {
        return QString::fromUtf8(refusal.what());
    }
    Files wanted = files;
    int done = 0;
    try {
        for (; done < 3; ++done) {
            put_file(directory / kResultFiles[done], *slot(wanted, done));
        }
    } catch (const std::exception& refusal) {
        for (int which = 0; which < done; ++which) {
            try {
                put_file(directory / kResultFiles[which], *slot(current, which));
            } catch (const std::exception&) {
            }
        }
        return QString::fromUtf8(refusal.what());
    }
    return {};
}

const std::vector<std::string>* ScanSession::extracted(int dataset) const {
    if (dataset < 0 || dataset >= static_cast<int>(datasets_.files.size())) {
        return nullptr;
    }
    if (index_.rows[dataset].offset >= 0) {
        return &index_.rows[dataset].extracted;
    }
    return metadata_[dataset] ? &*metadata_[dataset] : nullptr;
}

void ScanSession::want(int dataset) {
    if (dataset < 0 || dataset >= static_cast<int>(asked_.size()) || asked_[static_cast<std::size_t>(dataset)] ||
        index_.rows[static_cast<std::size_t>(dataset)].offset >= 0 || source_ == nullptr ||
        source_->sequential_fit.extract.empty()) {
        return;
    }
    asked_[static_cast<std::size_t>(dataset)] = true;
    if (wanted_.empty()) {
        QMetaObject::invokeMethod(this, &ScanSession::readWanted, Qt::QueuedConnection);
    }
    wanted_.push_back(dataset);
}

void ScanSession::readWanted() {
    if (wanted_.empty()) {
        return;
    }
    if (!metadata_stop_) {
        metadata_stop_ = std::make_shared<std::atomic<bool>>(false);
    }
    const std::shared_ptr<std::atomic<bool>> stop = metadata_stop_;
    const std::shared_ptr<const edi::Project> source = source_;
    const std::string directory = datasets_.directory;
    std::vector<std::pair<int, std::string>> wanted;
    for (const int dataset : wanted_) {
        wanted.emplace_back(dataset, datasets_.files[static_cast<std::size_t>(dataset)]);
    }
    wanted_.clear();
    // Each shown file is read once, for its extract rules only; the values reach this session only while it exists.
    const QPointer<ScanSession> self(this);
    (void)QtConcurrent::run([self, stop, source, directory, wanted = std::move(wanted)] {
        std::vector<std::pair<int, std::vector<std::string>>> done;
        for (const auto& [dataset, file] : wanted) {
            if (stop->load()) {
                return;
            }
            try {
                done.emplace_back(dataset, edi::scan_extract_values(*source, directory, file));
            } catch (const std::exception&) {
                done.emplace_back(dataset, std::vector<std::string>());
            }
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, stop, done = std::move(done)]() mutable {
                if (self.isNull() || stop->load() || done.empty()) {
                    return;
                }
                int first = done.front().first, last = first;
                for (auto& [dataset, values] : done) {
                    self->metadata_[static_cast<std::size_t>(dataset)] = std::move(values);
                    first = std::min(first, dataset);
                    last = std::max(last, dataset);
                }
                emit self->metadataLoaded(first, last);
            },
            Qt::QueuedConnection);
    });
}

void ScanSession::stopMetadata() {
    if (metadata_stop_) {
        metadata_stop_->store(true);
        metadata_stop_.reset();
    }
}

}  // namespace edi_app
