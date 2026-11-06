import { initialFleet, type Fleet } from './fleet'

export function createSceneFeed() {
  let current = initialFleet
  const listeners = new Set<() => void>()
  return {
    read: () => current,
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => { listeners.delete(listener) }
    },
    update(next: Fleet) {
      const sceneChanged = current.robots.size !== next.robots.size || [...next.robots].some(([id, robot]) => {
        const before = current.robots.get(id)
        return robot.pose !== before?.pose || robot.previous !== before?.previous || robot.status !== before?.status ||
          robot.path !== before?.path || robot.trail !== before?.trail
      })
      current = next
      if (sceneChanged) listeners.forEach(listener => listener())
    },
  }
}

export type SceneFeed = ReturnType<typeof createSceneFeed>
