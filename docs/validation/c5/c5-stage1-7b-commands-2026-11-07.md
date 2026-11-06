# C5 Aşama 1.7B doğrulama komutları

[Doğrulama raporu](c5-stage1-7b-validation-2026-11-07.md)

Komutlar worktree kökünden çalıştırıldı. İlk üretim derlemesi kaynak değişikliğinden önce alındı. Aşağıda `/tmp/c5-wh17-evidence` ölçüm ve yerel kanıt dizinidir.

## Kaynak ve üretim derlemeleri

```sh
git status --short --branch
git worktree list
git rev-parse HEAD refs/heads/feat/c5-dashboard-ui-polish
git ls-remote --heads origin feat/c5-dashboard-ui-polish feat/c5-warehouse-model-integration
git worktree add -b feat/c5-warehouse-model-integration ../ros2-fleet-manager-c5-warehouse b7fcb05c3cbcc24aaa6439ff494e459bc4d4549f
asset_tmp=$(mktemp /tmp/c5-warehouse.XXXXXX)
curl -fsSL https://cdn.3dassets.dev/assets/23990/v1/model.glb -o "$asset_tmp"
shasum -a 256 "$asset_tmp"
npm --prefix frontend ci
npm --prefix frontend run build -- --outDir /tmp/c5-wh17-base
C5_UI_PORT=19377 C5_API_PORT=19378 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17-base
# Entegrasyondan sonra, ayrı terminalde
npm --prefix frontend run build -- --outDir /tmp/c5-wh17-final --emptyOutDir
C5_UI_PORT=19407 C5_API_PORT=19408 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17-final
```

## Chrome

