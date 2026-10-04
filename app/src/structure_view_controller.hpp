// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STRUCTURE_VIEW_CONTROLLER_HPP
#define EDI_APP_STRUCTURE_VIEW_CONTROLLER_HPP

#include <QColor>
#include <QMatrix4x4>
#include <QObject>
#include <QPointF>
#include <QPointer>
#include <QQuaternion>
#include <QString>
#include <QVariantAnimation>
#include <QVector3D>
#include <QtQml/qqmlregistration.h>

#include "chart_models.hpp"
#include "edi/structure_scene.hpp"
#include "shared_site_geometry.hpp"
#include "structure_instances.hpp"
#include "structure_label_layer.hpp"
#include "structure_view_model.hpp"
#include "structure_view_options.hpp"

namespace edi_app {

// One structure view (edi ADR-0017 §16, ADR-0022). It draws what the core's edi::present_structure and
// edi::scene_drawing return and computes no geometry: it holds the view (the camera's direction, up,
// magnification and pan, the projection, the viewport), asks the core for the scene of the structure's
// captured source, and hands each instance table its entries. From a publication to the instance buffers every
// step is here in C++; no QVariant and no JavaScript per atom, bond or edge. The camera is a custom one whose
// matrices are the core's projection (edi::project), so the labels the core places and the atoms Qt draws
// agree in both projections.
class StructureViewController : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(edi_app::StructureViewModel* structure READ structure WRITE setStructure NOTIFY structureChanged)
    Q_PROPERTY(edi_app::StructureViewOptions* options READ options WRITE setOptions NOTIFY optionsChanged)
    // The view is shown: a hidden view prepares nothing and is only marked dirty; it is presented once, with the
    // latest source, when it is shown again. Its `current` still turns false at once when its geometry goes stale.
    Q_PROPERTY(bool active READ active WRITE setActive NOTIFY activeChanged)
    Q_PROPERTY(bool dark READ dark WRITE setDark NOTIFY darkChanged)
    // The 3D view's size in logical pixels, and the band kept clear at its top for the toolbar and legend.
    Q_PROPERTY(qreal viewportWidth READ viewportWidth WRITE setViewportWidth NOTIFY viewportWidthChanged)
    Q_PROPERTY(qreal viewportHeight READ viewportHeight WRITE setViewportHeight NOTIFY viewportHeightChanged)
    Q_PROPERTY(qreal topBand READ topBand WRITE setTopBand NOTIFY topBandChanged)
    // The QML-declared tables and layers this controller fills.
    Q_PROPERTY(edi_app::StructureInstances* spheres MEMBER spheres_ NOTIFY spheresChanged)
    Q_PROPERTY(edi_app::StructureInstances* cylinders MEMBER cylinders_ NOTIFY cylindersChanged)
    Q_PROPERTY(edi_app::StructureInstances* triadShafts MEMBER triad_shafts_ NOTIFY triadShaftsChanged)
    Q_PROPERTY(edi_app::StructureInstances* triadHeads MEMBER triad_heads_ NOTIFY triadHeadsChanged)
    Q_PROPERTY(edi_app::SharedSiteGeometry* shared MEMBER shared_ NOTIFY sharedChanged)
    Q_PROPERTY(edi_app::StructureLabelLayer* labels MEMBER labels_ NOTIFY labelsChanged)
    // What the view shows.
    Q_PROPERTY(bool current READ current NOTIFY currentChanged)
    Q_PROPERTY(int revision READ revision NOTIFY revisionChanged)
    Q_PROPERTY(int atomCount READ atomCount NOTIFY atomCountChanged)
    Q_PROPERTY(int bondCount READ bondCount NOTIFY bondCountChanged)
    Q_PROPERTY(int cellEdgeCount READ cellEdgeCount NOTIFY cellEdgeCountChanged)
    Q_PROPERTY(bool hasSites READ hasSites NOTIFY hasSitesChanged)
    Q_PROPERTY(bool hasCopies READ hasCopies NOTIFY hasCopiesChanged)
    // crysta found a bond: the toolbar offers the bonds button only then (diffraction-lib's modebar).
    Q_PROPERTY(bool hasBonds READ hasBonds NOTIFY hasBondsChanged)
    Q_PROPERTY(QString substitutedElements READ substitutedElements NOTIFY substitutedElementsChanged)
    // The mesh detail (ADR-0017 §16): chosen by the number of drawn atoms.
    Q_PROPERTY(QString detail READ detail NOTIFY detailChanged)
    Q_PROPERTY(int sphereSegments READ sphereSegments NOTIFY sphereSegmentsChanged)
    Q_PROPERTY(int sphereRings READ sphereRings NOTIFY sphereRingsChanged)
    Q_PROPERTY(int cylinderSegments READ cylinderSegments NOTIFY cylinderSegmentsChanged)
    Q_PROPERTY(QString projection READ projection NOTIFY projectionChanged)
    Q_PROPERTY(QVector3D cameraPosition READ cameraPosition NOTIFY cameraPositionChanged)
    Q_PROPERTY(QQuaternion cameraRotation READ cameraRotation NOTIFY cameraRotationChanged)
    Q_PROPERTY(QMatrix4x4 cameraProjection READ cameraProjection NOTIFY cameraProjectionChanged)
    // The orthographic projection as Qt's own orthographic camera draws it (its magnification is pixels per
    // Angstrom; its clip planes span the depth about the target), so Qt's own picks are parallel rays as well.
    Q_PROPERTY(double orthographicMagnification READ orthographicMagnification NOTIFY orthographicMagnificationChanged)
    Q_PROPERTY(double cameraClipFar READ cameraClipFar NOTIFY cameraClipFarChanged)
    Q_PROPERTY(double magnification READ magnification NOTIFY magnificationChanged)
    // The a, b, c and Home buttons turn and fit the view over this many milliseconds (easydiffractionbeta's view
    // rotation: EasyApp's theme-change animation, 1000 ms, out-quint; the owner, 2026-10-02); 0 jumps.
    Q_PROPERTY(int viewAnimationDuration READ viewAnimationDuration WRITE setViewAnimationDuration NOTIFY viewAnimationDurationChanged)
    Q_PROPERTY(bool animating READ animating NOTIFY animatingChanged)
    Q_PROPERTY(edi_app::ChartLegendModel* legend READ legend CONSTANT)
    // The theme's colours, bound in QML to EasyApp's EaStyle.Colors as easydiffractionbeta's structure view uses
    // them (the owner, 2026-10-02; ADR-0017 §16): the cell edges, the a, b and c axes with their letters, the
    // labels and their halo. Changes that arrive together (a theme switch) redraw once.
    Q_PROPERTY(QColor edgeColor READ edgeColor WRITE setEdgeColor NOTIFY edgeColorChanged)
    Q_PROPERTY(QColor axisColorA READ axisColorA WRITE setAxisColorA NOTIFY axisColorAChanged)
    Q_PROPERTY(QColor axisColorB READ axisColorB WRITE setAxisColorB NOTIFY axisColorBChanged)
    Q_PROPERTY(QColor axisColorC READ axisColorC WRITE setAxisColorC NOTIFY axisColorCChanged)
    Q_PROPERTY(QColor labelColor READ labelColor WRITE setLabelColor NOTIFY labelColorChanged)
    Q_PROPERTY(QColor haloColor READ haloColor WRITE setHaloColor NOTIFY haloColorChanged)
    // The key and fill lights' rotations in the camera's frame: each light shines from its camera-local
    // direction (right, up, towards the camera) to the scene, as diffraction-lib's headlights.
    Q_PROPERTY(QQuaternion keyLightRotation READ keyLightRotation CONSTANT)
    Q_PROPERTY(QQuaternion fillLightRotation READ fillLightRotation CONSTANT)
    Q_PROPERTY(double ambientLight READ ambientLight CONSTANT)
    Q_PROPERTY(double keyLight READ keyLight CONSTANT)
    Q_PROPERTY(double fillLight READ fillLight CONSTANT)

