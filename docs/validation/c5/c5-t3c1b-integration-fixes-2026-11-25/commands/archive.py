from pathlib import Path
import gzip,hashlib,json,shutil,tarfile
root=Path.cwd();src=Path('/tmp/c5-t3c1b-recovery-20261124')
out=root/'docs/validation/c5/c5-t3c1b-integration-fixes-2026-11-25';out.mkdir(exist_ok=False)
manifest=[]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
 return h.hexdigest()
def archive(source,dest):
 target=out/dest;identity=source.suffix in ('.gz','.sqlite3','.tsv','.sh','.py')
 if not identity:target=target.with_name(target.name+'.gz')
 target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists(),target
 if identity:shutil.copyfile(source,target)
 else:
  with source.open('rb') as input_stream,target.open('wb') as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=6) as output_stream:shutil.copyfileobj(input_stream,output_stream,1024*1024)
 manifest.append(dict(source=str(source),path=str(target.relative_to(out)),encoding='identity' if identity else 'gzip',
  original_bytes=source.stat().st_size,original_sha256=sha(source),archive_bytes=target.stat().st_size,archive_sha256=sha(target)))
for folder in sorted(src.iterdir()):
 if folder.is_dir() and (folder/'generated').exists():
  for source in sorted(folder.rglob('*')):
   if source.is_file():archive(source,Path('live')/folder.name/source.relative_to(folder))
for name in ('bridge-memcheck1','bridge-memcheck2'):
 for source in sorted((src/name).rglob('*')):
  if source.is_file():archive(source,Path('diagnostics')/name/source.relative_to(src/name))
for folder in sorted(src.iterdir()):
 if not folder.is_dir() or not folder.name.startswith(('ros-fixed-','lifetime-','nav2-lifecycle','native-regression','ros-debug','debug-image','memcheck-image')):continue
 for source in sorted(folder.iterdir()):
  if source.is_file() and source.suffix in ('.log','.txt','.tsv'):
   archive(source,Path('build')/folder.name/source.name)
 if (folder/'Dockerfile').exists():archive(folder/'Dockerfile',Path('build')/folder.name/'Dockerfile')
 if (folder/'Testing/Temporary/LastTest.log').exists():archive(folder/'Testing/Temporary/LastTest.log',Path('build')/folder.name/'LastTest.log')
 latest=folder/'log/latest_build'
 if latest.exists():
  for package in sorted(latest.iterdir()):
   if package.is_dir() and (package/'stdout_stderr.log').exists():
    archive(package/'stdout_stderr.log',Path('build')/folder.name/'colcon'/package.name/'stdout_stderr.log')
for source in sorted(src.iterdir()):
 if source.is_file() and source.suffix in ('.log','.txt','.tsv','.json','.py','.sh','.gz'):
  archive(source,Path('commands')/source.name)
source_proof=json.loads((src/'frozen-source-1.json').read_text())
with tarfile.open(out/'runtime-source.tar.gz','w:gz') as tar:
 for name,digest in sorted(source_proof['files'].items()):
  p=src/'frozen-source-1'/name;assert sha(p)==digest,name;tar.add(p,arcname='runtime-source/'+name,recursive=False)
 supplement=json.loads((src/'test-fixture-supplement.json').read_text());p=src/'frozen-source-1'/supplement['path']
 assert sha(p)==supplement['sha256'];tar.add(p,arcname='runtime-source/'+supplement['path'],recursive=False)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
verified=0
for entry in manifest:
 target=out/entry['path'];assert sha(target)==entry['archive_sha256'],target
 h=hashlib.sha256();opener=gzip.open if entry['encoding']=='gzip' else open
 with opener(target,'rb') as stream:
  for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
 assert h.hexdigest()==entry['original_sha256'],target;verified+=1
proof=dict(verified_raw_files=verified,all_original_archive_hashes_match=True,runtime_source_tar_sha256=sha(out/'runtime-source.tar.gz'),
 source_revision_sha256=source_proof['source_revision_sha256'],targeted_cases=3,full_matrix_run=False,commit_push_performed=False)
(out/'archive-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
