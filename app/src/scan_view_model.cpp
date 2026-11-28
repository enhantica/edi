// SPDX-License-Identifier: BSD-3-Clause
#include "scan_view_model.hpp"

#include <QCoreApplication>
#include <QFileInfo>
#include <QFontMetricsF>
#include <QMetaObject>
#include <QPointer>
#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <stdexcept>

#include "background.hpp"
#include "edi/display.hpp"
#include "edi/presentation.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"
#include "scan_session.hpp"

namespace edi_app {

namespace {

// Files read per background turn: few enough that the views fill in steadily, many enough to keep the turns cheap.
constexpr std::size_t kBatch = 8;
// The datasets read before any view has asked for its own: an even sample, enough for Stacked's most curves and a first
// Map, after which each view asks for what it shows.
constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();

// What every series row together may hold, in bytes (edi ADR-0089 point 5): a row keeps a summary of its pattern, never
// the pattern itself, at a resolution the series' size leaves room for.
constexpr std::size_t kSeriesBudget = std::size_t{64} << 20;

// A series row's pattern on d as the lowest and highest intensity of each of `buckets` buckets spaced evenly in log d
// (the same relative resolution over the whole range, so a peak at small d stays as sharp as one at large d), the two
// points of a bucket in the order of their d. A pattern with no more points than that is kept as it is.
void summarise_series_row(std::vector<double>& d, std::vector<double>& intensity, std::size_t buckets) {
    if (d.size() <= 2 * buckets) {
        return;
    }
    double low = std::numeric_limits<double>::infinity(), high = 0.0;
    for (const double v : d) {
        if (std::isfinite(v) && v > 0.0) {
            low = std::min(low, v);
            high = std::max(high, v);
        }
    }
    if (!(high > low)) {
        return;
    }
    const double log_low = std::log(low), span = std::log(high) - log_low;
    std::vector<std::ptrdiff_t> lowest(buckets, -1), highest(buckets, -1);
    for (std::size_t i = 0; i < d.size(); ++i) {
        if (!std::isfinite(d[i]) || d[i] <= 0.0 || !std::isfinite(intensity[i])) {
            continue;
        }
        const auto bucket = std::min(buckets - 1, static_cast<std::size_t>((std::log(d[i]) - log_low) / span * static_cast<double>(buckets)));
        if (lowest[bucket] < 0 || intensity[i] < intensity[static_cast<std::size_t>(lowest[bucket])]) {
            lowest[bucket] = static_cast<std::ptrdiff_t>(i);
        }
        if (highest[bucket] < 0 || intensity[i] > intensity[static_cast<std::size_t>(highest[bucket])]) {
            highest[bucket] = static_cast<std::ptrdiff_t>(i);
        }
    }
    std::vector<double> kept_d, kept_intensity;
    kept_d.reserve(2 * buckets);
    kept_intensity.reserve(2 * buckets);
    for (std::size_t b = 0; b < buckets; ++b) {
        if (lowest[b] < 0) {
            continue;
        }
        auto first = static_cast<std::size_t>(lowest[b]), second = static_cast<std::size_t>(highest[b]);
        if (d[second] < d[first]) {
            std::swap(first, second);
        }
        kept_d.push_back(d[first]);
        kept_intensity.push_back(intensity[first]);
        if (second != first) {
            kept_d.push_back(d[second]);
            kept_intensity.push_back(intensity[second]);
        }
    }
    d = std::move(kept_d);
    intensity = std::move(kept_intensity);
}

// The d of a native x, linear between the conversion's rows (its axis rising or falling); NaN beyond them, or with
// `clamp` the end row's d.
double d_of(const std::vector<double>& xs, const std::vector<double>& ds, double x, bool clamp) {
    if (xs.size() < 2 || !std::isfinite(x)) {
        return kNaN;
    }
    const bool rising = xs.back() > xs.front();
    const auto at = rising ? std::lower_bound(xs.begin(), xs.end(), x)
                           : std::lower_bound(xs.begin(), xs.end(), x, std::greater<>());
    if (at == xs.end()) {
        return clamp ? ds.back() : kNaN;
    }
    const std::size_t hi = static_cast<std::size_t>(at - xs.begin());
    if (*at == x) {
        return ds[hi];
    }
    if (hi == 0) {
        return clamp ? ds.front() : kNaN;
    }
    const std::size_t lo = hi - 1;
    return ds[lo] + (ds[hi] - ds[lo]) * (x - xs[lo]) / (xs[hi] - xs[lo]);
}

// An experiment's axis and its current d column, finite pairs only; empty without a current d column.
void conversion_of(const edi::ExperimentBase& experiment, std::vector<double>& xs, std::vector<double>& ds) {
    xs.clear();
    ds.clear();
    if (!experiment.data || !experiment.computed_current()) {
        return;
    }
    const std::vector<double>& x = experiment.data->axis();
    const std::vector<double>& d = experiment.data->d_spacing.values();
    for (std::size_t i = 0; i < x.size() && i < d.size(); ++i) {
        if (std::isfinite(x[i]) && std::isfinite(d[i])) {
            xs.push_back(x[i]);
            ds.push_back(d[i]);
        }
    }
}

// An experiment's axis and its calculated background, finite pairs only; empty when it sets no background
// (edi::has_background, fitted or not) or its computed columns are not current.
void background_of(const edi::ExperimentBase& experiment, std::vector<double>& xs, std::vector<double>& bs) {
    xs.clear();
    bs.clear();
    if (!experiment.data || !experiment.computed_current() || !edi::has_background(experiment)) {
        return;
    }
    const std::vector<double>& x = experiment.data->axis();
    const std::vector<double>& b = experiment.data->intensity_bkg.values();
    for (std::size_t i = 0; i < x.size() && i < b.size(); ++i) {
        if (std::isfinite(x[i]) && std::isfinite(b[i])) {
            xs.push_back(x[i]);
            bs.push_back(b[i]);
        }
    }
}

std::vector<std::pair<double, double>> excluded_of(const edi::ExperimentBase& experiment) {
    std::vector<std::pair<double, double>> out;
    for (const auto& [start, end] : edi::excluded_region_ranges(experiment.excluded_regions)) {
        if (std::isfinite(start) && std::isfinite(end)) {
            out.emplace_back(std::min(start, end), std::max(start, end));
        }
    }
    return out;
}

}  // namespace

ScanViewModel::ScanViewModel(QObject* parent) : QObject(parent) {
    delivery_.setSingleShot(true);
    delivery_.setInterval(50);
    connect(&delivery_, &QTimer::timeout, this, &ScanViewModel::publishDelivery);
    plan_.setSingleShot(true);
    plan_.setInterval(0);
    connect(&plan_, &QTimer::timeout, this, [this] {
        planReads();
        readNext();
    });
}

ScanViewModel::~ScanViewModel() { stop(); }

void ScanViewModel::clear() {
    stop();
    ++generation_;
    started_ = false;
    loaded_ = 0;
    publish(failed_, 0, &ScanViewModel::failedChanged);
    publish(error_, QString(), &ScanViewModel::errorChanged);
    value_problem_.clear();
    files_.clear();
    directory_.clear();
    source_.reset();
    datasets_.reset();
    session_ = nullptr;
    listing_ = nullptr;
    rule_ = {};
    patterns_.clear();
    values_.clear();
    value_texts_.clear();
    resetReads();
}

namespace {
// Whether two projects extract the same scan values: the same rules, target and pattern in order.
bool same_extract(const edi::Project* a, const edi::Project* b) {
    if (a == nullptr || b == nullptr) return a == b;
    const auto& x = a->sequential_fit.extract;
    const auto& y = b->sequential_fit.extract;
    if (x.size() != y.size()) return false;
    auto i = x.begin();
    for (auto j = y.begin(); j != y.end(); ++i, ++j) {
        if ((*i)->target.value() != (*j)->target.value() || (*i)->pattern.value() != (*j)->pattern.value() ||
            (*i)->required.get() != (*j)->required.get()) {
            return false;
        }
    }
    return true;
}
}  // namespace

void ScanViewModel::setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title) {
    const bool conversion_changed = readConversion(project);
    // Results read again over the same files (after a run or an undo) leave what was read: the patterns are the same.
    if (!joint_ && session != nullptr && project != nullptr && session->datasets().files == files_ &&
        session->datasets().directory == directory_ && extracted_title == extracted_title_ && !files_.empty() &&
        same_extract(source_.get(), project)) {
        // The values come from this session from now on (a reload is a new one).
        listing_ = session;
        if (session_ != nullptr) {
            rule_ = session->bankRule(*project);  // the project's rule as it is now
        }
        if (conversion_changed) {
            placeAxis();
            ++revision_;
            emit revisionChanged();
        }
        return;
    }
    // A rule edit over the same scan: its saved results were extracted under the earlier rules.
    const bool same_scan = session != nullptr && session->datasets().directory == directory_ && !directory_.empty();
    const bool edited = same_scan && (rules_edited_ || (source_ != nullptr && project != nullptr && !same_extract(source_.get(), project)));
    clear();
    rules_edited_ = edited;
    publish(joint_, false, &ScanViewModel::jointChanged);
    publish(native_shared_, true, &ScanViewModel::nativeSharedChanged);
    publish(row_labels_, QStringList(), &ScanViewModel::rowLabelsChanged);
    if (series_ && (session == nullptr || project == nullptr || !session->datasets().joint())) {
        series_ = false;
        series_experiments_.clear();
        emit seriesChanged();
        emit seriesExperimentsChanged();
    }
    if (session != nullptr && project != nullptr && !project->experiments.empty()) {
        files_ = session->datasets().files;
        directory_ = session->datasets().directory;
        source_ = std::make_shared<const edi::Project>(*project);
        // A series of joint fits draws its points on d: its experiments share no native axis.
        const bool series = session->datasets().joint();
        datasets_ = series ? std::make_shared<const edi::ScanDatasets>(session->datasets()) : nullptr;
        // What a series row's per-experiment rows are read against: the session's rule, and its index as each batch
        // is asked for (a fit adds rows meanwhile).
        session_ = series ? session : nullptr;
        listing_ = session;
        rule_ = series ? session->bankRule(*project) : edi::SeriesBankRule{};
        QStringList names;
        if (series) {
            for (const std::string& name : session->datasets().experiments) names.append(QString::fromStdString(name));
            if (rows_experiment_ >= names.size()) rows_experiment_ = -1;
        }
        if (series != series_ || names != series_experiments_) {
            series_ = series;
            series_experiments_ = names;
            emit seriesChanged();
            emit seriesExperimentsChanged();
        }
        if (series) {
            readSeriesBanks(project);
            publish(native_shared_, false, &ScanViewModel::nativeSharedChanged);
            publish(d_available_, true, &ScanViewModel::dAvailableChanged);
        }
        mode_ = project->experiment().effective_beam_mode();
        emit timeOfFlightChanged();
    }
    listing_values_ = source_ != nullptr && !source_->sequential_fit.extract.empty() && !extracted_title.isEmpty();
    has_values_ = listing_values_ && !(rows_by_bank_ && series_);
    extracted_title_ = extracted_title;
    emit valueTitleChanged();
    patterns_.assign(units(), {});
    values_.assign(units(), kNaN);
    value_texts_.assign(units(), QString());
    resetReads();
    placeAxis();
    placeRows();
    emit countChanged();
    emit loadedChanged();
    ++revision_;
    emit revisionChanged();
    if (wanted_) {
        start();
    }
}

