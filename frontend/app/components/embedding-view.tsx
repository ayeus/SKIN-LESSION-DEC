"use client";
import { useId, useMemo, useState } from "react";

// Orthographic rotation preserves geometry with one common display scale.
export function rotatePoint(point: number[], yaw: number, pitch: number) {
  const [x, y, z = 0] = point;
  const a = (yaw * Math.PI) / 180;
  const b = (pitch * Math.PI) / 180;
  const u = x * Math.cos(a) + z * Math.sin(a);
  const depth = -x * Math.sin(a) + z * Math.cos(a);
  return [
    u,
    y * Math.cos(b) - depth * Math.sin(b),
    y * Math.sin(b) + depth * Math.cos(b),
  ];
}

type Props = { coordinates: number[][]; method: string; variance?: number[] };
export default function EmbeddingView({
  coordinates,
  method,
  variance,
}: Props) {
  const title = useId();
  const [yaw, setYaw] = useState(25);
  const [pitch, setPitch] = useState(15);
  const [selected, setSelected] = useState(1);
  const dimensions = coordinates[0]?.length;
  const valid =
    coordinates.length > 0 &&
    [2, 3].includes(dimensions) &&
    coordinates.every(
      (v) => v.length === dimensions && v.every(Number.isFinite),
    );
  const geometry = useMemo(() => {
    if (!valid) return null;
    const center = Array.from(
      { length: dimensions },
      (_, j) =>
        coordinates.reduce((sum, v) => sum + v[j], 0) / coordinates.length,
    );
    const centered = coordinates.map((v) => v.map((x, j) => x - center[j]));
    const radius = centered.reduce(
      (max, v) => Math.max(max, Math.hypot(...v)),
      Number.EPSILON,
    );
    const indices = Array.from(
      { length: Math.min(2000, coordinates.length) },
      (_, i) =>
        Math.floor(
          (i * coordinates.length) / Math.min(2000, coordinates.length),
        ),
    );
    const chosen = Math.min(Math.max(1, selected), coordinates.length) - 1;
    if (!indices.includes(chosen)) indices.push(chosen);
    const project = (v: number[]) =>
      rotatePoint(v, dimensions === 3 ? yaw : 0, dimensions === 3 ? pitch : 0);
    return {
      chosen,
      radius,
      project,
      points: indices
        .map((index) => ({ index, point: project(centered[index]) }))
        .sort((a, b) => a.point[2] - b.point[2]),
    };
  }, [coordinates, dimensions, valid, yaw, pitch, selected]);
  if (!geometry)
    return (
      <p className="notice">
        Embedding coordinates are missing or invalid; no projection is
        displayed.
      </p>
    );
  const scale = 130 / geometry.radius;
  const axes = Array.from({ length: dimensions }, (_, j) =>
    geometry.project(
      Array.from({ length: dimensions }, (_, k) =>
        j === k ? geometry.radius : 0,
      ),
    ),
  );
  return (
    <section aria-label="Embedding exploration">
      <h3>
        {method.toUpperCase()}: {dimensions}-dimensional exploration
      </h3>
      <p>
        Coordinates from {coordinates.length.toLocaleString()} input rows. One
        common scale preserves relative distances before projection. Row numbers
        refer to input order, not patient identifiers.
      </p>
      {dimensions === 3 && (
        <div className="form-grid">
          <label>
            Horizontal rotation: {yaw}°
            <input
              type="range"
              min="-180"
              max="180"
              value={yaw}
              onChange={(e) => setYaw(Number(e.target.value))}
            />
          </label>
          <label>
            Vertical rotation: {pitch}°
            <input
              type="range"
              min="-90"
              max="90"
              value={pitch}
              onChange={(e) => setPitch(Number(e.target.value))}
            />
          </label>
          <button
            type="button"
            onClick={() => {
              setYaw(25);
              setPitch(15);
            }}
          >
            Reset view
          </button>
        </div>
      )}
      <svg
        viewBox="0 0 520 340"
        role="img"
        aria-labelledby={title}
        style={{
          width: "100%",
          maxHeight: 440,
          background: "#f2f8f7",
          borderRadius: 12,
        }}
      >
        <title id={title}>
          Projection of actual {method.toUpperCase()} coordinates.{" "}
          {dimensions === 3
            ? `Rotation ${yaw} by ${pitch} degrees.`
            : "Two-dimensional view."}
        </title>
        {axes.map((v, j) => (
          <g key={j}>
            <line
              x1="260"
              y1="170"
              x2={260 + v[0] * scale}
              y2={170 - v[1] * scale}
              stroke="#667d80"
            />
            <text
              x={260 + v[0] * scale + 5}
              y={170 - v[1] * scale - 5}
              fill="#385257"
              fontSize="12"
            >
              Component {j + 1}
            </text>
          </g>
        ))}
        {geometry.points.map(({ index, point }) => (
          <circle
            key={index}
            data-row={index + 1}
            cx={260 + point[0] * scale}
            cy={170 - point[1] * scale}
            r={index === geometry.chosen ? 5 : 2.5}
            fill={index === geometry.chosen ? "#ae421b" : "#087f83"}
            opacity={index === geometry.chosen ? 1 : 0.65}
          >
            <title>
              Input row {index + 1}:{" "}
              {coordinates[index].map((v) => v.toPrecision(5)).join(", ")}
            </title>
          </circle>
        ))}
      </svg>
      {coordinates.length > 2000 && (
        <p className="notice">
          Display shows 2,000 evenly spaced input rows, plus the selected row if
          needed. All coordinates remain in the downloadable result. This
          display subset is not a statistical sample.
        </p>
      )}
      <label>
        Inspect input row
        <input
          type="number"
          min="1"
          max={coordinates.length}
          step="1"
          value={selected}
          onChange={(e) =>
            setSelected(
              Math.min(
                coordinates.length,
                Math.max(1, Math.trunc(Number(e.target.value)) || 1),
              ),
            )
          }
        />
      </label>
      <p aria-live="polite">
        Input row {geometry.chosen + 1}:{" "}
        {coordinates[geometry.chosen]
          .map((v, j) => `Component ${j + 1}: ${v.toPrecision(6)}`)
          .join("; ")}
      </p>
      {variance && (
        <div className="table-wrap">
          <table>
            <caption>
              PCA explained variance on this exploratory dataset
            </caption>
            <thead>
              <tr>
                <th>Component</th>
                <th>Explained variance</th>
              </tr>
            </thead>
            <tbody>
              {variance.map((v, j) => (
                <tr key={j}>
                  <td>{j + 1}</td>
                  <td>{(v * 100).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="notice">
        Projected overlap or separation does not prove clinical validity.
        Rotation changes the view, not the underlying coordinates. t-SNE axes
        have no clinical units and its global distances require caution.
      </p>
    </section>
  );
}
