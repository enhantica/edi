// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_item.hpp"
#include "label_case.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <unordered_map>

#include <QRegularExpression>
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
    // The short name is the field's title, so it follows the label rule; the display name stays as the dictionary writes it.
    short_name_ = spec != nullptr ? label_case(QString::fromStdString(edi::label(uid_.toStdString()))) : name_;
    minimum_ = spec != nullptr ? spec->range.min : -std::numeric_limits<double>::infinity();
    maximum_ = spec != nullptr ? spec->range.max : std::numeric_limits<double>::infinity();
    category_icon_ = category_presentation(category_).icon;
    full_name_ = block_name_ + QLatin1Char('.') + category_ + (row_label_.isEmpty() ? QString() : QLatin1Char('.') + row_label_) + QLatin1Char('.') + name_;
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
      name_(QString::fromStdString(entry.name)),
      display_name_(QString::fromStdString(edi::label(entry.uid))),
      display_units_(QString::fromStdString(edi::units_label(entry.uid))) {
    short_name_ = label_case(display_name_);
    minimum_ = -std::numeric_limits<double>::infinity();
    maximum_ = std::numeric_limits<double>::infinity();
    category_icon_ = category_presentation(category_).icon;
    full_name_ = block_name_ + QLatin1Char('.') + category_ + (row_label_.isEmpty() ? QString() : QLatin1Char('.') + row_label_) + QLatin1Char('.') + name_;
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

void ParameterItem::setLabel(const QString& name, const QString& units) {
    const QString short_name = label_case(name);
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
        emit fileEditValueChanged();
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
        emit changeTextChanged();
        emit changeDirectionChanged();
        emit suFlaggedChanged();
        emit suReasonChanged();
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
    QString text = QString::fromStdString(edi::shown_text(uid_.toStdString(), value, variant_.toStdString()));
    // The limits are round numbers (sliderLower, sliderUpper), so trailing zeros only pad them: 10.2500 reads 10.25.
    // Only a plain decimal is trimmed; a value written with a power of ten keeps its digits.
    static const QRegularExpression plain(QStringLiteral("^-?[0-9]+\\.[0-9]+$"));
    if (plain.match(text).hasMatch()) {
        while (text.endsWith(QLatin1Char('0'))) text.chop(1);
        if (text.endsWith(QLatin1Char('.'))) text.chop(1);
    }
    return text;
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

void ParameterItem::setShared(bool shared) {
    // Shared and Free are independent; a parameter that cannot be shared says why (edi ADR-0107).
    if (const QString refusal = own_ == nullptr ? editor_.parameter_share_refusal(*parameter_) : tr("a setting");
        shared && !refusal.isEmpty()) {
        setLastError(tr("Cannot be shared: %1").arg(refusal));
        return;
    }
    edi::Parameter* parameter = parameter_;
    setLastError(editor_.assign_parameter_shared(*parameter, shared));
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
    if (const bool shared = own_ == nullptr && editor_.parameter_shared(*parameter_); shared != shared_) {
        shared_ = shared;
        changed |= SharedField;
    }
    if (const edi::Parameter* leader = own_ == nullptr ? editor_.parameter_shared_leader(*parameter_) : nullptr;
        (leader != nullptr && leader != parameter_) != shared_follower_) {
        shared_follower_ = !shared_follower_;
        changed |= SharedField;
    }
    if (const QString reason = own_ == nullptr ? editor_.parameter_share_refusal(*parameter_) : tr("a setting");
        reason != share_reason_) {
        share_reason_ = reason;
        changed |= SharedField;
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
    if ((changed & SharedField) != 0) {
        emit sharedChanged();
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

// The slider's smallest half width by parameter kind (the owner, 2026-11-17: a zero 2θ offset slid only ±0.001): a
// step a user would try first, so one drag shows the effect. Elsewhere the half width is half the value, never less
// than this; `name` matches the item name or its start.
//
// | kind                               | items                                   | unit      | min half width | why                                        |
// |------------------------------------|-----------------------------------------|-----------|----------------|--------------------------------------------|
// | 2θ offset (constant wavelength)    | instrument.calib_twotheta_offset        | deg       | 0.1            | the owner's ±0.1; zero errors are ~0.01-0.1 |
// | sample displacement, transparency  | instrument.calib_sample_*               | deg       | 0.1            | the same size of 2θ shift                  |
// | TOF zero shift                     | instrument.calib_d_to_tof_offset        | µs        | 5              | zero shifts are a few µs                   |
// | TOF DIFC                           | instrument.calib_d_to_tof_linear        | µs/Å      | 10             | about 0.1 % of a typical DIFC              |
// | TOF DIFA, reciprocal               | instrument.calib_d_to_tof_quadratic, …_reciprocal | µs/Å², µs·Å | 1     | small corrections around 0                 |
// | wavelength                         | instrument.setup_wavelength, …_2        | Å         | 0.01           | a calibration is known to ~0.001-0.01 Å     |
// | wavelength intensity ratio         | instrument.setup_wavelength_2_to_1_ratio| —         | 0.05           | Kα2/Kα1 is about 0.5                       |
// | polarization coefficient           | instrument.setup_polarization_coefficient | —       | 0.1            | between 0 and 1                            |
// | monochromator 2θ                   | instrument.setup_monochromator_twotheta | deg       | 1              | a geometry angle                           |
// | cell angles                        | cell.angle_*                            | deg       | 0.5            | a small distortion                         |
// | fractional coordinates             | atom_site.fract_*                       | —         | 0.01           | 0.05-0.1 Å in a 5-10 Å cell                |
// | occupancy                          | atom_site.occupancy                     | —         | 0.1            | a tenth of the 0-1 range                   |
// | displacement B                     | atom_site.adp_iso, atom_site_aniso.*    | Å²        | 0.5            | B is usually 0.2-2 Å²                      |
// | displacement U                     | atom_site.adp_iso, atom_site_aniso.*    | Å²        | 0.005          | U = B/8π², usually 0.003-0.03 Å²           |
// | displacement β                     | atom_site_aniso.*                       | —         | 0.001          | β is dimensionless and small               |
// | magnetic moments                   | atom_site_moment.crystalaxis_*          | μB        | 0.5            | moments are 0-5 μB                         |
// | peak width U, V, W                 | peak.broad_gauss_u, _v, _w              | deg²      | 0.05           | typical values are ±0.01-0.5               |
// | peak width X, Y                    | peak.broad_lorentz_x, _y                | deg       | 0.05           | typical values are 0-0.3                   |
// | size and strain                    | peak.broad_*_size, peak.broad_*_strain  | —         | 0.01           | small broadening terms                     |
// | asymmetry (FCJ S/L, D/L)           | peak.asym_fcj_*                         | —         | 0.01           | typical values are 0.005-0.05              |
// | asymmetry (Bérar-Baldinozzi)       | peak.asym_beba_a*, _b*                  | —         | 0.05           | typical values are ±0.01-0.2               |
// | pseudo-Voigt mixing                | peak.mixing_eta_*                       | —, 1/deg  | 0.1            | η runs from 0 to 1                         |
// | TOF Gaussian width                 | peak.broad_gauss_sigma_*                | µs², …    | 1              | values are 0-100 in their units            |
// | TOF Lorentzian width               | peak.broad_lorentz_gamma_*              | µs, …     | 1              | values are 0-10 in their units             |
// | TOF rise and decay                 | peak.rise_alpha_*, peak.decay_beta_*    | —         | 0.01           | values are 0.01-1                          |
// | background                         | background.intensity, background.coef   | counts    | 1              | at least one count; larger values use half |
// | scale                              | linked_structure.scale                  | —         | 0.001          | scales span decades: half the value rules  |
// | extinction coefficients            | extinction.coefficient*                 | —         | 0.01           | small corrections                          |
// | extinction radii                   | extinction.domain_radius, crystal_radius| μm, mm    | 0.1            | a tenth of a unit                          |
// | mosaic spread                      | extinction.mosaic_spread                | rad⁻¹     | 0.01           | small corrections                          |
// | absorption                         | absorption.mu_r, absorption.abscor1     | —, Å⁻¹    | 0.1            | μR is usually 0-2                          |
// | lattice constants                  | cell.length_*                           | Å         | 0.05 (fixed)   | the owner, 2026-10-04: always ±0.05 Å      |
// | anything else                      |                                         |           | 0.001          | the earlier floor                          |
struct SliderFloor {
    const char* category;
    const char* name;
    double half_width;
};
constexpr SliderFloor kSliderFloors[] = {
    {"instrument", "calib_twotheta_offset", 0.1},
    {"instrument", "calib_sample_", 0.1},
    {"instrument", "calib_d_to_tof_offset", 5.0},
    {"instrument", "calib_d_to_tof_linear", 10.0},
    {"instrument", "calib_d_to_tof_quadratic", 1.0},
    {"instrument", "calib_d_to_tof_reciprocal", 1.0},
    {"instrument", "setup_wavelength_2_to_1_ratio", 0.05},
    {"instrument", "setup_wavelength", 0.01},
    {"instrument", "setup_polarization_coefficient", 0.1},
    {"instrument", "setup_monochromator_twotheta", 1.0},
    {"cell", "angle_", 0.5},
    {"atom_site", "fract_", 0.01},
    {"atom_site", "occupancy", 0.1},
    {"atom_site_moment", "crystalaxis_", 0.5},
    {"peak", "broad_gauss_sigma_", 1.0},
    {"peak", "broad_lorentz_gamma_", 1.0},
    {"peak", "broad_gauss_size", 0.01},
    {"peak", "broad_gauss_strain", 0.01},
    {"peak", "broad_lorentz_size", 0.01},
    {"peak", "broad_lorentz_strain", 0.01},
    {"peak", "broad_gauss_", 0.05},
    {"peak", "broad_lorentz_", 0.05},
    {"peak", "asym_fcj_", 0.01},
    {"peak", "asym_beba_", 0.05},
    {"peak", "mixing_eta_", 0.1},
    {"peak", "rise_alpha_", 0.01},
    {"peak", "decay_beta_", 0.01},
    {"background", "intensity", 1.0},
    {"background", "coef", 1.0},
    {"extinction", "coefficient", 0.01},
    {"extinction", "domain_radius", 0.1},
    {"extinction", "crystal_radius", 0.1},
    {"extinction", "mosaic_spread", 0.01},
    {"absorption", "mu_r", 0.1},
    {"absorption", "abscor1", 0.1},
};
constexpr double kDefaultSliderFloor = 1e-3;
}  // namespace

double ParameterItem::sliderFloor() const {
    if ((category_ == QLatin1String("atom_site") && name_ == QLatin1String("adp_iso")) ||
        (category_ == QLatin1String("atom_site_aniso") && name_.startsWith(QLatin1String("adp_")))) {
        // The site's declared type decides the size: its symbol is the label (B, U or β).
        return short_name_.startsWith(QLatin1Char('U'), Qt::CaseInsensitive) ? 0.005
               : short_name_.startsWith(QChar(0x03B2)) || short_name_.startsWith(QLatin1String("beta")) ? 0.001
                                                                                                       : 0.5;
    }
    for (const SliderFloor& floor : kSliderFloors) {
        if (category_ == QLatin1String(floor.category) && name_.startsWith(QLatin1String(floor.name))) {
            return floor.half_width;
        }
    }
    return kDefaultSliderFloor;
}

double ParameterItem::sliderHalfWidth() const {
    if (category_ == QLatin1String("cell") && name_.startsWith(QLatin1String("length_"))) {
        return kLatticeConstantSliderHalfWidth;
    }
    return std::max(std::abs(value_) * 0.5, sliderFloor());
}

double ParameterItem::sliderLower() const {
    return edi::slider_limits(value_, sliderHalfWidth(), sliderStep(), minimum_, maximum_).first;
}

double ParameterItem::sliderUpper() const {
    return edi::slider_limits(value_, sliderHalfWidth(), sliderStep(), minimum_, maximum_).second;
}

}  // namespace edi_app
