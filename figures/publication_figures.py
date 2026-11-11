"""Exact finite semantic objects, not empirical estimates."""
import csv
import json
from fractions import Fraction
from itertools import product
from math import cos, sin, tau
from pathlib import Path

from figure_style import Plate, TEAL, BLUE, PURPLE, INK, LIGHT, MINT, RULE, MUTED, arguments, paper_style

HERE=Path(__file__).resolve().parent

def running(out,preview):
    from diagram_ink import emit
    emit('running',out,preview)

def closure(out,preview):
    with (HERE/'../generated/capacity_table.csv').open(encoding='utf8',newline='') as f:
        rows=list(csv.DictReader(f))
    assert [(int(r['program_variants']),int(r['quotient_cells']),
             int(r['exact_messages']),int(r['guaranteed_bits'])) for r in rows]==[
             (8,8,8,3),(8,4,4,2),(8,2,2,1),(8,1,1,0)]
    d=Plate(410,132)
    d.head(7,120,'Closure')
    d.head(87,120,'Same eight program variants')
    d.head(312,120,'Messages')
    d.head(374,120,'Bits')
    names=['Singletons','Pairs','Groups of four','Complete closure']
    variants=['p','p^a','p^b','p^{ab}','p^c','p^{ac}','p^{bc}','p^{abc}']
    for j,v in enumerate(variants):
        d.text(99+j*26,100,'$'+v+'$',10.5)
    for i,(n,row) in enumerate(zip(names,rows)):
        y=81-i*23
        group=2**i
        d.text(7,y,n,9,ha='left')
        for j in range(0,8,group):
            d.frame(92+j*26,y-5.5,26*(group-1)+14,11,
                    fill='white',edge=RULE)
            if group>1:d.rule(99+j*26,y,99+(j+group-1)*26,y,c=TEAL,lw=.74)
            for k in range(j,j+group):
                d.dot(99+k*26,y,'',edge=TEAL,r=2.4)
        d.text(334,y,row['exact_messages'],10,color=TEAL,weight='bold')
        d.text(384,y,row['guaranteed_bits'],10,color=PURPLE,weight='bold')
    d.save(out,'capacity-closure',preview)

def associativity(out, preview):
    s=json.loads((HERE/'../results/associativity/summary.json').read_text(encoding='utf8'))
    edges=s['source_edges']
    assert [len(e) for e in edges]==s['local_reachable_cells']==[3]*5
    links={(i,j) for i,edge in enumerate(edges) for j in edge if i<j}
    assert len(links)==5 and all((i in edges[j]) for i,j in links)
    assert s['capacity']==2 and s['two_rotation_capacity']==5
    assert s['ternary_colorings']==0 and all({s['labeling'][j] for j in e}=={0,1} for e in edges)
    from diagram_ink import Diagram
    d=Diagram(410,107)
    d.head(9,96,'(a) One rotation')
    coords={i:(44+25*sin(tau*k/5),44+22*cos(tau*k/5)) for k,i in enumerate([0,1,3,4,2])}
    for i,j in links:d.rule(*coords[i],*coords[j],c=BLUE,lw=1.1)
    for i,(x,y) in coords.items():
        d.dotmark(x,y,7,c=BLUE,fill=LIGHT)
        d.node_label(x,y,rf'$J_{i}$',8.6)
    for j in range(5):
        d.text(109+j*17,75,rf'$J_{j}$',9.2)
    for i in range(5):
        d.text(91,64-i*11,rf'$p_{i}$',9.2)
        for j in range(5):
            x,y=109+j*17,64-i*11
            live=j in edges[i]
            d.band(x-7.5,y-4.5,15,9,MINT if live else '#f5f6f7')
            if live:
                d.node_label(x,y,str(s['labeling'][j]),9.2,color=INK)
            else:
                d.rule(x-2.5,y,x+2.5,y,c=MUTED,lw=.88)
    d.head(216,96,'(b) Two rotations')
    for i in range(5):
        x=224+i*35
        d.dotmark(x+14,54,9,c=PURPLE)
        d.node_label(x+14,54,rf'$J_{i}$',9.1)
        d.text(x+14,24,f'Label {i}',9.2)
    d.save(out,'associativity-access',preview)

def stochastic(out,preview):
    edges=((0,1),(0,2),(1,2))
    half=Fraction(1,2)
    value=lambda labels,e:(1+abs(labels[e[0]]-labels[e[1]]))/2
    nonconstant=[tuple(map(Fraction,c)) for c in product((0,1),repeat=3) if len(set(c))>1]
    det=(Fraction(0),Fraction(0),Fraction(1))
    priv=(Fraction(0),half,Fraction(1))
    values=([value(det,e) for e in edges],[value(priv,e) for e in edges],
            [sum(value(c,e) for c in nonconstant)/len(nonconstant) for e in edges])
    assert tuple(min(v) for v in values)==(half,Fraction(3,4),Fraction(5,6))
    from diagram_ink import Diagram
    d=Diagram(414,136.8)
    for k,(x,title,labels,note) in enumerate(zip(
            [69,207,345],['(a) Deterministic','(b) Private coins','(c) Shared coins'],
            [['0','0','1'],['0','1/2','1'],[r'$\chi_0$',r'$\chi_1$',r'$\chi_2$']],
            ['Fixed labels','Node values: Pr[1]','One of six colorings'])):
        d.text(x,126,title,10,weight='bold')
        xy=[(x-33,55),(x,92),(x+33,55)]
        for (i,j),v,(dx,y) in zip(edges,values[k],[(-34,77),(0,48),(34,77)]):
            worst=v==min(values[k])
            d.rule(*xy[i],*xy[j],c=PURPLE if worst else MUTED,ls='--' if worst else '-',lw=1.05)
            d.text(x+dx,y,str(v),9.1,color=PURPLE if worst else MUTED)
        for (px,py),lab in zip(xy,labels):
            d.dotmark(px,py,9,c=BLUE)
            d.node_label(px,py,lab,9.1)
        d.text(x,28,note,9.1)
        d.text(x,13,'Minimum: '+str(min(values[k])),9,color=PURPLE,weight='bold')
    d.save(out,'stochastic-triangle',preview)

def support_bridge(out,preview):
    from diagram_ink import emit
    emit('support-bridge',out,preview)

def proof_route(out,preview):
    from diagram_ink import emit
    emit('proof-route',out,preview)


if __name__=='__main__':
    args=arguments();paper_style('toplas')
    for draw in (running,closure,associativity,stochastic,support_bridge,proof_route):draw(args.outdir,args.previews)
    from diagram_ink import emit_supplemental
    emit_supplemental(args.outdir,args.previews)
