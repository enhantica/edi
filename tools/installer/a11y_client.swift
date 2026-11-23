// An accessibility client for the installer check (a11y-check.sh): while the process `pid` runs, it walks every
// window's element tree and asks each element for several attributes in one call, the selected children among them,
// as some assistive tools do (AXUIElementCopyMultipleAttributeValues). Usage: swift a11y_client.swift <pid>
import AppKit
import ApplicationServices
import Foundation

guard CommandLine.arguments.count == 2, let pid = pid_t(CommandLine.arguments[1]) else {
    FileHandle.standardError.write("usage: a11y_client.swift <pid>\n".data(using: .utf8)!)
    exit(2)
}
if !AXIsProcessTrusted() {
    print("a11y-client: not permitted to read other processes' interfaces")
    exit(3)
}

let attributes = [kAXRoleAttribute, kAXChildrenAttribute, kAXSelectedChildrenAttribute, kAXTitleAttribute] as CFArray
let app = AXUIElementCreateApplication(pid)
var queries = 0

// The element's role and title, read one at a time (a single attribute is not the crashing call), printed before
// the multiple-attribute query so the last line names the element a crash happened on.
func describe(_ element: AXUIElement) -> String {
    var role: CFTypeRef?
    var title: CFTypeRef?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &role)
    AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &title)
    return "\((role as? String) ?? "?") \((title as? String) ?? "")"
}

// One element of a page, for the layout check: its role, its text and its frame in screen points.
struct Placed {
    let role: String
    let text: String
    let frame: CGRect
    let children: [CGRect]
}

func string(_ element: AXUIElement, _ attribute: String) -> String {
    var value: CFTypeRef?
    AXUIElementCopyAttributeValue(element, attribute as CFString, &value)
    return (value as? String) ?? ""
}

func frame(_ element: AXUIElement) -> CGRect? {
    var position: CFTypeRef?
    var size: CFTypeRef?
    guard AXUIElementCopyAttributeValue(element, kAXPositionAttribute as CFString, &position) == .success,
        AXUIElementCopyAttributeValue(element, kAXSizeAttribute as CFString, &size) == .success
    else { return nil }
    var point = CGPoint.zero
    var extent = CGSize.zero
    AXValueGetValue(position as! AXValue, .cgPoint, &point)
    AXValueGetValue(size as! AXValue, .cgSize, &extent)
    return CGRect(origin: point, size: extent)
}

func visit(_ element: AXUIElement, depth: Int, into placed: inout [Placed]) {
    guard depth < 40 else { return }
    var values: CFArray?
    queries += 1
    print("\(String(repeating: " ", count: depth))\(describe(element))")
    fflush(stdout)
    var children: [AXUIElement] = []
    if AXUIElementCopyMultipleAttributeValues(element, attributes, AXCopyMultipleAttributeOptions(rawValue: 0), &values)
        == .success, let list = values as? [AnyObject], list.count > 1, let found = list[1] as? [AXUIElement]
    {
        children = found
    }
    if depth > 0, let box = frame(element) {
        let role = string(element, kAXRoleAttribute)
        let text = [kAXTitleAttribute, kAXValueAttribute, kAXDescriptionAttribute]
            .map { string(element, $0) }.first { !$0.isEmpty } ?? ""
        placed.append(Placed(role: role, text: text, frame: box, children: children.compactMap(frame)))
    }
    for child in children { visit(child, depth: depth + 1, into: &placed) }
}

// The page's layout rules (owner, 2026-11-23): one left edge, gaps on the spacing scale, no clipped text, no frame
// mostly empty. Content lies between the header (the logo, at the top) and the row of wizard buttons.
let steps: [CGFloat] = [0, 4, 8, 12, 16, 24, 32]
let wizardButtons: Set<String> = ["Back", "Next", "Install", "Cancel", "Finish", "Uninstall", "Update", "Quit"]
let font = NSFont(name: "Helvetica Neue", size: 14) ?? NSFont.systemFont(ofSize: 14)
var reported = Set<String>()
var pagesSeen = 0
var pagesChecked = 0

func check(window: CGRect, title: String, placed: [Placed]) {
    let buttons = placed.filter { $0.role == "AXButton" && wizardButtons.contains($0.text) }
    let bottom = buttons.map(\.frame.minY).min() ?? window.maxY
    pagesSeen += 1
    let content = placed.filter {
        $0.frame.minY > window.minY + 140 && $0.frame.maxY < bottom - 2 && $0.frame.width > 1 && $0.frame.height > 1
            && ["AXStaticText", "AXCheckBox", "AXRadioButton", "AXTextField", "AXButton", "AXProgressIndicator",
                "AXTextArea", "AXScrollArea"].contains($0.role)
    }
    guard !content.isEmpty else {
        if reported.insert(title + "empty").inserted { print("layout: [\(title)] no content to check on a page") }
        return
    }
    pagesChecked += 1
    var problems: [String] = []
    // The first element of each row (nothing beside it to its left).
    let firsts = content.filter { item in
        !content.contains { other in
            other.frame.maxX <= item.frame.minX + 1 && other.frame.minY < item.frame.maxY - 2
                && other.frame.maxY > item.frame.minY + 2
        }
    }.sorted { $0.frame.minY < $1.frame.minY }
    let edge = firsts.map(\.frame.minX).min() ?? 0
    for item in firsts where abs(item.frame.minX - edge) > 1 {
        problems.append("left edge \(Int(item.frame.minX - edge)) px off: \(item.role) '\(item.text)'")
    }
    for (above, below) in zip(firsts, firsts.dropFirst()) {
        let gap = below.frame.minY - above.frame.maxY
        if gap < -1 {
            problems.append("overlap \(Int(-gap)) px between '\(above.text)' and '\(below.text)'")
        } else if !steps.contains(where: { abs($0 - gap) <= 1 }) {
            problems.append("gap \(Int(gap)) px between '\(above.text)' and '\(below.text)'")
        }
    }
    for item in content where ["AXStaticText", "AXCheckBox", "AXRadioButton", "AXButton"].contains(item.role) {
        let lines = item.text.split(separator: "\n")
        guard lines.count == 1, item.frame.height < 40 else { continue }
        let indicator: CGFloat = item.role == "AXCheckBox" || item.role == "AXRadioButton" ? 28 : 0
        let width = (String(lines[0]) as NSString).size(withAttributes: [.font: font]).width + indicator
        if width > item.frame.width + 2 {
            problems.append("clipped: \(item.role) '\(item.text)' needs \(Int(width)) px, has \(Int(item.frame.width))")
        }
    }
    for box in content where box.role == "AXScrollArea" {
        let filled = box.children.reduce(CGFloat(0)) { $0 + $1.intersection(box.frame).height }
        if filled < box.frame.height / 2 {
            problems.append("mostly empty frame: \(Int(filled)) of \(Int(box.frame.height)) px used")
        }
    }
    let page = content.map(\.text).joined(separator: "|")
    for problem in problems where reported.insert(title + page + problem).inserted {
        print("layout: [\(title)] \(problem)")
        fflush(stdout)
    }
}

while kill(pid, 0) == 0 {
    var windows: CFTypeRef?
    if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windows) == .success,
        let list = windows as? [AXUIElement]
    {
        for window in list {
            var placed: [Placed] = []
            visit(window, depth: 0, into: &placed)
            if let box = frame(window) { check(window: box, title: string(window, kAXTitleAttribute), placed: placed) }
        }
    }
    usleep(200_000)
}
print("layout-pages: \(pagesChecked)")
print("a11y-client: \(queries) multiple-attribute queries")
