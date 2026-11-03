// SPDX-License-Identifier: BSD-3-Clause
#include "shared_site_geometry.hpp"

#include <QByteArray>
#include <QVector3D>
#include <cstdint>
#include <vector>

namespace edi_app {

namespace {

struct Vertex {
    float position[3];
    float normal[3];
    float uv[2];
    float color[4];
};

QVector3D vec(const edi::Vec3& v) {
    return {static_cast<float>(v.x), static_cast<float>(v.y), static_cast<float>(v.z)};
}

}  // namespace

SharedSiteGeometry::SharedSiteGeometry(QQuick3DObject* parent) : QQuick3DGeometry(parent) {}

void SharedSiteGeometry::setSites(const edi::StructureScene& scene, const edi::SceneDrawing& drawing, int segments,
                                  int rings) {
    // QVector3D remains the renderer's original float-normalization adapter; tessellation policy is shared core.
    const QVector3D axis = vec(scene.frame.view_direction).normalized();
    const QVector3D up = vec(scene.frame.view_up).normalized();
    const QVector3D right = QVector3D::crossProduct(up, axis).normalized();
    const edi::SharedSiteBasis basis{{axis.x(), axis.y(), axis.z()}, {up.x(), up.y(), up.z()}, {right.x(), right.y(), right.z()}};
    const auto mesh = edi::shared_site_mesh(scene, drawing.shared, segments, rings, edi::SharedSiteMeshProfile::QtFloat, basis);
    std::vector<Vertex> vertices;
    vertices.reserve(mesh.vertices.size());
    for (const edi::SharedSiteVertex& vertex : mesh.vertices) {
        vertices.push_back({{static_cast<float>(vertex.position.x), static_cast<float>(vertex.position.y), static_cast<float>(vertex.position.z)},
                            {static_cast<float>(vertex.normal.x), static_cast<float>(vertex.normal.y), static_cast<float>(vertex.normal.z)},
                            {static_cast<float>(vertex.site), 0.0f},
                            {static_cast<float>(vertex.color.x), static_cast<float>(vertex.color.y), static_cast<float>(vertex.color.z), 1.0f}});
    }
    const auto& indices = mesh.indices;
    const QVector3D low = vec(mesh.low), high = vec(mesh.high);
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
    setBounds(low, high);
    update();
    const int count = static_cast<int>(drawing.shared.size());
    if (count != site_count_) {
        site_count_ = count;
        emit siteCountChanged();
    }
}

}  // namespace edi_app
