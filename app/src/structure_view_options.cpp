// SPDX-License-Identifier: BSD-3-Clause
#include "structure_view_options.hpp"

namespace edi_app {

StructureViewOptions::StructureViewOptions(QObject* parent)
    : QObject(parent), atom_view_options_(new OptionListModel(this)) {
    atom_view_options_->setOptions({"covalent", "vdw", "ionic"});
}

template <class T>
void StructureViewOptions::assign(T& field, T value, void (StructureViewOptions::*notify)()) {
    if (field != value) {
        field = value;
        emit(this->*notify)();
        emit changed();
    }
}

QString StructureViewOptions::atomView() const {
    switch (options_.atom_view) {
        case edi::AtomView::VanDerWaals:
            return QStringLiteral("vdw");
        case edi::AtomView::Ionic:
            return QStringLiteral("ionic");
        case edi::AtomView::Covalent:
            break;
    }
    return QStringLiteral("covalent");
}

void StructureViewOptions::setAtomView(const QString& view) {
    if (view == QLatin1String("covalent")) {
        assign(options_.atom_view, edi::AtomView::Covalent, &StructureViewOptions::atomViewChanged);
    } else if (view == QLatin1String("vdw")) {
        assign(options_.atom_view, edi::AtomView::VanDerWaals, &StructureViewOptions::atomViewChanged);
    } else if (view == QLatin1String("ionic")) {
        assign(options_.atom_view, edi::AtomView::Ionic, &StructureViewOptions::atomViewChanged);
    }
}

QString StructureViewOptions::colorScheme() const {
    return options_.colors == edi::ColorScheme::Vesta ? QStringLiteral("vesta") : QStringLiteral("jmol");
}

void StructureViewOptions::setColorScheme(const QString& scheme) {
    if (scheme == QLatin1String("jmol")) {
        assign(options_.colors, edi::ColorScheme::Jmol, &StructureViewOptions::colorSchemeChanged);
    } else if (scheme == QLatin1String("vesta")) {
        assign(options_.colors, edi::ColorScheme::Vesta, &StructureViewOptions::colorSchemeChanged);
    }
}

void StructureViewOptions::setAtomScale(double scale) {
    if (scale > 0.0 && scale <= 1.0) {  // diffraction-lib's range; NaN fails both
        assign(options_.atom_scale, scale, &StructureViewOptions::atomScaleChanged);
    }
}

void StructureViewOptions::setShowLabels(bool shown) { assign(options_.labels, shown, &StructureViewOptions::showLabelsChanged); }

QString StructureViewOptions::atoms() const {
    switch (options_.atoms) {
        case edi::AtomSubset::AsymmetricUnit:
            return QStringLiteral("asymmetric");
        case edi::AtomSubset::None:
            return QStringLiteral("none");
        case edi::AtomSubset::All:
            break;
    }
    return QStringLiteral("all");
}

void StructureViewOptions::setAtoms(const QString& atoms) {
    if (atoms == QLatin1String("all")) {
        assign(options_.atoms, edi::AtomSubset::All, &StructureViewOptions::atomsChanged);
    } else if (atoms == QLatin1String("asymmetric")) {
        assign(options_.atoms, edi::AtomSubset::AsymmetricUnit, &StructureViewOptions::atomsChanged);
    } else if (atoms == QLatin1String("none")) {
        assign(options_.atoms, edi::AtomSubset::None, &StructureViewOptions::atomsChanged);
    }
}

void StructureViewOptions::setBonds(bool shown) { assign(options_.bonds, shown, &StructureViewOptions::bondsChanged); }
void StructureViewOptions::setCell(bool shown) { assign(options_.cell, shown, &StructureViewOptions::cellChanged); }
void StructureViewOptions::setAxes(bool shown) { assign(options_.axes, shown, &StructureViewOptions::axesChanged); }

void StructureViewOptions::cycleAtoms(bool hasCopies) {
    switch (options_.atoms) {
        case edi::AtomSubset::All:
            assign(options_.atoms, hasCopies ? edi::AtomSubset::AsymmetricUnit : edi::AtomSubset::None, &StructureViewOptions::atomsChanged);
            break;
        case edi::AtomSubset::AsymmetricUnit:
            assign(options_.atoms, edi::AtomSubset::None, &StructureViewOptions::atomsChanged);
            break;
        case edi::AtomSubset::None:
            assign(options_.atoms, edi::AtomSubset::All, &StructureViewOptions::atomsChanged);
            break;
    }
}

}  // namespace edi_app
