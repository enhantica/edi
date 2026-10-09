// SPDX-License-Identifier: BSD-3-Clause
// edi Python bindings (ADR-0009): a THIN nanobind surface over the C++ product core — no product logic
// here. Exposes the user-facing model value types + Project.calculate() (results land in
// data.intensity_calc). Pythonic sugar lives in the pure-Python layer (edi/__init__.py).

#include <nanobind/nanobind.h>
#include <algorithm>
#include <iostream>
#include <nanobind/ndarray.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/map.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/shared_ptr.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/unique_ptr.h>
#include <nanobind/stl/variant.h>
#include <nanobind/stl/vector.h>
#include <type_traits>

#include <array>
#include <atomic>
#include <cmath>
#include <filesystem>
#include <numeric>
#include <variant>
#include <vector>

#include "edi/categories.hpp"
#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/parameter_spec.hpp"
#include "edi/report.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"
#include "edi/symmetry.hpp"
#include "edi/threading.hpp"
#include "edi/validation.hpp"
#include "edi/version.hpp"

#include <iomanip>
#include <sstream>
#include "collection_views.hpp"
#include "model_views_registry.hpp"

namespace nb = nanobind;
using namespace nb::literals;

// Metadata access on a bound Parameter. Fail-closed — a Parameter no model constructor attached
// a spec to has no metadata to report, and answering with a placeholder would hide exactly the
// defect the substrate gate exists to catch.
static const edi::ParameterSpec& require_spec(const edi::Parameter& parameter) {
    if (parameter.spec == nullptr) {
        throw std::runtime_error(
            "this Parameter carries no metadata spec: it was constructed bare rather than read "
            "from a model field (edi attaches specs to every model-owned parameter)");
    }
    return *parameter.spec;
}

// A computed column as a read-only NumPy array over crysta's own buffer. Zero-copy: the capsule
// co-owns the buffer, so the array outlives the model that held it, and a later calculation
// publishes a new buffer rather than changing this one.
template <typename T>
static nb::object readonly_array(const edi::ComputedColumn<T>& column) {
    using Buffer = typename edi::ComputedColumn<T>::Buffer;
    auto* owner = new Buffer(column.buffer() ? column.buffer()
                                             : std::make_shared<const std::vector<T>>());
    nb::capsule keeper(owner, [](void* held) noexcept { delete static_cast<Buffer*>(held); });
    const std::vector<T>& values = **owner;
    return nb::cast(
        nb::ndarray<nb::numpy, const T, nb::ndim<1>>(values.data(), {values.size()}, keeper));
}

// A computed text column — `calc_status`, `structure_id` — as `tuple[str, ...]` (ADR-0073 §2).
static nb::tuple text_tuple(const edi::ComputedColumn<std::string>& column) {
    nb::list out;
    for (const std::string& value : column) {
        out.append(value);
    }
    return nb::tuple(out);
}

// A structure's computed categories, read by column. A category object holds the geometry it was
// read from — the structure's stored unit as `current_geometry` returned it (so reading the
// property calculates through crysta when the unit is not current, and raises what crysta
// raises), or one result computed for a view window. Either way it never changes under its
// holder: a structure edit and a recalculation reach the next read of the property, not an
// object already held.
struct GeometryHandle {
    edi::Structure* structure = nullptr;
    std::shared_ptr<const edi::StructureGeometry> value;

    const edi::StructureGeometry& get() const { return *value; }
};
// The structure's stored unit, calculated when it is not current, as a held value. The copy shares
// crysta's immutable column buffers.
static std::shared_ptr<const edi::StructureGeometry> stored_geometry(edi::Structure& structure) {
    return std::make_shared<const edi::StructureGeometry>(structure.current_geometry());
}
struct SymopView : GeometryHandle {};
struct ExpandedAtomSitesView : GeometryHandle {};
struct GeomBondView : GeometryHandle {};
struct CartnTransformView : GeometryHandle {};
// One result of `Structure.geometry(view_range)`, kept with the structure it was computed from.
struct StructureGeometryView {
    edi::Structure* structure = nullptr;
    std::shared_ptr<const edi::WindowGeometry> value;

    // The result's categories, sharing its lifetime.
    std::shared_ptr<const edi::StructureGeometry> fixed() const {
        return {value, &value->geometry};
    }
};

// A positional id column: the 1-based row ordinals, as integers. The bond loop's two
// `expanded_atom_site_id` columns hold the same integers, so `id - 1` indexes the atom columns.
static nb::object ordinal_array(std::size_t size) {
    using Buffer = std::vector<std::int32_t>;
    auto* owner = new Buffer(size);
    std::iota(owner->begin(), owner->end(), std::int32_t{1});
    nb::capsule keeper(owner, [](void* held) noexcept { delete static_cast<Buffer*>(held); });
    return nb::cast(nb::ndarray<nb::numpy, const std::int32_t, nb::ndim<1>>(
        owner->data(), {owner->size()}, keeper));
}

// A `geom` value from Python: finite and >= 0, or None to unset it (crysta's default then
// applies).
static std::optional<double> geom_value(const std::optional<double>& value, const char* name) {
    if (value && (!std::isfinite(*value) || *value < 0.0)) {
        throw std::invalid_argument(std::string("geom.") + name + " must be finite and >= 0");
    }
    return value;
}

// A view window from Python: three (min, max) pairs, or None for the unit cell.
static edi::ViewWindow view_window(
    const std::optional<std::vector<std::vector<double>>>& range) {
    edi::ViewWindow window;
    if (!range) {
        return window;
    }
    if (range->size() != 3) {
        throw std::invalid_argument("view_range is three (min, max) pairs, one per axis");
    }
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if ((*range)[axis].size() != 2) {
            throw std::invalid_argument("view_range is three (min, max) pairs, one per axis");
        }
        window.min[axis] = (*range)[axis][0];
        window.max[axis] = (*range)[axis][1];
    }
    return window;
}

// A write to an input attribute of a model object is a write whatever value it leaves. It renews the
// identity the computed categories it feeds were calculated
// against (`renew`, a detail::Epoch), so exactly those categories go stale — another bank's are
// untouched — and a write to a non-input attribute renews nothing.
template <typename T, typename Renew>
static auto renewing_setattr(std::vector<std::string> non_inputs, Renew renew) {
    return [non_inputs = std::move(non_inputs), renew](nb::handle self, nb::str name,
                                                       nb::handle value) {
        if (PyObject_GenericSetAttr(self.ptr(), name.ptr(), value.ptr()) != 0) {
            throw nb::python_error();
        }
        if (std::find(non_inputs.begin(), non_inputs.end(), name.c_str()) == non_inputs.end()) {
            renew(nb::cast<T&>(self));
        }
    };
}
// The object's own identity renews.
static constexpr auto renew_epoch = [](auto& object) { object.epoch = edi::detail::Epoch(); };
// A view's category's identity renews.
static constexpr auto renew_storage = [](auto& view) { view.storage().epoch = edi::detail::Epoch(); };
// A peak view renews the experiment's peak even when it presents an earlier profile, so its type can
// still be switched back.
static constexpr auto renew_peak = [](edi::views::PeakNode& view) {
    view.experiment->peak.epoch = edi::detail::Epoch();
};

static nb::tuple names_tuple(std::span<const char* const> names) {
    nb::list out;
    for (const char* name : names) {
        out.append(nb::str(name));
    }
    return nb::tuple(out);
}

// The Python attribute boundary is one of the three declared validation stages — a value
// outside its spec's admissible range refuses (ValueError) instead of landing.
static void check_range(const edi::ParameterSpec* spec, double value, const char* where) {
    if (spec != nullptr && (value < spec->range.min || value > spec->range.max)) {
        throw std::invalid_argument(std::string(where) + " value " + std::to_string(value) +
                                    " is outside the declared admissible range [" +
                                    std::to_string(spec->range.min) + ", " +
                                    std::to_string(spec->range.max) + "]");
    }
}

// A Parameter slot takes a whole Parameter OR a bare number. The numeric spelling is
// upstream's setter semantics at 0ffba46f (`self._length_a.value = value`): it updates the
// VALUE of the parameter already in live storage, leaving uncertainty, free and spec
// untouched. The whole-Parameter spelling keeps the copy-with-spec-preservation semantics. ONE
// dispatch serves every Parameter-slot helper (required/optional × plain/view), so no route
// can accept a number on one slot and refuse it on another.
using ParameterOrNumber = std::variant<edi::Parameter, double>;

// ADR-0012: a removed row keeps its last values and refuses writes through its handles, as
// crysta's detached handles do. A row no collection ever held — a freshly built item, a bare
// Parameter — is not detached and stays writable.
static void refuse_detached(bool detached, const char* name) {
    if (detached) {
        throw std::logic_error(std::string("parameter '") + name +
                               "': its row was removed, so it is detached and refuses writes "
                               "(edi ADR-0012 §1)");
    }
}
static void refuse_detached(const edi::Parameter& parameter) {
    refuse_detached(parameter.is_detached(),
                    parameter.spec != nullptr ? parameter.spec->name : "value");
}

static void assign_parameter_slot(edi::Parameter& field, const ParameterOrNumber& incoming,
                                  const char* name) {
    if (const edi::Parameter* parameter = std::get_if<edi::Parameter>(&incoming)) {
        const edi::ParameterSpec* keep = field.spec;
        check_range(keep, parameter->value, name);
        field = *parameter;
        field.spec = keep;
        return;
    }
    const double value = std::get<double>(incoming);
    check_range(field.spec, value, name);
    field.value = value;
}

// The optional twin: None disengages (unchanged); a number on an ENGAGED field updates its value
// in place, on an absent field engages it with the slot's spec (the same engagement act as the
// whole-Parameter path — a programmatically engaged parameter is never spec-less).
static void assign_optional_parameter_slot(edi::OptionalParameter& field,
                                           std::optional<ParameterOrNumber> incoming,
                                           const edi::ParameterSpec& spec, const char* name) {
    if (!incoming) {
        field = std::nullopt;
        return;
    }
    if (edi::Parameter* parameter = std::get_if<edi::Parameter>(&*incoming)) {
        check_range(&spec, parameter->value, name);
        parameter->spec = &spec;
        field = std::move(*parameter);
        return;
    }
    const double value = std::get<double>(*incoming);
    check_range(&spec, value, name);
    if (field) {
        field->value = value;
    } else {
        edi::Parameter engaged(value);
        engaged.spec = &spec;
        field = engaged;
    }
}

// Bind a Parameter-typed model field. The getter returns a REFERENCE into the owning object
// (nested writes reach C++ storage — the S13 write-through convention); the setter dispatches
// per above, range-checked per I6.
template <typename Class>
static void def_parameter_field(nb::class_<Class>& cls, const char* name,
                                edi::Parameter Class::* member) {
    cls.def_prop_rw(
        name,
        [member](Class& self) -> edi::Parameter& {
            (self.*member).category.point_at(self.row);  // X12: the handle's row
            return self.*member;
        },
        [member, name](Class& self, const ParameterOrNumber& incoming) {
            refuse_detached(self.row.detached(), name);
            assign_parameter_slot(self.*member, incoming, name);
        },
        nb::rv_policy::reference_internal);
}

// Bind a presence-tracked optional Parameter field. The getter keeps the established copy
// semantics (None when absent); the setter attaches the field's spec on engagement, so a
// programmatically engaged CW/absorption parameter is never spec-less.
template <typename Class>
static void def_optional_parameter_field(nb::class_<Class>& cls, const char* name,
                                         edi::OptionalParameter Class::* member,
                                         const edi::ParameterSpec& spec) {
    cls.def_prop_rw(
        name,
        // A REFERENCE into the engaged Parameter (None when absent), so nested writes reach the
        // C++ storage — the same S13 write-through convention as the required fields.
        [member](Class& self) -> edi::Parameter* {
            edi::OptionalParameter& field = self.*member;
            if (!field) {
                return nullptr;
            }
            field->category.point_at(self.row);  // X12: the handle's row
            return &*field;
        },
        [member, &spec, name](Class& self, std::optional<ParameterOrNumber> incoming) {
            refuse_detached(self.row.detached(), name);
            assign_optional_parameter_slot(self.*member, std::move(incoming), spec, name);
        },
        nb::rv_policy::reference_internal);
}

// The view-projection twins of the two field helpers above: a concrete family class is a typed lens over
// the experiment's category storage, so its members project through `View::storage()` with the SAME
// spec-preserving write-through and range-check semantics.
template <typename View, typename Storage, typename... Extra>
static void def_view_parameter_field(nb::class_<View, Extra...>& cls, const char* name,
                                     edi::Parameter Storage::* member) {
    cls.def_prop_rw(
        name,
        [member](View& self) -> edi::Parameter& {
            (self.storage().*member).category.point_at(self.storage().row);  // X12
            return self.storage().*member;
        },
        [member, name](View& self, const ParameterOrNumber& incoming) {
            refuse_detached(self.storage().row.detached(), name);
            assign_parameter_slot(self.storage().*member, incoming, name);
        },
        nb::rv_policy::reference_internal);
}

template <typename View, typename Storage, typename... Extra>
static void def_view_optional_parameter_field(nb::class_<View, Extra...>& cls, const char* name,
                                              edi::OptionalParameter Storage::* member,
                                              const edi::ParameterSpec& spec) {
    cls.def_prop_rw(
        name,
        [member](View& self) -> edi::Parameter* {
            edi::OptionalParameter& field = self.storage().*member;
            if (!field) {
                return nullptr;
            }
            field->category.point_at(self.storage().row);  // X12: the handle's row
            return &*field;
        },
        [member, &spec, name](View& self, std::optional<ParameterOrNumber> incoming) {
            refuse_detached(self.storage().row.detached(), name);
            assign_optional_parameter_slot(self.storage().*member, std::move(incoming), spec,
                                           name);
        },
        nb::rv_policy::reference_internal);
}

// The Python progress-callback boundary.
//
// The hazard this is shaped around: a `nb::callable` is a Python-owned reference. COPYING one is a
// Py_INCREF and DESTROYING one is a Py_DECREF, and both are undefined unless the GIL is held. A
// refinement runs for many seconds, so the GIL must be released across it — which means the owning
// object cannot simply be captured into the callback and carried into the GIL-free region, and
// re-acquiring the GIL inside the per-iteration call does NOT retroactively protect the copies and
// destructions that happen around it. That was a real defect here, not a theoretical one.
//
// THE BOUNDARY, stated once:
//
//   1. Python ownership lives in EXACTLY ONE `std::shared_ptr<nb::callable>`, created while the GIL
//      is HELD (see `fit_with_callback`, which does not use nb::call_guard for this reason).
//   2. Every C++ copy of the callback copies only that shared_ptr — an atomic refcount, never a
//      Python one. So the engine and the adapter may copy the std::function as freely as they like
//      inside the GIL-free region; none of those copies touches CPython.
//   3. The binding holds its own shared_ptr for the whole call, so the count cannot reach zero
//      inside the fit. The `nb::callable` is destroyed when that anchor dies — at the end of the
//      binding body, with the GIL restored.
//   4. The GIL is released ONLY around the pure-C++ refinement, and re-acquired by the trampoline
//      solely to make the Python call itself.
//
// With no subscriber this yields an EMPTY std::function, so the engine's `if (on_iteration)` guard
// means there is no trampoline and no host crossing at all — that is what "zero overhead when
// absent" means, and it is assertable by call count rather than by wall clock. The internal history
// collector runs either way (see FitResultBase::iterations_history).
//
// ONE fit's cancel state, shared by every trampoline of the call and by its cancel predicate. A
// KeyboardInterrupt raised inside ANY edi callback — on_iteration, on_start, on_scan_start,
// on_file_complete or should_cancel itself, including the one Python's default SIGINT handler
// raises while such a callback runs — is not an error unwinding through C++: it is recorded here
// and becomes a cancel at the fit's next poll, so the fit returns CANCELLED with its committed
// state intact (a scan's results.csv prefix is the resume point). Any other Python exception
// propagates exactly as before. Sticky: once requested, every later poll answers true.
struct CancelState {
    std::atomic<bool> requested{false};
};

// Make one host call under the GIL, turning a KeyboardInterrupt into a cancel request.
template <typename Call>
static void call_host(CancelState& cancel, Call&& call) {
    nb::gil_scoped_acquire acquire;
    try {
        call();
    } catch (nb::python_error& error) {
        if (!error.matches(PyExc_KeyboardInterrupt)) {
            throw;
        }
        cancel.requested = true;  // `error` releases the exception here, GIL still held
    }
}

static edi::IterationCallback iteration_trampoline(std::shared_ptr<nb::callable> anchor,
                                                   std::shared_ptr<CancelState> cancel) {
    if (!anchor) {
        return {};
    }
    // Captures the shared_ptr, NOT the nb::callable: copying this lambda is refcount-only.
    return [anchor = std::move(anchor),
            cancel = std::move(cancel)](const edi::IterationRecord& record) {
        call_host(*cancel, [&] { (*anchor)(record); });
    };
}

// The predicate the engine polls between iterations. Always present, so a pending SIGINT
// reaches a fit that has no Python callback at all: PyErr_CheckSignals runs the interpreter's
// handler here (the default one raises KeyboardInterrupt, which becomes the cancel); a CLI that
// installed its own handler sees it run here too. Then the caller's
// `should_cancel`, by Python truthiness. One GIL acquisition per iteration, never per point.
static edi::CancelCallback cancel_trampoline(std::shared_ptr<nb::callable> predicate,
                                             std::shared_ptr<CancelState> cancel) {
    return [predicate = std::move(predicate), cancel = std::move(cancel)]() -> bool {
        if (cancel->requested) {
            return true;
        }
        call_host(*cancel, [&] {
            if (PyErr_CheckSignals() != 0) {
                throw nb::python_error();
            }
            if (predicate) {
                const nb::object answer = (*predicate)();
                const int truthy = PyObject_IsTrue(answer.ptr());
                if (truthy < 0) {
                    throw nb::python_error();
                }
                if (truthy != 0) {
                    cancel->requested = true;
                }
            }
        });
        return cancel->requested;
    };
}

// Create the single Python-owning anchor. MUST be called with the GIL held.
static std::shared_ptr<nb::callable> make_callback_anchor(
    const std::optional<nb::callable>& on_iteration) {
    if (!on_iteration.has_value() || on_iteration->is_none()) {
        return nullptr;
    }
    return std::make_shared<nb::callable>(*on_iteration);  // the one Py_INCREF, under the GIL
}

// Run one refinement with the boundary above. `run` receives the engine-facing callback and performs
// the fit; it is invoked with the GIL RELEASED. Deliberately not a nb::call_guard binding: the guard
// would already have released the GIL before this function's body could build the anchor.
template <typename Run>
static edi::LeastSquaresFitResult fit_with_callback(const std::optional<nb::callable>& on_iteration,
                                            Run&& run) {
    // GIL held here.
    std::shared_ptr<nb::callable> anchor = make_callback_anchor(on_iteration);
    edi::IterationCallback callback =
        iteration_trampoline(anchor, std::make_shared<CancelState>());
    edi::FitResultBase outcome;
    {
        nb::gil_scoped_release release;
        outcome = run(callback);
    }
    // GIL restored. `callback` and `anchor` die below, so the single Py_DECREF happens here. The
    // least-squares leaf, as the callback-pair helper returns.
    return edi::LeastSquaresFitResult(std::move(outcome));
}

// The one-shot preamble trampoline — the exact analog of iteration_trampoline. Captures the
// shared_ptr (NOT the nb::callable), so copying this lambda is refcount-only; the GIL is re-acquired
// only to make the single Python call. Empty when the anchor is absent (no host crossing).
static edi::PreambleCallback preamble_trampoline(std::shared_ptr<nb::callable> anchor,
                                                 std::shared_ptr<CancelState> cancel) {
    if (!anchor) {
        return {};
    }
    return [anchor = std::move(anchor),
            cancel = std::move(cancel)](const edi::FitPreamble& preamble) {
        call_host(*cancel, [&] { (*anchor)(preamble); });
    };
}

// The two-anchor generalisation of fit_with_callback for the streaming surface. BOTH Python anchors
// are created while the GIL is held and destroyed at the end of this body with the GIL
// restored (points 1 + 3 of the boundary above); both trampolines are refcount-only copyable, so the
// fit runs GIL-released while either callback may re-enter Python. `run` receives (iteration, start)
// callbacks; an absent callback yields an EMPTY std::function, so an unsubscribed hook crosses no host
// boundary at all. Plus the cancel predicate (cancel_trampoline) every fit now carries.
template <typename Run>
static edi::LeastSquaresFitResult fit_with_callbacks(const std::optional<nb::callable>& on_iteration,
                                             const std::optional<nb::callable>& on_start,
                                             const std::optional<nb::callable>& should_cancel,
                                             Run&& run) {
    // GIL held here — the only place a Python ref is created or destroyed.
    std::shared_ptr<nb::callable> it_anchor = make_callback_anchor(on_iteration);
    std::shared_ptr<nb::callable> st_anchor = make_callback_anchor(on_start);
    std::shared_ptr<nb::callable> cn_anchor = make_callback_anchor(should_cancel);
    auto cancel = std::make_shared<CancelState>();
    edi::IterationCallback it = iteration_trampoline(it_anchor, cancel);
    edi::PreambleCallback st = preamble_trampoline(st_anchor, cancel);
    edi::CancelCallback cn = cancel_trampoline(cn_anchor, cancel);
    edi::FitResultBase outcome;
    {
        nb::gil_scoped_release release;
        outcome = run(it, st, cn);
    }
    // GIL restored. `it`/`st` and both anchors die below → the paired Py_DECREFs happen here. The
    // least-squares leaf: edi's one minimizer path, typed as such.
    return edi::LeastSquaresFitResult(std::move(outcome));
}

