# C5 Aşama 1.6 görsel kabul komutları

[Görsel kabul raporu](c5-stage1-6-visual-acceptance-2026-11-06.md) · [Canlı senaryo kılavuzu](c5-stage1-6-commands-2026-11-06.md)

Komutlar hedef worktree kökünde çalıştırıldı. Ölçümler yerel Google Chrome 156.0.8078.80 ile alındı.

## Üretim build’leri ve Chrome

Kaynak değişikliğinden önce `51ad28d1` ucu doğrulandı. İki önizleme ayrı port ve çıktı dizini kullandı.

```sh
git worktree list --porcelain
git status --short --branch
git rev-parse HEAD
npm --prefix frontend run build -- --outDir /tmp/c5-visual-before
C5_UI_PORT=19167 C5_API_PORT=19168 npm --prefix frontend run preview -- --outDir /tmp/c5-visual-before
# Düzeltmeden sonra ayrı terminalde
npm --prefix frontend run build -- --outDir /tmp/c5-visual-after --emptyOutDir
C5_UI_PORT=19177 C5_API_PORT=19178 npm --prefix frontend run preview -- --outDir /tmp/c5-visual-after
```

Aşağıdaki JavaScript bloğu depo kökünden ayrı bir dosyaya çıkarılır. Betik üretim önizlemesine bağlanır ve test fixture’ını yalnız o Chrome bağlantısına verir.

```sh
mkdir -p /tmp/c5-visual-evidence
awk '/^```js$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-6-visual-commands-2026-11-06.md > /tmp/c5-visual-evidence/measure.mjs
node /tmp/c5-visual-evidence/measure.mjs 19167 /tmp/c5-visual-evidence/before-final
node /tmp/c5-visual-evidence/measure.mjs 19177 /tmp/c5-visual-evidence/after-final
C5_UI_PORT=19177 C5_API_PORT=19178 C5_BROWSER_TEST_DIR=/tmp/c5-visual-evidence/playwright-verified \
  npm --prefix frontend test -- --workers=1
git diff --check
```

Seçili robot, tamamlanmış kamera sıfırlaması ve bağlantı kesintisi kareleri aynı fixture ile ayrı bir görsel geçişte yeniden alındı. Bu geçiş performans örneklemedi.

```sh
node /tmp/c5-visual-evidence/measure.mjs 19167 /tmp/c5-visual-evidence/before-resets --screenshots-only
node /tmp/c5-visual-evidence/measure.mjs 19177 /tmp/c5-visual-evidence/after-resets --screenshots-only
```

## Canlı Fortress

İlk denemede iki Colcon derlemesi 120 sn’lik tarayıcı hazırlık bütçesini aştı. İkinci denemede izole TF STALE kontrolü geçti. Köprü kapanırken ürün kaynağı bataryayı kullanılamaz bildirdi ve bağımsız batarya göstergesi kontrolü durdu. Aşağıdaki koşuda backend, iki Nav2 yaşam döngüsü yöneticisi ACTIVE olduktan sonra başlatıldı. Test aracının başlangıç bekleme bütçesi 360 sn ve bağımsız okuyucuların kayıt süresi 600 sn.

```sh
set -euo pipefail
export DDS_TEST_PAYLOAD=fleet-c5-final-visual ROS_DOMAIN_ID=126
export C5_UI_PORT=19177 C5_API_PORT=19178 C5_SCENE_PORT=19179 C5_REQUIRE_COMPACT=1 C5_STARTUP_TIMEOUT_MS=360000
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/c5-visual-evidence/live-ready
evidence=$C43_EVIDENCE_DIR
simulation=$DDS_TEST_PAYLOAD-simulation-1
backend=$DDS_TEST_PAYLOAD-backend-1
scene=$DDS_TEST_PAYLOAD-scene-1
cleanup() {
  scripts/run_c5_dashboard.sh stop backend scene simulation > "$evidence/stop.log" 2>&1 || true
  docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
    "$backend" "$simulation" "$scene" > "$evidence/shutdown.txt" 2>&1 || true
  scripts/run_c5_dashboard.sh logs --no-color > "$evidence/compose.log" 2>&1 || true
  scripts/run_c5_dashboard.sh down > "$evidence/down.log" 2>&1 || true
}
mkdir -p "$evidence/gates"
scripts/run_c5_dashboard.sh config --format json > "$evidence/compose.json"
scripts/run_c5_dashboard.sh create --no-build
trap cleanup EXIT
scripts/run_c5_dashboard.sh start simulation scene
deadline=$((SECONDS + 300))
while true; do
  docker logs "$simulation" > "$evidence/simulation-readiness.log" 2>&1
  if rg -q 'robot_1.lifecycle_manager_navigation.*Managed nodes are active' "$evidence/simulation-readiness.log" &&
     rg -q 'robot_2.lifecycle_manager_navigation.*Managed nodes are active' "$evidence/simulation-readiness.log"; then
    break
  fi
  if (( SECONDS >= deadline )); then
    echo "Nav2 readiness timeout" >&2
    exit 1
  fi
  sleep 2
