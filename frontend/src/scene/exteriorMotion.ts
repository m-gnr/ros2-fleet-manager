import { useEffect } from 'react'
import { useThree } from '@react-three/fiber'
import type { Group } from 'three'
import type { RefObject } from 'react'

// Wall-clock decoration only; pausing freezes the local phase, with no catch-up on resume.
export function useExteriorMotion(root: RefObject<Group | null>, enabled: boolean, road: {
  left: number; right: number; roadZ: number; truckX: number
}) {
  const invalidate = useThree(state => state.invalidate)
  useEffect(() => {
    const group = root.current!
    const state = group.userData.motion ??= { elapsed: 0, ticks: 0, running: false,
      roadVehicles: 0, truckOffset: 0 }
    let timer: ReturnType<typeof setTimeout> | undefined
    let previous = performance.now()
    const paint = () => {
      const { offset, roadPhase } = exteriorMotionPose(state.elapsed)
      const truck = group.getObjectByName('shipping-truck-motion')!
      if (truck) truck.position.x = road.truckX + offset
      const car = group.getObjectByName('road-car-motion')!
      const phase = roadPhase
      car.visible = phase < 16
      car.position.set(road.left - 20 + phase / 16 * (road.right - road.left + 40), 0, road.roadZ + 1.35)
      state.roadVehicles = car.visible ? 1 : 0
      state.truckOffset = offset
    }
    const tick = () => {
      if (!enabled || document.hidden) return
      const now = performance.now()
      state.elapsed += (now - previous) / 1000
      previous = now
      state.ticks++
      paint()
      invalidate()
      timer = setTimeout(tick, 50)
    }
    const sync = () => {
      clearTimeout(timer)
      state.running = enabled && !document.hidden
      previous = performance.now()
      if (state.running) timer = setTimeout(tick, 50)
      invalidate()
    }
    paint()
    sync()
    document.addEventListener('visibilitychange', sync)
    return () => {
      clearTimeout(timer)
      state.running = false
      document.removeEventListener('visibilitychange', sync)
    }
  }, [enabled, invalidate, root, road])
}

export function exteriorMotionPose(elapsed: number) {
  const phase = elapsed % 80
  const offset = phase < 12 ? 0 : phase < 32 ? (phase - 12) / 20 * 2.8
    : phase < 52 ? 2.8 : phase < 72 ? (72 - phase) / 20 * 2.8 : 0
  return { offset, roadPhase: elapsed % 56 }
}
