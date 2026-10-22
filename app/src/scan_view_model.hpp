// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_VIEW_MODEL_HPP
#define EDI_APP_SCAN_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>
#include <algorithm>
#include <atomic>
#include <memory>
#include <vector>

#include "edi/model.hpp"
#include "edi/scan_views.hpp"

namespace edi_app {

class ScanSession;

// The stacked patterns and the 2D map of a scan (edi ADR-0041): every dataset's measured pattern, read in the
// background once a view is shown and kept only as its columns (edi::scan_columns) over the first dataset's x range,
// with each dataset's row on the vertical axis (its first extracted value, else its place in the scan).
class ScanViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    // A view shows the scan: its datasets are read, once.
    Q_PROPERTY(bool wanted READ wanted WRITE setWanted NOTIFY wantedChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)
    // How many datasets are processed so far (read or refused); `failed` of them could not be read, and draw nothing.
    Q_PROPERTY(int loaded READ loaded NOTIFY loadedChanged)
    Q_PROPERTY(int failed READ failed NOTIFY failedChanged)
    // Bumped whenever the columns or the rows change, for the views to draw again.
    Q_PROPERTY(int revision READ revision NOTIFY revisionChanged)
    Q_PROPERTY(QString xTitle READ xTitle NOTIFY xTitleChanged)
    Q_PROPERTY(QString rowTitle READ rowTitle NOTIFY rowTitleChanged)
    Q_PROPERTY(double xMin READ xMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax READ xMax NOTIFY xMaxChanged)
    Q_PROPERTY(double rowMin READ rowMin NOTIFY rowMinChanged)
    Q_PROPERTY(double rowMax READ rowMax NOTIFY rowMaxChanged)
    // How far up the stacked view draws a pattern's highest point above its row: four rows' height.
    Q_PROPERTY(double stackHeight READ stackHeight NOTIFY stackHeightChanged)
    // The first refusal of a read, if any (the other datasets are still read).
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)
    // Why the rows are placed by file index although the scan has an extract rule: the first dataset without a number
    // to place it by. Empty otherwise.
    Q_PROPERTY(QString rowNote READ rowNote NOTIFY rowNoteChanged)

   public:
    // Each dataset reduced to this many columns across the x range.
    static constexpr std::size_t kColumns = 1024;

    explicit ScanViewModel(QObject* parent);
    ~ScanViewModel() override;

    // The scan's datasets after a load or a refresh, the project they belong to and the first extract rule's title;
    // what was read is dropped and read again when a view next shows.
    void setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title);

    bool wanted() const { return wanted_; }
    void setWanted(bool wanted);
    int count() const { return static_cast<int>(files_.size()); }
    int loaded() const { return loaded_; }
    int failed() const { return failed_; }
    int revision() const { return revision_; }
    QString xTitle() const { return x_title_; }
    QString rowTitle() const { return row_title_; }
    double xMin() const { return x_min_; }
    double xMax() const { return x_max_; }
    double rowMin() const { return row_min_; }
    double rowMax() const { return row_max_; }
    double stackHeight() const { return stack_height_; }
    QString error() const { return error_; }
    QString rowNote() const { return row_note_; }

    // The dataset whose row holds `row` on the vertical axis, or -1.
    Q_INVOKABLE int datasetAt(double row) const;
    // A dataset's row on the vertical axis, NaN when it has none yet.
    Q_INVOKABLE double rowOf(int dataset) const;

    // Per dataset, in scan order: its columns (empty until read), its row and its row's extent.
    const std::vector<edi::ScanColumns>& columns() const { return columns_; }
    const std::vector<double>& rows() const { return rows_; }
    const std::vector<edi::ScanRowSpan>& spans() const { return spans_; }

   signals:
    void wantedChanged();
    void countChanged();
    void loadedChanged();
    void failedChanged();
    void revisionChanged();
    void xTitleChanged();
    void rowTitleChanged();
    void xMinChanged();
    void xMaxChanged();
    void rowMinChanged();
    void rowMaxChanged();
    void stackHeightChanged();
    void errorChanged();
    void rowNoteChanged();

   private:
    void start();
    void stop();
    void readNext();
    void placeRows();
    // One property's value and its own signal: only what changed notifies (the app's per-property rule).
    template <typename T>
    void publish(T& member, const T& value, void (ScanViewModel::*changed)()) {
        if (!(member == value)) {
            member = value;
            emit(this->*changed)();
        }
    }

    bool wanted_ = false;
    bool started_ = false;
    std::shared_ptr<const edi::Project> source_;  // what the files' extract rules are read with
    std::string directory_;
    std::vector<std::string> files_;
    edi::BeamModeEnum mode_ = edi::BeamModeEnum::CONSTANT_WAVELENGTH;
    std::vector<edi::ScanColumns> columns_;
    std::vector<double> values_;  // each dataset's first extracted value, NaN when it has none
    std::vector<double> rows_;
    std::vector<edi::ScanRowSpan> spans_;
    std::size_t next_ = 0;  // the next dataset to read
    int loaded_ = 0;
    int failed_ = 0;
    int revision_ = 0;
    bool has_values_ = false;  // the scan has an extract rule
    QString x_title_, row_title_, extracted_title_, error_, row_note_;
    QString value_problem_;  // the first dataset with no value to place its row by
    double x_min_ = 0.0, x_max_ = 1.0, row_min_ = 0.0, row_max_ = 1.0, stack_height_ = 0.0;
    std::uint64_t generation_ = 0;  // bumped by every listing; a read delivers only to its own
    std::shared_ptr<std::atomic<bool>> stop_;
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_VIEW_MODEL_HPP
