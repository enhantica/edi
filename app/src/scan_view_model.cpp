// SPDX-License-Identifier: BSD-3-Clause
#include "scan_view_model.hpp"

#include <QCoreApplication>
#include <QMetaObject>
#include <QPointer>
#include <algorithm>
#include <functional>
#include <cmath>
#include <limits>

#include "background.hpp"
#include "edi/scan.hpp"
#include "scan_session.hpp"

namespace edi_app {

namespace {

// Files read per background turn: few enough that the views fill in steadily, many enough to keep the turns cheap.
constexpr std::size_t kBatch = 8;

}  // namespace

ScanViewModel::ScanViewModel(QObject* parent) : QObject(parent) {}

ScanViewModel::~ScanViewModel() { stop(); }

void ScanViewModel::setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title) {
    // The template's d column, as the last calculation left it: what d-spacing is read from.
    template_x_.clear();
    template_d_.clear();
    if (project != nullptr && !project->experiments.empty()) {
        const edi::PdDataBase* data = project->experiment().data ? &*project->experiment().data : nullptr;
        if (data != nullptr) {
            const std::vector<double>& x = data->axis();
            const std::vector<double>& d = data->d_spacing.values();
            for (std::size_t i = 0; i < x.size() && i < d.size(); ++i) {
                if (std::isfinite(x[i]) && std::isfinite(d[i])) {
                    template_x_.push_back(x[i]);
                    template_d_.push_back(d[i]);
                }
            }
        }
    }
    // Results read again over the same files (after a run or an undo) leave what was read: the patterns are the same.
    if (session != nullptr && project != nullptr && session->datasets().files == files_ &&
        session->datasets().directory == directory_ && extracted_title == extracted_title_ && !files_.empty()) {
        placeAxis();
        return;
    }
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
    placeAxis();
    columns_.assign(files_.size(), {});
    values_.assign(files_.size(), std::numeric_limits<double>::quiet_NaN());
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
    // The first dataset alone: its x range is every dataset's.
    const std::size_t first = next_;
    const std::size_t last = first == 0 ? 1 : std::min(files_.size(), first + kBatch);
    next_ = last;
    struct Read {
        edi::ScanColumns columns;
        double value = std::numeric_limits<double>::quiet_NaN();
        double x_min = 0.0, x_max = 0.0;
        QString error, value_problem;
    };
    const QPointer<ScanViewModel> self(this);
    const std::uint64_t generation = generation_;
    const std::shared_ptr<std::atomic<bool>> stop = stop_;
    std::vector<std::string> batch(files_.begin() + static_cast<std::ptrdiff_t>(first),
                                   files_.begin() + static_cast<std::ptrdiff_t>(last));
    run_in_background([self, generation, stop, first, batch = std::move(batch), source = source_, directory = directory_,
                       mode = mode_, values = has_values_, range_known = first > 0, x_min = x_min_, x_max = x_max_] {
        std::vector<Read> done;
        for (const std::string& file : batch) {
            if (stop->load()) {
                break;
            }
            Read read;
            try {
                const edi::PdDataBase data = edi::read_scan_dataset(directory, file, mode);
                const std::vector<double>& x = data.axis();
                const std::vector<double>& y = data.intensity_meas.get();
                read.x_min = x_min;
                read.x_max = x_max;
                if (!range_known) {
                    const auto [low, high] = std::minmax_element(x.begin(), x.end());
                    if (low != x.end()) {
                        read.x_min = *low;
                        read.x_max = *high;
                    }
                }
                read.columns = edi::scan_columns(x, y, read.x_min, read.x_max, kColumns);
                if (values) {
                    const std::vector<std::string> extracted = edi::scan_extract_values(*source, directory, file);
                    double value = 0.0;
                    if (!extracted.empty() && edi::parse_scan_number(extracted.front(), value)) {
                        read.value = value;
                    } else {
                        read.value_problem = QString::fromStdString(file) +
                                             (extracted.empty() ? QStringLiteral(": nothing is extracted")
                                                                : QStringLiteral(": '%1' is not a number")
                                                                      .arg(QString::fromStdString(extracted.front())));
                    }
                }
            } catch (const std::exception& refusal) {
                read.error = QString::fromStdString(file) + QStringLiteral(": ") + QString::fromUtf8(refusal.what());
            }
            done.push_back(std::move(read));
        }
        QMetaObject::invokeMethod(
            QCoreApplication::instance(),
            [self, generation, stop, first, done = std::move(done)]() mutable {
                if (self.isNull() || generation != self->generation_ || stop->load()) {
                    return;  // a read of an earlier listing, or a stopped one
                }
                for (std::size_t i = 0; i < done.size(); ++i) {
                    Read& read = done[i];
                    const std::size_t dataset = first + i;
                    if (!read.error.isEmpty()) {
                        if (self->error_.isEmpty()) {
                            self->publish(self->error_, read.error, &ScanViewModel::errorChanged);
                        }
                        self->publish(self->failed_, self->failed_ + 1, &ScanViewModel::failedChanged);
                        if (self->value_problem_.isEmpty()) {
                            self->value_problem_ = read.error;
                        }
                    } else if (!read.value_problem.isEmpty() && self->value_problem_.isEmpty()) {
                        self->value_problem_ = read.value_problem;
                    }
                    if (dataset == 0 && read.x_max > read.x_min) {
                        self->x_min_ = read.x_min;
                        self->x_max_ = read.x_max;
                        self->placeAxis();
                    }
                    self->columns_[dataset] = std::move(read.columns);
                    self->values_[dataset] = read.value;
                    ++self->loaded_;
                }
                self->placeRows();
                emit self->loadedChanged();
                ++self->revision_;
                emit self->revisionChanged();
                self->readNext();
            },
            Qt::QueuedConnection);
    });
}

