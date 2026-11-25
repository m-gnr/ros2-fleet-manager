"""Pre-task scene readiness only. Never permit/actuator health authorization."""
REQUIRED=('clock','odometry','tf','amcl','observation:local',
    'lifecycle:amcl','lifecycle:controller_server','lifecycle:planner_server','lifecycle:bt_navigator')
PRE_TASK_UNKNOWN={'NO_ACTUAL_PERMIT_CONTEXT','STALE_OR_UNKNOWN:native','STALE_OR_UNKNOWN:robot_status'}


def scene_ready(result,initialization_stamp_ns):
    ages=result.get('source_ages',{})
    return (all(ages.get(name,{}).get('current') is True for name in REQUIRED)
        and ages['amcl']['source_stamp_ns']>=initialization_stamp_ns
        and not (set(result.get('reasons',[]))-PRE_TASK_UNKNOWN)
        and result.get('movement_eligible') is False and result.get('ownership_release') is False)
