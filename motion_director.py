"""Story-directed offline animation for Science WTF: independent gestures, face,
reflections, visual explanations and locked camera. No external assets or APIs."""
from __future__ import annotations
import math
from PIL import Image
from motion_studio import _Painter, _ease, CYAN, YELLOW, PINK, WHITE, PANEL, PANEL2, MUTED, DARK

INK=(8,19,30)
TEAL_DEEP=(22,67,78)
MIRROR=(34,80,91)

def _lerp(a,b,n):
    return a+(b-a)*n

def _ease_out(t):
    t=max(0.,min(1.,t))
    return 1-(1-t)**3

def _pulse(t,speed=4.2):
    return (1+math.sin(t*speed))/2

def _blink(t,offset=0.):
    return ((t+offset)%2.7)<.11

def _circle(p,x,y,r,color,width=3):
    p.ellipse((x-r,y-r,x+r,y+r),outline=color,width=width)

def _actor(p,x,y,s,t,*,mouth=0.,feeling="curious",action="talk",mirror=False,progress=0.):
    """Articulated original character: brows, blinks, four mouth shapes and actions."""
    talk=min(1.,max(0.,mouth))
    shock=1. if feeling=="surprised" else 0.
    x+=(-8 if not mirror else 8)*shock*math.sin(min(1.,progress*2.)*math.pi/2)*s
    y+=2.5*math.sin(t*2.5)*s
    def pt(a,b):
        return (x+a*s,y+b*s)
    def ellipse(l,top,r,bottom,color,outline=None,width=2):
        p.ellipse((*pt(l,top),*pt(r,bottom)),fill=color,outline=outline,width=width*s)
    def stroke(coords,color,width):
        p.line([pt(a,b) for a,b in coords],color,width*s)
    ellipse(-56,166,60,180,(7,18,30))
    step=math.sin(t*6.2)*22 if action=="walk" else 3*math.sin(t*1.8)
    for sign,swing in ((-1,step),(1,-step)):
        knee=(sign*22+swing*.4,114)
        foot=(sign*34+swing,159)
        stroke([(0,59),knee,foot],INK,18)
        stroke([(0,59),knee,foot],WHITE,11)
        stroke([foot,(foot[0]+15*sign,159)],INK,7)
        stroke([foot,(foot[0]+15*sign,159)],YELLOW if sign==1 else WHITE,3)
    if not mirror:
        p.rect((*pt(19,-33),*pt(78,78)),YELLOW,radius=13*s,outline=INK,width=5*s)
        p.line([pt(54,-22),pt(54,24)],(248,229,152),3*s)
        ellipse(49,32,61,44,INK)
    stroke([(0,-46),(0,67)],INK,23)
    stroke([(0,-46),(0,67)],WHITE,15)
    ellipse(-17,-52,17,-26,WHITE,outline=INK,width=4)
    if action=="point":
        left=[(-6,-20),(-36,-4),(-65,25)]
        right=[(7,-20),(42,-43),(105,-63)]
    elif action=="inspect":
        left=[(-6,-22),(-38,-4),(-45,-49)]
        right=[(7,-20),(41,-47),(71,-91)]
    elif action=="recoil":
        left=[(-7,-20),(-54,-56),(-70,-92)]
        right=[(7,-20),(50,-67),(78,-111)]
    elif action=="walk":
        left=[(-6,-20),(-37,-9+step*.3),(-55,29+step)]
        right=[(6,-20),(39,-4-step*.3),(55,26-step)]
    else:
        wobble=math.sin(t*4)*(9 if talk>.1 else 3)
        left=[(-6,-20),(-45,-16),(-64,9+wobble)]
        right=[(6,-20),(40,-16),(56,-17-wobble-talk*14)]
    # Gestures unfold gradually in the shot, instead of teleporting into a pose.
    if action in ("point", "inspect", "recoil"):
        blend=_ease_out(min(1.0,max(0.0,(progress-.08)/.38)))
        if action == "recoil":
            blend=_ease_out(min(1.0,max(0.0,(progress-.03)/.25)))
        rest_left=[(-6,-20),(-45,-16),(-64,9)]
        rest_right=[(6,-20),(40,-16),(56,-17)]
        def interpolated(rest,target):
            return [(_lerp(a,x,blend),_lerp(b,y,blend))
                    for (a,b),(x,y) in zip(rest,target)]
        left=interpolated(rest_left,left)
        right=interpolated(rest_right,right)
    for arm in (left,right):
        stroke(arm,INK,18)
        stroke(arm,WHITE,11)
        hx,hy=arm[-1]
        ellipse(hx-7,hy-7,hx+7,hy+7,WHITE,outline=INK,width=2)
    head_x=-3*shock*math.sin(t*3.1)
    head_y=-107-6*shock+2*math.sin(t*2.1)-1.8*talk*math.sin(t*8.5)
    ellipse(head_x-52,head_y-57,head_x+52,head_y+48,WHITE,outline=INK,width=5)
    brows=-12 if shock else -4 if feeling=="curious" else 1
    for side in (-1,1):
        ex=head_x+side*20
        if _blink(t,(side+1)*.035):
            stroke([(ex-7,head_y-5),(ex+7,head_y-5)],INK,3)
        else:
            ellipse(ex-5,head_y-12,ex+5,head_y+1,INK)
            ellipse(ex-2,head_y-11,ex,head_y-8,WHITE)
        stroke([(ex-10,head_y-22+brows),
                (ex+9,head_y-26+brows*(.45 if side<0 else 1))],INK,3)
    lip_y=head_y+25
    if talk>.75:
        ellipse(head_x-13,lip_y-10,head_x+13,lip_y+12,INK)
        stroke([(head_x-7,lip_y+5),(head_x+7,lip_y+5)],PINK,3)
    elif talk>.42:
        ellipse(head_x-12,lip_y-5,head_x+12,lip_y+8,INK)
    elif talk>.13:
        ellipse(head_x-11,lip_y-2,head_x+11,lip_y+4,INK)
    elif shock:
        ellipse(head_x-9,lip_y-8,head_x+9,lip_y+13,INK)
    else:
        stroke([(head_x-13,lip_y),(head_x,lip_y+5),(head_x+13,lip_y)],INK,3)
    if shock:
        ellipse(head_x+45,head_y+8,head_x+52,head_y+24,CYAN)