// The scan-event trampolines — exact analogs of preamble_trampoline for the whole-scan preamble
// and the per-file completion event. Refcount-only copyable; the GIL is re-acquired only to
// make the Python call; empty when the anchor is absent (no host crossing).
static edi::ScanStartCallback scan_start_trampoline(std::shared_ptr<nb::callable> anchor,
                                                    std::shared_ptr<CancelState> cancel) {
    if (!anchor) {
        return {};
    }
    return [anchor = std::move(anchor),
            cancel = std::move(cancel)](const edi::ScanPreamble& preamble) {
        call_host(*cancel, [&] { (*anchor)(preamble); });
    };
}

static edi::FileCompleteCallback file_complete_trampoline(std::shared_ptr<nb::callable> anchor,
                                                          std::shared_ptr<CancelState> cancel) {
    if (!anchor) {
        return {};
    }
    return [anchor = std::move(anchor),
            cancel = std::move(cancel)](const edi::ScanFileRecord& record) {
        call_host(*cancel, [&] { (*anchor)(record); });
    };
}

// The four-anchor generalisation of fit_with_callbacks for the scan entries. All four Python
// anchors are created with the GIL held and destroyed at the end of this body with the GIL
// restored; every trampoline is refcount-only copyable, so the scan runs GIL-released while any
// callback may re-enter Python. An absent callback yields an EMPTY std::function — an
// unsubscribed event crosses no host boundary (and, for on_file_complete, skips the CSV probe
// in the adapter entirely).
template <typename Run>
static edi::LeastSquaresFitResult fit_with_scan_callbacks(
    const std::optional<nb::callable>& on_iteration, const std::optional<nb::callable>& on_start,
    const std::optional<nb::callable>& on_scan_start,
    const std::optional<nb::callable>& on_file_complete,
    const std::optional<nb::callable>& should_cancel, Run&& run) {
    // GIL held here — the only place a Python ref is created or destroyed.
    std::shared_ptr<nb::callable> it_anchor = make_callback_anchor(on_iteration);
    std::shared_ptr<nb::callable> st_anchor = make_callback_anchor(on_start);
    std::shared_ptr<nb::callable> sc_anchor = make_callback_anchor(on_scan_start);
    std::shared_ptr<nb::callable> fc_anchor = make_callback_anchor(on_file_complete);
    std::shared_ptr<nb::callable> cn_anchor = make_callback_anchor(should_cancel);
    auto cancel = std::make_shared<CancelState>();
    edi::IterationCallback it = iteration_trampoline(it_anchor, cancel);
    edi::PreambleCallback st = preamble_trampoline(st_anchor, cancel);
    edi::ScanStartCallback sc = scan_start_trampoline(sc_anchor, cancel);
    edi::FileCompleteCallback fc = file_complete_trampoline(fc_anchor, cancel);
    edi::CancelCallback cn = cancel_trampoline(cn_anchor, cancel);
    edi::FitResultBase outcome;
    {
        nb::gil_scoped_release release;
        outcome = run(it, st, sc, fc, cn);
    }
    // GIL restored. The trampolines and all four anchors die below → the paired Py_DECREFs
    // happen here. The least-squares leaf.
    return edi::LeastSquaresFitResult(std::move(outcome));
}

// `parameters` / `free_parameters` on every node — diffraction-lib's spelling (R18). References
// into the owning node (reference_internal), so
// `for p in cell.parameters: p.free = True` writes through, and the node outlives every element.
// R18 on a category block that carries no free subset of its own (D46 bounds `free_parameters`
// to the six engine nodes): `parameters` only.
template <typename Class>
static void def_parameters(nb::class_<Class>& cls) {
    cls.def_prop_ro(
        "parameters",
        [](Class& self) {
            // X12: each handle's row — through the lens for a view, else the block itself.
            if constexpr (requires { self.storage(); }) {
                edi::detail::point_parameters(self.storage());
            } else {
                edi::detail::point_parameters(self);
            }
            return self.parameters();
        },
        nb::rv_policy::reference_internal, "The block's parameters in field order (references).");
}

template <typename Class>
static void def_parameter_walks(nb::class_<Class>& cls) {
    cls.def_prop_ro(
        "parameters",
        [](Class& self) {
            edi::detail::point_parameters(self);  // X12: each handle's row
            return self.parameters();
        },
        nb::rv_policy::reference_internal,
        "The node's parameters, own fields then children, in field order (references).");
}

// `free_parameters` lives where diffraction-lib carries it - on the project (owner ruling
// keep-on-strong-justification: the per-node subset had no consumer and no counterpart).
template <typename Class>
static void def_free_parameters(nb::class_<Class>& cls) {
    cls.def_prop_ro(
        "free_parameters",
        [](Class& self) {
            edi::detail::point_parameters(self);  // X12: each handle's row
            return self.free_parameters();
        },
        nb::rv_policy::reference_internal, "The subset of `parameters` whose `free` is set.");
}

// The Python edi.IoError type (subclass of ValueError), kept alive for the exception translator so a
// fail-closed C++ IoError surfaces as a structured Python error carrying a `.diagnostics` mapping.
static nb::object* g_io_error_type = nullptr;

// The validation taxonomy. `ValidationError` is-a `IoError` (so is-a `ValueError`); the three tier
// subclasses are selected by the C++ error's tier. Kept alive as module attributes; the translator
// is registered AFTER IoError's so it runs first.
struct ValidationErrorTypes {
    nb::object base;
    nb::object syntax;
    nb::object schema;
    nb::object domain;
};
static ValidationErrorTypes* g_validation_types = nullptr;

// The Python-side family registries: one dict per factory, seeded with the implemented concretes (None
// marks a reserved row); the category getters construct through these, so a Python-registered class is
// served like a built-in one.
static nb::object* g_peak_registry = nullptr;
static nb::object* g_instrument_registry = nullptr;
static nb::object* g_absorption_registry = nullptr;

static std::string derive_registration_token(const nb::object& cls) {
    for (const char* attr : {"tag", "token", "type_token"}) {
        if (nb::hasattr(cls, attr)) {
            nb::object value = nb::getattr(cls, attr);
            if (nb::isinstance<nb::str>(value)) {
                return nb::cast<std::string>(value);
            }
        }
    }
    // Fall back to the kebab-cased class name — the token grammar's own convention.
    const std::string name = nb::cast<std::string>(nb::getattr(cls, "__name__"));
    std::string token;
    for (std::size_t i = 0; i < name.size(); ++i) {
        const char c = name[i];
        if (c >= 'A' && c <= 'Z') {
            if (i != 0) {
                token.push_back('-');
            }
            token.push_back(static_cast<char>(c - 'A' + 'a'));
        } else {
            token.push_back(c);
        }
    }
    return token;
}

static nb::object registry_lookup(const nb::object& registry, const std::string& token) {
    // Typed dict access, not a stringly attribute dispatch on the removed leaf spelling (r113:
    // the source scanner fails closed on an owner-unresolved literal lookup — and the registry
    // IS a dict, so say so with the typed API).
    const nb::dict rows = nb::cast<nb::dict>(registry);
    if (!rows.contains(token.c_str())) {
        throw std::invalid_argument("'" + token +
                                    "' has no registered concrete class (reserved or unknown)");
    }
    nb::object cls = nb::cast<nb::object>(rows[token.c_str()]);
    if (cls.is_none()) {
        throw std::invalid_argument("'" + token +
                                    "' has no registered concrete class (reserved or unknown)");
    }
    return cls;
}

static nb::object* g_bragg_experiment_cls = nullptr;

static nb::list active_tags(const nb::object& registry) {
    std::vector<std::string> tags;
    for (auto item : nb::cast<nb::dict>(registry)) {
        if (!nb::borrow(item.second).is_none()) {
            tags.push_back(nb::cast<std::string>(nb::str(item.first)));
        }
    }
    std::sort(tags.begin(), tags.end());
    nb::list out;
    for (const std::string& tag : tags) {
        out.append(nb::str(tag.c_str()));
    }
    return out;
}

static nb::object factory_create(const nb::object& registry, const std::string& tag,
                                 nb::object experiment) {
    nb::object cls = registry_lookup(registry, tag);
    if (experiment.is_none()) {
        experiment = (*g_bragg_experiment_cls)();
    }
    return cls(experiment);
}

static nb::dict copy_registry(const nb::object& registry) {
    nb::dict out;
    for (auto item : nb::cast<nb::dict>(registry)) {
        out[item.first] = item.second;
    }
    return out;
}

// The STAR timestamp ('%d %b %Y %H:%M:%S', UTC) as a UTC-aware python datetime — the
// counterpart value semantics (the storage string must not leak). The persisted snapshot
// must BE the state a caller observes after a successful save — `last_modified` advances
// BEFORE the write, so the record carries the advanced value, and a FAILED publication
// rolls it back, so failure mutates nothing. One helper for all three save routes; the
// closed class was "serialize, then mutate what the snapshot claimed to have serialized",
// which left disk one successful save behind forever.
static void save_project_advancing_last_modified(edi::Project& self,
                                                 const std::string& directory) {
    const std::string previous = self.metadata.last_modified;
    self.metadata.update_last_modified();
    try {
        edi::save_project(self, directory);
    } catch (...) {
        self.metadata.last_modified = previous;
        throw;
    }
}

static nb::object star_datetime(const std::string& stored) {
    std::tm tm{};
    std::istringstream stream(stored);
    stream >> std::get_time(&tm, "%d %b %Y %H:%M:%S");
    if (stream.fail()) {
        throw std::invalid_argument("unparseable STAR timestamp '" + stored + "'");
    }
    const nb::object datetime = nb::module_::import_("datetime");
    return datetime.attr("datetime")(tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour,
                                     tm.tm_min, tm.tm_sec, 0,
                                     datetime.attr("timezone").attr("utc"));
}

static std::string peak_token_of(const edi::ExperimentBase& experiment) {
    return edi::effective_peak_type(experiment);
}

// One validation rule for the project name, whichever spelling sets it: a name lands in
// filesystem paths at save, so a path separator refuses at the boundary.
static const std::string& validated_project_name(const std::string& value) {
    if (value.find('/') != std::string::npos || value.find('\\') != std::string::npos) {
        throw std::invalid_argument("project name '" + value +
                                    "' must not contain a path separator ('/' or '\\')");
    }
    return value;
}


// --- the declared relations (edi ADR-0024) --------------------------------------------------------

// crysta's coded warnings, as Python warnings led by the code.
static void warn_python(const std::string& message) {
    if (PyErr_WarnEx(PyExc_UserWarning, message.c_str(), 1) < 0) {
        throw nb::python_error();
    }
}

// The project a relation row belongs to, once that project handed its collection out; else null.
static edi::Project* host_of(const edi::ItemKey& key) {
    const edi::detail::KeyedBase* owner = key.owner();
    return owner != nullptr ? owner->host() : nullptr;
}

// Before a calculation or fit: crysta re-marks every parameter and clears a dependent's stale free flag
// with its warning, as crysta's own entry points do. A set that cannot hold is refused by the call itself.
static void warn_dependents(edi::Project& project) {
    try {
        edi::refresh_relations(project, warn_python);
    } catch (const edi::ValidationError&) {  // NOLINT(bugprone-empty-catch) — refused at use
    }
}

// After an edit of the relations: it is an edit of the project, so the computed categories go stale
// and the next read or calculation applies the new relations; crysta re-marks every parameter and
// clears a newly dependent free flag with its warning. No parameter value is written here. A set that
// cannot hold yet stays as declared; the next calculation, fit or save refuses it with crysta's code.
static void relations_changed(edi::Project& project) {
    project.note_edit();
    warn_dependents(project);
}

// The project a parameter handle belongs to, through the row it is attached to (X12); null for one no
// project holds. The row's collection names the project that adopted it, which may have been destroyed
// (the link then reads none) or may no longer hold the row (removed, replaced or moved to another
// project), so the project must still hold this very parameter.
static edi::Project* project_of(const edi::Parameter& parameter) {
    const edi::detail::RowLink* link = parameter.category.get();
    const edi::detail::Membership* record = link != nullptr ? link->record() : nullptr;
    edi::Project* project =
        record != nullptr && record->owner != nullptr ? record->owner->host() : nullptr;
    if (project == nullptr) {
        return nullptr;
    }
    for (const edi::NamedSlot& slot : edi::named_slots(*project)) {
        if (slot.parameter == &parameter) {
            return project;
        }
    }
    return nullptr;
}

// A parameter's dependence as it is now. An edit that reaches no project (a space-group change) can
// leave the marks behind, so the project's relations are refreshed first. A parameter no live project
// holds (removed, moved, or its project destroyed) is set by no relation: the mark a former project
// left is cleared, so its readers and its free flag agree.
static edi::Dependence dependence_now(edi::Parameter& parameter) {
    edi::Project* project = project_of(parameter);
    if (project == nullptr) {
        parameter.dependence = edi::Dependence::Independent;
        return edi::Dependence::Independent;
    }
    warn_dependents(*project);
    return parameter.dependence;
}

// The Python object that owns a parameter's storage: its keyed row (a site, a background point or term,
// a texture row, a linked structure) or, for a block field, its structure or experiment. None when the project holds none.
// The structure whose sites hold `site`, in a project or not; null for a site no structure holds.
static edi::Structure* holding_structure(edi::AtomSite& site) {
    const edi::detail::Membership* record = site.row.record();
    return record != nullptr && record->owner != nullptr ? record->owner->holder() : nullptr;
}

static nb::object owner_of(edi::Project& project, const edi::Parameter* parameter) {
    const auto holds = [parameter](auto& node) {
        for (const edi::Parameter* held : node.parameters()) {
            if (held == parameter) {
                return true;
            }
        }
        return false;
    };
    for (const std::shared_ptr<edi::Structure>& structure : project.structures) {
        for (const std::shared_ptr<edi::AtomSite>& site : structure->atom_sites) {
            if (holds(*site)) {
                return nb::cast(site);
            }
        }
        for (const std::shared_ptr<edi::AtomSiteAniso>& tensor : structure->atom_site_aniso) {
            if (holds(*tensor)) {
                return nb::cast(tensor);
            }
        }
        if (holds(structure->cell)) {
            return nb::cast(structure);
        }
    }
    for (const std::shared_ptr<edi::BraggPdExperiment>& experiment : project.experiments) {
        for (const std::shared_ptr<edi::PrefOrient>& row : experiment->preferred_orientation) {
            if (holds(*row)) {
                return nb::cast(row);
            }
        }
        for (const std::shared_ptr<edi::LinkedStructure>& link : experiment->linked_structures) {
            if (holds(*link)) {
                return nb::cast(link);
            }
        }
        for (const std::shared_ptr<edi::LineSegment>& point : experiment->background) {
            if (holds(*point)) {
                return nb::cast(point);
            }
        }
        for (const std::shared_ptr<edi::PolynomialTerm>& term : experiment->background_terms) {
            if (holds(*term)) {
                return nb::cast(term);
            }
        }
        if (holds(experiment->peak) || holds(experiment->instrument) || holds(experiment->absorption)) {
            return nb::cast(experiment);
        }
    }
    return nb::none();
}

static void relations_changed(const edi::ItemKey& key) {
    if (edi::Project* project = host_of(key)) {
        relations_changed(*project);
    }
}

namespace edi::views {
void after_change(const AliasesView& view) { relations_changed(*view.owner); }
void after_change(const ConstraintsView& view) { relations_changed(*view.owner); }
// A site added, removed or replaced: the tensor rows follow the sites' types.
void after_change(const AtomSitesView& view) { sync_atom_site_aniso(*view.owner); }
void after_change(const AtomSiteAnisoView& view) { sync_atom_site_aniso(*view.owner); }
}  // namespace edi::views

// The text either side of a constraint's first '=' (diffraction-lib Constraint._split_expression).
static std::pair<std::string, std::string> split_constraint(const std::string& text) {
    const auto trim = [](std::string value) {
        value.erase(0, value.find_first_not_of(" \t"));
        value.erase(value.find_last_not_of(" \t") + 1);
        return value;
    };
    const std::size_t equals = text.find('=');
    if (equals == std::string::npos) {
        return {trim(text), std::string()};
    }
    return {trim(text.substr(0, equals)), trim(text.substr(equals + 1))};
}

// ---: the R15 collection protocol ---------------------------------------
//
// One registrar per keyed view + its lazy query iterator. Verb semantics are the accepted plan's
// per-verb conformance table, read from upstream `R15` @0ffba46f: string lookup resolves the LAST
// duplicate, `add`-replacement and `remove` the FIRST; `[]` takes str (KeyError) or int
// (IndexError, negatives from the end), anything else TypeError in upstream's spelling; iteration
// yields ITEMS in insertion order; `keys`/`values`/`items` are lazy iterators over live storage
// (no list mutator exists to spell); `names` is the anchor's LIST — a fresh projected snapshot of
// immutable keys per read, so mutating it never reaches storage; mutation verbs return None.
// Lifetime: every borrowed object keeps its immediate lender's wrapper alive via keep_alive<0,1>;
// items ride shared_ptr.

template <typename View, typename Iter, typename ItemT>
static void def_keyed_collection(nb::class_<View>& view_cls, nb::class_<Iter>& iter_cls) {
    iter_cls
        .def(
            "__iter__", [](Iter& self) -> Iter& { return self; }, nb::rv_policy::none)
        .def("__next__", [](Iter& self) -> nb::object {
            const edi::ItemVec<ItemT>& items = self.view.vec();
            if (self.index >= items.size()) {
                throw nb::stop_iteration();
            }
            const std::size_t i = self.index++;
            switch (self.mode) {
                case edi::views::IterMode::Keys: return nb::cast(self.view.key_of(*items[i]));
                case edi::views::IterMode::Values: return nb::cast(items[i]);
                case edi::views::IterMode::Items:
                    return nb::make_tuple(self.view.key_of(*items[i]), items[i]);
            }
            throw nb::stop_iteration();
        });
    view_cls
        .def("__len__", [](const View& self) { return self.vec().size(); })
        .def(
            "__iter__",
            [](const View& self) { return Iter{self, edi::views::IterMode::Values}; },
            nb::keep_alive<0, 1>())
        .def("__contains__",
             [](const View& self, nb::object key) {
                 if (nb::isinstance<nb::str>(key)) {
                     return self.find_last(nb::cast<std::string>(key)) >= 0;
                 }
                 // Anchor semantics (plan seam row 13): ordinary dict membership — a hashable
                 // non-str probe is absent (False), an unhashable one raises TypeError.
                 if (PyObject_Hash(key.ptr()) == -1) {
                     throw nb::python_error();
                 }
                 return false;
             })
        .def("__getitem__",
             [](const View& self, nb::object key) -> nb::object {
                 if (nb::isinstance<nb::int_>(key)) {
                     std::ptrdiff_t i = nb::cast<std::ptrdiff_t>(key);
                     const std::ptrdiff_t n = static_cast<std::ptrdiff_t>(self.vec().size());
                     if (i < 0) i += n;
                     if (i < 0 || i >= n) {
                         throw nb::index_error("collection index out of range");
                     }
                     return nb::cast(self.vec()[static_cast<std::size_t>(i)]);
                 }
                 if (nb::isinstance<nb::str>(key)) {
                     const std::string name = nb::cast<std::string>(key);
                     const std::ptrdiff_t at = self.find_last(name);
                     if (at < 0) {
                         throw nb::key_error(name.c_str());
                     }
                     return nb::cast(self.vec()[static_cast<std::size_t>(at)]);
                 }
                 const std::string msg =
                     "Collection indices must be str or int, not " +
                     nb::cast<std::string>(key.type().attr("__name__"));
                 throw nb::type_error(msg.c_str());
             })
        .def("__delitem__",
             [](View& self, const std::string& name) {
                 const std::ptrdiff_t at = self.find_first(name);
                 if (at < 0) {
                     throw nb::key_error(name.c_str());
                 }
                 self.vec().erase_at(static_cast<std::size_t>(at));
                 after_change(self);
             })
        .def(
            "add",
            [](View& self, std::shared_ptr<ItemT> item) {
                const std::string name = self.key_of(*item);
                self.set_item(name, std::move(item));
                after_change(self);
            },
            "item"_a,
            "Insert or replace a pre-built item under its identity key (R15: replace acts on the "
            "first match, in place; the passed object itself is stored).")
        .def(
            "remove",
            [](View& self, const std::string& name) {
                const std::ptrdiff_t at = self.find_first(name);
                if (at < 0) {
                    throw nb::key_error(name.c_str());
                }
                if constexpr (std::is_same_v<View, edi::views::StructuresView>) {
                    // A structure an experiment links stays: removing it would leave the link naming
                    // nothing. Remove the link first.
                    for (const auto& experiment : self.owner->experiments) {
                        for (const auto& link : experiment->linked_structures) {
                            if (link->structure_id.value() == name) {
                                throw std::invalid_argument("structure '" + name + "' is linked by experiment '" +
                                                            experiment->name + "'; remove that link first");
                            }
                        }
                    }
                }
                self.vec().erase_at(static_cast<std::size_t>(at));
                after_change(self);
            },
            "name"_a,
            "Remove an item by its key (R15: KeyError when absent; a held item survives, "
            "detached).")
        .def(
            "clear",
            [](View& self) {
                self.vec().clear();
                after_change(self);
            },
            "Remove every item (R15; held items survive, detached).")
        // ADR-0016: the "these are the items" bulk path (StructureFactory.from_dict): the whole list
        // is admitted at once, so an internal duplicate id is refused by name rather than silently
        // collapsed by add()'s upsert. Private — no public surface change.
        .def(
            "_assign",
            [](View& self, std::vector<std::shared_ptr<ItemT>> items) {
                for (const std::shared_ptr<ItemT>& item : items) {
                    if (!item) {
                        throw nb::type_error("_assign: an item is None");
                    }
                    validate_insert(self, *item);
                }
                self.vec().assign(std::move(items));
                after_change(self);
            },
            "items"_a)
        .def(
            "keys", [](const View& self) { return Iter{self, edi::views::IterMode::Keys}; },
            nb::keep_alive<0, 1>(), "Lazily yield keys in insertion order (R15).")
        .def(
            "values", [](const View& self) { return Iter{self, edi::views::IterMode::Values}; },
            nb::keep_alive<0, 1>(), "Lazily yield items in insertion order (R15).")
        .def(
            "items", [](const View& self) { return Iter{self, edi::views::IterMode::Items}; },
            nb::keep_alive<0, 1>(), "Lazily yield (key, item) pairs in insertion order (R15).")
        .def_prop_ro(
            "names",
            [](const View& self) {
                // R15 anchor-exact: upstream `names` returns list(self.keys()) — the projected
                // LIST of immutable keys, an explicit snapshot, never the collection whose
                // mutators used to vanish. The anchor outranks the local tuple safety
                // spelling.
                nb::list out;
                for (const auto& item : self.vec()) {
                    out.append(nb::cast(self.key_of(*item)));
                }
                return out;
            },
            "List of item keys in insertion order (upstream CollectionBase.names).");
}

