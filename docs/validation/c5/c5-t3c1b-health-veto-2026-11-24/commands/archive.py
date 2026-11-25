from pathlib import Path
import gzip,hashlib,json,shutil
root=Path.cwd();out=root/'docs/validation/c5/c5-t3c1b-health-veto-2026-11-24'
out.mkdir(exist_ok=False);manifest=[]
def archive(source,dest):
    raw=source.read_bytes();target=out/dest
    encoding='identity' if source.suffix in ('.gz','.sqlite3','.tsv','.sh','.png','.py') else 'gzip'
    if encoding=='gzip':target=target.with_name(target.name+'.gz')
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists(),target
    target.write_bytes(raw if encoding=='identity' else gzip.compress(raw,mtime=0))
    manifest.append(dict(source=str(source),path=str(target.relative_to(out)),encoding=encoding,original_bytes=len(raw),
        original_sha256=hashlib.sha256(raw).hexdigest(),archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
live=Path('/tmp/c5-t3c1b-live-20261124')
for source in sorted(live.rglob('*')):
    if source.is_file():archive(source,Path('live')/source.relative_to(live))
for folder in sorted(Path('/tmp').glob('c5-t3c1b-native-20261124-a*'))+sorted(Path('/tmp').glob('c5-t3c1b-legacy-*-20261124')):
    for name in ('build-test.log','source-sha256.txt','binary-sha256.txt','packages.tsv','image-id.txt'):
        source=folder/name
        if source.exists():archive(source,Path('native')/folder.name/name)
for source in sorted(Path('/tmp').glob('c5-t3c1b*.log')):
    archive(source,Path('commands/logs')/source.name)
for pattern in ('c5-t3c1b*20261124.tsv','c5-t3c1b*20261124.sh','c5-t3c1b*20261124.json'):
    for source in sorted(Path('/tmp').glob(pattern)):archive(source,Path('commands')/source.name)
archive(Path('/tmp/c5-t3c1b-ros-build-20261124/build.log'),Path('commands/ros-overlay-build.log'))
archive(Path('/tmp/c5-t3c1b-health-veto-20261124.png'),Path('diagram-preview.png'))
archive(Path('/tmp/c5-t3c1b-archive-20261124.py'),Path('commands/archive.py'))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Archived',len(manifest),'files;',sum((out/m['path']).stat().st_size for m in manifest),'bytes')