def _reflect_face(p,cx,cy,width,distortion,t):
    """Morph independent eyes/mouth and facial geometry, not the whole camera."""
    d=max(0.,min(1.,distortion))
    wobble=math.sin(t*2.3)
    fw=width*(1+d*.28*wobble)
    fh=width*(1.14+d*.38*math.sin(t*3.2+.7))
    offset=d*12*math.sin(t*3.7)
    p.ellipse((cx-fw+offset,cy-fh,cx+fw+offset,cy+fh),WHITE,outline=INK,width=5)
    for dx,dy,rscale in [(-.39,-.13,1-d*.13),(.39,-.12-d*.32*(.5+.5*wobble),1+d*.9)]:
        px=cx+dx*fw+d*12*math.sin(t*2.7+dx)
        py=cy+dy*fh
        rad=6*rscale
        p.ellipse((px-rad,py-rad,px+rad,py+rad),INK)
        p.ellipse((px-rad*.3,py-rad*.4,px,py-rad*.1),WHITE)
    if d>.3:
        p.line([(cx,cy+5),(cx-6*d,cy+21+d*12)],(128,150,160),3)
        ow=8+15*d
        oh=6+24*d
        p.ellipse((cx-ow,cy+fh*.43-oh*.4,cx+ow,cy+fh*.43+oh),INK)
    else:
        p.line([(cx-15,cy+fh*.44),(cx,cy+fh*.47+3),(cx+17,cy+fh*.42)],INK,3)
    if d>.26:
        p.line([(cx-fw*.62,cy-fh*.35),(cx+fw*.49,cy-fh*.29+d*10)],PINK,2)
        for j in range(2):
            a=(t*1.5+j*.5)%1
            ry=cy+fh*(a-.5)
            p.line([(cx-fw*.76,ry),(cx+fw*.7,ry+8*math.sin(t*3+j))],CYAN if j else PINK,2)