void ScanViewModel::setJoint(const edi::Project* project) {
    // Several experiments fitted together or each alone (independent without a scan, ADR-0081).
    const std::string fitting = project != nullptr ? edi::fit_kind(*project) : std::string();
    const bool joint = project != nullptr && project->experiments.size() >= 2 &&
                       (fitting == "joint" || (fitting == "independent" && !project->sequential_fit.declared()));
    if (!joint && !joint_) {
        return;  // a scan, or nothing, stays as it is
    }
    if (joint && series_) {
        series_ = false;
        series_experiments_.clear();
        emit seriesChanged();
        emit seriesExperimentsChanged();
    }
    // Every experiment's points as they are now; one without data draws nothing and counts as not read.
    std::vector<Pattern> next;
    QStringList labels;
    bool shared = true, every_d = joint;
    edi::BeamModeEnum mode = mode_;
    if (joint) {
        mode = project->experiment().effective_beam_mode();
        for (const auto& experiment : project->experiments) {
            shared = shared && (experiment->effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH) ==
                                   (mode == edi::BeamModeEnum::CONSTANT_WAVELENGTH);
            Pattern pattern;
            labels.append(QString::fromStdString(experiment->name));
            if (experiment->data) {
                const std::vector<double>& x = experiment->data->axis();
                const std::vector<double>& y = experiment->data->intensity_meas.get();
                pattern.x.assign(x.begin(), x.end());
                pattern.intensity.assign(y.begin(), y.end());
                pattern.intensity.resize(pattern.x.size(), kNaN);
            }
            std::vector<double> xs;
            conversion_of(*experiment, xs, pattern.d);
            // The d column is kept beside the points, matched point by point when it covers them all.
            if (xs.size() != pattern.x.size() || xs != pattern.x) {
                std::vector<double> d;
                d.reserve(pattern.x.size());
                for (const double x : pattern.x) {
                    d.push_back(d_of(xs, pattern.d, x, false));
                }
                pattern.d = std::move(d);
            }
            every_d = every_d && xs.size() >= 2;
            std::vector<double> bs;
            background_of(*experiment, xs, bs);
            if (xs.size() >= 2) {
                for (const double x : pattern.x) {
                    pattern.background.push_back(d_of(xs, bs, x, false));
                }
            }
            pattern.excluded = excluded_of(*experiment);
            next.push_back(std::move(pattern));
        }
    }
    // Taken again after every edit and calculation: the same experiments with the same data change nothing, so a
    // running joint fit neither redraws the views nor resets their zoom.
    const auto same = [](const std::vector<double>& a, const std::vector<double>& b) {
        return std::equal(a.begin(), a.end(), b.begin(), b.end(),
                          [](double u, double v) { return u == v || (std::isnan(u) && std::isnan(v)); });
    };
    if (joint && joint_ && labels == row_labels_ && next.size() == patterns_.size() &&
        std::equal(next.begin(), next.end(), patterns_.begin(), [&same](const Pattern& a, const Pattern& b) {
            return same(a.x, b.x) && same(a.intensity, b.intensity) && same(a.d, b.d) &&
                   same(a.background, b.background) && a.excluded == b.excluded;
        })) {
        return;
    }
    const bool count_changed = next.size() != patterns_.size() || joint != joint_;
    clear();
    publish(joint_, joint, &ScanViewModel::jointChanged);
    has_values_ = false;
    extracted_title_.clear();
    emit valueTitleChanged();
    if (mode != mode_) {
        mode_ = mode;
        emit timeOfFlightChanged();
    }
    int empty = 0;
    for (const Pattern& pattern : next) {
        empty += pattern.x.empty() ? 1 : 0;
    }
    patterns_ = std::move(next);
    values_.assign(patterns_.size(), kNaN);
    value_texts_.assign(patterns_.size(), QString());
    loaded_ = static_cast<int>(patterns_.size());
    resetReads();
    state_.assign(patterns_.size(), State::Read);  // a joint fit's experiments come whole from the project
    publish(failed_, empty, &ScanViewModel::failedChanged);
    publish(d_available_, every_d, &ScanViewModel::dAvailableChanged);
    publish(native_shared_, shared, &ScanViewModel::nativeSharedChanged);
    publish(row_labels_, labels, &ScanViewModel::rowLabelsChanged);
    placeAxis();
    placeRows();
    if (count_changed) {
        emit countChanged();
    }
    emit loadedChanged();
    ++revision_;
    emit revisionChanged();
}

