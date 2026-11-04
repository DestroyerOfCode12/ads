"""Single source of truth for timing (frames at 30 fps, 480 total)."""
import math
FPS=30; N=480
Q="web design Midrand"
T_TYPE0=48; T_KEY=3.5           # first keystroke frame, frames per key
T_ENTER=120; T_RES=128          # enter key, results scene appears
T_PIN=150
T_CUR0=172; T_HOVER=204
T_INS0=212; T_CLICK=222; T_INS1=236   # trackpad insert, click
T_SITE=246                      # site scene appears
T_PULL0=328; T_PULL1=398
T_PHONE=350
T_END=400                       # crossfade to end card starts
END_ITEMS=dict(shapes=(404,428),logo=(414,426),tag=(424,434),wa=(432,442),area=(440,450))

def clamp(v,a=0,b=1): return max(a,min(b,v))
def smooth(t): t=clamp(t); return t*t*(3-2*t)
def ease_io(t): t=clamp(t); return 0.5-0.5*math.cos(math.pi*t)
def ease_out(t): t=clamp(t); return 1-(1-t)**3

def key_frames():
    return [round(T_TYPE0+i*T_KEY) for i in range(len(Q))]

def ui_state(f):
    """Laptop screen UI state for frame f (only meaningful for f<T_END)."""
    kf=key_frames()
    if f<T_RES:
        n=sum(1 for k in kf if f>=k)
        typing = T_TYPE0<=f<kf[-1]+6
        caret = typing or (f//15)%2==0
        s=dict(scene='home',q=Q[:n],caret=caret and f<T_ENTER)
        if f>=T_ENTER: s['progress']=round(clamp((f-T_ENTER)/10)*0.7,3)
        return s
    if f<T_SITE:
        s=dict(scene='results',q=Q,reveal=round(clamp((f-T_RES-14)/24),3),pin=round(clamp((f-T_PIN)/10),3))
        if f<T_RES+4: s['progress']=round(0.7+0.3*(f-T_RES)/4,3)
        # cursor glides in from lower right to the result title
        if f>=T_CUR0:
            t=ease_io((f-T_CUR0)/(T_HOVER-T_CUR0))
            x0,y0=1180,880; x1,y1=470,646
            s['cur']=[round(x0+(x1-x0)*t,1),round(y0+(y1-y0)*t+math.sin(t*math.pi)*-40,1)]
            s['hover']=f>=T_HOVER-2
        if f>=T_INS1:
            s['press']=f<T_INS1+3; s['ring']=round(clamp((f-T_INS1)/9),3)
            s['progress']=round(clamp((f-T_INS1-2)/8)*0.6,3)
        return s
    s=dict(scene='site',load=round(clamp((f-T_SITE)/26),3))
    if f<T_SITE+6: s['progress']=round(0.6+0.4*(f-T_SITE)/6,3)
    return s

# camera: crop rect in plate coords (centre x, centre y, width); plate 3072x5456
PW,PH=3072,5456
WIDE=(1536,2728,3072)
WIDE2=(1560,2700,2860)
def cam_plate(f):
    # key framings derived from screen homography (see composite.py) -> set there
    raise NotImplementedError
