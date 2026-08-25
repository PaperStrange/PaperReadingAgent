import React from "react";

function shortText(text, maxLen = 180) {
  const s = String(text ?? "");
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen - 14) + "...[truncated]";
}

function Primitive({ value }) {
  if (value === null) return <span className="json-null">null</span>;
  if (typeof value === "string") return <span className="json-str">"{shortText(value)}"</span>;
  if (typeof value === "number") return <span className="json-num">{String(value)}</span>;
  if (typeof value === "boolean") return <span className="json-bool">{String(value)}</span>;
  return <span className="json-str">"{shortText(String(value))}"</span>;
}

function JsonNode({ name, value, depth = 0 }) {
  const isArr = Array.isArray(value);
  const isObj = value && typeof value === "object" && !isArr;

  if (!isArr && !isObj) {
    return (
      <div className="json-row" style={{ paddingLeft: `${depth * 12}px` }}>
        {name != null ? <span className="json-key">{name}: </span> : null}
        <Primitive value={value} />
      </div>
    );
  }

  const entries = isArr
    ? value.map((v, i) => [i, v])
    : Object.entries(value || {});

  return (
    <details className="json-details" open={depth < 2}>
      <summary className="json-summary" style={{ marginLeft: `${depth * 12}px` }}>
        {name != null ? <span className="json-key">{name}: </span> : null}
        <span className="json-type">{isArr ? `[${entries.length}]` : `{${entries.length}}`}</span>
      </summary>
      <div>
        {entries.map(([k, v]) => (
          <JsonNode key={`${depth}-${String(k)}`} name={String(k)} value={v} depth={depth + 1} />
        ))}
      </div>
    </details>
  );
}

export default function JsonTree({ value }) {
  return (
    <div className="json-tree">
      <JsonNode value={value} depth={0} />
    </div>
  );
}