def _mirror(p,cx,cy,w,h,t,distortion=0.,reveal=0.):
    x1,y1,x2,y2=cx-w/2,cy-h/2,cx+w/2,cy+h/2
    p.rect((x1-11,y1-13,x2+11,y2+13),INK,radius=29,outline=CYAN,width=7)
    p.rect((x1,y1,x2,y2),MIRROR,radius=21,outline=(78,141,152),width=2)
    p.rect((x1+12,y1+18,x1+19,y2-18),TEAL_DEEP,radius=4)
    p.line([(x1+32,y1+18),(x1+47,y1+42)],(75,126,137),3)
    _reflect_face(p,cx,cy-h*.17,w*.24,distortion,t)
    p.line([(cx,cy-h*.17+w*.27),(cx,cy+h*.30)],WHITE,15)
    p.rect((cx+w*.055,cy+h*.11,cx+w*.17,cy+h*.24),YELLOW,radius=8,outline=INK,width=3)
    if reveal:
        _circle(p,cx,cy-h*.18,25+20*reveal,CYAN,3)

def _brain(p,cx,cy,t,scale=1.,build=1.):
    """Original schematic of visual reconstruction, not an anatomical claim."""
    pts=[(-78,-50),(-103,8),(-65,68),(-24,104),
         (-54,-94),(-4,-115),(52,-92),
         (78,-50),(103,8),(65,68),(24,104)]
    for i,(a,b) in enumerate(pts):
        x,y=cx+a*scale,cy+b*scale
        pulse=1+math.sin(t*3.2+i*.85)*.035
        rr=37*scale*pulse
        p.ellipse((x-rr,y-rr,x+rr,y+rr),PANEL2,outline=CYAN if i%2 else MUTED,width=3)
    p.line([(cx,cy-96*scale),(cx,cy+100*scale)],INK,7*scale)
    for i in range(len(pts)-1):
        if i/max(1,len(pts)-1)<=build:
            a,b=pts[i];e,f=pts[i+1]
            p.line([(cx+a*scale,cy+b*scale),(cx+e*scale,cy+f*scale)],YELLOW if i%2 else CYAN,3)
    for i,(a,b) in enumerate(pts):
        if i/max(1,len(pts))<=build:
            x=cx+a*scale+7*scale*math.sin(t*2.7+i)
            y=cy+b*scale
            r=5+3*_pulse(t+i*.5)
            p.ellipse((x-r,y-r,x+r,y+r),YELLOW if i%3 else PINK)

def _stage(p,kind,shot,progress,t):
    p.rect((34,196,506,203),PANEL2,radius=3)
    if progress<.17:
        p.rect((34,196,34+230*_ease_out(progress/.17),203),YELLOW,radius=3)
    for j in range(3):
        cx=70+j*205
        r=12+4*math.sin(t*2+j)
        p.ellipse((cx-r,238-r,cx+r,238+r),outline=(36,87,96),width=2)

