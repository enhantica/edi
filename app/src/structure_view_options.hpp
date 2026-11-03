// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STRUCTURE_VIEW_OPTIONS_HPP
#define EDI_APP_STRUCTURE_VIEW_OPTIONS_HPP

#include <QObject>
#include <map>
#include <string>
#include <QString>
#include <QtQml/qqmlregistration.h>

#include "edi/structure_scene.hpp"
#include "option_list_model.hpp"

namespace edi_app {

// The structure view's options (edi ADR-0022 §5, ADR-0017 §16): diffraction-lib's, with its names, values
// and defaults — `atom_view` (covalent, vdw, ionic, adp), `color_scheme` (jmol, vesta), `atom_scale` and
// `adp_probability` of its `structure_style`, `show_labels` of its `structure_view`, and the feature set (atoms all,
// asymmetric or none; bonds, cell and axes). View state of the open project: one object, owned by the
// project view-model and shared by the toolbar, the Appearance group and every structure's view. They are not
// read from or written to the project file. A value outside its set is refused and the option stays as it was.
class StructureViewOptions : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(QString atomView READ atomView WRITE setAtomView NOTIFY atomViewChanged)
    Q_PROPERTY(QString colorScheme READ colorScheme WRITE setColorScheme NOTIFY colorSchemeChanged)
    Q_PROPERTY(double atomScale READ atomScale WRITE setAtomScale NOTIFY atomScaleChanged)
    Q_PROPERTY(double adpProbability READ adpProbability WRITE setAdpProbability NOTIFY adpProbabilityChanged)
    Q_PROPERTY(bool showLabels READ showLabels WRITE setShowLabels NOTIFY showLabelsChanged)
    Q_PROPERTY(QString atoms READ atoms WRITE setAtoms NOTIFY atomsChanged)
    Q_PROPERTY(bool bonds READ bonds WRITE setBonds NOTIFY bondsChanged)
    Q_PROPERTY(bool cell READ cell WRITE setCell NOTIFY cellChanged)
    Q_PROPERTY(bool axes READ axes WRITE setAxes NOTIFY axesChanged)
    // Whether the magnetic moments are drawn (`_structure_view.show_moments`), and their arrows' length in
    // Angstrom per Bohr magneton (`_structure_view.moment_scale`), saved with the structure (edi ADR-0068).
    Q_PROPERTY(bool showMoments READ showMoments WRITE setShowMoments NOTIFY showMomentsChanged)
    Q_PROPERTY(double momentScale READ momentScale WRITE setMomentScale NOTIFY momentScaleChanged)
    // The form the Magnetic moments table shows and edits the moments in: "crystal_axes", "cartesian" or "spherical"
    // (`_structure_view.moment_form`, saved with the structure; the stored form stays crystal axes; edi ADR-0068).
    Q_PROPERTY(QString momentForm READ momentForm WRITE setMomentForm NOTIFY momentFormChanged)
    // Where a moment's arrow sits on its atom: "through_atom", "from_centre" or "from_surface"
    // (`_structure_view.moment_view`, saved with the structure; the owner, 2026-11-03).
    Q_PROPERTY(QString momentView READ momentView WRITE setMomentView NOTIFY momentViewChanged)
    Q_PROPERTY(edi_app::OptionListModel* momentViewOptions READ momentViewOptions CONSTANT)
    // How the arrows are coloured — "atom", "greyed" or "single" — the app's preference, not saved with a project.
    Q_PROPERTY(QString momentColours READ momentColours WRITE setMomentColours NOTIFY momentColoursChanged)
    // The atom views diffraction-lib offers, for the Appearance group's selector.
    Q_PROPERTY(edi_app::OptionListModel* atomViewOptions READ atomViewOptions CONSTANT)
    Q_PROPERTY(edi_app::OptionListModel* momentFormOptions READ momentFormOptions CONSTANT)

   public:
    explicit StructureViewOptions(QObject* parent = nullptr);

    QString atomView() const;
    void setAtomView(const QString& view);
    QString colorScheme() const;
    void setColorScheme(const QString& scheme);
    double atomScale() const { return options_.atom_scale; }
    void setAtomScale(double scale);  // above 0 and at most 1
    double adpProbability() const { return options_.adp_probability; }
    void setAdpProbability(double probability);  // above 0 and below 1
    bool showLabels() const { return options_.labels; }
    void setShowLabels(bool shown);
    QString atoms() const;  // "all", "asymmetric" or "none"
    void setAtoms(const QString& atoms);
    bool bonds() const { return options_.bonds; }
    void setBonds(bool shown);
    bool cell() const { return options_.cell; }
    void setCell(bool shown);
    bool axes() const { return options_.axes; }
    void setAxes(bool shown);
    bool showMoments() const { return options_.moments; }
    void setShowMoments(bool shown);
    double momentScale() const { return options_.moment_scale; }
    QString momentColours() const;
    void setMomentColours(const QString& colours);
    void setMomentScale(double scale);  // above 0
    QString momentForm() const { return moment_form_; }
    QString momentView() const;
    void setMomentView(const QString& view);  // one of the three; anything else is ignored
    OptionListModel* momentViewOptions() const { return moment_view_options_; }
    void setMomentForm(const QString& form);  // one of the three; anything else is ignored

    // The Atoms selector's tokens, the magnetic ones only for a magnetic structure.
    Q_INVOKABLE QStringList atomChoices(bool magnetic) const;

    const edi::SceneOptions& sceneOptions() const { return options_; }
    // The options as a structure saves them (`_structure_view`, by item name), and set from such a map, each item
    // it lacks at its default.
    std::map<std::string, std::string> toView() const;
    void setFromView(const std::map<std::string, std::string>& view);
    OptionListModel* atomViewOptions() const { return atom_view_options_; }
    OptionListModel* momentFormOptions() const { return moment_form_options_; }

   signals:
    void atomViewChanged();
    void colorSchemeChanged();
    void atomScaleChanged();
    void adpProbabilityChanged();
    void showLabelsChanged();
    void atomsChanged();
    void bondsChanged();
    void cellChanged();
    void axesChanged();
    void showMomentsChanged();
    void momentScaleChanged();
    void momentFormChanged();
    void momentViewChanged();
    void momentColoursChanged();
    // Any option changed: what the views re-present on.
    void changed();

   private:
    template <class T>
    void assign(T& field, T value, void (StructureViewOptions::*notify)());
    edi::SceneOptions options_;
    // Whether the structure states show_moments, so a structure that does not keeps its bytes.
    bool moments_declared_ = false;
    OptionListModel* atom_view_options_;
    OptionListModel* moment_form_options_;
    OptionListModel* moment_view_options_;
    QString moment_form_ = QStringLiteral("crystal_axes");
};

}  // namespace edi_app

#endif  // EDI_APP_STRUCTURE_VIEW_OPTIONS_HPP
