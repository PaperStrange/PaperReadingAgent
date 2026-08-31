"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, App, Button, Card, Col, Input, Layout, Row, Space, Steps, Typography } from "antd";
import { CheckOutlined, SaveOutlined } from "@ant-design/icons";

const { Content, Header } = Layout;

interface FanoutStep {
  order: number;
  step: string;
  role: string;
  spec: string;
  condition: string;
  executor: string;
}
interface FanoutDoc {
  version: number;
  planning_pipeline: FanoutStep[];
  sprint_close_pipeline: FanoutStep[];
}

export default function FanoutPage() {
  const { message } = App.useApp();
  const [doc, setDoc] = useState<FanoutDoc | null>(null);
  const [content, setContent] = useState("");
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const d = await fetch("/api/fanout").then((r) => r.json());
    if (d.parsed) {
      setDoc(d.parsed as FanoutDoc);
      setContent(d.content as string);
      setFeedback(d.valid ? null : { ok: false, text: `当前文件校验失败：${d.error}` });
    } else {
      setFeedback({ ok: false, text: `加载失败：${d.error}` });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      const r = await fetch("/api/fanout", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      const d = await r.json();
      setFeedback(d.ok ? { ok: true, text: "已写入 agents/fanout.json（下一轮关闭流程按新配置执行）" } : { ok: false, text: `保存失败：${d.error}` });
      if (d.ok) {
        message.success("fan-out 配置已保存");
        await load();
      }
    } finally {
      setBusy(false);
    }
  };

  const validate = () => {
    // POST = dry-run 校验（不写入），与保存（PUT 直写）语义分离（017 major 修复）
    fetch("/api/fanout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) })
      .then((r) => r.json())
      .then((d) => setFeedback({ ok: d.ok, text: d.ok ? "结构校验通过（dry-run，未写入任何文件）" : `校验失败：${d.error}` }));
  };

  const renderSteps = (title: string, steps?: FanoutStep[]) => (
    <Card title={title} style={{ height: "100%" }}>
      <Steps
        direction="vertical"
        size="small"
        current={-1}
        items={(steps ?? []).map((s) => ({
          title: `${s.order}. ${s.step} — ${s.role}`,
          description: (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              spec: {s.spec} · condition: {s.condition} · executor: {s.executor}
            </Typography.Text>
          ),
        }))}
      />
    </Card>
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          fan-out 配置（agents/fanout.json）
        </Typography.Title>
        <a href="/" style={{ fontSize: 13 }}>
          ← 看板
        </a>
        <a href="/specs" style={{ fontSize: 13 }}>
          spec 编辑
        </a>
      </Header>
      <Content style={{ padding: 24 }}>
        <Row gutter={[16, 16]} align="stretch">
          <Col xs={24} md={8}>{renderSteps("planning_pipeline（规划前置）", doc?.planning_pipeline)}</Col>
          <Col xs={24} md={8}>{renderSteps("sprint_close_pipeline（关闭三查）", doc?.sprint_close_pipeline)}</Col>
          <Col xs={24} md={8}>
            <Card
              title="JSON 编辑器（条件/顺序/执行者可调）"
              style={{ height: "100%" }}
              extra={
                <Space>
                  <Button size="small" icon={<CheckOutlined />} loading={busy} onClick={validate}>
                    校验
                  </Button>
                  <Button size="small" type="primary" icon={<SaveOutlined />} loading={busy} onClick={() => void save()}>
                    保存（直写文件）
                  </Button>
                </Space>
              }
            >
              <Space direction="vertical" style={{ width: "100%" }} size="middle">
                {feedback && <Alert type={feedback.ok ? "success" : "error"} message={feedback.text} showIcon />}
                <Input.TextArea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  spellCheck={false}
                  style={{ height: "calc(100vh - 320px)", fontFamily: "monospace", fontSize: 12 }}
                />
              </Space>
            </Card>
          </Col>
        </Row>
        <Typography.Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 16 }}>
          保存后下一轮关闭流程（scope→doc-audit→code-review→lessons→workspace-check）与规划前置调研按此配置执行；写入仅绑定 127.0.0.1 回环（与 spec 编辑同约定）。
        </Typography.Text>
      </Content>
    </Layout>
  );
}
