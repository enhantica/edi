// An accessibility client for the installer check (a11y-check.sh): while the process `pid` runs, it walks every
// window's element tree and asks each element for several attributes in one call, the selected children among them,
// as some assistive tools do (AXUIElementCopyMultipleAttributeValues). Usage: swift a11y_client.swift <pid>
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

func visit(_ element: AXUIElement, depth: Int) {
    guard depth < 40 else { return }
    var values: CFArray?
    queries += 1
    print("\(String(repeating: " ", count: depth))\(describe(element))")
    fflush(stdout)
    if AXUIElementCopyMultipleAttributeValues(element, attributes, AXCopyMultipleAttributeOptions(rawValue: 0), &values)
        == .success, let list = values as? [AnyObject], list.count > 1, let children = list[1] as? [AXUIElement]
    {
        for child in children { visit(child, depth: depth + 1) }
    }
}

while kill(pid, 0) == 0 {
    var windows: CFTypeRef?
    if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windows) == .success,
        let list = windows as? [AXUIElement]
    {
        for window in list { visit(window, depth: 0) }
    }
    usleep(200_000)
}
print("a11y-client: \(queries) multiple-attribute queries")
