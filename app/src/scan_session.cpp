// SPDX-License-Identifier: BSD-3-Clause
#include "scan_session.hpp"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFuture>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QMetaObject>
#include <QPointer>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string_view>

#include "background.hpp"
#include "edi/io.hpp"

namespace edi_app {
namespace {

namespace fs = std::filesystem;

fs::path analysis_dir(const edi::Project& project) { return fs::path(project.path) / "analysis"; }

const char* const kResultFiles[] = {"results.csv", "results-provenance.csv", "scan-run.json", "scan-notes.csv"};
constexpr int kResultFileCount = 4;

std::optional<std::string>* slot(ScanSession::Files& files, int which) {
    return which == 0 ? &files.results : which == 1 ? &files.provenance : which == 2 ? &files.run : &files.skipped;
}

const std::optional<std::string>* slot(const ScanSession::Files& files, int which) {
    return which == 0 ? &files.results : which == 1 ? &files.provenance : which == 2 ? &files.run : &files.skipped;
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
    metadata_errors_.clear();
    loaded_.clear();
    // A new generation: a read still in flight from before delivers nothing, and does not hold up this one's queue.
    ++metadata_generation_;
    reading_ = false;
    readRun(project);
    return reindex(project);
}

QString ScanSession::readRun(const edi::Project& project) {
    // Only a provenance file that is not there is a legacy run; one that is there must read whole: the template it
    // names, the last kind, a known outcome, a finite non-negative time or none.
    run_ = {};
    const auto invalid = [this](const QString& why) {
        run_ = {};
        run_.invalid = true;
        run_.error = QStringLiteral("analysis/scan-run.json: %1").arg(why);
        return run_.error;
    };
    std::optional<std::string> bytes;
    try {
        bytes = read_file(analysis_dir(project) / "scan-run.json");
    } catch (const std::exception& refusal) {
        return invalid(QString::fromUtf8(refusal.what()));
    }
    if (!bytes) {
        return {};
    }
    QJsonParseError parse;
    const QJsonDocument document = QJsonDocument::fromJson(QByteArray::fromStdString(*bytes), &parse);
    if (parse.error != QJsonParseError::NoError || !document.isObject()) {
        return invalid(QStringLiteral("not a JSON object"));
    }
    const QJsonObject object = document.object();
    const QJsonValue identity = object.value(QStringLiteral("template"));
    const QJsonValue last = object.value(QStringLiteral("last"));
    const QJsonValue outcome = object.value(QStringLiteral("outcome"));
    const QJsonValue seconds = object.value(QStringLiteral("seconds"));
    const QJsonValue mixed = object.value(QStringLiteral("mixed"));
    static const QStringList outcomes{QString(), QStringLiteral("success"), QStringLiteral("maxIterations"),
                                      QStringLiteral("noStep"), QStringLiteral("notConverged"),
                                      QStringLiteral("stopped"), QStringLiteral("failed")};
    if (!identity.isString() || identity.toString().isEmpty()) {
        return invalid(QStringLiteral("no template identity"));
    }
    if (!last.isString() || (last.toString() != QLatin1String("scan") && last.toString() != QLatin1String("single"))) {
        return invalid(QStringLiteral("no last fit kind"));
    }
    if (!outcome.isString() || !outcomes.contains(outcome.toString())) {
        return invalid(QStringLiteral("an unknown outcome"));
    }
    if (!seconds.isUndefined() && (!seconds.isDouble() || !std::isfinite(seconds.toDouble()) || seconds.toDouble() < 0.0)) {
        return invalid(QStringLiteral("a time that is not a finite non-negative number"));
    }
    if (!mixed.isUndefined() && !mixed.isBool()) {
        return invalid(QStringLiteral("a mixed flag that is not true or false"));
    }
    run_.identity = identity.toString().toStdString();
    run_.last_single = last.toString() == QLatin1String("single");
    run_.outcome = outcome.toString();
    run_.seconds = seconds.isUndefined() ? -1.0 : seconds.toDouble();
    run_.mixed = mixed.toBool(false);
    return {};
}

QString ScanSession::reindex(const edi::Project& project, bool writing) {
    // The old index goes first: a scan's two indexes at once would double what it holds at the end of a run.
    index_ = {};
    index_ = edi::index_scan_results(project, datasets_, places_, writing);
    return QString::fromStdString(index_.error);
}

int ScanSession::place(const std::string& file) const {
    const auto found = places_.find(file);
    return found == places_.end() ? -1 : static_cast<int>(found->second);
}

int ScanSession::addRow(const edi::Project& project, const std::vector<std::string>& cells,
                        const std::string& termination, QString& error) {
    if (!index_.error.empty()) {
        error = QString::fromStdString(index_.error);
        return -1;
    }
    if (index_.header.empty()) {
        // The run's first row: the header is on disk now, before it (the run is still writing).
        reindex(project, true);
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
        row.termination = termination;
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
    {
        std::ifstream input(analysis_dir(project) / "results.csv", std::ios::binary);
        std::string header;
        if (!std::getline(input, header) || split(header) != index_.header) {
            throw std::invalid_argument("analysis/results.csv changed under the app: its header is not the one read "
                                        "before");
        }
    }
    std::vector<std::string> cells = edi::read_scan_row(project, index_.rows[dataset].offset);
    const std::string& expected = datasets_.files[static_cast<std::size_t>(dataset)];
    if (cells.size() != index_.header.size() || edi::scan_row_file(index_, cells) != expected) {
        throw std::invalid_argument("analysis/results.csv changed under the app: the row for '" + expected +
                                    "' is no longer where it was");
    }
    // Checked again as it was when indexed: a row edited since is refused, never shown in part.
    if (edi::scan_row_facts(project, places_, index_, cells).first != static_cast<std::size_t>(dataset)) {
        throw std::invalid_argument("analysis/results.csv changed under the app: the row for '" + expected +
                                    "' names another file");
    }
    return cells;
}

QString ScanSession::outcome(int dataset) const {
    if (dataset >= 0 && dataset < static_cast<int>(index_.rows.size()) && index_.rows[dataset].skipped) {
        return QStringLiteral("skipped");
    }
    if (dataset < 0 || dataset >= static_cast<int>(index_.rows.size()) || index_.rows[dataset].offset < 0) {
        return {};
    }
    // From the row's own facts: converged, else the reason crysta's ledger recorded when the file was fitted; a row
    // fitted before the ledger recorded reasons did not converge for a reason no one knows now.
    const edi::ScanResultIndex::Row& row = index_.rows[dataset];
    if (row.converged) {
        return QStringLiteral("success");
    }
    if (row.termination == "refused" || !row.refusal.empty()) {
        return QStringLiteral("refused");
    }
    if (row.termination == "max_iter_exhausted") {
        return QStringLiteral("maxIterations");
    }
    if (row.termination == "no_accepted_step") {
        return QStringLiteral("noStep");
    }
    return QStringLiteral("notConverged");
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
    // The columns mean what the indexed header says only while the file still has that header.
    if (!std::getline(input, line) || split(line) != index_.header) {
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
        // A refused file's row holds the values its fit started from, not a result: it is not drawn.
        if (dataset >= 0 && cells[index_.chi] != "nan" && edi::parse_scan_number(cells[value_column], value) &&
            edi::parse_scan_number(cells[uncertainty_column], uncertainty)) {
            visit(dataset, value, uncertainty);
        }
    }
}

QString ScanSession::writeRun(const edi::Project& project, const Run& run) {
    run_ = run;
    QJsonObject object{{QStringLiteral("template"), QString::fromStdString(run.identity)},
                       {QStringLiteral("outcome"), run.outcome},
                       {QStringLiteral("last"), run.last_single ? QStringLiteral("single") : QStringLiteral("scan")},
                       {QStringLiteral("mixed"), run.mixed}};
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
    // The name, title and description (project.edi) and the fitting mode are not the template: changing them leaves
    // the results current. The minimizer's settings are part of it: rows fitted under another bound or descent are
    // another generation.
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
            if (!line.starts_with("_fitting_mode.")) {
                hash.addData(QByteArrayView(line.data(), static_cast<qsizetype>(line.size())));
                hash.addData(QByteArrayView("\n", 1));
            }
            start = end + 1;
        }
    }
    return hash.result().toHex().toStdString();
}

namespace {

// The earlier result files wait here while they are replaced, so a failure can always put them back; a failure that
// cannot leaves them here, and the refusal says so.
// One directory per replacement, never reused: the files a fresh run or Reset fits took stay there until an Undo puts
// them back, so they are on disk whatever fails later.
fs::path set_aside_dir(const edi::Project& project, const std::string& name) {
    return analysis_dir(project) / ".edi-set-aside" / name;
}

std::string fresh_name(const char* kind) {
    static int serial = 0;
    const auto now = std::chrono::system_clock::now().time_since_epoch();
    return std::string(kind) + "-" + std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(now).count()) +
           "-" + std::to_string(++serial);
}

// Renames `from` over `to`. The source is proven first, and nothing is removed before the rename, which replaces
// `to` in one step: a failure leaves both as they were.
void move_file(const fs::path& from, const fs::path& to) {
    std::error_code error;
    if (!fs::exists(from, error)) {
        throw std::runtime_error("cannot move " + from.string() + ": it is not there");
    }
    fs::rename(from, to, error);
    if (error) {
        throw std::runtime_error("cannot move " + from.string() + " to " + to.string() + ": " + error.message());
    }
}

// Moves the present result files aside, recording in `moved` each one that moved; a failure throws with `moved`
// telling the caller, which alone undoes them, what to move back.
void set_aside(const edi::Project& project, const ScanSession::Files& present, const fs::path& aside,
               std::vector<int>& moved) {
    const fs::path directory = analysis_dir(project);
    fs::create_directories(aside);
    for (int which = 0; which < kResultFileCount; ++which) {
        if (*slot(present, which)) {
            move_file(directory / kResultFiles[which], aside / kResultFiles[which]);
            moved.push_back(which);
        }
    }
}

// Moves back what `moved` says went aside; false when one could not (it stays aside).
bool move_back(const edi::Project& project, const fs::path& aside, const std::vector<int>& moved) {
    bool all = true;
    for (const int which : moved) {
        try {
            move_file(aside / kResultFiles[which], analysis_dir(project) / kResultFiles[which]);
        } catch (const std::exception&) {
            all = false;
        }
    }
    return all;
}

void drop_set_aside(const fs::path& aside) {
    std::error_code ignored;
    fs::remove_all(aside, ignored);
}

QString kept_aside(const fs::path& aside, const std::exception& refusal) {
    return QStringLiteral("%1; the earlier result files are kept in %2")
        .arg(QString::fromUtf8(refusal.what()), QString::fromStdString(aside.string()));
}

}  // namespace

