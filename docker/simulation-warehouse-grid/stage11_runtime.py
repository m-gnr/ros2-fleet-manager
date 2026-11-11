"""Observe committed transitions in the real runtime without changing scheduling."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from backend.fleet_manager.event_loop import FleetEventLoop
from backend.dashboard.runtime import main


original = FleetEventLoop._process
previous = {}


def observe(self, event):
    result = original(self, event)
    statuses = {row['task_id']: row['status'] for row in self.store.connection.execute('SELECT task_id,status FROM tasks')}
    changes = {tid: status for tid,status in statuses.items() if previous.get(tid)!=status}
    if changes or event.kind=='ACTION_FEEDBACK':
        record=dict(utc=datetime.now(timezone.utc).isoformat(),monotonic=time.monotonic(),kind=event.kind,
            outcome=result,payload=event.payload if event.kind=='ACTION_FEEDBACK' else {},transitions=changes)
        with Path(os.environ['STAGE11_TRANSITIONS']).open('a') as stream:
            stream.write(json.dumps(record,default=str,allow_nan=False)+'\n')
    previous.update(statuses)
    return result


FleetEventLoop._process = observe
if __name__=='__main__':
    main()
