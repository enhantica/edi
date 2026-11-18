// SPDX-License-Identifier: BSD-3-Clause
#include "polyhedra_geometry.hpp"

#include <QByteArray>
#include <QVector3D>
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace edi_app {

namespace {

struct Vertex {
    float position[3];
    float normal[3];
    float color[4];
};

QVector3D vec(const edi::Vec3& v) {
    return {static_cast<float>(v.x), static_cast<float>(v.y), static_cast<float>(v.z)};
}

float linear(std::uint8_t channel) {
    const double c = channel / 255.0;
    return static_cast<float>(c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4));
}

}  // namespace

PolyhedraGeometry::PolyhedraGeometry(QQuick3DObject* parent) : QQuick3DGeometry(parent) {}

void PolyhedraGeometry::setPolyhedra(const edi::StructureScene& scene) {
    std::vector<Vertex> vertices;
    const float big = std::numeric_limits<float>::max();
    QVector3D low(big, big, big), high(-big, -big, -big);
    for (const edi::ScenePolyhedron& polyhedron : scene.polyhedra) {
        const float colour[4] = {linear(polyhedron.color.r), linear(polyhedron.color.g), linear(polyhedron.color.b),
                                 1.0F};
        for (const auto& face : polyhedron.faces) {
            const QVector3D a = vec(polyhedron.corners[face[0]]), b = vec(polyhedron.corners[face[1]]),
                            c = vec(polyhedron.corners[face[2]]);
            const QVector3D normal = QVector3D::crossProduct(b - a, c - a).normalized();
            for (const QVector3D& p : {a, b, c}) {
                vertices.push_back({{p.x(), p.y(), p.z()},
                                    {normal.x(), normal.y(), normal.z()},
                                    {colour[0], colour[1], colour[2], colour[3]}});
                low = QVector3D(std::min(low.x(), p.x()), std::min(low.y(), p.y()), std::min(low.z(), p.z()));
                high = QVector3D(std::max(high.x(), p.x()), std::max(high.y(), p.y()), std::max(high.z(), p.z()));
            }
        }
    }
    clear();
    setStride(static_cast<int>(sizeof(Vertex)));
    setPrimitiveType(PrimitiveType::Triangles);
    addAttribute(Attribute::PositionSemantic, 0, Attribute::F32Type);
    addAttribute(Attribute::NormalSemantic, static_cast<int>(offsetof(Vertex, normal)), Attribute::F32Type);
    addAttribute(Attribute::ColorSemantic, static_cast<int>(offsetof(Vertex, color)), Attribute::F32Type);
    setVertexData(QByteArray(reinterpret_cast<const char*>(vertices.data()),
                             static_cast<qsizetype>(vertices.size() * sizeof(Vertex))));
    if (vertices.empty()) {
        low = high = QVector3D();
    }
    setBounds(low, high);
    update();
    const int count = static_cast<int>(scene.polyhedra.size());
    if (count != count_) {
        count_ = count;
        emit countChanged();
    }
}

}  // namespace edi_app