QString ScanSession::takeFiles(const edi::Project& project, Files& taken) {
    const fs::path directory = analysis_dir(project);
    taken = {};
    try {
        for (int which = 0; which < kResultFileCount; ++which) {
            *slot(taken, which) = read_file(directory / kResultFiles[which]);
        }
    } catch (const std::exception& refusal) {
        return QString::fromUtf8(refusal.what());
    }
    // Set aside, all or none, and kept there until an Undo puts them back (the caller holds the bytes too).
    const fs::path aside = set_aside_dir(project, fresh_name("taken"));
    std::vector<int> moved;
    try {
        set_aside(project, taken, aside, moved);
    } catch (const std::exception& refusal) {
        if (!move_back(project, aside, moved)) {
            return kept_aside(aside, refusal);
        }
        drop_set_aside(aside);
        return QString::fromUtf8(refusal.what());
    }
    taken.kept = aside.string();
    run_ = {};
    return {};
}

QString ScanSession::putFiles(const edi::Project& project, const Files& files) {
    const fs::path directory = analysis_dir(project);
    Files current;
    try {
        fs::create_directories(directory);
        for (int which = 0; which < kResultFileCount; ++which) {
            *slot(current, which) = read_file(directory / kResultFiles[which]);
        }
    } catch (const std::exception& refusal) {
        return QString::fromUtf8(refusal.what());
    }
    // 1. The wanted files written beside their places; a failure here changes nothing.
    Files wanted = files;
    std::vector<int> staged;
    try {
        for (int which = 0; which < kResultFileCount; ++which) {
            if (const std::optional<std::string>& text = *slot(wanted, which)) {
                const fs::path path = directory / (std::string(kResultFiles[which]) + ".edi-staged");
                std::ofstream output(path, std::ios::binary | std::ios::trunc);
                output << *text;
                output.close();
                if (!output) {
                    throw std::runtime_error("cannot write " + path.string());
                }
                staged.push_back(which);
            }
        }
    } catch (const std::exception& refusal) {
        for (const int which : staged) {
            std::error_code ignored;
            fs::remove(directory / (std::string(kResultFiles[which]) + ".edi-staged"), ignored);
        }
        return QString::fromUtf8(refusal.what());
    }
    // 2. The present files set aside; 3. the staged ones moved in. A failure puts the earlier ones back.
    std::vector<int> moved_aside, moved_in;
    const fs::path aside = set_aside_dir(project, fresh_name("replaced"));
    try {
        set_aside(project, current, aside, moved_aside);
        for (const int which : staged) {
            move_file(directory / (std::string(kResultFiles[which]) + ".edi-staged"), directory / kResultFiles[which]);
            moved_in.push_back(which);
        }
    } catch (const std::exception& refusal) {
        // Undone here alone, exactly as far as it went: the files moved in go back to their staged names (the bytes
        // to put back stay on disk), then the files set aside return.
        bool whole = true;
        for (const int which : moved_in) {
            try {
                move_file(directory / kResultFiles[which], directory / (std::string(kResultFiles[which]) + ".edi-staged"));
            } catch (const std::exception&) {
                whole = false;
            }
        }
        whole = move_back(project, aside, moved_aside) && whole;
        if (!whole) {
            return kept_aside(aside, refusal);
        }
        for (const int which : staged) {
            std::error_code ignored;
            fs::remove(directory / (std::string(kResultFiles[which]) + ".edi-staged"), ignored);
        }
        drop_set_aside(aside);
        return QString::fromUtf8(refusal.what());
    }
    // Put back: the replaced files and the copies kept when these were taken go.
    drop_set_aside(aside);
    if (!files.kept.empty()) {
        drop_set_aside(fs::path(files.kept));
    }
    readRun(project);
    return {};
}

