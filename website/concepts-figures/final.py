"""The concept page's raw detector image: rings computed from the measured D20 2.3 K pattern."""

import matplotlib as mpl
import numpy as np

mpl.use('Agg')
# The app's bundled Noto Sans, from the repository root.
from pathlib import Path

import matplotlib.pyplot as plt
from edicmap import cmap
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

F = str(Path(__file__).resolve().parents[2] / 'app/resources/fonts/Noto_Sans/NotoSans-Regular.ttf')
fm.fontManager.addfont(F)
plt.rcParams['font.family'] = fm.FontProperties(fname=F).get_name()
plt.rcParams['svg.fonttype'] = 'path'
rng = np.random.default_rng(7)
lo = np.load('lo.npy')
tt, intensity = lo[:, 0], lo[:, 1]
W, H = 1200, 840
L = W / 2 / np.tan(np.radians(56))
y, x = np.mgrid[0:H, 0:W]
x = x - W / 2 + 0.5
y = y - H / 2 + 0.5
r = np.hypot(x, y)
t2 = np.degrees(np.arctan(r / L))
phi = np.arctan2(y, x)
Iw = np.where(tt < 6.5, np.interp(7.0, tt, intensity) * 0.9, intensity)
img = np.interp(t2, tt, Iw)
g = np.zeros_like(img)
for k in range(1, 40):
    g += (
        rng.normal(0, 1)
        / k**0.9
        * np.cos(k * phi + rng.uniform(0, 6.3))
        * np.cos(np.radians(t2) * rng.uniform(20, 60) + rng.uniform(0, 6.3))
    )
img *= 1 + 0.06 * g / np.abs(g).max()
img *= np.cos(np.radians(t2)) ** 3
cnt = rng.poisson(img * 0.6) / 0.6
lo_, hi_ = np.percentile(cnt, 20), np.percentile(cnt, 99.9)
v = np.clip((cnt - lo_) / (hi_ - lo_), 0, 1) ** 0.8
# edi's Blue-Red map (core/src/scan_views.cpp blue_red): off-plot colour -> blue -> red, in Oklab
# halves
maps = {
    'light': (cmap(['#FFFFFF', '#3F7FBF', '#C8323C']), '#6B7280', '#FFFFFF'),
    'dark': (cmap(['#181818', '#6AA6EA', '#FC4F81']), '#A0A6B0', '#1E2129'),
}
cx, cy = W / 2, H / 2
labels = [
    (170.1, '(001) magnetic', -0.40, 'mag'),
    (77.2, '(100) magnetic', -0.02, 'mag'),
    (462.3, '(221) nuclear', 0.62, 'nuc'),
]
# edi Main palette: the nuclear phase's Bragg ticks are orange, the magnetic phase's teal
PHASE = {
    'light': {'nuc': '#DB7A12', 'mag': '#2E8F8A'},
    'dark': {'nuc': '#F5961A', 'mag': '#55B1B3'},
}
for theme, (cm, txt, bg) in maps.items():
    fig = plt.figure(figsize=(8.6, 4.6), dpi=200)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0.005, 0.02, 0.70, 0.96])
    im = ax.imshow(v, cmap=cm, extent=(0, W, H, 0), vmin=0, vmax=1)
    ax.set_axis_off()
    clip = FancyBboxPatch(
        (0, 0),
        W,
        H,
        boxstyle='round,pad=0,rounding_size=28',
        transform=ax.transData,
        fc='none',
        ec='#8888' if theme == 'light' else 'none',
        lw=0.6,
    )
    ax.add_patch(clip)
    im.set_clip_path(clip)
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    for rr, name, ang, ph in labels:
        px = cx + rr * np.cos(ang)
        py = cy + rr * np.sin(ang)
        ax.plot([px, W], [py, py], color=txt, lw=1.6, alpha=0.9, clip_on=False)
        ax.plot([W, W + 40], [py, py], color=txt, lw=1.6, clip_on=False)
        ax.plot(
            [px],
            [py],
            'o',
            ms=9,
            mfc=PHASE[theme][ph],
            mec='white' if theme == 'light' else '#181818',
            mew=1.2,
        )
        ax.text(W + 50, py, name, fontsize=15, color=txt, va='center')
    fig.savefig(f'raw-2d-{theme}.svg', transparent=True)
    fig.savefig(f'raw-2d-{theme}.png', transparent=True, dpi=200)
    fig.patch.set_alpha(1)
    fig.savefig(f'raw-2d-{theme}-onbg.png', facecolor=bg, dpi=120)
    plt.close(fig)
