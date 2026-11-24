// An accessibility client for the installer check (a11y-check.sh): while the process `pid` runs, it walks every
// window's element tree and asks each element for several attributes in one call, the selected children among them,
// as some assistive tools do (AXUIElementCopyMultipleAttributeValues). Usage: swift a11y_client.swift <pid>
// [pages.log]: with the page log a captured walk writes (Installer.qs), it ends with one witness line per page it read,
// "witness: <page> reads=<n> layout=<0|1> trees=<n>", which a11y-check.sh requires for every page of the walk.
import AppKit
import ApplicationServices
import Foundation

guard [2, 3].contains(CommandLine.arguments.count), let pid = pid_t(CommandLine.arguments[1]) else {
    FileHandle.standardError.write("usage: a11y_client.swift <pid> [pages.log]\n".data(using: .utf8)!)
    exit(2)
}
if !AXIsProcessTrusted() {
    print("a11y-client: not permitted to read other processes' interfaces")
    exit(3)
}

let attributes = [kAXRoleAttribute, kAXChildrenAttribute, kAXSelectedChildrenAttribute, kAXTitleAttribute] as CFArray
let app = AXUIElementCreateApplication(pid)
let pageLog = CommandLine.arguments.count == 3 ? CommandLine.arguments[2] : nil
// Queries that returned values; a query that failed proves nothing about the page.
var queries = 0
var trees = 0
// Elements a tree view is made of: an outline or browser, or a row that opens and closes (a disclosure).
let treeRoles: Set<String> = ["AXOutline", "AXBrowser", "AXDisclosureTriangle"]

// The page the walk shows now: the last line of its page log.
func currentPage() -> String? {
    guard let path = pageLog, let text = try? String(contentsOfFile: path, encoding: .utf8) else { return nil }
    return text.split(whereSeparator: \.isNewline).last.map { $0.trimmingCharacters(in: .whitespaces) }
}

// What one pass over a page found: successful queries, tree elements, whether its layout was checked.
struct Tally {
    var reads = 0
    var trees = 0
    var laidOut = false
}
var witnessed: [String: Tally] = [:]
var witnessOrder: [String] = []

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

func visit(_ element: AXUIElement, depth: Int, into placed: inout [Placed], tally: inout Tally) {
    guard depth < 40 else { return }
    var values: CFArray?
    print("\(String(repeating: " ", count: depth))\(describe(element))")
    fflush(stdout)
    var children: [AXUIElement] = []
    let answered = AXUIElementCopyMultipleAttributeValues(
        element, attributes, AXCopyMultipleAttributeOptions(rawValue: 0), &values) == .success
    if answered {
        queries += 1
        tally.reads += 1
    }
    if answered, let list = values as? [AnyObject], list.count > 1, let found = list[1] as? [AXUIElement] {
        children = found
    }
    let role = string(element, kAXRoleAttribute)
    var disclosing: CFTypeRef?
    if treeRoles.contains(role)
        || AXUIElementCopyAttributeValue(element, "AXDisclosing" as CFString, &disclosing) == .success
    {
        trees += 1
        tally.trees += 1
        print("tree: \(describe(element))")
        fflush(stdout)
    }
    if depth > 0, let box = frame(element) {
        let text = [kAXTitleAttribute, kAXValueAttribute, kAXDescriptionAttribute]
            .map { string(element, $0) }.first { !$0.isEmpty } ?? ""
        placed.append(Placed(role: role, text: text, frame: box, children: children.compactMap(frame)))
    }
    for child in children { visit(child, depth: depth + 1, into: &placed, tally: &tally) }
}

