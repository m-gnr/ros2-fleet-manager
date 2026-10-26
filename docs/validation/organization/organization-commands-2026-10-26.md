# Depo düzeni doğrulama komutları

Tarih: 26 Ekim 2026. Komutlar depo kökünde çalıştırıldı. Bu ek ürün kurulum talimatı değildir; canlı ROS/Gazebo başlatılmadı.

## Host testleri ve import

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor uv run --with-requirements requirements-c1.txt pytest tests/ ros2_ws/src/fleet_robot_executor/test/ --import-mode=importlib -q
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor uv run --with-requirements requirements-c1.txt pytest tests/ ros2_ws/src/fleet_robot_executor/test/ --import-mode=importlib --collect-only -q
PYTHONPATH=. uv run --with-requirements requirements-c1.txt python -m fleet_config config/fleet.yaml
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor uv run --with-requirements requirements-c1.txt python -c 'import fleet_config; import backend.fleet_manager.builder; import fleet_manager.event_loop; import fleet_robot_executor.state_machine; print("Host imports OK")'
```

Sonuç: **224 passed, 19 skipped in 2.97s**; keşifte **242 tests collected**; filo CLI **VALID: 2 robots; schema, semantic and file reference checks passed**. Host importları geçti. Modül seviyesinde atlanan ROS testleri keşif toplamına farklı yansır; passed + skipped toplamı keşif sayısıyla eşit olmak zorunda değildir. Bu koşu ROS 2/colcon testi değildir.

## Compose ve Python kaynak yolları

Aşağıdaki Python kontrolü on Compose birleşimini çözümler, build/Dockerfile/bind yollarını ve Git tarafından izlenen Python kaynaklarının sözdizimini denetler. İlk taramada üretilmiş install symlink'leri hata verdi; aşağıdaki düzeltilmiş kapsam izlenen kaynakları kullanır.

```python
from pathlib import Path
import subprocess,os,json,ast
base='docker/compose/docker-compose.'
combinations=[['dds'],['dds','dds-action']]+[['dds','simulation-check']]+[['dds','simulation-check','simulation-'+s] for s in ['lidar-check','nav2-check','amcl-test','b3','b3-retry','c2-3','c3-3-3']]
for combo in combinations:
    cmd=['docker','compose']
    for part in combo: cmd+=['-f',base+part+'.yml']
    cmd+=['config','--format','json']
    p=subprocess.run(cmd,env={**os.environ,'DDS_TEST_PAYLOAD':'organization-audit'},capture_output=True,text=True)
    if p.returncode: print(combo,p.returncode,p.stderr);raise SystemExit(1)
    cfg=json.loads(p.stdout)
    for svc in cfg['services'].values():
        build=svc.get('build',{})
        if build:
            assert Path(build['context']).exists(),build
            assert (Path(build['context'])/build.get('dockerfile','Dockerfile')).exists(),build
        for vol in svc.get('volumes',[]):
            if vol['type']=='bind': assert Path(vol['source']).exists(),vol
    print('COMPOSE OK',','.join(combo))
