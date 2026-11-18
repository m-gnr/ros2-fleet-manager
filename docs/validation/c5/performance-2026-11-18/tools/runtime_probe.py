"""Opt-in timing instrumentation; no policy, source, timeout or data changes."""
import sys,time,os,json,asyncio,runpy,functools,threading
from pathlib import Path
from contextlib import contextmanager
sys.path.insert(0,'/workspace/docker/simulation-warehouse-grid')
role=sys.argv.pop(1);rows=[];lock=threading.Lock();path=Path('/evidence')/(role+'-timing.jsonl');f=path.open('w')
def emit(kind,**v):
 with lock:rows.append(dict(kind=kind,mono=time.monotonic(),utc=time.time(),**v))
def flush():
 while True:
  time.sleep(1)
  with lock:batch=rows[:];rows.clear()
  f.writelines(json.dumps(x)+'\n' for x in batch);f.flush()
threading.Thread(target=flush,daemon=True).start()
if role=='manager':
 import sqlite3
 original_connect=sqlite3.connect
 class TimedConnection(sqlite3.Connection):
  def execute(self,sql,*a,**k):
   if sql not in ('COMMIT','BEGIN IMMEDIATE','ROLLBACK'):return super().execute(sql,*a,**k)
   started=time.monotonic()
   try:return super().execute(sql,*a,**k)
   finally:emit('sqlite_statement',sql=sql,duration_s=time.monotonic()-started)
 def connect(*a,**k):
  k['factory']=TimedConnection
  return original_connect(*a,**k)
 sqlite3.connect=connect
 from backend.fleet_manager.persistence.store import SQLiteStore
 from backend.fleet_manager.event_loop import FleetEventLoop
 from backend.fleet_manager.adapters.route_resolver import AsyncRouteResolver
 import backend.dashboard.runtime as runtime
 import backend.dashboard.publisher as publisher
 old_tx=SQLiteStore.transaction
 @contextmanager
 def transaction(self):
  start=time.monotonic()
  try:
   with old_tx(self):yield
  finally:emit('sqlite_transaction',duration_s=time.monotonic()-start)
 SQLiteStore.transaction=transaction
 old_process=FleetEventLoop._process
 def process(self,event):
  start=time.monotonic()
  try:return old_process(self,event)
  finally:emit('event',event=event.kind,duration_s=time.monotonic()-start,queue=self._queue.qsize())
 FleetEventLoop._process=process
 old_write=publisher._write
 def write(*a,**k):
  start=time.monotonic()
  try:return old_write(*a,**k)
  finally:emit('publisher_write',duration_s=time.monotonic()-start)
 publisher._write=write
 old_compute=AsyncRouteResolver.compute_route
 async def compute(self,*a,**k):
  start=time.monotonic();result=None
  try:result=await old_compute(self,*a,**k);return result
  finally:emit('nav2_query',robot=a[0],duration_s=time.monotonic()-start,success=result is not None)
 AsyncRouteResolver.compute_route=compute
 old_run=runtime.run
 async def lag():
  while True:
   expected=time.monotonic()+.05
   await asyncio.sleep(.05)
   emit('event_loop_lag',lag_s=max(0,time.monotonic()-expected))
 async def run(*a,**k):
  task=asyncio.create_task(lag())
  try:return await old_run(*a,**k)
  finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
 runtime.run=run
 runtime.main()
elif role=='observer':
 import rclpy
 from rclpy.node import Node
 from rclpy.clock import Clock,ClockType
 old_sub=Node.create_subscription;old_node=rclpy.create_node
 def subscription(self,msg_type,topic,callback,*a,**k):
  @functools.wraps(callback)
  def cb(msg):
   start=time.monotonic()
   try:return callback(msg)
   finally:emit('callback',topic=topic,duration_s=time.monotonic()-start)
  return old_sub(self,msg_type,topic,cb,*a,**k)
 Node.create_subscription=subscription
 def create(*a,**k):
  node=old_node(*a,**k);due=[time.monotonic()+.1]
  def timer():
   now=time.monotonic();emit('observer_timer_lag',lag_s=max(0,now-due[0]));due[0]=now+.1
  node.create_timer(.1,timer,clock=Clock(clock_type=ClockType.STEADY_TIME))
  return node
 rclpy.create_node=create
 runpy.run_path('/workspace/docker/simulation-warehouse-grid/stage1_observer.py',run_name='__main__')
