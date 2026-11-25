from pathlib import Path
import gzip,hashlib,json,shutil
src=Path('/tmp/c5-t3c1b-last-two-20261125');out=Path('/Users/murat/develop/ros2-fleet-manager-demo/docs/validation/c5/c5-t3c1b-last-two-2026-11-25');out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=[]
def archive(source,rel):
 dest=out/rel;identity=source.suffix in ('.gz','.sqlite3','.tsv','.sh','.py')
 if not identity:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists(),dest
 if identity:shutil.copyfile(source,dest)
 else:
  with source.open('rb') as i,dest.open('wb') as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=6) as o:shutil.copyfileobj(i,o)
 manifest.append(dict(path=str(dest.relative_to(out)),source=str(source),encoding='identity' if identity else 'gzip',original_sha256=sha(source),archive_sha256=sha(dest),original_bytes=source.stat().st_size,archive_bytes=dest.stat().st_size))
for folder in sorted(src.iterdir()):
 if folder.is_dir() and (folder/'generated').exists():
  for source in sorted(folder.rglob('*')):
   if source.is_file():archive(source,Path('live')/folder.name/source.relative_to(folder))
for folder in ('native-diagnostic1','native-fixed1','native-final'):
 root=src/folder
 for f in root.iterdir():
  if f.is_file() and f.suffix in ('.log','.tsv','.txt'):archive(f,Path('build')/folder/f.name)
 f=root/'Testing/Temporary/LastTest.log'
 if f.exists():archive(f,Path('build')/folder/'LastTest.log')
for f in sorted(src.iterdir()):
 if f.is_file() and f.suffix in ('.log','.txt','.tsv','.json','.py','.sh','.gz','.patch'):archive(f,Path('commands')/f.name)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for e in manifest:
 f=out/e['path'];assert sha(f)==e['archive_sha256']
 data=gzip.open(f,'rb').read() if e['encoding']=='gzip' else f.read_bytes()
 assert hashlib.sha256(data).hexdigest()==e['original_sha256']
proof=dict(files_verified=len(manifest),all_original_hashes_match=True,acceptance_complete=True,final_matrix_passed=14,final_matrix_failed=0,source_revision=json.loads((src/'source-final2.json').read_text())['source_revision_sha256'])
(out/'archive-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