static void def_collection_views(nb::module_& m) {
    using namespace edi::views;

    nb::class_<StructuresView> structures_view(
        m, "Structures",
        "Live keyed collection of the project's structures (R15; key: the datablock name).");
    nb::class_<StructuresIter> structures_iter(m, "_StructuresIterator");
    def_keyed_collection<StructuresView, StructuresIter, edi::Structure>(structures_view,
                                                                         structures_iter);
    structures_view.def(
        "create",
        [](StructuresView& self, const std::string& name) {
            auto built = std::make_shared<edi::Structure>();
            built->name = name;
            self.set_item(name, std::move(built));
        },
        nb::kw_only(), "name"_a,
        "Create a minimal named structure and add it (upstream Structures.create).");
    // The add_from_* loaders — upstream Structures/Experiments at 0ffba46f: delegate to the
    // committed Python-side factory (never duplicated), then insert the built item into LIVE
    // storage under its own parsed key (R15 add semantics); return None. add_from_edi_path
    // delegates to the same from_cif_path parser — edi's factories parse CIF and .edi text
    // through one committed path.
    structures_view.def(
        "add_from_cif_str",
        [](StructuresView& self, const std::string& cif_str) {
            nb::object built =
                nb::module_::import_("edi").attr("StructureFactory").attr("from_cif_str")(cif_str);
            auto item = nb::cast<std::shared_ptr<edi::Structure>>(built);
            const std::string key = self.key_of(*item);
            self.set_item(key, std::move(item));
        },
        "cif_str"_a,
        "Create a structure from CIF content and add it (upstream Structures.add_from_cif_str).");
    structures_view.def(
        "add_from_cif_path",
        [](StructuresView& self, const std::filesystem::path& cif_path) {
            nb::object built =
                nb::module_::import_("edi").attr("StructureFactory").attr("from_cif_path")(cif_path);
            auto item = nb::cast<std::shared_ptr<edi::Structure>>(built);
            const std::string key = self.key_of(*item);
            self.set_item(key, std::move(item));
        },
        "cif_path"_a,
        "Create a structure from a CIF file and add it (upstream Structures.add_from_cif_path).");
    structures_view.def(
        "add_from_edi_path",
        [](StructuresView& self, const std::filesystem::path& edi_path) {
            nb::object built =
                nb::module_::import_("edi").attr("StructureFactory").attr("from_cif_path")(edi_path);
            auto item = nb::cast<std::shared_ptr<edi::Structure>>(built);
            const std::string key = self.key_of(*item);
            self.set_item(key, std::move(item));
        },
        "edi_path"_a,
        "Create a structure from an .edi file and add it (upstream Structures.add_from_edi_path).");
    structures_view.def(
        "show_names",
        [](const StructuresView& self) {
            // Text emission rides the one committed text path — the ProjectMetadata.show_as_text
            // precedent (builtins print; edi has no upstream `console`) — carrying the anchor's
            // exact content: the header paragraph, then the printed names list
            // (Structures.show_names at 0ffba46f; R11: cheap, over the shipped `names` kernel).
            const nb::object print = nb::module_::import_("builtins").attr("print");
            print("Defined structures 🧩");
            nb::list out;
            for (const auto& item : self.vec()) {
                out.append(nb::cast(self.key_of(*item)));
            }
            print(out);
        },
        "List all structure names in the collection (upstream Structures.show_names).");

    nb::class_<ExperimentsView> experiments_view(
        m, "Experiments",
        "Live keyed collection of the project's experiments (R15; key: the datablock name).");
    nb::class_<ExperimentsIter> experiments_iter(m, "_ExperimentsIterator");
    def_keyed_collection<ExperimentsView, ExperimentsIter, edi::BraggPdExperiment>(
        experiments_view, experiments_iter);
    experiments_view.def(
        "create",
        [](ExperimentsView& self, const std::string& name,
           std::optional<std::string> sample_form, std::optional<std::string> beam_mode,
           std::optional<std::string> radiation_probe,
           std::optional<std::string> scattering_type) {
            // Upstream Experiments.create delegates to the factory; edi's factory is the
            // committed Python-side ExperimentFactory (D4) — delegated, never duplicated.
            nb::object from_scratch =
                nb::module_::import_("edi").attr("ExperimentFactory").attr("from_scratch");
            nb::object built = from_scratch(
                "name"_a = name, "sample_form"_a = sample_form.value_or(""),
                "beam_mode"_a = beam_mode.value_or(""),
                "radiation_probe"_a = radiation_probe.value_or(""),
                "scattering_type"_a = scattering_type.value_or(""));
            self.set_item(name, nb::cast<std::shared_ptr<edi::BraggPdExperiment>>(built));
        },
        nb::kw_only(), "name"_a, "sample_form"_a = nb::none(), "beam_mode"_a = nb::none(),
        "radiation_probe"_a = nb::none(), "scattering_type"_a = nb::none(),
        "Add an experiment without associating a data file (upstream Experiments.create, "
        "delegating to ExperimentFactory.from_scratch).");
    // The experiment add_from_* loaders — same delegation shape as the structure ones
    // above (upstream Experiments at 0ffba46f).
    experiments_view.def(
        "add_from_cif_str",
        [](ExperimentsView& self, const std::string& cif_str) {
            nb::object built =
                nb::module_::import_("edi").attr("ExperimentFactory").attr("from_cif_str")(cif_str);
            auto item = nb::cast<std::shared_ptr<edi::BraggPdExperiment>>(built);
            const std::string key = self.key_of(*item);
            self.set_item(key, std::move(item));
        },
        "cif_str"_a,
        "Add an experiment from a CIF string (upstream Experiments.add_from_cif_str).");
    experiments_view.def(
        "add_from_cif_path",
        [](ExperimentsView& self, const std::filesystem::path& cif_path) {
            nb::object built = nb::module_::import_("edi").attr("ExperimentFactory").attr(
                "from_cif_path")(cif_path);
            auto item = nb::cast<std::shared_ptr<edi::BraggPdExperiment>>(built);
            const std::string key = self.key_of(*item);
            self.set_item(key, std::move(item));
        },
        "cif_path"_a,
        "Add an experiment from a CIF file path (upstream Experiments.add_from_cif_path).");
    experiments_view.def(
        "add_from_edi_path",
        [](ExperimentsView& self, const std::filesystem::path& edi_path) {
            nb::object built = nb::module_::import_("edi").attr("ExperimentFactory").attr(
                "from_cif_path")(edi_path);
            auto item = nb::cast<std::shared_ptr<edi::BraggPdExperiment>>(built);
            const std::string key = self.key_of(*item);
            self.set_item(key, std::move(item));
        },
        "edi_path"_a,
        "Add an experiment from an .edi file (upstream Experiments.add_from_edi_path).");
    experiments_view.def(
        "add_from_data_path",
        [](ExperimentsView& self, const std::string& name, const std::filesystem::path& data_path,
           std::optional<std::string> sample_form, std::optional<std::string> beam_mode,
           std::optional<std::string> radiation_probe,
           std::optional<std::string> scattering_type) {
            nb::object built =
                nb::module_::import_("edi").attr("ExperimentFactory").attr("from_data_path")(
                    "name"_a = name, "data_path"_a = data_path,
                    "sample_form"_a = sample_form.value_or(""),
                    "beam_mode"_a = beam_mode.value_or(""),
                    "radiation_probe"_a = radiation_probe.value_or(""),
                    "scattering_type"_a = scattering_type.value_or(""));
            auto item = nb::cast<std::shared_ptr<edi::BraggPdExperiment>>(built);
            self.set_item(name, std::move(item));
        },
        nb::kw_only(), "name"_a, "data_path"_a, "sample_form"_a = nb::none(),
        "beam_mode"_a = nb::none(), "radiation_probe"_a = nb::none(),
        "scattering_type"_a = nb::none(),
        "Add an experiment from a measured-data file path (upstream "
        "Experiments.add_from_data_path, delegating to ExperimentFactory.from_data_path).");
    experiments_view.def(
        "show_names",
        [](const ExperimentsView& self) {
            // Same emission precedent as Structures.show_names above (show_as_text's builtins
            // print), same anchor shape (Experiments.show_names at 0ffba46f).
            const nb::object print = nb::module_::import_("builtins").attr("print");
            print("Defined experiments 🔬");
            nb::list out;
            for (const auto& item : self.vec()) {
                out.append(nb::cast(self.key_of(*item)));
            }
            print(out);
        },
        "List all experiment names in the collection (upstream Experiments.show_names).");

    nb::class_<AtomSitesView> atom_sites_view(
        m, "AtomSites",
        "Live keyed collection of a structure's atom sites (R15; key: the site id).");
    nb::class_<AtomSitesIter> atom_sites_iter(m, "_AtomSitesIterator");
    def_keyed_collection<AtomSitesView, AtomSitesIter, edi::AtomSite>(atom_sites_view,
                                                                      atom_sites_iter);
    atom_sites_view.def(
        "create",
        [](AtomSitesView& self, nb::kwargs kwargs) {
            // Upstream CategoryCollection.create: default-construct, then a plain setattr loop
            // routed through the bound setters.
            auto built = std::make_shared<edi::AtomSite>();
            nb::object obj = nb::cast(built);
            for (auto kv : kwargs) {
                nb::setattr(obj, kv.first, kv.second);
            }
            // The key is copied BEFORE the move: argument evaluation order is unspecified, so
            // `set_item(built->id, std::move(built))` may null `built` first.
            const std::string key = built->id;
            self.set_item(key, std::move(built));
        },
        "Create a new atom site from keyword attributes and add it (upstream "
        "CategoryCollection.create).");

    // Upstream's PrefOrients — the experiment's preferred-orientation rows keyed by structure_id
    // (R15). The engine links one structure, so the adapter refuses a second row at calculation;
    // the collection itself follows the shared protocol.
    // The anisotropic sites' tensors (diffraction-lib's AtomSiteAnisoCollection). Rows follow the
    // sites' types: a site gets one when its type becomes anisotropic.
    nb::class_<AtomSiteAnisoView> atom_site_aniso_view(
        m, "AtomSiteAnisoCollection",
        "Live keyed collection of a structure's anisotropic displacement tensors (key: the site id).");
    nb::class_<AtomSiteAnisoIter> atom_site_aniso_iter(m, "_AtomSiteAnisoIterator");
    def_keyed_collection<AtomSiteAnisoView, AtomSiteAnisoIter, edi::AtomSiteAniso>(
        atom_site_aniso_view, atom_site_aniso_iter);

    nb::class_<PrefOrientsView> pref_orients_view(
        m, "PrefOrients",
        "Live keyed collection of an experiment's preferred-orientation rows (key: structure_id).");
    nb::class_<PrefOrientsIter> pref_orients_iter(m, "_PrefOrientsIterator");
    def_keyed_collection<PrefOrientsView, PrefOrientsIter, edi::PrefOrient>(pref_orients_view,
                                                                          pref_orients_iter);
    pref_orients_view.def(
        "create",
        [](PrefOrientsView& self, nb::kwargs kwargs) {
            // Upstream CategoryCollection.create, as AtomSites.create above.
            auto built = std::make_shared<edi::PrefOrient>();
            nb::object obj = nb::cast(built);
            for (auto kv : kwargs) {
                nb::setattr(obj, kv.first, kv.second);
            }
            const std::string key = built->structure_id;
            self.set_item(key, std::move(built));
        },
        "Create a preferred-orientation row from keyword attributes and add it (upstream "
        "CategoryCollection.create).");

    // diffraction-lib's analysis aliases and constraints (R15; key: the id). Their rows are text;
    // crysta resolves, parses, checks and applies them (edi ADR-0024).
    nb::class_<edi::ParameterAlias>(m, "Alias",
                                    "A name for one refinable parameter, used in constraints "
                                    "(diffraction-lib Alias).")
        .def_prop_rw(
            "id", [](const edi::ParameterAlias& self) { return self.id.value(); },
            [](edi::ParameterAlias& self, const std::string& id) {
                self.id = id;
                relations_changed(self.id);
            })
        .def_prop_ro("parameter_unique_name",
                     [](const edi::ParameterAlias& self) { return self.parameter_unique_name.value(); })
        // diffraction-lib Alias.parameters lists the descriptors the alias owns. Here `parameters` lists
        // refinable parameters, and an alias has none: its id and target name are text.
        .def_prop_ro(
            "parameters", [](const edi::ParameterAlias& /*self*/) { return std::vector<edi::Parameter*>{}; },
            "The alias's own refinable parameters: none (diffraction-lib Alias.parameters).")
        .def_prop_ro(
            "param",
            [](const edi::ParameterAlias& self) -> nb::object {
                edi::Project* project = host_of(self.id);
                if (project == nullptr) {
                    return nb::none();
                }
                for (const edi::NamedSlot& slot : edi::named_slots(*project)) {
                    if (slot.unique_name == self.parameter_unique_name.value()) {
                        // As an ordinary field getter returns it: attached to its row (X12), and
                        // keeping alive the object that owns its storage.
                        edi::detail::point_parameters(*project);
                        nb::object owner = owner_of(*project, slot.parameter);
                        if (owner.is_none()) {
                            return nb::none();
                        }
                        return nb::cast(slot.parameter, nb::rv_policy::reference_internal, owner);
                    }
                }
                return nb::none();
            },
            "The parameter this alias names, or None when it resolves to none.");
    nb::class_<AliasesView> aliases_view(m, "Aliases",
                                         "Live keyed collection of the project's aliases (R15; "
                                         "key: the id).");
    nb::class_<AliasesIter> aliases_iter(m, "_AliasesIterator");
    def_keyed_collection<AliasesView, AliasesIter, edi::ParameterAlias>(aliases_view, aliases_iter);
    aliases_view.def(
        "create",
        [](AliasesView& self, const std::string& id, const edi::Parameter& param) {
            if (self.find_first(id) >= 0) {
                throw nb::value_error(("an alias '" + id + "' already exists").c_str());
            }
            std::string name;
            for (const edi::NamedSlot& slot : edi::named_slots(*self.owner)) {
                if (slot.parameter == &param) {
                    name = slot.unique_name;
                    break;
                }
            }
            if (name.empty()) {
                throw nb::value_error(
                    ("alias '" + id + "': the parameter is not a refinable parameter of this project")
                        .c_str());
            }
            auto alias = std::make_shared<edi::ParameterAlias>();
            alias->id = id;
            alias->parameter_unique_name = name;
            self.set_item(id, std::move(alias));
            try {
                edi::refresh_relations(*self.owner, warn_python);
            } catch (const edi::ValidationError&) {
                self.vec().erase_at(static_cast<std::size_t>(self.find_first(id)));
                relations_changed(*self.owner);
                throw;
            }
        },
        nb::kw_only(), "id"_a, "param"_a,
        "Create an alias naming one of this project's parameters (diffraction-lib Aliases.create). "
        "A taken id, a parameter of another project or a name crysta reserves is refused.");

    nb::class_<edi::ParameterConstraint>(m, "Constraint",
                                         "One declared relation, `<alias> = <expression>` "
                                         "(diffraction-lib Constraint).")
        .def_prop_rw(
            "id", [](const edi::ParameterConstraint& self) { return self.id.value(); },
            [](edi::ParameterConstraint& self, const std::string& id) { self.id = id; })
        .def_prop_rw(
            "expression", [](const edi::ParameterConstraint& self) { return self.expression.value(); },
            [](edi::ParameterConstraint& self, const std::string& expression) {
                self.expression = expression;
                relations_changed(self.id);
            })
        .def_prop_rw(
            "enabled", [](const edi::ParameterConstraint& self) { return self.enabled.get(); },
            [](edi::ParameterConstraint& self, bool enabled) {
                self.enabled = enabled;
                relations_changed(self.id);
            },
            "Whether the constraint applies; a disabled one stays declared (saved as "
            "`_constraint.enabled false`).")
        .def_prop_ro("lhs_alias",
                     [](const edi::ParameterConstraint& self) {
                         return split_constraint(self.expression.value()).first;
                     })
        .def_prop_ro("rhs_expr", [](const edi::ParameterConstraint& self) {
            return split_constraint(self.expression.value()).second;
        });
    nb::class_<ConstraintsView> constraints_view(m, "Constraints",
                                                 "Live keyed collection of the project's constraints "
                                                 "(R15; key: the id).");
    nb::class_<ConstraintsIter> constraints_iter(m, "_ConstraintsIterator");
    def_keyed_collection<ConstraintsView, ConstraintsIter, edi::ParameterConstraint>(constraints_view,
                                                                                     constraints_iter);
    constraints_view
        .def(
            "create",
            [](ConstraintsView& self, const std::string& expression, std::optional<std::string> id) {
                const std::string key = id.value_or(split_constraint(expression).first);
                if (key.empty()) {
                    throw nb::value_error(("constraint '" + expression +
                                           "' names no alias left of an '=', so it needs an id")
                                              .c_str());
                }
                if (self.find_first(key) >= 0) {
                    throw nb::value_error(("a constraint '" + key + "' already exists").c_str());
                }
                auto constraint = std::make_shared<edi::ParameterConstraint>();
                constraint->id = key;
                constraint->expression = expression;
                self.set_item(key, std::move(constraint));
                try {
                    edi::refresh_relations(*self.owner, warn_python);
                } catch (const edi::ValidationError&) {
                    self.vec().erase_at(static_cast<std::size_t>(self.find_first(key)));
                    relations_changed(*self.owner);
                    throw;
                }
            },
            nb::kw_only(), "expression"_a, "id"_a = nb::none(),
            "Create a constraint from `<alias> = <expression>` (diffraction-lib "
            "Constraints.create); the id defaults to the left-hand alias. crysta checks it "
            "first: a refused constraint is not added.")
        .def_prop_ro(
            "enabled",
            [](const ConstraintsView& self) {
                return std::any_of(self.vec().begin(), self.vec().end(),
                                   [](const auto& constraint) { return constraint->enabled.get(); });
            },
            "Whether any constraint applies (diffraction-lib Constraints.enabled).")
        .def(
            "enable",
            [](ConstraintsView& self) {
                for (const auto& constraint : self.vec()) {
                    constraint->enabled = true;
                }
                relations_changed(*self.owner);
            },
            "Apply every constraint (diffraction-lib Constraints.enable).")
        .def(
            "disable",
            [](ConstraintsView& self) {
                for (const auto& constraint : self.vec()) {
                    constraint->enabled = false;
                }
                relations_changed(*self.owner);
            },
            "Keep every constraint declared but apply none (diffraction-lib Constraints.disable).")
        .def(
            "show",
            [](const ConstraintsView& self) {
                const nb::object print = nb::module_::import_("builtins").attr("print");
                if (self.vec().empty()) {
                    print("No constraints defined.");
                    return;
                }
                print("User defined constraints 🧷");
                for (const auto& constraint : self.vec()) {
                    print(constraint->id.value() + ": " + constraint->expression.value() +
                          (constraint->enabled.get() ? "" : "  (disabled)"));
                }
            },
            "Print the declared constraints (diffraction-lib Constraints.show).");

    nb::class_<BackgroundView> background_view(
        m, "_BackgroundView",
        "Live positional view over an experiment's background points (internal; R12 adapts the "
        "upstream id to list position).");
    nb::class_<BackgroundIter> background_iter(m, "_BackgroundIterator");
    background_iter
        .def(
            "__iter__", [](BackgroundIter& self) -> BackgroundIter& { return self; },
            nb::rv_policy::none)
        .def("__next__", [](BackgroundIter& self) {
            const edi::ItemVec<edi::LineSegment>& items = self.experiment->background;
            if (self.index >= items.size()) {
                throw nb::stop_iteration();
            }
            return items[self.index++];
        });
    background_view
        .def("__len__", [](const BackgroundView& self) { return self.vec().size(); })
        .def(
            "__iter__", [](const BackgroundView& self) { return BackgroundIter{self.experiment}; },
            nb::keep_alive<0, 1>())
        .def("__getitem__", [](const BackgroundView& self, std::ptrdiff_t i) {
            const std::ptrdiff_t n = static_cast<std::ptrdiff_t>(self.vec().size());
            if (i < 0) i += n;
            if (i < 0 || i >= n) {
                throw nb::index_error("background index out of range");
            }
            return self.vec()[static_cast<std::size_t>(i)];
        });
}