files=subprocess.check_output(['git','ls-files','*.py'],text=True).splitlines()
for p in files: ast.parse(Path(p).read_text(),filename=p)
print('PYTHON AST OK',len(files))
```

Sonuç:

```text
COMPOSE OK dds
COMPOSE OK dds,dds-action
COMPOSE OK dds,simulation-check
COMPOSE OK dds,simulation-check,simulation-lidar-check
COMPOSE OK dds,simulation-check,simulation-nav2-check
COMPOSE OK dds,simulation-check,simulation-amcl-test
COMPOSE OK dds,simulation-check,simulation-b3
COMPOSE OK dds,simulation-check,simulation-b3-retry
COMPOSE OK dds,simulation-check,simulation-c2-3
COMPOSE OK dds,simulation-check,simulation-c3-3-3
PYTHON AST OK 88
```

Container başlatılmadı; image build veya DDS çalışma kanıtı değildir.

## Mermaid ve SVG üretimi

Node/npm üzerinden `@mermaid-js/mermaid-cli@11.12.0` kullanıldı. Kurulum npm cache'inde kaldı; ürün bağımlılıkları değiştirilmedi. Puppeteer 23.11.1 için paket yöneticisinin bakım uyarısı görüldü; render işlemleri başarılı oldu.

Depo kökünde aşağıdaki Python bloğu bütün kaynakları üretir (geçici tema dosyası `/tmp` altındadır):

```python
from pathlib import Path
import subprocess,json
config=Path('/tmp/fleet-mermaid-config.json')
config.write_text(json.dumps({'theme':'base','themeVariables':{'fontFamily':'Arial, sans-serif','fontSize':'16px','lineColor':'#64748b','primaryTextColor':'#0f172a'},'flowchart':{'htmlLabels':False,'curve':'linear','nodeSpacing':35,'rankSpacing':45,'padding':18}}))
for src in sorted(Path('docs/diagrams/src').glob('*.mmd')):
    result=subprocess.run(['npx','--yes','--package','@mermaid-js/mermaid-cli@11.12.0','mmdc','-i',str(src),'-o',str(Path('docs/diagrams/svg')/(src.stem+'.svg')),'-c',str(config),'-b','white'],capture_output=True,text=True)
    print(src.name, result.returncode, result.stderr.strip(),flush=True)
    if result.returncode: raise SystemExit(result.returncode)
```

Sonuç: **18/18 çıkış 0**. SVG'ler XML olarak ayrıştırıldı; katalog içindeki Mermaid bloklarının `.mmd` dosyalarıyla aynı olduğu kontrol edildi. Kaynak dosyaları `.mmd`, türetilmiş dosyalar `.svg` olarak Git'e uygundur; npm/cache veya PNG inceleme dosyaları depoya eklenmedi.

## SVG görünüm denetimi

Puppeteer ile her SVG açıldı. Her `g.node` içindeki label bounding rectangle, şeklin bounding rectangle sınırlarıyla karşılaştırıldı (2 px tolerans). **18/18 dosyada taşma yok**. Bu geometrik kontrol bütün ok/etiket çakışmalarının otomatik ispatı değildir; ayrıca 18 çizimin temas sayfası ve preemption akışı görsel olarak incelendi. Uzun akışlar SVG olarak büyütülebilir.

İnceleme çıktısı:

```text
assignment-reconciliation.svg {"width":1117.533203125,"height":1647.1015625,"overflow":[]}
battery-wh-integration.svg {"width":397.861328125,"height":1438,"overflow":[]}
charging-exit-policy.svg {"width":867.625,"height":1730.171875,"overflow":[]}
charging-queue-selection.svg {"width":683.96484375,"height":1692.5234375,"overflow":[]}
dds-goal-cancel.svg {"width":1120.6484375,"height":1255.0205078125,"overflow":[]}
duplicate-restart-guard.svg {"width":790.4375,"height":2135.46875,"overflow":[]}
executor-lifecycle.svg {"width":836.14453125,"height":1192.765625,"overflow":[]}
failure-operator-recovery.svg {"width":1008.0625,"height":1493.5062255859375,"overflow":[]}
fleet-config-lifecycle.svg {"width":641.69921875,"height":1724.0078125,"overflow":[]}
parking-reservations.svg {"width":786.1328125,"height":1936.3734130859375,"overflow":[]}
rest-websocket-gui.svg {"width":1866.015625,"height":405.3609924316406,"overflow":[]}
robot-selection-energy.svg {"width":614.00390625,"height":1622.0546875,"overflow":[]}
route-cache.svg {"width":640.5078125,"height":1484.84375,"overflow":[]}
safe-preemption.svg {"width":1279.92578125,"height":2668.6484375,"overflow":[]}
sqlite-outbox-consumer.svg {"width":836.27197265625,"height":2249.884521484375,"overflow":[]}
status-session-order.svg {"width":1035.00390625,"height":2452.078125,"overflow":[]}
system-architecture.svg {"width":1421.31640625,"height":1154.7015380859375,"overflow":[]}
task-admission-fifo.svg {"width":947.5078125,"height":2317.40625,"overflow":[]}
```

GitHub sunucusunda render doğrulanmadı. Standart Markdown SVG gömmesi ve açılabilir Mermaid kaynakları kullanıldı; katalogdaki katlanır Mermaid görünümü alternatif sunar.

## Yerel Markdown bağlantıları ve kaynak eşliği

Kontrolün kapsamı README, AGENTS, docs altındaki Markdown dosyaları ve Compose kılavuzudur. Kullanıcının mevcut raporu salt okunur olarak taramaya dahildir. URL/PDF içi hedefler hariçtir. Başlıklar GitHub biçimine yakın Unicode slug ve explicit HTML anchor ile kontrol edilir; bu GitHub sunucusu testi değildir.

```python
from pathlib import Path
import re,unicodedata,urllib.parse,subprocess,json,xml.etree.ElementTree as ET
root=Path.cwd(); errors=[]; count=0; anchors_checked=0
files=[root/'README.md',root/'AGENTS.md']+list((root/'docs').rglob('*.md'))+[root/'docker/compose/README.md']
def anchors(p):
    text=p.read_text(); out=set(re.findall(r'<a\s+id="([^"]+)"',text)); seen={}
    for line in re.sub(r'```.*?```','',text,flags=re.S).splitlines():
        if not re.match(r'^#{1,6} ',line):continue
        h=re.sub(r'^#+\s+','',line).strip().lower()
        h=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',h)
        h=''.join(c for c in h if c in '-_ ' or unicodedata.category(c)[0] in 'LNM')
        h=h.replace(' ','-'); n=seen.get(h,0);seen[h]=n+1
        out.add(h+(f'-{n}' if n else ''))
    return out
