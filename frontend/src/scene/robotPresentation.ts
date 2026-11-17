import type { Robot } from '../fleet'

export type RobotVisualState = 'idle' | 'active' | 'charging' | 'error' | 'unknown'

export const robotStateColors: Record<Exclude<RobotVisualState, 'unknown'>, string> = {
  idle: '#64748B',
  active: '#6554B5',
  charging: '#44846B',
  error: '#C45151',
}

export function robotVisualState(state: Robot['state']): RobotVisualState {
  if (state === 'IDLE') return 'idle'
  if (state === 'CHARGING') return 'charging'
  if (state === 'ERROR') return 'error'
  if (state === 'EXECUTING_TASK' || state === 'RETURNING_TO_CHARGE' || state === 'RETURNING_TO_PARK') {
    return 'active'
  }
  return 'unknown'
}

export function robotStateColor(state: RobotVisualState) {
  return state === 'unknown' ? '#94A3B8' : robotStateColors[state]
}

export function isMovingState(state: RobotVisualState) {
  return state === 'active'
}