def draw_professional_frame(base: Image.Image,kind: str,shot: int,
                            progress: float,seconds: float,mouth: float,beat_progress=None,
                            absolute_seconds=None)->Image.Image:
    """Storyboard-aware animated frame with a stable camera and independent layers."""
    frame=base.copy()
    p=_Painter(frame)
    t=progress*seconds if absolute_seconds is None else absolute_seconds
    arc=progress if beat_progress is None else beat_progress
    _stage(p,kind,shot,progress,t)
    mode=shot%4
    if kind in ("brain","neural","vision"):
        if mode in (0,2):
            _brain(p,275,438,t,1.43 if mode==2 else 1.17,build=_ease_out(min(1,progress*1.7)))
            _actor(p,102,700,.50,t,mouth=mouth,action="point",feeling="curious",progress=progress)
            if mode==2:
                for i in range(5):
                    ang=t*1.8+i*math.tau/5
                    x=275+185*math.cos(ang);y=445+175*math.sin(ang)
                    p.ellipse((x-6,y-6,x+6,y+6),YELLOW)
        elif mode==1:
            _actor(p,255,660,1.16,t,mouth=mouth,feeling="curious",action="point",progress=progress)
            _brain(p,415,358,t,.48,build=_ease_out(progress*1.8))
        else:
            _actor(p,112,674,.75,t,mouth=mouth,feeling="curious",action="inspect",progress=progress)
            _brain(p,394,394,t,.85,build=_ease_out(progress*2))
            for i in range(4):
                travel=(progress*1.2+i*.25)%1
                x=_lerp(175,299,travel)
                y=397+19*math.sin(travel*math.pi+i*.6)
                p.ellipse((x-7,y-7,x+7,y+7),CYAN)
    elif kind=="experiment":
        if mode==1:
            _actor(p,240,673,1.06,t,mouth=mouth,action="point",progress=progress)
            p.ellipse((378,300,468,390),outline=YELLOW,width=6)
            theta=t*2
            p.line([(423,345),(423+32*math.cos(theta),345+32*math.sin(theta))],YELLOW,5)
        else:
            _mirror(p,354,494,211,410,t,distortion=.10*_ease(progress))
            x=158 if mode!=0 else 18+145*_ease_out(progress*1.5)
            _actor(p,x,665,.72,t,mouth=mouth,action="inspect",progress=progress)
            p.ellipse((65,290,155,380),outline=YELLOW,width=5)
            theta=t*1.5
            p.line([(110,334),(110+30*math.cos(theta),334+30*math.sin(theta))],YELLOW,5)
    elif kind=="distort":
        if mode==0:
            _mirror(p,275,450,300,435,t,distortion=.2+.75*_ease(arc))
            _actor(p,105,702,.50,t,mouth=mouth,feeling="surprised",action="recoil",progress=progress)
        elif mode==1:
            _actor(p,266,653,1.27,t,mouth=mouth,feeling="surprised",action="recoil",progress=progress)
            _circle(p,420,331,44+16*_pulse(t),PINK,4)
            p.line([(420,302),(420,339)],YELLOW,7)
            p.ellipse((414,347,426,359),YELLOW)
        elif mode==2:
            _mirror(p,270,448,358,450,t,distortion=.36+.6*_ease_out(arc))
            _actor(p,80,712,.41,t,mouth=mouth,feeling="surprised",action="recoil",progress=progress)
        else:
            _mirror(p,145,458,202,356,t,distortion=0.)
            _mirror(p,394,458,202,356,t,distortion=.27+.70*_ease(arc))
            _actor(p,264,710,.44,t,mouth=mouth,feeling="surprised",action="point",progress=progress)
            p.line([(270,300),(270,639)],MUTED,2)
    elif kind=="outro":
        _brain(p,270,420,t,1.0,build=1.)
        _actor(p,128,703,.70,t,mouth=mouth,feeling="curious",action="point",progress=progress)
        p.text((270,710),"SCIENCE WTF",WHITE,29)
    elif kind=="reveal":
        if mode==1:
            _actor(p,262,670,1.25,t,mouth=mouth,action="talk",progress=progress)
            _circle(p,415,334,37,CYAN,4)
        else:
            _mirror(p,363,465,210,417,t,distortion=(1-_ease_out(arc))*.8,reveal=_ease_out(arc))
            _actor(p,135,685,.79,t,mouth=mouth,action="point",progress=progress)
    else:
        if mode==1:
            # A speaking character always shares the screen with the actual
            # story object, not an unrelated decorative target circle.
            _mirror(p,413,454,164,335,t,distortion=.12*_ease_out(progress))
            _actor(p,209,650,1.09,t,mouth=mouth,action="inspect",
                   feeling="curious",progress=progress)
        elif mode==2:
            _mirror(p,277,474,332,454,t,distortion=.10*_ease(progress))
            _actor(p,94,707,.48,t,mouth=mouth,action="inspect",progress=progress)
        elif mode==3:
            _mirror(p,365,460,214,398,t,distortion=.08*_pulse(t))
            _actor(p,156,676,.85,t,mouth=mouth,action="point",progress=progress)
        else:
            x=-110+260*_ease_out(progress*1.7) if kind=="approach" else 153
            _mirror(p,377,468,213,409,t,distortion=0.)
            _actor(p,x,678,.83,t,mouth=mouth,
                   action="walk" if kind=="approach" else "inspect",progress=progress)
    return frame
