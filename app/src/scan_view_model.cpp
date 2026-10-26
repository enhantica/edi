// SPDX-License-Identifier: BSD-3-Clause
#include "scan_view_model.hpp"

#include <QCoreApplication>
#include <QFileInfo>
#include <QMetaObject>
#include <QPointer>
#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <stdexcept>

#include "background.hpp"
#include "edi/display.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"
#include "scan_session.hpp"

namespace edi_app {

namespace {

// Files read per background turn: few enough that the views fill in steadily, many enough to keep the turns cheap.
constexpr std::size_t kBatch = 8;
constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();

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
    patterns_.clear();
    values_.clear();
    value_texts_.clear();
}

void ScanViewModel::setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title) {
    readConversion(project);
    // Results read again over the same files (after a run or an undo) leave what was read: the patterns are the same.
    if (!joint_ && session != nullptr && project != nullptr && session->datasets().files == files_ &&
        session->datasets().directory == directory_ && extracted_title == extracted_title_ && !files_.empty()) {
        placeAxis();
        ++revision_;
        emit revisionChanged();
        return;
    }
    clear();
    publish(joint_, false, &ScanViewModel::jointChanged);
    publish(native_shared_, true, &ScanViewModel::nativeSharedChanged);
    publish(row_labels_, QStringList(), &ScanViewModel::rowLabelsChanged);
    if (session != nullptr && project != nullptr && !project->experiments.empty()) {
        files_ = session->datasets().files;
        directory_ = session->datasets().directory;
        source_ = std::make_shared<const edi::Project>(*project);
        mode_ = project->experiment().effective_beam_mode();
        emit timeOfFlightChanged();
    }
    has_values_ = source_ != nullptr && !source_->sequential_fit.extract.empty() && !extracted_title.isEmpty();
    extracted_title_ = extracted_title;
    emit valueTitleChanged();
    patterns_.assign(files_.size(), {});
    values_.assign(files_.size(), kNaN);
    value_texts_.assign(files_.size(), QString());
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
    const bool joint = project != nullptr && project->experiments.size() >= 2 &&
                       edi::effective_fitting_mode(*project) == "joint";
    if (!joint && !joint_) {
        return;  // a scan, or nothing, stays as it is
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
            return same(a.x, b.x) && same(a.intensity, b.intensity) && same(a.d, b.d) && a.excluded == b.excluded;
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

void ScanViewModel::start() {
    if (started_ || files_.empty()) {
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
    if (next_ >= files_.size()) {
        return;
    }
    const std::size_t first = next_;
    const std::size_t last = std::min(files_.size(), first + kBatch);
    next_ = last;
    const QPointer<ScanViewModel> self(this);
    const std::uint64_t generation = generation_;
    const std::shared_ptr<std::atomic<bool>> stop = stop_;
    std::vector<std::string> batch(files_.begin() + static_cast<std::ptrdiff_t>(first),
                                   files_.begin() + static_cast<std::ptrdiff_t>(last));
    run_in_background([self, generation, stop, first, batch = std::move(batch), source = source_, directory = directory_,
                       mode = mode_, values = has_values_] {
        std::vector<Read> done;
        for (const std::string& file : batch) {
            if (stop->load()) {
                break;
            }
            Read read;
            // The pattern: unreadable, it is not drawn and is counted as such.
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
        pattern.excluded = template_excluded_;
        placePattern(pattern);
        values_[dataset] = read.value;
        value_texts_[dataset] = read.value_text;
    }
    placeRange();
    placeRows();
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
        } else {
            texts.append(i < files_.size() ? QFileInfo(QString::fromStdString(files_[i])).fileName() : QString());
        }
    }
    publish(row_texts_, texts, &ScanViewModel::rowTextsChanged);
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
    // Four rows' height, times the chosen scale: how far up the stacked view draws a pattern's highest point above
    // its row.
    publish(stack_height_,
            4.0 * stack_scale_ * (high - low) / std::max<double>(1.0, static_cast<double>(patterns_.size())),
            &ScanViewModel::stackHeightChanged);
}

// The project's current d column against its own axis, finite pairs only, what a scan's d-spacing is read from, and the
// template's excluded regions, which every dataset of a scan shares.
bool ScanViewModel::readConversion(const edi::Project* project) {
    std::vector<double> xs, ds;
    std::vector<std::pair<double, double>> excluded;
    if (project != nullptr && !project->experiments.empty()) {
        conversion_of(project->experiment(), xs, ds);
        excluded = excluded_of(project->experiment());
    }
    if (xs == template_x_ && ds == template_d_ && excluded == template_excluded_) {
        return false;
    }
    template_x_ = std::move(xs);
    template_d_ = std::move(ds);
    template_excluded_ = std::move(excluded);
    for (Pattern& pattern : patterns_) {
        pattern.excluded = template_excluded_;
    }
    return true;
}

void ScanViewModel::setConversion(const edi::Project* project) {
    // A calculation published: a joint fit's experiments are taken again (their d columns, their excluded regions);
    // a scan's d axis follows the template's conversion, as the pattern chart's does.
    if (joint_) {
        setJoint(project);
        return;
    }
    if (readConversion(project)) {
        placeAxis();
        ++revision_;
        emit revisionChanged();
    }
}

void ScanViewModel::setDSpacing(bool on) {
    if (on != d_spacing_) {
        d_spacing_ = on;
        emit dSpacingChanged();
        placeAxis();
        ++revision_;
        emit revisionChanged();
    }
}

void ScanViewModel::setIncludedOnly(bool on) {
    if (on != included_only_) {
        included_only_ = on;
        emit includedOnlyChanged();
        placeRange();
        ++revision_;
        emit revisionChanged();
    }
}

void ScanViewModel::setStackScale(int scale) {
    const int bounded = std::clamp(scale, 1, 5);
    if (bounded != stack_scale_) {
        stack_scale_ = bounded;
        emit stackScaleChanged();
        placeRows();
        ++revision_;
        emit revisionChanged();
    }
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
void ScanViewModel::placePattern(Pattern& pattern) const {
    pattern.excluded_shown.clear();
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
}

void ScanViewModel::placeRange() {
    double low = std::numeric_limits<double>::infinity(), high = -low;
    for (const Pattern& pattern : patterns_) {
        for (const double x : pattern.shown) {
            const bool excluded = included_only_ && excludedAt(pattern, x);
            if (std::isfinite(x) && !excluded) {
                low = std::min(low, x);
                high = std::max(high, x);
            }
        }
    }
    if (!(high > low)) {
        low = 0.0;
        high = 1.0;
    }
    publish(axis_min_, low, &ScanViewModel::xMinChanged);
    publish(axis_max_, high, &ScanViewModel::xMaxChanged);
}

// Every dataset on the axis shown, its range and its title.
void ScanViewModel::placeAxis() {
    if (!joint_) {
        publish(d_available_, template_x_.size() >= 2, &ScanViewModel::dAvailableChanged);
    }
    // d when asked for, and always for experiments that share no native axis, once it is given.
    const bool d = (d_spacing_ || !native_shared_) && d_available_;
    publish(d_shown_, d, &ScanViewModel::dShownChanged);
    for (Pattern& pattern : patterns_) {
        placePattern(pattern);
    }
    placeRange();
    // The axis is titled by its data item's dictionary label and units (edi ADR-0051).
    const char* const axis = d || !native_shared_                                  ? "data.d_spacing"
                             : mode_ == edi::BeamModeEnum::CONSTANT_WAVELENGTH ? "data.two_theta"
                                                                               : "data.time_of_flight";
    publish(x_title_, QString::fromStdString(edi::label(axis) + " (" + edi::units_label(axis) + ")"),
            &ScanViewModel::xTitleChanged);
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