// The page's layout rules (owner, 2026-11-23): one left edge, gaps on the spacing scale, no clipped text, no frame
// mostly empty. Content lies between the header (the logo, at the top) and the row of wizard buttons.
let steps: [CGFloat] = [0, 4, 8, 12, 16, 24, 32]
let wizardButtons: Set<String> = ["Back", "Next", "Install", "Cancel", "Finish", "Uninstall", "Update", "Quit"]
let font = NSFont(name: "Helvetica Neue", size: 14) ?? NSFont.systemFont(ofSize: 14)
var reported = Set<String>()
var pagesSeen = 0
// Each window's content left edge, relative to the window, on every page: one alignment across pages.
// Each window's page left edges, with the element that starts the page at each.
var pageEdges: [String: [Int: String]] = [:]
var pagesChecked = 0

// Whether the page had content whose layout was checked.
@discardableResult
func check(window: CGRect, title: String, placed: [Placed]) -> Bool {
    let buttons = placed.filter { $0.role == "AXButton" && wizardButtons.contains($0.text) }
    let bottom = buttons.map(\.frame.minY).min() ?? window.maxY
    pagesSeen += 1
    // Everything under the title bar: the pages have no header, the logo is the page's first element.
    let content = placed.filter {
        !($0.role == "AXStaticText" && $0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) &&
        $0.frame.minY > window.minY + 28 && $0.frame.maxY < bottom - 2 && $0.frame.width > 1 && $0.frame.height > 1
            && ["AXStaticText", "AXCheckBox", "AXRadioButton", "AXTextField", "AXButton", "AXProgressIndicator",
                "AXTextArea", "AXScrollArea"].contains($0.role)
    }
    // A moment between two pages has no content; a run that never checks a page fails (layout-pages: 0).
    guard !content.isEmpty else { return false }
    pagesChecked += 1
    var problems: [String] = []
    // The first element of each row (nothing beside it to its left).
    let firsts = content.filter { item in
        !content.contains { other in
            other.frame.maxX <= item.frame.minX + 1 && other.frame.minY < item.frame.maxY - 2
                && other.frame.maxY > item.frame.minY + 2
        }
    }.sorted { $0.frame.minY < $1.frame.minY }
    // Every control is drawn by the stylesheet (Qt's Modern wizard style), so each frame is what is drawn: the
    // allowances the native Mac controls needed (a field's focus ring, a box's offset) are gone, measured on the
    // 2026-11-24 captures where field, boxes and text line up at the same pixel.
    func drawn(_ item: Placed) -> CGRect { item.frame }
    func drawnX(_ item: Placed) -> CGFloat { item.frame.minX }
    let edge = firsts.map(drawnX).min() ?? 0
    let leader = firsts.min { drawnX($0) < drawnX($1) }
    pageEdges[title, default: [:]][Int((edge - window.minX).rounded())] = "\(leader?.role ?? "") '\(leader?.text ?? "")'"
    // Exactly one edge: frames are in whole points, and a widget the native style moves off its cell is 2 off.
    for item in firsts where abs(drawnX(item) - edge) > 0.5 {
        problems.append("left edge \(Int(drawnX(item) - edge)) px off: \(item.role) '\(item.text)'")
    }
    // Boxes of one kind on a page start at one x and are one height: a box moved or cut by its widget's frame starts
    // further right (its indicator is clipped on the left), a box with an inner margin is taller.
    for kind in ["AXCheckBox", "AXRadioButton"] {
        let boxes = content.filter { $0.role == kind }
        guard let first = boxes.first else { continue }
        for box in boxes.dropFirst() {
            if abs(box.frame.minX - first.frame.minX) > 0.5 {
                problems.append("\(kind) '\(box.text)' starts \(Int(box.frame.minX - first.frame.minX)) px from '\(first.text)'")
            }
            if abs(box.frame.height - first.frame.height) > 0.5 {
                problems.append("\(kind) '\(box.text)' is \(Int(box.frame.height)) px high, '\(first.text)' \(Int(first.frame.height))")
            }
        }
    }
    // The page sits centred: as much space right of its widest stretching element (a field or a bar) as left of
    // its content. A page without one (only short lines) is not judged.
    let stretching = content.filter { ["AXTextField", "AXProgressIndicator", "AXTextArea"].contains($0.role) }
    if let widest = stretching.map({ drawn($0).maxX }).max() {
        // ...or whatever ends its row (the Browse button, the percentage).
        let browse = content.filter { item in
            stretching.contains { drawn(item).minY < $0.frame.maxY && drawn(item).maxY > $0.frame.minY }
        }.map { drawn($0).maxX }.max() ?? widest
        let right = window.maxX - max(widest, browse)
        if abs((edge - window.minX) - right) > 24 {
            problems.append("off centre: \(Int(edge - window.minX)) px on the left, \(Int(right)) px on the right")
        }
    }
    for (above, below) in zip(firsts, firsts.dropFirst()) {
        let gap = drawn(below).minY - drawn(above).maxY
        if gap < -0.5 {
            problems.append("overlap \(Int(-gap)) px between '\(above.text)' and '\(below.text)'")
        } else if !steps.contains(where: { abs($0 - gap) <= 0.5 }) {
            problems.append("gap \(Int(gap)) px between '\(above.text)' and '\(below.text)'")
        }
    }
    // Every text on the window, wrapped or not: no word wider than its frame, and the wrapped text no taller.
    let lineHeight = font.ascender - font.descender + font.leading
    for item in placed where ["AXStaticText", "AXCheckBox", "AXRadioButton", "AXButton"].contains(item.role)
        && !item.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        && item.frame.width > 1 && item.frame.height > 1
    {
        let indicator: CGFloat = item.role == "AXCheckBox" || item.role == "AXRadioButton" ? 28 : 0
        let available = max(item.frame.width - indicator, 1)
        let word = item.text.split(whereSeparator: { $0.isWhitespace })
            .map { (String($0) as NSString).size(withAttributes: [.font: font]).width }.max() ?? 0
        let needed = (item.text as NSString).boundingRect(
            with: CGSize(width: available, height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading], attributes: [.font: font]
        ).height
        if word > available + 2 {
            problems.append("clipped: \(item.role) '\(item.text)' has a word \(Int(word)) px wide in \(Int(available))")
        } else if needed > item.frame.height + lineHeight / 2 {
            // Half a line of slack for font metrics; a line that does not fit is a whole line short.
            problems.append("clipped: \(item.role) '\(item.text)' needs \(Int(needed)) px high, has \(Int(item.frame.height))")
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
    return true
}

while kill(pid, 0) == 0 {
    var windows: CFTypeRef?
    if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windows) == .success,
        let list = windows as? [AXUIElement]
    {
        for window in list {
            // A pass counts for a page only when the page log names the same page before and after it.
            let before = currentPage()
            var placed: [Placed] = []
            var tally = Tally()
            visit(window, depth: 0, into: &placed, tally: &tally)
            if let box = frame(window) {
                tally.laidOut = check(window: box, title: string(window, kAXTitleAttribute), placed: placed)
            }
            if let page = before, !page.isEmpty, page == currentPage() {
                if witnessed[page] == nil { witnessOrder.append(page) }
                var sum = witnessed[page] ?? Tally()
                sum.reads += tally.reads
                sum.trees += tally.trees
                sum.laidOut = sum.laidOut || tally.laidOut
                witnessed[page] = sum
            }
        }
    }
    usleep(200_000)
}
for (title, edges) in pageEdges where edges.count > 1 {
    let named = edges.keys.sorted().map { "\($0) (\(edges[$0]!))" }.joined(separator: ", ")
    print("layout: [\(title)] pages start at different left edges: \(named)")
}
for page in witnessOrder {
    let seen = witnessed[page]!
    print("witness: \(page) reads=\(seen.reads) layout=\(seen.laidOut ? 1 : 0) trees=\(seen.trees)")
}
print("layout-pages: \(pagesChecked)")
print("a11y-client: \(trees) tree elements")
print("a11y-client: \(queries) multiple-attribute queries")
