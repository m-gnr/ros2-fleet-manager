import { memo, useLayoutEffect, useRef, useState } from "react";
import { BatteryCharging, Crosshair, Maximize, Minus, Plus } from "lucide-react";
import { Arrow, Circle, Group, Layer, Line, Rect, Stage, Text } from "react-konva";
import type { Fleet, Reliability, Station } from "./fleet";
import { fitCamera, projectPose, zoomCamera, type Camera } from "./mapMath";

const rows = [
  { x: -4.0, y: -2.7, label: "A" }, { x: 1.95, y: -2.7, label: "B" },
  { x: -4.0, y: 0.45, label: "C" }, { x: 1.95, y: 0.45, label: "D" },
  { x: -7.7, y: -2.7, label: "E" }, { x: 5.6, y: 0.45, label: "F" },
];
const grid = Array.from({ length: 31 }, (_, index) => index - 15);

const Floor = memo(function Floor() {
  return (
    <Group listening={false}>
      {grid.map((position) => (
        <Group key={position}>
          <Line points={[position, -15, position, 15]} stroke="#e1e9eb" strokeWidth={0.012} />
          <Line points={[-15, position, 15, position]} stroke="#e1e9eb" strokeWidth={0.012} />
        </Group>
      ))}
      <Rect x={-8.5} y={-3.18} width={17} height={6.36} cornerRadius={0.18}
        fill="#f7faf9" stroke="#d9e5e5" strokeWidth={0.018} dash={[0.10, 0.07]} />
      <Line points={[-8.1, 0, 8.1, 0]} stroke="#dbe7e6" strokeWidth={0.024} dash={[0.14, 0.10]} />
      <Line points={[0, -2.92, 0, 2.92]} stroke="#dbe7e6" strokeWidth={0.024} dash={[0.14, 0.10]} />
      <Line points={[-5.05, -2.92, -5.05, 2.92]} stroke="#dbe7e6" strokeWidth={0.024} dash={[0.14, 0.10]} />
      <Line points={[5.05, -2.92, 5.05, 2.92]} stroke="#dbe7e6" strokeWidth={0.024} dash={[0.14, 0.10]} />
      <Rect x={-7.7} y={0.46} width={2.23} height={1.61} cornerRadius={0.10} fill="#eef4f3"
        stroke="#ccdddd" strokeWidth={0.024} dash={[0.13, 0.08]} />
      <Rect x={5.6} y={-2.69} width={2.23} height={1.61} cornerRadius={0.10} fill="#eef4f3"
        stroke="#ccdddd" strokeWidth={0.024} dash={[0.13, 0.08]} />
      {rows.map(({ x, y, label }) => (
        <Group x={x} y={y} key={label}>
          <Text y={-0.24} text={`RAF ALANI  ${label}`} fill="#7c9296" fontSize={0.17} fontStyle="bold" />
          {[0, 0.58, 1.16, 1.74].map((cell) => (
            <Group x={cell} key={cell}>
              <Rect width={0.50} height={1.62} cornerRadius={0.055} fill="#e5edee" stroke="#d5e1e3" strokeWidth={0.014} />
              <Line points={[0.07, 0.54, 0.43, 0.54]} stroke="#cbdadb" strokeWidth={0.017} />
              <Line points={[0.07, 1.08, 0.43, 1.08]} stroke="#cbdadb" strokeWidth={0.017} />
            </Group>
          ))}
        </Group>
      ))}
      <Circle radius={0.055} stroke="#758e92" strokeWidth={0.018} />
    </Group>
  );
});

const markerColor: Record<Reliability, string> = {
  LIVE: "#087d70", STALE: "#976718", BLOCKED: "#b44549", NO_DATA: "#71858a", UNAVAILABLE: "#71858a",
};

function RobotMarker({ id, x, y, rotation, reliability, selected, scale, onSelect }: {
  id: string; x: number; y: number; rotation: number; reliability: Reliability;
  selected: boolean; scale: number; onSelect: () => void;
}) {
  const color = markerColor[reliability];
  return (
    <Group x={x} y={y} scaleX={1 / scale} scaleY={1 / scale} onClick={onSelect} onTap={onSelect}
      onMouseEnter={(event) => { event.target.getStage()!.container().style.cursor = "pointer"; }}
      onMouseLeave={(event) => { event.target.getStage()!.container().style.cursor = ""; }}>
      {selected && <Circle radius={23} fill={color} opacity={0.15} />}
      <Circle radius={16} fill="white" stroke={color} strokeWidth={selected ? 2.6 : 1.8}
        dash={reliability === "LIVE" ? [] : [4, 2]} shadowColor="#234b4d" shadowBlur={6} shadowOpacity={0.15} />
      <Group rotation={rotation} listening={false}>
        <Arrow points={[-7, 0, 7, 0]} stroke={color} fill={color} strokeWidth={2.6}
          pointerLength={6} pointerWidth={8} lineCap="round" />
      </Group>
      <Rect x={-39} y={22} width={78} height={19} cornerRadius={5} fill="white" stroke="#d9e4e4" strokeWidth={1} />
      <Text x={-39} y={26} width={78} text={id} fill={color} fontSize={11} fontStyle="bold" align="center" />
    </Group>
  );
}