void ScanViewModel::setRowsExperiment(int experiment) {
    const int wanted = experiment >= 0 && experiment < series_experiments_.size() ? experiment : -1;
    if (wanted == rows_experiment_) {
        return;
    }
    rows_experiment_ = wanted;
    emit rowsExperimentChanged();
    if (series_) {
        restartReads();
    }
}

// The rows read again over the same points, from the first.
void ScanViewModel::restartReads() {
    stop();
    ++generation_;
    started_ = false;
    loaded_ = 0;
    publish(failed_, 0, &ScanViewModel::failedChanged);
    publish(error_, QString(), &ScanViewModel::errorChanged);
    has_values_ = listing_values_ && !(rows_by_bank_ && series_);
    emit valueTitleChanged();
    patterns_.assign(units(), {});
    values_.assign(units(), kNaN);
    value_texts_.assign(units(), QString());
    resetReads();
    placeAxis();
    placeRows();
    emit countChanged();
    emit loadedChanged();
    ++revision_;
    emit revisionChanged();
    if (wanted_) {
        start();
    }
}

void ScanViewModel::setWanted(bool wanted) {
    if (wanted == wanted_) {
        return;
    }
    wanted_ = wanted;
    emit wantedChanged();
    if (wanted_) {
        start();
        plan_.start();
    } else {
        // A batch under way finishes; nothing more is read while no view wants the scan.
        queue_.clear();
        publish(pending_, reading_patterns_, &ScanViewModel::pendingChanged);
    }
}

void ScanViewModel::setRowsByBank(bool on) {
    if (on == rows_by_bank_) {
        return;
    }
    rows_by_bank_ = on;
    emit rowsByBankChanged();
    if (series_) {
        restartReads();
    }
}

void ScanViewModel::setSeriesFocus(int point, int bank) {
    if (!series_) {
        bank_point_ = std::max(0, point);
        return;
    }
    if (rows_by_bank_) {
        if (point >= 0 && point != bank_point_) {
            bank_point_ = point;
            restartReads();
        }
        return;
    }
    bank_point_ = std::max(0, point);
    setRowsExperiment(bank);
}

void ScanViewModel::start() {
    if (started_ || units() == 0) {
        return;
    }
    started_ = true;
    stop_ = std::make_shared<std::atomic<bool>>(false);
    reading_ = false;
    reading_patterns_ = 0;
    planReads();
    readNext();
}

void ScanViewModel::resetReads() {
    state_.assign(units(), State::Unread);
    value_seen_.assign(units(), false);
    value_reading_.assign(units(), false);
    requests_.clear();
    queue_.clear();
    reading_ = false;
    reading_patterns_ = 0;
    values_known_ = 0;
    value_queue_.clear();
    plan_.stop();
    publish(pending_, 0, &ScanViewModel::pendingChanged);
}

void ScanViewModel::request(const void* who, std::vector<std::size_t> datasets) {
    const auto at = requests_.find(who);
    if (datasets.empty() ? at == requests_.end() : at != requests_.end() && at->second == datasets) {
        return;
    }
    if (datasets.empty()) {
        requests_.erase(at);
    } else {
        requests_[who] = std::move(datasets);
    }
    placeRange();
    plan_.start();
}

std::atomic<long long>& scanFileReads() {
    static std::atomic<long long> reads{0};
    return reads;
}

std::atomic<long long>& listFileReads() {
    static std::atomic<long long> reads{0};
    return reads;
}

int ScanViewModel::demandSize() const {
    std::set<std::size_t> all;
    for (const auto& [who, datasets] : requests_) all.insert(datasets.begin(), datasets.end());
    return static_cast<int>(all.size());
}

int ScanViewModel::unreadDemanded() const {
    std::set<std::size_t> all;
    for (const auto& [who, datasets] : requests_)
        for (const std::size_t unit : datasets)
            if (unit < state_.size() && state_[unit] != State::Read) all.insert(unit);
    return static_cast<int>(all.size());
}

