// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "edi/edit.hpp"
#include "edi/assistant_limits.hpp"
#include <QString>
#include <QVariant>
#include <QVariantMap>
#include <stdexcept>
#include <algorithm>
#include <limits>
namespace edi_app {
// ItemVec::assign prepares candidate/admissibility keys, new columns, row holds,
// anchors, three hash indexes and kept-column references before its one commit.
// Existing live rows are borrowed. The selected clone plus two scalar snapshots,
// before/after pointer vectors and ordinary model publication have separate roles.
inline constexpr quint64 background_preparation_bytes() {
    using Row = edi::LineSegment;
    using Limits = edi::assistant::Limits;
    static_assert(std::tuple_size_v<decltype(crysta::RowSchema<Row>::fields)> == 3,
                  "Background preparation must admit every row field");
    constexpr quint64 numeric = 2 * sizeof(double) + 3 * sizeof(std::optional<double>) + sizeof(std::uint8_t);
    constexpr quint64 indexes = 3 * (sizeof(std::pair<const Row*, std::size_t>) + 4 * sizeof(void*));
    constexpr quint64 pointers = 8 * sizeof(std::shared_ptr<Row>);
    constexpr quint64 strings = 4 * (sizeof(std::string) + Limits::id_bytes);
    constexpr quint64 rows = sizeof(edi::detail::RowHold) + 2 * sizeof(edi::detail::Holding) + sizeof(crysta::detail::RowAnchor);
    constexpr quint64 ui = 2 * (sizeof(QVariantMap) + 3 * sizeof(QVariant) + sizeof(QString) + 2 * Limits::id_bytes);
    return sizeof(edi::BackgroundPointChange) + sizeof(Row) + 3 * Limits::id_bytes +
        sizeof(edi::detail::RowColumns<Row>) + sizeof(crysta::detail::AnchorList) + sizeof(edi::detail::Membership) +
        sizeof(edi::detail::TableNotes) + 7 * (sizeof(void*) + sizeof(std::uint64_t)) +
        Limits::stream_items * (numeric + indexes + pointers + strings + rows + ui);
}
// The original Add starts a real editable row with ordinary defaults, not a form.
inline edi::BackgroundPointInput background_append_input(const edi::ExperimentBase& experiment) {
    edi::BackgroundPointInput input;
    for (std::size_t ordinal = 1; input.id.empty(); ++ordinal) {
        if (ordinal == std::numeric_limits<std::size_t>::max()) throw std::length_error("Background identities are exhausted");
        const auto candidate = std::to_string(ordinal);
        if (std::none_of(experiment.background.begin(), experiment.background.end(), [&](const auto& point) { return point->id.value() == candidate; }))
            input.id = candidate;
    }
    if (!experiment.background.empty()) {
        input.position = experiment.background[experiment.background.size() - 1]->position.get();
        input.intensity = experiment.background[experiment.background.size() - 1]->intensity.value.get();
    }
    return input;
}
inline std::string background_text(const QString& text, bool native_bounded = true) {
    using Limits = edi::assistant::Limits;
    if (text.isEmpty() || (native_bounded && text.size() > static_cast<qsizetype>(Limits::id_bytes)))
        throw std::length_error("The background identity exceeds its admitted limit");
    quint64 bytes = 0;
    for (qsizetype i = 0; i < text.size();) {
        const QChar c = text.at(i);
        if (c.unicode() < 32 || c.unicode() == 127 || c.isLowSurrogate() ||
            (c.isHighSurrogate() && (i + 1 == text.size() || !text.at(i + 1).isLowSurrogate())))
            throw std::invalid_argument("A background identity requires valid text without controls");
        const qsizetype width = c.isHighSurrogate() ? 2 : 1;
        const auto part = text.mid(i, width).toUtf8();
        if (native_bounded && static_cast<quint64>(part.size()) > Limits::id_bytes - bytes)
            throw std::length_error("The background identity exceeds its admitted limit");
        bytes += static_cast<quint64>(part.size()); i += width;
    }
    return text.toUtf8().toStdString();
}
inline edi::BackgroundPointInput background_input(const QString& operation, const QString& id,
                                                 double position, double intensity, bool free, bool native_bounded = true) {
    edi::BackgroundPointInput value;
    if (operation == "add") value.action = edi::BackgroundPointInput::Action::Add;
    else if (operation == "update") value.action = edi::BackgroundPointInput::Action::Update;
    else if (operation == "remove") value.action = edi::BackgroundPointInput::Action::Remove;
    else throw std::invalid_argument("Unknown background operation");
    value.id = background_text(id, native_bounded); value.position = position; value.intensity = intensity; value.free = free;
    if (value.action != edi::BackgroundPointInput::Action::Remove && (!std::isfinite(position) || !std::isfinite(intensity)))
        throw std::invalid_argument("Background values must be finite");
    return value;
}
} // namespace edi_app
