import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { PerspectiveCamera, Vector3 } from 'three'
import { chromium } from '@playwright/test'

const [beforeUrl, afterUrl, beforeFile, afterFile, costmapFile, output, liveFile, operatorUrl] = process.argv.slice(2)
assert.ok(output, 'Provide before/after URLs and fixtures, a Nav2 costmap capture and evidence directory')
const read = path => JSON.parse(readFileSync(path, 'utf8'))
const costmap = read(costmapFile)
const live = liveFile ? read(liveFile) : undefined
mkdirSync(output, { recursive: true })
const chrome = await chromium.launch({ channel: 'chrome', headless: true })
const evidence = { chrome: chrome.version(), source: 'controlled product fixture and recorded Nav2 costmap', captures: {} }

async function capture(url, fixture, modern) {
  const page = await chrome.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 })
  const errors = []
  const { fleet, layout } = fixture.original
  let timer, stamp = 1_000_000_000, sequence = fleet.sequence
  page.on('pageerror', error => errors.push(error.message))
  await page.addInitScript(() => {
    window.addEventListener('fleet-visualizer:frame', event => { window.frame = event.detail })
    window.addEventListener('fleet-visualizer:warehouse-bounds', event => { window.corners = event.detail })
  })
  await page.route('**/api/warehouse-layout', route => route.fulfill({ json: layout }))
  await page.route('**/api/task-catalog', route => route.fulfill({ json: { ...layout, enabled: modern } }))
  await page.route('**/api/warehouse-costmap', route => route.fulfill({ json: costmap }))
  await page.routeWebSocket('**/ws/fleet', socket => {
    const send = packet => socket.send(JSON.stringify({ type: 'scene', packet }))
    socket.send('{"type":"scene_connected"}')
    send({ type: 'fleet_hello', version: 1, robot_ids: fleet.robots.map(r => r.robot_id) })
    for (const robot of fleet.robots) {
      send({ type: 'hello', version: 1, stream_id: fleet.source_session_id, robot_id: robot.robot_id,
        epoch: 0, frame_id: 'map', source: 'tf', after_stamp_ns: '0', stale_after_ms: 10000,
        path_topic: `/${robot.robot_id}/plan` })
    }
    const tick = () => {
      socket.send(JSON.stringify({ ...fleet, sequence: ++sequence }))
      for (const robot of fleet.robots) {
        const measured = modern && (live?.final_pose?.[robot.robot_id] ?? live?.traces?.[robot.robot_id]?.at(-1))
        const [x,y,yaw] = measured ? measured.slice(1) : [robot.pose.x,robot.pose.y,robot.pose.yaw]
        send({ type: 'robot_pose', version: 1, stream_id: fleet.source_session_id, robot_id: robot.robot_id,
          epoch: 0, frame_id: 'map', source: 'tf', x,y,yaw, stamp_ns: String(stamp += 100_000_000) })
      }
      const path = modern && live?.routes?.[0]?.legs?.[1]?.path
      if (path?.length) send({ type: 'robot_path', version: 1, stream_id: fleet.source_session_id,
        robot_id: fleet.robots[0].robot_id, epoch: 0, frame_id: 'map', source: 'tf',
        source_topic: `/${fleet.robots[0].robot_id}/plan`, plan_source: 'nav2_observed_plan',
        stamp_ns: String(stamp += 100_000_000), ttl_ms: 2000, points: path })
    }
    tick()
    clearInterval(timer)
    timer = setInterval(tick, 100)
  })
  try {
    await page.goto(url+'/?trace=1')
    await page.waitForFunction(() => window.frame?.warehouse === 'grid' && window.frame.robots.filter(r => r.visible).length === 2)
    await page.waitForTimeout(1200)
    if(modern&&live) await page.locator('.scene-legend small').evaluate(node=>{
      node.textContent='Ortak YAML · Nav2/TF kaydı · ürün telemetrisi ayrı kaynaktır'
    })
    await page.screenshot({ path: join(output, modern ? 'after.png' : 'before.png') })
    const frame = () => page.evaluate(() => window.frame)
    const framed = async () => {
      const canvas = await page.locator('.scene-viewport canvas').boundingBox()
      const f = await frame()
      const corners = await page.evaluate(() => window.corners)
      const camera = new PerspectiveCamera(42,canvas.width/canvas.height,.035,240)
      camera.position.fromArray(f.camera)
      camera.lookAt(new Vector3().fromArray(f.target))
      camera.updateMatrixWorld()
      const projected = corners.map(p => new Vector3().fromArray(p).project(camera).toArray())
      assert.ok(projected.every(([x,y,z]) => Math.abs(x)<=1 && Math.abs(y)<=1 && Math.abs(z)<=1), 'warehouse must fit')
      return { camera:f.camera, calls:f.calls, geometries:f.geometries, textures:f.textures, corners:projected }
    }
    const overview = await framed()
    await page.getByRole('button',{name:'Üstten',exact:true}).click()
    await page.waitForFunction(() => window.frame?.mode === 'top' && !window.frame.transitioning)
    await page.waitForTimeout(200)
    await page.screenshot({ path:join(output,modern?'after-top.png':'before-top.png') })
    if (!modern) return { overview, top:await framed(), errors }
    assert.equal(costmap.profile_digest,layout.profile_digest)
    assert.equal(layout.layout.racks.length,10)
    assert.equal(layout.layout.transfer_points.filter(p=>p.rack_id).length,10)
    assert.equal((await frame()).routeHiddenRacks.length,0)
    const visibleLabels = () => page.locator('.scene-point-label:visible').evaluateAll(nodes => nodes
      .filter(node => getComputedStyle(node).visibility === 'visible').map(node => ({
        text:node.textContent,key:node.dataset.operationPoint,
        box:{x:node.getBoundingClientRect().x,y:node.getBoundingClientRect().y,
          width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height},
      })))
    const far = await visibleLabels()
    if(fleet.robots.some(robot=>robot.charging==='UNAVAILABLE')) {
      assert.ok(far.some(label=>label.text.includes('Şarj —/')), 'unknown charging must be masked')
    }
    assert.ok(far.every(label=>label.key.startsWith('zone:')), 'far view only shows region labels')
    for (const name of ['Paketleme','Sevkiyat','Şarj']) assert.ok(far.some(label=>label.text.includes(name)), name)
    for (let i=0;i<far.length;i++) for (const b of far.slice(i+1)) {
      const a=far[i].box, c=b.box
      assert.ok(a.x+a.width<=c.x || c.x+c.width<=a.x || a.y+a.height<=c.y || c.y+c.height<=a.y,'region labels overlap')
    }
    const view = await page.locator('.scene-viewport canvas').boundingBox()
    const f = await frame()
    const camera = new PerspectiveCamera(42,view.width/view.height,.035,240)
    camera.position.fromArray(f.camera)
    camera.lookAt(new Vector3().fromArray(f.target))
    camera.updateMatrixWorld()
    const rackRects = layout.layout.racks.map(rack=>{
      const points=[]
      for(const x of [rack.bounds.x_min,rack.bounds.x_max]) for(const y of [rack.bounds.y_min,rack.bounds.y_max]) {
        for(const z of [0,rack.height]) {
          const p=new Vector3(x,z,-y).project(camera)
          points.push([view.x+(p.x+1)*view.width/2,view.y+(1-p.y)*view.height/2])
        }
      }
      return {id:rack.id,x:Math.min(...points.map(p=>p[0])),right:Math.max(...points.map(p=>p[0])),
        y:Math.min(...points.map(p=>p[1])),bottom:Math.max(...points.map(p=>p[1]))}
    })
    for(const label of far) for(const rack of rackRects) {
      const b=label.box
      assert.ok(b.x+b.width<=rack.x || b.x>=rack.right || b.y+b.height<=rack.y || b.y>=rack.bottom,
        `${label.key} overlaps ${rack.id}`)
    }
    await page.getByRole('checkbox',{name:'Costmap katmanı'}).check()
    await page.getByText('Nav2 global costmap · kayıt',{exact:false}).waitFor()
    await page.waitForTimeout(500)
    await page.screenshot({ path:join(output,'after-costmap.png') })
    await page.getByRole('checkbox',{name:'Costmap katmanı'}).uncheck()
    const canvas = await page.locator('.scene-viewport canvas').boundingBox()
    await page.mouse.move(canvas.x+canvas.width/2,canvas.y+canvas.height/2)
    await page.mouse.wheel(0,-1500)
    await page.waitForTimeout(1200)
    const near = await visibleLabels()
    assert.ok(near.some(label=>label.key.startsWith('detail:')), 'near view shows individual IDs')
    await page.screenshot({path:join(output,'after-close.png')})
    await page.getByRole('button',{name:'Kamerayı sıfırla'}).click()
    await page.waitForFunction(()=>window.frame?.mode==='free' && !window.frame.transitioning)
    await page.setViewportSize({width:390,height:844})
    await page.waitForTimeout(800)
    const mobile = await framed()
    await page.screenshot({path:join(output,'after-mobile.png')})
    await page.setViewportSize({width:1440,height:1000})
    const shelf=layout.layout.transfer_points.find(point=>point.id==='pick_B1')
    const inbound=layout.layout.transfer_points.find(point=>point.id==='inbound_1')
    fleet.tasks=[{task_id:'acceptance-inbound',status:'QUEUED',priority:'LOW',
      pickup:{...inbound.pose,frame_id:'map'},dropoff:{...shelf.pose,frame_id:'map'},
      assigned_robot_id:null,created_at_source_seconds:1,review_hold:false}]
    fleet.task_counts={total:1,active:0,queued:1}
    await page.waitForFunction(()=>window.frame?.points.some(point=>point.key==='dropoff:acceptance-inbound'))
    const atShelf=(await frame()).points.filter(point=>point.position[0]===shelf.pose.x&&point.position[2]===-shelf.pose.y)
    assert.equal(atShelf.length,1,'a shelf delivery must replace the catalog pickup pad')
    assert.equal(atShelf[0].kind,'dropoff')
    fleet.tasks=[]
    fleet.task_counts={total:0,active:0,queued:0}
    const commands=[]
    await page.route('**/api/tasks',async route=>{
      const request=route.request().postDataJSON()
      commands.push(request)
      await route.fulfill({status:201,json:{task_id:'web-'+request.request_id,outcome:'APPLIED'}})
    })
    await page.getByRole('link',{name:'Görevler',exact:true}).click()
    await page.getByRole('heading',{name:'Görev oluştur',exact:true}).waitFor()
    for (const task of layout.layout.example_tasks) {
      await page.getByLabel('Örnek rota',{exact:true}).selectOption(task.id)
      assert.equal(await page.getByLabel('Alım noktası',{exact:true}).inputValue(),task.pickup)
      assert.equal(await page.getByLabel('Teslim noktası',{exact:true}).inputValue(),task.dropoff)
      const submitted=page.waitForResponse(response=>response.url().endsWith('/api/tasks')&&response.request().method()==='POST')
      await page.getByRole('button',{name:'Görevi gönder',exact:true}).click()
      await submitted
      await page.getByText('Fleet Manager kabul etti',{exact:false}).waitFor()
    }
    assert.equal(commands.length,3)
    assert.equal(new Set(commands.map(c=>c.request_id)).size,3)
    assert.equal(commands[2].dropoff_id,'pick_B1')
    await page.screenshot({path:join(output,'tasks.png')})
    assert.deepEqual(errors,[])
    return {overview,mobile,far,near,rackRects,atShelf,commands,errors,costmap:{source:costmap.source,width:costmap.width,
      height:costmap.height,origin:costmap.origin,resolution:costmap.resolution}}
  } finally {clearInterval(timer);await page.close()}
}