void ScanViewModel::setShown(const void* who, bool shown) {
    const bool before = !shown_.empty();
    if (shown) {
        shown_.insert(who);
    } else {
        shown_.erase(who);
    }
    if (!before && !shown_.empty()) plan_.start();
}

void ScanViewModel::planReads() {
    // The one demand (edi ADR-0102 rule 6): the patterns the shown views ask for and, while their rows are placed by
    // scan value, the values of the files not yet placed. Nothing else is read: no sample before a view asks, nothing
    // ahead while idle, nothing while no view shows the scan or wants it.
    queue_.clear();
    value_queue_.clear();
    std::vector<bool> queued(state_.size(), false);
    if (wanted_ && !shown_.empty()) {
        for (const auto& [who, datasets] : requests_) {
            for (const std::size_t unit : datasets) {
                if (unit < state_.size() && !queued[unit] && (state_[unit] == State::Unread || state_[unit] == State::ValueOnly)) {
                    queued[unit] = true;
                    queue_.push_back(unit);
                }
            }
        }
        if (has_values_ && !rows_by_index_) {
            bool took = false;
            for (std::size_t unit = 0; unit < state_.size(); ++unit) {
                // A coordinate is tracked apart from its pattern: a pattern read in File order still needs its value
                // once the rows are placed by value again.
                if (value_seen_[unit] || value_reading_[unit] || state_[unit] == State::Reading || queued[unit]) continue;
                // A value the scan already holds (its results or the experiments list's reads) is taken, not read again.
                if (takeKnownValue(unit, state_[unit] == State::Unread)) {
                    took = true;
                } else {
                    value_queue_.push_back(unit);
                }
            }
            if (took && values_known_ == count()) {
                placeRows();
                ++revision_;
                emit revisionChanged();
            }
        }
    }
    publish(pending_, static_cast<int>(queue_.size() + value_queue_.size()) + reading_patterns_, &ScanViewModel::pendingChanged);
}

bool ScanViewModel::takeKnownValue(std::size_t unit, bool setState) {
    // A series point's value is its first experiment's file's, which the session holds under the point's key (crysta
    // writes one results row per point); by bank, a row is one bank at one point and has no coordinate of its own.
    if (listing_ == nullptr || (series_ && rows_by_bank_)) return false;
    // After a rule edit only the session's own reads under the current rules count; results rows are the earlier rules'.
    const std::vector<std::string>* extracted =
        !rules_edited_ ? listing_->extracted(static_cast<int>(unit))
        : same_extract(listing_->source(), source_.get()) ? listing_->listExtracted(static_cast<int>(unit))
                                                         : nullptr;
    if (extracted == nullptr) return false;
    double value = 0.0;
    if (!extracted->empty() && edi::parse_scan_number(extracted->front(), value)) {
        values_[unit] = value;
        value_texts_[unit] = QString::fromStdString(extracted->front()).trimmed();
    } else if (value_problem_.isEmpty()) {
        value_problem_ = QString::fromStdString(files_.at(unit)) +
                         (extracted->empty() ? QStringLiteral(": nothing is extracted")
                                             : QStringLiteral(": '%1' is not a number").arg(QString::fromStdString(extracted->front())));
    }
    value_seen_[unit] = true;
    ++values_known_;
    if (setState) state_[unit] = State::ValueOnly;
    return true;
}

void ScanViewModel::stop() {
    if (stop_) {
        stop_->store(true);
    }
}

