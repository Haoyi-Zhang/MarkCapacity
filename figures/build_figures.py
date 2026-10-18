"""Direct vector illustrations for the declared capacity instances.

Run with Python and Matplotlib; no TeX executable or private project is used.
The numeric illustration is derived from the retained capacity table.
"""
from pathlib import Path
import argparse
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

plt.rcParams.update({'font.family': 'STIXGeneral', 'mathtext.fontset': 'stix',
                     'font.size': 9, 'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'text.usetex': False, 'axes.unicode_minus': False})


class Drawing:
    def __init__(self, width, height):
        self.fig = plt.figure(figsize=(width/2.54, height/2.54))
        self.ax = self.fig.add_axes([0, 0, 1, 1], xlim=(0, width), ylim=(0, height))
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.labels = []

    def text(self, x, y, text, size=9, **kw):
        label = self.ax.text(x, y, text, ha='center', va='center',
                             fontsize=size, linespacing=1.15, zorder=4, **kw)
        self.labels.append(label)

    def box(self, x, y, width, height, text='', circle=False):
        patch = Circle((x, y), width/2) if circle else Rectangle((x-width/2, y-height/2), width, height)
        patch.set(edgecolor='black', facecolor='white', linewidth=.65, zorder=2)
        self.ax.add_patch(patch)
        if text:
            self.text(x, y, text)

    def line(self, points, arrow=False, dashed=False):
        xs, ys = zip(*points)
        self.ax.plot(xs, ys, color='black', lw=.65, linestyle='--' if dashed else '-', zorder=1)
        if arrow:
            self.ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle='-|>',
                             mutation_scale=8, lw=.65, color='black', zorder=1))

    def save(self, out, name):
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        extent = self.fig.bbox
        for label in self.labels:
            box = label.get_window_extent(renderer)
            if box.x0 < extent.x0 or box.x1 > extent.x1 or box.y0 < extent.y0 or box.y1 > extent.y1:
                raise ValueError('Clipped label: ' + label.get_text())
        self.fig.savefig(out/(name+'.pdf'), metadata={'Creator': 'Python Matplotlib',
                         'Producer': None, 'CreationDate': None, 'ModDate': None})
        plt.close(self.fig)


def running(out):
    d = Drawing(14.8, 7.8)
    d.text(3.6, 7.35, '(a) Behavior-preserving variants')
    d.text(10, 7.35, '(b) Detector-visible cells')
    for x, y, label in [(1.8, 5.8, '$p$\nreturn $x+1$'),
                        (5.2, 5.8, '$p^{s}$\nreturn $1+x$'),
                        (1.8, 3.5, '$p^{l}$\nlet $y=x+1$;\nreturn $y$'),
                        (5.2, 3.5, '$p^{sl}$\nlet $y=1+x$;\nreturn $y$')]:
        d.box(x, y, 2.6, 1.6, label)
    for y in (5.8, 3.5):
        d.line([(3.15, y), (3.85, y)], arrow=True)
        d.line([(3.85, y), (3.15, y)], arrow=True)
        d.text(3.5, y+.35, 'swap', 8)
    for x in (1.8, 5.2):
        d.line([(x, 5), (x, 4.3)], arrow=True)
        d.line([(x, 4.3), (x, 5)], arrow=True)
        d.text(x+.34, 4.65, 'let', 8)
    d.ax.add_patch(Rectangle((.3, 2.45), 6.4, 4.4, fill=False, lw=.6, ls='--'))
    d.box(10, 5.8, 3.6, 1.6, 'left-order cell\n$p,\\ p^l$\nmessage 0')
    d.box(10, 3.5, 3.6, 1.6, 'right-order cell\n$p^s,\\ p^{sl}$\nmessage 1')
    d.line([(6.7, 4.65), (7.5, 4.65), (8.2, 5.8)], arrow=True)
    d.line([(7.5, 4.65), (8.2, 3.5)], arrow=True)
    d.text(9.8, 2.1, '(c) After operand normalization')
    d.box(9.8, .95, 4.4, 1.45, 'one operational cell\none fixed message\nno owner-selected bit')
    d.line([(11.8, 5.8), (13.4, 5.8), (13.4, .95), (12, .95)], arrow=True)
    d.line([(11.8, 3.5), (13.4, 3.5)])
    d.save(out, 'running')


