from pathlib import Path
import gzip,hashlib,json,shutil
src=Path('/tmp/c5-t3c1b-final-20261125');out=Path('/Users/murat/develop/ros2-fleet-manager-demo/docs/validation/c5/c5-t3c1b-final-2026-11-25');out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=[]
for source in sorted(src.rglob('*')):
 if not source.is_file():continue
 rel=source.relative_to(src)
 # Exclude no scenario records, including failures; no secrets/binaries were mounted here.
 dest=out/rel;identity=source.suffix in ('.gz','.sqlite3','.tsv','.sh','.py')
 if not identity:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True)
 if identity:shutil.copyfile(source,dest)
 else:
  with source.open('rb') as i,dest.open('wb') as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=6) as o:shutil.copyfileobj(i,o)
 manifest.append(dict(path=str(dest.relative_to(out)),source=str(source),encoding='identity' if identity else 'gzip',original_sha256=sha(source),archive_sha256=sha(dest),original_bytes=source.stat().st_size,archive_bytes=dest.stat().st_size))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for e in manifest:
 f=out/e['path'];assert sha(f)==e['archive_sha256']
 data=gzip.open(f,'rb').read() if e['encoding']=='gzip' else f.read_bytes()
 assert hashlib.sha256(data).hexdigest()==e['original_sha256']
proof=dict(files_verified=len(manifest),all_original_hashes_match=True,acceptance_complete=False,passed=12,failed=2,source_revision='14eb4e63a2eb0c69c986aaf0f0dca71894c23b5901da72d044bfd9012b543da8')
(out/'archive-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
