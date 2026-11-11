// Live Chrome validation. No HTTP/WS interception or synthetic telemetry.
import assert from 'node:assert/strict';
import { createWriteStream, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from '@playwright/test';

const [origin, output, scenario] = process.argv.slice(2);
assert.ok(origin && output && ['a','b'].includes(scenario));
mkdirSync(output,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:join(output,'video')}});
const stream=createWriteStream(join(output,'chrome-ws.jsonl'));
const report={scenario,started:new Date().toISOString(),chrome:browser.version(),responses:[],errors:[],transitions:[]};
let latest;
let lastProductAt=Date.now();
const seen=new Map();
const rendered=[];
const page=await context.newPage();
await page.exposeFunction('captureRendered',detail=>rendered.push({utc:new Date().toISOString(),detail}));
await page.addInitScript(()=>window.addEventListener('fleet-visualizer:rendered',e=>window.captureRendered(e.detail)));
page.on('pageerror',error=>report.errors.push(error.message));
page.on('websocket',socket=>socket.on('framereceived',({payload})=>{
  const packet=JSON.parse(payload.toString());
  const utc=new Date().toISOString();
  stream.write(JSON.stringify({utc,packet})+'\n');
  if(!packet.type){
    latest=packet;
    lastProductAt=Date.now();
    for(const task of packet.tasks){
      const value=task.status+'/'+task.assigned_robot_id;
      if(seen.get(task.task_id)!==value){
        seen.set(task.task_id,value);
        report.transitions.push({utc,sequence:packet.sequence,task});
        console.log(utc,task.task_id,value);
      }
    }
  }
}));
async function until(test,label,timeout=120000){
  const end=Date.now()+timeout;
  while(Date.now()<end){if(await test())return;await delay(200)}
  throw new Error(label);
}
try{
  await page.goto(origin+'/?trace=1#tasks');
  await until(()=>latest?.robots.length===2&&latest.robots.every(r=>r.telemetry==='LIVE'&&r.battery_reliability==='LIVE'), 'Live product data not ready');
  await page.getByRole('heading',{name:'Görev oluştur',exact:true}).waitFor();
  await page.screenshot({path:join(output,'before.png'),fullPage:true});
  const tasks=scenario==='a'?[['pick_A1','packing_1']]:[['pick_A1','packing_1'],['pick_A2','quality_1']];
  for(const [pickup,dropoff] of tasks){
    await page.getByLabel('Alım noktası',{exact:true}).selectOption(pickup);
    await page.getByLabel('Teslim noktası',{exact:true}).selectOption(dropoff);
    await page.getByLabel('Öncelik',{exact:true}).selectOption('LOW');
    const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Görevi gönder',exact:true}).click();
    const response=await responsePromise;
    const request=response.request().postDataJSON();
    const body=await response.json();
    report.responses.push({utc:new Date().toISOString(),status:response.status(),request,body});
    writeFileSync(join(output,'browser-progress.json'),JSON.stringify(report,null,2));
    assert.equal(response.status(),201);
    // Exact accepted browser request replay verifies idempotency against the same live API.
    const retry=await page.evaluate(async payload=>{
      const r=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      return {status:r.status,body:await r.json()};
    },request);
    report.responses.at(-1).retry=retry;
    assert.equal(retry.status,200);
    assert.equal(retry.body.task_id,body.task_id);
    assert.equal(retry.body.outcome,'DUPLICATE');
  }
  await until(()=>latest?.tasks.length===tasks.length,'Accepted task snapshot unavailable',10000);
  await page.screenshot({path:join(output,'accepted.png'),fullPage:true});
  await page.getByRole('link',{name:'Genel görünüm',exact:true}).click();
  const ids=report.responses.map(r=>r.body.task_id);
  let lastShot=0;
  await until(async()=>{
    const tasks=latest?.tasks.filter(t=>ids.includes(t.task_id))??[];
    if(Date.now()-lastProductAt>10000)throw new Error('Live product snapshot unavailable for 10 seconds');
    if(Date.now()-lastShot>30000){
      lastShot=Date.now();
      await page.screenshot({path:join(output,'progress-'+lastShot+'.png'),fullPage:true});
    }
    if(tasks.some(t=>t.status==='FAILED'||t.review_hold))throw new Error('Task failed or held for review');
    return tasks.length===ids.length&&tasks.every(t=>t.status==='COMPLETED');
  },'Tasks did not complete within the 12-minute observation window',720000);
  await page.screenshot({path:join(output,'completed-overview.png'),fullPage:true});
  await page.getByRole('link',{name:'Görevler',exact:true}).click();
  await page.screenshot({path:join(output,'completed.png'),fullPage:true});
  report.final=latest;
  assert.equal(latest.tasks.length,tasks.length);
  if(scenario==='b')assert.equal(new Set(latest.tasks.map(t=>t.assigned_robot_id)).size,2,'Scheduler did not use two robots');
  report.result='geçti';
}catch(error){
  report.result='başarısız';report.failure=error.stack;report.final=latest;
  await page.screenshot({path:join(output,'failure.png'),fullPage:true}).catch(()=>{});
  process.exitCode=1;
}finally{
  report.finished=new Date().toISOString();
  writeFileSync(join(output,'chrome-evidence.json'),JSON.stringify(report,null,2));
  writeFileSync(join(output,'rendered.json'),JSON.stringify(rendered));
  await context.close();await browser.close();stream.end();
}
