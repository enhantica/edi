// SPDX-License-Identifier: BSD-3-Clause
#include "scan_lines.hpp"

#include <QQuickWindow>
#include <QSGGeometry>
#include <QSGGeometryNode>
#include <QSGMaterial>
#include <QSGMaterialShader>
#include <QSGRectangleNode>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <type_traits>

namespace edi_app {

namespace {

// How many patterns one node draws: the shader's uniform arrays hold this many (app/shaders/scan_line.vert).
constexpr std::size_t kGroup = 64;

// What the shader is given besides the matrix and the opacity: each pattern's baseline and height in item pixels,
// and its colour.
class LineMaterial : public QSGMaterial {
   public:
    LineMaterial() { setFlag(Blending); }
    QSGMaterialType* type() const override {
        static QSGMaterialType kind;
        return &kind;
    }
    QSGMaterialShader* createShader(QSGRendererInterface::RenderMode /*mode*/) const override;
    int compare(const QSGMaterial* other) const override {
        const auto* that = static_cast<const LineMaterial*>(other);
        if (placement != that->placement || colour != that->colour || half_width != that->half_width ||
            pixel != that->pixel) {
            return this < that ? -1 : 1;
        }
        return 0;
    }

    std::array<float, 4 * kGroup> placement{};
    std::array<float, 4 * kGroup> colour{};
    float half_width = 1.0F;
    float pixel = 1.0F;  // one device pixel, in item pixels
};

class LineShader : public QSGMaterialShader {
   public:
    LineShader() {
        setShaderFileName(VertexStage, QStringLiteral(":/edi/shaders/scan_line.vert.qsb"));
        setShaderFileName(FragmentStage, QStringLiteral(":/edi/shaders/scan_line.frag.qsb"));
    }
    // The uniform block's std140 layout: the matrix, the placements, the colours, then the opacity, the half width and
    // the device pixel.
    bool updateUniformData(RenderState& state, QSGMaterial* material, QSGMaterial* /*old*/) override {
        constexpr std::size_t kArray = 4 * kGroup * sizeof(float);
        char* buffer = state.uniformData()->data();
        const auto* line = static_cast<const LineMaterial*>(material);
        std::memcpy(buffer, state.combinedMatrix().constData(), 64);
        std::memcpy(buffer + 64, line->placement.data(), kArray);
        std::memcpy(buffer + 64 + kArray, line->colour.data(), kArray);
        const float rest[3] = {state.opacity(), line->half_width, line->pixel};
        std::memcpy(buffer + 64 + 2 * kArray, rest, sizeof(rest));
        return true;
    }
};

QSGMaterialShader* LineMaterial::createShader(QSGRendererInterface::RenderMode /*mode*/) const {
    return new LineShader;
}

// A vertex: its segment's two points (x in pixels, v in [0, 1]), the points before and after it (each equal to the
// segment's end when there is none), which end and which side of the segment it is (end * 2 + side), and its pattern's
// place in the group with whether the points before and after exist (place * 4 + before + 2 * after).
struct Vertex {
    float x0, v0, x1, v1, xb, vb, xa, va, corner, pattern;
};

const QSGGeometry::AttributeSet& vertex_layout() {
    static const QSGGeometry::Attribute attributes[] = {
        QSGGeometry::Attribute::createWithAttributeType(0, 4, QSGGeometry::FloatType, QSGGeometry::PositionAttribute),
        QSGGeometry::Attribute::createWithAttributeType(1, 4, QSGGeometry::FloatType, QSGGeometry::UnknownAttribute),
        QSGGeometry::Attribute::createWithAttributeType(2, 2, QSGGeometry::FloatType, QSGGeometry::UnknownAttribute)};
    static const QSGGeometry::AttributeSet layout = {3, sizeof(Vertex), attributes};
    return layout;
}

bool finite_point(const ScanLines::Trace& trace, std::size_t k) {
    return std::isfinite(trace.x[k]) && std::isfinite(trace.v[k]);
}

// A group of traces' quads, in order: four vertices and two triangles for each segment whose two points are finite.
QSGGeometry* quads_of(const std::vector<ScanLines::Trace>& traces, std::size_t first, std::size_t count) {
    std::size_t segments = 0;
    for (std::size_t i = first; i < first + count; ++i) {
        const ScanLines::Trace& trace = traces[i];
        const std::size_t points = std::min(trace.x.size(), trace.v.size());
        for (std::size_t k = 0; k + 1 < points; ++k) {
            segments += finite_point(trace, k) && finite_point(trace, k + 1) ? 1 : 0;
        }
    }
    const bool wide = 4 * segments > std::numeric_limits<quint16>::max();
    auto* geometry = new QSGGeometry(vertex_layout(), static_cast<int>(4 * segments), static_cast<int>(6 * segments),
                                     wide ? QSGGeometry::UnsignedIntType : QSGGeometry::UnsignedShortType);
    geometry->setDrawingMode(QSGGeometry::DrawTriangles);
    auto* vertex = static_cast<Vertex*>(geometry->vertexData());
    for (std::size_t i = first; i < first + count; ++i) {
        const ScanLines::Trace& trace = traces[i];
        const auto place = static_cast<float>(i - first);
        const std::size_t points = std::min(trace.x.size(), trace.v.size());
        for (std::size_t k = 0; k + 1 < points; ++k) {
            if (!finite_point(trace, k) || !finite_point(trace, k + 1)) {
                continue;
            }
            const float x0 = trace.x[k], v0 = trace.v[k], x1 = trace.x[k + 1], v1 = trace.v[k + 1];
            const bool before = k > 0 && finite_point(trace, k - 1);
            const bool after = k + 2 < points && finite_point(trace, k + 2);
            const float xb = before ? trace.x[k - 1] : x0, vb = before ? trace.v[k - 1] : v0;
            const float xa = after ? trace.x[k + 2] : x1, va = after ? trace.v[k + 2] : v1;
            const float code = 4.0F * place + (before ? 1.0F : 0.0F) + (after ? 2.0F : 0.0F);
            for (const float corner : {0.0F, 1.0F, 2.0F, 3.0F}) {
                *vertex++ = {x0, v0, x1, v1, xb, vb, xa, va, corner, code};
            }
        }
    }
    const auto fill = [segments](auto* index) {
        using Index = std::remove_pointer_t<decltype(index)>;
        for (std::size_t q = 0; q < segments; ++q) {
            for (const std::size_t corner : {0U, 1U, 2U, 1U, 3U, 2U}) {
                *index++ = static_cast<Index>(4 * q + corner);
            }
        }
    };
    if (wide) {
        fill(geometry->indexDataAsUInt());
    } else {
        fill(geometry->indexDataAsUShort());
    }
    return geometry;
}

}  // namespace

ScanLines::ScanLines(QQuickItem* parent) : QQuickItem(parent) { setFlag(ItemHasContents, true); }

void ScanLines::setTraces(std::vector<Trace> traces) {
    traces_ = std::move(traces);
    traces_changed_ = true;
    update();
}

void ScanLines::setStyles(std::vector<Style> styles) {
    styles_ = std::move(styles);
    update();
}

void ScanLines::setBands(std::vector<QRectF> bands, const QColor& colour) {
    if (bands != bands_ || colour != band_colour_) {
        bands_ = std::move(bands);
        band_colour_ = colour;
        bands_changed_ = true;
        update();
    }
}

void ScanLines::setYMin(double value) {
    if (value != y_min_) {
        y_min_ = value;
        emit yMinChanged();
        update();
    }
}

void ScanLines::setYMax(double value) {
    if (value != y_max_) {
        y_max_ = value;
        emit yMaxChanged();
        update();
    }
}

void ScanLines::setLineWidth(double width) {
    if (width != line_width_) {
        line_width_ = width;
        emit lineWidthChanged();
        update();
    }
}

QSGNode* ScanLines::updatePaintNode(QSGNode* old, UpdatePaintNodeData* /*data*/) {
    // The root's first child holds the bands; the groups of lines follow it.
    auto* root = old;
    if (root == nullptr) {
        root = new QSGNode;
        root->appendChildNode(new QSGNode);
    }
    QSGNode* bands = root->firstChild();
    if (bands_changed_ && window() != nullptr) {
        while (QSGNode* child = bands->firstChild()) {
            bands->removeChildNode(child);
            delete child;
        }
        for (const QRectF& band : bands_) {
            QSGRectangleNode* node = window()->createRectangleNode();
            node->setRect(band);
            node->setColor(band_colour_);
            bands->appendChildNode(node);
        }
        bands_changed_ = false;
    }
    const std::size_t lines = std::min(traces_.size(), styles_.size());
    const std::size_t groups = (lines + kGroup - 1) / kGroup;
    const bool rebuild = traces_changed_ || static_cast<std::size_t>(root->childCount() - 1) != groups;
    if (rebuild) {
        while (QSGNode* child = bands->nextSibling()) {
            root->removeChildNode(child);
            delete child;
        }
    }
    const double span = y_max_ - y_min_;
    const double h = height();
    QSGNode* child = bands->nextSibling();
    for (std::size_t g = 0; g < groups; ++g) {
        const std::size_t first = g * kGroup, count = std::min(kGroup, lines - first);
        auto* node = static_cast<QSGGeometryNode*>(child);
        if (rebuild) {
            node = new QSGGeometryNode;
            node->setGeometry(quads_of(traces_, first, count));
            node->setMaterial(new LineMaterial);
            node->setFlags(QSGNode::OwnsGeometry | QSGNode::OwnsMaterial);
            root->appendChildNode(node);
        }
        auto* material = static_cast<LineMaterial*>(node->material());
        for (std::size_t i = 0; i < count; ++i) {
            const Style& style = styles_[first + i];
            material->placement[4 * i] = span > 0.0 ? static_cast<float>((y_max_ - style.row) / span * h) : 0.0F;
            material->placement[4 * i + 1] = span > 0.0 ? static_cast<float>(style.lift / span * h) : 0.0F;
            const float alpha = style.colour.alphaF();
            material->colour[4 * i] = style.colour.redF() * alpha;
            material->colour[4 * i + 1] = style.colour.greenF() * alpha;
            material->colour[4 * i + 2] = style.colour.blueF() * alpha;
            material->colour[4 * i + 3] = alpha;
        }
        material->half_width = static_cast<float>(line_width_ / 2.0);
        material->pixel = static_cast<float>(1.0 / (window() != nullptr ? window()->effectiveDevicePixelRatio() : 1.0));
        node->markDirty(QSGNode::DirtyMaterial);
        child = node->nextSibling();
    }
    traces_changed_ = false;
    // A hidden item draws nothing: a size change syncs it while the painter draws the view.
    if (isVisible()) {
        emit rendered();
    }
    return root;
}

}  // namespace edi_app