function StationMarker({ station, x, y, scale }: { station: Station; x: number; y: number; scale: number }) {
  const charging = station.station_type === "CHARGING";
  const color = station.state === "BLOCKED" ? "#a73741" : charging ? "#7358a6" : "#42658b";
  const letter = charging ? "Ş" : station.station_type === "PARKING" ? "P" : "B";
  return (
    <Group x={x} y={y} scaleX={1 / scale} scaleY={1 / scale} listening={false}>
      <Rect x={-12} y={-12} width={24} height={24} cornerRadius={6} fill="#fff" stroke={color} strokeWidth={1.6} />
      <Text x={-12} y={-6} width={24} text={letter} align="center" fontStyle="bold" fontSize={12} fill={color} />
      <Text x={-45} y={16} width={90} text={station.station_id} align="center" fontSize={10} fill={color} />
    </Group>
  );
}

export function WarehouseMap({ fleet, connected, selected, onSelect }: {
  fleet: Fleet | null; connected: boolean; selected: string | undefined; onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [customCamera, setCamera] = useState<Camera | null>(null);

  useLayoutEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: Math.floor(entry.contentRect.width), height: Math.floor(entry.contentRect.height) });
      setCamera(null);
    });
    observer.observe(container.current!);
    return () => observer.disconnect();
  }, []);

  const frame = fleet?.map_frame ?? "map";
  const robots = (fleet?.robots ?? []).flatMap((robot) => {
    const point = robot.pose && projectPose(robot.pose, frame);
    return point ? [{ robot, point }] : [];
  });
  const stations = (fleet?.stations ?? []).flatMap((station) => {
    const point = station.pose && projectPose(station.pose, frame);
    return point ? [{ station, point }] : [];
  });
  const camera = customCamera ?? fitCamera([...robots, ...stations].map((entry) => entry.point), size.width, size.height);
  const midpoint = { x: size.width / 2, y: size.height / 2 };
  const zoom = (factor: number) => setCamera(zoomCamera(camera, midpoint, factor));

  return (
    <section className="card warehouse" aria-labelledby="warehouse-heading">
      <div className="card-heading map-heading">
        <div><h2 id="warehouse-heading">Depo görünümü</h2><p>Konum telemetrisi · <code>{frame}</code> koordinat çerçevesi</p></div>
        <span className="tag map-tag">TEMSİLİ 2D DEPO</span>
      </div>
      <div className="map-viewport" ref={container} data-scale={camera.scale} data-camera-x={camera.x}
        data-camera-y={camera.y} aria-label="2D depo haritası">
        {size.width > 0 && size.height > 0 && (
          <Stage width={size.width} height={size.height} onWheel={(event) => {
            event.evt.preventDefault();
            const anchor = event.target.getStage()?.getPointerPosition();
            if (anchor) setCamera(zoomCamera(camera, anchor, event.evt.deltaY < 0 ? 1.13 : 1 / 1.13));
          }}>
            <Layer>
              <Group x={camera.x} y={camera.y} scaleX={camera.scale} scaleY={camera.scale} draggable
                onDragEnd={(event) => setCamera({ ...camera, x: event.target.x(), y: event.target.y() })}>
                <Rect x={-80} y={-80} width={160} height={160} fill="#edf3f3" />
                <Floor />
                {stations.map(({ station, point }) => <StationMarker key={station.station_id} station={station}
                  {...point} scale={camera.scale} />)}
                {robots.map(({ robot, point }) => <RobotMarker key={robot.robot_id} id={robot.robot_id}
                  {...point} scale={camera.scale} selected={selected === robot.robot_id}
                  reliability={connected || robot.pose_reliability === "BLOCKED" ? robot.pose_reliability : "STALE"}
                  onSelect={() => onSelect(robot.robot_id)} />)}
              </Group>
            </Layer>
          </Stage>
        )}
        <span className="axis-label"><Crosshair size={14} /> +X sağa · +Y yukarı</span>
        {robots.length === 0 && <span className="map-notice">Doğrulanmış robot konumu bekleniyor</span>}
        <div className="map-controls" aria-label="Harita kontrolleri">
          <button type="button" title="Yakınlaştır" aria-label="Yakınlaştır" onClick={() => zoom(1.24)}><Plus size={17} /></button>
          <button type="button" title="Uzaklaştır" aria-label="Uzaklaştır" onClick={() => zoom(1 / 1.24)}><Minus size={17} /></button>
          <button type="button" title="Filoyu kadraja al" aria-label="Filoyu kadraja al" onClick={() => setCamera(null)}><Maximize size={15} /></button>
        </div>
        <span className="map-scale"><span style={{ width: Math.min(camera.scale, 90) }} />
          {camera.scale > 90 ? `${(90 / camera.scale).toFixed(2)} m` : "1 m"}</span>
      </div>
      <div className="map-footer">
        <span><i className="legend-dot live" /> Canlı poz</span><span><i className="legend-dot stale" /> Son doğrulanmış poz</span>
        <span><BatteryCharging size={14} /> İstasyon</span>
        <span className="map-note">Raflar görsel referanstır</span>
      </div>
    </section>
  );
}
