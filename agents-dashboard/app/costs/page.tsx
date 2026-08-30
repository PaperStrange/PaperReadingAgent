"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Card,
  Col,
  Layout,
  Progress,
  Row,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import Link from "next/link";

const { Content, Header } = Layout;

interface Agg {
  total: number;
  cost_total: number;
  pending_price: number;
  estimated_count: number;
  fx_usd_cny: number;
  by_model: { model: string; runs: number; cost: number; pending: number }[];
}

interface RunCtx {
  run_id: string;
  role: string;
  context: { input_tokens: number; max_context: number; ratio: number };
  usage: { input_tokens: number; output_tokens: number };
  model: string;
}

export default function CostsPage() {
  const [agg, setAgg] = useState<Agg | null>(null);
  const [ctxRows, setCtxRows] = useState<RunCtx[]>([]);

  useEffect(() => {
    Promise.all([
      fetch("/api/aggregates").then((r) => r.json()),
      fetch("/api/runs?limit=50").then((r) => r.json()),
    ]).then(([a, l]) => {
      setAgg(a);
      setCtxRows(l.rows as RunCtx[]);
    });
  }, []);

  const fmtCost = (v: number) => `¥${v.toFixed(6)}`;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          成本 / 上下文
        </Typography.Title>
        <Link href="/" style={{ fontSize: 13 }}>← 看板</Link>
        <Link href="/specs" style={{ fontSize: 13 }}>spec 编辑</Link>
      </Header>
      <Content style={{ padding: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} md={6}>
            <Card>
              <Statistic title="累计成本（CNY，自报+估算）" value={agg ? fmtCost(agg.cost_total) : "—"} valueStyle={{ fontSize: 18 }} />
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                汇率 fx_usd_cny = {agg?.fx_usd_cny ?? "—"}（改 `agents/runtime/prices.json` meta）
              </Typography.Text>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic title="待价表条数（pending_price）" value={agg?.pending_price ?? 0} valueStyle={{ fontSize: 18 }} />
              <Typography.Text type="warning" style={{ fontSize: 12 }}>
                缺单价的模型不计入成本
              </Typography.Text>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic title="估算条数（chars/4 兜底）" value={agg?.estimated_count ?? 0} valueStyle={{ fontSize: 18 }} />
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                无 token 上报时的近似口径
              </Typography.Text>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic title="总 Run 数" value={agg?.total ?? 0} valueStyle={{ fontSize: 18 }} />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={14}>
            <Card title="按模型成本">
              <Table
                rowKey="model"
                size="small"
                dataSource={agg?.by_model ?? []}
                pagination={false}
                columns={[
                  { title: "模型", dataIndex: "model", render: (v) => <Typography.Text code>{v}</Typography.Text> },
                  { title: "Run 数", dataIndex: "runs", width: 90 },
                  { title: "成本（¥）", dataIndex: "cost", width: 160, render: (v: number) => fmtCost(v) },
                  {
                    title: "待价表",
                    dataIndex: "pending",
                    width: 110,
                    render: (v: number) => (v > 0 ? <Tag color="warning">{v} 条</Tag> : <Tag>0</Tag>),
                  },
                ]}
              />
            </Card>
          </Col>
          <Col xs={24} md={10}>
            <Card title="上下文占用（最近 50 条，input/max_context）">
              <div style={{ maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
                {ctxRows
                  .filter((r) => r.context?.max_context > 0)
                  .slice(0, 20)
                  .map((r) => {
                    const pct = Math.min(100, Math.round((r.context.ratio || 0) * 100));
                    return (
                      <div key={r.run_id}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 260 }}>
                            {r.role} · <Typography.Text code>{r.run_id.slice(-16)}</Typography.Text>
                          </span>
                          <span>
                            {r.context.input_tokens}/{r.context.max_context}（{pct}%）
                          </span>
                        </div>
                        <Progress
                          percent={pct}
                          size="small"
                          status={pct >= 80 ? "exception" : pct >= 50 ? "active" : "normal"}
                        />
                      </div>
                    );
                  })}
                {ctxRows.filter((r) => r.context?.max_context > 0).length === 0 && (
                  <Typography.Text type="secondary">暂无上下文数据（finish 时未自报 context 字段）</Typography.Text>
                )}
              </div>
            </Card>
          </Col>
        </Row>

        <Alert
          style={{ marginTop: 16 }}
          type="info"
          showIcon
          message="口径说明"
          description="成本 = usage × 价表单价（USD/token）× fx_usd_cny（CNY）；无 usage 时按 chars/4 兜底并标 ~；pending_price 表示该模型无单价（在 agents/runtime/prices.json manual 段填入即可计入）。精确账单以服务商后台为准。"
        />
      </Content>
    </Layout>
  );
}