Kaynak değişikliğinden önceki ilk kadraj ölçümünde [Aşama 1.6 ölçüm betiği](c5-stage1-6-visual-commands-2026-11-06.md#chrome-ölçüm-betiği) 19377 portundaki build ile çalıştırıldı.

Ölçüm betiği aynı ürün ve TF yükünü iki önizlemeye verir. 5 saniyelik ölçümler Chrome süreç RSS toplamını ve renderer JS heap kullanımını ayrı kaydeder. İlk çizim, GLB’nin ilk çizimi ve tarayıcı kaynak zamanlaması `performance.timeOrigin` bazındadır. Yeni geometri sınırları izleme olayından alınır ve Three.js perspektif kamerasıyla CSS piksel alanına yansıtılır. `quick` kipi yalnız 1440×900’de görsel kontrol çalıştırır.

```sh
mkdir -p /tmp/c5-wh17-evidence
awk '/^```js$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-7b-commands-2026-11-07.md > /tmp/c5-wh17-evidence/check.mjs
node /tmp/c5-wh17-evidence/check.mjs 19377 /tmp/c5-wh17-evidence/before
node /tmp/c5-wh17-evidence/check.mjs 19407 /tmp/c5-wh17-evidence/after
C5_UI_PORT=19407 C5_API_PORT=19408 C5_BROWSER_TEST_DIR=/tmp/c5-wh17-evidence/playwright-verified \
  npm --prefix frontend test -- --workers=1
npm --prefix frontend run build -- --outDir /tmp/c5-wh17-verified --emptyOutDir
shasum -a 256 frontend/src/scene/assets/warehouse-aisle.glb /tmp/c5-wh17-verified/assets/*.glb
diff -q /tmp/c5-wh17-verified/index.html /tmp/c5-wh17-final/index.html
git diff --check
```

## C4.5 Fortress

[Aşama 1.6 canlı komut dizisi](c5-stage1-6-visual-commands-2026-11-06.md#canlı-fortress) kullanıldı. Bu koşunun ortam değerleri aşağıdadır. Compose konfigürasyonu çözüldü, var olan image’larla `create --no-build` çalıştı ve backend iki Nav2 yaşam döngüsü yöneticisi ACTIVE olduktan sonra başlatıldı. Bağımsız ROS okuyucuları, tarayıcıyla aynı anda ayrı TF ve Nav2 kayıtları aldı.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-warehouse-17b-final ROS_DOMAIN_ID=128
export C5_UI_PORT=19407 C5_API_PORT=19408 C5_SCENE_PORT=19409
export C5_REQUIRE_COMPACT=1 C5_VERIFY_WAREHOUSE=1 C5_STARTUP_TIMEOUT_MS=360000
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/c5-wh17-evidence/live-final
# Bağlantı, iki Nav2 readiness ve bağımsız okuyucular için bağlantı verilen diziyi kullan.
node frontend/tests/live-acceptance.mjs
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 docker/simulation-c5/compare_scene_evidence.py "$C43_EVIDENCE_DIR"
awk '/^```python$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-7b-commands-2026-11-07.md > /tmp/c5-wh17-evidence/check-independent.py
python3 /tmp/c5-wh17-evidence/check-independent.py "$C43_EVIDENCE_DIR"
```

## Tarayıcı ölçüm betiği

```js
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
const require = createRequire(resolve('frontend/package.json'));
const { build } = require('esbuild');
const { chromium } = require('@playwright/test');
const { PerspectiveCamera, Vector3 } = require('three');
const { execFileSync } = require('node:child_process');
const { mkdirSync, readFileSync, writeFileSync } = require('node:fs');
const [, , port, output, mode] = process.argv;
mkdirSync(output, { recursive: true });
const spec = readFileSync('frontend/tests/dashboard.spec.ts', 'utf8');
const { outputFiles: [fixtureModule] } = await build({
  stdin: { contents: spec.slice(spec.indexOf('const backend'), spec.indexOf('async function trace'))
    .replace(/^(const fixture|function telemetry)/gm, 'export $1'), loader: 'ts' },
  bundle: true, write: false, format: 'esm',
});
const { fixture, telemetry } = await import('data:text/javascript;base64,' + Buffer.from(fixtureModule.contents).toString('base64'));
const dock = {x:.5,y:-2,yaw:0,frame_id:'map'};
const park = {x:-2,y:1,yaw:1.57,frame_id:'map'};
const pickup = {x:1.6,y:1.8,yaw:0,frame_id:'map'};
const dropoff = {x:-1.3,y:-1.6,yaw:0,frame_id:'map'};
const snapshot = {
  ...fixture,
  robots: [{...fixture.robots[0],pose:dock,charging_station_id:'dock_1'}, {...fixture.robots[1],pose:pickup}],
  tasks: [{...fixture.tasks[0],task_id:'delivery-01',status:'EXECUTING',pickup,dropoff}],
  stations:[{...fixture.stations[0],station_id:'dock_1',pose:dock},
    {station_id:'park_1',station_type:'PARKING',pose:park,state:'FREE',charging:'NOT_APPLICABLE',
      occupied_by_robot_id:null,reserved_by_robot_id:null,charging_robot_id:null}],
};
snapshot.robots[1].active_task_id = 'delivery-01';
const chrome = await chromium.launch({ channel:'chrome', headless:true });
const system = await chrome.newBrowserCDPSession();
const result = {chrome:chrome.version(), gpu:(await system.send('SystemInfo.getInfo')).gpu.devices, windows:[]};
try {
  for (const [width,height] of mode === 'quick' ? [[1440,900]] : [[1280,850],[1440,900],[1920,1080],[390,844]]) {
    const page = await chrome.newPage({viewport:{width,height},deviceScaleFactor:1});
    const errors = [];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',msg=>{ if(msg.type()==='error')errors.push(msg.text()); });
    await page.addInitScript(() => {
      window.framesObserved = [];
      window.addEventListener('fleet-visualizer:frame', ({detail}) => {
        window.lastFrame = detail;
        window.firstFrame ??= detail.at;
        if(detail.warehouse==='glb')window.firstDecor ??= detail.at;
        if(window.recording)window.framesObserved.push(detail);
      });
      window.addEventListener('fleet-visualizer:warehouse-bounds', ({detail})=>{window.warehouseCorners=detail;});
      window.addEventListener('fleet-visualizer:routes', ({detail})=>{
        (window.latestRoutes ??= {})[detail.robot_id]=detail;
      });
    });
    let socket, tf, timer, sendTF=true, closed=false, seq=snapshot.sequence, stamp=2_000_000_000, tick=0, plan=false;
    const sample=()=>{
      stamp+=100_000_000;
      if(sendTF) {
        tf.sample('robot_alpha',dock.x,dock.y,stamp);
        tf.sample('robot_beta',1.7+Math.cos(tick/9)*.45,.2+Math.sin(tick/9)*.6,stamp);
      }
      if(tick%5===0) {
        socket.send(JSON.stringify({...snapshot,sequence:++seq}));
        if(plan)tf.plan('robot_beta');
      }
      tick++;
    };
    await page.routeWebSocket('**/ws/fleet',route=>{
      if(closed)return;
      socket=route;
      tf=telemetry(route);
      socket.send(JSON.stringify(snapshot));
      tf.connect();
      sample();
      timer=setInterval(sample,100);
    });
    await page.goto('http://127.0.0.1:'+port+'/?trace=1');
    await page.waitForFunction(isNew=>window.lastFrame?.robots.filter(r=>r.visible&&r.status==='LIVE').length===2 &&
      (!isNew||window.lastFrame.warehouse==='glb'),port!=='19377',{timeout:10000});
    const capture = (name, fullPage=false) => page.screenshot({path:output+'/'+name+'.png',fullPage});
    await capture('viewport-'+width);
    if(width===390)await capture('mobile-full',true);
    const data = await page.evaluate(() => {
      const gl=document.querySelector('canvas').getContext('webgl2'), ext=gl.getExtension('WEBGL_debug_renderer_info');
      const {width,height}=gl.canvas.getBoundingClientRect();
      const resource=performance.getEntriesByType('resource').find(e=>e.name.endsWith('.glb'));
      return { width:innerWidth,height:innerHeight,canvas:[width,height],dpr:devicePixelRatio,
        renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),
        scrollWidth:document.documentElement.scrollWidth,firstFrameMs:window.firstFrame,firstDecorMs:window.firstDecor??null,
        asset:resource?{fetchMs:resource.duration,startMs:resource.startTime,endMs:resource.responseEnd,
          decodedBodySize:resource.decodedBodySize,fetchToFrameMs:window.firstDecor-resource.startTime}:null,
        frame:window.lastFrame, corners:window.warehouseCorners,
        markerLabels:[...document.querySelectorAll('[data-operation-point]')].map(node=>({
          key:node.dataset.operationPoint, visible:getComputedStyle(node).visibility==='visible',
          text:node.textContent,
        })) };
    });
    if (data.corners) {
      const camera = new PerspectiveCamera(42,data.canvas[0]/data.canvas[1],.035,90);
      camera.position.fromArray(data.frame.camera);
      camera.lookAt(new Vector3(...data.frame.target));
      camera.updateMatrixWorld(true);
      const projected = data.corners.map(coords=>new Vector3(...coords).project(camera));
      const x=projected.map(v=>v.x), y=projected.map(v=>v.y);
      data.projection={horizontal:(Math.max(...x)-Math.min(...x))/2,vertical:(Math.max(...y)-Math.min(...y))/2,
        clipped:projected.some(v=>Math.max(Math.abs(v.x),Math.abs(v.y),Math.abs(v.z))>1)};
      if(data.projection.clipped)throw new Error('Warehouse clipped at '+width);
      delete data.corners;
    }
    if(mode!=='quick') {
      const initial=await system.send('SystemInfo.getProcessInfo');
      const stats=await page.evaluate(async()=>{
        window.recording=true;
        const raf=[];
        await new Promise(resolve=>{
          const next=t=>{raf.push(t);if(t-raf[0]>=5000)resolve();else requestAnimationFrame(next);};
          requestAnimationFrame(next);
        });
        window.recording=false;
        const pct95=items=>items.sort((a,b)=>a-b)[Math.floor((items.length-1)*.95)];
        const perf=times=>({samples:times.length,fps:(times.length-1)*1000/(times.at(-1)-times[0]),
          p95:pct95(times.slice(1).map((t,i)=>t-times[i]))});
        const frames=window.framesObserved;
        return {seconds:(raf.at(-1)-raf[0])/1000,raf:perf(raf),scene:perf(frames.map(f=>f.at)),
          callsP95:pct95(frames.map(f=>f.calls)),trianglesP95:pct95(frames.map(f=>f.triangles)),
          geometries:window.lastFrame.geometries,textures:window.lastFrame.textures};
      });
      const final=await system.send('SystemInfo.getProcessInfo');
      const pids=new Set(final.processInfo.map(p=>p.id));
      const startCPU=new Map(initial.processInfo.map(p=>[p.id,p.cpuTime]));
      const rss=execFileSync('ps',['-ax','-o','pid=,rss='],{encoding:'utf8'}).trim().split('\n')
        .map(line=>line.trim().split(/\s+/).map(Number)).reduce((sum,[pid,kib])=>sum+(pids.has(pid)?kib:0),0);
      const cdp=await page.context().newCDPSession(page);
      data.performance={...stats,chromeRssBytes:rss*1024,heapUsedBytes:(await cdp.send('Runtime.getHeapUsage')).usedSize,
        chromeCpuPercentOneCore:100*final.processInfo.reduce((sum,p)=>sum+p.cpuTime-(startCPU.get(p.id)??p.cpuTime),0)/stats.seconds};
    }
    if(width===1440) {
      await capture('charging');
      const chosen=page.getByRole('button',{name:'Robot seç: robot_beta',exact:true});
      const selectionStart=performance.now();
      await chosen.click();
      await page.waitForFunction(()=>window.lastFrame?.selected==='robot_beta');
      data.selectionMs=Math.round(performance.now()-selectionStart);
      await capture('selected');
      plan=true;
      tf.plan('robot_beta');
      await page.getByTestId('plan-status').getByText(/Güncel/).waitFor();
      await capture('task-plan-trail');
      const camera=async (button, mode)=>{
        const start=performance.now();
        await page.getByRole('button',{name:button,exact:true}).click();
        await page.waitForFunction(value=>window.lastFrame?.mode===value&&!window.lastFrame.transitioning,mode,{timeout:7000});
        return Math.round(performance.now()-start);
      };
      if(mode!=='quick') sendTF=false;
      data.cameraMs={follow:await camera('Robotu takip et','follow')};
      if(mode!=='quick') sendTF=true;
      await capture('follow');
      data.cameraMs.top=await camera('Üstten','top');
      await capture('top');
      data.cameraMs.fit=await camera('Filoyu kadraja al','fit');
      data.cameraMs.reset=await camera('Kamerayı sıfırla','free');
      sendTF=false;
      tf.status('robot_alpha','STALE');tf.status('robot_beta','STALE');
      await page.getByTestId('tf-status').getByText('STALE',{exact:true}).waitFor();
      await capture('stale');
      closed=true;
      clearInterval(timer);
      await socket.close();
      await page.getByRole('alert').waitFor();
      await capture('disconnected');
    }
    data.errors=errors;
    result.windows.push(data);
    writeFileSync(output+'/metrics.json',JSON.stringify(result,null,2));
    clearInterval(timer);
    await page.close();
  }
} finally { await chrome.close(); }
```

## Bağımsız istasyon ve görev karşılaştırması

```python
import json
import sqlite3
import sys
from pathlib import Path

