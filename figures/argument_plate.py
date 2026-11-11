"""Regenerate the paper's mechanism figures."""
import argparse
import json
from pathlib import Path
from article_diagrams import FIGURES
from diagram_ink import emit
from figure_style import paper_style
from figure_style import Plate, BLUE, TEAL, AMBER, MUTED
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Bbox


def check_labels(d, placed, arrows):
    """Verify labels against reserved space and every horizontal or vertical route."""
    d.fig.canvas.draw()
    render=d.fig.canvas.get_renderer()
    tf=d.ax.transData
    canvas=d.fig.bbox
    boxes=[]
    for text,reserved in placed:
        box=text.get_window_extent(render)
        (x0,y0),(x1,y1)=tf.transform(((reserved[0],reserved[1]),(reserved[2],reserved[3])))
        assert box.x0>=x0-.5 and box.x1<=x1+.5 and box.y0>=y0-.5 and box.y1<=y1+.5, text.get_text()
        assert canvas.contains(box.x0,box.y0) and canvas.contains(box.x1,box.y1),text.get_text()
        assert not any(box.overlaps(other) for other in boxes),text.get_text()
        for (a,b) in arrows:
            (ax,ay),(bx,by)=tf.transform((a,b))
            rect=Bbox.from_extents(min(ax,bx)-1.5,min(ay,by)-1.5,max(ax,bx)+1.5,max(ay,by)+1.5)
            assert not box.overlaps(rect),(text.get_text(),a,b)
        boxes.append(box)


def source_access(spec,out,previews):
    width=spec.get('width',420)
    labels=[]
    arrows=[]
    # The rows are the exact illustrative access sets in the paper.
    base=((1,1,0),(0,1,1),(1,0,1))
    changed=((1,1,1),*base[1:])
    coloring=(1,1,0)
    assert all({coloring[i] for i,hit in enumerate(row) if hit}=={0,1} for row in changed)
    d=Plate(width,99)
    for start, title, matrix in ((32,'(a) Two targets per source',base),(226,'(b) Add one target',changed)):
        labels.append((d.text(start+71,90,title,9.5,weight='bold'),(start,82,start+153,99)))
        for j in range(3):
            x=start+50+j*29
            labels.append((d.text(x,70,rf'$x_{j}$',9.3),(x-12,63,x+12,78)))
            for i in range(3):
                if j==0:
                    y=52-i*17
                    labels.append((d.text(start+19,y,rf'$x_{i}$',9.3),(start+6,y-7,start+32,y+7)))
                y=52-i*17
                if matrix[i][j]:
                    one=start>50 and coloring[j]==1
                    if one:
                        d.ax.add_patch(Rectangle((x-3.4,y-3.4),6.8,6.8,
                                                 facecolor=TEAL,edgecolor=TEAL,zorder=3))
                    else:
                        d.ax.add_patch(Circle((x,y),4,facecolor=BLUE,edgecolor=BLUE,zorder=3))
                    if start>50 and i==0 and j==2:
                        d.ax.add_patch(Circle((x,y),7,fill=False,edgecolor=AMBER,linewidth=1.15,zorder=3))
                else:
                    d.rule(x-3,y,x+3,y,c=MUTED,lw=.85)
    a,b=(170,43),(222,43)
    d.arrow(a,b,color=AMBER);arrows.append((a,b))
    labels.append((d.text(196,55,'Add access',8.7,color=AMBER),(171,49,222,62)))
    d.ax.add_patch(Circle((253,6),2.4,facecolor=BLUE,edgecolor=BLUE,zorder=3))
    d.text(260,6,'Label 0',8.3,ha='left',color=BLUE)
    d.ax.add_patch(Rectangle((310,3.5),5,5,facecolor=TEAL,edgecolor=TEAL,zorder=3))
    d.text(320,6,'Label 1',8.3,ha='left',color=TEAL)
    check_labels(d,labels,arrows)
    d.save(out,spec['name'],previews)


def draw(spec,out,previews=None):
    name=spec['name']
    if name in FIGURES:
        return emit(name,out,previews)
    if name=='source-access':
        return source_access(spec,out,previews)
    raise ValueError(name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--previews',type=Path)
    args=parser.parse_args()
    spec=json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))
    paper_style(spec['venue'])
    for item in spec['figures']:
        draw(item,args.output,args.previews)


if __name__=='__main__':
    main()