done

git show f3e3901:fleet-visualizer/validation/nav2_reference.py |
  docker exec -i "$simulation" bash -c \
    'source /opt/ros/humble/setup.bash; exec python3 -u - 600' \
  > "$evidence/nav2.jsonl" 2> "$evidence/nav2.err" &
for id in robot_1 robot_2; do
  git show f3e3901:fleet-visualizer/validation/ros_reference.py |
    docker exec -i "$simulation" bash -c \
      'source /opt/ros/humble/setup.bash; exec timeout -s INT 600 python3 -u - --namespace "/$1" "$1/base_link"' -- "$id" \
    > "$evidence/tf-$id.jsonl" 2> "$evidence/tf-$id.err" &
done

scripts/run_c5_dashboard.sh start backend
node frontend/tests/live-acceptance.mjs > "$evidence/chrome.log" 2>&1
docker exec "$simulation" bash -ec \
  'source /opt/ros/humble/setup.bash; ros2 node info /fleet_visualizer --no-daemon --include-hidden' \
  > "$evidence/bridge-graph.txt"
docker wait "$backend" > "$evidence/backend-exit.txt"
test "$(cat "$evidence/backend-exit.txt")" -eq 0
sqlite3 "$evidence/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;' > "$evidence/sqlite-check.txt"
python3 docker/simulation-c5/compare_scene_evidence.py "$evidence" > "$evidence/ros-chrome-compare.json"
```

## Python ve ROS regresyonu

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
../ros2-fleet-manager-c5-dashboard/.venv/bin/python -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
```

```sh
set -euo pipefail
docker run --rm --name fleet-c5-visual-ros-regression \
  -e ROS_DOMAIN_ID=66 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-c5-validation:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  tests/test_c5_dashboard.py tests/test_battery_ros2.py tests/test_c42_battery_ros2.py \
  tests/test_c43_station_ros2.py tests/test_c44_charging.py
'
```

## Chrome ölçüm betiği

