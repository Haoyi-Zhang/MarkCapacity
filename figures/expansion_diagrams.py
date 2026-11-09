"""Illustrations of decoder fibers and Fano incidence."""
from math import sqrt
from matplotlib.patches import Circle
from diagram_ink import Diagram, S, T, A, G, F

def decoder_fibers():
    d=Diagram(420,77)
    d.tag(12,66,'Access edge')
    d.txt(126,66,'Fiber for label 0',9.8,color=S,bold=True)
    d.txt(247,66,'Fiber for label 1',9.8,color=T,bold=True)
    for y,i,js in [(44,0,(1,3)),(23,1,(2,4))]:
        d.txt(39,y,rf'$e_{i}$',10.8)
        for x,j,c in zip((126,247),js,(S,T)):
            d.dotmark(x-14,y,3,c=c,fill=c)
            d.txt(x+6,y,rf'$v_{j}$',10.8,color=c)
        d.mark('check',333,y,16,T)
    d.txt(358,66,'Both labels',9.6,bold=True)
    return d

def fano_incidence():
    d=Diagram(420,122)
    a,b,c=(48,15),(150,15),(99,15+51*sqrt(3))
    mid=lambda p,q:tuple((x+y)/2 for x,y in zip(p,q))
    xy={0:a,1:b,2:c,3:mid(a,b),4:mid(b,c),6:mid(c,a)}
    xy[5]=(99,15+17*sqrt(3))
    for u,v in [(0,1),(1,2),(2,0),(0,4),(1,6),(2,3)]:
        d.wire(xy[u],xy[v],c=S if (u,v) in [(0,1),(1,2),(2,0)] else G,arrow=False)
    d.ax.add_patch(Circle(xy[5],17*sqrt(3),fill=False,edgecolor=T,lw=.95,ls='--',zorder=2))
    positions={0:(35,14),1:(164,14),2:(99,113),3:(99,8),4:(135,65),5:(113,46),6:(63,65)}
    for i,(x,y) in xy.items():
        d.dotmark(x,y,2.5,c=S,fill='white')
        d.txt(*positions[i],rf'$v_{i}$',9.2)
    d.wire((200,92),(224,92),c=S,arrow=False)
    d.txt(234,92,'Triangle sides: three edges',9.8,ha='left')
    d.wire((200,64),(224,64),c=G,arrow=False)
    d.txt(234,64,'Medians: three edges',9.8,ha='left')
    d.wire((200,36),(224,36),c=T,arrow=False,dash=True)
    d.txt(234,36,r'Circle: $\{v_3,v_4,v_6\}$',9.8,ha='left')
    return d

FIGURES={'decoder-fibers':decoder_fibers,'fano-incidence':fano_incidence}
