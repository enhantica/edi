// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STRUCTURE_VIEW_OPTIONS_HPP
#define EDI_APP_STRUCTURE_VIEW_OPTIONS_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

#include "edi/structure_scene.hpp"
#include "option_list_model.hpp"

namespace edi_app {

// The structure view's options (edi ADR-0022 §5, ADR-0017 §16): diffraction-lib's, with its names, values
// and defaults — `atom_view` (covalent, vdw, ionic), `color_scheme` (jmol, vesta) and
// `atom_scale` of its `structure_style`, `show_labels` of its `structure_view`, and the feature set (atoms all,
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
    Q_PROPERTY(bool showLabels READ showLabels WRITE setShowLabels NOTIFY showLabelsChanged)
    Q_PROPERTY(QString atoms READ atoms WRITE setAtoms NOTIFY atomsChanged)
    Q_PROPERTY(bool bonds READ bonds WRITE setBonds NOTIFY bondsChanged)
    Q_PROPERTY(bool cell READ cell WRITE setCell NOTIFY cellChanged)
    Q_PROPERTY(bool axes READ axes WRITE setAxes NOTIFY axesChanged)
    // The atom views diffraction-lib offers, less `adp`, for the Appearance group's selector.
    Q_PROPERTY(edi_app::OptionListModel* atomViewOptions READ atomViewOptions CONSTANT)

   public:
    explicit StructureViewOptions(QObject* parent = nullptr);

    QString atomView() const;
    void setAtomView(const QString& view);
    QString colorScheme() const;
    void setColorScheme(const QString& scheme);
    double atomScale() const { return options_.atom_scale; }
    void setAtomScale(double scale);  // above 0 and at most 1
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

    // The atom subset's next state, as diffraction-lib's atoms button: all, asymmetric unit, none; with no
    // atom outside the asymmetric unit, all and none.
    Q_INVOKABLE void cycleAtoms(bool hasCopies);

    const edi::SceneOptions& sceneOptions() const { return options_; }
    OptionListModel* atomViewOptions() const { return atom_view_options_; }

   signals:
    void atomViewChanged();
    void colorSchemeChanged();
    void atomScaleChanged();
    void showLabelsChanged();
    void atomsChanged();
    void bondsChanged();
    void cellChanged();
    void axesChanged();
    // Any option changed: what the views re-present on.
    void changed();

   private:
    template <class T>
    void assign(T& field, T value, void (StructureViewOptions::*notify)());
    edi::SceneOptions options_;
    OptionListModel* atom_view_options_;
};

}  // namespace edi_app

#endif  // EDI_APP_STRUCTURE_VIEW_OPTIONS_HPP