void ScanViewModel::readNext() {
    if (reading_ || !started_ || (stop_ && stop_->load()) || shown_.empty()) {
        return;
    }
    std::vector<Unit> chosen_units;
    bool took_at_admission = false;
    while (chosen_units.size() < kBatch && !queue_.empty()) {
        const std::size_t unit = queue_.front();
        queue_.pop_front();
        if (unit < state_.size() && (state_[unit] == State::Unread || state_[unit] == State::ValueOnly)) {
            // Its scan value too only while the rows are placed by value and it has none, held or read (rule 6).
            bool with_value = has_values_ && !rows_by_index_ && !value_seen_[unit] && !value_reading_[unit];
            if (with_value && takeKnownValue(unit, false)) {
                with_value = false;
                took_at_admission = true;
            }
            state_[unit] = State::Reading;
            chosen_units.push_back({unit, false, with_value});
        }
    }
    reading_patterns_ = static_cast<int>(chosen_units.size());
    // The last missing coordinate taken from the session here places the rows now: no delivery will see it arrive.
    if (took_at_admission && values_known_ == count()) {
        placeRows();
        ++revision_;
        emit revisionChanged();
    }
    // Then the scan values the rows' placement still needs (planReads), each file read for its value alone.
    while (chosen_units.empty() && !value_queue_.empty()) {
        while (chosen_units.size() < kBatch && !value_queue_.empty()) {
            const std::size_t unit = value_queue_.front();
            value_queue_.pop_front();
            if (unit < state_.size() && state_[unit] != State::Reading && !value_seen_[unit] && !value_reading_[unit]) {
                if (state_[unit] == State::Unread) state_[unit] = State::Reading;
                value_reading_[unit] = true;
                chosen_units.push_back({unit, true, true});
            }
        }
    }
    if (chosen_units.empty()) {
        return;
    }
    reading_ = true;
    const QPointer<ScanViewModel> self(this);
    const std::uint64_t generation = generation_;
    const std::shared_ptr<std::atomic<bool>> stop = stop_;
    // The session's shared copy of its index, which only a series' rows read: never a copy per batch.
    static const auto kNoIndex = std::make_shared<const edi::ScanResultIndex>();
    const std::shared_ptr<const edi::ScanResultIndex> index = session_ != nullptr && datasets_ ? session_->indexSnapshot() : kNoIndex;
    // By bank the units are the banks at one point; otherwise the points (or a scan's files).
    const bool by_bank = rows_by_bank_ && series_;
    const std::size_t at_point = by_bank ? std::min<std::size_t>(static_cast<std::size_t>(bank_point_), files_.empty() ? 0 : files_.size() - 1) : 0;
    std::vector<std::string> batch;
    batch.reserve(chosen_units.size());
    for (const Unit& unit : chosen_units) {
        batch.push_back(by_bank ? files_.at(at_point) : files_.at(unit.index));
    }
    run_in_background([self, generation, stop, chosen_units, batch = std::move(batch), source = source_, directory = directory_,
                       mode = mode_, values = has_values_, datasets = datasets_, index, rule = rule_,
                       chosen = rows_experiment_, by_bank,
                       at_point] {
        std::vector<Read> done;
        for (std::size_t k = 0; k < batch.size(); ++k) {
            const std::string& key = batch[k];
            if (stop->load()) {
                break;
            }
            Read read;
            ++scanFileReads();
            // A series' row is its point on d; its place along the series comes from the first experiment's file.
            const std::size_t point = by_bank ? at_point : chosen_units[k].index;
            const bool value_only = chosen_units[k].value_only;
            const std::string file = datasets ? datasets->point_files.at(point).front() : key;
            if (datasets && !value_only) {
                try {
                    std::vector<std::size_t> experiments;
                    for (std::size_t e = 0; e < datasets->experiments.size(); ++e) {
                        if (by_bank ? e == chosen_units[k].index : chosen < 0 || static_cast<std::size_t>(chosen) == e)
                            experiments.push_back(e);
                    }
                    const edi::SeriesPointCheck check = edi::series_point_check(rule, *datasets, *index, point);
                    const std::vector<double> scales = edi::series_point_scales(*source, key, check);
                    edi::SeriesRowPattern row =
                        edi::series_row_pattern(*source, *datasets, point, experiments, scales, check);
                    if (experiments.size() == 1) {
                        read.bank = static_cast<int>(experiments.front());
                        read.scale = experiments.front() < scales.size() ? scales[experiments.front()] : 1.0;
                    }
                    if (row.d.empty()) {
                        throw std::runtime_error("the point has no pattern on d");
                    }
                    // Summarised here, off the GUI thread, and the full pattern released: every row together stays
                    // within the budget, its x, intensity, place on the axis and background as doubles.
                    const std::size_t rows = std::max<std::size_t>(1, by_bank ? datasets->experiments.size() : datasets->files.size());
                    const std::size_t buckets = std::clamp<std::size_t>(kSeriesBudget / (rows * 2 * 4 * sizeof(double)), 64, 4096);
                    summarise_series_row(row.d, row.intensity, buckets);
                    read.x = std::move(row.d);
                    read.intensity = std::move(row.intensity);
                } catch (const std::exception& refusal) {
                    read.error = QString::fromStdString(key) + QStringLiteral(": ") + QString::fromUtf8(refusal.what());
                    done.push_back(std::move(read));
                    continue;
                }
            }
            // The pattern: unreadable, it is not drawn and is counted as such.
            if (!datasets && !value_only) {
                try {
                    const edi::PdDataBase data = edi::read_scan_dataset(directory, file, mode);
                    const std::vector<double>& x = data.axis();
                    const std::vector<double>& y = data.intensity_meas.get();
                    if (std::none_of(x.begin(), x.end(), [](double value) { return std::isfinite(value); })) {
                        throw std::runtime_error("the pattern has no x range");
                    }
                    read.x.assign(x.begin(), x.end());
                    read.intensity.assign(y.begin(), y.end());
                    read.intensity.resize(read.x.size(), kNaN);
                } catch (const std::exception& refusal) {
                    read.error = QString::fromStdString(file) + QStringLiteral(": ") + QString::fromUtf8(refusal.what());
                    done.push_back(std::move(read));
                    continue;
                }
            }
            // Its place along the scan: without one the pattern is still drawn, and the rows stay by file index with
            // the reason.
            if (values && chosen_units[k].with_value) {
                read.value_tried = true;
                try {
                    const std::vector<std::string> extracted = edi::scan_extract_values(*source, directory, file);
                    double value = 0.0;
                    if (!extracted.empty() && edi::parse_scan_number(extracted.front(), value)) {
                        read.value = value;
                        read.value_text = QString::fromStdString(extracted.front()).trimmed();
                    } else {
                        read.value_problem = QString::fromStdString(file) +
                                             (extracted.empty() ? QStringLiteral(": nothing is extracted")
                                                                : QStringLiteral(": '%1' is not a number")
                                                                      .arg(QString::fromStdString(extracted.front())));
                    }
                } catch (const std::exception& refusal) {
                    read.value_problem = QString::fromStdString(file) + QStringLiteral(": ") + QString::fromUtf8(refusal.what());
                }
            }
            done.push_back(std::move(read));
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, generation, stop, chosen_units, done = std::move(done)]() mutable {
                if (self.isNull() || generation != self->generation_ || stop->load()) {
                    return;  // a read of an earlier listing, or a stopped one
                }
                self->deliver(chosen_units, done);
            },
            Qt::QueuedConnection);
    });
}

// A batch's reads, in scan order from `first`: each dataset keeps its points, placed on the axis shown, and the x range
// grows to hold them.
void ScanViewModel::deliver(const std::vector<Unit>& units, std::vector<Read>& done) {
    reading_ = false;
    reading_patterns_ = 0;
    const bool values_were_known = values_known_ == count();
    for (std::size_t i = 0; i < done.size() && i < units.size(); ++i) {
        Read& read = done[i];
        const std::size_t dataset = units[i].index;
        // A value is seen only where this unit read one: a pattern read without its value leaves it to be found.
        if (units[i].value_only) value_reading_[dataset] = false;
        if (read.value_tried && !value_seen_[dataset]) {
            value_seen_[dataset] = true;
            ++values_known_;
        }
        if (units[i].value_only) {
            // A pattern already read stays read; one not read is now known by its value alone.
            if (state_[dataset] == State::Reading) state_[dataset] = State::ValueOnly;
            if (!read.value_problem.isEmpty() && value_problem_.isEmpty()) value_problem_ = read.value_problem;
            values_[dataset] = read.value;
            value_texts_[dataset] = read.value_text;
            continue;
        }
        state_[dataset] = State::Read;
        ++loaded_;
        if (!read.error.isEmpty()) {
            if (error_.isEmpty()) {
                publish(error_, read.error, &ScanViewModel::errorChanged);
            }
            publish(failed_, failed_ + 1, &ScanViewModel::failedChanged);
            continue;
        }
        if (!read.value_problem.isEmpty() && value_problem_.isEmpty()) {
            value_problem_ = read.value_problem;
        }
        Pattern& pattern = patterns_[dataset];
        pattern.x = std::move(read.x);
        pattern.intensity = std::move(read.intensity);
        // A series' point is read on d: its x is its d (placePattern takes it as such, with no copy), and its background
        // and excluded regions are its bank's.
        if (series_) {
            pattern.d.clear();
            pattern.bank = read.bank;
            pattern.scale = read.scale;
            applySeriesBank(pattern);
        } else {
            pattern.excluded = template_excluded_;
        }
        placePattern(pattern);
        if (read.value_tried) {
            values_[dataset] = read.value;
            value_texts_[dataset] = read.value_text;
        }
    }
    // A batch cut short by a stop leaves its other units to be read again.
    for (std::size_t i = done.size(); i < units.size(); ++i) {
        if (state_[units[i].index] == State::Reading) state_[units[i].index] = State::Unread;
        if (units[i].value_only) value_reading_[units[i].index] = false;
    }
    placeRange();
    if (series_) publishBackground();
    planReads();
    // File-index rows and labels stay fixed while batches arrive; extracted values reorder them once every dataset's
    // value is known.
    if (has_values_ && !values_were_known && values_known_ == count()) placeRows();
    const bool complete = pending_ == 0;
    // The batches' patterns reach the views at most every 50 ms (ADR-0102 rule 4): a scan of tens of thousands of
    // files arrives in thousands of batches, and each drew the Stacked and Map views again. The last one at once.
    if (complete) {
        delivery_.stop();
        publishDelivery();
    } else if (!delivery_.isActive()) {
        delivery_.start();
    }
    readNext();
}

