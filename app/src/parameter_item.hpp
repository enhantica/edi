// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PARAMETER_ITEM_HPP
#define EDI_APP_PARAMETER_ITEM_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

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
    // False while the space group fixes the parameter or ties it to another (edi ADR-0019): a page shows
    // it disabled, with the value symmetry implies, and the Analysis table does not list it.
    Q_PROPERTY(bool refinable READ isRefinable NOTIFY refinableChanged)
    // False for a fixed setting (the Berar-Baldinozzi limit angle): its value is edited, it is never fitted,
    // so a page shows no fit toggle and the Analysis table does not list it.
    Q_PROPERTY(bool fittable READ isFittable CONSTANT)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QString path READ path CONSTANT)
    Q_PROPERTY(QString uid READ uid CONSTANT)
    Q_PROPERTY(QString blockKind READ blockKind CONSTANT)
    Q_PROPERTY(QString blockName READ blockName CONSTANT)
    Q_PROPERTY(QString category READ category CONSTANT)
    Q_PROPERTY(QString rowLabel READ rowLabel CONSTANT)
    Q_PROPERTY(QString name READ name CONSTANT)
    Q_PROPERTY(QString displayName READ displayName CONSTANT)
    Q_PROPERTY(QString shortName READ shortName CONSTANT)
    Q_PROPERTY(QString displayUnits READ displayUnits CONSTANT)
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

   public:
    enum Field { ValueField = 1, UncertaintyField = 2, FreeField = 4 };

    ParameterItem(const edi::ParameterEntry& entry, ProjectEditor& editor, QObject* parent);

    double value() const { return value_; }
    void setValue(double value);
    double uncertainty() const { return uncertainty_.value_or(0.0); }
    bool hasUncertainty() const { return uncertainty_.has_value(); }
    bool isFree() const { return free_; }
    void setFree(bool free);
    bool isRefinable() const { return refinable_; }
    bool isFittable() const { return fittable_; }
    // Set by the registry at each rebuild and publish: a space-group edit changes it while the parameter
    // stays shown.
    void setRefinable(bool refinable);
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
    // Set by the registry at each rebuild: a block's place and a site's element can change while the
    // parameter stays shown.
    void setBlockIndex(int index);
    void setElementSymbol(const QString& symbol);
    void setPhaseIndex(int index);

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
    void lastErrorChanged();
    void blockIndexChanged();
    void elementSymbolChanged();
    void phaseIndexChanged();

   private:
    void setLastError(const QString& error);

    ProjectEditor& editor_;
    edi::Parameter* parameter_;
    double value_;
    std::optional<double> uncertainty_;
    bool free_;
    bool refinable_;
    bool fittable_;
    QString last_error_;
    QString path_, uid_, block_kind_, block_name_, category_, row_label_, name_, display_name_, display_units_,
        short_name_, category_icon_, element_symbol_;
    double minimum_, maximum_;
    int block_index_ = -1;
    int phase_index_ = -1;
};

}  // namespace edi_app

#endif  // EDI_APP_PARAMETER_ITEM_HPP