   public:
    explicit StructureViewController(QObject* parent = nullptr);

    StructureViewModel* structure() const { return structure_; }
    void setStructure(StructureViewModel* structure);
    StructureViewOptions* options() const { return options_; }
    void setOptions(StructureViewOptions* options);
    bool active() const { return active_; }
    void setActive(bool active);
    bool dark() const { return dark_; }
    void setDark(bool dark);
    qreal viewportWidth() const { return viewport_.width; }
    void setViewportWidth(qreal width);
    qreal viewportHeight() const { return viewport_.height; }
    void setViewportHeight(qreal height);
    qreal topBand() const { return viewport_.top_band; }
    void setTopBand(qreal band);

    bool current() const { return current_; }
    int revision() const { return revision_; }
    int atomCount() const { return static_cast<int>(scene_.atoms.size()); }
    int bondCount() const { return static_cast<int>(scene_.bonds.size()); }
    int cellEdgeCount() const { return static_cast<int>(scene_.cell_edges.size()); }
    bool hasSites() const { return !source_.site_types.empty(); }
    bool hasCopies() const { return scene_.has_copies; }
    bool hasBonds() const { return source_.bond_distance && !source_.bond_distance->empty(); }
    QString substitutedElements() const;
    QString detail() const;
    int sphereSegments() const { return sphere_segments_; }
    int sphereRings() const { return sphere_rings_; }
    int cylinderSegments() const { return cylinder_segments_; }
    QString projection() const;
    QVector3D cameraPosition() const { return camera_position_; }
    QQuaternion cameraRotation() const { return camera_rotation_; }
    QMatrix4x4 cameraProjection() const { return camera_projection_; }
    double orthographicMagnification() const { return orthographic_magnification_; }
    double cameraClipFar() const { return camera_clip_far_; }
    double magnification() const { return view_.magnification; }
    int viewAnimationDuration() const { return view_animation_duration_; }
    void setViewAnimationDuration(int duration);
    bool animating() const;
    ChartLegendModel* legend() const { return legend_; }
    QColor edgeColor() const { return edge_color_; }
    void setEdgeColor(const QColor& color);
    QColor axisColorA() const { return axis_colors_[0]; }
    void setAxisColorA(const QColor& color);
    QColor axisColorB() const { return axis_colors_[1]; }
    void setAxisColorB(const QColor& color);
    QColor axisColorC() const { return axis_colors_[2]; }
    void setAxisColorC(const QColor& color);
    QColor labelColor() const { return label_color_; }
    void setLabelColor(const QColor& color);
    QColor haloColor() const { return halo_color_; }
    void setHaloColor(const QColor& color);
    QQuaternion keyLightRotation() const;
    QQuaternion fillLightRotation() const;
    double ambientLight() const;
    double keyLight() const;
    double fillLight() const;

