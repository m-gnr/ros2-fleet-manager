import { useEffect, useRef, useState } from "react";
import { compareSnapshot, fleetSchema, type Fleet } from "./fleet";

export type Connection = "CONNECTING" | "CONNECTED" | "RECONNECTING" | "DISCONNECTED";

const FRAME_LIMIT = 513 * 1024;
const SILENCE_MS = 2200;

export function useFleet() {
  const [fleet, setFleet] = useState<Fleet | null>(null);
  const [connection, setConnection] = useState<Connection>("CONNECTING");
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const latest = useRef<Fleet | null>(null);

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | undefined;
    let reconnect: ReturnType<typeof setTimeout>;
    let watchdog: ReturnType<typeof setTimeout>;
    let attempts = 0;

    function connect() {
      if (stopped) return;
      setConnection(attempts || retry ? "RECONNECTING" : "CONNECTING");
      const url = new URL("/ws/fleet", window.location.href);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      const peer = new WebSocket(url);
      socket = peer;
      let first = true;

      function armWatchdog() {
        clearTimeout(watchdog);
        watchdog = setTimeout(() => {
          setError("Filo akışından güncel veri alınamadı.");
          peer.close();
        }, SILENCE_MS);
      }
      armWatchdog();
      peer.onmessage = (event) => {
        if (stopped || peer !== socket || peer.readyState !== WebSocket.OPEN) return;
        try {
          if (typeof event.data !== "string" || event.data.length > FRAME_LIMIT) throw new Error();
          const next = fleetSchema.parse(JSON.parse(event.data));
          const decision = compareSnapshot(next, latest.current, first);
          if (decision === "resync") throw new Error();
          if (decision === "ignore") return;
          if (decision === "apply") {
            latest.current = next;
            setFleet(next);
          }
          first = false;
          attempts = 0;
          setConnection("CONNECTED");
          setError(null);
          armWatchdog();
        } catch {
          setError("Filo akışı doğrulanamadı. Yeniden eşitleniyor.");
          peer.close();
        }
      };
      peer.onerror = () => {
        if (!stopped && peer === socket) setError("Operasyon sunucusuna erişilemiyor.");
      };
      peer.onclose = () => {
        if (stopped || peer !== socket) return;
        clearTimeout(watchdog);
        setConnection("DISCONNECTED");
        setError((message) => message ?? "Canlı bağlantı kesildi.");
        const delay = Math.min(4000, 400 * 2 ** attempts++);
        reconnect = setTimeout(connect, delay);
      };
    }
    connect();
    return () => {
      stopped = true;
      clearTimeout(reconnect);
      clearTimeout(watchdog);
      socket?.close();
    };
  }, [retry]);

  return { fleet, connection, error, reconnect: () => setRetry((value) => value + 1) };
}