void ScanViewModel::publishDelivery() {
    emit loadedChanged();
    ++revision_;
    emit revisionChanged();
}

void ScanViewModel::placeRows() {
    // By value once every dataset has one; until then, and without an extract rule (a joint fit has none), by place.
    const bool by_value = has_values_ && !rows_by_index_ && values_known_ == count() &&
                          std::all_of(values_.begin(), values_.end(), [](double value) { return std::isfinite(value); });
    rows_ = by_value ? edi::scan_row_positions(values_)
                     : edi::scan_row_positions(std::vector<double>(patterns_.size(), kNaN));
    spans_ = edi::scan_row_spans(rows_);
    // Datasets at one scan value (a temperature held, or reached again) each keep a band and a row of their own.
    edi::separate_shared_rows(rows_, spans_);
    publish(rows_by_value_, by_value, &ScanViewModel::rowsByValueChanged);
    // An axis title starts with a capital, as every label (the owner's label rule): "File", "Datablock".
    QString title = by_value ? extracted_title_ : orderName();
    if (!title.isEmpty()) title[0] = title[0].toUpper();
    // Every dataset read and still placed by file although the scan extracts a value: say why.
    publish(row_note_,
            has_values_ && !rows_by_index_ && !by_value && values_known_ == count() && !value_problem_.isEmpty()
                ? tr("Rows by file: %1").arg(value_problem_)
                : QString(),
            &ScanViewModel::rowNoteChanged);
    // Each row's label: the value with the unit the extract rule's title gives in brackets ("temperature (K)"), the
    // file's name, or the datablock's.
    const qsizetype bracket = extracted_title_.lastIndexOf(QLatin1Char('('));
    const QString unit = bracket >= 0 && extracted_title_.endsWith(QLatin1Char(')'))
                             ? extracted_title_.mid(bracket + 1, extracted_title_.size() - bracket - 2).trimmed()
                             : QString();
    // Values share one number of decimals: one digit past the smallest gap between neighbouring values, so neighbours
    // read apart and no label carries the file's trailing zeros ("93.4840" beside "497.379").
    int decimals = 0;
    if (by_value) {
        std::vector<double> sorted;
        for (const double value : values_)
            if (std::isfinite(value)) sorted.push_back(value);
        std::sort(sorted.begin(), sorted.end());
        double gap = 0;
        for (std::size_t i = 1; i < sorted.size(); ++i)
            if (const double step = sorted[i] - sorted[i - 1]; step > 0 && (gap == 0 || step < gap)) gap = step;
        if (gap > 0) decimals = std::clamp(1 - static_cast<int>(std::floor(std::log10(gap))), 0, 4);
    }
    QStringList texts;
    for (std::size_t i = 0; i < patterns_.size(); ++i) {
        if (by_value) {
            const QString value = std::isfinite(values_[i]) ? QString::number(values_[i], 'f', decimals)
                                  : i < value_texts_.size()  ? value_texts_[i]
                                                             : QString();
            texts.append(unit.isEmpty() ? value : value + QLatin1Char(' ') + unit);
        } else if (joint_) {
            texts.append(static_cast<qsizetype>(i) < row_labels_.size() ? row_labels_[static_cast<qsizetype>(i)] : QString());
        } else if (rows_by_bank_ && series_) {
            texts.append(static_cast<qsizetype>(i) < series_experiments_.size() ? series_experiments_[static_cast<qsizetype>(i)] : QString());
        } else {
            texts.append(i < files_.size() ? QFileInfo(QString::fromStdString(files_[i])).fileName() : QString());
        }
    }
    const bool changed = texts != row_texts_;
    if (changed) {
        ++row_texts_revision_;
    }
    publish(row_texts_, texts, &ScanViewModel::rowTextsChanged);
    if (changed) {
        emit rowTextsRevisionChanged();
    }
    emit orderNameChanged();
    double low = 0.0, high = 1.0;
    if (!spans_.empty()) {
        low = std::min_element(spans_.begin(), spans_.end(), [](const auto& a, const auto& b) { return a.low < b.low; })->low;
        high = std::max_element(spans_.begin(), spans_.end(), [](const auto& a, const auto& b) { return a.high < b.high; })->high;
    }
    publish(row_title_, title, &ScanViewModel::rowTitleChanged);
    publish(row_min_, low, &ScanViewModel::rowMinChanged);
    publish(row_max_, high, &ScanViewModel::rowMaxChanged);
    double lowest = 0.0, highest = 0.0;
    if (!rows_.empty()) {
        lowest = *std::min_element(rows_.begin(), rows_.end());
        highest = *std::max_element(rows_.begin(), rows_.end());
    }
    publish(row_lowest_, lowest, &ScanViewModel::rowLowestChanged);
    publish(row_highest_, highest, &ScanViewModel::rowHighestChanged);
}

// The project's current d column against its own axis, finite pairs only, what a scan's d-spacing is read from, and the
// template's excluded regions, which every dataset of a scan shares.
bool ScanViewModel::readConversion(const edi::Project* project) {
    std::vector<double> xs, ds, bx, bs;
    std::vector<std::pair<double, double>> excluded;
    if (project != nullptr && !project->experiments.empty()) {
        conversion_of(project->experiment(), xs, ds);
        background_of(project->experiment(), bx, bs);
        excluded = excluded_of(project->experiment());
    }
    if (xs == template_x_ && ds == template_d_ && bx == template_bx_ && bs == template_bkg_ &&
        excluded == template_excluded_) {
        return false;
    }
    template_x_ = std::move(xs);
    template_d_ = std::move(ds);
    template_bx_ = std::move(bx);
    template_bkg_ = std::move(bs);
    template_excluded_ = std::move(excluded);
    if (!series_) {
        for (Pattern& pattern : patterns_) {
            pattern.excluded = template_excluded_;
        }
    }
    return true;
}