    // A style key's colour in the current theme.
    Q_INVOKABLE QColor styleColor(const QString& key) const;
    // The toolbar (ADR-0017 §16, diffraction-lib's modebar) and the pointer (edi::rotated, zoomed, panned).
    Q_INVOKABLE void toggleProjection();
    Q_INVOKABLE void viewAlong(int axis);  // 0, 1, 2: a, b, c
    Q_INVOKABLE void resetView();          // the home view; the projection is kept
    Q_INVOKABLE void rotateBy(double dx, double dy);
    Q_INVOKABLE void zoomAt(double x, double y, int angleDelta);  // one notch is 120
    Q_INVOKABLE void panBy(double dx, double dy);
    // The text for a pick: a sphere by its instance index, a shared site by the pick's texture coordinate u.
    // Empty when the pick names no drawn atom.
    Q_INVOKABLE QString hoverAtSphere(int instanceIndex) const;
    Q_INVOKABLE QString hoverAtShared(double u) const;
    // Where an atom's centre is drawn, in the view's logical pixels (edi::project); (NaN, NaN) behind the camera.
    Q_INVOKABLE QPointF projectedCentre(int atom) const;
    // The scene ray under a point of the view, as the core's projection draws it: the hover picks along it
    // (View3D.rayPick), so what it names is what is drawn there in both projections. Qt's own pick would build
    // a perspective ray from the custom camera whatever its projection.
    Q_INVOKABLE QVector3D pickOrigin(double x, double y) const;
    Q_INVOKABLE QVector3D pickDirection(double x, double y) const;
    Q_INVOKABLE void refresh();

