"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Input,
  Layout,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import DonutChart from "./components/DonutChart";

const { Content, Header } = Layout;

const STATUS_COLOR_HEX: Record<string, string> = {
  succeeded: "#52c41a",
  running: "#1677ff",
  failed: "#ff4d4f",
  queued: "#d9d9d9",
  cancelled: "#faad14",
};

const ROLE_COLORS = ["#1677ff", "#52c41a", "#faad14", "#722ed1", "#13c2c2", "#eb2f96"];

interface RunRow {
  run_id: string;
  task_id: string;
  role: string;
  spec_source: string;
  status: string;
  started_at: string | null;
  output_chars: number;
  cost: { total?: number | null; estimated?: boolean; pending_price?: boolean };
}

interface Agg {
  total: number;
  by_status: Record<string, number>;
  by_role: Record<string, number>;
  cost_total: number;
  pending_price: number;
}

const fmt = (iso: string | null) => (iso ? iso.replace("T", " ").slice(0, 19) : "—");
const costText = (c: RunRow["cost"]) =>
  typeof c?.total === "number"
    ? `$${c.total.toFixed(6)}${c.estimated ? "~" : ""}`
    : c?.pending_price
      ? "待价表"
      : "—";

const STATUS_COLOR: Record<string, string> = {
  succeeded: "success",
  failed: "error",
  running: "processing",
  queued: "default",
  cancelled: "warning",
};

export default function Home() {
  const [agg, setAgg] = useState<Agg | null>(null);
  const [rows, setRows] = useState<RunRow[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [role, setRole] = useState<string | undefined>();
  const [status, setStatus] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (search = q, r = role, s = status) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set("q", search);
      if (r) params.set("role", r);
      if (s) params.set("status", s);
      const [a, l] = await Promise.all([
        fetch("/api/aggregates").then((x) => x.json()),
        fetch(`/api/runs?${params.toString()}`).then((x) => x.json()),
      ]);
      setAgg(a);
      setRows(l.rows as RunRow[]);
      setTotal(l.total);
    } finally {
      setLoading(false);
    }
  }, [q, role, status]);

  useEffect(() => {
    const t = setTimeout(() => void load(), 200);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          AgentOps 看板
        </Typography.Title>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>
          刷新
        </Button>
      </Header>
      <Content style={{ padding: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} md={6}>
            <Card styles={{ body: { minHeight: 210, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" } }}>
              <Statistic title="总 Run 数" value={agg?.total ?? 0} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card
              title="状态分布"
              styles={{ body: { minHeight: 210, display: "flex", alignItems: "center", justifyContent: "center" } }}
            >
              {agg ? (
                <DonutChart
                  center={String(agg.total)}
                  data={Object.entries(agg.by_status).map(([k, v]) => ({
                    label: k,
                    value: v,
                    color: STATUS_COLOR_HEX[k] ?? "#d9d9d9",
                  }))}
                />
              ) : (
                <Typography.Text type="secondary">—</Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card
              title="职能分布"
              styles={{ body: { minHeight: 210, display: "flex", alignItems: "center", justifyContent: "center" } }}
            >
              {agg ? (
                <DonutChart
                  center={String(agg.total)}
                  data={Object.entries(agg.by_role).map(([k, v], i) => ({
                    label: k,
                    value: v,
                    color: ROLE_COLORS[i % ROLE_COLORS.length],
                  }))}
                />
              ) : (
                <Typography.Text type="secondary">—</Typography.Text>
              )}
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card styles={{ body: { minHeight: 210, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" } }}>
              <Statistic
                title="累计成本（自报+估算）"
                value={agg ? `$${agg.cost_total.toFixed(6)}` : "—"}
                valueStyle={{ fontSize: 16 }}
              />
              {agg && agg.pending_price > 0 && (
                <Typography.Text type="warning" style={{ fontSize: 12 }}>
                  {agg.pending_price} 条待价表（精确账单以服务商后台为准）
                </Typography.Text>
              )}
            </Card>
          </Col>
        </Row>

        <Card style={{ marginTop: 16 }}>
          <Space wrap style={{ marginBottom: 16 }}>
            <Input.Search
              allowClear
              placeholder="全文检索（role/task/spec/报告内容）"
              style={{ width: 360 }}
              onSearch={(v) => setQ(v)}
            />
            <Select
              allowClear
              placeholder="全部职能"
              style={{ width: 180 }}
              value={role}
              onChange={setRole}
              options={(agg ? Object.keys(agg.by_role) : []).map((r) => ({ value: r, label: r }))}
            />
            <Select
              allowClear
              placeholder="全部状态"
              style={{ width: 140 }}
              value={status}
              onChange={setStatus}
              options={(agg ? Object.keys(agg.by_status) : []).map((s) => ({ value: s, label: s }))}
            />
          </Space>
          <Table<RunRow>
            rowKey="run_id"
            loading={loading}
            size="small"
            dataSource={rows}
            pagination={{ pageSize: 20, total, showTotal: (t) => `共 ${t} 条` }}
            columns={[
              { title: "Run", dataIndex: "run_id", width: 260, render: (v) => <Typography.Text code>{v}</Typography.Text> },
              { title: "任务", dataIndex: "task_id", width: 160, render: (v) => v || "—" },
              { title: "职能", dataIndex: "role", width: 150 },
              { title: "spec", dataIndex: "spec_source", width: 220, render: (v) => <Typography.Text code>{v}</Typography.Text> },
              {
                title: "状态",
                dataIndex: "status",
                width: 110,
                render: (v: string) => <Tag color={STATUS_COLOR[v] ?? "default"}>{v}</Tag>,
              },
              { title: "开始", dataIndex: "started_at", width: 170, render: (v) => <Typography.Text code>{fmt(v)}</Typography.Text> },
              { title: "成本", dataIndex: "cost", width: 120, render: (v) => costText(v as RunRow["cost"]) },
            ]}
          />
        </Card>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          数据源：agents/runtime/registry.json（文件真相源）+ SQLite 派生索引
        </Typography.Text>
      </Content>
    </Layout>
  );
}
