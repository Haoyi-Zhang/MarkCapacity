"""Program equivalence, operational closure, and access drawn as relations."""
from diagram_ink import Diagram,S,T,A,K,G,F,L,P


def running():
    d=Diagram(411,154)
    d.tag(10,143,'(a) Local rewrites')
    d.tag(209,143,'(b) Decoder quotient')
    coords=[(34,113),(134,113),(34,61),(134,61)]
    for idx,((x,y),title,code) in enumerate(zip(coords,
            (r'$p$',r'$p^s$',r'$p^\ell$',r'$p^{s\ell}$'),
            (r'return $x+1$',r'return $1+x$',r'let $y=x+1$; return $y$',r'let $y=1+x$; return $y$'))):
        d.dotmark(x,y,3)
        d.txt(x-6,y+12,title,10,ha='right')
        if idx<2:d.txt(x+8,y-13,code,8.15,ha='left')
        else:d.txt(x+8,y-13,code,8.15)
    for y in (113,61):d.wire((38,y),(130,y),c=S,arrow=False)
    for x in (34,134):d.wire((x,109),(x,65),c=T,arrow=False)
    d.wire((9,24),(27,24),c=S,arrow=False);d.txt(33,24,'Swap',8.5,ha='left')
    d.wire((78,24),(96,24),c=T,arrow=False);d.txt(102,24,'Temporary',8.5,ha='left')
    d.zone(206,89,83,42,c=T,fill='white')
    d.zone(309,89,83,42,c=S,fill='white')
    for x,lab,programs,color in [(247,'Label 0',(r'$p$',r'$p^\ell$'),T),(350,'Label 1',(r'$p^s$',r'$p^{s\ell}$'),S)]:
        d.txt(x,122,lab,8.8,color=color)
        d.wire((x-12,104),(x+12,104),c=color,dash=True,arrow=False)
        for xx,l in zip((x-20,x+20),programs):
            d.dotmark(xx,104,7,c=color);d.txt(xx,104,l,8.6)
        d.wire((x,86),(x,69),(298,69),c=G,arrow=False)
    d.wire((298,69),(298,41),c=G)
    d.txt(306,54,'Normalize operands',8.9,ha='left')
    d.dotmark(298,30,6,c=T,fill=P);d.txt(298,14,'One operational cell',9.1)
    return d


def support_bridge():
    d=Diagram(410,104)
    d.tag(9,94,'(a) Close, then restrict')
    d.tag(214,94,'(b) Restrict, then close')
    d.zone(11,19,182,29,c=T,fill='white')
    d.zone(214,19,183,29,c=T,fill='white')
    for x,y,ch in [(45,34,'a'),(166,34,'b'),(106,69,'z'),(246,34,'a'),(365,34,'b')]:
        d.dotmark(x,y,7,c=T if ch!='z' else S);d.txt(x,y,ch,9.4)
    d.wire((52,38),(98,64),c=S,dash=True,arrow=False)
    d.wire((114,64),(159,38),c=A,arrow=False)
    d.txt(67,62,'D',8.6,color=S);d.txt(144,62,'A',8.6,color=A)
    d.txt(30,12,r'$S$',8.4,color=T)
    d.txt(102,12,r'$\{a,b\}$',9.5)
    d.txt(246,12,r'$\{a\}$',9.5);d.txt(365,12,r'$\{b\}$',9.5)
    d.txt(305,68,r'$z\notin S$',9.2,color=G)
    return d


def proof_route():
    d=Diagram(411,83)
    d.mark('graph',148,69,19)
    d.txt(163,70,r'Operational quotient $\mathrm{Prog}/{\equiv_J}$',10,ha='left')
    d.wire((205,61),(205,49),(105,49),(105,41),c=T)
    d.wire((205,49),(307,49),(307,41),c=S)
    d.txt(105,30,r'$\equiv_J\,\subseteq\,\approx$',10.2,color=T,bold=True)
    d.txt(307,30,'Cells cross behavior classes',9.4,color=S,bold=True)
    d.txt(105,13,r'$|M|_{\max}=\min_C |C/{\equiv_J}|$',10)
    d.txt(307,13,'One coloring across classes',9.3)
    return d


def interface_contracts():
    d=Diagram(420,99)
    d.tag(10,90,'Evidence from implementation')
    d.tag(306,90,'Theorem instance')
    for y,ic,label,result,c in [
            (69,'code','Context observations',r'$\approx$',S),
            (43,'join','Detector pairs + attack edges',r'$\equiv_J$',T),
            (17,'branch','Source-indexed rewrites',r'$a_p^R$',A)]:
        d.mark(ic,21,y,17,c)
        d.txt(39,y,label,9.2,ha='left')
        d.wire((174,y),(221,y),c=c)
        d.txt(244,y,result,10.6,color=c)
        d.wire((264,y),(288,y),(288,43),c=c,arrow=False)
    d.dotmark(288,43,2.2,c=G,fill=G)
    d.wire((291,43),(312,43),c=G)
    d.txt(319,43,r'$(\approx,\;\equiv_J,\;a_p^R)$',11.2,ha='left')
    return d


def predicate_toggle():
    d=Diagram(420,69)
    d.tag(8,55,'Recognition')
    d.mark('lens',116,55,16)
    d.txt(132,55,'Observed cell',9,ha='left')
    d.wire((203,55),(255,55),c=S)
    d.txt(265,55,r'$W(J)$',10,ha='left',color=S)
    d.tag(8,22,'Insertion')
    d.mark('code',116,22,16,T)
    d.txt(132,22,r'Source $p$',9,ha='left')
    d.wire((188,22),(246,22),(246,31),(297,31),c=T)
    d.wire((246,22),(246,12),(297,12),c=T)
    for yy,lab in [(31,r'Cell with $W=0$'),(12,r'Cell with $W=1$')]:
        d.dotmark(307,yy,4,c=T)
        d.txt(318,yy,lab,9.2,ha='left')
    return d


FIGURES={f.__name__.replace('_','-'):f for f in (
    running,support_bridge,proof_route,interface_contracts,predicate_toggle)}
