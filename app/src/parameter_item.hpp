// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PARAMETER_ITEM_HPP
#define EDI_APP_PARAMETER_ITEM_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

#include <memory>
#include <string>

#include "edi/parameter_walk.hpp"

namespace edi_app {

class ProjectEditor;

// One core parameter as the pages see it: every view of the parameter binds this one object.
// Writes go through the core (assign_value, D5); the registry publishes the core state after
// every change and each property signals only when its own value changed (I3).
class ParameterItem : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("A ParameterItem belongs to an open project")
    Q_PROPERTY(double value READ value WRITE setValue NOTIFY valueChanged)
    Q_PROPERTY(double uncertainty READ uncertainty NOTIFY uncertaintyChanged)
    Q_PROPERTY(bool hasUncertainty READ hasUncertainty NOTIFY hasUncertaintyChanged)
    Q_PROPERTY(bool free READ isFree WRITE setFree NOTIFY freeChanged)
    // False while the space group fixes the parameter or ties it to another (edi ADR-0019), and for a
    // descriptor that is no parameter: a page shows it disabled, with the value symmetry implies.
    Q_PROPERTY(bool refinable READ isRefinable NOTIFY refinableChanged)
    // Whether a fit of the project can vary it, by crysta's rule (edi ADR-0053); when not, fitReason says why. The
    // free toggle is enabled while it is fittable or free, so a flag set before a change can still be cleared.
    Q_PROPERTY(bool fittable READ isFittable NOTIFY fittableChanged)
    Q_PROPERTY(QString fitReason READ fitReason NOTIFY fitReasonChanged)
    // True for an auto-mode background's point intensity or term coefficient (ADR-0040): the estimate owns the value,
    // so a page shows it locked and a value write refuses; it can still be freed or fixed.
    Q_PROPERTY(bool estimated READ isEstimated NOTIFY estimatedChanged)
    // Why the value is non-physical though in range (an anisotropic tensor with a negative eigenvalue); empty if not.
    Q_PROPERTY(QString domainWarning READ domainWarning NOTIFY domainWarningChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QString path READ path CONSTANT)
    Q_PROPERTY(QString uid READ uid CONSTANT)
    Q_PROPERTY(QString blockKind READ blockKind CONSTANT)
    Q_PROPERTY(QString blockName READ blockName CONSTANT)
    Q_PROPERTY(QString category READ category CONSTANT)
    Q_PROPERTY(QString rowLabel READ rowLabel CONSTANT)
    Q_PROPERTY(QString name READ name CONSTANT)
    Q_PROPERTY(QString displayName READ displayName CONSTANT)
    // An ADP parameter's symbol and units follow its site's declared type (edi::adp_display).
    Q_PROPERTY(QString shortName READ shortName NOTIFY shortNameChanged)
    Q_PROPERTY(QString displayUnits READ displayUnits NOTIFY displayUnitsChanged)
    Q_PROPERTY(double minimum READ minimum CONSTANT)
    Q_PROPERTY(double maximum READ maximum CONSTANT)
    // The value lies outside [minimum, maximum] (the owner, 2026-10-02): a fit writes its values unchecked, as
    // the CLI's does, and the tables show such a value in red, as diffraction-lib's table of fitted parameters
    // does.
    Q_PROPERTY(bool outsideRange READ outsideRange NOTIFY outsideRangeChanged)
    // The Analysis table's iconified name (edi ADR-0017 §8): the block's place in its list (its colour),
    // the category's icon, and for an atom site the site's element (the atom icon's colour).
    Q_PROPERTY(int blockIndex READ blockIndex NOTIFY blockIndexChanged)
    Q_PROPERTY(QString categoryIcon READ categoryIcon CONSTANT)
    Q_PROPERTY(QString elementSymbol READ elementSymbol NOTIFY elementSymbolChanged)
    // For a parameter one phase owns (its scale, its texture) in a project of several structures, the place
    // of that structure in the project's list (its colour); -1 otherwise.
    Q_PROPERTY(int phaseIndex READ phaseIndex NOTIFY phaseIndexChanged)
    // The value and its s.u. as the project file and the Text tab spell them under the project's rule
    // (edi::file_text): what a field, the slider and the Analysis table show. The s.u. is empty without one.
    Q_PROPERTY(QString fileValue READ fileValue NOTIFY fileValueChanged)
    Q_PROPERTY(QString fileSu READ fileSu NOTIFY fileSuChanged)
    // One unit of the last digit the item's display format shows: the slider's step (edi::display_step).
    Q_PROPERTY(double sliderStep READ sliderStep NOTIFY sliderStepChanged)
    // The item's label for its variant and its `.edi` name, as a field's and a cell's tooltip names it (edi ADR-0051);
    // empty for a parameter the dictionary does not know.
    Q_PROPERTY(QString toolTip READ toolTip NOTIFY toolTipChanged)

   public:
    enum Field { ValueField = 1, UncertaintyField = 2, FreeField = 4 };

    ParameterItem(const edi::ParameterEntry& entry, ProjectEditor& editor, QObject* parent);
    // A descriptor that is no parameter (edi::model_descriptors): its value is shown, never typed or fitted.
    ParameterItem(const edi::DescriptorEntry& entry, ProjectEditor& editor, QObject* parent);

