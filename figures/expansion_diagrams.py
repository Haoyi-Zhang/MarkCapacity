"""Illustrations of decoder fibers and Fano incidence."""
from math import sqrt
from matplotlib.patches import Circle
from diagram_ink import Diagram, S, T, A, G, F

def decoder_fibers():
    d=Diagram(420,77)
    d.txt(78,64,'Label 0 fiber',9.7,color=S)
    d.txt(342,64,'Label 1 fiber',9.7,color=T)
    for y,i,j,k in [(43,0,1,3),(17,1,2,4)]:
        d.wire((100,y),(186,y),c=S,arrow=False)
        d.wire((234,y),(320,y),c=T,arrow=False)
        d.dotmark(90,y,7.3,c=S)
        d.node_label(90,y,rf'$v_{j}$',9.1,color=S)
        d.block(322,y-7.5,15,15,T,'white')
        d.node_label(329.5,y,rf'$v_{k}$',9.1,color=T)
        d.txt(210,y,rf'$e_{i}$',11.1)
    return d

def fano_incidence():
    d=Diagram(420,122)
    a,b,c=(48,20),(150,20),(99,20+51*sqrt(3))
    mid=lambda p,q:tuple((x+y)/2 for x,y in zip(p,q))
    xy={0:a,1:b,2:c,3:mid(a,b),4:mid(b,c),6:mid(c,a)}
    xy[5]=(99,20+17*sqrt(3))
    for u,v in [(0,1),(1,2),(2,0),(0,4),(1,6),(2,3)]:
        d.wire(xy[u],xy[v],c=S if (u,v) in [(0,1),(1,2),(2,0)] else G,arrow=False)
    d.ax.add_patch(Circle(xy[5],17*sqrt(3),fill=False,edgecolor=T,lw=.95,ls='--',zorder=2))
    positions={0:(35,19),1:(164,19),2:(113,110),3:(99,8),4:(135,70),5:(113,51),6:(63,70)}
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

def finite_certificate():
    d=Diagram(420,93)
    d.tag(9,82,'Observed prefix')
    d.tag(169,82,'Continuation')
    d.tag(240,82,'What follows')
    lanes=[(61,'0010','00...',T,'One observed 1 suffices'),
           (29,'0000','00...',G,'All-zero continuation'),
           (10,'0000','10...',S,'A later 1 is still possible')]
    for y,prefix,suffix,c,label in lanes:
        for i,bit in enumerate(prefix):
            x=19+i*25
            d.block(x-8,y-6,16,12,T if bit=='1' else F,'white')
            d.node_label(x,y,bit,9.5,color=T if bit=='1' else G)
        d.wire((115,y),(164,y),c=c,dash=y!=61)
        d.txt(194,y,suffix,10.0,color=c)
        d.txt(240,y,label,9.6,ha='left',color=c)
    return d


FIGURES={'decoder-fibers':decoder_fibers,'fano-incidence':fano_incidence,
         'finite-certificate':finite_certificate}
