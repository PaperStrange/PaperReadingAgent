"use client";

import { useEffect, useState } from "react";
import { Card, Descriptions, Layout, Tag, Typography } from "antd";
import Link from "next/link";
import { useParams } from "next/navigation";

const { Content, Header } = Layout;

interface RunDetail {
  run_id: string;
  task_id: string;
  role: string;
  spec_source: string;
  model: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  input_chars: number;
  output_chars: number;
  usage: Record<string, number>;
  context: Record<string, number>;
  cost: Record<string, unknown>;
  result_files: string[];
  report_body: string;
}

const STATUS_COLOR: Record<string, string> = {
  succeeded: "success",
  failed: "error",
  running: "processing",
  queued: "default",
  cancelled: "warning",
};

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/runs/${encodeURIComponent(params.id)}`)
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) setError(d.error ?? "not found");
        else setRun(d);
      })
      .catch((e) => setError(String(e)));
  }, [params.id]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header style={{ display: "flex", alignItems: "center", gap: 24, background: "#fff", borderBottom: "1px solid #f0f0f0" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          报告浏览（memory 存档）
        </Typography.Title>
        <Link href="/" style={{ fontSize: 13 }}>← 看板</Link>
      </Header>
      <Content style={{ padding: 24, maxWidth: 1100, margin: "0 auto", width: "100%" }}>
        {error && <Typography.Text type="danger">{error}</Typography.Text>}
        {run && (
          <>
            <Card title={<Typography.Text code>{run.run_id}</Typography.Text>} style={{ marginBottom: 16 }}>
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="职能">{run.role}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={STATUS_COLOR[run.status] ?? "default"}>{run.status}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="任务">{run.task_id || "—"}</Descriptions.Item>
                <Descriptions.Item label="spec">{run.spec_source}</Descriptions.Item>
                <Descriptions.Item label="模型">{run.model || "—"}</Descriptions.Item>
                <Descriptions.Item label="开始 / 结束">
                  {run.started_at ?? "—"} → {run.ended_at ?? "—"}
                </Descriptions.Item>
                <Descriptions.Item label="usage（in/out/cache_r/cache_w）">
                  {run.usage.input_tokens ?? 0}/{run.usage.output_tokens ?? 0}/{run.usage.cache_read_tokens ?? 0}/{run.usage.cache_write_tokens ?? 0}
                </Descriptions.Item>
                <Descriptions.Item label="上下文（input/max/ratio）">
                  {run.context.input_tokens ?? 0}/{run.context.max_context ?? 0}（{run.context.ratio ?? 0}）
                </Descriptions.Item>
                <Descriptions.Item label="成本（CNY，自报+估算）">
                  {typeof run.cost.total === "number" ? `¥${run.cost.total.toFixed(6)}` : "待价表"}
                  {run.cost.estimated ? " ~" : ""}
                </Descriptions.Item>
                <Descriptions.Item label="结果文件">{run.result_files?.join(", ") || "—"}</Descriptions.Item>
              </Descriptions>
            </Card>
            <Card title="报告全文（agents/runs/ 存档）">
              {run.report_body ? (
                <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, fontFamily: "monospace", margin: 0 }}>
                  {run.report_body}
                </pre>
              ) : (
                <Typography.Text type="secondary">无报告存档</Typography.Text>
              )}
            </Card>
          </>
        )}
      </Content>
    </Layout>
  );
}