void ScanViewModel::readSeriesBanks(const edi::Project* project) {
    bank_d_.clear();
    bank_background_.clear();
    bank_excluded_.clear();
    if (project == nullptr) return;
    for (const auto& experiment : project->experiments) {
        std::vector<double> xs, ds, bx, bs;
        conversion_of(*experiment, xs, ds);
        background_of(*experiment, bx, bs);
        // The background on d, in rising d whatever the native axis.
        std::vector<std::pair<double, double>> on_d;
        for (std::size_t i = 0; i < bx.size() && i < bs.size(); ++i) {
            const double d = d_of(xs, ds, bx[i], false);
            if (std::isfinite(d) && std::isfinite(bs[i])) on_d.emplace_back(d, bs[i]);
        }
        std::sort(on_d.begin(), on_d.end());
        std::vector<double> d_column, b_column;
        for (const auto& [d, b] : on_d) {
            d_column.push_back(d);
            b_column.push_back(b);
        }
        // An end past this experiment's data runs on to the end of d (as good as 0 or infinity): another point's data reach a little
        // further than the template's, and their ends are excluded too.
        const auto end_of = [&](double x) {
            if (const double d = d_of(xs, ds, x, false); std::isfinite(d)) return d;
            const double clamped = d_of(xs, ds, x, true);
            if (!std::isfinite(clamped) || ds.empty()) return clamped;
            // Finite, so Q and sinθ/λ of either end are numbers too.
            return clamped <= std::min(ds.front(), ds.back()) ? 1e-12 : 1e12;
        };
        std::vector<std::pair<double, double>> excluded;
        for (const auto& [a, b] : excluded_of(*experiment)) {
            const double da = end_of(a), db = end_of(b);
            if (std::isfinite(da) && std::isfinite(db)) excluded.emplace_back(std::min(da, db), std::max(da, db));
        }
        bank_d_.push_back(std::move(d_column));
        bank_background_.push_back(std::move(b_column));
        bank_excluded_.push_back(std::move(excluded));
    }
}

void ScanViewModel::applySeriesBank(Pattern& pattern) const {
    pattern.background.clear();
    pattern.excluded.clear();
    const auto bank = static_cast<std::size_t>(pattern.bank);
    if (pattern.bank < 0 || bank >= bank_d_.size()) return;
    if (bank_d_[bank].size() >= 2 && pattern.scale != 0.0 && std::isfinite(pattern.scale)) {
        pattern.background.reserve(pattern.x.size());
        for (const double d : pattern.x) pattern.background.push_back(d_of(bank_d_[bank], bank_background_[bank], d, false) / pattern.scale);
    }
    pattern.excluded = bank_excluded_[bank];
}

void ScanViewModel::setConversion(const edi::Project* project) {
    // A calculation published: a joint fit's experiments are taken again (their d columns, their excluded regions);
    // a scan's d axis follows the template's conversion, as the pattern chart's does.
    if (joint_) {
        setJoint(project);
        return;
    }
    if (series_) {
        // Each row its bank's background and excluded regions again, then every row placed and the range taken anew.
        readSeriesBanks(project);
        for (Pattern& pattern : patterns_) {
            if (!pattern.x.empty()) applySeriesBank(pattern);
        }
        placeAxis();
        ++revision_;
        emit revisionChanged();
        return;
    }
    if (readConversion(project)) {
        placeAxis();
        ++revision_;
        emit revisionChanged();
    }
}

void ScanViewModel::setDSpacing(bool on) {
    if (on != dSpacing()) {
        setXAxis(QLatin1String(on ? "d_spacing" : "native"));
    }
}

QString ScanViewModel::xAxis() const {
    const std::string_view token = edi::pattern_axis_token(axis_);
    return QString::fromLatin1(token.data(), static_cast<qsizetype>(token.size()));
}

void ScanViewModel::setXAxis(const QString& token) {
    const edi::PatternAxis axis = edi::pattern_axis_from_token(token.toStdString());
    if (axis == axis_) {
        return;
    }
    const bool was_d = dSpacing();
    axis_ = axis;
    emit xAxisChanged();
    if (dSpacing() != was_d) {
        emit dSpacingChanged();
    }
    placeAxis();
    ++revision_;
    emit revisionChanged();
}

void ScanViewModel::setIncludedOnly(bool on) {
    if (on != included_only_) {
        included_only_ = on;
        // The range first: the chart starts over on it when told (onIncludedOnlyChanged), so it must be the new one.
        placeRange();
        emit includedOnlyChanged();
        ++revision_;
        emit revisionChanged();
    }
}

double ScanViewModel::widestRowText(const QList<int>& shown, const QFont& font) const {
    const QFontMetricsF metrics(font);
    double widest = 0.0;
    for (const int dataset : shown) {
        if (dataset >= 0 && dataset < row_texts_.size()) {
            widest = std::max(widest, metrics.horizontalAdvance(row_texts_.at(dataset)));
        }
    }
    return widest;
}

void ScanViewModel::setRowsByIndex(bool on) {
    if (on != rows_by_index_) {
        rows_by_index_ = on;
        emit rowsByIndexChanged();
        // By file the rows need no scan value; by value again they do (planReads).
        plan_.start();
        placeRows();
        ++revision_;
        emit revisionChanged();
    }
}

