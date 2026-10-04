// SPDX-License-Identifier: BSD-3-Clause
#include "shared_site_geometry.hpp"

#include <QByteArray>
#include <QVector3D>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numbers>

namespace edi_app {

namespace {

struct Vertex {
    float position[3];
    float normal[3];
    float uv[2];
    float color[4];
};

// sRGB to linear light: a vertex colour is used as given, while Qt converts a material or instance colour.
float linear(std::uint8_t channel) {
    const double c = channel / 255.0;
    return static_cast<float>(c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4));
}

QVector3D vec(const edi::Vec3& v) {
    return {static_cast<float>(v.x), static_cast<float>(v.y), static_cast<float>(v.z)};
}

}  // namespace

SharedSiteGeometry::SharedSiteGeometry(QQuick3DObject* parent) : QQuick3DGeometry(parent) {}

void SharedSiteGeometry::setSites(const edi::StructureScene& scene, const edi::SceneDrawing& drawing, int segments,
                                  int rings) {
    segments = std::max(segments, 3);
    rings = std::max(rings, 2);
    const QVector3D axis = vec(scene.frame.view_direction).normalized();
    const QVector3D up = vec(scene.frame.view_up).normalized();
    const QVector3D right = QVector3D::crossProduct(up, axis).normalized();
    std::vector<Vertex> vertices;
    std::vector<std::uint32_t> indices;
    QVector3D low(std::numeric_limits<float>::max(), std::numeric_limits<float>::max(),
                  std::numeric_limits<float>::max());
    QVector3D high = -low;
    for (std::size_t k = 0; k != drawing.shared.size(); ++k) {
        const edi::SceneAtom& atom = scene.atoms[drawing.shared[k]];
        const QVector3D centre = vec(atom.centre);
        const auto radius = static_cast<float>(atom.radius);
        const float u = static_cast<float>(k) + 0.5f;
        low = QVector3D(std::min(low.x(), centre.x() - radius), std::min(low.y(), centre.y() - radius),
                        std::min(low.z(), centre.z() - radius));
        high = QVector3D(std::max(high.x(), centre.x() + radius), std::max(high.y(), centre.y() + radius),
                         std::max(high.z(), centre.z() + radius));
        double start = 0.0;
        for (const edi::ScenePart& part : atom.parts) {
            const double fraction = std::isfinite(part.fraction) ? std::clamp(part.fraction, 0.0, 1.0) : 0.0;
            if (fraction <= 0.0) {
                continue;  // no wedge, no triangle
            }
            const double span = fraction * 2.0 * std::numbers::pi;
            const int steps = std::max(1, static_cast<int>(std::ceil(fraction * segments)));
            const float color[4] = {linear(part.color.r), linear(part.color.g), linear(part.color.b), 1.0f};
            const auto base = static_cast<std::uint32_t>(vertices.size());
            for (int i = 0; i <= rings; ++i) {
                const double theta = std::numbers::pi * i / rings;  // from the axis, towards the viewer at 0
                for (int j = 0; j <= steps; ++j) {
                    const double phi = start + span * j / steps;  // from up, towards right
                    const QVector3D normal = static_cast<float>(std::sin(theta)) *
                                                 (static_cast<float>(std::cos(phi)) * up +
                                                  static_cast<float>(std::sin(phi)) * right) +
                                             static_cast<float>(std::cos(theta)) * axis;
                    const QVector3D position = centre + radius * normal;
                    vertices.push_back({{position.x(), position.y(), position.z()},
                                        {normal.x(), normal.y(), normal.z()},
                                        {u, 0.0f},
                                        {color[0], color[1], color[2], color[3]}});
                }
            }
            const auto row = static_cast<std::uint32_t>(steps + 1);
            for (int i = 0; i != rings; ++i) {
                for (int j = 0; j != steps; ++j) {
                    const std::uint32_t a = base + static_cast<std::uint32_t>(i) * row + static_cast<std::uint32_t>(j);
                    const std::uint32_t b = a + row;
                    indices.insert(indices.end(), {a, a + 1, b, a + 1, b + 1, b});
                }
            }
            start += span;
        }
    }
    clear();
    setStride(static_cast<int>(sizeof(Vertex)));
    setPrimitiveType(PrimitiveType::Triangles);
    addAttribute(Attribute::PositionSemantic, 0, Attribute::F32Type);
    addAttribute(Attribute::NormalSemantic, static_cast<int>(offsetof(Vertex, normal)), Attribute::F32Type);
    addAttribute(Attribute::TexCoord0Semantic, static_cast<int>(offsetof(Vertex, uv)), Attribute::F32Type);
    addAttribute(Attribute::ColorSemantic, static_cast<int>(offsetof(Vertex, color)), Attribute::F32Type);
    addAttribute(Attribute::IndexSemantic, 0, Attribute::U32Type);
    setVertexData(QByteArray(reinterpret_cast<const char*>(vertices.data()),
                             static_cast<qsizetype>(vertices.size() * sizeof(Vertex))));
    setIndexData(QByteArray(reinterpret_cast<const char*>(indices.data()),
                            static_cast<qsizetype>(indices.size() * sizeof(std::uint32_t))));
    if (vertices.empty()) {
        low = high = QVector3D();
    }
    setBounds(low, high);
    update();
    const int count = static_cast<int>(drawing.shared.size());
    if (count != site_count_) {
        site_count_ = count;
        emit siteCountChanged();
    }
}

}  // namespace edi_app
