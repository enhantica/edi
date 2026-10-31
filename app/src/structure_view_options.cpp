// SPDX-License-Identifier: BSD-3-Clause
#include "structure_view_options.hpp"

namespace edi_app {

StructureViewOptions::StructureViewOptions(QObject* parent)
    : QObject(parent), atom_view_options_(new OptionListModel(this)) {
    atom_view_options_->setOptions({"covalent", "vdw", "ionic", "adp"});
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
        case edi::AtomView::Adp:
            return QStringLiteral("adp");
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
    } else if (view == QLatin1String("adp")) {
        assign(options_.atom_view, edi::AtomView::Adp, &StructureViewOptions::atomViewChanged);
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

void StructureViewOptions::setAdpProbability(double probability) {
    if (probability > 0.0 && probability < 1.0) {  // diffraction-lib's range; NaN fails both
        assign(options_.adp_probability, probability, &StructureViewOptions::adpProbabilityChanged);
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

std::map<std::string, std::string> StructureViewOptions::toView() const {
    const auto flag = [](bool on) { return std::string(on ? "true" : "false"); };
    return {{"atom_view", atomView().toStdString()},
            {"colour_scheme", colorScheme().toStdString()},
            {"atom_scale", QString::number(options_.atom_scale, 'g', 6).toStdString()},
            {"adp_probability", QString::number(options_.adp_probability, 'g', 6).toStdString()},
            {"labels", flag(options_.labels)},
            {"atoms", atoms().toStdString()},
            {"bonds", flag(options_.bonds)},
            {"cell", flag(options_.cell)},
            {"axes", flag(options_.axes)}};
}

void StructureViewOptions::setFromView(const std::map<std::string, std::string>& view) {
    const edi::SceneOptions defaults;
    const auto text = [&view](const char* name) {
        const auto found = view.find(name);
        return found != view.end() ? QString::fromStdString(found->second) : QString();
    };
    const auto flag = [&text](const char* name, bool fallback) {
        const QString value = text(name);
        return value == QLatin1String("true") ? true : value == QLatin1String("false") ? false : fallback;
    };
    const auto number = [&text](const char* name, double fallback) {
        bool ok = false;
        const double value = text(name).toDouble(&ok);
        return ok ? value : fallback;
    };
    setAtomView(text("atom_view").isEmpty() ? QStringLiteral("covalent") : text("atom_view"));
    setColorScheme(text("colour_scheme").isEmpty() ? QStringLiteral("jmol") : text("colour_scheme"));
    setAtomScale(number("atom_scale", defaults.atom_scale));
    setAdpProbability(number("adp_probability", defaults.adp_probability));
    setShowLabels(flag("labels", defaults.labels));
    setAtoms(text("atoms").isEmpty() ? QStringLiteral("all") : text("atoms"));
    setBonds(flag("bonds", defaults.bonds));
    setCell(flag("cell", defaults.cell));
    setAxes(flag("axes", defaults.axes));
}

}  // namespace edi_app