// One dataset on the axis shown: its own x, or d read off a joint fit's experiment's own d column or a scan's template
// conversion, linear between the conversion's rows; a point beyond the conversion has no d. Its excluded ranges follow,
// their ends clamped to the conversion's.
void ScanViewModel::placePattern(Pattern& pattern) {
    pattern.generation = ++pattern_generation_;
    pattern.excluded_shown.clear();
    // A scan's datasets share the template's background; a joint fit's experiment keeps its own; a series' row its
    // bank's (applySeriesBank).
    if (!joint_ && !series_) {
        pattern.background.clear();
        if (template_bx_.size() >= 2) {
            pattern.background.reserve(pattern.x.size());
            for (const double x : pattern.x) {
                pattern.background.push_back(d_of(template_bx_, template_bkg_, x, false));
            }
        }
    }
    // Experiments on different native axes have no x to share until d is given: nothing is placed.
    if (!d_shown_ && !native_shared_) {
        pattern.shown.assign(pattern.x.size(), kNaN);
        return;
    }
    if (!d_shown_) {
        pattern.shown = pattern.x;
        pattern.excluded_shown = pattern.excluded;
        return;
    }
    // Q and sinθ/λ: the values placed on d, converted.
    const auto onAxis = [this, &pattern] {
        if (axis_ != edi::PatternAxis::Q && axis_ != edi::PatternAxis::SinThetaOverLambda) {
            return;
        }
        // Q and sinθ/λ only from a positive d: a time-of-flight channel before the offset has d at or below zero, whose
        // Q is infinite or negative and would stretch the axis over nothing.
        for (double& x : pattern.shown) {
            x = std::isfinite(x) && x > 0.0 ? edi::d_on_axis(axis_, x) : kNaN;
        }
        for (auto& [a, b] : pattern.excluded_shown) {
            const double ca = edi::d_on_axis(axis_, a), cb = edi::d_on_axis(axis_, b);
            a = std::min(ca, cb);
            b = std::max(ca, cb);
        }
    };
    if (series_) {
        pattern.shown = pattern.x;
        pattern.excluded_shown = pattern.excluded;
        onAxis();
        return;
    }
    if (joint_) {
        pattern.shown = pattern.d;
        std::vector<double> xs, ds;
        for (std::size_t i = 0; i < pattern.x.size() && i < pattern.d.size(); ++i) {
            if (std::isfinite(pattern.x[i]) && std::isfinite(pattern.d[i])) {
                xs.push_back(pattern.x[i]);
                ds.push_back(pattern.d[i]);
            }
        }
        for (const auto& [a, b] : pattern.excluded) {
            const double da = d_of(xs, ds, a, true), db = d_of(xs, ds, b, true);
            if (std::isfinite(da) && std::isfinite(db)) {
                pattern.excluded_shown.emplace_back(std::min(da, db), std::max(da, db));
            }
        }
        onAxis();
        return;
    }
    pattern.shown.resize(pattern.x.size());
    for (std::size_t i = 0; i < pattern.x.size(); ++i) {
        pattern.shown[i] = d_of(template_x_, template_d_, pattern.x[i], false);
    }
    for (const auto& [a, b] : pattern.excluded) {
        const double da = d_of(template_x_, template_d_, a, true), db = d_of(template_x_, template_d_, b, true);
        if (std::isfinite(da) && std::isfinite(db)) {
            pattern.excluded_shown.emplace_back(std::min(da, db), std::max(da, db));
        }
    }
    onAxis();
}

void ScanViewModel::placeRange() {
    double low = std::numeric_limits<double>::infinity(), high = -low;
    // Over what the shown views ask for only (ADR-0102 rule 6): the x range follows the views, never the rows an
    // earlier view happened to load. With no view asking it stays as it was, for the next view to ask.
    if (requests_.empty()) return;
    std::vector<bool> asked(patterns_.size(), false);
    for (const auto& [who, datasets] : requests_) {
        for (const std::size_t set : datasets)
            if (set < asked.size()) asked[set] = true;
    }
    for (std::size_t set = 0; set < patterns_.size(); ++set) {
        Pattern& pattern = patterns_[set];
        if (!asked[set]) continue;
        if (pattern.range_generation != pattern.generation || pattern.range_included != included_only_) {
            pattern.range_low = std::numeric_limits<double>::infinity();
            pattern.range_high = -pattern.range_low;
            for (const double x : pattern.shown) {
                if (std::isfinite(x) && !(included_only_ && excludedAt(pattern, x))) {
                    pattern.range_low = std::min(pattern.range_low, x);
                    pattern.range_high = std::max(pattern.range_high, x);
                }
            }
            pattern.range_generation = pattern.generation;
            pattern.range_included = included_only_;
        }
        low = std::min(low, pattern.range_low);
        high = std::max(high, pattern.range_high);
    }
    if (!(high > low)) {
        low = 0.0;
        high = 1.0;
    }
    publish(axis_min_, low, &ScanViewModel::xMinChanged);
    publish(axis_max_, high, &ScanViewModel::xMaxChanged);
}

void ScanViewModel::publishBackground() {
    const bool any = joint_ || series_ ? std::any_of(patterns_.begin(), patterns_.end(),
                                          [](const Pattern& pattern) { return !pattern.background.empty(); })
                            : template_bx_.size() >= 2;
    publish(background_available_, any, &ScanViewModel::backgroundAvailableChanged);
}

// Every dataset on the axis shown, its range and its title.
void ScanViewModel::placeAxis() {
    if (series_) {
        publish(d_available_, true, &ScanViewModel::dAvailableChanged);
    } else if (!joint_) {
        publish(d_available_, template_x_.size() >= 2, &ScanViewModel::dAvailableChanged);
    }
    // d when asked for, and always for experiments that share no native axis, once it is given.
    const bool d = (axis_ != edi::PatternAxis::Native || !native_shared_) && d_available_;
    publish(d_shown_, d, &ScanViewModel::dShownChanged);
    for (Pattern& pattern : patterns_) {
        placePattern(pattern);
    }
    placeRange();
    publishBackground();
    // The axis is titled by its data item's dictionary label and units (edi ADR-0051).
    const char* const axis = d || !native_shared_                                  ? "data.d_spacing"
                             : mode_ == edi::BeamModeEnum::CONSTANT_WAVELENGTH ? "data.two_theta"
                                                                               : "data.time_of_flight";
    std::string title = edi::label(axis) + " (" + edi::units_label(axis) + ")";
    if (d && (axis_ == edi::PatternAxis::Q || axis_ == edi::PatternAxis::SinThetaOverLambda)) {
        title = edi::pattern_axis_title(axis_);
    }
    publish(x_title_, QString::fromStdString(title), &ScanViewModel::xTitleChanged);
}

bool ScanViewModel::excludedAt(const Pattern& pattern, double x) {
    return std::any_of(pattern.excluded_shown.begin(), pattern.excluded_shown.end(),
                       [x](const std::pair<double, double>& range) { return x >= range.first && x <= range.second; });
}

int ScanViewModel::datasetAt(double row) const {
    for (std::size_t i = 0; i < spans_.size(); ++i) {
        if (row >= spans_[i].low && row < spans_[i].high) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

double ScanViewModel::rowOf(int dataset) const {
    return dataset >= 0 && static_cast<std::size_t>(dataset) < rows_.size() ? rows_[static_cast<std::size_t>(dataset)]
                                                                           : kNaN;
}

double ScanViewModel::rowLowEdge(int dataset) const {
    return dataset >= 0 && static_cast<std::size_t>(dataset) < spans_.size() ? spans_[static_cast<std::size_t>(dataset)].low
                                                                             : kNaN;
}

double ScanViewModel::rowHighEdge(int dataset) const {
    return dataset >= 0 && static_cast<std::size_t>(dataset) < spans_.size() ? spans_[static_cast<std::size_t>(dataset)].high
                                                                             : kNaN;
}

}  // namespace edi_app
