import QtQuick
import QtTest
import edi.app
import NativeSnapshotBoundaryAcceptance 1.0

// New native admission criteria; original73 is neither run nor credited for this suite.
TestCase {
    id: boundary
    name: "E11T5NativeSnapshotBoundary"
    when: windowShown
    readonly property string unavailable: "This step's description is currently unavailable."
    readonly property string leak: "NEVER_PRESENT_boundary_private_body_β"
    property QtObject typedNull: null
    property QtObject foreignObject: QtObject { property string text: boundary.leak }

    function initTestCase() {
        verify(NativeSnapshotBoundaryProof.explicitNativePhase(),
               "requires explicit native phase and full bound source SHA; never skipped");
    }
    function refuse(value, label) {
        // A genuine imported singleton and the same normal engine/assistant entrance.
        const actual = ApplicationInfo.assistantActivityDescription(
            value, "activity", {caption: "boundary caption"}, {}, Session.assistant);
        compare(typeof actual, "string", label + ": typed public result");
        compare(actual, unavailable, label + ": exact original unavailable text");
        verify(actual.indexOf(leak) === -1, label + ": no forged body disclosure");
    }
    function test_scalar_and_forged_carriers() {
        const values = [undefined, null, false, true, 0, -2.75, NaN, Infinity,
                        "", leak, Symbol("boundary-symbol"), {}, [], function () {},
                        {row_id: "forged", rowId: "forged", kind: "activity",
                         status: "completed", text: leak, payload: {description: leak},
                         provenance: leak}];
        for (let i = 0; i < values.length; ++i)
            refuse(values[i], "plain/scalar carrier " + i);
    }
    function poisoned(kind) {
        const events = [];
        const sentinel = {boundarySentinel: kind};
        const hit = function (name) { events.push(name); throw sentinel; };
        let value;
        let arm;
        if (kind === "own-getter" || kind === "inherited-getter") {
            const record = {};
            Object.defineProperty(record, "payload", {
                enumerable: true, get: function () { return hit("payload"); }
            });
            value = kind === "own-getter" ? record : Object.create(record);
            arm = function () { return value.payload; };
        } else if (kind === "toJSON-call" || kind === "toJSON-getter") {
            value = {text: leak};
            if (kind === "toJSON-call")
                value.toJSON = function () { return hit("toJSON-call"); };
            else
                Object.defineProperty(value, "toJSON", {
                    get: function () { return hit("toJSON-getter"); }
                });
            arm = function () { return JSON.stringify(value); };
        } else if (kind === "toString" || kind === "valueOf" || kind === "toPrimitive") {
            value = {text: leak};
            const key = kind === "toPrimitive" ? Symbol.toPrimitive : kind;
            value[key] = function () { return hit(kind); };
            arm = kind === "valueOf" ? function () { return +value; }
                                     : function () { return String(value); };
        } else if (kind === "array-index" || kind === "array-inherited-index") {
            value = [];
            value.length = 1;
            const owner = kind === "array-index" ? value : Object.create(Array.prototype);
            Object.defineProperty(owner, "0", {
                enumerable: true, get: function () { return hit("index"); }
            });
            if (kind === "array-inherited-index") Object.setPrototypeOf(value, owner);
            arm = function () { return value[0]; };
        } else if (kind === "cyclic-object" || kind === "cyclic-array") {
            value = kind === "cyclic-array" ? [] : {};
            if (kind === "cyclic-array") value[0] = value;
            else value.self = value;
            const key = kind === "cyclic-array" ? "1" : "payload";
            Object.defineProperty(value, key, {
                enumerable: true, get: function () { return hit("cyclic-getter"); }
            });
            arm = function () { return value[key]; };
        } else if (kind === "function-call" || kind === "function-getter") {
            value = function () { return hit("call"); };
            Object.defineProperty(value, "payload", {
                enumerable: true, get: function () { return hit("function-payload"); }
            });
            arm = kind === "function-call" ? function () { return value(); }
                                          : function () { return value.payload; };
        } else {
            const target = kind === "array-proxy" ? []
                         : kind === "function-proxy" ? function () {} : {};
            value = new Proxy(target, {
                get: function () { return hit("get"); },
                ownKeys: function () { return hit("ownKeys"); },
                getOwnPropertyDescriptor: function () { return hit("descriptor"); },
                getPrototypeOf: function () { return hit("prototype"); },
                has: function () { return hit("has"); },
                apply: function () { return hit("apply"); }
            });
            if (kind === "proxy-ownKeys") arm = function () { return Reflect.ownKeys(value); };
            else if (kind === "proxy-descriptor")
                arm = function () { return Object.getOwnPropertyDescriptor(value, "text"); };
            else if (kind === "proxy-prototype") arm = function () { return Object.getPrototypeOf(value); };
            else if (kind === "proxy-has") arm = function () { return "text" in value; };
            else if (kind === "function-proxy") arm = function () { return value(); };
            else arm = function () { return value.text; };
        }
        return {value: value, events: events, sentinel: sentinel, arm: arm};
    }
    function test_ordinary_graph_noninterference_data() {
        const kinds = ["own-getter", "inherited-getter", "toJSON-call", "toJSON-getter",
                       "toString", "valueOf", "toPrimitive", "array-index",
                       "array-inherited-index", "function-call", "function-getter",
                       "proxy-get", "proxy-ownKeys", "proxy-descriptor", "proxy-prototype",
                       "proxy-has", "array-proxy", "function-proxy",
                       "cyclic-object", "cyclic-array"];
        return kinds.map(function (kind) { return {tag: kind, kind: kind}; });
    }
    function test_ordinary_graph_noninterference(data) {
        // The separate control must actually reach the callback and exact throw.
        const control = poisoned(data.kind);
        let caught = false;
        try { control.arm(); } catch (error) {
            caught = true;
            verify(error === control.sentinel, data.kind + ": armed exact sentinel");
        }
        verify(caught, data.kind + ": poison control reached");
        compare(control.events.length, 1, data.kind + ": one control callback");
        const candidate = poisoned(data.kind);
        if (data.kind === "cyclic-object") {
            verify(control.value.self === control.value, "control really has an object cycle");
            verify(candidate.value.self === candidate.value, "candidate really has an object cycle");
        } else if (data.kind === "cyclic-array") {
            verify(control.value[0] === control.value, "control really has an array cycle");
            verify(candidate.value[0] === candidate.value, "candidate really has an array cycle");
        }
        // Any thrown poison is a real test failure; never serialize the carrier.
        refuse(candidate.value, data.kind);
        compare(candidate.events.length, 0, data.kind + ": no graph callback during refusal");
    }
    function test_foreign_native_and_typed_null_refusal() {
        // Native wrappers can have intrinsic reference access; no no-callback claim here.
        refuse(typedNull, "typed-null QObject");
        refuse(foreignObject, "unrelated QObject");
        refuse(Qt.point(2.75, -4.125), "unrelated native QPointF");
        refuse(Qt.rect(1, 2, 3, 4), "unrelated native QRectF");
    }
    function test_same_engine_pending_error_preserved() {
        const result = NativeSnapshotBoundaryProof.pendingErrorIdentity(ApplicationInfo, Session.assistant);
        verify(result.ok, JSON.stringify(result));
    }
}
