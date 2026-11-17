import { useEffect, useRef, useState } from "react";
import { compareSnapshot, fleetSchema, type Fleet } from "./fleet";

import { connectFleet, disconnectFleet, expireFleet, initialFleet, receiveFleet } from "./scene/fleet";
import { createSceneFeed } from "./scene/sceneFeed";

export type Connection = "CONNECTING" | "CONNECTED" | "RECONNECTING" | "DISCONNECTED";

const FRAME_LIMIT = 513 * 1024;
const SILENCE_MS = 2200;
const RECONNECT_NOTICE_MS = 5000;
const CONNECTION_ERROR_MS = 15000;

export function useFleet() {
  const [fleet, setFleet] = useState<Fleet | null>(null);
  const [connection, setConnection] = useState<Connection>("CONNECTING");
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const latest = useRef<Fleet | null>(null);
  const [sceneFeed] = useState(createSceneFeed);
  const [scene, setScene] = useState(initialFleet);

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | undefined;
    let reconnect: ReturnType<typeof setTimeout>;
    let watchdog: ReturnType<typeof setTimeout>;
    let reconnectNotice: ReturnType<typeof setTimeout>;
    let connectionError: ReturnType<typeof setTimeout>;
    let attempts = 0;
    let productWatchdog: ReturnType<typeof setTimeout>;
    let lastScenePacket = 0;
    let outageStartedAt: number | undefined;
    let protocolError: string | undefined;

    function beginOutage() {
      if (outageStartedAt !== undefined) return;
      outageStartedAt = performance.now();
      setConnection("CONNECTING");
      if (!protocolError) setError(null);
      reconnectNotice = setTimeout(() => {
        if (!stopped && outageStartedAt !== undefined) setConnection("RECONNECTING");
      }, RECONNECT_NOTICE_MS);
      connectionError = setTimeout(() => {
        if (stopped || outageStartedAt === undefined || protocolError) return;
        setConnection("DISCONNECTED");
        setError("Görev ve rezervasyon verilerine 15 saniyeden uzun süredir erişilemiyor.");
      }, CONNECTION_ERROR_MS);
    }

    function restoreConnection() {
      outageStartedAt = undefined;
      clearTimeout(reconnectNotice);
      clearTimeout(connectionError);
      protocolError = undefined;
      setConnection("CONNECTED");
      setError(null);
    }

    function updateScene(next: typeof initialFleet) {
      if (next !== sceneFeed.read()) sceneFeed.update(next);
    }

    const publishScene = window.setInterval(() => {
      const now = performance.now();
      const current = sceneFeed.read();
      if (current.connection === "CONNECTED" && now - lastScenePacket > 2500) {
        updateScene(disconnectFleet(current));
      } else {
        updateScene(expireFleet(current, now));
      }
      setScene(sceneFeed.read());
    }, 200);

    function connect() {
      if (stopped) return;
      beginOutage();
      const url = new URL("/ws/fleet", window.location.href);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      const peer = new WebSocket(url, "fleet.scene.v1");
      socket = peer;
      let first = true;

      function armWatchdog() {
        clearTimeout(watchdog);
        watchdog = setTimeout(() => {
          beginOutage();
          peer.close();
        }, SILENCE_MS);
      }
      function productUnavailable() {
        clearTimeout(productWatchdog);
        first = true;
        beginOutage();
        peer.close();
      }
      armWatchdog();
      peer.onmessage = (event) => {
        if (stopped || peer !== socket || peer.readyState !== WebSocket.OPEN) return;
        try {
          if (typeof event.data !== "string" || event.data.length > FRAME_LIMIT) throw new Error();
          const message = JSON.parse(event.data);
          switch (message?.type) {
            case "heartbeat":
              armWatchdog();
              return;
            case "product_unavailable":
              productUnavailable();
              armWatchdog();
              return;
            case "scene_connected":
              lastScenePacket = performance.now();
              updateScene(connectFleet(sceneFeed.read()));
              return;
            case "scene_disconnected":
              updateScene(disconnectFleet(sceneFeed.read()));
              return;
            case "scene": {
              const now = performance.now();
              const current = sceneFeed.read();
              const next = receiveFleet(current, JSON.stringify(message.packet), now);
              if (next !== current) {
                lastScenePacket = now;
                updateScene(next);
              }
              return;
            }
          }
          const next = fleetSchema.parse(message);
          const decision = compareSnapshot(next, latest.current, first);
          if (decision === "resync") throw new Error();
          if (decision === "ignore") return;
          if (decision === "apply") {
            latest.current = next;
            setFleet(next);
          }
          first = false;
          attempts = 0;
          restoreConnection();
          clearTimeout(productWatchdog);
          productWatchdog = setTimeout(productUnavailable, SILENCE_MS);
          armWatchdog();
        } catch {
          protocolError = "Filo akışı doğrulanamadı. Yeniden eşitleniyor.";
          setError(protocolError);
          peer.close();
        }
      };
      peer.onerror = () => {
        if (!stopped && peer === socket) beginOutage();
      };
      peer.onclose = () => {
        if (stopped || peer !== socket) return;
        clearTimeout(watchdog);
        clearTimeout(productWatchdog);
        updateScene(disconnectFleet(sceneFeed.read()));
        beginOutage();
        const delay = Math.min(4000, 400 * 2 ** attempts++);
        reconnect = setTimeout(connect, delay);
      };
    }
    connect();
    return () => {
      stopped = true;
      clearTimeout(reconnect);
      clearTimeout(watchdog);
      clearTimeout(reconnectNotice);
      clearTimeout(connectionError);
      clearTimeout(productWatchdog);
      window.clearInterval(publishScene);
      updateScene(disconnectFleet(sceneFeed.read()));
      socket?.close();
    };
  }, [retry, sceneFeed]);

  return { fleet, connection, error, scene, sceneFeed, reconnect: () => setRetry((value) => value + 1) };
}
