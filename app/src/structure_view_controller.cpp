// SPDX-License-Identifier: BSD-3-Clause
#include "structure_view_controller.hpp"

#include <QEasingCurve>
#include <QStringList>
#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>

namespace edi_app {

namespace {

// The home view's zoom (ADR-0017 §16; the owner, 2026-10-02): the initial view, the reset and the views along a, b
// and c show the structure at 0.9 of the core's fitted size (edi::default_view, diffraction-lib's fit), with more
// margin; the orientation rule is the core's, unchanged.
constexpr double kHomeZoom = 0.9;

QVector3D vec(const edi::Vec3& v) {
    return {static_cast<float>(v.x), static_cast<float>(v.y), static_cast<float>(v.z)};
}

edi::Vec3 cross(const edi::Vec3& a, const edi::Vec3& b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}

const edi::SceneStyle* style_row(const QString& key) {
    const std::string wanted = key.toStdString();
    for (const edi::SceneStyle& style : edi::structure_style_table()) {
        if (style.key == wanted) {
            return &style;
        }
    }
    return nullptr;
}

double style_value(const char* key) {
    const edi::SceneStyle* row = style_row(QString::fromLatin1(key));
    return row != nullptr ? row->value : 0.0;
}

// The placement of one part of a triad arrow: a unit mesh along +y turned onto the arrow's direction.
edi::SceneInstance arrow_part(const edi::SceneArrow& arrow, double from, double length, double radius) {
    edi::SceneInstance part;
    const QVector3D direction = vec(arrow.direction);
    const QVector3D centre = vec(arrow.origin) + direction * static_cast<float>(from + length / 2.0);
    part.position = {centre.x(), centre.y(), centre.z()};
    part.scale = {radius, length, radius};
    const QQuaternion turn = QQuaternion::rotationTo(QVector3D(0.0f, 1.0f, 0.0f), direction);
    part.rotation = {turn.scalar(), turn.x(), turn.y(), turn.z()};
    part.color = arrow.color;
    return part;
}

}  // namespace

StructureViewController::StructureViewController(QObject* parent)
    : QObject(parent), view_animation_(new QVariantAnimation(this)), legend_(new ChartLegendModel(this)) {
    view_animation_->setStartValue(0.0);
    view_animation_->setEndValue(1.0);
    view_animation_->setEasingCurve(QEasingCurve::OutQuint);
    connect(view_animation_, &QVariantAnimation::valueChanged, this, [this](const QVariant& value) {
        // The orientation turns along the shorter arc; the zoom changes by a constant ratio, the pan linearly.
        const double t = value.toDouble();
        const edi::SceneView& a = animation_from_;
        const edi::SceneView& b = animation_to_;
        const auto rotation = [](const edi::SceneView& view) {
            return QQuaternion::fromAxes(vec(cross(view.up, view.direction)), vec(view.up), vec(view.direction));
        };
        const QQuaternion turn = QQuaternion::slerp(rotation(a), rotation(b), static_cast<float>(t));
        const QVector3D direction = turn.rotatedVector(QVector3D(0.0f, 0.0f, 1.0f)).normalized();
        const QVector3D up = turn.rotatedVector(QVector3D(0.0f, 1.0f, 0.0f)).normalized();
        view_.direction = {direction.x(), direction.y(), direction.z()};
        view_.up = {up.x(), up.y(), up.z()};
        view_.magnification = a.magnification > 0.0 && b.magnification > 0.0
                                  ? a.magnification * std::pow(b.magnification / a.magnification, t)
                                  : b.magnification;
        view_.pan_x = a.pan_x + (b.pan_x - a.pan_x) * t;
        view_.pan_y = a.pan_y + (b.pan_y - a.pan_y) * t;
        view_.projection = b.projection;
        placeCamera();
    });
    connect(view_animation_, &QVariantAnimation::finished, this, [this] {
        view_ = animation_to_;  // exactly the button's view, with no rounding of the interpolation
        placeCamera();
        emit animatingChanged();
    });
    for (const auto signal : {&StructureViewController::spheresChanged, &StructureViewController::cylindersChanged,
                              &StructureViewController::triadShaftsChanged, &StructureViewController::triadHeadsChanged,
                              &StructureViewController::sharedChanged, &StructureViewController::labelsChanged}) {
        connect(this, signal, this, [this] { refresh(); });
    }
}

void StructureViewController::setStructure(StructureViewModel* structure) {
    if (structure == structure_) {
        return;
    }
    stopAnimation();
    disconnect(source_connection_);
    disconnect(stale_connection_);
    structure_ = structure;
    source_ = {};  // another structure's frame is never kept
    viewed_ = false;
    if (structure_ != nullptr) {
        source_connection_ = connect(structure_, &StructureViewModel::sceneSourceChanged, this,
                                     &StructureViewController::sourceChanged);
        stale_connection_ = connect(structure_, &StructureViewModel::sceneWentStale, this,
                                    &StructureViewController::sourceWentStale);
    }
    emit structureChanged();
    sourceChanged();
}

void StructureViewController::setOptions(StructureViewOptions* options) {
    if (options == options_) {
        return;
    }
    disconnect(options_connection_);
    options_ = options;
    if (options_ != nullptr) {
        options_connection_ = connect(options_, &StructureViewOptions::changed, this, [this] { refresh(); });
    }
    emit optionsChanged();
    refresh();
}

void StructureViewController::setActive(bool active) {
    if (active != active_) {
        active_ = active;
        emit activeChanged();
        if (active_ && dirty_) {
            refresh();
        }
    }
}

void StructureViewController::setDark(bool dark) {
    if (dark != dark_) {
        dark_ = dark;
        emit darkChanged();
        scheduleDraw();
    }
}

void StructureViewController::setColor(QColor& field, const QColor& color, void (StructureViewController::*notify)()) {
    if (color != field) {
        field = color;
        emit(this->*notify)();
        scheduleDraw();
    }
}

void StructureViewController::setEdgeColor(const QColor& color) { setColor(edge_color_, color, &StructureViewController::edgeColorChanged); }
void StructureViewController::setAxisColorA(const QColor& color) { setColor(axis_colors_[0], color, &StructureViewController::axisColorAChanged); }
void StructureViewController::setAxisColorB(const QColor& color) { setColor(axis_colors_[1], color, &StructureViewController::axisColorBChanged); }
void StructureViewController::setAxisColorC(const QColor& color) { setColor(axis_colors_[2], color, &StructureViewController::axisColorCChanged); }
void StructureViewController::setLabelColor(const QColor& color) { setColor(label_color_, color, &StructureViewController::labelColorChanged); }
void StructureViewController::setHaloColor(const QColor& color) { setColor(halo_color_, color, &StructureViewController::haloColorChanged); }

void StructureViewController::scheduleDraw() {
    // A theme switch changes the edge, axis and label colours one binding at a time: they are drawn once, after
    // the last of them, so a changed palette repacks each table once.
    if (draw_scheduled_) {
        return;
    }
    draw_scheduled_ = true;
    QMetaObject::invokeMethod(
        this,
        [this] {
            draw_scheduled_ = false;
            draw();
        },
        Qt::QueuedConnection);
}

void StructureViewController::setViewportWidth(qreal width) {
    if (width != viewport_.width) {
        viewport_.width = width;
        emit viewportWidthChanged();
        resized();
    }
}

void StructureViewController::setViewportHeight(qreal height) {
    if (height != viewport_.height) {
        viewport_.height = height;
        emit viewportHeightChanged();
        resized();
    }
}

void StructureViewController::resized() {
    // ADR-0022 §7: the drawing is prepared again only when the size changes the fitted half height H (edi::
    // scene_drawing's `fitted_half_height`, I13's max(half height, half width × height / width)); otherwise
    // only the camera follows.
    const edi::SceneFrame& frame = scene_.frame;
    const double h = viewport_.width > 0.0 && viewport_.height > 0.0
                         ? std::max(frame.half_height, frame.half_width * viewport_.height / viewport_.width)
                         : std::max(frame.half_height, frame.half_width);
    if (h != drawing_.fitted_half_height) {
        draw();
    } else {
        placeCamera();
    }
}

void StructureViewController::setTopBand(qreal band) {
    if (band != viewport_.top_band) {
        viewport_.top_band = band;
        emit topBandChanged();
        placeCamera();
    }
}

QString StructureViewController::substitutedElements() const {
    QStringList elements;
    for (const std::string& element : scene_.substituted_elements) {
        elements.append(element.empty() ? QStringLiteral("?") : QString::fromStdString(element));  // no element
    }
    return elements.join(QStringLiteral(", "));
}

QString StructureViewController::detail() const {
    return QStringLiteral("spheres %1×%2, cylinders %3").arg(sphere_segments_).arg(sphere_rings_).arg(cylinder_segments_);
}

QString StructureViewController::projection() const {
    return view_.projection == edi::Projection::Perspective ? QStringLiteral("perspective")
                                                             : QStringLiteral("orthographic");
}

// A Qt Quick 3D light shines along its node's -z: the rotation that takes +z to the light's camera-local
// direction (right, up, towards the camera) makes it shine from there towards the scene.
QQuaternion StructureViewController::keyLightRotation() const {
    const QVector3D from(static_cast<float>(style_value("light.key.right")), static_cast<float>(style_value("light.key.up")),
                         static_cast<float>(style_value("light.key.toward")));
    return QQuaternion::rotationTo(QVector3D(0.0f, 0.0f, 1.0f), from.normalized());
}

QQuaternion StructureViewController::fillLightRotation() const {
    const QVector3D from(static_cast<float>(style_value("light.fill.right")), static_cast<float>(style_value("light.fill.up")),
                         static_cast<float>(style_value("light.fill.toward")));
    return QQuaternion::rotationTo(QVector3D(0.0f, 0.0f, 1.0f), from.normalized());
}

double StructureViewController::ambientLight() const { return style_value("light.ambient"); }
double StructureViewController::keyLight() const { return style_value("light.key"); }
double StructureViewController::fillLight() const { return style_value("light.fill"); }

QColor StructureViewController::styleColor(const QString& key) const {
    const edi::SceneStyle* row = style_row(key);
    if (row == nullptr) {
        return {};
    }
    return QColor(QString::fromStdString(dark_ ? row->dark : row->light));
}

void StructureViewController::setViewAnimationDuration(int duration) {
    duration = std::max(duration, 0);
    if (duration != view_animation_duration_) {
        view_animation_duration_ = duration;
        emit viewAnimationDurationChanged();
    }
}

bool StructureViewController::animating() const { return view_animation_->state() == QAbstractAnimation::Running; }

void StructureViewController::animateTo(const edi::SceneView& target) {
    const bool was = animating();
    view_animation_->stop();
    if (view_animation_duration_ <= 0) {
        view_ = target;
        placeCamera();
        if (was) {
            emit animatingChanged();
        }
        return;
    }
    // From where the view is, mid-animation included: a new click retargets smoothly.
    animation_from_ = view_;
    animation_to_ = target;
    view_animation_->setDuration(view_animation_duration_);
    view_animation_->start();
    if (!was) {
        emit animatingChanged();
    }
}

void StructureViewController::stopAnimation() {
    if (animating()) {
        view_animation_->stop();
        emit animatingChanged();
    }
}

void StructureViewController::toggleProjection() {
    stopAnimation();
    view_.projection = view_.projection == edi::Projection::Orthographic ? edi::Projection::Perspective
                                                                         : edi::Projection::Orthographic;
    placeCamera();
}

void StructureViewController::viewAlong(int axis) {
    const edi::Projection projection = view_.projection;
    edi::SceneView target = edi::view_along(scene_, axis);
    target.magnification = kHomeZoom;
    target.projection = projection;
    animateTo(target);
}

void StructureViewController::resetView() {
    const edi::Projection projection = view_.projection;
    edi::SceneView target = edi::default_view(scene_);
    target.magnification = kHomeZoom;
    target.projection = projection;
    animateTo(target);
}

void StructureViewController::rotateBy(double dx, double dy) {
    stopAnimation();
    view_ = edi::rotated(view_, dx, dy);
    placeCamera();
}

void StructureViewController::zoomAt(double x, double y, int angleDelta) {
    stopAnimation();
    view_ = edi::zoomed(scene_, view_, viewport_, x, y, angleDelta);
    placeCamera();
}

void StructureViewController::panBy(double dx, double dy) {
    stopAnimation();
    view_ = edi::panned(view_, dx, dy);
    placeCamera();
}

QString StructureViewController::hoverAtSphere(int instanceIndex) const {
    if (instanceIndex < 0 || static_cast<std::size_t>(instanceIndex) >= drawing_.spheres.size()) {
        return {};
    }
    return QString::fromStdString(edi::hover_text(source_, scene_, drawing_.spheres[instanceIndex].atom));
}

QString StructureViewController::hoverAtShared(double u) const {
    if (!(u >= 0.0) || u >= static_cast<double>(drawing_.shared.size())) {
        return {};
    }
    return QString::fromStdString(edi::hover_text(source_, scene_, drawing_.shared[static_cast<std::size_t>(u)]));
}

QPointF StructureViewController::projectedCentre(int atom) const {
    if (atom < 0 || static_cast<std::size_t>(atom) >= scene_.atoms.size()) {
        return {std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::quiet_NaN()};
    }
    const edi::Projected at = edi::project(scene_, view_, viewport_, scene_.atoms[atom].centre);
    return {at.x, at.y};
}

QVector3D StructureViewController::pickOrigin(double x, double y) const {
    if (view_.projection == edi::Projection::Perspective) {
        return camera_position_;
    }
    // Orthographic: the camera's plane, at the point the core's projection draws at (x, y).
    const double scale = edi::fitted_scale(scene_, viewport_, view_.projection) * view_.magnification;
    if (!(scale > 0.0)) {
        return camera_position_;
    }
    const edi::Vec3 right = cross(view_.up, view_.direction);
    const double shift = viewport_.top_band / (2.0 * (1.0 + viewport_.top_band / viewport_.height));
    const double u = (x - viewport_.width / 2.0 - view_.pan_x) / scale;
    const double v = -(y - viewport_.height / 2.0 - shift - view_.pan_y) / scale;
    const double back = 1000.0 * drawing_.fitted_half_height;
    const edi::Vec3& t = scene_.frame.target;
    return vec({t.x + right.x * u + view_.up.x * v + view_.direction.x * back,
                t.y + right.y * u + view_.up.y * v + view_.direction.y * back,
                t.z + right.z * u + view_.up.z * v + view_.direction.z * back});
}

QVector3D StructureViewController::pickDirection(double x, double y) const {
    if (view_.projection != edi::Projection::Perspective) {
        return -vec(view_.direction);
    }
    // Perspective: from the camera through the target plane's point the core draws at (x, y).
    const double scale = edi::fitted_scale(scene_, viewport_, view_.projection) * view_.magnification;
    if (!(scale > 0.0)) {
        return -vec(view_.direction);
    }
    const edi::Vec3 right = cross(view_.up, view_.direction);
    const double u = (x - viewport_.width / 2.0 - view_.pan_x) / scale;
    const double v = -(y - viewport_.height / 2.0 - view_.pan_y) / scale;
    const edi::Vec3& t = scene_.frame.target;
    const QVector3D point = vec({t.x + right.x * u + view_.up.x * v, t.y + right.y * u + view_.up.y * v,
                                 t.z + right.z * u + view_.up.z * v});
    return (point - camera_position_).normalized();
}

void StructureViewController::refresh() {
    if (!active_) {
        dirty_ = true;
        return;
    }
    present();
}

void StructureViewController::sourceChanged() {
    const edi::SceneSource next = structure_ != nullptr ? structure_->sceneSource() : edi::SceneSource{};
    // A publication that carries no geometry (a refused calculation) keeps the structure's last published frame,
    // not current; any other source replaces it. `source_` is what the frame is drawn from, and its own `current`
    // only says that its geometry was current when it was captured: the view's `current` is the latest request's
    // (latestCurrent), so no later presentation of the kept frame reports it current (ADR-0022 §1).
    if (!next.current && source_.current) {
        setCurrent(false);
        return;
    }
    source_ = next;
    if (!active_) {
        setCurrent(false);  // the frame shown is not yet this source's: it is presented when the view is shown
    }
    refresh();
}

bool StructureViewController::latestCurrent() const {
    // The structure's live source is the latest request's: current only once that request has published. When
    // it is, `source_` is that very source (sourceChanged replaces the kept one at its publication).
    return structure_ != nullptr && structure_->sceneSource().current;
}

void StructureViewController::sourceWentStale() {
    // ADR-0022 §1 with publication: the frame stays the last published one, reported as not current, until
    // the newest request publishes.
    setCurrent(false);
}

void StructureViewController::present() {
    dirty_ = false;
    const edi::SceneOptions options = options_ != nullptr ? options_->sceneOptions() : edi::SceneOptions{};
    scene_ = edi::present_structure(source_, options);
    if (!viewed_ && scene_.current) {
        const edi::Projection projection = view_.projection;
        view_ = edi::default_view(scene_);
        view_.magnification = kHomeZoom;
        view_.projection = projection;
        viewed_ = true;
    } else if (!viewed_) {
        const edi::Projection projection = view_.projection;
        view_ = edi::default_view(scene_);
        view_.magnification = kHomeZoom;
        view_.projection = projection;
    }
    QList<ChartLegendModel::Entry> entries;
    for (const edi::SceneLegendEntry& entry : scene_.legend) {
        entries.append({QString::fromStdString(entry.element), QColor(entry.color.r, entry.color.g, entry.color.b),
                        QStringLiteral("●"), false});
    }
    legend_->setEntries(entries);
    emit atomCountChanged();
    emit bondCountChanged();
    emit cellEdgeCountChanged();
    emit hasSitesChanged();
    emit hasCopiesChanged();
    emit hasBondsChanged();
    emit substitutedElementsChanged();
    setCurrent(scene_.current && latestCurrent());
    draw();
}

void StructureViewController::draw() {
    if (!active_) {
        dirty_ = true;
        return;
    }
    drawing_ = edi::scene_drawing(scene_, viewport_);
    setDetail(static_cast<int>(drawing_.spheres.size() + drawing_.shared.size()));
    if (spheres_ != nullptr) {
        spheres_->setEntries(drawing_.spheres);
    }
    if (cylinders_ != nullptr) {
        cylinders_->setEntries(drawing_.cylinders, 2 * scene_.bonds.size(),
                               edge_color_.isValid() ? std::optional<QColor>(edge_color_) : std::nullopt);
    }
    std::vector<edi::SceneInstance> shafts, heads;
    for (const edi::SceneArrow& arrow : drawing_.triad) {
        edi::SceneArrow themed = arrow;
        const int axis = arrow.letter - 'a';
        if (axis >= 0 && axis < 3 && axis_colors_[axis].isValid()) {
            const QColor& color = axis_colors_[axis];
            themed.color = {static_cast<std::uint8_t>(color.red()), static_cast<std::uint8_t>(color.green()),
                            static_cast<std::uint8_t>(color.blue())};
        }
        shafts.push_back(arrow_part(themed, 0.0, themed.shaft_length, themed.shaft_radius));
        heads.push_back(arrow_part(themed, themed.shaft_length, themed.head_length, themed.head_radius));
    }
    if (triad_shafts_ != nullptr) {
        triad_shafts_->setEntries(shafts);
    }
    if (triad_heads_ != nullptr) {
        triad_heads_->setEntries(heads);
    }
    if (shared_ != nullptr) {
        shared_->setSites(scene_, drawing_, sphere_segments_, sphere_rings_);
    }
    ++revision_;
    emit revisionChanged();
    placeCamera();
}

void StructureViewController::placeCamera() {
    if (!active_) {
        dirty_ = true;  // a hidden view prepares nothing: it is presented again when it is shown
        return;
    }
    const edi::SceneFrame& frame = scene_.frame;
    const edi::Vec3 right = cross(view_.up, view_.direction);
    const QVector3D r = vec(right), u = vec(view_.up), d = vec(view_.direction);
    camera_rotation_ = QQuaternion::fromAxes(r, u, d);
    const double width = viewport_.width, height = viewport_.height;
    const double h = drawing_.fitted_half_height > 0.0 ? drawing_.fitted_half_height : 1.0;
    QMatrix4x4 projection;  // identity for a viewport with no area
    QVector3D position = vec(frame.target);
    if (width > 0.0 && height > 0.0) {
        const double fitted = edi::fitted_scale(scene_, viewport_, view_.projection);
        if (view_.projection == edi::Projection::Perspective) {
            // edi::project: scale = fitted × magnification × D / (D − depth), no band, the pan on the screen.
            const double distance = 1.05 * h / std::tan(15.0 * std::numbers::pi / 180.0);
            const double near = 0.01 * distance, far = distance + 100.0 * h;
            const double a = 2.0 * fitted * view_.magnification * distance / width;
            const double c = 2.0 * fitted * view_.magnification * distance / height;
            position += d * static_cast<float>(distance);
            projection = QMatrix4x4(static_cast<float>(a), 0.0f, static_cast<float>(-2.0 * view_.pan_x / width), 0.0f,
                                    0.0f, static_cast<float>(c), static_cast<float>(2.0 * view_.pan_y / height), 0.0f,
                                    0.0f, 0.0f, static_cast<float>(-(far + near) / (far - near)),
                                    static_cast<float>(-2.0 * far * near / (far - near)), 0.0f, 0.0f, -1.0f, 0.0f);
        } else {
            // edi::project: scale = fitted × magnification about the target, which sits half the top band lower,
            // plus the pan. The camera stands where the screen's centre is, far back along the view direction:
            // Qt's lighting takes the view ray from the camera's position, and from that distance the rays are
            // parallel, as an orthographic camera's are in three.js, so every atom carries the same highlight
            // (standing at the target, the camera lit only the atoms near the screen's centre). The depth range
            // reaches as far on either side of the target.
            const double scale = fitted * view_.magnification;
            const double shift = viewport_.top_band / (2.0 * (1.0 + viewport_.top_band / height));
            const double back = 1000.0 * h;
            position += r * static_cast<float>(-view_.pan_x / scale) +
                        u * static_cast<float>((shift + view_.pan_y) / scale) + d * static_cast<float>(back);
            projection = QMatrix4x4(static_cast<float>(2.0 * scale / width), 0.0f, 0.0f, 0.0f, 0.0f,
                                    static_cast<float>(2.0 * scale / height), 0.0f, 0.0f, 0.0f, 0.0f,
                                    static_cast<float>(-1.0 / back), -1.0f, 0.0f, 0.0f, 0.0f, 1.0f);
            orthographic_magnification_ = scale;
            camera_clip_far_ = 2.0 * back;
        }
    }
    camera_position_ = position;
    camera_projection_ = projection;
    emit projectionChanged();
    emit cameraPositionChanged();
    emit cameraRotationChanged();
    emit cameraProjectionChanged();
    emit magnificationChanged();
    emit orthographicMagnificationChanged();
    emit cameraClipFarChanged();
    placeTexts();
}

void StructureViewController::placeTexts() {
    if (labels_ == nullptr) {
        return;
    }
    QList<StructureLabelLayer::Text> texts;
    const QColor color = label_color_.isValid() ? label_color_ : styleColor(QStringLiteral("label"));
    const QColor halo = halo_color_.isValid() ? halo_color_ : styleColor(QStringLiteral("label.halo"));
    for (const edi::SceneLabel& label : scene_.labels) {
        const edi::Projected at = edi::project(scene_, view_, viewport_, label.anchor);
        if (std::isfinite(at.x) && std::isfinite(at.y)) {
            texts.append({QPointF(at.x, at.y), QString::fromStdString(label.text), color, halo, false});
        }
    }
    for (const edi::SceneArrow& arrow : drawing_.triad) {
        const edi::Projected at = edi::project(scene_, view_, viewport_, arrow.letter_anchor);
        if (std::isfinite(at.x) && std::isfinite(at.y)) {
            const int axis = arrow.letter - 'a';
            const QColor letter = axis >= 0 && axis < 3 && axis_colors_[axis].isValid()
                                      ? axis_colors_[axis]
                                      : QColor(arrow.color.r, arrow.color.g, arrow.color.b);
            texts.append({QPointF(at.x, at.y), QString(QChar::fromLatin1(arrow.letter)), letter, halo, true});
        }
    }
    labels_->setTexts(std::move(texts));
}

void StructureViewController::setCurrent(bool current) {
    if (current != current_) {
        current_ = current;
        emit currentChanged();
    }
}

void StructureViewController::setDetail(int drawn) {
    // ADR-0017 §16's table: the first values, tuned on GPU hardware.
    const int segments = drawn <= 500 ? 32 : drawn <= 5000 ? 16 : 10;
    const int rings = drawn <= 500 ? 16 : drawn <= 5000 ? 8 : 5;
    const int cylinder = drawn <= 500 ? 16 : drawn <= 5000 ? 8 : 6;
    if (segments != sphere_segments_ || rings != sphere_rings_ || cylinder != cylinder_segments_) {
        sphere_segments_ = segments;
        sphere_rings_ = rings;
        cylinder_segments_ = cylinder;
        emit detailChanged();
        emit sphereSegmentsChanged();
        emit sphereRingsChanged();
        emit cylinderSegmentsChanged();
    }
}

}  // namespace edi_app