bool ScanSession::runFile(const edi::Project& project, std::optional<std::string>& bytes) const {
    try {
        bytes = read_file(analysis_dir(project) / kResultFiles[2]);
        return true;
    } catch (const std::exception&) {
        bytes.reset();
        return false;  // there, but unreadable: not the same as absent
    }
}

QString ScanSession::putRunFile(const edi::Project& project, const std::optional<std::string>& bytes) {
    try {
        put_file(analysis_dir(project) / kResultFiles[2], bytes);
    } catch (const std::exception& refusal) {
        return QString::fromUtf8(refusal.what());
    }
    readRun(project);
    return {};
}

QString ScanSession::swapRunFile(const edi::Project& project, const std::optional<std::string>& bytes,
                                 std::string& kept) {
    const fs::path record = analysis_dir(project) / kResultFiles[2];
    const fs::path aside = set_aside_dir(project, fresh_name("run"));
    std::error_code error;
    const bool present = fs::exists(record, error);
    try {
        fs::create_directories(aside);
        if (present) {
            move_file(record, aside / kResultFiles[2]);
        }
    } catch (const std::exception& refusal) {
        drop_set_aside(aside);
        return QString::fromUtf8(refusal.what());
    }
    try {
        put_file(record, bytes);
    } catch (const std::exception& refusal) {
        if (present) {
            try {
                move_file(aside / kResultFiles[2], record);
            } catch (const std::exception&) {
                return QStringLiteral("%1; the run record is kept in %2")
                    .arg(QString::fromUtf8(refusal.what()), QString::fromStdString(aside.string()));
            }
        }
        drop_set_aside(aside);
        return QString::fromUtf8(refusal.what());
    }
    kept = aside.string();
    readRun(project);
    return {};
}

