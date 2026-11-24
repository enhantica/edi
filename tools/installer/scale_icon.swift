// The installer icon's art, unchanged but larger: cropped to its visible pixels and drawn at a given share of each
// icon size, centred, into an iconset for iconutil (package.py standard_icns). Finder then shows the installer as
// tall as a document icon beside it. Usage: swift scale_icon.swift <1024 px PNG> <height share> <iconset folder>
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let arguments = CommandLine.arguments
guard arguments.count == 4, let share = Double(arguments[2]),
    let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: arguments[1]) as CFURL, nil),
    let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
else {
    FileHandle.standardError.write("usage: scale_icon.swift <png> <height share> <iconset>\n".data(using: .utf8)!)
    exit(2)
}

// The visible pixels' bounds, read from the alpha of an RGBA copy.
let width = image.width, height = image.height
var pixels = [UInt8](repeating: 0, count: width * height * 4)
let space = CGColorSpace(name: CGColorSpace.sRGB)!
let reader = CGContext(
    data: &pixels, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4, space: space,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
reader.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
var left = width, right = -1, top = height, bottom = -1
for y in 0..<height {
    for x in 0..<width where pixels[(y * width + x) * 4 + 3] > 8 {
        left = min(left, x); right = max(right, x); top = min(top, y); bottom = max(bottom, y)
    }
}
guard right >= left, bottom >= top else { exit(3) }
// Rows in the buffer run from the top; CGImage cropping counts from the top as well.
let art = image.cropping(to: CGRect(x: left, y: top, width: right - left + 1, height: bottom - top + 1))!

let sizes: [(String, Int)] = [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32), ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256), ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512), ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
]
let folder = URL(fileURLWithPath: arguments[3])
try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
for (name, size) in sizes {
    let side = Double(size)
    let scale = min(side * share / Double(art.height), side / Double(art.width))
    let w = Double(art.width) * scale, h = Double(art.height) * scale
    let canvas = CGContext(
        data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0, space: space,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    canvas.interpolationQuality = .high
    canvas.draw(art, in: CGRect(x: (side - w) / 2, y: (side - h) / 2, width: w, height: h))
    let out = CGImageDestinationCreateWithURL(
        folder.appendingPathComponent(name) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(out, canvas.makeImage()!, nil)
    guard CGImageDestinationFinalize(out) else { exit(4) }
}