try {
  evidence.captures.before=await capture(beforeUrl,read(beforeFile),false)
  evidence.captures.after=await capture(afterUrl,read(afterFile),true)
  if(operatorUrl){
    const page=await chrome.newPage({viewport:{width:1440,height:1000}})
    const errors=[]
    page.on('pageerror',error=>errors.push(error.message))
    await page.goto(operatorUrl+'/#tasks')
    await page.getByRole('heading',{name:'Görev oluştur',exact:true}).waitFor()
    const responses=[]
    for(const task of read(afterFile).original.layout.layout.example_tasks){
      await page.getByLabel('Örnek rota',{exact:true}).selectOption(task.id)
      const submitted=page.waitForResponse(response=>response.url().endsWith('/api/tasks')&&response.request().method()==='POST')
      await page.getByRole('button',{name:'Görevi gönder',exact:true}).click()
      const response=await submitted
      assert.equal(response.status(),201)
      responses.push(await response.json())
    }
    await page.waitForFunction(()=>document.querySelectorAll('tbody tr').length===3)
    await page.screenshot({path:join(output,'tasks.png')})
    assert.deepEqual(errors,[])
    evidence.hostTaskAPI={responses,errors}
    await page.close()
  }
  writeFileSync(join(output,'chrome-evidence.json'),JSON.stringify(evidence,null,2)+'\n')
  console.log('Distributed warehouse Chrome acceptance passed')
} finally {await chrome.close()}
