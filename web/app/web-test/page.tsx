"use client"

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
    Play, Square, Globe, Terminal, Activity, RefreshCw, FileText, CheckCircle2,
    XCircle, AlertCircle, ClipboardList, Loader2, Upload, ArrowLeft
} from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';

interface TestSpec {
    id: string;
    title: string;
    bundle_path: string;
}

interface StepRecord {
    i: number;
    ts: string;
    action: { name: string; args?: Record<string, any> };
    status: string;
    error?: string;
}

interface Verdict {
    status: string;
    summary: string;
    assertions: Array<{
        id: string;
        status: string;
        why: string;
    }>;
}

export default function WebTestPage() {
    // Mode: "direct", "spec", or "prd"
    const [mode, setMode] = useState<"direct" | "spec" | "prd">("direct");

    // PRD Mode State
    const [prdContent, setPrdContent] = useState("");
    const [prdFile, setPrdFile] = useState<File | null>(null);

    // Direct Mode State
    const [url, setUrl] = useState("https://www.baidu.com");
    const [instruction, setInstruction] = useState("搜索 AI 技术并浏览结果");

    // Spec Mode State
    const [specs, setSpecs] = useState<TestSpec[]>([]);
    const [selectedSpec, setSelectedSpec] = useState<string>("");
    const [loadingSpecs, setLoadingSpecs] = useState(false);

    // Run State
    const [runId, setRunId] = useState<string | null>(null);
    const [status, setStatus] = useState("idle");
    const [logs, setLogs] = useState<string[]>([]);
    const [steps, setSteps] = useState<StepRecord[]>([]);
    const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
    const [verdict, setVerdict] = useState<Verdict | null>(null);

    // WebSocket
    const wsRef = useRef<WebSocket | null>(null);

    // Load Specs on mount
    useEffect(() => {
        loadSpecs();
    }, []);

    const loadSpecs = async () => {
        setLoadingSpecs(true);
        try {
            // Fetch bundles that have device_type: web
            const res = await axios.get("/api/bundles");
            const webSpecs = res.data.filter((b: any) =>
                b.preconditions?.custom?.device_type === "web" ||
                b.bundle_path?.includes("web")
            );
            setSpecs(webSpecs.map((b: any) => ({
                id: b.id,
                title: b.title || b.id,
                bundle_path: b.bundle_path
            })));
        } catch (e) {
            console.error("Failed to load specs:", e);
        } finally {
            setLoadingSpecs(false);
        }
    };

    const startDirectTest = async () => {
        try {
            setStatus("starting");
            setLogs([]);
            setSteps([]);
            setScreenshotUrl(null);
            setVerdict(null);

            const fullInstruction = `Open ${url} and ${instruction}`;

            const res = await axios.post("/api/runs/direct", {
                device_id: "web",
                instruction: fullInstruction
            });

            const newRunId = res.data.run_id;
            setRunId(newRunId);
            setStatus("running");
            toast.success("Web Agent 任务已启动");

            connectWebSocket(newRunId);

        } catch (e: any) {
            toast.error("启动失败: " + e.message);
            setStatus("idle");
        }
    };

    const startSpecTest = async () => {
        if (!selectedSpec) {
            toast.warning("请先选择一个测试规格");
            return;
        }

        try {
            setStatus("starting");
            setLogs([]);
            setSteps([]);
            setScreenshotUrl(null);
            setVerdict(null);

            const spec = specs.find(s => s.id === selectedSpec);
            if (!spec) return;

            const res = await axios.post("/api/runs/spec", {
                bundle_path: spec.bundle_path,
                device_id: "web"
            });

            const newRunId = res.data.run_id;
            setRunId(newRunId);
            setStatus("running");
            toast.success(`开始执行规格: ${spec.title}`);

            connectWebSocket(newRunId);

        } catch (e: any) {
            toast.error("启动失败: " + e.message);
            setStatus("idle");
        }
    };

    const startPrdTest = async () => {
        if (!prdContent && !prdFile) {
            toast.warning("请输入 PRD 内容或上传文件");
            return;
        }

        try {
            setStatus("starting");
            setLogs([]);
            setSteps([]);
            setScreenshotUrl(null);
            setVerdict(null);

            let docId = "";

            if (prdFile) {
                // Upload file first
                const formData = new FormData();
                formData.append("file", prdFile);
                const uploadRes = await axios.post("/api/docs/upload", formData);
                docId = uploadRes.data.doc_id;
            } else {
                // Create temp doc from content
                const saveRes = await axios.post("/api/docs/save", {
                    content: prdContent,
                    filename: `web_prd_${Date.now()}.md`
                });
                docId = saveRes.data.doc_id;
            }

            // Create run with doc_id and web device
            const res = await axios.post("/api/runs", {
                doc_id: docId,
                device_id: "web",
                config: {}
            });

            const newRunId = res.data.run_id;
            setRunId(newRunId);
            setStatus("running");
            toast.success("PRD 文档已提交，正在生成测试...");

            connectWebSocket(newRunId);

        } catch (e: any) {
            toast.error("启动失败: " + e.message);
            setStatus("idle");
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setPrdFile(file);
            setPrdContent(""); // Clear text if file selected
            toast.info(`已选择文件: ${file.name}`);
        }
    };

    const stopTest = async () => {
        if (!runId) return;
        try {
            await axios.post(`/api/runs/${runId}/stop`);
            toast.info("已请求停止任务");
        } catch (e) {
            console.error(e);
        }
    };

    const connectWebSocket = (id: string) => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/runs/${id}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WS Connected");
            addLog("System: Connected to Agent Stream");
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "log") {
                addLog(msg.content);
            } else if (msg.type === "step") {
                setSteps(prev => [...prev, msg.data]);
                addLog(`执行步骤: ${msg.data?.action?.name || 'Unknown'}`);
            } else if (msg.type === "status") {
                setStatus(msg.status);
                if (msg.status === "done" || msg.status === "failed" || msg.status === "stopped") {
                    addLog(`>>> WebSocket 已关闭`);
                    // Load verdict if available
                    loadVerdict(id);
                }
            } else if (msg.type === "live_update") {
                setScreenshotUrl(msg.url);
            }
        };

        ws.onclose = () => {
            console.log("WS Closed");
        };
    };

    const loadVerdict = async (id: string) => {
        try {
            const res = await axios.get(`/api/runs/${id}/report`);
            if (res.data) {
                setVerdict(res.data);
            }
        } catch (e) {
            // No verdict available (might be direct run without assertions)
        }
    };

    const addLog = (msg: string) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    // Cleanup
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    const getVerdictIcon = (stat: string) => {
        if (stat === "PASS") return <CheckCircle2 className="h-5 w-5 text-green-500" />;
        if (stat === "FAIL") return <XCircle className="h-5 w-5 text-red-500" />;
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    };

    return (
        <div className="container mx-auto py-6 px-4 h-[calc(100vh-64px)] flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <Link href="/">
                        <Button variant="ghost" size="icon" className="rounded-full">
                            <ArrowLeft className="h-6 w-6" />
                        </Button>
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold flex items-center gap-2">
                            <Globe className="h-8 w-8 text-blue-500" />
                            Web 测试
                        </h1>
                        <p className="text-muted-foreground">基于 GLM-4V 的网页自动化测试控制台</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Badge variant={status === "running" ? "default" : "secondary"} className="text-base px-3 py-1">
                        {status === "running" ? "运行中" : status === "idle" ? "就绪" : status}
                    </Badge>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
                {/* Left: Controls & Logs */}
                <div className="flex flex-col gap-6 lg:col-span-1 h-full overflow-hidden">
                    <Card>
                        <CardHeader>
                            <CardTitle>任务配置</CardTitle>
                            <CardDescription>选择模式：快捷指令 或 完整规格</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Tabs value={mode} onValueChange={(v) => setMode(v as "direct" | "spec" | "prd")}>
                                <TabsList className="grid w-full grid-cols-3">
                                    <TabsTrigger value="direct">快捷指令</TabsTrigger>
                                    <TabsTrigger value="spec">测试规格</TabsTrigger>
                                    <TabsTrigger value="prd">PRD文档</TabsTrigger>
                                </TabsList>

                                <TabsContent value="direct" className="space-y-4 mt-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">目标 URL</label>
                                        <Input
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                            placeholder="https://example.com"
                                            disabled={status === "running"}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">测试指令</label>
                                        <Input
                                            value={instruction}
                                            onChange={(e) => setInstruction(e.target.value)}
                                            placeholder="例如: 点击登录按钮并输入账号..."
                                            disabled={status === "running"}
                                        />
                                    </div>
                                </TabsContent>

                                <TabsContent value="spec" className="space-y-4 mt-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium flex items-center gap-2">
                                            <ClipboardList className="h-4 w-4" />
                                            选择测试规格
                                        </label>
                                        <Select value={selectedSpec} onValueChange={setSelectedSpec} disabled={status === "running"}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="选择一个 Web 测试规格..." />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {specs.length === 0 && (
                                                    <SelectItem value="none" disabled>暂无可用的 Web 规格</SelectItem>
                                                )}
                                                {specs.map(spec => (
                                                    <SelectItem key={spec.id} value={spec.id}>
                                                        {spec.title}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <Button variant="ghost" size="sm" onClick={loadSpecs} disabled={loadingSpecs}>
                                            <RefreshCw className={`h-4 w-4 mr-2 ${loadingSpecs ? 'animate-spin' : ''}`} />
                                            刷新列表
                                        </Button>
                                    </div>
                                </TabsContent>

                                <TabsContent value="prd" className="space-y-4 mt-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium flex items-center gap-2">
                                            <FileText className="h-4 w-4" />
                                            PRD 文档内容
                                        </label>
                                        <Textarea
                                            value={prdContent}
                                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
                                                setPrdContent(e.target.value);
                                                setPrdFile(null);
                                            }}
                                            placeholder="粘贴 PRD 内容，或描述您想要测试的功能..."
                                            disabled={status === "running" || !!prdFile}
                                            className="min-h-[120px]"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium">或上传文件</label>
                                        <div className="flex gap-2 items-center">
                                            <Input
                                                type="file"
                                                accept=".md,.txt,.docx"
                                                onChange={handleFileChange}
                                                disabled={status === "running"}
                                                className="flex-1"
                                            />
                                            {prdFile && (
                                                <Badge variant="secondary">{prdFile.name}</Badge>
                                            )}
                                        </div>
                                    </div>
                                </TabsContent>
                            </Tabs>

                            <div className="pt-2 flex gap-3">
                                {status !== "running" ? (
                                    <Button
                                        className="w-full gap-2"
                                        onClick={mode === "direct" ? startDirectTest : mode === "spec" ? startSpecTest : startPrdTest}
                                    >
                                        <Play className="h-4 w-4" />
                                        {mode === "direct" ? "启动 Web Agent" : mode === "spec" ? "执行测试规格" : "从 PRD 生成测试"}
                                    </Button>
                                ) : (
                                    <Button variant="destructive" className="w-full gap-2" onClick={stopTest}>
                                        <Square className="h-4 w-4" /> 停止任务
                                    </Button>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Verdict Panel (if available) */}
                    {verdict && (
                        <Card className="border-l-4 border-l-green-500">
                            <CardHeader className="py-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    {getVerdictIcon(verdict.status)}
                                    判定结果: {verdict.status}
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="text-sm space-y-2">
                                <p>{verdict.summary}</p>
                                {verdict.assertions.length > 0 && (
                                    <div className="space-y-1">
                                        {verdict.assertions.map((a, i) => (
                                            <div key={i} className="flex items-center gap-2 text-xs">
                                                {a.status === "PASS" ? (
                                                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                                                ) : (
                                                    <XCircle className="h-3 w-3 text-red-500" />
                                                )}
                                                <span>{a.id}: {a.why}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    <Card className="flex-1 min-h-0 flex flex-col">
                        <CardHeader className="py-4 border-b">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Terminal className="h-4 w-4" />
                                运行日志
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 overflow-auto p-0 font-mono text-xs bg-slate-950 text-slate-50">
                            <div className="p-4 space-y-1">
                                {logs.length === 0 && <span className="text-slate-500">等待任务启动...</span>}
                                {logs.map((log, i) => (
                                    <div key={i} className="break-all whitespace-pre-wrap">{log}</div>
                                ))}
                                {/* Auto scroll anchor */}
                                <div ref={(el) => el?.scrollIntoView({ behavior: "smooth" })} />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Visual Preview */}
                <Card className="lg:col-span-2 flex flex-col h-full overflow-hidden border-blue-500/20 shadow-lg">
                    <CardHeader className="py-4 border-b bg-muted/30">
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Activity className="h-4 w-4 text-blue-500" />
                                实时画面预览
                            </CardTitle>
                            {screenshotUrl && (
                                <Badge variant="outline" className="font-mono text-xs">
                                    Source: Live
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent className="flex-1 p-0 relative bg-slate-100 dark:bg-slate-900 flex items-center justify-center overflow-hidden">
                        {screenshotUrl ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                                src={screenshotUrl}
                                alt="Live View"
                                className="max-w-full max-h-full object-contain shadow-2xl"
                            />
                        ) : (
                            <div className="text-center text-muted-foreground">
                                <Globe className="h-16 w-16 mx-auto mb-4 opacity-20" />
                                <p>等待画面同步...</p>
                            </div>
                        )}

                        {status === "running" && (
                            <div className="absolute top-4 right-4 animate-pulse">
                                <Badge className="bg-red-500 text-white shadow-lg">LIVE</Badge>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
