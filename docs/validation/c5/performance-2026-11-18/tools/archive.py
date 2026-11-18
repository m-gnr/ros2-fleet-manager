import sys,json,gzip,shutil,hashlib
from pathlib import Path
source=Path(sys.argv[1]);target=Path(sys.argv[2]);target.mkdir(parents=True,exist_ok=True)
selected=[]
for path in source.rglob('*'):
 if not path.is_file():continue
 rel=path.relative_to(source)
 if any(x in ('tools','ros2-fleet-c5-overlay') for x in rel.parts):continue
 if path.suffix in ('.json','.jsonl','.log','.txt','.diff','.sqlite3','.sdf','.yaml') or path.name=='source-sha256.json':selected.append(path)
for path in selected:
 rel=path.relative_to(source)
 if len(rel.parts)>3:continue
 if path.name.endswith(('.jsonl','.log','.sqlite3','.sdf')):
  dest=target/(str(rel)+'.gz');dest.parent.mkdir(parents=True,exist_ok=True)
  with path.open('rb') as f, gzip.open(dest,'wb') as out:shutil.copyfileobj(f,out)
 else:
  dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
manifest={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file() and p.name!='sha256.json'}
(target/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print(target,len(manifest),'files',sum(p.stat().st_size for p in target.rglob('*') if p.is_file()))
