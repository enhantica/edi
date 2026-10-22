// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_VIEW_MODEL_HPP
#define EDI_APP_SCAN_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <algorithm>
#include <limits>
#include <atomic>
#include <memory>
#include <utility>
#include <vector>

#include "edi/model.hpp"
#include "edi/scan_views.hpp"

namespace edi_app {

class ScanSession;

// The stacked patterns and the 2D map (edi ADR-0041) of a scan, or of a joint fit's experiments: every dataset's
// measured points, a scan's read in the background once a view is shown, a joint fit's taken from its experiments,
// each with its row on the vertical axis (a scan's first extracted value, else its place). The views reduce the points
// for what they show (edi::scan_trace, edi::scan_pixel_values) each time they draw.
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
    // The x axis: the pattern's own (2θ or TOF), or d-spacing when asked for and a current d column gives it (as the
    // pattern chart: without one the views stay on their own axis). xMin and xMax are on the axis shown, over every
    // dataset read.
    Q_PROPERTY(bool dSpacing READ dSpacing WRITE setDSpacing NOTIFY dSpacingChanged)
    Q_PROPERTY(bool dShown READ dShown NOTIFY dShownChanged)
    // Whether d can be shown: a scan's template, or every experiment of a joint fit, has a current d column.
    Q_PROPERTY(bool dAvailable READ dAvailable NOTIFY dAvailableChanged)
    // Rows by file index although the scan extracts a value (the Map's y choice).
    Q_PROPERTY(bool rowsByIndex READ rowsByIndex WRITE setRowsByIndex NOTIFY rowsByIndexChanged)
    // Only the included range (the pattern charts' eraser button, one app setting): xMin and xMax run from the first
    // to the last point outside every excluded region.
    Q_PROPERTY(bool includedOnly READ includedOnly WRITE setIncludedOnly NOTIFY includedOnlyChanged)
    Q_PROPERTY(QString xTitle READ xTitle NOTIFY xTitleChanged)
    // Whether the pattern's own axis is time-of-flight (else 2θ), and the title of the extracted value the rows can
    // be placed by (empty without an extract rule).
    Q_PROPERTY(bool timeOfFlight READ timeOfFlight NOTIFY timeOfFlightChanged)
    Q_PROPERTY(QString valueTitle READ valueTitle NOTIFY valueTitleChanged)
    Q_PROPERTY(QString rowTitle READ rowTitle NOTIFY rowTitleChanged)
    // The other order the rows can take, by name (the owner, 2026-10-22): "file" for a scan's datasets, which share a
    // datablock and differ by file, "datablock" for a joint fit's experiments.
    Q_PROPERTY(QString orderName READ orderName NOTIFY orderNameChanged)
    // Each dataset's label for its row, by the order shown: its scan value with its unit, its file's name, or its
    // datablock's name.
    Q_PROPERTY(QStringList rowTexts READ rowTexts NOTIFY rowTextsChanged)
    // Whether the rows sit at their scan values (else in order, by file or datablock, one equal band each).
    Q_PROPERTY(bool rowsByValue READ rowsByValue NOTIFY rowsByValueChanged)
    Q_PROPERTY(double xMin READ xMin NOTIFY xMinChanged)
    Q_PROPERTY(double xMax READ xMax NOTIFY xMaxChanged)
    Q_PROPERTY(double rowMin READ rowMin NOTIFY rowMinChanged)
    Q_PROPERTY(double rowMax READ rowMax NOTIFY rowMaxChanged)
    // The lowest and the highest row itself (not its extent): the range of scan values the rows stand for.
    Q_PROPERTY(double rowLowest READ rowLowest NOTIFY rowLowestChanged)
    Q_PROPERTY(double rowHighest READ rowHighest NOTIFY rowHighestChanged)
    // How many times the default rise a stacked pattern takes (the owner, 2026-10-22: 1 to 5, an app setting).
    Q_PROPERTY(int stackScale READ stackScale WRITE setStackScale NOTIFY stackScaleChanged)
    // How far up the stacked view draws a pattern's highest point above its row: four rows' height, times stackScale.
    Q_PROPERTY(double stackHeight READ stackHeight NOTIFY stackHeightChanged)
    // A joint fit's experiments rather than a scan's datasets: rows by place, each labelled with its experiment's name.
    Q_PROPERTY(bool joint READ joint NOTIFY jointChanged)
    // Whether every dataset has the same native axis (2θ or TOF): a joint fit of a 2θ and a TOF experiment does not,
    // and is shown on d only, once a calculation has given it.
    Q_PROPERTY(bool nativeShared READ nativeShared NOTIFY nativeSharedChanged)
    Q_PROPERTY(QStringList rowLabels READ rowLabels NOTIFY rowLabelsChanged)
    // The first refusal of a read, if any (the other datasets are still read).
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)
    // Why the rows are placed by file index although the scan has an extract rule: the first dataset without a number
    // to place it by. Empty otherwise.
    Q_PROPERTY(QString rowNote READ rowNote NOTIFY rowNoteChanged)

   public:
    explicit ScanViewModel(QObject* parent);
    ~ScanViewModel() override;

    // The scan's datasets after a load or a refresh, the project they belong to and the first extract rule's title;
    // what was read is dropped and read again when a view next shows.
    void setScan(const ScanSession* session, const edi::Project* project, const QString& extracted_title);
    // A joint fit's experiments, read from the project as it is now; null (or a project that is not a joint fit of
    // several experiments) shows nothing. A scan set later replaces them.
    void setJoint(const edi::Project* project);
    // After a calculation: the d axis takes the project's current conversion, a scan's excluded regions the template's.
    void setConversion(const edi::Project* project);

    bool wanted() const { return wanted_; }
    void setWanted(bool wanted);
    int count() const { return static_cast<int>(patterns_.size()); }
    int loaded() const { return loaded_; }
    int failed() const { return failed_; }
    int revision() const { return revision_; }
    QString xTitle() const { return x_title_; }
    bool timeOfFlight() const { return mode_ != edi::BeamModeEnum::CONSTANT_WAVELENGTH; }
    bool joint() const { return joint_; }
    bool nativeShared() const { return native_shared_; }
    QStringList rowLabels() const { return row_labels_; }
    QString valueTitle() const { return has_values_ ? extracted_title_ : QString(); }
    QString rowTitle() const { return row_title_; }
    QString orderName() const { return joint_ ? tr("datablock") : tr("file"); }
    QStringList rowTexts() const { return row_texts_; }
    bool rowsByValue() const { return rows_by_value_; }
    double xMin() const { return axis_min_; }
    double xMax() const { return axis_max_; }
    bool dSpacing() const { return d_spacing_; }
    void setDSpacing(bool on);
    bool dShown() const { return d_shown_; }
    bool dAvailable() const { return d_available_; }
    bool rowsByIndex() const { return rows_by_index_; }
    bool includedOnly() const { return included_only_; }
    int stackScale() const { return stack_scale_; }
    void setStackScale(int scale);
    void setIncludedOnly(bool on);
    void setRowsByIndex(bool on);
    double rowMin() const { return row_min_; }
    double rowMax() const { return row_max_; }
    double rowLowest() const { return row_lowest_; }
    double rowHighest() const { return row_highest_; }
    double stackHeight() const { return stack_height_; }
    QString error() const { return error_; }
    QString rowNote() const { return row_note_; }

    // The dataset whose row holds `row` on the vertical axis, or -1.
    Q_INVOKABLE int datasetAt(double row) const;
    // A dataset's row on the vertical axis, NaN when it has none yet.
    Q_INVOKABLE double rowOf(int dataset) const;
    // The lower and upper edge of a dataset's row extent (halfway to its neighbours), NaN when it has none yet.
    Q_INVOKABLE double rowLowEdge(int dataset) const;
    Q_INVOKABLE double rowHighEdge(int dataset) const;

    // Per dataset, in scan order: its measured points (empty until read) with x on the axis shown (NaN where that axis
    // has no value), its excluded ranges on the axis shown, its row and its row's extent.
    struct Pattern {
        std::vector<double> x, intensity, shown;
        std::vector<std::pair<double, double>> excluded, excluded_shown;  // native, and on the axis shown
        std::vector<double> d;                                            // a joint fit's experiment's own d column
    };
    const std::vector<Pattern>& patterns() const { return patterns_; }
    // Whether `x`, on the axis shown, falls in one of the pattern's excluded regions.
    static bool excludedAt(const Pattern& pattern, double x);
    const std::vector<double>& rows() const { return rows_; }
    const std::vector<edi::ScanRowSpan>& spans() const { return spans_; }

   signals:
    void wantedChanged();
    void countChanged();
    void loadedChanged();
    void failedChanged();
    void revisionChanged();
    void xTitleChanged();
    void timeOfFlightChanged();
    void valueTitleChanged();
    void dSpacingChanged();
    void dShownChanged();
    void dAvailableChanged();
    void rowsByIndexChanged();
    void includedOnlyChanged();
    void stackScaleChanged();
    void rowTitleChanged();
    void orderNameChanged();
    void rowTextsChanged();
    void rowsByValueChanged();
    void xMinChanged();
    void xMaxChanged();
    void rowMinChanged();
    void rowMaxChanged();
    void rowLowestChanged();
    void rowHighestChanged();
    void stackHeightChanged();
    void errorChanged();
    void rowNoteChanged();
    void jointChanged();
    void nativeSharedChanged();
    void rowLabelsChanged();

   private:
    void start();
    void stop();
    // One dataset's read: its points, its scan value; an unreadable pattern's refusal, or why a readable one has no
    // scan value.
    struct Read {
        std::vector<double> x, intensity;
        double value = std::numeric_limits<double>::quiet_NaN();
        QString value_text;  // the value as the file writes it
        QString error, value_problem;
    };
    void readNext();
    void deliver(std::size_t first, std::vector<Read>& done);
    void placeRows();
    void placeAxis();
    // One dataset's x and excluded ranges on the axis shown.
    void placePattern(Pattern& pattern) const;
    // The axis shown's range over every dataset read.
    void placeRange();
    bool readConversion(const edi::Project* project);
    void clear();
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
    std::vector<Pattern> patterns_;
    std::vector<double> values_;  // each dataset's first extracted value, NaN when it has none
    std::vector<QString> value_texts_;  // the same as the file writes it
    QStringList row_texts_;
    std::vector<double> rows_;
    std::vector<edi::ScanRowSpan> spans_;
    std::size_t next_ = 0;  // the next dataset to read
    int loaded_ = 0;
    int failed_ = 0;
    int revision_ = 0;
    bool has_values_ = false;  // the scan has an extract rule
    QString x_title_, row_title_, extracted_title_, error_, row_note_;
    QString value_problem_;  // the first dataset with no value to place its row by
    double row_min_ = 0.0, row_max_ = 1.0, row_lowest_ = 0.0, row_highest_ = 0.0, stack_height_ = 0.0;
    double axis_min_ = 0.0, axis_max_ = 1.0;
    bool d_spacing_ = false, d_shown_ = false, d_available_ = false, rows_by_index_ = false, joint_ = false;
    bool native_shared_ = true, included_only_ = false, rows_by_value_ = false;
    int stack_scale_ = 1;
    QStringList row_labels_;
    std::vector<double> template_x_, template_d_;  // the template's own axis and its current d column, where finite
    std::vector<std::pair<double, double>> template_excluded_;  // a scan's excluded regions, the template's
    std::uint64_t generation_ = 0;  // bumped by every listing; a read delivers only to its own
    std::shared_ptr<std::atomic<bool>> stop_;
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_VIEW_MODEL_HPP
