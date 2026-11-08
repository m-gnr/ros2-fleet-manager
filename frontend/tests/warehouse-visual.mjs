import { build } from 'esbuild';
import { chromium } from '@playwright/test';
import { PerspectiveCamera, Vector3 } from 'three';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const [, , port, output, mode] = process.argv;
if (!port || !output) throw new Error('Usage: warehouse-visual.mjs <preview-port> <evidence-dir> [quick]');
mkdirSync(output, { recursive: true });
const { outputFiles: [fixtureModule] } = await build({
  entryPoints: [fileURLToPath(new URL('./dashboard-fixtures.ts', import.meta.url))],
  bundle: true, write: false, format: 'esm',
});
const { fixture, telemetry } = await import('data:text/javascript;base64,' + Buffer.from(fixtureModule.contents).toString('base64'));
const dock = {x:.5,y:-2,yaw:0,frame_id:'map'};
const park = {x:-2,y:1,yaw:1.57,frame_id:'map'};
const pickup = {x:2.3,y:-2.5,yaw:0,frame_id:'map'};
const dropoff = {x:2.5,y:-1,yaw:0,frame_id:'map'};
const snapshot = {
  ...fixture,
  robots: [{...fixture.robots[0],pose:dock,charging_station_id:'dock_1'}, {...fixture.robots[1],pose:pickup}],
  tasks: [{...fixture.tasks[0],task_id:'delivery-01',status:'EXECUTING',pickup,dropoff}],
  stations:[{...fixture.stations[0],station_id:'dock_1',pose:dock},
    {station_id:'park_1',station_type:'PARKING',pose:park,state:'FREE',charging:'NOT_APPLICABLE',
      occupied_by_robot_id:null,reserved_by_robot_id:null,charging_robot_id:null}],
};
snapshot.robots[1].active_task_id = 'delivery-01';
const nearby = { ...snapshot.tasks[0], task_id: 'shipment-warehouse-0217',
  pickup: { ...pickup, x: -3.7, y: 3.2 }, dropoff: { ...dropoff, x: -3.2, y: 3.3 } };
const chrome = await chromium.launch({ channel:'chrome', headless:true });
const system = await chrome.newBrowserCDPSession();
const result = {chrome:chrome.version(), gpu:(await system.send('SystemInfo.getInfo')).gpu.devices,
  fixtureTaskPoints: [snapshot.tasks[0], nearby].flatMap(task =>
    ['pickup', 'dropoff'].map(kind => ({ key: kind + ':' + task.task_id, pose: task[kind] }))),
  windows:[]};
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
    let socket, tf, timer, sendTF=true, closed=false, seq=snapshot.sequence, stamp=2_000_000_000, tick=0, plan=false, product=snapshot, closeRobots=false;
    const sample=()=>{
      stamp+=100_000_000;
      if(sendTF) {
        tf.sample('robot_alpha',closeRobots ? -3.3 : dock.x,closeRobots ? 3.1 : dock.y,stamp);
        tf.sample('robot_beta',closeRobots ? -3.29 : 1.8+Math.cos(tick/9)*.40,closeRobots ? 3.1 : -.5+Math.sin(tick/9)*.6,stamp);
      }
      if(tick%5===0) {
        socket.send(JSON.stringify({...product,sequence:++seq}));
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
    await page.waitForFunction(()=>window.lastFrame?.robots.filter(r=>r.visible&&r.status==='LIVE').length===2 &&
      window.lastFrame.warehouse==='glb', undefined, {timeout:15000});
    const capture = (name, fullPage=false) => page.screenshot({path:output+'/'+name+'.png',fullPage});
    await capture('viewport-'+width);
    if(width===390)await capture('mobile-full',true);
    const data = await page.evaluate(() => {
      const gl=document.querySelector('canvas').getContext('webgl2'), ext=gl.getExtension('WEBGL_debug_renderer_info');
      const {width,height}=gl.canvas.getBoundingClientRect();
      const resource=performance.getEntriesByType('resource').find(e=>e.name.endsWith('.glb'));
      return { width:innerWidth,height:innerHeight,canvas:[width,height],dpr:devicePixelRatio,
        renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),
        scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,
        panelBottom:document.querySelector('.robot-details').getBoundingClientRect().bottom,
        cardsBottom:document.querySelector('.fleet-panel').getBoundingClientRect().bottom,firstFrameMs:window.firstFrame,firstDecorMs:window.firstDecor??null,
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
      if (data.scrollWidth > width || (width === 1440 &&
          Math.max(data.scrollHeight, data.panelBottom, data.cardsBottom) > height)) {
        throw new Error('Dashboard overflow at '+width);
      }
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
      if (mode !== 'quick') {
        closeRobots = true;
        product = { ...snapshot, tasks: [nearby], robots: [snapshot.robots[0],
          { ...snapshot.robots[1], active_task_id: nearby.task_id }] };
        socket.send(JSON.stringify({ ...product, sequence: ++seq }));
        await page.waitForFunction(() => window.lastFrame?.points.some(point => point.id === 'shipment-warehouse-0217') &&
          window.lastFrame?.robots.every(robot => robot.pose[0] < -3));
        await capture('nearby-pickup-dropoff');
        closeRobots = false;
        product = { ...snapshot, robots: snapshot.robots.map(robot => ({ ...robot, active_task_id: null })),
          tasks: [], task_counts: {total:0,active:0,queued:0} };
        socket.send(JSON.stringify({ ...product, sequence: ++seq }));
        await page.waitForFunction(() => window.lastFrame?.points.length === 2);
        await capture('no-task-park');
      }
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
    if (errors.length) throw new Error(errors.join('\n'));
    data.errors=errors;
    result.windows.push(data);
    writeFileSync(output+'/metrics.json',JSON.stringify(result,null,2));
    clearInterval(timer);
    await page.close();
  }
} finally { await chrome.close(); }