void ScanSession::dropRunFile(const std::string& kept) {
    drop_set_aside(fs::path(kept));
}

QString ScanSession::restoreRunFile(const edi::Project& project, const std::string& kept) {
    const fs::path record = analysis_dir(project) / kResultFiles[2];
    const fs::path aside(kept);
    try {
        std::error_code error;
        if (fs::exists(aside / kResultFiles[2], error)) {
            move_file(aside / kResultFiles[2], record);  // replaces the earlier record in one step
        } else {
            put_file(record, std::nullopt);  // there was none before the swap
        }
    } catch (const std::exception& refusal) {
        readRun(project);
        return QStringLiteral("%1; the newer run record is kept in %2")
            .arg(QString::fromUtf8(refusal.what()), QString::fromStdString(aside.string()));
    }
    drop_set_aside(aside);
    readRun(project);
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

QString ScanSession::metadataError(int dataset) const {
    const auto found = metadata_errors_.find(dataset);
    return found == metadata_errors_.end() ? QString() : found->second;
}

namespace {
constexpr std::size_t kMetadataBatch = 64;     // files read per background task
constexpr std::size_t kMetadataQueue = 256;    // requests waiting; older ones are dropped and asked again when shown
constexpr std::size_t kMetadataCache = 4096;   // datasets holding read values; the oldest are dropped first
}  // namespace

void ScanSession::want(int dataset) {
    if (dataset < 0 || dataset >= static_cast<int>(asked_.size()) || asked_[static_cast<std::size_t>(dataset)] ||
        index_.rows[static_cast<std::size_t>(dataset)].offset >= 0 || source_ == nullptr ||
        source_->sequential_fit.extract.empty()) {
        return;
    }
    asked_[static_cast<std::size_t>(dataset)] = true;
    if (wanted_.empty() && !reading_) {
        QMetaObject::invokeMethod(this, &ScanSession::readWanted, Qt::QueuedConnection);
    }
    wanted_.push_back(dataset);
    // The newest requests are the rows on screen now; the oldest past the bound are forgotten until shown again.
    if (wanted_.size() > kMetadataQueue) {
        const std::size_t drop = wanted_.size() - kMetadataQueue;
        for (std::size_t i = 0; i < drop; ++i) {
            asked_[static_cast<std::size_t>(wanted_[i])] = false;
        }
        wanted_.erase(wanted_.begin(), wanted_.begin() + static_cast<std::ptrdiff_t>(drop));
    }
}

void ScanSession::readWanted() {
    if (wanted_.empty() || reading_) {
        return;
    }
    if (!metadata_stop_) {
        metadata_stop_ = std::make_shared<std::atomic<bool>>(false);
    }
    const std::shared_ptr<std::atomic<bool>> stop = metadata_stop_;
    const std::shared_ptr<const edi::Project> source = source_;
    const std::string directory = datasets_.directory;
    const std::uint64_t generation = metadata_generation_;
    // The newest batch first: the rows on screen now.
    const std::size_t take = std::min(kMetadataBatch, wanted_.size());
    std::vector<std::pair<int, std::string>> batch;
    for (std::size_t i = wanted_.size() - take; i < wanted_.size(); ++i) {
        batch.emplace_back(wanted_[i], datasets_.files[static_cast<std::size_t>(wanted_[i])]);
    }
    wanted_.resize(wanted_.size() - take);
    reading_ = true;
    // Each file is read once, for its extract rules only; the values reach this session only while it exists.
    const QPointer<ScanSession> self(this);
    run_in_background([self, stop, source, directory, generation, batch = std::move(batch)] {
        struct Read {
            int dataset;
            std::vector<std::string> values;
            QString error;
        };
        std::vector<Read> done;
        for (const auto& [dataset, file] : batch) {
            if (stop->load()) {
                break;
            }
            try {
                done.push_back({dataset, edi::scan_extract_values(*source, directory, file), {}});
            } catch (const std::exception& refusal) {
                done.push_back({dataset, {}, QString::fromUtf8(refusal.what())});
            }
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, stop, generation, done = std::move(done)]() mutable {
                if (self.isNull() || generation != self->metadata_generation_) {
                    return;  // a read of an earlier listing: its results and its running state are not this one's
                }
                self->reading_ = false;
                if (stop->load()) {
                    self->readWanted();
                    return;
                }
                int first = std::numeric_limits<int>::max(), last = -1;
                for (Read& read : done) {
                    const auto index = static_cast<std::size_t>(read.dataset);
                    if (read.error.isEmpty()) {
                        self->metadata_[index] = std::move(read.values);
                        self->loaded_.push_back(read.dataset);
                    } else {
                        // A failed read is named, and not tried again until the scan is listed again.
                        self->metadata_errors_[read.dataset] = read.error;
                    }
                    first = std::min(first, read.dataset);
                    last = std::max(last, read.dataset);
                }
                while (self->loaded_.size() > kMetadataCache) {
                    const auto oldest = static_cast<std::size_t>(self->loaded_.front());
                    self->loaded_.pop_front();
                    self->metadata_[oldest].reset();
                    self->asked_[oldest] = false;
                }
                if (last >= 0) {
                    emit self->metadataLoaded(first, last);
                }
                self->readWanted();
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
