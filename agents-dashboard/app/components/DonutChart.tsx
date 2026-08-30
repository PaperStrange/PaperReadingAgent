"use client";

interface DonutDatum {
  label: string;
  value: number;
  color: string;
}

export default function DonutChart({
  data,
  center,
  size = 110,
  thickness = 14,
}: {
  data: DonutDatum[];
  center: string;
  size?: number;
  thickness?: number;
}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  const segs = data
    .filter((d) => d.value > 0)
    .map((d) => {
      const frac = d.value / total;
      const seg = (
        <circle
          key={d.label}
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={d.color}
          strokeWidth={thickness}
          strokeDasharray={`${frac * c} ${c}`}
          strokeDashoffset={-offset * c}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      );
      offset += frac;
      return seg;
    });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f0f0f0" strokeWidth={thickness} />
          {segs}
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.2 }}>{center}</span>
          <span style={{ fontSize: 11, color: "rgba(0,0,0,0.45)" }}>合计</span>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2, width: "100%" }}>
        {data
          .filter((d) => d.value > 0)
          .map((d) => (
            <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: d.color,
                  flexShrink: 0,
                }}
              />
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {d.label}
              </span>
              <span style={{ color: "rgba(0,0,0,0.65)", fontVariantNumeric: "tabular-nums" }}>{d.value}</span>
            </div>
          ))}
      </div>
    </div>
  );
}