NB_MODULE(_edi, m) {
    // The engine's threading policy (crysta — passive wait + max(1, cores-2) team, any present
    // caller wait variable standing the whole policy down, a caller OMP_NUM_THREADS winning
    // the team) is planted as ENVIRONMENT by edi's package preamble (lib/edi/__init__.py)
    // before this extension loads — that is the seam. This call is a defensive no-op once the
    // preamble has planted the environment.
    edi::apply_engine_thread_defaults();
    // The module binds itself to the source it was built from — the same contract as crysta's
    // `__build_commit__`.
    m.attr("__build_commit__") = edi::build_commit();
    // The from_cif_str core entries — private: the python factories wrap them. The one name -> path
    // decision (crysta's), for the Python CLI's calc writer — private, so edi keeps no naming policy
    // of its own and no public name.
    m.def("_entity_path", &edi::entity_path, "directory"_a, "kind"_a, "name"_a);
    // The private hooks of the crysta-vs-edi parity checks, named as crysta's own are.
    m.def("_model_dump", &edi::engine_model_dump, "project"_a);
    m.def("_folds_reflections", &edi::engine_folds_reflections, "project"_a);
    m.def("_structure_factor_evaluations", &edi::engine_structure_factor_evaluations);
    m.def("_structure_from_edi_text",
          [](const std::string& text) { return edi::structure_from_edi_text(text); });
    m.def("_experiment_from_edi_text",
          [](const std::string& text) { return edi::experiment_from_edi_text(text); });
    // The one plain-data reader (crysta's), for ExperimentFactory.from_data_path: the rows and what it dropped.
    m.def(
        "_read_plain_data",
        [](const std::string& path) {
            edi::PlainDataRows read = edi::read_plain_data(path);
            nb::dict rows;
            rows["x"] = read.x;
            rows["y"] = read.y;
            rows["sigma"] = read.sigma;
            rows["skipped"] = read.skipped;
            rows["nonpositive"] = read.nonpositive;
            rows["duplicates"] = read.duplicates;
            rows["reordered"] = read.reordered;
            rows["derived"] = read.derived;
            return rows;
        },
        "path"_a);
    // The descent registry resolved from the LINKED crysta engine at call time, never a
    // transcribed copy.
    // `python -m edi` renders its `--descent` choices and help default from these, so every edi
    // advertisement of the set has crysta's registry as its single source.
    m.def("_descent_ids", [] { return edi::descent_ids(); },
          "The registered descent ids, in crysta's `--list-descents` order.");
    m.def("_default_descent", [] { return edi::default_descent(); },
          "The registry id an omitted descent selection runs.");

    m.doc() = "edi core bindings (thin nanobind over the C++ product core; ADR-0009)";

    // Fail-closed I/O errors surface as edi.IoError, a subclass of ValueError carrying a non-empty
    // `.diagnostics` mapping (category + message) so a rejection is structured, not opaque.
    nb::object io_error_type =
        nb::steal(PyErr_NewException("edi._edi.IoError", PyExc_ValueError, nullptr));
    m.attr("IoError") = io_error_type;
    g_io_error_type = new nb::object(io_error_type);
    nb::register_exception_translator(
        [](const std::exception_ptr& pointer, void* /*payload*/) {
            try {
                std::rethrow_exception(pointer);
            } catch (const edi::IoError& error) {
                nb::object exception = (*g_io_error_type)(nb::str(error.what()));
                nb::dict entry;
                entry["code"] = "io-error";
                entry["message"] = nb::str(error.what());
                nb::list diagnostics;
                diagnostics.append(entry);
                exception.attr("diagnostics") = diagnostics;
                PyErr_SetObject(g_io_error_type->ptr(), exception.ptr());
            }
        },
        nullptr);

    // Severity, Diagnostic and the ValidationError hierarchy.
    nb::enum_<edi::Severity>(m, "Severity")
        .value("Error", edi::Severity::Error)
        .value("Warning", edi::Severity::Warning)
        .value("Info", edi::Severity::Info);
    nb::class_<edi::Diagnostic>(m, "Diagnostic")
        .def_ro("code", &edi::Diagnostic::code)
        .def_ro("severity", &edi::Diagnostic::severity)
        .def_ro("path", &edi::Diagnostic::path)
        .def_ro("message", &edi::Diagnostic::message)
        .def_ro("params", &edi::Diagnostic::params)
        .def_ro("source", &edi::Diagnostic::source)
        .def("__repr__", [](const edi::Diagnostic& diagnostic) {
            std::string repr = "<Diagnostic " + diagnostic.code + " " +
                               std::string(edi::severity_name(diagnostic.severity));
            if (!diagnostic.path.empty()) {
                repr += " @" + diagnostic.path;
            }
            return repr + ": " + diagnostic.message + ">";
        });
    auto make_error_type = [&m](const char* name, const nb::object& base) {
        const std::string qualified = "edi._edi." + std::string(name);
        nb::object type = nb::steal(PyErr_NewException(qualified.c_str(), base.ptr(), nullptr));
        m.attr(name) = type;
        return type;
    };
    g_validation_types = new ValidationErrorTypes{};
    g_validation_types->base = make_error_type("ValidationError", io_error_type);
    g_validation_types->syntax = make_error_type("SyntaxValidationError", g_validation_types->base);
    g_validation_types->schema = make_error_type("SchemaValidationError", g_validation_types->base);
    g_validation_types->domain = make_error_type("DomainValidationError", g_validation_types->base);
    nb::register_exception_translator(
        [](const std::exception_ptr& pointer, void* /*payload*/) {
            try {
                std::rethrow_exception(pointer);
            } catch (const edi::ValidationError& error) {
                const ValidationErrorTypes& types = *g_validation_types;
                const nb::object& type = error.tier() == 1   ? types.syntax
                                         : error.tier() == 2 ? types.schema
                                         : error.tier() == 3 ? types.domain
                                                             : types.base;
                nb::object exception = type(nb::str(error.what()));
                exception.attr("diagnostics") = nb::cast(error.diagnostics());
                PyErr_SetObject(type.ptr(), exception.ptr());
            }
        },
        nullptr);

    // A data or reflection object's computed columns are a value read. They are its experiment's
    // current ones, calculated first when they are not; a failed calculation raises and never
    // returns earlier numbers.
    const auto live_data = [](const edi::PdDataBase& p) -> const edi::PdDataBase& {
        return p.computed_for_read();
    };
    const auto live_refln = [](const edi::PowderReflnDataBase& r) -> const edi::PowderReflnDataBase& {
        return r.computed_for_read();
    };

    nb::class_<edi::Parameter>(m, "Parameter")
        .def("__setattr__",
             renewing_setattr<edi::Parameter>({"uncertainty", "start_value", "start_uncertainty", "free"}, renew_epoch), nb::arg("name"), nb::arg("value").none())
        // uncertainty is Optional[float]: an omitted uncertainty defaults to present 0.0 (compat), an explicit
        // None marks the refinable-no-prior-uncertainty state (`value()`), and `.uncertainty` reads back None for
        // that state, a float otherwise.
        .def(nb::init<double, std::optional<double>, bool>(), "value"_a, "uncertainty"_a = 0.0,
             "free"_a = false)
        .def_prop_rw(
            "value", [](const edi::Parameter& p) { return p.value.get(); },
            [](edi::Parameter& p, double value) {
                refuse_detached(p);
                check_range(p.spec, value, p.spec ? p.spec->name : "value");
                p.value = value;
            })
        .def_prop_rw(
            "uncertainty", [](const edi::Parameter& p) { return p.uncertainty.get(); },
            [](edi::Parameter& p, std::optional<double> uncertainty) {
                refuse_detached(p);
                p.uncertainty = uncertainty;
            })
        // The persisted pre-fit snapshot (diffraction-lib spelling); None = disengaged,
        // no fit state recorded.
        .def_prop_rw(
            "start_value", [](const edi::Parameter& p) { return p.start_value.get(); },
            [](edi::Parameter& p, std::optional<double> start_value) {
                refuse_detached(p);
                p.start_value = start_value;
            })
        .def_prop_rw(
            "start_uncertainty", [](const edi::Parameter& p) { return p.start_uncertainty.get(); },
            [](edi::Parameter& p, std::optional<double> start_uncertainty) {
                refuse_detached(p);
                p.start_uncertainty = start_uncertainty;
            })
        .def_prop_rw(
            "free", [](const edi::Parameter& p) { return p.free.get(); },
            [](edi::Parameter& p, bool free) {
                refuse_detached(p);
                if (free && edi::is_fixed_setting(p.spec)) {
                    throw std::invalid_argument(std::string(p.spec->name) +
                                                " is a fixed setting, not a refinable parameter");
                }
                (void)dependence_now(p);  // the marks as the relations are now
                if (!edi::set_free(p, free)) {
                    const std::string name = p.spec != nullptr ? p.spec->name : std::string("parameter");
                    const std::string message =
                        "crysta.domain.dependent_free_ignored: parameter '" + name + "' is " +
                        (p.dependence == edi::Dependence::Constrained ? "set by a constraint"
                         : p.dependence == edi::Dependence::SymmetryFixed ? "fixed by symmetry"
                                                                          : "constrained by symmetry") +
                        "; free = True is ignored and it stays dependent";
                    if (PyErr_WarnEx(PyExc_UserWarning, message.c_str(), 1) < 0) {
                        throw nb::python_error();
                    }
                }
            })
        // Whether a declared constraint or the space group sets this parameter (diffraction-lib
        // GenericParameter.user_constrained / .symmetry_constrained), from crysta's relation graph.
        .def_prop_ro("user_constrained",
                     [](edi::Parameter& p) { return dependence_now(p) == edi::Dependence::Constrained; })
        .def_prop_ro("symmetry_constrained",
                     [](edi::Parameter& p) {
                         const edi::Dependence dependence = dependence_now(p);
                         return dependence == edi::Dependence::SymmetryFixed ||
                                dependence == edi::Dependence::SymmetryTied;
                     })
        // ADR-0012: whether a collection holds this parameter's row. A removed row's parameters
        // keep their last values and refuse writes.
        .def("is_attached", [](const edi::Parameter& p) { return p.is_attached(); })
        // Metadata (read-only; the spec is shared static data, never per-instance). The leaf
        // name (diffraction-lib `GenericDescriptorBase.name`), from the spec.
        .def_prop_ro("name", [](const edi::Parameter& p) { return require_spec(p).name; })
        .def_prop_ro("units", [](const edi::Parameter& p) { return require_spec(p).units; })
        .def_prop_ro("description",
                     [](const edi::Parameter& p) { return require_spec(p).description; })
        .def_prop_ro("min_value", [](const edi::Parameter& p) { return require_spec(p).range.min; })
        .def_prop_ro("max_value", [](const edi::Parameter& p) { return require_spec(p).range.max; });

    nb::class_<edi::AtomSite> atom_site(m, "AtomSite", nb::is_weak_referenceable());
    atom_site.def("__setattr__", renewing_setattr<edi::AtomSite>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    // Shared-owned from birth (nb::new_), so a stored item releases its wrapper without
    // losing storage while add() still shares the caller's object.
    atom_site.def(nb::new_([]() { return std::make_shared<edi::AtomSite>(); }))
        // ADR-0016: assigning is a rename the owning structure admits; an anisotropic site's
        // tensor row, keyed by the site id, follows it.
        .def_prop_rw(
            "id", [](const edi::AtomSite& self) { return self.id.value(); },
            // Every assignment is a write, an equal one included; the collection carries a tensor row
            // along (detail::follow_site_rename).
            [](edi::AtomSite& self, std::string value) { self.id = std::move(value); })
        // A geometry input records its own writes, so it binds as a property.
        .def_prop_rw(
            "type_symbol", [](const edi::AtomSite& self) { return self.type_symbol.value(); },
            [](edi::AtomSite& self, std::string value) { self.type_symbol = std::move(value); })
        .def_prop_rw(
            "wyckoff_letter", [](const edi::AtomSite& self) { return self.wyckoff_letter.value(); },
            [](edi::AtomSite& self, std::string value) { self.wyckoff_letter = std::move(value); })
        // A new type converts the site's values (ADR-0027) at its structure's cell, its
        // uncertainty and fit start with them.
        .def_prop_rw(
            "adp_type", [](const edi::AtomSite& self) { return self.adp_type.value(); },
            [](edi::AtomSite& self, const std::string& value) {
                if (!edi::is_adp_type(value)) {
                    throw nb::value_error(("adp_type '" + value +
                                           "' is not one of Biso, Uiso, Bani, Uani, beta")
                                              .c_str());
                }
                // A site no structure holds yet is being declared: its values are taken as
                // given in the new type.
                if (!self.row.attached()) {
                    self.adp_type = value;
                    return;
                }
                edi::Structure* structure = holding_structure(self);
                if (structure == nullptr) {
                    throw nb::value_error("the site's collection names no structure");
                }
                edi::change_adp_type(*structure, self, value);
            });
    def_parameter_walks(atom_site);
    def_parameter_field(atom_site, "fract_x", &edi::AtomSite::fract_x);
    def_parameter_field(atom_site, "fract_y", &edi::AtomSite::fract_y);
    def_parameter_field(atom_site, "fract_z", &edi::AtomSite::fract_z);
    def_parameter_field(atom_site, "occupancy", &edi::AtomSite::occupancy);
    def_parameter_field(atom_site, "adp_iso", &edi::AtomSite::adp_iso);

    // An anisotropic site's tensor (diffraction-lib's AtomSiteAniso), keyed by the site id; its
    // components are in the site's declared type.
    nb::class_<edi::AtomSiteAniso> atom_site_aniso(m, "AtomSiteAniso");
    atom_site_aniso.def("__setattr__", renewing_setattr<edi::AtomSiteAniso>({}, renew_epoch),
                        nb::arg("name"), nb::arg("value").none());
    atom_site_aniso.def(nb::new_([]() { return std::make_shared<edi::AtomSiteAniso>(); }))
        // The key is the site's id: set while the row is being declared, renamed with its site;
        // a held row refuses a rename of its own (detail::follow_tensor_rename).
        .def_prop_rw(
            "id", [](const edi::AtomSiteAniso& self) { return self.id.value(); },
            [](edi::AtomSiteAniso& self, std::string value) { self.id = std::move(value); });
    def_parameter_walks(atom_site_aniso);
    def_parameter_field(atom_site_aniso, "adp_11", &edi::AtomSiteAniso::adp_11);
    def_parameter_field(atom_site_aniso, "adp_22", &edi::AtomSiteAniso::adp_22);
    def_parameter_field(atom_site_aniso, "adp_33", &edi::AtomSiteAniso::adp_33);
    def_parameter_field(atom_site_aniso, "adp_12", &edi::AtomSiteAniso::adp_12);
    def_parameter_field(atom_site_aniso, "adp_13", &edi::AtomSiteAniso::adp_13);
    def_parameter_field(atom_site_aniso, "adp_23", &edi::AtomSiteAniso::adp_23);

    // One upstream PrefOrient row — the March-Dollase coefficient and random fraction (fit
    // parameters), the fixed integer texture axis, the structure it corrects.
    nb::class_<edi::PrefOrient> pref_orient(m, "PrefOrient");
    pref_orient.def("__setattr__", renewing_setattr<edi::PrefOrient>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    pref_orient.def(nb::new_([]() { return std::make_shared<edi::PrefOrient>(); }))
        // ADR-0016: assigning is a rename the owning experiment admits.
        .def_prop_rw(
            "structure_id", [](const edi::PrefOrient& self) { return self.structure_id.value(); },
            [](edi::PrefOrient& self, std::string value) { self.structure_id = std::move(value); });
    for (const auto& [name, member] :
         {std::pair<const char*, edi::detail::Written<int> edi::PrefOrient::*>{
              "index_h", &edi::PrefOrient::index_h},
          std::pair<const char*, edi::detail::Written<int> edi::PrefOrient::*>{
              "index_k", &edi::PrefOrient::index_k},
          std::pair<const char*, edi::detail::Written<int> edi::PrefOrient::*>{
              "index_l", &edi::PrefOrient::index_l}}) {
        pref_orient.def_prop_rw(
            name, [member](const edi::PrefOrient& self) { return (self.*member).get(); },
            [member](edi::PrefOrient& self, int value) {
                if (value > edi::kPreferredOrientationAxisBound ||
                    value < -edi::kPreferredOrientationAxisBound) {  // review-4 F2
                    throw std::invalid_argument("a texture axis component exceeds the bound " +
                                                std::to_string(edi::kPreferredOrientationAxisBound));
                }
                const int previous = self.*member;
                self.*member = value;
                if (self.index_h == 0 && self.index_k == 0 && self.index_l == 0) {
                    self.*member = previous;
                    throw std::invalid_argument("the texture axis [0 0 0] has no direction");
                }
            });
    }
    def_parameter_walks(pref_orient);
    def_parameter_field(pref_orient, "march_r", &edi::PrefOrient::march_r);
    def_parameter_field(pref_orient, "march_random_fract", &edi::PrefOrient::march_random_fract);

    nb::class_<edi::Cell> cell(m, "Cell");
    cell.def("__setattr__", renewing_setattr<edi::Cell>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    cell.def(nb::init<>());
    def_parameter_walks(cell);
    def_parameter_field(cell, "length_a", &edi::Cell::length_a);
    def_parameter_field(cell, "length_b", &edi::Cell::length_b);
    def_parameter_field(cell, "length_c", &edi::Cell::length_c);
    def_parameter_field(cell, "angle_alpha", &edi::Cell::angle_alpha);
    def_parameter_field(cell, "angle_beta", &edi::Cell::angle_beta);
    def_parameter_field(cell, "angle_gamma", &edi::Cell::angle_gamma);

    // The space-group category (name + ITA coordinate-system code as one object).
    nb::class_<edi::SpaceGroup>(m, "SpaceGroup")
        .def("__setattr__", renewing_setattr<edi::SpaceGroup>({}, renew_epoch), nb::arg("name"), nb::arg("value").none())
        .def(nb::init<>())
        .def_prop_rw(
            "name_h_m", [](const edi::SpaceGroup& self) { return self.name_h_m.value(); },
            // A new name takes that group's default setting, so the code and a stored IT number follow it (as
            // diffraction-lib's name_h_m setter resets the code); a name crysta's table lacks is kept as given.
            [](edi::SpaceGroup& self, std::string value) {
                if (edi::same_space_group_name(value, self.name_h_m.value())) {
                    self.name_h_m = std::move(value);
                } else if (const auto setting = edi::space_group_setting_for_name(value)) {
                    edi::assign_space_group_setting(self, *setting, false);
                } else {
                    self.name_h_m = std::move(value);
                }
            })
        .def_prop_rw(
            "coord_system_code",
            [](const edi::SpaceGroup& self) { return self.coord_system_code.value(); },
            [](edi::SpaceGroup& self, std::string value) {
                self.coord_system_code = std::move(value);
            })
        // The IUCr IT number, presence-tracked (`int | None`). A number takes that group's default setting: its
        // name and code follow.
        .def_prop_rw(
            "it_number", [](const edi::SpaceGroup& self) { return self.it_number; },
            [](edi::SpaceGroup& self, std::optional<int> value) {
                const auto setting = value ? edi::space_group_setting_for_number(*value) : std::nullopt;
                if (setting) {
                    edi::assign_space_group_setting(self, *setting, true);
                } else {
                    self.it_number = value;
                }
            });

    nb::class_<edi::Structure> structure(m, "Structure", nb::is_weak_referenceable());
    structure.def("__setattr__", renewing_setattr<edi::Structure>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    def_parameter_walks(structure);
    // Shared-owned from birth (nb::new_), so a stored item releases its wrapper without
    // losing storage while add() still shares the caller's object.
    structure.def(nb::new_([]() { return std::make_shared<edi::Structure>(); }))
        .def_prop_rw(  // A rename the owning project admits
            "name", [](const edi::Structure& self) { return self.name.value(); },
            [](edi::Structure& self, std::string value) { self.name = std::move(value); })
        .def_rw("space_group", &edi::Structure::space_group)
        .def_rw("cell", &edi::Structure::cell)
        // The R15 keyed collection view (live; the def_rw list copy is retired).
        .def_prop_ro(
            "atom_sites",
            [](edi::Structure& self) {
                return edi::views::AtomSitesView{&self, &edi::Structure::atom_sites,
                                                 &edi::AtomSite::id};
            },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "atom_site_aniso",
            [](edi::Structure& self) {
                return edi::views::AtomSiteAnisoView{&self, &edi::Structure::atom_site_aniso,
                                                     &edi::AtomSiteAniso::id};
            },
            nb::keep_alive<0, 1>())
        .def_prop_rw(
            "scattering_lengths_fm",
            [](const edi::Structure& self) { return self.scattering_lengths_fm.get(); },
            [](edi::Structure& self, std::map<std::string, double> value) {
                self.scattering_lengths_fm = std::move(value);
            })
        // The bond cutoffs (an input), and crysta's computed structure categories — the
        // stored unit-cell result, each property read calculating through crysta when it is
        // not current and returning an object that holds what it read. edi computes none of
        // these numbers.
        .def_prop_ro(
            "geom", [](edi::Structure& self) -> edi::Geom& { return self.geom; },
            nb::rv_policy::reference_internal)
        .def_prop_ro(
            "space_group_symop",
            [](edi::Structure& self) { return SymopView{{&self, stored_geometry(self)}}; },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "expanded_atom_sites",
            [](edi::Structure& self) {
                return ExpandedAtomSitesView{{&self, stored_geometry(self)}};
            },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "geom_bond",
            [](edi::Structure& self) { return GeomBondView{{&self, stored_geometry(self)}}; },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "atom_sites_cartn_transform",
            [](edi::Structure& self) {
                return CartnTransformView{{&self, stored_geometry(self)}};
            },
            nb::keep_alive<0, 1>())
        .def(
            "geometry",
            [](edi::Structure& self,
               const std::optional<std::vector<std::vector<double>>>& view_range) {
                return StructureGeometryView{
                    &self, std::make_shared<const edi::WindowGeometry>(
                               edi::window_geometry(self, view_window(view_range)))};
            },
            nb::arg("view_range") = nb::none(), nb::keep_alive<0, 1>(),
            "The computed structure categories for a view window: three (min, max) fractional "
            "pairs, one per axis; None is the unit cell.");

    nb::class_<edi::Geom>(m, "Geom")
        .def_prop_rw(
            "min_bond_distance_cutoff",
            [](const edi::Geom& self) {
                return self.min_bond_distance_cutoff->value_or(
                    edi::default_min_bond_distance_cutoff());
            },
            [](edi::Geom& self, std::optional<double> value) {
                // The field records the write, whatever value it leaves.
                self.min_bond_distance_cutoff = geom_value(value, "min_bond_distance_cutoff");
            },
            nb::arg("value").none(),
            "Minimum permitted bonded distance (angstrom); None restores the default 0.")
        .def_prop_rw(
            "bond_distance_inc",
            [](const edi::Geom& self) {
                return self.bond_distance_inc->value_or(edi::default_bond_distance_inc());
            },
            [](edi::Geom& self, std::optional<double> value) {
                self.bond_distance_inc = geom_value(value, "bond_distance_inc");
            },
            nb::arg("value").none(),
            "Increment added to the summed covalent radii (angstrom); None restores the default "
            "0.25.");

    nb::class_<SymopView>(m, "SpaceGroupSymop")
        .def_prop_ro(
            "id",
            [](const SymopView& self) { return ordinal_array(self.get().space_group_symop.size()); })
        .def_prop_ro("operation_xyz", [](const SymopView& self) {
            return text_tuple(self.get().space_group_symop.operation_xyz);
        });

    nb::class_<ExpandedAtomSitesView> expanded(m, "ExpandedAtomSites");
    expanded
        .def_prop_ro("id",
                     [](const ExpandedAtomSitesView& self) {
                         return ordinal_array(self.get().expanded_atom_sites.size());
                     })
        .def_prop_ro("atom_site_id",
                     [](const ExpandedAtomSitesView& self) {
                         return text_tuple(self.get().expanded_atom_sites.atom_site_id);
                     })
        .def_prop_ro("site_symmetry",
                     [](const ExpandedAtomSitesView& self) {
                         return text_tuple(self.get().expanded_atom_sites.site_symmetry);
                     })
        .def_prop_ro("cluster_id", [](const ExpandedAtomSitesView& self) {
            return readonly_array(self.get().expanded_atom_sites.cluster_id);
        });
    for (const auto& [name, member] :
         {std::pair<const char*, edi::ComputedColumn<double> edi::ExpandedAtomSites::*>{
              "fract_x", &edi::ExpandedAtomSites::fract_x},
          {"fract_y", &edi::ExpandedAtomSites::fract_y},
          {"fract_z", &edi::ExpandedAtomSites::fract_z},
          {"cartn_x", &edi::ExpandedAtomSites::cartn_x},
          {"cartn_y", &edi::ExpandedAtomSites::cartn_y},
          {"cartn_z", &edi::ExpandedAtomSites::cartn_z},
          {"occupancy", &edi::ExpandedAtomSites::occupancy},
          {"u_iso", &edi::ExpandedAtomSites::u_iso}}) {
        expanded.def_prop_ro(name, [member](const ExpandedAtomSitesView& self) {
            return readonly_array(self.get().expanded_atom_sites.*member);
        });
    }

    nb::class_<GeomBondView>(m, "GeomBond")
        .def_prop_ro(
            "id", [](const GeomBondView& self) { return ordinal_array(self.get().geom_bond.size()); })
        .def_prop_ro("expanded_atom_site_id_1",
                     [](const GeomBondView& self) {
                         return readonly_array(self.get().geom_bond.expanded_atom_site_id_1);
                     })
        .def_prop_ro("expanded_atom_site_id_2",
                     [](const GeomBondView& self) {
                         return readonly_array(self.get().geom_bond.expanded_atom_site_id_2);
                     })
        .def_prop_ro("atom_site_label_1",
                     [](const GeomBondView& self) {
                         return text_tuple(self.get().geom_bond.atom_site_label_1);
                     })
        .def_prop_ro("atom_site_label_2",
                     [](const GeomBondView& self) {
                         return text_tuple(self.get().geom_bond.atom_site_label_2);
                     })
        .def_prop_ro("site_symmetry_1",
                     [](const GeomBondView& self) {
                         return text_tuple(self.get().geom_bond.site_symmetry_1);
                     })
        .def_prop_ro("site_symmetry_2",
                     [](const GeomBondView& self) {
                         return text_tuple(self.get().geom_bond.site_symmetry_2);
                     })
        .def_prop_ro("distance", [](const GeomBondView& self) {
            return readonly_array(self.get().geom_bond.distance);
        });

    // r = M x, row-major: `mat_ij` is row i, column j, and the matrix's columns are the cell's
    // basis vectors. The members are the category's nine CIF items, as crysta computed them.
    nb::class_<CartnTransformView> cartn(m, "AtomSitesCartnTransform");
    cartn.def_prop_ro("axes", [](const CartnTransformView& self) {
        return self.get().atom_sites_cartn_transform.axes;
    });
    for (const auto& [name, index] :
         {std::pair<const char*, std::size_t>{"mat_11", 0}, {"mat_12", 1}, {"mat_13", 2},
          {"mat_21", 3}, {"mat_22", 4}, {"mat_23", 5},
          {"mat_31", 6}, {"mat_32", 7}, {"mat_33", 8}}) {
        cartn.def_prop_ro(name, [index](const CartnTransformView& self) {
            return self.get().atom_sites_cartn_transform.matrix[index];
        });
    }

    nb::class_<StructureGeometryView>(m, "StructureGeometry")
        .def_prop_ro("space_group_symop",
                     [](const StructureGeometryView& self) {
                         return SymopView{{self.structure, self.fixed()}};
                     })
        .def_prop_ro("expanded_atom_sites",
                     [](const StructureGeometryView& self) {
                         return ExpandedAtomSitesView{{self.structure, self.fixed()}};
                     })
        .def_prop_ro("geom_bond",
                     [](const StructureGeometryView& self) {
                         return GeomBondView{{self.structure, self.fixed()}};
                     })
        .def_prop_ro("atom_sites_cartn_transform",
                     [](const StructureGeometryView& self) {
                         return CartnTransformView{{self.structure, self.fixed()}};
                     })
        .def_prop_ro("view_range",
                     [](const StructureGeometryView& self) {
                         nb::list out;
                         for (std::size_t axis = 0; axis < 3; ++axis) {
                             out.append(nb::make_tuple(self.value->geometry.window.min[axis],
                                                       self.value->geometry.window.max[axis]));
                         }
                         return nb::tuple(out);
                     })
        .def(
            "is_current",
            [](const StructureGeometryView& self) {
                return edi::window_geometry_current(*self.structure, *self.value);
            },
            "Whether no input of the structure's geometry was written since this was computed.");

    nb::class_<edi::LineSegment> background_point(m, "LineSegment", nb::is_weak_referenceable());
    background_point.def("__setattr__", renewing_setattr<edi::LineSegment>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    background_point
        .def(nb::new_([]() { return std::make_shared<edi::LineSegment>(); }))
        .def_prop_rw(
            "position", [](const edi::LineSegment& self) { return self.position.get(); },
            [](edi::LineSegment& self, double value) { self.position = value; });
    def_parameter_walks(background_point);
    def_parameter_field(background_point, "intensity", &edi::LineSegment::intensity);

    // One term of a polynomial or Chebyshev background — its fixed order and its refinable
    // coefficient.
    nb::class_<edi::PolynomialTerm> background_term(m, "PolynomialTerm");
    background_term.def("__setattr__", renewing_setattr<edi::PolynomialTerm>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    background_term
        .def(nb::new_([]() { return std::make_shared<edi::PolynomialTerm>(); }))
        .def_prop_rw(
            "order", [](const edi::PolynomialTerm& self) { return self.order.get(); },
            [](edi::PolynomialTerm& self, int value) { self.order = value; });
    def_parameter_walks(background_term);
    def_parameter_field(background_term, "coef", &edi::PolynomialTerm::coef);

    // The four typed experiment-type axes (upstream's classification). Values and tokens
    // match diffraction-lib verbatim; consumers switch on a typed axis, never a string sniff.
    nb::enum_<edi::SampleFormEnum>(m, "SampleFormEnum")
        .value("POWDER", edi::SampleFormEnum::POWDER)
        .value("SINGLE_CRYSTAL", edi::SampleFormEnum::SINGLE_CRYSTAL);
    nb::enum_<edi::BeamModeEnum>(m, "BeamModeEnum")
        .value("CONSTANT_WAVELENGTH", edi::BeamModeEnum::CONSTANT_WAVELENGTH)
        .value("TIME_OF_FLIGHT", edi::BeamModeEnum::TIME_OF_FLIGHT);
    nb::enum_<edi::RadiationProbeEnum>(m, "RadiationProbeEnum")
        .value("NEUTRON", edi::RadiationProbeEnum::NEUTRON)
        .value("XRAY", edi::RadiationProbeEnum::XRAY);
    nb::enum_<edi::ScatteringTypeEnum>(m, "ScatteringTypeEnum")
        .value("BRAGG", edi::ScatteringTypeEnum::BRAGG)
        .value("TOTAL", edi::ScatteringTypeEnum::TOTAL);
    nb::enum_<edi::PeakProfileTypeEnum>(m, "PeakProfileTypeEnum")
        .value("TOF_JORGENSEN", edi::PeakProfileTypeEnum::TOF_JORGENSEN)
        .value("TOF_JORGENSEN_VON_DREELE", edi::PeakProfileTypeEnum::TOF_JORGENSEN_VON_DREELE)
        .value("CWL_GAUSSIAN", edi::PeakProfileTypeEnum::CWL_GAUSSIAN)
        .value("CWL_LORENTZIAN", edi::PeakProfileTypeEnum::CWL_LORENTZIAN)
        .value("CWL_PSEUDO_VOIGT", edi::PeakProfileTypeEnum::CWL_PSEUDO_VOIGT)
        .value("CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI", edi::PeakProfileTypeEnum::CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI)
        .value("CWL_TCH_PSEUDO_VOIGT", edi::PeakProfileTypeEnum::CWL_TCH_PSEUDO_VOIGT)
        .value("CWL_TCH_PSEUDO_VOIGT_FCJ", edi::PeakProfileTypeEnum::CWL_TCH_PSEUDO_VOIGT_FCJ)
        .value("TOF_PSEUDO_VOIGT", edi::PeakProfileTypeEnum::TOF_PSEUDO_VOIGT);

    // The experiment-type category: presence-tracked axes read as their EFFECTIVE value (the
    // declared edi defaults) and engage on assignment; the writer round-trips presence.
    nb::class_<edi::ExperimentType> experiment_type(m, "ExperimentType");
    experiment_type.def("__setattr__", renewing_setattr<edi::ExperimentType>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    experiment_type.def(nb::init<>())
        .def_prop_rw(
            "sample_form",
            [](const edi::ExperimentType& t) { return t.effective_sample_form(); },
            [](edi::ExperimentType& t, edi::SampleFormEnum value) { t.sample_form = value; })
        .def_prop_rw(
            "beam_mode", [](const edi::ExperimentType& t) { return t.effective_beam_mode(); },
            [](edi::ExperimentType& t, edi::BeamModeEnum value) { t.beam_mode = value; })
        .def_prop_rw(
            "radiation_probe",
            [](const edi::ExperimentType& t) { return t.effective_radiation_probe(); },
            [](edi::ExperimentType& t, edi::RadiationProbeEnum value) { t.radiation_probe = value; })
        .def_prop_rw(
            "scattering_type",
            [](const edi::ExperimentType& t) { return t.effective_scattering_type(); },
            [](edi::ExperimentType& t, edi::ScatteringTypeEnum value) { t.scattering_type = value; });

    // The peak-profile category: typed selector + TOF/CW parameter blocks (CW presence-tracked).
    nb::class_<edi::views::PeakNode> peak(m, "PeakBase");
    peak.def("__setattr__", renewing_setattr<edi::views::PeakNode>({}, renew_peak), nb::arg("name"), nb::arg("value").none());
    peak.def(
        "show_supported",
        [](edi::views::PeakNode& self) {
            const std::string current =
                edi::effective_peak_type(*self.experiment);
            const nb::object print = nb::module_::import_("builtins").attr("print");
            print("Supported peak types");
            for (nb::handle tag : active_tags(*g_peak_registry)) {
                const std::string token = nb::cast<std::string>(nb::str(tag));
                print((token == current ? "* " : "  ") + token);
            }
        },
        "Print supported peak types, marking the active one (diffraction-lib "
        "SwitchableCategoryBase.show_supported — ruling absorb-ten-26).");
    peak.def_prop_rw(
            "type",
            [](edi::views::PeakNode& self) -> nb::object {
                // The three shipped kernels keep their enum spelling (crysta parity); a
                // registered extension token reads back verbatim (seam 20); absent is None.
                if (!self.experiment->peak.type) {
                    return nb::none();
                }
                const std::string& stored = *self.experiment->peak.type;
                if (stored == "tof-jorgensen") {
                    return nb::cast(edi::PeakProfileTypeEnum::TOF_JORGENSEN);
                }
                if (stored == "tof-jorgensen-von-dreele") {
                    return nb::cast(edi::PeakProfileTypeEnum::TOF_JORGENSEN_VON_DREELE);
                }
                for (const edi::PeakProfileTypeEnum profile :
                     {edi::PeakProfileTypeEnum::CWL_GAUSSIAN,
                      edi::PeakProfileTypeEnum::CWL_LORENTZIAN,
                      edi::PeakProfileTypeEnum::CWL_PSEUDO_VOIGT,
                      edi::PeakProfileTypeEnum::CWL_PSEUDO_VOIGT_BERAR_BALDINOZZI,
                      edi::PeakProfileTypeEnum::CWL_TCH_PSEUDO_VOIGT,
                      edi::PeakProfileTypeEnum::CWL_TCH_PSEUDO_VOIGT_FCJ,
                      edi::PeakProfileTypeEnum::TOF_PSEUDO_VOIGT}) {
                    if (stored == edi::token(profile)) {
                        return nb::cast(profile);
                    }
                }
                return nb::cast(stored);
            },
            [](edi::views::PeakNode& self, nb::object value) {
                // The selector accepts any REGISTERED token (seam 20 / I15 — registration-live),
                // the enum, or None (presence-tracked); an unknown token refuses fail-closed.
                // Every switch reshapes the block to the slots the new profile carries, as the
                // app's select_peak_profile does. The beam mode is not checked here: it may be
                // declared after the type, and the loader refuses a contradiction.
                edi::PeakBase& peak = self.experiment->peak;
                if (!value || value.is_none()) {
                    // No type: the beam mode's default, whose slots the block takes as any switch.
                    peak.type = std::nullopt;
                    edi::conform_peak_slots(peak, edi::effective_peak_type(*self.experiment));
                    return;
                }
                if (nb::isinstance<nb::str>(value)) {
                    const std::string token = nb::cast<std::string>(value);
                    if (!edi::peak_type_known(token)) {
                        throw std::invalid_argument(
                            "peak type '" + token +
                            "' is neither a shipped profile token nor a registered extension "
                            "(register it via PeakFactory.register)");
                    }
                    peak.type = token;
                    edi::conform_peak_slots(peak, token);
                    return;
                }
                const std::string token(edi::token(nb::cast<edi::PeakProfileTypeEnum>(value)));
                peak.type = token;
                edi::conform_peak_slots(peak, token);
            },
            nb::for_setter(nb::arg("value").none()))
        .def_prop_rw(
            "cutoff_fwhm", [](edi::views::PeakNode& self) { return self.experiment->peak.cutoff_fwhm; },
            [](edi::views::PeakNode& self, double value) { self.experiment->peak.cutoff_fwhm = value; });

    nb::class_<edi::views::TofJorgensen, edi::views::PeakNode> tof_jorgensen(m, "TofJorgensen");
    tof_jorgensen.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_parameter_field(tof_jorgensen, "rise_alpha_0", &edi::PeakBase::rise_alpha_0);
    def_view_parameter_field(tof_jorgensen, "rise_alpha_1", &edi::PeakBase::rise_alpha_1);
    def_view_parameter_field(tof_jorgensen, "decay_beta_0", &edi::PeakBase::decay_beta_0);
    def_view_parameter_field(tof_jorgensen, "decay_beta_1", &edi::PeakBase::decay_beta_1);
    def_view_parameter_field(tof_jorgensen, "broad_gauss_sigma_0", &edi::PeakBase::broad_gauss_sigma_0);
    def_view_parameter_field(tof_jorgensen, "broad_gauss_sigma_1", &edi::PeakBase::broad_gauss_sigma_1);
    def_view_parameter_field(tof_jorgensen, "broad_gauss_sigma_2", &edi::PeakBase::broad_gauss_sigma_2);
    def_view_parameter_field(tof_jorgensen, "broad_gauss_size", &edi::PeakBase::broad_gauss_size);
    def_view_parameter_field(tof_jorgensen, "broad_gauss_strain", &edi::PeakBase::broad_gauss_strain);

    nb::class_<edi::views::TofJorgensenVonDreele, edi::views::TofJorgensen> tof_jorgensen_von_dreele(
        m, "TofJorgensenVonDreele");
    tof_jorgensen_von_dreele.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_parameter_field(tof_jorgensen_von_dreele, "broad_lorentz_gamma_0",
                             &edi::PeakBase::broad_lorentz_gamma_0);
    def_view_parameter_field(tof_jorgensen_von_dreele, "broad_lorentz_gamma_1",
                             &edi::PeakBase::broad_lorentz_gamma_1);
    def_view_parameter_field(tof_jorgensen_von_dreele, "broad_lorentz_gamma_2",
                             &edi::PeakBase::broad_lorentz_gamma_2);
    def_view_parameter_field(tof_jorgensen_von_dreele, "broad_lorentz_size",
                             &edi::PeakBase::broad_lorentz_size);
    def_view_parameter_field(tof_jorgensen_von_dreele, "broad_lorentz_strain",
                             &edi::PeakBase::broad_lorentz_strain);

    // The constant-wavelength profiles, each with only its own members: the
    // Caglioti U, V, W on every one, then the TCH X, Y or the pseudo-Voigt mixing, then the
    // asymmetry coefficients. The TOF pseudo-Voigt follows.
    const auto def_caglioti = [](auto& cls) {
        def_view_optional_parameter_field(cls, "broad_gauss_u", &edi::PeakBase::broad_gauss_u,
                                          edi::spec::peak_broad_gauss_u);
        def_view_optional_parameter_field(cls, "broad_gauss_v", &edi::PeakBase::broad_gauss_v,
                                          edi::spec::peak_broad_gauss_v);
        def_view_optional_parameter_field(cls, "broad_gauss_w", &edi::PeakBase::broad_gauss_w,
                                          edi::spec::peak_broad_gauss_w);
    };
    const auto def_tch = [&def_caglioti](auto& cls) {
        def_caglioti(cls);
        def_view_optional_parameter_field(cls, "broad_lorentz_x", &edi::PeakBase::broad_lorentz_x,
                                          edi::spec::peak_broad_lorentz_x);
        def_view_optional_parameter_field(cls, "broad_lorentz_y", &edi::PeakBase::broad_lorentz_y,
                                          edi::spec::peak_broad_lorentz_y);
    };
    const auto def_pseudo_voigt = [&def_caglioti](auto& cls) {
        def_caglioti(cls);
        def_view_optional_parameter_field(cls, "mixing_eta_0", &edi::PeakBase::mixing_eta_0,
                                          edi::spec::peak_mixing_eta_0);
        def_view_optional_parameter_field(cls, "mixing_eta_1", &edi::PeakBase::mixing_eta_1,
                                          edi::spec::peak_mixing_eta_1);
    };
    nb::class_<edi::views::CwlGaussian, edi::views::PeakNode> cwl_gaussian(m, "CwlGaussian");
    cwl_gaussian.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_caglioti(cwl_gaussian);
    nb::class_<edi::views::CwlLorentzian, edi::views::PeakNode> cwl_lorentzian(m, "CwlLorentzian");
    cwl_lorentzian.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_caglioti(cwl_lorentzian);
    nb::class_<edi::views::CwlPseudoVoigt, edi::views::PeakNode> cwl_pseudo_voigt(m, "CwlPseudoVoigt");
    cwl_pseudo_voigt.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_pseudo_voigt(cwl_pseudo_voigt);
    nb::class_<edi::views::CwlTchPseudoVoigt, edi::views::PeakNode> cwl_tch_pseudo_voigt(
        m, "CwlTchPseudoVoigt");
    cwl_tch_pseudo_voigt.def(nb::init<edi::ExperimentBase*>(), "experiment"_a,
                             nb::keep_alive<1, 2>());
    def_tch(cwl_tch_pseudo_voigt);
    nb::class_<edi::views::CwlTchPseudoVoigtFcj, edi::views::PeakNode> cwl_tch_pseudo_voigt_fcj(
        m, "CwlTchPseudoVoigtFcj");
    cwl_tch_pseudo_voigt_fcj.def(nb::init<edi::ExperimentBase*>(), "experiment"_a,
                                 nb::keep_alive<1, 2>());
    def_tch(cwl_tch_pseudo_voigt_fcj);
    def_view_optional_parameter_field(cwl_tch_pseudo_voigt_fcj, "asym_fcj_1",
                                      &edi::PeakBase::asym_fcj_1, edi::spec::peak_asym_fcj_1);
    def_view_optional_parameter_field(cwl_tch_pseudo_voigt_fcj, "asym_fcj_2",
                                      &edi::PeakBase::asym_fcj_2, edi::spec::peak_asym_fcj_2);

    nb::class_<edi::views::CwlPseudoVoigtBerarBaldinozzi, edi::views::PeakNode> cwl_beba(
        m, "CwlPseudoVoigtBerarBaldinozzi");
    cwl_beba.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_pseudo_voigt(cwl_beba);
    def_view_optional_parameter_field(cwl_beba, "asym_beba_a0", &edi::PeakBase::asym_beba_a0,
                                      edi::spec::peak_asym_beba_a0);
    def_view_optional_parameter_field(cwl_beba, "asym_beba_b0", &edi::PeakBase::asym_beba_b0,
                                      edi::spec::peak_asym_beba_b0);
    def_view_optional_parameter_field(cwl_beba, "asym_beba_a1", &edi::PeakBase::asym_beba_a1,
                                      edi::spec::peak_asym_beba_a1);
    def_view_optional_parameter_field(cwl_beba, "asym_beba_b1", &edi::PeakBase::asym_beba_b1,
                                      edi::spec::peak_asym_beba_b1);
    def_view_optional_parameter_field(cwl_beba, "asym_beba_limit", &edi::PeakBase::asym_beba_limit,
                                      edi::spec::peak_asym_beba_limit);

    nb::class_<edi::views::TofPseudoVoigt, edi::views::PeakNode> tof_pseudo_voigt(
        m, "TofPseudoVoigt");
    tof_pseudo_voigt.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_parameter_field(tof_pseudo_voigt, "broad_gauss_sigma_0", &edi::PeakBase::broad_gauss_sigma_0);
    def_view_parameter_field(tof_pseudo_voigt, "broad_gauss_sigma_1", &edi::PeakBase::broad_gauss_sigma_1);
    def_view_parameter_field(tof_pseudo_voigt, "broad_gauss_sigma_2", &edi::PeakBase::broad_gauss_sigma_2);
    def_view_parameter_field(tof_pseudo_voigt, "broad_gauss_size", &edi::PeakBase::broad_gauss_size);
    def_view_parameter_field(tof_pseudo_voigt, "broad_gauss_strain", &edi::PeakBase::broad_gauss_strain);
    def_view_parameter_field(tof_pseudo_voigt, "broad_lorentz_gamma_0",
                             &edi::PeakBase::broad_lorentz_gamma_0);
    def_view_parameter_field(tof_pseudo_voigt, "broad_lorentz_gamma_1",
                             &edi::PeakBase::broad_lorentz_gamma_1);
    def_view_parameter_field(tof_pseudo_voigt, "broad_lorentz_gamma_2",
                             &edi::PeakBase::broad_lorentz_gamma_2);
    def_view_parameter_field(tof_pseudo_voigt, "broad_lorentz_size", &edi::PeakBase::broad_lorentz_size);
    def_view_parameter_field(tof_pseudo_voigt, "broad_lorentz_strain",
                             &edi::PeakBase::broad_lorentz_strain);

    // The instrument category: the d<->TOF calibration + bank take-off angle, CW pair
    // presence-tracked.
    nb::class_<edi::views::InstrumentNode> instrument(m, "InstrumentBase");
    instrument.def("__setattr__", renewing_setattr<edi::views::InstrumentNode>({}, renew_storage), nb::arg("name"), nb::arg("value").none());

    nb::class_<edi::views::CwlInstrumentBase, edi::views::InstrumentNode>(m, "CwlInstrumentBase");
    nb::class_<edi::views::CwlPdInstrumentBase, edi::views::CwlInstrumentBase>(
        m, "CwlPdInstrumentBase");

    nb::class_<edi::views::TofPdInstrument, edi::views::InstrumentNode> tof_pd_instrument(
        m, "TofPdInstrument");
    tof_pd_instrument.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_parameter_field(tof_pd_instrument, "setup_twotheta_bank",
                             &edi::InstrumentBase::setup_twotheta_bank);
    def_view_parameter_field(tof_pd_instrument, "calib_d_to_tof_offset",
                             &edi::InstrumentBase::calib_d_to_tof_offset);
    def_view_parameter_field(tof_pd_instrument, "calib_d_to_tof_linear",
                             &edi::InstrumentBase::calib_d_to_tof_linear);
    def_view_parameter_field(tof_pd_instrument, "calib_d_to_tof_quadratic",
                             &edi::InstrumentBase::calib_d_to_tof_quadratic);
    def_view_parameter_field(tof_pd_instrument, "calib_d_to_tof_reciprocal",
                             &edi::InstrumentBase::calib_d_to_tof_reciprocal);

    nb::class_<edi::views::CwlPdNeutronInstrument, edi::views::CwlPdInstrumentBase>
        cwl_pd_neutron_instrument(m, "CwlPdNeutronInstrument");
    cwl_pd_neutron_instrument.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_optional_parameter_field(cwl_pd_neutron_instrument, "setup_wavelength",
                                      &edi::InstrumentBase::setup_wavelength,
                                      edi::spec::instrument_wavelength);
    def_view_optional_parameter_field(cwl_pd_neutron_instrument, "calib_twotheta_offset",
                                      &edi::InstrumentBase::calib_twotheta_offset,
                                      edi::spec::instrument_twotheta_offset);
    def_view_optional_parameter_field(cwl_pd_neutron_instrument, "calib_sample_displacement",
                                      &edi::InstrumentBase::calib_sample_displacement,
                                      edi::spec::instrument_sample_displacement);
    def_view_optional_parameter_field(cwl_pd_neutron_instrument, "calib_sample_transparency",
                                      &edi::InstrumentBase::calib_sample_transparency,
                                      edi::spec::instrument_sample_transparency);

    // The CW X-ray instrument — the same CW slots as the neutron one; adds the monochromator
    // polarization pair, X-ray only.
    nb::class_<edi::views::CwlPdXrayInstrument, edi::views::CwlPdInstrumentBase>
        cwl_pd_xray_instrument(m, "CwlPdXrayInstrument");
    cwl_pd_xray_instrument.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_optional_parameter_field(cwl_pd_xray_instrument, "setup_wavelength",
                                      &edi::InstrumentBase::setup_wavelength,
                                      edi::spec::instrument_wavelength);
    def_view_optional_parameter_field(cwl_pd_xray_instrument, "calib_twotheta_offset",
                                      &edi::InstrumentBase::calib_twotheta_offset,
                                      edi::spec::instrument_twotheta_offset);
    def_view_optional_parameter_field(cwl_pd_xray_instrument, "calib_sample_displacement",
                                      &edi::InstrumentBase::calib_sample_displacement,
                                      edi::spec::instrument_sample_displacement);
    def_view_optional_parameter_field(cwl_pd_xray_instrument, "calib_sample_transparency",
                                      &edi::InstrumentBase::calib_sample_transparency,
                                      edi::spec::instrument_sample_transparency);
    def_view_optional_parameter_field(cwl_pd_xray_instrument, "setup_polarization_coefficient",
                                      &edi::InstrumentBase::setup_polarization_coefficient,
                                      edi::spec::instrument_polarization_coefficient);
    def_view_optional_parameter_field(cwl_pd_xray_instrument, "setup_monochromator_twotheta",
                                      &edi::InstrumentBase::setup_monochromator_twotheta,
                                      edi::spec::instrument_monochromator_twotheta);

    // One linked structure (phase): the structure it names, its scale and whether it takes part.
    nb::class_<edi::LinkedStructure> linked_structure(m, "LinkedStructure");
    linked_structure.def("__setattr__", renewing_setattr<edi::LinkedStructure>({}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    linked_structure.def(nb::new_([]() { return std::make_shared<edi::LinkedStructure>(); }))
        // ADR-0016: assigning is a rename the owning experiment admits.
        .def_prop_rw(
            "structure_id", [](const edi::LinkedStructure& self) { return self.structure_id.value(); },
            [](edi::LinkedStructure& self, std::string value) { self.structure_id = std::move(value); })
        .def_prop_rw(
            "enabled", [](const edi::LinkedStructure& self) { return self.enabled.get(); },
            [](edi::LinkedStructure& self, bool value) { self.enabled = value; },
            "Whether the phase takes part: a disabled link is kept and saved, but neither calculated "
            "nor fitted.");
    def_parameter_field(linked_structure, "scale", &edi::LinkedStructure::scale);

    // The experiment's linked structures (phases), keyed by structure_id (R15).
    nb::class_<edi::views::LinkedStructuresView> linked_structures_view(
        m, "LinkedStructures",
        "Live keyed collection of an experiment's linked structures (key: structure_id).");
    nb::class_<edi::views::LinkedStructuresIter> linked_structures_iter(m, "_LinkedStructuresIterator");
    def_keyed_collection<edi::views::LinkedStructuresView, edi::views::LinkedStructuresIter, edi::LinkedStructure>(
        linked_structures_view, linked_structures_iter);
    linked_structures_view.def(
        "create",
        [](edi::views::LinkedStructuresView& self, nb::kwargs kwargs) {
            // Upstream CategoryCollection.create, as AtomSites.create.
            auto built = std::make_shared<edi::LinkedStructure>();
            nb::object obj = nb::cast(built);
            for (auto kv : kwargs) {
                nb::setattr(obj, kv.first, kv.second);
            }
            const std::string key = built->structure_id;
            self.set_item(key, std::move(built));
        },
        "Link a structure from keyword attributes (structure_id, scale, enabled) and add it.");

    // The absorption category — the FullProf ABSCOR pair, presence-tracked (parity doc records
    // why the spellings stay).
    nb::class_<edi::views::AbsorptionNode> absorption(m, "AbsorptionBase");
    absorption.def("__setattr__", renewing_setattr<edi::views::AbsorptionNode>({}, renew_storage), nb::arg("name"), nb::arg("value").none());
    absorption.def_prop_rw(
        "type", [](edi::views::AbsorptionNode& self) { return self.storage().type; },
        [](edi::views::AbsorptionNode& self, std::optional<std::string> value) {
            // Review-8 F4: mutation goes through the ruled family contract — none clears the
            // family body, a typed token initialises it, anything else refuses. None spells
            // the loader's absent-means-none state. The vocabulary is beam-scoped exactly as
            // at the loader — a CW experiment spells none/cylinder-hewat/ cylinder-lobanov
            // (the mu_r body); a TOF one none/cylinder (the ABSCOR pair), with the
            // "cylinder-hewat" inventory token mapping to its TOF file token. The rule is
            // edi::select_absorption's, on crysta's own
            // vocabulary (the adapter asks it); nothing is listed or mapped here.
            edi::select_absorption(*self.experiment, value.value_or("none"));
        });

    nb::class_<edi::views::CylinderHewatAbsorption, edi::views::AbsorptionNode>
        cylinder_hewat_absorption(m, "CylinderHewatAbsorption");
    cylinder_hewat_absorption.def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());
    def_view_optional_parameter_field(cylinder_hewat_absorption, "abscor1",
                                      &edi::AbsorptionBase::abscor1,
                                      edi::spec::absorption_abscor1);
    def_view_optional_parameter_field(cylinder_hewat_absorption, "abscor2",
                                      &edi::AbsorptionBase::abscor2,
                                      edi::spec::absorption_abscor2);
    // The CW face of the same lens — muR = mu * R (cylinder radius) at the reflection's
    // Bragg theta, beside the TOF pair on the one cylinder-Hewat node (crysta's D9/R46
    // shape); each member resolves against the experiment's own family block.
    def_view_optional_parameter_field(cylinder_hewat_absorption, "mu_r",
                                      &edi::AbsorptionBase::mu_r,
                                      edi::spec::absorption_mu_r);

    // The Lobanov concrete is bound and registry-seeded so the getter can return a loaded
    // built-in and the factory can enumerate and construct it — but it is NOT re-exported in
    // edi.__all__: crysta demonstrates the shape (internal-but-correct until a follow-up
    // declares the public pair in both products).
    nb::class_<edi::views::CylinderLobanovAbsorption, edi::views::AbsorptionNode>
        cylinder_lobanov_absorption(m, "CylinderLobanovAbsorption");
    cylinder_lobanov_absorption.def(nb::init<edi::ExperimentBase*>(), "experiment"_a,
                                    nb::keep_alive<1, 2>());
    def_view_optional_parameter_field(cylinder_lobanov_absorption, "mu_r",
                                      &edi::AbsorptionBase::mu_r,
                                      edi::spec::absorption_mu_r);

    nb::class_<edi::views::NoAbsorption, edi::views::AbsorptionNode>(m, "NoAbsorption")
        .def(nb::init<edi::ExperimentBase*>(), "experiment"_a, nb::keep_alive<1, 2>());

    def_parameters(peak);
    def_parameters(instrument);
    def_parameters(linked_structure);
    def_parameters(absorption);

    nb::class_<edi::ExperimentBase> experiment(m, "ExperimentBase");
    experiment.def("__setattr__", renewing_setattr<edi::ExperimentBase>({"dataset_weight"}, renew_epoch), nb::arg("name"), nb::arg("value").none());
    def_parameter_walks(experiment);
    experiment
        .def_prop_rw(  // A rename the owning project admits
            "name", [](const edi::ExperimentBase& self) { return self.name.value(); },
            [](edi::ExperimentBase& self, std::string value) { self.name = std::move(value); })
        .def_rw("experiment_type", &edi::ExperimentBase::experiment_type)
        .def_prop_rw(
            "linked_structure",
            [](edi::ExperimentBase& self) {
                self.linked_structure();  // refuses a bank of no or several links
                return self.linked_structures.front();
            },
            [](edi::ExperimentBase& self, const edi::LinkedStructure& value) {
                // The single-phase shortcut: the one link takes the value's fields.
                edi::LinkedStructure& only = self.linked_structure();
                only.structure_id = value.structure_id.value();
                only.scale = value.scale;
                only.enabled = value.enabled.get();
            },
            "The one linked structure (the single-phase shortcut); refused when the experiment links several.")
        .def_prop_ro(
            "linked_structures",
            [](edi::ExperimentBase& self) {
                return edi::views::LinkedStructuresView{&self, &edi::ExperimentBase::linked_structures,
                                                        &edi::LinkedStructure::structure_id};
            },
            nb::keep_alive<0, 1>(), "The linked structures (phases), keyed by structure_id.")
        .def_rw("dataset_weight", &edi::ExperimentBase::dataset_weight);

    // The abstract intermediates: the powder base homes the pd-shared members exactly where upstream
    // places them; the single-crystal base exists and refuses construction until its physics arrives.
    nb::class_<edi::PdExperimentBase, edi::ExperimentBase> pd_experiment_base(
        m, "PdExperimentBase");
    pd_experiment_base
        .def_prop_ro(
            "peak",
            [](edi::ExperimentBase& self) -> nb::object {
                nb::object cls = registry_lookup(*g_peak_registry, peak_token_of(self));
                return cls(nb::cast(&self, nb::rv_policy::reference));
            },
            nb::keep_alive<0, 1>())
        .def_prop_rw(
            "data",
            [](nb::handle self_object) -> nb::object {
                edi::ExperimentBase& self = nb::cast<edi::ExperimentBase&>(self_object);
                if (!self.data) {
                    return nb::none();
                }
                // The leaf matching the engaged axis, as a copy. Its computed columns only while
                // they describe the experiment as it is now; and linked to this experiment's node,
                // so a write through it reaches the node, as diffraction-lib's live category does
                // (PdDataBase::write_column). The object keeps the experiment alive, so the link
                // never dangles.
                edi::PdDataBase node = *self.data;
                if (!self.computed_current()) {
                    node.clear_computed();
                }
                const bool cwl = node.two_theta.has_value();
                nb::object out = cwl ? nb::cast(edi::PdCwlData(std::move(node)))
                                     : nb::cast(edi::PdTofData(std::move(node)));
                nb::cast<edi::PdDataBase&>(out).source.link(self, self.data->epoch.value());
                nb::detail::keep_alive(out.ptr(), self_object.ptr());
                return out;
            },
            [](edi::ExperimentBase& self, std::optional<edi::PdDataBase> incoming) {
                // A replaced data node has not been calculated here, so neither its computed
                // columns (another experiment's, when copied from one) nor this experiment's
                // reflections survive the replacement.
                if (incoming) {
                    incoming->clear_computed();
                }
                self.data = std::move(incoming);
                self.refln.clear();
            })
        // The reflections crysta computed, as the leaf matching the beam mode. The getter itself
        // never calculates; a column read does (live_refln).
        .def_prop_ro("refln",
                     [](nb::handle self_object) -> nb::object {
                         // Linked to this experiment and kept alive by it, so a retained object is
                         // read against the experiment as it is then.
                         edi::ExperimentBase& self = nb::cast<edi::ExperimentBase&>(self_object);
                         edi::PowderReflnDataBase rows =
                             self.computed_current() ? self.refln : edi::PowderReflnDataBase{};
                         nb::object out =
                             self.effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH
                                 ? nb::cast(edi::PowderCwlReflnData(std::move(rows)))
                                 : nb::cast(edi::PowderTofReflnData(std::move(rows)));
                         nb::cast<edi::PowderReflnDataBase&>(out).source.link(self, 0);
                         nb::detail::keep_alive(out.ptr(), self_object.ptr());
                         return out;
                     })
        // Immutable tuple-of-pairs out — no mutable copy can exist; the replacement setter
        // stays (ExcludedRegion items are D8's own task).
        .def_prop_rw(
            "excluded_regions",
            [](const edi::ExperimentBase& self) {
                nb::list out;
                for (const auto& region : self.excluded_regions) {
                    out.append(nb::make_tuple(region->first.get(), region->second.get()));
                }
                return nb::tuple(out);
            },
            [](edi::ExperimentBase& self, std::vector<std::pair<double, double>> regions) {
                self.excluded_regions = edi::excluded_region_rows(regions);
            });

    nb::class_<edi::ScExperimentBase, edi::ExperimentBase>(m, "ScExperimentBase");

    // The concrete experiment leaf: the loader builds it and Python constructs it — the bases above
    // carry the shared surface, the leaf its own categories.
    nb::class_<edi::BraggPdExperiment, edi::PdExperimentBase>(m, "BraggPdExperiment",
                                                              nb::is_weak_referenceable())
        .def(nb::new_([]() { return std::make_shared<edi::BraggPdExperiment>(); }))
        .def_prop_ro(
            "instrument",
            [](edi::ExperimentBase& self) -> nb::object {
                const bool cw = self.effective_beam_mode() ==
                                edi::BeamModeEnum::CONSTANT_WAVELENGTH;
                const bool xray =
                    self.experiment_type.effective_radiation_probe() == edi::RadiationProbeEnum::XRAY;
                nb::object cls = registry_lookup(
                    *g_instrument_registry,
                    !cw ? "tof-pd" : xray ? "cwl-pd-xray" : "cwl-pd-neutron");
                return cls(nb::cast(&self, nb::rv_policy::reference));
            },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "preferred_orientation",
            [](edi::ExperimentBase& self) {
                return edi::views::PrefOrientsView{&self,
                                                   &edi::ExperimentBase::preferred_orientation,
                                                   &edi::PrefOrient::structure_id};
            },
            nb::keep_alive<0, 1>(),
            "The per-structure March-Dollase preferred-orientation rows.")
        .def_prop_ro(
            "absorption",
            [](edi::ExperimentBase& self) -> nb::object {
                const edi::AbsorptionBase& a = self.absorption;
                std::string token =
                    a.type ? *a.type
                           : ((a.abscor1 || a.abscor2 || a.mu_r) ? std::string("cylinder-hewat")
                                                                 : std::string("none"));
                if (a.type) {
                    // The declared file spelling classifies as its registry token, which is
                    // crysta's mapping.
                    token = edi::absorption_registry_token(self.effective_beam_mode(), token);
                }
                nb::object cls = registry_lookup(*g_absorption_registry, token);
                return cls(nb::cast(&self, nb::rv_policy::reference));
            },
            nb::keep_alive<0, 1>())
        // Positional live view (R12: id -> list position, not a keyed category); the
        // replacement setter stays the population verb until background plane.
        .def_prop_rw(
            "background",
            [](edi::ExperimentBase& self) { return edi::views::BackgroundView{&self}; },
            [](edi::ExperimentBase& self,
               std::vector<std::shared_ptr<edi::LineSegment>> points) {
                // Points are a line-segment model's rows only.
                if (self.background_type != "line-segment") {
                    throw std::invalid_argument("a " + self.background_type +
                                                " background holds terms, not line-segment points; "
                                                "set background_type first");
                }
                self.background.assign(std::move(points));
            },
            nb::keep_alive<0, 1>())
        // The declared background model — its selector, its constants and its term rows,
        // the fields the declaration owns.
        .def_prop_rw(
            "background_type", [](const edi::ExperimentBase& self) { return self.background_type; },
            [](edi::ExperimentBase& self, const std::string& token) {
                const std::vector<std::string> supported = edi::supported_background_types();
                if (std::find(supported.begin(), supported.end(), token) == supported.end()) {
                    throw std::invalid_argument("unknown _background.type '" + token + "'");
                }
                self.background_type = token;
            },
            "The declared background model: line-segment, chebyshev or polynomial.")
        .def_prop_rw(
            "background_origin", [](const edi::ExperimentBase& self) { return self.background_origin; },
            [](edi::ExperimentBase& self, std::optional<double> value) { self.background_origin = value; },
            "The polynomial background's origin (FullProf Bkpos), or None.")
        .def_prop_rw(
            "background_x_min", [](const edi::ExperimentBase& self) { return self.background_x_min; },
            [](edi::ExperimentBase& self, std::optional<double> value) { self.background_x_min = value; },
            "The lower end of the Chebyshev background's domain, or None.")
        .def_prop_rw(
            "background_x_max", [](const edi::ExperimentBase& self) { return self.background_x_max; },
            [](edi::ExperimentBase& self, std::optional<double> value) { self.background_x_max = value; },
            "The upper end of the Chebyshev background's domain, or None.")
        .def_prop_rw(
            "background_terms",
            [](edi::ExperimentBase& self) {
                std::vector<std::shared_ptr<edi::PolynomialTerm>> out;
                for (const std::shared_ptr<edi::PolynomialTerm>& term : self.background_terms) {
                    out.push_back(term);
                }
                return out;
            },
            [](edi::ExperimentBase& self, std::vector<std::shared_ptr<edi::PolynomialTerm>> terms) {
                if (self.background_type == "line-segment") {
                    throw std::invalid_argument(
                        "a line-segment background holds points, not terms; set background_type first");
                }
                self.background_terms.assign(std::move(terms));
            },
            "The polynomial or Chebyshev background's term rows (order, coef).");

    // The family factories, public and registry-backed: `registry()` lists every selector token with
    // its class (None = reserved); `register()` is the Python extension seam for the view layer (edi's
    // own .edi grammar stays its loader's contract).
    nb::class_<edi::views::PeakFactory>(m, "PeakFactory")
        .def_static("supported_tags", [] { return active_tags(*g_peak_registry); })
        .def_static("default_tag", [] { return "tof-jorgensen"; })
        .def_static(
            "show_supported",
            [] {
                const nb::object print = nb::module_::import_("builtins").attr("print");
                print("Supported peak types");
                for (nb::handle tag : active_tags(*g_peak_registry)) {
                    print("  " + nb::cast<std::string>(nb::str(tag)));
                }
            },
            "Print the supported peak types (diffraction-lib FactoryBase.show_supported — "
            "ruling absorb-ten-26).")
        .def_static(
            "create",
            [](const std::string& tag, nb::object experiment) {
                return factory_create(*g_peak_registry, tag, std::move(experiment));
            },
            "tag"_a = "tof-jorgensen", "experiment"_a = nb::none())
        .def_static(
            "create_default_for",
            [](const std::string& value, nb::object experiment) {
                const std::string tag = (value == "constant wavelength" || value == "cwl")
                                            ? "cwl-tch-pseudo-voigt"
                                            : "tof-jorgensen";
                return factory_create(*g_peak_registry, tag, std::move(experiment));
            },
            "value"_a, "experiment"_a = nb::none())
        .def_static("registry", [] { return copy_registry(*g_peak_registry); })
        .def_static(
            "register",
            [](nb::object token_or_cls, nb::object cls, const std::string& beam_mode) {
                std::string token;
                nb::object klass;
                if (cls.is_none()) {
                    klass = token_or_cls;
                    token = derive_registration_token(klass);
                } else {
                    token = nb::cast<std::string>(token_or_cls);
                    klass = cls;
                }
                (*g_peak_registry)[nb::str(token.c_str())] = klass;
                // seam 20 / I15: the loader's token map is registration-live (crysta parity).
                edi::register_peak_type(token, beam_mode == "constant wavelength"
                                                   ? edi::BeamModeEnum::CONSTANT_WAVELENGTH
                                                   : edi::BeamModeEnum::TIME_OF_FLIGHT);
                return klass;
            },
            "token_or_cls"_a, "cls"_a = nb::none(), nb::kw_only(),
            "beam_mode"_a = "time-of-flight");

    nb::class_<edi::views::InstrumentFactory>(m, "InstrumentFactory")
        .def_static("supported_tags", [] { return active_tags(*g_instrument_registry); })
        .def_static("default_tag", [] { return "tof-pd"; })
        .def_static(
            "create",
            [](const std::string& tag, nb::object experiment) {
                return factory_create(*g_instrument_registry, tag, std::move(experiment));
            },
            "tag"_a = "tof-pd", "experiment"_a = nb::none())
        .def_static(
            "create_default_for",
            [](const std::string& value, nb::object experiment) {
                const bool cw = value == "constant wavelength" || value == "cwl";
                const bool xray = cw && !experiment.is_none() &&
                                  nb::cast<edi::ExperimentBase&>(experiment)
                                          .experiment_type.effective_radiation_probe() ==
                                      edi::RadiationProbeEnum::XRAY;
                const std::string tag = !cw ? "tof-pd" : xray ? "cwl-pd-xray" : "cwl-pd-neutron";
                return factory_create(*g_instrument_registry, tag, std::move(experiment));
            },
            "value"_a, "experiment"_a = nb::none())
        .def_static("registry", [] { return copy_registry(*g_instrument_registry); })
        .def_static(
            "register",
            [](nb::object token_or_cls, nb::object cls) {
                std::string token;
                nb::object klass;
                if (cls.is_none()) {
                    klass = token_or_cls;
                    token = derive_registration_token(klass);
                } else {
                    token = nb::cast<std::string>(token_or_cls);
                    klass = cls;
                }
                (*g_instrument_registry)[nb::str(token.c_str())] = klass;
                return klass;
            },
            "token_or_cls"_a, "cls"_a = nb::none());

    nb::class_<edi::views::AbsorptionFactory>(m, "AbsorptionFactory")
        .def_static("supported_tags", [] { return active_tags(*g_absorption_registry); })
        .def_static("default_tag", [] { return "none"; })
        .def_static(
            "create",
            [](const std::string& tag, nb::object experiment) {
                nb::object node =
                    factory_create(*g_absorption_registry, tag, std::move(experiment));
                // The selection is imprinted into the model AS THE RULED FILE TOKEN and
                // through the ruled family contract: selecting none CLEARS the coefficient
                // body, selecting cylinder INITIALISES a missing coefficient to the owner's
                // default — a typed family's parameters exist iff the type says so, on
                // mutation exactly as on load. "cylinder-hewat" persists as "cylinder"; the
                // classify view maps it back to the inventory class.
                edi::views::AbsorptionNode& view = nb::cast<edi::views::AbsorptionNode&>(node);
                const bool cw = view.experiment->effective_beam_mode() ==
                                edi::BeamModeEnum::CONSTANT_WAVELENGTH;
                // On a CW experiment "cylinder-hewat" IS the ruled file token (the mu_r
                // body); the inventory→file mapping is TOF-only. Review-4: the factory
                // enforces the same beam-scoped vocabulary as the type setter and the loader,
                // so a construction can never imprint a family the model's own loaders would
                // refuse (TOF has no Lobanov spelling).
                std::string family_token = tag;
                if (!cw && tag == "cylinder-hewat") {
                    family_token = "cylinder";
                }
                if (!cw && family_token != "none" && family_token != "cylinder") {
                    throw std::invalid_argument(
                        "unknown TOF _absorption.type '" + tag +
                        "' (the registry spells none or cylinder-hewat)");
                }
                edi::apply_absorption_family(view.storage(), family_token);
                return node;
            },
            "tag"_a = "none", "experiment"_a = nb::none())
        .def_static(
            "create_default_for",
            [](const std::string& value, nb::object experiment) {
                (void)value;
                nb::object node =
                    factory_create(*g_absorption_registry, "none", std::move(experiment));
                edi::apply_absorption_family(
                    nb::cast<edi::views::AbsorptionNode&>(node).storage(), "none");
                return node;
            },
            "value"_a, "experiment"_a = nb::none())
        .def_static("registry", [] { return copy_registry(*g_absorption_registry); })
        .def_static(
            "register",
            [](nb::object token_or_cls, nb::object cls) {
                std::string token;
                nb::object klass;
                if (cls.is_none()) {
                    klass = token_or_cls;
                    token = derive_registration_token(klass);
                } else {
                    token = nb::cast<std::string>(token_or_cls);
                    klass = cls;
                }
                (*g_absorption_registry)[nb::str(token.c_str())] = klass;
                return klass;
            },
            "token_or_cls"_a, "cls"_a = nb::none());

    g_bragg_experiment_cls = new nb::object(m.attr("BraggPdExperiment"));
    g_peak_registry = new nb::object(nb::dict());
    (*g_peak_registry)["tof-jorgensen"] = m.attr("TofJorgensen");
    (*g_peak_registry)["tof-jorgensen-von-dreele"] = m.attr("TofJorgensenVonDreele");
    // The constant-wavelength profiles and the TOF pseudo-Voigt, each with its
    // class.
    (*g_peak_registry)["cwl-gaussian"] = m.attr("CwlGaussian");
    (*g_peak_registry)["cwl-lorentzian"] = m.attr("CwlLorentzian");
    (*g_peak_registry)["cwl-pseudo-voigt"] = m.attr("CwlPseudoVoigt");
    (*g_peak_registry)["cwl-pseudo-voigt-berar-baldinozzi"] =
        m.attr("CwlPseudoVoigtBerarBaldinozzi");
    (*g_peak_registry)["cwl-tch-pseudo-voigt"] = m.attr("CwlTchPseudoVoigt");
    (*g_peak_registry)["cwl-tch-pseudo-voigt-fcj"] = m.attr("CwlTchPseudoVoigtFcj");
    (*g_peak_registry)["tof-pseudo-voigt"] = m.attr("TofPseudoVoigt");
    g_instrument_registry = new nb::object(nb::dict());
    (*g_instrument_registry)["tof-pd"] = m.attr("TofPdInstrument");
    (*g_instrument_registry)["cwl-pd-neutron"] = m.attr("CwlPdNeutronInstrument");
    (*g_instrument_registry)["cwl-pd-xray"] = m.attr("CwlPdXrayInstrument");
    g_absorption_registry = new nb::object(nb::dict());
    (*g_absorption_registry)["cylinder-hewat"] = m.attr("CylinderHewatAbsorption");
    // The loaded built-in resolves — enumerable and constructible — while the class itself
    // stays out of edi.__all__ (internal, crysta's shape).
    (*g_absorption_registry)["cylinder-lobanov"] = m.attr("CylinderLobanovAbsorption");
    (*g_absorption_registry)["none"] = m.attr("NoAbsorption");

    // One bank's measured pattern: the axis is MODE-NAMED — construct with exactly one of
    // two_theta / time_of_flight (I13) — and `axis()` is the mode-agnostic accessor. Measured
    // data is not part of the persisted .edi model, so the caller supplies it.
    nb::class_<edi::PdDataBase>(m, "PdDataBase")
        .def("__setattr__", renewing_setattr<edi::PdDataBase>({}, [](edi::PdDataBase& data) { data.written = edi::detail::Epoch(); }), nb::arg("name"), nb::arg("value").none())
        .def("axis", [](const edi::PdDataBase& p) { return p.axis(); },
             "The engaged axis (two_theta or time_of_flight) — fails closed on none-or-both.")
        // A write reaches the experiment node the object came from.
        .def_prop_rw(
            "intensity_meas", [](const edi::PdDataBase& p) { return p.intensity_meas.get(); },
            [](edi::PdDataBase& p, std::vector<double> values) {
                p.write_column(&edi::PdDataBase::intensity_meas, std::move(values));
            })
        .def_prop_rw(
            "intensity_meas_su", [](const edi::PdDataBase& p) { return p.intensity_meas_su.get(); },
            [](edi::PdDataBase& p, std::vector<double> values) {
                p.write_column(&edi::PdDataBase::intensity_meas_su, std::move(values));
            })
        // The calculated pattern lands in the model (written by Project.calculate).
        // Diffraction-lib's computed `_data` columns, crysta's published buffers as read-only
        // arrays; NaN on an excluded row. Read lazily (live_data).
        .def_prop_ro("d_spacing",
                     [live_data](const edi::PdDataBase& p) {
                         return readonly_array(live_data(p).d_spacing);
                     })
        .def_prop_ro("intensity_calc",
                     [live_data](const edi::PdDataBase& p) {
                         return readonly_array(live_data(p).intensity_calc);
                     })
        .def_prop_ro("intensity_bkg",
                     [live_data](const edi::PdDataBase& p) {
                         return readonly_array(live_data(p).intensity_bkg);
                     })
        .def_prop_ro("calc_status",
                     [live_data](const edi::PdDataBase& p) { return text_tuple(live_data(p).calc_status); });

    // The data leaves: the axis member lives on the concrete class, upstream's schema; construction
    // takes exactly that axis.
    nb::class_<edi::PdCwlData, edi::PdDataBase>(m, "PdCwlData")
        .def(
            "__init__",
            [](edi::PdCwlData* self, std::vector<double> two_theta,
               std::vector<double> intensity_meas, std::vector<double> intensity_meas_su) {
                new (self) edi::PdCwlData();
                self->two_theta = std::move(two_theta);
                self->intensity_meas = std::move(intensity_meas);
                self->intensity_meas_su = std::move(intensity_meas_su);
                self->axis();  // I13: exactly one engaged axis, checked at construction
            },
            nb::kw_only(), "two_theta"_a, "intensity_meas"_a, "intensity_meas_su"_a)
        .def_prop_rw(
            "two_theta", [](const edi::PdDataBase& p) { return p.two_theta.get(); },
            [](edi::PdDataBase& p, std::optional<std::vector<double>> values) {
                p.write_axis(&edi::PdDataBase::two_theta, std::move(values));
            });

    nb::class_<edi::PdTofData, edi::PdDataBase>(m, "PdTofData")
        .def(
            "__init__",
            [](edi::PdTofData* self, std::vector<double> time_of_flight,
               std::vector<double> intensity_meas, std::vector<double> intensity_meas_su) {
                new (self) edi::PdTofData();
                self->time_of_flight = std::move(time_of_flight);
                self->intensity_meas = std::move(intensity_meas);
                self->intensity_meas_su = std::move(intensity_meas_su);
                self->axis();  // I13: exactly one engaged axis, checked at construction
            },
            nb::kw_only(), "time_of_flight"_a, "intensity_meas"_a, "intensity_meas_su"_a)
        .def_prop_rw(
            "time_of_flight", [](const edi::PdDataBase& p) { return p.time_of_flight.get(); },
            [](edi::PdDataBase& p, std::optional<std::vector<double>> values) {
                p.write_axis(&edi::PdDataBase::time_of_flight, std::move(values));
            });

    // The reflections crysta computed, read-only by column (diffraction-lib `PowderReflnDataBase`
    // and its mode-named leaves). `id` is the row ordinal, as the saved loop spells it.
    nb::class_<edi::PowderReflnDataBase>(m, "PowderReflnDataBase")
        .def_prop_ro("id",
                     [live_refln](const edi::PowderReflnDataBase& r) {
                         nb::list out;
                         for (std::size_t row = 1; row <= live_refln(r).size(); ++row) {
                             out.append(std::to_string(row));
                         }
                         return nb::tuple(out);
                     })
        .def_prop_ro("structure_id",
                     [live_refln](const edi::PowderReflnDataBase& r) { return text_tuple(live_refln(r).structure_id); })
        .def_prop_ro("d_spacing",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).d_spacing); })
        .def_prop_ro("sin_theta_over_lambda",
                     [live_refln](const edi::PowderReflnDataBase& r) {
                         return readonly_array(live_refln(r).sin_theta_over_lambda);
                     })
        .def_prop_ro("index_h",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).index_h); })
        .def_prop_ro("index_k",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).index_k); })
        .def_prop_ro("index_l",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).index_l); })
        .def_prop_ro("f_calc",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).f_calc); })
        .def_prop_ro("f_squared_calc", [live_refln](const edi::PowderReflnDataBase& r) {
            return readonly_array(live_refln(r).f_squared_calc);
        });
    nb::class_<edi::PowderCwlReflnData, edi::PowderReflnDataBase>(m, "PowderCwlReflnData")
        .def_prop_ro("two_theta",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).position); });
    nb::class_<edi::PowderTofReflnData, edi::PowderReflnDataBase>(m, "PowderTofReflnData")
        .def_prop_ro("time_of_flight",
                     [live_refln](const edi::PowderReflnDataBase& r) { return readonly_array(live_refln(r).position); });

    // Whole-fit result: edi's own value type returned by Project.fit — no crysta type crosses the boundary.
    // `values`/`uncertainty` are label->number dicts (the fit's parameter identities). The reader's
    // unknown-tag policy, exposed so it can be CHECKED against the reference dictionary it was derived from
    // rather than trusted to stay in step with it.

    // The committed parameter-metadata table, enumerable for gates and the parity document
    // — one dict per Parameter-typed model field kind, sorted by (category, name).

    // One bank's post-fit metrics. Every field is the engine's own number, carried into edi's
    // value type — nothing on the Python side recomputes a metric. reporting types. edi's OWN, not
    // the engine's: the bindings are a thin marshaller over edi's core (ADR-0009) and the core's
    // public surface is engine-free (ADR-0003), so no crysta type crosses the `import edi`
    // boundary here any more than elsewhere.
    nb::enum_<edi::FitStatus>(m, "FitStatus")
        .value("DONE", edi::FitStatus::DONE)
        .value("MAX_ITER", edi::FitStatus::MAX_ITER)
        .value("NO_STEP", edi::FitStatus::NO_STEP)
        .value("CANCELLED", edi::FitStatus::CANCELLED)
        .value("ERROR", edi::FitStatus::ERROR)
        // The Python surface must be able to SAY unavailable, or a resumed scan's honest status
        // has nowhere to land and reverts to an invented one at the boundary.
        .value("UNAVAILABLE", edi::FitStatus::UNAVAILABLE)
        // A model input was written while the fit ran, so it published nothing.
        .value("SUPERSEDED", edi::FitStatus::SUPERSEDED);

    // One verbosity for both channels, so `--verbosity` means the same thing whichever `--report`
    // is chosen.
    nb::enum_<edi::VerbosityEnum>(m, "VerbosityEnum")
        .value("OFF", edi::VerbosityEnum::OFF)
        .value("COMPACT", edi::VerbosityEnum::COMPACT)
        .value("FULL", edi::VerbosityEnum::FULL);

    // Default-constructible with writable fields: a caller (and a conformance test) constructs
    // synthetic records to exercise the formatters on fixed values, independent of a live fit.
    // Reading them off a FitResultBase is unchanged.
    nb::class_<edi::IterationRecord>(m, "IterationRecord")
        .def(nb::init<>())
        .def_rw("iteration", &edi::IterationRecord::iteration)
        .def_rw("rwp", &edi::IterationRecord::rwp)
        .def_rw("reduced_chi_square", &edi::IterationRecord::reduced_chi_square);

    // The streaming preamble — the facts a live surface prints its header + pre-fit row from before
    // iteration 1. Delivered to `on_start`; edi-owned and adapter-local (never a crysta seam).
    nb::class_<edi::FitPreamble>(m, "FitPreamble")
        .def(nb::init<>())
        .def_rw("pre_fit", &edi::FitPreamble::pre_fit);

    // One completed scan file — the facts of its committed results.csv row, delivered to
    // `on_file_complete` after crysta's driver appended the row (numbers commit as produced).
    // Bound before ScanPreamble, which carries a list of them.
    nb::class_<edi::ScanFileRecord>(m, "ScanFileRecord")
        .def(nb::init<>())
        .def_rw("file_name", &edi::ScanFileRecord::file_name)
        .def_rw("converged", &edi::ScanFileRecord::converged)
        .def_rw("reduced_chi_square", &edi::ScanFileRecord::reduced_chi_square)
        .def_rw("iterations", &edi::ScanFileRecord::iterations);

    // The whole-scan preamble — the seam a progress surface takes its N from (never from
    // counting iteration restarts). Delivered to `on_scan_start` once, before the first file's
    // fit; `completed_rows` is every row already committed to results.csv, published as the
    // ROWS rather than counts over them so a resumed scan's names, χ² values and counts are
    // all folds over ONE population.
    nb::class_<edi::ScanPreamble>(m, "ScanPreamble")
        .def(nb::init<>())
        .def_rw("total_files", &edi::ScanPreamble::total_files)
        .def_rw("completed_rows", &edi::ScanPreamble::completed_rows);

    // Both formatters RETURN a string and print nothing: `import edi` + project.fit() must emit
    // nothing at all unless the caller asks, so choosing a stream is the caller's decision. The
    // machine record is the engine's emitter; the human view is edi's own, shared across surfaces.
    m.def("machine_report", &edi::machine_report, "project"_a, "outcome"_a, "verbosity"_a,
          "The machine record for this outcome, rendered by the shared crysta emitter.");
    m.def("error_report", &edi::error_report, "verbosity"_a,
          "The minimal machine failure record: no numeric rows, ever.");
    // Streaming seams (edi-owned presentation; the retired post-hoc report composed the same pieces so the live
    // and after-the-fact tables cannot drift).
    m.def("iteration_line", &edi::iteration_line, "record"_a, "previous_reduced_chi2"_a,
          "One per-iteration table row; `change` is computed against the previous reduced χ².");
    m.def("stream_header", &edi::stream_header, "preamble"_a, "project_name"_a,
          "The header line + iteration-table header + pre-fit starting row, from a FitPreamble.");
    m.def("summary_line", &edi::summary_line, "outcome"_a, "The trailing `done · …` summary line.");
    // Scan renderers: the core owns every line; a surface only chooses the emission mode (in
    // place on a TTY, one line per file otherwise) and supplies the injected-clock elapsed.
    m.def("scan_progress_line", &edi::scan_progress_line, "completed"_a,
          "total_files"_a.none() = nb::none(), "elapsed_seconds"_a, "measured_completed"_a,
          "ok_count"_a, "fail_count"_a, "file_name"_a, "reduced_chi_square"_a,
          "One scan progress line (bar · count · percent · elapsed · eta · ok · fail · file · "
          "χ²). With total_files None the line degrades to a bare count — no bar, percentage or "
          "eta; the eta is mean(elapsed over measured_completed) × remaining, labelled as the "
          "estimate it is; elapsed_seconds is the caller's injected-clock reading, never a "
          "wall-clock read here. measured_completed is how many of the completed files that "
          "reading covers (all of them on a fresh scan, only this call's on a resume) — it is "
          "required so the time basis is always stated, and below `completed` the elapsed group "
          "says `this run`.");
    m.def("scan_summary", &edi::scan_summary, "total_files"_a, "ok_count"_a, "fail_count"_a,
          "chi2_min"_a, "chi2_max"_a, "elapsed_seconds"_a, "measured_completed"_a,
          "The scan summary after the frozen progress line: failures are COUNTED, never listed "
          "(the per-file outcome is in analysis/results.csv). Every population "
          "quantity is the caller's fold over the scan's committed rows; measured_completed says "
          "how many completions "
          "elapsed_seconds covers, so a no-op resume (0) renders no duration at all and a "
          "partial one names its basis.");
    m.def("parameter_table", &edi::parameter_table, "outcome"_a,
          "The per-bank + refined-parameter block (the surface prints it only at full verbosity).");
    m.def("progress_report", &edi::progress_report, "record"_a,
          "The machine streamed record=progress for one iteration (crysta's shared emitter).");
    // The machine calc record, rendered by crysta's shared emitter so `python -m edi calc` and
    // `crysta <dir> calc` emit byte-comparable records by construction.
    m.def("_calc_report", &edi::calc_report, "n_points"_a, "checksum"_a, "elapsed_ms"_a,
          "verbosity"_a,
          "The machine record=calc for a forward calculation (crysta's shared emitter).");

    nb::class_<edi::BankMetric>(m, "BankMetric")
        .def_ro("name", &edi::BankMetric::name)
        .def_ro("n_points", &edi::BankMetric::n_points)
        .def_ro("rwp", &edi::BankMetric::rwp)
        .def_ro("chi_square", &edi::BankMetric::chi_square);

    nb::class_<edi::FitResultBase>(m, "FitResultBase")
        .def_ro("values", &edi::FitResultBase::values)
        .def_ro("uncertainty", &edi::FitResultBase::uncertainty)
        // Pre-fit value per identity path; shares its key set with `values`, so a caller can render
        // a start-vs-value change column without re-reading the project. Per-bank metrics:
        // populated for a joint refinement, EMPTY for a single-bank one, mirroring crysta, whose
        // single-file result carries no per-bank block.
        .def_ro("banks", &edi::FitResultBase::banks)
        .def_ro("rwp", &edi::FitResultBase::rwp)
        .def_ro("reduced_chi_square", &edi::FitResultBase::reduced_chi_square)
        .def_ro("iterations", &edi::FitResultBase::iterations)
        // The engine's work counters, as crysta's own Python result spells them — private,
        // compared by the crysta-vs-edi parity checks.
        .def_prop_ro("_folded",
                     [](const edi::FitResultBase& self) {
                         nb::list out;
                         for (const bool folded : self.reflections_folded) {
                             out.append(folded);
                         }
                         return nb::tuple(out);
                     })
        .def_ro("_structure_factor_evaluations",
                &edi::FitResultBase::structure_factor_evaluations)
        .def_ro("converged", &edi::FitResultBase::converged)
        .def_ro("status", &edi::FitResultBase::status)
        // The three cheap absorb projections of data already carried.
        .def_prop_ro(
            "success", [](const edi::FitResultBase& self) { return self.converged; },
            "Whether the fit succeeded (diffraction-lib FitResultBase.success).")
        .def_prop_ro(
            "result_kind", [](const edi::FitResultBase&) { return "deterministic"; },
            "Kind of the fit result (diffraction-lib FitResultKindEnum spelling).")
        .def_prop_ro(
            "fitting_time",
            [](const edi::FitResultBase& self) -> nb::object {
                if (self.elapsed_ms <= 0.0) {
                    return nb::none();
                }
                return nb::cast(self.elapsed_ms / 1000.0);
            },
            "Fitting time in seconds (diffraction-lib FitResultBase.fitting_time; None until a "
            "solve ran).");

    nb::class_<edi::LeastSquaresFitResult, edi::FitResultBase>(m, "LeastSquaresFitResult");

    nb::class_<edi::ProjectMetadata>(m, "ProjectMetadata")
        .def(nb::init<>())
        .def_prop_rw(
            "name", [](const edi::ProjectMetadata& self) { return self.name; },
            [](edi::ProjectMetadata& self, const std::string& value) {
                self.name = validated_project_name(value);
            },
            "The project name (validated: no path separators).")
        .def_prop_ro(
            "unique_name", [](const edi::ProjectMetadata& self) { return self.name; },
            "Unique name for diagnostics (upstream: the project name).")
        .def_rw("title", &edi::ProjectMetadata::title)
        .def_prop_rw(
            "description", [](const edi::ProjectMetadata& self) { return self.description; },
            [](edi::ProjectMetadata& self, const std::string& value) {
                std::istringstream words(value);
                std::string word;
                std::string out;
                while (words >> word) {
                    if (!out.empty()) {
                        out += ' ';
                    }
                    out += word;
                }
                self.description = out;
            },
            "The project description, sanitized to single spaces.")
        .def_prop_rw(
            "path",
            [](const edi::ProjectMetadata& self) -> nb::object {
                if (self.path.empty()) {
                    return nb::none();
                }
                return nb::cast(std::filesystem::path(self.path));
            },
            [](edi::ProjectMetadata& self, const std::filesystem::path& value) {
                self.path = value.string();
            },
            "The project directory as a Path (None until loaded or saved).")
        .def_prop_ro(
            "created",
            [](const edi::ProjectMetadata& self) { return star_datetime(self.created); },
            "The creation timestamp as a UTC-aware datetime (the counterpart value semantics).")
        .def_prop_ro(
            "last_modified",
            [](const edi::ProjectMetadata& self) { return star_datetime(self.last_modified); },
            "The last-modified timestamp as a UTC-aware datetime; save()/save_as() advance it.")
        .def_prop_rw(
            "timestamp",
            [](const edi::ProjectMetadata& self) -> nb::object {
                if (self.timestamp.empty()) {
                    return nb::none();
                }
                return nb::cast(self.timestamp);
            },
            [](edi::ProjectMetadata& self, nb::object value) {
                self.timestamp = value.is_none() ? "" : nb::cast<std::string>(value);
            },
            "The latest fit timestamp (None until set).")
        .def("update_last_modified", &edi::ProjectMetadata::update_last_modified,
             "Update the last modified timestamp.")
        .def(
            "show_as_text",
            [](const edi::ProjectMetadata& self) {
                const nb::object print = nb::module_::import_("builtins").attr("print");
                print("_metadata.name " + self.name);
                print("_metadata.title " + self.title);
                if (!self.description.empty()) {
                    print("_metadata.description " + self.description);
                }
                print("_metadata.created " + self.created);
                print("_metadata.last_modified " + self.last_modified);
                if (!self.timestamp.empty()) {
                    print("_metadata.timestamp " + self.timestamp);
                }
            },
            "Pretty-print the project metadata as text (the .edi _metadata.* spellings — "
            "diffraction-lib ProjectMetadata.show_as_text).");

    def_collection_views(m);

    nb::class_<edi::Project> project(m, "Project");
    def_parameter_walks(project);
    def_free_parameters(project);
    project.def(nb::init<>())
        // NAMED construction — the port's spelling
        // `Project(name='si_sepd')`. The positional `Project(structure, experiment)` constructor
        // is RETIRED by the same ruling: calling it raises TypeError, and populating a project
        // goes through the collections/factories.
        .def(
            "__init__",
            [](edi::Project* self, const std::string& name) {
                new (self) edi::Project();
                self->metadata.name = validated_project_name(name);
            },
            nb::kw_only(), "name"_a,
            "Construct an empty project with the given name (diffraction-lib Project(name=...)).")
        // Plural storage with the singular accessors as documented first-element shortcuts —
        // VIEWS into the collections (reference_internal), fail-closed on an empty collection;
        // the singular setters auto-create on empty. The R15 keyed collection views (live).
        .def_prop_ro(
            "structures",
            [](edi::Project& p) {
                return edi::views::StructuresView{&p, &edi::Project::structures,
                                                  &edi::Structure::name};
            },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "_aliases",
            [](edi::Project& p) {
                return edi::views::AliasesView{&p, &edi::Project::aliases, &edi::ParameterAlias::id};
            },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "_constraints",
            [](edi::Project& p) {
                return edi::views::ConstraintsView{&p, &edi::Project::constraints,
                                                   &edi::ParameterConstraint::id};
            },
            nb::keep_alive<0, 1>())
        .def_prop_ro(
            "experiments",
            [](edi::Project& p) {
                return edi::views::ExperimentsView{&p, &edi::Project::experiments,
                                                   &edi::ExperimentBase::name};
            },
            nb::keep_alive<0, 1>())
        .def_prop_rw(
            "structure",
            [](edi::Project& p) -> edi::Structure& {
                return p.structure();
            },
            [](edi::Project& p, const edi::Structure& incoming) {
                if (p.structures.empty()) {
                    p.structures.push_back(incoming);
                } else {
                    *p.structures.front() = incoming;
                }
            },
            nb::rv_policy::reference_internal)
        .def_prop_rw(
            "experiment",
            [](edi::Project& p) -> edi::BraggPdExperiment& {
                return p.experiment();
            },
            [](edi::Project& p, const edi::BraggPdExperiment& incoming) {
                if (p.experiments.empty()) {
                    p.experiments.push_back(incoming);
                } else {
                    *p.experiments.front() = incoming;
                }
            },
            nb::rv_policy::reference_internal)
        // The diffraction-lib spelling is `project.analysis.fitting_mode` (ruled C); the
        // engine-project property is PUBLIC too: crysta adapts the selector onto its engine
        // Project (D3), and I11 needs edi to carry every crysta Project member, so both
        // spellings read one storage stays on the core Project, reachable for the facade under
        // the private spelling. Review-1 F4: the setter is CLOSED, mirroring crysta's.
        // Assignment is the second way a mode reaches the model (the loader is the first), and
        // an open setter meant a lookalike or an unimplemented value was only discovered a whole
        // fit later — or, on the single-bank path, never.
        .def_prop_rw(
            "_template_file", [](const edi::Project& self) { return self.sequential_fit.template_file; },
            [](edi::Project& self, const std::string& file) { edi::set_scan_template_file(self, file); })
        .def_prop_rw(
            "fitting_mode", [](const edi::Project& self) { return self.fitting_mode; },
            [](edi::Project& self, const std::string& value) {
                // Review-2 F2: no empty-token exemption — "" bypassed the closed set and fell
                // through as a single fit, and " "/"\t" rode the same guard.
                if (!edi::is_declared_fitting_mode(value)) {
                    throw std::invalid_argument("_fitting_mode.type is '" + value + "', expected " +
                                                edi::declared_fitting_modes());
                }
                self.fitting_mode = value;
            })
        // The declared `_minimizer.max_iterations` (0 = absent -> 50). Underscored:
        // engine-internal model state set by the loader (crysta parity — the internal budget
        // seam for tooling that pins its own bound).
        .def_rw("_minimizer_max_iterations", &edi::Project::minimizer_max_iterations)
        // The declared `_minimizer.chi_square_tolerance` (0 = absent -> crysta's
        // default), same shape; the declared descent is the public `descent` below.
        .def_rw("_minimizer_chi_square_tolerance", &edi::Project::minimizer_chi_square_tolerance)
        .def_prop_ro(
            "name", [](const edi::Project& self) { return self.metadata.name; },
            "Convenience property for the project name (diffraction-lib Project.name).")
        .def_prop_ro(
            "metadata", [](edi::Project& self) -> edi::ProjectMetadata& { return self.metadata; },
            nb::rv_policy::reference_internal,
            "Project metadata container (diffraction-lib Project.metadata).")
        .def_static(
            "load",
            [](const std::filesystem::path& directory) {
                // crysta's coded warnings reach Python as warnings led by the code; the loader's
                // own notes keep their stderr line.
                return edi::load_project(directory.string(), [](const std::string& message) {
                    if (message.rfind("crysta.", 0) == 0) {
                        if (PyErr_WarnEx(PyExc_UserWarning, message.c_str(), 1) < 0) {
                            throw nb::python_error();
                        }
                        return;
                    }
                    std::cerr << "Warning: " << message << "\n";
                });
            },
            "directory"_a,
            "Load a COMPLETE declarative .edi project directory (structures/, experiments/, "
            "analysis/) — THE ONE LOADER.\n\n"
            "The project's own contents select the mode (owner ruling: one loader, project "
            "contents select calculate vs fit): an experiment declaring an embedded _data loop is "
            "fit-ready and a successful return proves non-empty, finite, positive-sigma measured "
            "data on that bank; one declaring _data_range.<axis>_min/_max/_step is "
            "calculation-only and carries a generated grid instead (the data postconditions do "
            "not apply); declaring neither, or both, raises edi.IoError naming the offending "
            "file. A partially-loaded project is unrepresentable; after a fit-ready load, "
            "fit()/fit_joint() can be called with no arguments and cannot fail for a data "
            "reason.")
        .def(
            "save_as",
            [](edi::Project& self, const std::filesystem::path& directory) {
                // edi NARRATES its saves (the display facade is edi's, R6); the write itself
                // is delegated to crysta's silent writer (:save_project validates and hands
                // over).
                nb::module_::import_("builtins").attr("print")(
                    "Saving project to '" + directory.string() + "'");
                // review-32 F2: upstream advances on save;: BEFORE the write, rolled back
                // on failure, so the record holds the advanced value.
                save_project_advancing_last_modified(self, directory.string());
                self.path = directory.string();
                self.metadata.path = directory.string();
            },
            "directory"_a,
            "Write the project out as a .edi project directory and remember it (inverse of "
            "load).")
        .def(
            "_undo_fit",
            [](edi::Project& self) {
                // Undo the last fit — restore the persisted start state, clear the snapshot,
                // report (restored ids, was_no_op). The CLI's undo verb.
                const edi::UndoFitOutcome outcome = edi::undo_fit(self);
                return nb::make_tuple(outcome.restored_parameters, outcome.was_no_op);
            },
            "Internal: undo the last fit (restored slot ids, was_no_op).")
        .def(
            "_dry_run_into",
            [](edi::Project& self, const std::filesystem::path& directory) {
                // The CLI's --dry. What a fit writes lands under
                // `directory` (the project's path from here on; a scan's analysis/results*.csv),
                // while a scan's data are read in place from the directory this project was
                // loaded from — never copied.
                if (self.path.empty()) {
                    throw std::invalid_argument(
                        "this project has no directory (never loaded or saved): nothing to run "
                        "dry against");
                }
                self.scan_data_root = self.path;
                self.path = directory.string();
                self.metadata.path = self.path;
            },
            "directory"_a,
            "Internal: route this project's fit outputs into `directory` and read scan data in "
            "place (the CLI's --dry).")
        .def(
            "_save_silent",
            [](edi::Project& self) {
                // The machine channel's persistence — the write without the narration line, so
                // `python -m edi fit --report machine` stdout stays the versioned record and
                // nothing else (byte-comparable with `crysta fit`).
                if (self.path.empty()) {
                    throw std::invalid_argument(
                        "this project has no directory yet (never loaded or saved): use "
                        "save_as(directory) first");
                }
                save_project_advancing_last_modified(self, self.path);
            },
            "Internal: write the project back silently (the machine channel's save).")
        .def(
            "save",
            [](edi::Project& self) {
                if (self.path.empty()) {
                    throw std::invalid_argument(
                        "this project has no directory yet (never loaded or saved): use "
                        "save_as(directory) first");
                }
                nb::module_::import_("builtins").attr("print")(
                    "Saving project to '" + self.path + "'");
                // review-32 F2 +: advance before the write, roll back on failure.
                save_project_advancing_last_modified(self, self.path);
            },
            "Write the project back into its own directory (the one it was loaded from or last "
            "saved to).")
        .def(
            "calculate",
            [](edi::Project& self) {
                // The model is the single source of truth — no grid, bank, cutoff or
                // scattering argument exists; the result is read from
                // experiment.data.intensity_calc.
                warn_dependents(self);  // a stale free flag on a dependent warns, as crysta's does
                nb::gil_scoped_release nogil;
                self.calculate();
            },
            "Forward-calculate every experiment from the model alone (diffraction-lib "
            "Analysis.calculate): inputs are read from the project and the result is written "
            "into each experiment's data.intensity_calc.")
        // The one-call forms: refine against the project's OWN embedded data — the only public
        // shape (the explicit-data overloads are retired).
        .def(
            "fit",
            [](edi::Project& self, const std::optional<nb::callable>& on_iteration,
               const std::optional<nb::callable>& on_start,
               const std::optional<nb::callable>& should_cancel) {
                warn_dependents(self);
                return fit_with_callbacks(
                    on_iteration, on_start, should_cancel,
                    [&](const edi::IterationCallback& cb, const edi::PreambleCallback& pre,
                        const edi::CancelCallback& cancel) {
                        return self.fit(cb, pre, cancel);
                    });
            },
            "on_iteration"_a = nb::none(), "on_start"_a = nb::none(),
            "should_cancel"_a = nb::none(),
            "Whole-fit refinement against the project's own embedded measured data — the one-call "
            "form: the bank's data comes from the model, so the caller assembles nothing. `on_start` is an optional one-shot "
            "preamble subscriber, fired once before iteration 1 with the FitPreamble (bank names, "
            "point counts, free count, pre-fit record) — the live-streaming header seam. Raises "
            "ValueError if this experiment carries no measured data — a calculation-only or "
            "hand-assembled experiment (impossible for a fit-ready load). `should_cancel` is polled between iterations; true, or a "
            "KeyboardInterrupt raised in any callback, stops the fit cleanly with a CANCELLED "
            "result.")
        .def(
            "fit_joint",
            [](edi::Project& self, const std::optional<nb::callable>& on_iteration,
               const std::optional<nb::callable>& on_start,
               const std::optional<nb::callable>& should_cancel) {
                warn_dependents(self);
                return fit_with_callbacks(
                    on_iteration, on_start, should_cancel,
                    [&](const edi::IterationCallback& cb, const edi::PreambleCallback& pre,
                        const edi::CancelCallback& cancel) {
                        return self.fit_joint(cb, pre, cancel);
                    });
            },
            "on_iteration"_a = nb::none(), "on_start"_a = nb::none(),
            "should_cancel"_a = nb::none(),
            "Joint multi-bank refinement against every bank's own embedded measured data — the "
            "one-call form: each pattern comes from the model. `on_start` fires once before iteration 1 with the FitPreamble. Raises "
            "ValueError if any bank carries no measured data — a calculation-only or "
            "hand-assembled experiment (impossible for a fit-ready load). `should_cancel` is polled between iterations; true, or a "
            "KeyboardInterrupt raised in any callback, stops the fit cleanly with a CANCELLED "
            "result.")
        .def(
            "fit_sequential",
            [](edi::Project& self, const std::optional<nb::callable>& on_iteration,
               const std::optional<nb::callable>& on_start,
               const std::optional<nb::callable>& on_scan_start,
               const std::optional<nb::callable>& on_file_complete,
               const std::optional<nb::callable>& should_cancel) {
                warn_dependents(self);
                return fit_with_scan_callbacks(
                    on_iteration, on_start, on_scan_start, on_file_complete, should_cancel,
                    [&](const edi::IterationCallback& cb, const edi::PreambleCallback& pre,
                        const edi::ScanStartCallback& scan_start,
                        const edi::FileCompleteCallback& file_complete,
                        const edi::CancelCallback& cancel) {
                        return self.fit_sequential(cb, pre, scan_start, file_complete, cancel);
                    });
            },
            "on_iteration"_a = nb::none(), "on_start"_a = nb::none(),
            "on_scan_start"_a = nb::none(), "on_file_complete"_a = nb::none(),
            "should_cancel"_a = nb::none(),
            "Sequential scan refinement — the one native entry point the `sequential` "
            "fitting mode delegates to: crysta's own driver fits the declared "
            "_sequential_fit.data_dir files one after another against the single template "
            "experiment, carries each fit's converged values into the next, and appends one "
            "analysis/results.csv row per newly fitted file (resume: a completed scan adds zero "
            "rows). Raises ValueError unless the fitting mode is exactly 'sequential', the "
            "project was loaded or saved (it needs a directory), and the scan block is declared. "
            "`on_start` never fires: the per-file preambles belong to the per-file fits. "
            "`on_scan_start` fires once with the ScanPreamble (walk total + the "
            "already-committed resume rows); `on_file_complete` fires once per file completed "
            "during this call, with its committed "
            "results.csv row's facts; `on_iteration` receives the scan-level renumbered records "
            "the history collects. `should_cancel` is polled between iterations; true, or a "
            "KeyboardInterrupt raised in any callback, stops the fit cleanly with a CANCELLED "
            "result.")
        .def(
            "fit_independent",
            [](edi::Project& self, const std::optional<nb::callable>& on_iteration,
               const std::optional<nb::callable>& on_start,
               const std::optional<nb::callable>& on_scan_start,
               const std::optional<nb::callable>& on_file_complete,
               const std::optional<nb::callable>& should_cancel) {
                warn_dependents(self);
                return fit_with_scan_callbacks(
                    on_iteration, on_start, on_scan_start, on_file_complete, should_cancel,
                    [&](const edi::IterationCallback& cb, const edi::PreambleCallback& pre,
                        const edi::ScanStartCallback& scan_start,
                        const edi::FileCompleteCallback& file_complete,
                        const edi::CancelCallback& cancel) {
                        return self.fit_independent(cb, pre, scan_start, file_complete, cancel);
                    });
            },
            "on_iteration"_a = nb::none(), "on_start"_a = nb::none(),
            "on_scan_start"_a = nb::none(), "on_file_complete"_a = nb::none(),
            "should_cancel"_a = nb::none(),
            "Independent scan refinement — the native entry point the 'independent' "
            "fitting mode delegates to. Identical to `fit_sequential` except where each file's "
            "fit STARTS: every file is fitted from the same initial parameters, so each row is "
            "what fitting that file alone against the untouched project produces. Both scan modes "
            "execute serially. Raises ValueError unless the fitting mode is exactly 'independent'. "
            "Carries the same scan-event subscribers as `fit_sequential`. `should_cancel` is polled between iterations; true, or a "
            "KeyboardInterrupt raised in any callback, stops the fit cleanly with a CANCELLED "
            "result.")
        // The descent selection is MODEL STATE, public on the engine Project exactly as
        // `fitting_mode` is; the analysis facade's `descent` property (lib/edi) delegates here.
        // The setter validates fail-closed against the linked crysta registry, naming the
        // registered set; None or the empty string clears the selection back to the engine
        // default. The getter returns the EFFECTIVE id (the engine default when nothing is
        // selected), so a reader always sees the id the next fit would run and record.
        .def_prop_rw(
            "descent",
            [](const edi::Project& self) {
                return self.descent.empty() ? edi::default_descent() : self.descent;
            },
            [](edi::Project& self, const std::optional<std::string>& value) {
                const std::string id = value.value_or(std::string{});
                edi::validate_descent(id, "edi descent");
                self.descent = id;
            },
            "The selected descent-flow registry id — model state, resolved from the "
            "linked crysta registry (`crysta fit --list-descents` prints the same set). Reading "
            "gives the effective id (the engine default when nothing is selected); assigning an "
            "unknown id raises ValueError naming the registered set; assigning None restores "
            "the default.")
        // Review-1 F1: the explicit-data fit(grid, observed, sigma) and
        // fit_joint(patterns) overloads are gone from the public surface — the model is the
        // single source of truth for fit inputs, and an argument-bearing overload was the exact
        // seam the task retires. The C++ methods remain the internal engine seam; only the
        // one-call forms above are bound.
        ;
}
