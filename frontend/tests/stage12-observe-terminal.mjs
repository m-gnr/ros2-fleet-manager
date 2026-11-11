// Read-only observation after an acceptance failure; never submits or retries a task.
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';
import assert from 'node:assert/strict';
const [origin,output]=process.argv.slice(2);
assert.ok(origin&&output);mkdirSync(output,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
let latest;const observed=[];
page.on('websocket',socket=>socket.on('framereceived',({payload})=>{
  const packet=JSON.parse(payload.toString());
  if(!packet.type){latest=packet;observed.push({utc:new Date().toISOString(),tasks:packet.tasks});}
}));
try{
  await page.goto(origin+'/#tasks');
  const deadline=Date.now()+150000;
  while(!(latest?.tasks.length===2&&latest.tasks.every(t=>['COMPLETED','FAILED'].includes(t.status)))){
    if(Date.now()>deadline)throw new Error('Two terminal tasks were not observed');
    await delay(200);
  }
  await page.getByRole('heading',{name:'Görevler',exact:true}).waitFor();
  for(const task of latest.tasks){
    const row=page.getByRole('row').filter({hasText:task.task_id});
    await row.getByText(task.status==='COMPLETED'?'Tamamlandı':'Başarısız',{exact:true}).waitFor();
  }
  await page.screenshot({path:output+'/terminal-tasks.png',fullPage:true});
  writeFileSync(output+'/terminal-observation.json',JSON.stringify({chrome:browser.version(),latest,observed},null,2));
}finally{await browser.close();}