   signals:
    void structureChanged();
    void optionsChanged();
    void activeChanged();
    void darkChanged();
    void currentChanged();
    void revisionChanged();
    void detailChanged();
    void viewportWidthChanged();
    void viewportHeightChanged();
    void topBandChanged();
    void spheresChanged();
    void cylindersChanged();
    void triadShaftsChanged();
    void triadHeadsChanged();
    void sharedChanged();
    void labelsChanged();
    void atomCountChanged();
    void bondCountChanged();
    void cellEdgeCountChanged();
    void hasSitesChanged();
    void hasCopiesChanged();
    void hasBondsChanged();
    void substitutedElementsChanged();
    void sphereSegmentsChanged();
    void sphereRingsChanged();
    void cylinderSegmentsChanged();
    void projectionChanged();
    void cameraPositionChanged();
    void cameraRotationChanged();
    void cameraProjectionChanged();
    void magnificationChanged();
    void viewAnimationDurationChanged();
    void animatingChanged();
    void orthographicMagnificationChanged();
    void cameraClipFarChanged();
    void edgeColorChanged();
    void labelColorChanged();
    void haloColorChanged();
    void axisColorAChanged();
    void axisColorBChanged();
    void axisColorCChanged();

   private:
    void sourceChanged();
    void sourceWentStale();
    bool latestCurrent() const;  // the latest request has published its geometry
    void present();        // present_structure, then draw
    void draw();           // scene_drawing into the tables; one revision
    void resized();        // a new viewport size: draw when H moves, else only the camera
    void scheduleDraw();   // one draw after the changes arriving together (a theme switch)
    void animateTo(const edi::SceneView& target);  // a button's view: turned and fitted over the duration
    void stopAnimation();  // the pointer takes over from where the view is
    void setColor(QColor& field, const QColor& color, void (StructureViewController::*notify)());
    void placeCamera();    // the camera and the label layer, from the view
    void placeTexts();
    void setCurrent(bool current);
    void setDetail(int drawn);

    QPointer<StructureViewModel> structure_;
    QPointer<StructureViewOptions> options_;
    StructureInstances* spheres_ = nullptr;
    StructureInstances* cylinders_ = nullptr;
    StructureInstances* triad_shafts_ = nullptr;
    StructureInstances* triad_heads_ = nullptr;
    SharedSiteGeometry* shared_ = nullptr;
    StructureLabelLayer* labels_ = nullptr;
    QMetaObject::Connection source_connection_, stale_connection_, options_connection_;

    edi::SceneSource source_;
    edi::StructureScene scene_;
    edi::SceneDrawing drawing_;
    edi::SceneView view_;
    edi::Viewport viewport_;
    bool viewed_ = false;  // a current scene has set the view since the structure was chosen
    bool active_ = true;
    bool dark_ = false;
    bool dirty_ = false;
    bool current_ = false;
    int revision_ = 0;
    int sphere_segments_ = 32, sphere_rings_ = 16, cylinder_segments_ = 16;
    QColor edge_color_, label_color_, halo_color_;
    QColor axis_colors_[3];
    bool draw_scheduled_ = false;
    QVariantAnimation* view_animation_;
    edi::SceneView animation_from_, animation_to_;
    int view_animation_duration_ = 1000;
    QVector3D camera_position_;
    QQuaternion camera_rotation_;
    QMatrix4x4 camera_projection_;
    double orthographic_magnification_ = 1.0;
    double camera_clip_far_ = 10000.0;
    ChartLegendModel* legend_;
};

}  // namespace edi_app

#endif  // EDI_APP_STRUCTURE_VIEW_CONTROLLER_HPP
