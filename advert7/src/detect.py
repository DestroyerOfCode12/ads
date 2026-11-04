import numpy as np, json
from PIL import Image
im=np.asarray(Image.open('assets/desk.png').convert('RGB')).astype(np.int32)
R,G,B=im[...,0],im[...,1],im[...,2]
m=(G>120)&(G>R+50)&(G>B+50)
ys,xs=np.nonzero(m)
# split laptop vs phone by region: phone is lower right
lap=(ys<3500)&(xs<2950)
ph=(ys>=3500)&(xs>2250)
out={}
for name,sel in [('laptop',lap),('phone',ph)]:
    x=xs[sel];y=ys[sel]
    print(name,len(x),x.min(),x.max(),y.min(),y.max())
    s=x+y;d=x-y
    tl=(x[s.argmin()],y[s.argmin()]);br=(x[s.argmax()],y[s.argmax()])
    tr=(x[d.argmax()],y[d.argmax()]);bl=(x[d.argmin()],y[d.argmin()])
    top=(x[y.argmin()],y[y.argmin()]);bot=(x[y.argmax()],y[y.argmax()])
    lef=(x[x.argmin()],y[x.argmin()]);rig=(x[x.argmax()],y[x.argmax()])
    print(' diag',tl,tr,br,bl);print(' axis',top,rig,bot,lef)
    out[name]={'diag':[tl,tr,br,bl],'axis':[top,rig,bot,lef]}
json.dump(out,open('build/quads_raw.json','w'),default=int)
Image.fromarray((m*255).astype(np.uint8)).save('build/mask.png')
