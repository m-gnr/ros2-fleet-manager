import { useEffect, useState } from 'react'
import { connected, disconnected, expire, initial, receive } from './telemetry'
import type { Telemetry } from './telemetry'

const retryMs = 750
const heartbeatTimeoutMs = 2500

export function useTelemetry(url: string) {
  const [view, setView] = useState(initial)
  useEffect(() => {
    let state: Telemetry = initial
    let socket: WebSocket | undefined
    let retry: number | undefined
    let lastPacketAt = 0
    let stopped = false

    function update(next: Telemetry) {
      if (next !== state) {
        state = next
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
        if (socket === candidate) update(connected(state))
      }
      candidate.onmessage = ({ data }) => {
        if (socket !== candidate) return
        const now = performance.now()
        const next = receive(state, data, now)
        if (next !== state) {
          lastPacketAt = now
          update(next)
        }
      }
      function lost() {
        if (socket !== candidate) return
        socket = undefined
        candidate.close()
        update(disconnected(state))
        retry = window.setTimeout(connect, retryMs)
      }
      candidate.onclose = lost
      candidate.onerror = lost
    }

    connect()
    const timer = window.setInterval(() => {
      const now = performance.now()
      update(expire(state, now))
      if (socket && now - lastPacketAt > heartbeatTimeoutMs) {
        socket.close()
        socket = undefined
        update(disconnected(state))
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
  }, [url])
  return view
}
