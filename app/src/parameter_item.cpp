// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_item.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <unordered_map>

#include <QStringList>
#include <limits>

#include "category_list_model.hpp"
#include "edi/display.hpp"
#include "edi/fittability.hpp"
#include "edi/parameter_spec.hpp"
#include "edi/report.hpp"
#include "edi/report_model.hpp"
#include "crysta/dictionary_items.hpp"
#include "project_editor.hpp"

namespace edi_app {

ParameterItem::ParameterItem(const edi::ParameterEntry& entry, ProjectEditor& editor, QObject* parent)
    : QObject(parent),
      editor_(editor),
      parameter_(entry.parameter),
      value_(entry.parameter->value),
      uncertainty_(entry.parameter->uncertainty),
      free_(entry.parameter->free),
      refinable_(entry.refinable),
      path_(QString::fromStdString(entry.path)),
      block_kind_(QString::fromStdString(entry.block_kind)),
      block_name_(QString::fromStdString(entry.block_name)),
      category_(QString::fromStdString(entry.category)),
      row_label_(QString::fromStdString(entry.row_label)),
      name_(QString::fromStdString(entry.name)) {
    const edi::ParameterSpec* spec = entry.parameter->spec;
    uid_ = spec != nullptr ? QStringLiteral("%1.%2").arg(QString::fromUtf8(spec->category), QString::fromUtf8(spec->name))
                           : category_ + QLatin1Char('.') + name_;
    // Every name the parameter shows comes from crysta's dictionary through the core's bridge.
    display_name_ = spec != nullptr ? QString::fromStdString(edi::label(uid_.toStdString())) : name_;
    display_units_ = spec != nullptr ? QString::fromStdString(edi::units_label(uid_.toStdString())) : QString();
    short_name_ = spec != nullptr ? QString::fromStdString(edi::label(uid_.toStdString())) : name_;
    minimum_ = spec != nullptr ? spec->range.min : -std::numeric_limits<double>::infinity();
    maximum_ = spec != nullptr ? spec->range.max : std::numeric_limits<double>::infinity();
    category_icon_ = category_presentation(category_).icon;
}

ParameterItem::ParameterItem(const edi::DescriptorEntry& entry, ProjectEditor& editor, QObject* parent)
    : QObject(parent),
      editor_(editor),
      own_(std::make_unique<edi::Parameter>(entry.value)),
      parameter_(own_.get()),
      value_(entry.value),
      uncertainty_(0.0),
      free_(false),
      refinable_(false),
      fittable_(false),
      fit_reason_(QString::fromStdString(edi::fit_reason(edi::FitBlocker::Descriptor))),
      fit_group_(FixedSetting),
      path_(QString::fromStdString(entry.path)),
      uid_(QString::fromStdString(entry.uid)),
      block_kind_(QString::fromStdString(entry.block_kind)),
      block_name_(QString::fromStdString(entry.block_name)),
      category_(QString::fromStdString(entry.category)),
      row_label_(QString::fromStdString(entry.row_label)),
      name_(QString::fromStdString(entry.name)) {
    display_name_ = QString::fromStdString(edi::label(entry.uid));
    display_units_ = QString::fromStdString(edi::units_label(entry.uid));
    short_name_ = display_name_;
    minimum_ = -std::numeric_limits<double>::infinity();
    maximum_ = std::numeric_limits<double>::infinity();
    category_icon_ = category_presentation(category_).icon;
}

void ParameterItem::setFittability(bool fittable, const QString& reason, int group) {
    if (fit_group_ != group) {
        fit_group_ = group;
        emit fitGroupChanged();
    }
    if (fittable_ != fittable) {
        fittable_ = fittable;
        emit fittableChanged();
    }
    if (fit_reason_ != reason) {
        fit_reason_ = reason;
        emit fitReasonChanged();
    }
}

void ParameterItem::setDescriptorValue(double value) {
    if (own_ != nullptr) {
        own_->value = value;
    }
}

void ParameterItem::setBlockIndex(int index) {
    if (block_index_ != index) {
        block_index_ = index;
        emit blockIndexChanged();
    }
}

void ParameterItem::setElementSymbol(const QString& symbol) {
    if (element_symbol_ != symbol) {
        element_symbol_ = symbol;
        emit elementSymbolChanged();
    }
}

void ParameterItem::setLabel(const QString& short_name, const QString& units) {
    if (short_name_ != short_name) {
        short_name_ = short_name;
        emit shortNameChanged();
    }
    if (display_units_ != units) {
        display_units_ = units;
        emit displayUnitsChanged();
    }
}

void ParameterItem::setVariant(const QString& variant) {
    if (variant_ != variant) {
        variant_ = variant;
        emit sliderStepChanged();
        emit toolTipChanged();
    }
}

QString ParameterItem::toolTip() const {
    if (parameter_->spec == nullptr && own_ == nullptr) {
        return {};
    }
    return QString::fromStdString(edi::tooltip(uid_.toStdString(), variant_.toStdString()));
}

void ParameterItem::setSpelling(const std::string& rule, bool exact) {
    if (su_rule_ != rule || exact_ != exact) {
        su_rule_ = rule;
        exact_ = exact;
        refreshFileText();
    }
}

void ParameterItem::refreshFileText() {
    // Empty for a parameter the dictionary does not know; a page then shows the value itself.
    QString value;
    QString su;
    QString edit;
    // Very large or small numbers in scientific notation, as every parameter table writes them (owner record
    // 2026-11-09): a value with an s.u. keeps its rounding in the value's power, one without has three digits.
    if (own_ != nullptr) {
        const std::string text = edi::display_text(uid_.toStdString(), value_);
        value = QString::fromStdString(edi::table_number(value_, text, true));
        edit = QString::fromStdString(text);
    } else if (parameter_->spec != nullptr && !su_rule_.empty()) {
        const edi::FileText text = edi::file_text(*parameter_, su_rule_, exact_);
        const double number = parameter_->value.get();
        const std::optional<double> uncertainty = parameter_->uncertainty.get();
        edit = QString::fromStdString(text.value);
        if (uncertainty.has_value() && *uncertainty != 0.0 && std::isfinite(*uncertainty)) {
            const auto [shown, shown_su] = edi::table_value_su(number, text.value, text.su, true);
            value = QString::fromStdString(shown);
            su = QString::fromStdString(shown_su);
        } else {
            value = QString::fromStdString(edi::table_number(number, text.value, true));
            su = QString::fromStdString(text.su);
        }
    }
    if (value != file_value_ || edit != file_edit_value_) {
        file_value_ = value;
        file_edit_value_ = edit;
        emit fileValueChanged();
    }
    if (su != file_su_) {
        file_su_ = su;
        emit fileSuChanged();
    }
    refreshStart();
}

namespace {
// The project's correlation marks (edi::su_marks), made again only when its fit's correlations change: every item of
// the table asks after a fit.
const edi::SuMarks* correlation_mark(const edi::Project& project, const edi::Parameter* parameter) {
    struct Cache {
        const edi::Project* project = nullptr;
        const void* rows = nullptr;
        std::size_t count = 0;
        std::unordered_map<const edi::Parameter*, edi::SuMarks> marks;
    };
    static Cache cache;
    const auto& rows = project.fit_result.correlations;
    const void* first = rows.size() == 0 ? nullptr : static_cast<const void*>(rows.begin()->get());
    if (cache.project != &project || cache.rows != first || cache.count != rows.size()) {
        cache.project = &project;
        cache.rows = first;
        cache.count = rows.size();
        cache.marks = edi::su_marks(project);
    }
    const auto found = cache.marks.find(parameter);
    return found != cache.marks.end() && !found->second.partner.empty() ? &found->second : nullptr;
}
}  // namespace

void ParameterItem::refreshStart() {
    // The report's fit table cells (report_model.cpp): the start in the item's display format, the change in % of it
    // with its direction apart, so the percentages align on their last digit and the arrow is drawn as an icon.
    QString start;
    QString change;
    int direction = 0;
    if (own_ == nullptr && parameter_->spec != nullptr) {
        if (const std::optional<double> before = parameter_->start_value.get(); before.has_value()) {
            const std::string text = edi::display_text(uid_.toStdString(), *before, variant_.toStdString());
            start = QString::fromStdString(edi::table_number(*before, text, true));
            const double value = parameter_->value.get();
            change = QString::fromStdString(edi::display_exponents(edi::change_percent(value, *before)));
            if (!change.isEmpty()) direction = value > *before ? 1 : -1;
        }
    }
    // The s.u.'s red and its reasons, after a fit of a free parameter.
    QStringList reasons;
    const std::optional<double> su = parameter_->uncertainty.get();
    if (own_ == nullptr && parameter_->spec != nullptr && parameter_->free.get() && su.has_value() && std::isfinite(*su) &&
        *su != 0.0) {
        const crysta::DictionaryItem* item = crysta::find_dictionary_item(uid_.toStdString());
        if (item != nullptr && !item->near_zero && std::fabs(*su) > std::fabs(parameter_->value.get())) {
            reasons << QString::fromStdString(edi::su_poor_text());
        }
        if (const edi::Project* project = editor_.currentProject(); project != nullptr) {
            if (const edi::SuMarks* mark = correlation_mark(*project, parameter_); mark != nullptr) {
                reasons << QString::fromStdString(edi::su_correlated_text(*mark));
            }
        }
    }
    const QString reason = reasons.join(QLatin1Char('\n'));
    if (start != start_text_ || change != change_text_ || direction != change_direction_ || reason != su_reason_) {
        start_text_ = start;
        change_text_ = change;
        change_direction_ = direction;
        su_reason_ = reason;
        emit startTextChanged();
    }
}

double ParameterItem::sliderStep() const {
    if (parameter_->spec == nullptr) {
        return 0.0;
    }
    return edi::display_step(*parameter_, variant_.toStdString());
}

QString ParameterItem::displayText(double value) const {
    if (parameter_->spec == nullptr) {
        return {};
    }
    return QString::fromStdString(edi::shown_text(uid_.toStdString(), value, variant_.toStdString()));
}

void ParameterItem::setPhaseIndex(int index) {
    if (phase_index_ != index) {
        phase_index_ = index;
        emit phaseIndexChanged();
    }
}

void ParameterItem::setRefinable(bool refinable) {
    if (refinable_ != refinable) {
        refinable_ = refinable;
        emit refinableChanged();
    }
}

void ParameterItem::setDomainWarning(const QString& warning) {
    if (domain_warning_ != warning) {
        domain_warning_ = warning;
        emit domainWarningChanged();
    }
}

void ParameterItem::setEstimated(bool estimated) {
    if (estimated_ != estimated) {
        estimated_ = estimated;
        emit estimatedChanged();
    }
}

namespace {
// The refusal of a write to a parameter symmetry holds (edi ADR-0019). The pages disable such a field, so
// this answers only a caller that writes anyway.
QString symmetry_refusal() { return QObject::tr("the space group fixes this parameter or ties it to another"); }
}  // namespace

void ParameterItem::setValue(double value) {
    if (own_ != nullptr) {
        setLastError(tr("a descriptor: its value is edited on its page"));
        return;
    }
    if (!refinable_) {
        setLastError(symmetry_refusal());
        return;
    }
    // Asked of the project as it is now, not of `estimated`, which follows the mode only at the next publish.
    if (const QString refusal = editor_.value_refusal(*parameter_); !refusal.isEmpty()) {
        setLastError(refusal);
        return;
    }
    edi::Parameter* parameter = parameter_;
    setLastError(editor_.assign_parameter_value(*parameter, value));
}

void ParameterItem::setFree(bool free) {
    // A flag is set only where a fit can vary it; one set before a change that blocked it can still be cleared.
    if (free && !fittable_) {
        setLastError(tr("Cannot be fitted: %1").arg(fit_reason_));
        return;
    }
    if (!refinable_) {
        setLastError(symmetry_refusal());
        return;
    }
    if (const QString refusal = editor_.free_refusal(); !refusal.isEmpty()) {
        setLastError(refusal);
        return;
    }
    edi::Parameter* parameter = parameter_;
    setLastError(editor_.assign_parameter_free(*parameter, free));
}

int ParameterItem::publish(bool formatted) {
    int changed = 0;
    const bool was_outside = outsideRange();
    if (parameter_->value != value_) {
        value_ = parameter_->value;
        changed |= ValueField;
    }
    const bool had_uncertainty = uncertainty_.has_value();
    if (parameter_->uncertainty != uncertainty_) {
        uncertainty_ = parameter_->uncertainty;
        changed |= UncertaintyField;
    }
    if (parameter_->free != free_) {
        free_ = parameter_->free;
        changed |= FreeField;
    }
    if ((changed & ValueField) != 0) {
        emit valueChanged();
        emit sliderStepChanged();
        if (outsideRange() != was_outside) {
            emit outsideRangeChanged();
        }
    }
    if ((changed & UncertaintyField) != 0) {
        emit uncertaintyChanged();
        if (had_uncertainty != uncertainty_.has_value()) {
            emit hasUncertaintyChanged();
        }
    }
    if ((changed & FreeField) != 0) {
        emit freeChanged();
    }
    // A symmetry change alters how a value is written without changing it, so the text is read again each time.
    if (formatted) refreshFileText();
    refreshStart();
    return changed;
}

void ParameterItem::setLastError(const QString& error) {
    if (error != last_error_) {
        last_error_ = error;
        emit lastErrorChanged();
    }
}

namespace {
// The Analysis slider's half width around a lattice constant's value, in Å (the owner, 2026-10-04).
constexpr double kLatticeConstantSliderHalfWidth = 0.05;
}  // namespace

double ParameterItem::sliderHalfWidth() const {
    if (category_ == QLatin1String("cell") && name_.startsWith(QLatin1String("length_"))) {
        return kLatticeConstantSliderHalfWidth;
    }
    return std::max(std::abs(value_) * 0.5, 1e-3);
}

}  // namespace edi_app
