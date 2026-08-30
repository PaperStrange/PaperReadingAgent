"use client";

import { useEffect, useState } from "react";
import { App, Alert, Button, Input, Layout, List, Space, Typography } from "antd";
import { CheckOutlined, SaveOutlined } from "@ant-design/icons";

const { Content, Header, Sider } = Layout;

interface Spec {
  name: string;
  version: string;
}

export default function SpecsPage() {
  const { message } = App.useApp();
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/specs")
      .then((r) => r.json())
      .then((d) => setSpecs(d.specs ?? []));
  }, []);

  const open = async (name: string) => {
    setCurrent(name);
    setFeedback(null);
    const d = await fetch(`/api/specs/${encodeURIComponent(name)}`).then((r) => r.json());
    setContent(d.content ?? "");
  };

  const save = async () => {
    if (!current) return;
    setBusy(true);
    try {
      const r = await fetch("/api/specs", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: current, content }),
      });
      const d = await r.json();
      setFeedback(d.ok ? { ok: true, text: `已保存 ${current}` } : { ok: false, text: `保存失败：${d.error}` });
      if (d.ok) message.success("已写入 agents/functions/（文件真相源）");
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    if (!current) return;
    setBusy(true);
    setFeedback(null);
    try {
      const r = await fetch("/api/specs/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: current, content }),
      });
      const d = await r.json();
      setFeedback({ ok: d.ok, text: d.message });
    } finally {
      setBusy(false);
    }
  };

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
          职能 spec 编辑（直写 agents/functions/）
        </Typography.Title>
        <a href="/" style={{ fontSize: 13 }}>
          ← 看板
        </a>
      </Header>
      <Layout>
        <Sider width={230} theme="light" style={{ borderRight: "1px solid #f0f0f0", padding: 12 }}>
          <List
            size="small"
            dataSource={specs}
            renderItem={(s) => (
              <List.Item
                onClick={() => void open(s.name)}
                style={{
                  cursor: "pointer",
                  padding: "8px 12px",
                  borderRadius: 6,
                  background: current === s.name ? "#e6f4ff" : undefined,
                }}
              >
                <List.Item.Meta title={s.name} description={`v${s.version}`} />
              </List.Item>
            )}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          {current ? (
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Space wrap>
                <Button type="primary" icon={<SaveOutlined />} loading={busy} onClick={() => void save()}>
                  保存（直写文件）
                </Button>
                <Button icon={<CheckOutlined />} loading={busy} onClick={() => void validate()}>
                  validate-spec 校验
                </Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  source 块（skill URL/ref/sha256/fallback）直接编辑下方 frontmatter
                </Typography.Text>
              </Space>
              {feedback && (
                <Alert
                  type={feedback.ok ? "success" : "error"}
                  message={feedback.text}
                  showIcon
                />
              )}
              <Input.TextArea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                spellCheck={false}
                autoSize={false}
                style={{ height: "calc(100vh - 260px)", fontFamily: "monospace", fontSize: 12 }}
              />
            </Space>
          ) : (
            <Typography.Text type="secondary">从左侧选择要编辑的职能 spec</Typography.Text>
          )}
        </Content>
      </Layout>
    </Layout>
  );
}