import yaml

evidence = Path(sys.argv[1])
rendered = json.loads((evidence / "chrome-operation-points.json").read_text())
fleet = yaml.safe_load(Path("config/fleet.yaml").read_text())
stations = {
    station["id"]: station["pose"]
    for group in fleet["stations"].values()
    for station in group
}
with sqlite3.connect(f"file:{evidence / 'c5-charging.sqlite3'}?mode=ro", uri=True) as database:
    tasks = dict(database.execute("SELECT task_id, snapshot FROM tasks"))
    result = []
    for point in rendered:
        kind = point["kind"]
        if kind in ("pickup", "dropoff"):
            reference = json.loads(tasks[point["id"]])[kind + "_pose"]
            assert reference["frame_id"] == "map"
            source = "SQLite tasks.snapshot"
        else:
            reference = stations[point["id"]]
            saved = database.execute("SELECT snapshot FROM reservations WHERE station_id=?", (point["id"],)).fetchone()
            assert saved
            station_pose = json.loads(saved[0])["pose"]
            assert station_pose["frame_id"] == "map"
            assert all(station_pose[key] == reference[key] for key in ("x", "y", "yaw"))
            source = "fleet.yaml + SQLite reservations.snapshot"
        assert point["source"]["frame_id"] == "map"
        assert point["position"] == [reference["x"], 0, -reference["y"]], point
        assert point["yaw"] == reference["yaw"], point
        result.append({"key": point["key"], "source": source, "scene_position": point["position"], "yaw": point["yaw"]})
print(json.dumps(result, indent=2, ensure_ascii=False))
```
