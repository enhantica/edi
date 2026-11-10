// SPDX-License-Identifier: BSD-3-Clause
// edi_app_ui_compare: compares the images the demo mode produced with
// the one committed expected set, by structural similarity rather than bytes.
//
//   edi_app_ui_compare --actual DIR --expected DIR --diff DIR
//
// For each PNG name in either directory: SSIM on luminance (Rec. 601) over non-overlapping 8x8
// windows (a partial window at an edge uses the pixels it has), aggregated per 32x32-pixel tile and
// over the whole image. An image fails when any tile scores below 0.90 or the whole image below 0.98;
// an image missing from either side, or of another size, fails too. Each failure writes a similarity
// map (<name>.png in the diff directory: white = identical, black = unrelated). Exit 0 only when
// every image passes.
#include <QCommandLineParser>
#include <QDir>
#include <QCoreApplication>
#include <QImage>
#include <algorithm>
#include <cstdio>
#include <vector>

namespace {

constexpr int kWindow = 8;
constexpr int kTile = 32;
constexpr double kTileThreshold = 0.90;
constexpr double kImageThreshold = 0.98;
constexpr double kC1 = (0.01 * 255) * (0.01 * 255);  // the SSIM stabilisers for an 8-bit range
constexpr double kC2 = (0.03 * 255) * (0.03 * 255);

std::vector<double> luminance(const QImage& image) {
    const QImage rgb = image.convertToFormat(QImage::Format_RGB32);
    std::vector<double> y(static_cast<std::size_t>(rgb.width()) * rgb.height());
    for (int row = 0; row < rgb.height(); ++row) {
        const auto* line = reinterpret_cast<const QRgb*>(rgb.constScanLine(row));
        for (int column = 0; column < rgb.width(); ++column) {
            const QRgb pixel = line[column];
            y[static_cast<std::size_t>(row) * rgb.width() + column] =
                0.299 * qRed(pixel) + 0.587 * qGreen(pixel) + 0.114 * qBlue(pixel);
        }
    }
    return y;
}

struct Score {
    double mean = 1.0;
    double min_tile = 1.0;
    std::vector<double> windows;  // per window, row-major
    int windows_x = 0, windows_y = 0;
};

Score compare(const QImage& actual, const QImage& expected) {
    const int width = actual.width();
    const int height = actual.height();
    const std::vector<double> a = luminance(actual);
    const std::vector<double> b = luminance(expected);
    Score score;
    score.windows_x = (width + kWindow - 1) / kWindow;
    score.windows_y = (height + kWindow - 1) / kWindow;
    score.windows.assign(static_cast<std::size_t>(score.windows_x) * score.windows_y, 1.0);
    const int tiles_x = (width + kTile - 1) / kTile;
    const int tiles_y = (height + kTile - 1) / kTile;
    std::vector<double> tile_sum(static_cast<std::size_t>(tiles_x) * tiles_y, 0.0);
    std::vector<int> tile_count(tile_sum.size(), 0);
    double total = 0.0;
    for (int wy = 0; wy < score.windows_y; ++wy) {
        for (int wx = 0; wx < score.windows_x; ++wx) {
            const int x0 = wx * kWindow, y0 = wy * kWindow;
            const int x1 = std::min(x0 + kWindow, width), y1 = std::min(y0 + kWindow, height);
            const double n = static_cast<double>((x1 - x0) * (y1 - y0));
            double sa = 0, sb = 0;
            for (int y = y0; y < y1; ++y) {
                for (int x = x0; x < x1; ++x) {
                    sa += a[static_cast<std::size_t>(y) * width + x];
                    sb += b[static_cast<std::size_t>(y) * width + x];
                }
            }
            const double ma = sa / n, mb = sb / n;
            double va = 0, vb = 0, cov = 0;
            for (int y = y0; y < y1; ++y) {
                for (int x = x0; x < x1; ++x) {
                    const double da = a[static_cast<std::size_t>(y) * width + x] - ma;
                    const double db = b[static_cast<std::size_t>(y) * width + x] - mb;
                    va += da * da;
                    vb += db * db;
                    cov += da * db;
                }
            }
            va /= n;
            vb /= n;
            cov /= n;
            const double ssim = ((2 * ma * mb + kC1) * (2 * cov + kC2)) / ((ma * ma + mb * mb + kC1) * (va + vb + kC2));
            score.windows[static_cast<std::size_t>(wy) * score.windows_x + wx] = ssim;
            total += ssim;
            const std::size_t tile = static_cast<std::size_t>(y0 / kTile) * tiles_x + x0 / kTile;
            tile_sum[tile] += ssim;
            tile_count[tile] += 1;
        }
    }
    score.mean = total / static_cast<double>(score.windows.size());
    for (std::size_t i = 0; i < tile_sum.size(); ++i) {
        score.min_tile = std::min(score.min_tile, tile_sum[i] / tile_count[i]);
    }
    return score;
}

void write_map(const Score& score, const QSize& size, const QString& path) {
    QImage map(size, QImage::Format_Grayscale8);
    for (int y = 0; y < size.height(); ++y) {
        uchar* line = map.scanLine(y);
        for (int x = 0; x < size.width(); ++x) {
            const double ssim = score.windows[static_cast<std::size_t>(y / kWindow) * score.windows_x + x / kWindow];
            line[x] = static_cast<uchar>(std::clamp(ssim, 0.0, 1.0) * 255.0 + 0.5);
        }
    }
    map.save(path);
}

}  // namespace

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);  // PNG reading and writing need no display
    QCommandLineParser parser;
    parser.addHelpOption();
    const QCommandLineOption actual_option("actual", "Images the demo produced.", "dir");
    const QCommandLineOption expected_option("expected", "The committed expected set.", "dir");
    const QCommandLineOption diff_option("diff", "Where similarity maps of failures go.", "dir");
    parser.addOptions({actual_option, expected_option, diff_option});
    parser.process(app);
    if (!parser.isSet(actual_option) || !parser.isSet(expected_option) || !parser.isSet(diff_option)) {
        std::fprintf(stderr, "usage: edi_app_ui_compare --actual DIR --expected DIR --diff DIR\n");
        return 2;
    }
    const QDir actual_dir(parser.value(actual_option));
    const QDir expected_dir(parser.value(expected_option));
    QDir diff_dir(parser.value(diff_option));
    diff_dir.mkpath(QStringLiteral("."));

    QStringList names = actual_dir.entryList({QStringLiteral("*.png")}, QDir::Files);
    for (const QString& name : expected_dir.entryList({QStringLiteral("*.png")}, QDir::Files)) {
        if (!names.contains(name)) {
            names.append(name);
        }
    }
    names.sort();
    if (names.isEmpty()) {
        std::fprintf(stderr, "edi_app_ui_compare: no images in %s or %s\n", qPrintable(actual_dir.path()),
                     qPrintable(expected_dir.path()));
        return 1;
    }
    int failures = 0;
    for (const QString& name : names) {
        const QImage actual(actual_dir.filePath(name));
        const QImage expected(expected_dir.filePath(name));
        if (expected.isNull() || actual.isNull()) {
            std::printf("FAIL %s: missing %s image\n", qPrintable(name), expected.isNull() ? "expected" : "actual");
            ++failures;
            continue;
        }
        if (actual.size() != expected.size()) {
            std::printf("FAIL %s: size %dx%d, expected %dx%d\n", qPrintable(name), actual.width(), actual.height(),
                        expected.width(), expected.height());
            ++failures;
            continue;
        }
        const Score score = compare(actual, expected);
        const bool pass = score.min_tile >= kTileThreshold && score.mean >= kImageThreshold;
        std::printf("%s %s: min tile %.4f, image %.4f\n", pass ? "ok  " : "FAIL", qPrintable(name), score.min_tile,
                    score.mean);
        if (!pass) {
            write_map(score, actual.size(), diff_dir.filePath(name));
            ++failures;
        }
    }
    std::printf("%lld image(s), %d failed\n", static_cast<long long>(names.size()), failures);
    return failures == 0 ? 0 : 1;
}
