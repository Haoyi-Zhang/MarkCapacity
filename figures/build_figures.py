"""Direct vector illustrations for the declared capacity instances.

Run with Python and Matplotlib; no TeX executable or private project is used.
The numeric illustration is derived from the retained capacity table.
"""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

from figure_style import paper_style



class Drawing:
    def __init__(self, width, height):
        self.fig = plt.figure(figsize=(width/2.54, height/2.54))
        self.ax = self.fig.add_axes([0, 0, 1, 1], xlim=(0, width), ylim=(0, height))
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.labels = []

    def text(self, x, y, text, size=9.7, **kw):
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
    d.text(10.4, .65, '$\\mathrm{pc}(T\\mathcal{\\boxtimes} T)=3$')
    d.save(out, 'triangle-product')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    from publication_figures import closure, running, stochastic
    paper_style('toplas')
    for draw in (running, stochastic, closure):
        draw(args.outdir, None)
    triangle(args.outdir)


if __name__ == '__main__':
    main()
