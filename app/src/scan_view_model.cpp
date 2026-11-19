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

ScanViewModel::ScanViewModel(QObject* parent) : QObject(parent) {}

ScanViewModel::~ScanViewModel() { stop(); }

void ScanViewModel::clear() {
    stop();
    ++generation_;
    started_ = false;
    next_ = 0;
    loaded_ = 0;
    publish(failed_, 0, &ScanViewModel::failedChanged);
    publish(error_, QString(), &ScanViewModel::errorChanged);
    value_problem_.clear();
    files_.clear();
    directory_.clear();
    source_.reset();
    datasets_.reset();
    session_ = nullptr;
    rule_ = {};
    patterns_.clear();
    values_.clear();
    value_texts_.clear();
}

void ScanViewModel::setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title) {
    const bool conversion_changed = readConversion(project);
    // Results read again over the same files (after a run or an undo) leave what was read: the patterns are the same.
    if (!joint_ && session != nullptr && project != nullptr && session->datasets().files == files_ &&
        session->datasets().directory == directory_ && extracted_title == extracted_title_ && !files_.empty()) {
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
    clear();
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
    const std::string fitting = project != nullptr ? edi::effective_fitting_mode(*project) : std::string();
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
    next_ = 0;
    loaded_ = 0;
    publish(failed_, 0, &ScanViewModel::failedChanged);
    publish(error_, QString(), &ScanViewModel::errorChanged);
    has_values_ = listing_values_ && !(rows_by_bank_ && series_);
    emit valueTitleChanged();
    patterns_.assign(units(), {});
    values_.assign(units(), kNaN);
    value_texts_.assign(units(), QString());
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
    readNext();
}

void ScanViewModel::stop() {
    if (stop_) {
        stop_->store(true);
    }
}

void ScanViewModel::readNext() {
    const std::size_t units = this->units();
    if (next_ >= units) {
        return;
    }
    const std::size_t first = next_;
    const std::size_t last = std::min(units, first + kBatch);
    next_ = last;
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
    for (std::size_t unit = first; unit < last; ++unit) {
        batch.push_back(by_bank ? files_.at(at_point) : files_.at(unit));
    }
    run_in_background([self, generation, stop, first, batch = std::move(batch), source = source_, directory = directory_,
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
            // A series' row is its point on d; its place along the series comes from the first experiment's file.
            const std::size_t point = by_bank ? at_point : first + k;
            const std::string file = datasets ? datasets->point_files.at(point).front() : key;
            if (datasets) {
                try {
                    std::vector<std::size_t> experiments;
                    for (std::size_t e = 0; e < datasets->experiments.size(); ++e) {
                        if (by_bank ? e == first + k : chosen < 0 || static_cast<std::size_t>(chosen) == e)
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
            if (!datasets) {
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
            if (values) {
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
            [self, generation, stop, first, done = std::move(done)]() mutable {
                if (self.isNull() || generation != self->generation_ || stop->load()) {
                    return;  // a read of an earlier listing, or a stopped one
                }
                self->deliver(first, done);
            },
            Qt::QueuedConnection);
    });
}

// A batch's reads, in scan order from `first`: each dataset keeps its points, placed on the axis shown, and the x range
// grows to hold them.
void ScanViewModel::deliver(std::size_t first, std::vector<Read>& done) {
    for (std::size_t i = 0; i < done.size(); ++i) {
        Read& read = done[i];
        const std::size_t dataset = first + i;
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
        values_[dataset] = read.value;
        value_texts_[dataset] = read.value_text;
    }
    placeRange();
    if (series_) publishBackground();
    // File-index rows and labels stay fixed while batches arrive; extracted values reorder them once at the end.
    if (loaded_ == count()) placeRows();
    emit loadedChanged();
    ++revision_;
    emit revisionChanged();
    readNext();
}

void ScanViewModel::placeRows() {
    // By value once every dataset has one; until then, and without an extract rule (a joint fit has none), by place.
    const bool by_value = has_values_ && !rows_by_index_ && loaded_ == count() &&
                          std::all_of(values_.begin(), values_.end(), [](double value) { return std::isfinite(value); });
    rows_ = by_value ? edi::scan_row_positions(values_)
                     : edi::scan_row_positions(std::vector<double>(patterns_.size(), kNaN));
    spans_ = edi::scan_row_spans(rows_);
    // Datasets at one scan value (a temperature held, or reached again) each keep a band and a row of their own.
    edi::separate_shared_rows(rows_, spans_);
    publish(rows_by_value_, by_value, &ScanViewModel::rowsByValueChanged);
    const QString title = by_value ? extracted_title_ : orderName();
    // Every dataset read and still placed by file although the scan extracts a value: say why.
    publish(row_note_,
            has_values_ && !rows_by_index_ && !by_value && loaded_ == count() && !value_problem_.isEmpty()
                ? tr("Rows by file: %1").arg(value_problem_)
                : QString(),
            &ScanViewModel::rowNoteChanged);
    // Each row's label: the value with the unit the extract rule's title gives in brackets ("temperature (K)"), the
    // file's name, or the datablock's.
    const qsizetype bracket = extracted_title_.lastIndexOf(QLatin1Char('('));
    const QString unit = bracket >= 0 && extracted_title_.endsWith(QLatin1Char(')'))
                             ? extracted_title_.mid(bracket + 1, extracted_title_.size() - bracket - 2).trimmed()
                             : QString();
    QStringList texts;
    for (std::size_t i = 0; i < patterns_.size(); ++i) {
        if (by_value) {
            const QString value = i < value_texts_.size() && !value_texts_[i].isEmpty() ? value_texts_[i]
                                                                                        : QString::number(values_[i], 'g', 6);
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
    for (Pattern& pattern : patterns_) {
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
