// SPDX-License-Identifier: BSD-3-Clause
#include "structure_view_options.hpp"

#include <optional>

namespace edi_app {

StructureViewOptions::StructureViewOptions(QObject* parent)
    : QObject(parent),
      atom_view_options_(new OptionListModel(this)),
      moment_form_options_(new OptionListModel(this)),
      moment_view_options_(new OptionListModel(this)) {
    atom_view_options_->setOptions({"covalent", "vdw", "ionic", "adp"});
    // Each shows its name from crysta's dictionary: Crystal axes, Cartesian, Spherical.
    moment_form_options_->setItemOptions("structure_view.moment_form", {"crystal_axes", "cartesian", "spherical"});
    moment_view_options_->setItemOptions("structure_view.moment_view", {"through_atom", "from_centre", "from_surface"});
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
        case edi::AtomSubset::AsymmetricMagnetic:
            return QStringLiteral("asymmetric_magnetic");
        case edi::AtomSubset::MagneticAtoms:
            return QStringLiteral("magnetic");
        case edi::AtomSubset::None:
            return QStringLiteral("none");
        case edi::AtomSubset::All:
            break;
    }
    return QStringLiteral("all");
}

QStringList StructureViewOptions::atomChoices(bool magnetic) const {
    if (magnetic) {
        return {QStringLiteral("all"), QStringLiteral("asymmetric"), QStringLiteral("asymmetric_magnetic"),
                QStringLiteral("magnetic"), QStringLiteral("none")};
    }
    return {QStringLiteral("all"), QStringLiteral("asymmetric"), QStringLiteral("none")};
}

void StructureViewOptions::setAtoms(const QString& atoms) {
    if (atoms == QLatin1String("all")) {
        assign(options_.atoms, edi::AtomSubset::All, &StructureViewOptions::atomsChanged);
    } else if (atoms == QLatin1String("asymmetric")) {
        assign(options_.atoms, edi::AtomSubset::AsymmetricUnit, &StructureViewOptions::atomsChanged);
    } else if (atoms == QLatin1String("asymmetric_magnetic")) {
        assign(options_.atoms, edi::AtomSubset::AsymmetricMagnetic, &StructureViewOptions::atomsChanged);
    } else if (atoms == QLatin1String("magnetic")) {
        assign(options_.atoms, edi::AtomSubset::MagneticAtoms, &StructureViewOptions::atomsChanged);
    } else if (atoms == QLatin1String("none")) {
        assign(options_.atoms, edi::AtomSubset::None, &StructureViewOptions::atomsChanged);
    }
}

void StructureViewOptions::setBonds(bool shown) { assign(options_.bonds, shown, &StructureViewOptions::bondsChanged); }
void StructureViewOptions::setCell(bool shown) { assign(options_.cell, shown, &StructureViewOptions::cellChanged); }
void StructureViewOptions::setAxes(bool shown) { assign(options_.axes, shown, &StructureViewOptions::axesChanged); }
void StructureViewOptions::setShowMoments(bool shown) {
    moments_declared_ = moments_declared_ || shown != options_.moments;
    assign(options_.moments, shown, &StructureViewOptions::showMomentsChanged);
}
void StructureViewOptions::setMomentScale(double scale) {
    if (scale > 0.0) {
        moments_declared_ = moments_declared_ || scale != options_.moment_scale;
        assign(options_.moment_scale, scale, &StructureViewOptions::momentScaleChanged);
    }
}

void StructureViewOptions::setMomentForm(const QString& form) {
    if (form != moment_form_ && (form == QLatin1String("crystal_axes") || form == QLatin1String("cartesian") ||
                                 form == QLatin1String("spherical"))) {
        moments_declared_ = true;
        moment_form_ = form;
        emit momentFormChanged();
        emit changed();
    }
}

QString StructureViewOptions::momentView() const {
    switch (options_.moment_view) {
        case edi::MomentView::FromCentre:
            return QStringLiteral("from_centre");
        case edi::MomentView::FromSurface:
            return QStringLiteral("from_surface");
        case edi::MomentView::ThroughAtom:
            break;
    }
    return QStringLiteral("through_atom");
}

void StructureViewOptions::setMomentView(const QString& view) {
    const auto chosen = view == QLatin1String("from_centre")    ? std::optional(edi::MomentView::FromCentre)
                        : view == QLatin1String("from_surface") ? std::optional(edi::MomentView::FromSurface)
                        : view == QLatin1String("through_atom") ? std::optional(edi::MomentView::ThroughAtom)
                                                                : std::nullopt;
    if (chosen.has_value()) {
        moments_declared_ = moments_declared_ || *chosen != options_.moment_view;
        assign(options_.moment_view, *chosen, &StructureViewOptions::momentViewChanged);
    }
}

QString StructureViewOptions::momentColours() const {
    switch (options_.moment_colours) {
        case edi::MomentColours::Atom:
            return QStringLiteral("atom");
        case edi::MomentColours::Single:
            return QStringLiteral("single");
        case edi::MomentColours::GreyedAtom:
            break;
    }
    return QStringLiteral("greyed");
}

void StructureViewOptions::setMomentColours(const QString& colours) {
    const edi::MomentColours scheme = colours == QLatin1String("atom")     ? edi::MomentColours::Atom
                                      : colours == QLatin1String("single") ? edi::MomentColours::Single
                                                                           : edi::MomentColours::GreyedAtom;
    assign(options_.moment_colours, scheme, &StructureViewOptions::momentColoursChanged);
}

std::map<std::string, std::string> StructureViewOptions::toView() const {
    const auto flag = [](bool on) { return std::string(on ? "true" : "false"); };
    std::map<std::string, std::string> view{{"atom_view", atomView().toStdString()},
            {"colour_scheme", colorScheme().toStdString()},
            {"atom_scale", QString::number(options_.atom_scale, 'g', 6).toStdString()},
            {"adp_probability", QString::number(options_.adp_probability, 'g', 6).toStdString()},
            {"labels", flag(options_.labels)},
            {"atoms", atoms().toStdString()},
            {"bonds", flag(options_.bonds)},
            {"cell", flag(options_.cell)},
            {"axes", flag(options_.axes)}};
    if (moments_declared_) {
        view["show_moments"] = flag(options_.moments);
        view["moment_scale"] = QString::number(options_.moment_scale, 'g', 6).toStdString();
        view["moment_form"] = moment_form_.toStdString();
        view["moment_view"] = momentView().toStdString();
    }
    return view;
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
    setShowMoments(flag("show_moments", defaults.moments));
    setMomentScale(number("moment_scale", defaults.moment_scale));
    setMomentForm(text("moment_form").isEmpty() ? QStringLiteral("crystal_axes") : text("moment_form"));
    setMomentView(text("moment_view").isEmpty() ? QStringLiteral("through_atom") : text("moment_view"));
    moments_declared_ = view.contains("show_moments") || view.contains("moment_scale") || view.contains("moment_form") ||
                        view.contains("moment_view");
}

}  // namespace edi_app
