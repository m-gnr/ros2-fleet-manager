import { useEffect, useState } from 'react'
import { connectFleet, disconnectFleet, expireFleet, initialFleet, receiveFleet, type Fleet } from './fleet'

const retryMs = 750
const heartbeatTimeoutMs = 2500

function createSceneFeed() {
  let current = initialFleet
  const listeners = new Set<() => void>()
  return {
    read: () => current,
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => { listeners.delete(listener) }
    },
    update(next: Fleet) {
      const poseChanged = current.robots.size !== next.robots.size || [...next.robots].some(([id, robot]) => {
        const before = current.robots.get(id)
        return robot.pose !== before?.pose || robot.previous !== before?.previous || robot.status !== before?.status
      })
      current = next
      if (poseChanged) listeners.forEach(listener => listener())
    },
  }
}

export type SceneFeed = ReturnType<typeof createSceneFeed>

export function useTelemetry(url: string) {
  const [view, setView] = useState(initialFleet)
  const [feed] = useState(createSceneFeed)
  useEffect(() => {
    let state = initialFleet
    let socket: WebSocket | undefined
    let retry: number | undefined
    let lastPacketAt = 0
    let stopped = false

    function update(next: Fleet) {
      if (next !== state) {
        state = next
        feed.update(next)
        setView(next)
      }
    }

    function connect() {
      if (stopped) return
      let candidate: WebSocket
      try { candidate = new WebSocket(url) } catch { return }
      socket = candidate
      lastPacketAt = performance.now()
      candidate.onopen = () => {
        if (socket === candidate) update(connectFleet(state))
      }
      candidate.onmessage = ({ data }) => {
        if (socket !== candidate) return
        const now = performance.now()
        const next = receiveFleet(state, data, now)
        if (next !== state) {
          lastPacketAt = now
          update(next)
        }
      }
      function lost() {
        if (socket !== candidate) return
        socket = undefined
        candidate.close()
        update(disconnectFleet(state))
        retry = window.setTimeout(connect, retryMs)
      }
      candidate.onclose = lost
      candidate.onerror = lost
    }

    connect()
    const timer = window.setInterval(() => {
      const now = performance.now()
      update(expireFleet(state, now))
      if (socket && now - lastPacketAt > heartbeatTimeoutMs) {
        socket.close()
        socket = undefined
        update(disconnectFleet(state))
        retry = window.setTimeout(connect, retryMs)
      }
    }, 100)
    return () => {
      stopped = true
      const active = socket
      socket = undefined
      active?.close()
      window.clearInterval(timer)
      window.clearTimeout(retry)
    }
  }, [url, feed])
  return { view, feed }
}