```js
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
const require = createRequire(resolve('frontend/package.json'));
const { build } = require('esbuild');
const { chromium } = require('@playwright/test');
const { PerspectiveCamera, Vector3, Box3 } = require('three');
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
const [, , port, output, mode] = process.argv;
if (!port || !output) throw new Error('Usage: node measure.mjs <preview-port> <evidence-dir>');
mkdirSync(output, { recursive: true });
const { outputFiles: [bundle] } = await build({
  stdin: { contents: 'export { Warehouse } from "./frontend/src/scene/Warehouse"; export { fixture, telemetry } from "./frontend/tests/dashboard.spec";',
    resolveDir: process.cwd(), loader: 'ts' }, bundle: true, write: false, format: 'esm', jsx: 'automatic',
  plugins: [{name:'fixture',setup(plugin){plugin.onLoad({ filter: /dashboard\.spec\.ts$/ }, async ({path}) => {
    const { readFile } = await import('node:fs/promises');
    const data = await readFile(path,'utf8');
    return { contents: data.slice(data.indexOf('const backend'), data.indexOf('async function trace')).replace(/^(const fixture|function telemetry)/gm, 'export $1'), loader: 'ts' };
  });}}],
});
const { Warehouse, fixture, telemetry } = await import('data:text/javascript;base64,' + Buffer.from(bundle.contents).toString('base64'));
const corners = [], geometry = {};
function box(name, x, y, z, w, h, d) {
  const min = [x-w/2,y-h/2,z-d/2], max=[x+w/2,y+h/2,z+d/2];
  const bounds = geometry[name] ??= new Box3();
  bounds.expandByPoint(new Vector3(...min)).expandByPoint(new Vector3(...max));
  for (const a of [min[0], max[0]]) for (const b of [min[1], max[1]]) for (const c of [min[2], max[2]]) corners.push(new Vector3(a,b,c));
}
for (const {props} of Warehouse.type({softShadows:true}).props.children.filter(Boolean)) {
  if (props.boxes) for (const row of props.boxes) box(props.name, ...row);
  else if (props.name === 'warehouse-floor') box(props.name,...props.position,...props.children[0].props.args);
}
const chrome = await chromium.launch({channel:'chrome',headless:true});
const system = await chrome.newBrowserCDPSession();
const result = { chrome:chrome.version(), headless:true, quality:'standard', mode:'free', fixture:'dashboard.spec.ts telemetry; stationary TF at 10 Hz, product at 2 Hz, except explicit scenario changes', windows:[], gpu:(await system.send('SystemInfo.getInfo')).gpu.devices, geometry, cornerCount:corners.length };
function projection(camera, points, width, height) {
  const projected = points.map(p=>p.clone().project(camera));
  const xs = projected.map(p=>(p.x+1)/2*width), ys=projected.map(p=>(1-p.y)/2*height);
  const [left,top,right,bottom]=[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
  return {left,top,right,bottom,horizontal:(right-left)/width,vertical:(bottom-top)/height,
    clipped:left<0||top<0||right>width||bottom>height||projected.some(p=>Math.abs(p.z)>1)};
}
try {
for (const [width,height] of [[1280,850],[1440,900],[1920,1080],[390,844]]) {
  const page = await chrome.newPage({viewport:{width,height},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error') errors.push(m.text());});
  await page.addInitScript(() => {
    window.draws = [];
    window.addEventListener('fleet-visualizer:frame',e=> {window.lastFrame=e.detail; if(window.recording) window.draws.push(e.detail);});
  });
  let timer, ws, tf, near=false, active=true, dropped=false, sequence=fixture.sequence, stamp=2_000_000_000;
  const sample=()=>{ if (!active) return; stamp+=100_000_000;
    tf.sample('robot_alpha',near?0:-2,near?0:1,stamp); tf.sample('robot_beta',near?.01:2,near?0:-1,stamp); };
  await page.routeWebSocket('**/ws/fleet',socket=>{
    if (dropped) return;
    ws=socket; tf=telemetry(ws); ws.send(JSON.stringify(fixture)); tf.connect(); sample();
    clearInterval(timer); timer=setInterval(()=>{ sample(); if(sequence % 5 === 0) ws.send(JSON.stringify({...fixture,sequence:sequence+1})); sequence++; },100);
  });
  await page.goto('http://127.0.0.1:'+port+'/?trace=1');
  const waitForLive = () => page.waitForFunction(() =>
    window.lastFrame?.robots.filter(r => r.visible && r.status === 'LIVE').length === 2 &&
    document.querySelector('.scene-indicator')?.textContent === '2 / 2 TF LIVE');
  await waitForLive();
  const capture = async (name, overlay=false) => {
    await page.screenshot({path:output+'/'+name+'.png'});
    const data=await page.evaluate(()=>{
      const box=(e)=>{const {x,y,width,height,bottom}=e.getBoundingClientRect();return {x,y,width,height,bottom};};
      const rect=(s)=>box(document.querySelector(s));
      const canvas=document.querySelector('canvas'), gl=canvas.getContext('webgl2'), ext=gl.getExtension('WEBGL_debug_renderer_info');
      const fonts={};
      for(const s of ['.detail-identity h3','.detail-identity p','.status-badge','.battery-line strong','.robot-card-task span','.robot-card-task strong','.detail-grid dt','.detail-grid dd','.detail-grid dd small','.metric dt','.metric strong','.metric small','.robot-card-top strong','.robot-card-top p','.robot-card-status small','.scene-label > span','.scene-label > small','.scene-footer label','.scene-footer small','.scene-indicator','.section-heading .tag','.measurement-details summary']) {
        const values=[...document.querySelectorAll(s)].map(e=>parseFloat(getComputedStyle(e).fontSize)); if(values.length)fonts[s]=Math.min(...values);
      }
      const list=(s)=>[...document.querySelectorAll(s)].map(e=>({ id:e.dataset.robotId??e.closest('[data-robot-id]')?.dataset.robotId, ...box(e), visible:getComputedStyle(e).visibility==='visible',text:e.textContent }));
      const panel=document.querySelector('.details-scroll')??document.querySelector('.robot-details');
      return {width:innerWidth,height:innerHeight,dpr:devicePixelRatio,renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),
        scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight, topbar:rect('.topbar'), heading:document.querySelector('.page-heading')?rect('.page-heading'):null,
        metrics:rect('.metrics'), scene:rect('.scene-panel'), panel:rect('.robot-details'), viewport:rect('canvas'), cards:list('.robot-card'),
        panelScroll:[panel.clientHeight,panel.scrollHeight], canvasBackingWidth:canvas.width, canvasBackingHeight:canvas.height,
        planStatus:document.querySelector('[data-testid=plan-status]')?.textContent, tfStatus:document.querySelector('[data-testid=tf-status]')?.textContent, labels:list('.scene-label'), markers:list('.scene-marker'), fonts, frame:window.lastFrame};
    });
    const {viewport:v,frame:f} = data;
    const camera=new PerspectiveCamera(42,v.width/v.height,.035,90);
    camera.position.fromArray(f.camera); camera.lookAt(new Vector3(...f.target)); camera.updateMatrixWorld(true);
    data.projection=projection(camera,corners,v.width,v.height);
    data.legacyMarkers=f.robots.filter(r=>r.visible).map(({robot_id,pose,yaw})=>{
      const circle=Array.from({length:49},(_,i)=>{
        const a=yaw+i*Math.PI/24;return new Vector3(pose[0]+.238*Math.cos(a),pose[1]+.004,pose[2]-.238*Math.sin(a));
      });
      return {robot_id,...projection(camera,circle,v.width,v.height)};
    });
    data.projectedRoots=f.robots.map(({robot_id,pose})=>{const q=new Vector3(...pose).project(camera);return {robot_id,x:v.x+(1+q.x)/2*v.width,y:v.y+(1-q.y)/2*v.height};});
    data.altPadding=data.height-Math.max(...data.cards.map(c=>c.bottom));
    data.panelDifference=Math.abs(data.scene.height-data.panel.height);
    data.upperHeight=data.scene.y;
    data.minFont=Math.min(...Object.values(data.fonts));
    if(overlay){
      await page.evaluate(({x,y,left,top,right,bottom})=>{
        const e=document.createElement('div'); e.id='proof-box';
        Object.assign(e.style,{position:'fixed',pointerEvents:'none',zIndex:30,border:'1px dashed #9a2974',
          left:(x+left)+'px',top:(y+top)+'px',width:(right-left)+'px',height:(bottom-top)+'px'});document.body.append(e);
      },{x:v.x,y:v.y,...data.projection});
      await page.screenshot({path:output+'/'+name+'-projected.png'});
      await page.locator('#proof-box').evaluate(e=>e.remove());
    }
    return data;
  };
  const data=await capture('viewport-'+width,true);
  if (mode !== '--screenshots-only') {
    const initial=await system.send('SystemInfo.getProcessInfo');
    const stats=await page.evaluate(async()=>{
      window.recording=true; const ticks=[];
      await new Promise(resolve=>{const start=performance.now();const tick=t=>{ticks.push(t);if(t-start>=5000)resolve();else requestAnimationFrame(tick);};requestAnimationFrame(tick);});
      window.recording=false;
      const pct95=values=>values.sort((a,b)=>a-b)[Math.floor((values.length-1)*.95)];
      const perf=(times)=>({samples:times.length,fps:(times.length-1)*1000/(times.at(-1)-times[0]),p95: pct95(times.slice(1).map((v,i)=>v-times[i]))});
      return {seconds:(ticks.at(-1)-ticks[0])/1000,raf:perf(ticks),scene:perf(window.draws.map(f=>f.at)),drawCallsP95:pct95(window.draws.map(f=>f.calls)),geometries:window.lastFrame.geometries,textures:window.lastFrame.textures};
    });
    const end=await system.send('SystemInfo.getProcessInfo');
    const beforeCpu=new Map(initial.processInfo.map(p=>[p.id,p.cpuTime]));
    const pids=new Set(end.processInfo.map(p=>p.id));
    const rss=execFileSync('ps',['-ax','-o','pid=,rss='],{encoding:'utf8'}).trim().split('\n')
      .map(line=>line.trim().split(/\s+/).map(Number)).reduce((sum,[pid,kib])=>sum+(pids.has(pid)?kib:0),0);
    const cdp=await page.context().newCDPSession(page);
    data.performance={...stats, chromeCpuPercentOneCore:100*end.processInfo.reduce((sum,p)=>sum+p.cpuTime-(beforeCpu.get(p.id)??p.cpuTime),0)/stats.seconds,
      chromeRssBytes:rss*1024, heapUsedBytes:(await cdp.send('Runtime.getHeapUsage')).usedSize};
  }
  if(width===1440) {
    data.scenarios={};
    const scenario=async(name)=>{ data.scenarios[name]=await capture(name); };
    await scenario('plan-none');
    tf.plan('robot_alpha');
    await page.getByTestId('plan-status').getByText(/Güncel/).waitFor();
    await scenario('plan-fresh');
    await page.waitForFunction(()=>/sona erdi|Bayat/.test(document.querySelector('[data-testid="plan-status"]').textContent));
    await scenario('plan-stale');
    active=false; tf.status('robot_alpha','STALE');
    await page.getByTestId('tf-status').getByText('STALE',{exact:true}).waitFor();
    await scenario('tf-stale');
    active=true; near=true; sample();
    await waitForLive();
    await page.waitForFunction(() => window.lastFrame.robots.every(r => Math.abs(r.pose[0]) < .02));
    await scenario('close-robots');
    await page.getByRole('button',{name:'Robot seç: robot_beta'}).click();
    await page.waitForFunction(() => window.lastFrame.selected === 'robot_beta' &&
      getComputedStyle(document.querySelector('.scene-label[data-robot-id="robot_beta"]')).visibility === 'visible');
    await scenario('selected-robot');
    const b=await page.locator('canvas').boundingBox();
    await page.mouse.move(b.x+b.width*.35,b.y+b.height*.45); await page.mouse.wheel(0,420);
    await page.waitForTimeout(400);
    await scenario('close-robots-far');
    await page.setViewportSize({width:1280,height:850});
    await page.waitForTimeout(350);
    await scenario('manual-resize');
    await page.getByRole('button',{name:'Kamerayı sıfırla'}).click();
    const preset = result.windows.find(window => window.width === 1280).frame;
    await page.waitForFunction(({camera, target}) => {
      const frame = window.lastFrame;
      return !frame.transitioning && frame.camera.every((value, i) => Math.abs(value - camera[i]) < .005)
        && frame.target.every((value, i) => Math.abs(value - target[i]) < .005);
    }, preset);
    await scenario('camera-reset');
    dropped=true; clearInterval(timer); await ws.close();
    await page.getByRole('alert').waitFor();
    await page.getByTestId('tf-status').getByText('STALE', { exact: true }).waitFor();
    await scenario('connection-loss');
  }
  data.errors=errors;
  result.windows.push(data); writeFileSync(output+'/metrics.json',JSON.stringify(result,null,2));
  clearInterval(timer); await page.close();
}
} finally { await chrome.close(); }
```
