"""Program equivalence, operational closure, and access drawn as relations."""
from diagram_ink import Diagram,S,T,A,K,G,F,L,P


def running():
    d=Diagram(411,154)
    d.tag(10,143,'(a) Local rewrites')
    d.tag(208,143,'(b) Decoder quotient')
    # The two rows carry each program form into its operational cell.
    for y,expr,plain,temporary,lab,members,color in [
        (104,'x+1',r'$p$',r'$p^\ell$','Label 0',r'$\{p,p^\ell\}$',S),
        (54,'1+x',r'$p^s$',r'$p^{s\ell}$','Label 1',r'$\{p^s,p^{s\ell}\}$',T),
    ]:
        d.txt(44,y+20,temporary,10)
        d.zone(12,y-13,64,26,c=F,fill='white',dash=False)
        d.txt(44,y+5,rf'let $y={expr}$',8.7)
        d.txt(44,y-6,r'return $y$',8.7)
        d.zone(116,y-11,75,22,c=F,fill='white',dash=False)
        d.txt(153.5,y+20,plain,10)
        d.txt(153.5,y,'return $' + expr + '$',8.7)
        d.wire((79,y),(112,y),c=G)
        d.wire((194,y),(214,y),c=color)
        d.zone(217,y-11,66,22,c=color,fill='white',dash=False)
        d.node_label(250,y,members,9.9)
        d.txt(250,y-19,lab,9.0,color=color)
        d.wire((285,y),(301,y),(301,79),c=color,arrow=False)
    d.txt(205,118,'Cell',8.2)
    d.wire((179,91),(179,67),c=S,dash=True,arrow=False)
    d.txt(185,79,'Swap',8.5,ha='left',color=S)
    d.wire((301,79),(322,79),c=G)
    d.dotmark(301,79,1.8,c=G,fill=G)
    d.txt(360,108,'Normalize operands',8.8)
    d.zone(325,66,80,26,c=G,fill=P,dash=False)
    d.node_label(365,79,r'$\{p,p^\ell,p^s,p^{s\ell}\}$',9.4)
    d.txt(365,53,'One operational cell',8.8)
    d.wire((12,18),(29,18),c=G)
    d.txt(34,18,'Eliminate temporary',8.5,ha='left')
    d.txt(305,18,r'$1\ \mathrm{bit}\ \to\ 0\ \mathrm{bits}$',10)
    return d


def support_bridge():
    d=Diagram(410,104)
    d.tag(9,94,'(a) Close, then restrict')
    d.tag(214,94,'(b) Restrict, then close')
    for x,y,s,c in [(44,37,'a',T),(164,37,'b',T),(104,72,'z',G),
                    (254,37,'a',T),(365,37,'b',T)]:
        d.dotmark(x,y,6.6,c=c)
        d.node_label(x,y,s,9.8)
    d.wire((51,41),(97,68),c=S,dash=True,arrow=False)
    d.wire((111,68),(157,41),c=A,arrow=False)
    d.txt(65,60,'D',9.2,color=S)
    d.txt(144,60,'A',9.2,color=A)
    d.txt(104,20,r'$\{a,b\}$',10.2,color=T)
    d.txt(254,20,r'$\{a\}$',10.2,color=T)
    d.txt(365,20,r'$\{b\}$',10.2,color=T)
    d.txt(308,65,r'$z\notin S$',10,color=G)
    return d


def proof_route():
    d=Diagram(411,83)
    d.tag(13,73,'(a) Refinement')
    d.tag(214,73,'(b) Cross-class cells')
    # The right-hand outlines are incidence sets, not classes of programs.
    # Both edges in that panel contain the same vertex J1.
    for x,w,c,dash in ((13,77,S,False),(103,77,T,True),
                       (220,103,S,False),(287,108,T,True)):
        d.zone(x,33 if x==287 else 31,w,23,c=c,dash=dash,fill='none')
    for x,s in ((51,r'$e_{C_0}$'),(141,r'$e_{C_1}$'),
                (247,r'$e_{C_0}$'),(370,r'$e_{C_1}$')):
        d.txt(x,61,s,9)
    for x,i in ((35,0),(68,1),(125,2),(158,3),(245,0),(305,1),(370,2)):
        d.dotmark(x,42,7,c=G,fill=P if x==305 else 'white')
        d.node_label(x,42,rf'$J_{i}$',9.0)
    d.node_label(97,12,r'$|M|_{\max}=\min_C\,|C/{\equiv}_{J}|$',10)
    d.node_label(307,12,r'One label for the shared $J_1$',9.8)
    return d


def interface_contracts():
    d=Diagram(420,99)
    y=67
    d.mark('code',18,y,17,S)
    d.txt(32,y,r'$p$',10.7,ha='left')
    d.wire((42,y),(69,y),c=S)
    d.node_label(101,y,r'$R(p)$',11)
    d.txt(101,86,'Rewrite targets',9.4)
    d.wire((120,y),(177,y),c=S)
    d.diamond(185,y,6,S)
    d.txt(185,86,'Filter',9.4)
    d.wire((194,y),(287,y),c=S)
    d.txt(242,79,r'$R(p)\cap C_p$',10.4)
    d.diamond(296,y,6,T)
    d.txt(296,86,'Project',9.4)
    d.wire((305,y),(353,y),c=T)
    d.node_label(380,y,r'$a_p^R$',11.5,color=T)
    d.txt(380,85,'Access edge',9.4)
    d.txt(12,39,'Context observations',9.3,ha='left')
    d.wire((110,39),(161,39),c=S)
    d.node_label(185,39,r'$C_p$',10.7,color=S)
    d.wire((185,47),(185,58),c=S)
    d.txt(12,15,'Detector and attack closure',9.3,ha='left')
    d.wire((130,15),(279,15),c=T)
    d.node_label(296,15,r'$V_J$',10.7,color=T)
    d.wire((296,23),(296,58),c=T)
    return d


def predicate_toggle():
    d=Diagram(420,69)
    d.tag(8,54,'Recognition')
    d.tag(8,20,'Insertion')
    d.dotmark(121,54,7,c=S)
    d.node_label(121,54,r'$J$',9.2,color=S)
    d.wire((131,54),(186,54),c=S)
    d.mark('lens',197,54,14,S)
    d.txt(211,54,r'$W(J)$',10.5,ha='left',color=S)
    d.mark('code',121,20,17,T)
    d.txt(142,20,r'$p$',10,color=T)
    d.wire((152,20),(219,20),c=T)
    d.txt(185,31,'Reachable',8.7,color=T)
    d.dotmark(223,20,1.8,c=T,fill=T)
    for y,b in [(34,0),(8,1)]:
        d.wire((223,20),(247,y),(300,y),c=T)
        if b==0:d.dotmark(311,y,5.5,c=S)
        else:d.block(306,y-4.5,10,9,T,P)
        d.txt(325,y,rf'$W={b}$',10,ha='left')
    return d


FIGURES={f.__name__.replace('_','-'):f for f in (
    running,support_bridge,proof_route,interface_contracts,predicate_toggle)}
