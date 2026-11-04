import json,sys,os
sys.path.insert(0,os.path.dirname(__file__))
from timeline import *
seen={};frames={}
for f in range(T_END+1):
    s=ui_state(f); k=json.dumps(s,sort_keys=True)
    if k not in seen: seen[k]='s%03d'%len(seen)
    frames[f]=seen[k]
json.dump([{'key':v,'state':json.loads(k)} for k,v in seen.items()],open('build/states.json','w'))
json.dump(frames,open('build/frame_states.json','w'))
print(len(seen),'unique states')