    double value() const { return value_; }
    void setValue(double value);
    double uncertainty() const { return uncertainty_.value_or(0.0); }
    bool hasUncertainty() const { return uncertainty_.has_value(); }
    bool isFree() const { return free_; }
    void setFree(bool free);
    bool isRefinable() const { return refinable_; }
    bool isFittable() const { return fittable_; }
    QString fitReason() const { return fit_reason_; }
    // Set by the registry at each publish from the parameter's mark (edi::refresh_fittability).
    void setFittability(bool fittable, const QString& reason);
    bool isDescriptorValue() const { return own_ != nullptr; }
    // A descriptor row's value, as the model holds it now; set by the registry before each publish.
    void setDescriptorValue(double value);
    // Set by the registry at each rebuild and publish: a space-group edit changes it while the parameter
    // stays shown.
    void setRefinable(bool refinable);
    bool isEstimated() const { return estimated_; }
    // Set by the registry at each publish, as the mode changes while the parameter stays shown.
    void setEstimated(bool estimated);
    QString domainWarning() const { return domain_warning_; }
    void setDomainWarning(const QString& warning);
    QString lastError() const { return last_error_; }
    QString path() const { return path_; }
    QString uid() const { return uid_; }
    QString blockKind() const { return block_kind_; }
    QString blockName() const { return block_name_; }
    QString category() const { return category_; }
    QString rowLabel() const { return row_label_; }
    QString name() const { return name_; }
    QString displayName() const { return display_name_; }
    // The symbol a field label shows (σ₁, α₀, U), read from the spec's LaTeX name; the display name
    // when the spec has none this can spell.
    QString shortName() const { return short_name_; }
    QString displayUnits() const { return display_units_; }
    double minimum() const { return minimum_; }
    double maximum() const { return maximum_; }
    bool outsideRange() const { return value_ < minimum_ || value_ > maximum_; }
    // The Analysis slider spans the value ± this half width, set when a parameter is selected or its value is
    // committed: a lattice constant's kLatticeConstantSliderHalfWidth (0.05 Å; the owner, 2026-10-04); any
    // other parameter's half its magnitude, at least 1e-3.
    Q_INVOKABLE double sliderHalfWidth() const;
    int blockIndex() const { return block_index_; }
    QString categoryIcon() const { return category_icon_; }
    QString elementSymbol() const { return element_symbol_; }
    int phaseIndex() const { return phase_index_; }
    QString fileValue() const { return file_value_; }
    QString fileSu() const { return file_su_; }
    double sliderStep() const;
    QString toolTip() const;
    // A number of this item, a slider limit, in its display format; empty for a parameter the dictionary does not know.
    Q_INVOKABLE QString displayText(double value) const;
    // Set by the registry at each rebuild: a block's place and a site's element can change while the
    // parameter stays shown.
    void setBlockIndex(int index);
    void setElementSymbol(const QString& symbol);
    void setPhaseIndex(int index);
    void setLabel(const QString& short_name, const QString& units);
    // The token the label and format follow (an ADP's site type, an active doublet), set at each publish.
    void setVariant(const QString& variant);
    const QString& variant() const { return variant_; }
    // The project's `_su_format.rule`, set at each rebuild and publish; the file text follows it.
    // The project's s.u. rule, and whether its save writes this value exactly (edi::save_spelling).
    void setSpelling(const std::string& rule, bool exact);

    const edi::Parameter* parameter() const { return parameter_; }
    // Emit a signal for each field whose core value differs from the last published one; returns
    // the changed fields (ParameterItem::Field bits).
    int publish();

   signals:
    void valueChanged();
    void outsideRangeChanged();
    void uncertaintyChanged();
    void hasUncertaintyChanged();
    void freeChanged();
    void refinableChanged();
    void fittableChanged();
    void fitReasonChanged();
    void estimatedChanged();
    void domainWarningChanged();
    void lastErrorChanged();
    void blockIndexChanged();
    void elementSymbolChanged();
    void phaseIndexChanged();
    void shortNameChanged();
    void displayUnitsChanged();
    void fileValueChanged();
    void fileSuChanged();
    void sliderStepChanged();
    void toolTipChanged();

   private:
    void setLastError(const QString& error);
    void refreshFileText();

    ProjectEditor& editor_;
    std::unique_ptr<edi::Parameter> own_;  // a descriptor row's value; parameter_ points at it
    edi::Parameter* parameter_;
    double value_;
    std::optional<double> uncertainty_;
    bool free_;
    bool refinable_;
    bool fittable_ = true;
    QString fit_reason_;
    bool estimated_ = false;
    QString domain_warning_;
    QString last_error_;
    QString path_, uid_, block_kind_, block_name_, category_, row_label_, name_, display_name_, display_units_,
        short_name_, category_icon_, element_symbol_, variant_, file_value_, file_su_;
    std::string su_rule_;
    bool exact_ = false;
    double minimum_, maximum_;
    int block_index_ = -1;
    int phase_index_ = -1;
};

}  // namespace edi_app

#endif  // EDI_APP_PARAMETER_ITEM_HPP