void ScanViewModel::placeRows() {
    // By value once every dataset has one; until then, and without an extract rule, by place.
    const bool by_value = has_values_ && !rows_by_index_ && loaded_ == count() &&
                          std::all_of(values_.begin(), values_.end(), [](double value) { return std::isfinite(value); });
    rows_ = by_value ? edi::scan_row_positions(values_) : edi::scan_row_positions(std::vector<double>(files_.size(), std::numeric_limits<double>::quiet_NaN()));
    spans_ = edi::scan_row_spans(rows_);
    const QString title = by_value ? extracted_title_ : tr("file index");
    // Every dataset read and still placed by file index although the scan extracts a value: say why.
    publish(row_note_,
            has_values_ && !rows_by_index_ && !by_value && loaded_ == count() && !value_problem_.isEmpty()
                ? tr("Rows by file index: %1").arg(value_problem_)
                : QString(),
            &ScanViewModel::rowNoteChanged);
    double low = 0.0, high = 1.0;
    if (!spans_.empty()) {
        low = std::min_element(spans_.begin(), spans_.end(), [](const auto& a, const auto& b) { return a.low < b.low; })->low;
        high = std::max_element(spans_.begin(), spans_.end(), [](const auto& a, const auto& b) { return a.high < b.high; })->high;
    }
    publish(row_title_, title, &ScanViewModel::rowTitleChanged);
    publish(row_min_, low, &ScanViewModel::rowMinChanged);
    publish(row_max_, high, &ScanViewModel::rowMaxChanged);
    // Four rows' height: how far up the stacked view draws a pattern's highest point above its row.
    publish(stack_height_, 4.0 * (high - low) / std::max<double>(1.0, static_cast<double>(files_.size())),
            &ScanViewModel::stackHeightChanged);
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

void ScanViewModel::setRowsByIndex(bool on) {
    if (on != rows_by_index_) {
        rows_by_index_ = on;
        emit rowsByIndexChanged();
        placeRows();
        ++revision_;
        emit revisionChanged();
    }
}

// The columns' edges on the axis shown, and its range and title. d is read off the template's d column by linear
// interpolation in its own axis; an edge beyond that column has no d.
void ScanViewModel::placeAxis() {
    const bool d = d_spacing_ && template_x_.size() >= 2;
    const std::size_t columns = kColumns;
    edges_.assign(columns + 1, std::numeric_limits<double>::quiet_NaN());
    const bool rising = template_x_.size() >= 2 && template_x_.back() > template_x_.front();
    for (std::size_t c = 0; c <= columns; ++c) {
        const double x = x_min_ + (x_max_ - x_min_) * static_cast<double>(c) / static_cast<double>(columns);
        if (!d) {
            edges_[c] = x;
            continue;
        }
        const auto at = rising ? std::lower_bound(template_x_.begin(), template_x_.end(), x)
                               : std::lower_bound(template_x_.begin(), template_x_.end(), x, std::greater<>());
        if (at == template_x_.begin() || at == template_x_.end()) {
            if (at != template_x_.end() && *at == x) {
                edges_[c] = template_d_[static_cast<std::size_t>(at - template_x_.begin())];
            }
            continue;
        }
        const std::size_t hi = static_cast<std::size_t>(at - template_x_.begin()), lo = hi - 1;
        const double f = (x - template_x_[lo]) / (template_x_[hi] - template_x_[lo]);
        edges_[c] = template_d_[lo] + (template_d_[hi] - template_d_[lo]) * f;
    }
    double low = std::numeric_limits<double>::infinity(), high = -low;
    for (const double edge : edges_) {
        if (std::isfinite(edge)) {
            low = std::min(low, edge);
            high = std::max(high, edge);
        }
    }
    if (!(high > low)) {
        low = x_min_;
        high = x_max_;
    }
    publish(axis_min_, low, &ScanViewModel::xMinChanged);
    publish(axis_max_, high, &ScanViewModel::xMaxChanged);
    publish(d_shown_, d, &ScanViewModel::dShownChanged);
    publish(x_title_,
            d ? QStringLiteral("d (Å)")
              : mode_ == edi::BeamModeEnum::CONSTANT_WAVELENGTH ? QStringLiteral("2θ (deg)") : QStringLiteral("TOF (µs)"),
            &ScanViewModel::xTitleChanged);
}

int ScanViewModel::columnAt(double x) const {
    for (std::size_t c = 0; c + 1 < edges_.size(); ++c) {
        const double a = edges_[c], b = edges_[c + 1];
        if (std::isfinite(a) && std::isfinite(b) && x >= std::min(a, b) && x <= std::max(a, b)) {
            return static_cast<int>(c);
        }
    }
    return -1;
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
                                                                           : std::numeric_limits<double>::quiet_NaN();
}

}  // namespace edi_app