for p in files:
    text=re.sub(r'```.*?```','',p.read_text(),flags=re.S)
    for target in re.findall(r'\]\(([^)\s]+)\)',text):
        target=urllib.parse.unquote(target)
        if re.match(r'^[a-zA-Z][\w+.-]*:',target):continue
        path,sep,frag=target.partition('#'); dest=(p.parent/path).resolve() if path else p
        count+=1
        if not dest.exists():errors.append(f'{p.relative_to(root)}: missing {target}');continue
        if frag and dest.suffix=='.md':
            anchors_checked+=1
            if frag not in anchors(dest):errors.append(f'{p.relative_to(root)}: anchor {target}')
for p in (root/'docs/diagrams/src').glob('*.mmd'):
    svg=root/'docs/diagrams/svg'/f'{p.stem}.svg'
    ET.parse(svg)
    assert p.read_text() in (root/'docs/diagrams/README.md').read_text(),p
print(f'{len(files)} Markdown files, {count} local links, {anchors_checked} anchors, {len(errors)} errors')
print('\n'.join(errors))
Path('/tmp/fleet-link-result.json').write_text(json.dumps({'files':len(files),'links':count,'anchors':anchors_checked,'errors':errors},ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
```

Sonuç: **66 Markdown dosyası, 638 yerel bağlantı, 78 başlık/anchor, 0 hata**. `git diff --check` çıkış 0.

## Git ve içerik korunması

```sh
git diff --check
git diff --name-only -- backend fleet_config ros2_ws interfaces config docker scripts tests docs/project-context.md
```

Dokuz taşınan dosyanın `git show HEAD:<eski-yol>` içeriğiyle yeni içerik karşılaştırıldı: yalnız göreli Markdown link hedefleri farklıdır; gövde ve tarihsel kod blokları korunur. Ürün/config/test/proje bağlamı için diff boştur. PDF'ler ve kişisel notlar değişmedi. Başlangıçtaki `docs/README.md` C4 rapor bağlantısı ve `docs/reports/` korunur. Commit, staging ve push yapılmadı.

## Commit öncesi ek kontrol

Kullanıcının sonraki açık commit/push talebiyle staged kontrol tekrarlandı. Taşınan dört karar belgesindeki 10 eski çift boşluklu Markdown satır kırımı, aynı görünümü koruyan ters eğik çizgi biçimine çevrildi. Staged `git diff --check` geçti. Önceki “commit/staging/push yapılmadı” kaydı ilk düzenleme aşamasını anlatır; sonraki talep bu sınırı değiştirdi. Kişisel rapor dosyaları ve önceden eklenmiş rapor bağlantısı commit dışında tutuldu.