def triangle(out):
    d = Drawing(14.2, 6.2)
    d.text(3.3, 5.75, '(a) One component')
    pts = [(1.7, 2.7), (4.9, 2.7), (3.3, 4.8)]
    d.line([*pts, pts[0]])
    for i, (x, y) in enumerate(pts):
        d.box(x, y, .85, .85, '$J_'+str(i)+'$', circle=True)
    d.text(3.3, 2.05, '$e_A$')
    d.text(4.65, 4, '$e_B$')
    d.text(1.95, 4, '$e_C$')
    d.text(3.3, .65, '$\\mathrm{pc}(T)=1$')
    d.text(10.4, 5.75, '(b) Two coordinated components')
    for row in range(3):
        for col in range(3):
            x, y = 9.4+col, 4.5-row
            if row < 2 and col < 2:
                d.ax.add_patch(Rectangle((x-.5, y-.5), 1, 1, color='.93', zorder=0))
            d.ax.add_patch(Rectangle((x-.5, y-.5), 1, 1, fill=False, lw=.5))
            d.text(x, y, str((row+col) % 3))
        d.text(8.4, 4.5-row, '$J_'+str(row)+'$')
        d.text(9.4+row, 5.22, '$J_'+str(row)+'$')
    d.ax.add_patch(Rectangle((8.84, 2.94), 2.12, 2.12, fill=False, lw=.65, ls='--'))
    d.text(10.4, 1.55, '$2\\times2$ constraint')
    d.text(10.4, 1.1, '$\\chi(i,j)=i+j\\ (\\mathrm{mod}\\ 3)$')
    d.text(10.4, .65, '$\\mathrm{pc}(T\\boxtimes T)=3$')
    d.save(out, 'triangle-product')


def stochastic(out):
    d = Drawing(14.6, 4.8)
    titles = ['Deterministic', 'Private decoder coins', 'Shared coloring coins']
    labels = [['$0$', '$0$', '$1$'], ['$0$', '$1/2$', '$1$'],
              ['$\\chi_1$', '$\\chi_2$', '$\\chi_3$']]
    notes = ['one monochromatic edge\nworst value $1/2$',
             'node entries are $\\Pr[1]$\nworst value $3/4$',
             'uniform over six\nnonconstant colorings\nworst value $5/6$']
    for i, x in enumerate((2.4, 7.3, 12.2)):
        d.text(x, 4.4, titles[i])
        points = [(x, 3.5), (x-.95, 2.1), (x+.95, 2.1)]
        d.line([*points, points[0]])
        for (px, py), label in zip(points, labels[i]):
            d.box(px, py, .8, .8, label, circle=True)
        d.text(x, .85, notes[i])
    d.save(out, 'stochastic-triangle')


def capacity(out):
    table = Path(__file__).resolve().parents[1]/'generated/capacity_table.csv'
    with table.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    # This example is specified independently of any runtime measurement.
    # The retained table must contain its four exact message/bit pairs.
    observed = [(int(row['program_variants']), int(row['quotient_cells']),
                 int(row['exact_messages']), int(row['guaranteed_bits'])) for row in rows]
    if observed != [(8, 8, 8, 3), (8, 4, 4, 2), (8, 2, 2, 1), (8, 1, 1, 0)]:
        raise ValueError('Retained capacity table does not match the illustrated chain')
    d = Drawing(14.7, 6.6)
    d.text(1.8, 6.15, 'operational partition', 8)
    d.text(12.4, 6.15, 'exact capacity', 8)
    labels = ['$p$', '$p^a$', '$p^b$', '$p^{ab}$', '$p^c$', '$p^{ac}$', '$p^{bc}$', '$p^{abc}$']
    for row, (group, name) in enumerate([(1, 'singletons'), (2, 'pairs'),
                                       (4, 'blocks of four'), (8, 'complete closure')]):
        y = 5.35-row*1.4
        d.text(1.65, y, name)
        for i, label in enumerate(labels):
            d.box(3.5+.7*i, y, .62, .48, label)
        for start in range(0, 8, group):
            d.ax.add_patch(Rectangle((3.16+.7*start, y-.38), .7*group-.02, .76,
                                     fill=False, lw=.85, zorder=3))
        messages = 8//group
        d.text(11, y, str(messages)+(' message' if messages == 1 else ' messages'))
        d.text(13.4, y, str(3-row)+(' bit' if row == 2 else ' bits'))
        if row < 3:
            d.line([(.3, y-.7), (14.4, y-.7)])
            d.line([(9.4, y-.42), (9.4, y-.98)], arrow=True)
    d.save(out, 'capacity-closure')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    for draw in (running, triangle, stochastic, capacity):
        draw(args.outdir)


if __name__ == '__main__':
    main()
