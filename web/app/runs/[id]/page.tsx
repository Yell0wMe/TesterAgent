"use client"

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import axios from 'axios';
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Activity, Terminal, ArrowLeft, FileText, CheckCircle, XCircle, ClipboardList, FileCode, Download, Loader2, Image } from 'lucide-react';

interface Testcase {
    spec_id: string;
    goal: string;
    preconditions: string[];
    agent_config?: { max_steps?: number };
}

interface AssertionResult {
    expected?: string;
    actual?: string;
    id: string;
    status: string;
    evidence?: string;
    why?: string;
}

interface Report {
    case_id?: string;
    status: string;
    summary?: string;
    assertions?: AssertionResult[];
}

export default function RunDetailPage() {
    const params = useParams();
    const runId = params.id as string;

    const [logs, setLogs] = useState<string[]>([]);
    const [status, setStatus] = useState<string>("loading");
    const [metadata, setMetadata] = useState<any>(null);
    const [artifacts, setArtifacts] = useState<any[]>([]);
    const [currentLiveUrl, setCurrentLiveUrl] = useState<string>(`/api/runs/${runId}/live?t=${Date.now()}`);
    const [takeoverMsg, setTakeoverMsg] = useState<string | null>(null);
    
    const [verboseLog, setVerboseLog] = useState<string | null>(null);
    const [testcase, setTestcase] = useState<Testcase | null>(null);
    const [report, setReport] = useState<Report | null>(null);

    const scrollRef = useRef<HTMLDivElement>(null);

    const loadArtifacts = () => {
        axios.get(`/api/runs/${runId}/artifacts`).then(res => setArtifacts(res.data)).catch(() => {});
    }
    
    const loadTestcase = () => {
        axios.get(`/api/runs/${runId}/testcase`).then(res => setTestcase(res.data)).catch(() => {});
    }
    
    const loadReport = () => {
        axios.get(`/api/runs/${runId}/report`).then(res => setReport(res.data)).catch(() => {});
    }
    
    const loadVerboseLog = () => {
        axios.get(`/api/runs/${runId}/verbose-log`).then(res => setVerboseLog(res.data.log)).catch(() => {});
    }

    useEffect(() => {
        axios.get(`/api/runs/${runId}`).then(res => {
            setMetadata(res.data);
            setStatus(res.data.status);
            if (res.data.logs) {
                setLogs(res.data.logs.map((l: any) => l.content));
            }
            if (["done", "failed", "stopped"].includes(res.data.status)) {
                loadArtifacts();
                loadReport();
                loadVerboseLog();
            }
        }).catch(console.error);
        loadTestcase();
    }, [runId]);

    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let host = window.location.host;
        if (host.includes(":3000")) {
            host = host.replace(":3000", ":8000");
        }
        const wsUrl = `${protocol}//${host}/ws/runs/${runId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            setLogs(prev => [...prev, ">>> WebSocket 已连接"]);
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "log") {
                setLogs(prev => [...prev, msg.content]);
            } else if (msg.type === "status") {
                setStatus(msg.status);
                if (["done", "failed", "stopped"].includes(msg.status)) {
                    loadArtifacts();
                    loadReport();
                    loadVerboseLog();
                }
            } else if (msg.type === "step") {
                const actionName = msg.data.action?.name || "未知动作";
                setLogs(prev => [...prev, `[步骤 ${msg.data.i}] ${actionName}`]);
            } else if (msg.type === "takeover_request") {
                setTakeoverMsg(msg.message);
                setLogs(prev => [...prev, `>>> ⚠️ 请求人工接管: ${msg.message}`]);
            } else if (msg.type === "live_update") {
                setCurrentLiveUrl(msg.url);
            }
        };

        ws.onclose = () => {
            setLogs(prev => [...prev, ">>> WebSocket 已断开"]);
        };

        return () => ws.close();
    }, [runId]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    const handleStop = async () => {
        if (!confirm("确定要停止任务吗？")) return;
        try {
            await axios.post(`/api/runs/${runId}/stop`);
            setStatus("stopped");
            setTakeoverMsg(null);
        } catch (e) {
            alert("停止失败");
        }
    };

    const getStatusBadge = (s: string) => {
        switch (s) {
            case 'running': return <Badge className="bg-blue-500 text-white">运行中</Badge>;
            case 'done': return <Badge className="bg-green-500 text-white">已完成</Badge>;
            case 'failed': return <Badge variant="destructive">失败</Badge>;
            case 'stopped': return <Badge variant="secondary">已停止</Badge>;
            default: return <Badge variant="outline">{s}</Badge>;
        }
    };

    const isFinished = ["done", "failed", "stopped"].includes(status);

    return (
        <div className="container mx-auto py-4 px-4">
            {/* Takeover Modal */}
            {takeoverMsg && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <Card className="w-full max-w-md shadow-2xl">
                        <CardHeader>
                            <CardTitle className="text-red-600 flex items-center gap-2">
                                <Activity className="h-5 w-5" />
                                需要人工介入
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <p className="text-sm text-muted-foreground">Agent 遇到无法处理的情况，需要您手动操作手机。</p>
                            <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-800">{takeoverMsg}</div>
                            <Separator />
                            <div className="flex gap-3 justify-end">
                                <Button variant="destructive" onClick={handleStop}>停止任务</Button>
                                <Button onClick={() => setTakeoverMsg(null)}>已完成，继续</Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Header */}
            <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
                <div className="flex items-center gap-3">
                    <Link href="/">
                        <Button variant="ghost" size="icon" className="rounded-full h-9 w-9">
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                    </Link>
                    <div>
                        <h1 className="text-xl font-bold font-mono">{runId}</h1>
                        <div className="flex items-center gap-2 mt-1">
                            {getStatusBadge(status)}
                            {metadata && <span className="text-xs text-muted-foreground">设备: {metadata.device_id}</span>}
                        </div>
                    </div>
                </div>
                <div className="flex gap-2">
                    {status === 'running' && (
                        <Button variant="destructive" size="sm" onClick={handleStop}>
                            <Loader2 className="h-4 w-4 mr-1 animate-spin" />停止
                        </Button>
                    )}
                    {isFinished && (
                        <>
                            <Dialog>
                                <DialogTrigger asChild>
                                    <Button variant="outline" size="sm"><FileCode className="h-4 w-4 mr-1" />完整日志</Button>
                                </DialogTrigger>
                                <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
                                    <DialogHeader><DialogTitle>完整执行日志</DialogTitle></DialogHeader>
                                    <ScrollArea className="flex-1 bg-zinc-900 text-green-400 p-4 rounded font-mono text-xs max-h-[60vh]">
                                        <pre className="whitespace-pre-wrap">{verboseLog || "加载中..."}</pre>
                                    </ScrollArea>
                                </DialogContent>
                            </Dialog>
                            <Link href={`/api/runs/${runId}/download`} target="_blank">
                                <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" />下载</Button>
                            </Link>
                        </>
                    )}
                </div>
            </div>

            {/* Main 3-Column Layout */}
            <div style={{ display: 'grid', gridTemplateColumns: '5fr 3fr 4fr', gap: '16px', minHeight: '70vh' }}>
                {/* Left: Console */}
                <Card className="flex flex-col bg-zinc-950 text-green-400 border-zinc-800 overflow-hidden">
                    <CardHeader className="py-2 px-3 bg-zinc-900 border-b border-zinc-800 flex-shrink-0">
                        <CardTitle className="text-xs flex items-center gap-2 text-green-400">
                            <Terminal className="h-3 w-3" />控制台输出
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 p-0 overflow-hidden">
                        <ScrollArea className="h-full p-3 font-mono text-xs" style={{ height: '60vh' }}>
                            {logs.map((log, i) => (
                                <div key={i} className="mb-0.5 break-all whitespace-pre-wrap leading-relaxed">
                                    <span className="opacity-40 select-none mr-1 text-[10px]">{String(i+1).padStart(3, '0')}</span>
                                    {log}
                                </div>
                            ))}
                            <div ref={scrollRef} />
                        </ScrollArea>
                    </CardContent>
                </Card>

                {/* Center: Live View */}
                <Card className="flex flex-col overflow-hidden">
                    <CardHeader className="py-2 px-3 border-b flex-shrink-0">
                        <CardTitle className="text-xs flex items-center gap-2">
                            <Activity className="h-3 w-3" />实时画面
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 flex items-center justify-center bg-zinc-100 dark:bg-zinc-900 p-2 overflow-hidden">
                        <img
                            src={currentLiveUrl}
                            alt="Live View"
                            className="max-h-full max-w-full object-contain rounded shadow"
                            style={{ maxHeight: '58vh' }}
                            onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                if (!target.src.includes("placehold.co")) {
                                    target.src = "https://placehold.co/270x480/1a1a1a/666?text=等待中...";
                                }
                            }}
                        />
                    </CardContent>
                </Card>

                {/* Right: Testcase + Report */}
                <div className="flex flex-col gap-3 overflow-y-auto" style={{ maxHeight: '70vh' }}>
                    {testcase && (
                        <Card className="flex-shrink-0">
                            <CardHeader className="py-2 px-3 border-b">
                                <CardTitle className="text-xs flex items-center gap-2">
                                    <ClipboardList className="h-3 w-3" />测试用例
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-3 space-y-2 text-sm">
                                <div>
                                    <span className="text-[10px] text-muted-foreground block">测试目标</span>
                                    <p className="font-medium text-sm">{testcase.goal}</p>
                                </div>
                                {testcase.preconditions?.length > 0 && (
                                    <div>
                                        <span className="text-[10px] text-muted-foreground block">前置条件</span>
                                        <ul className="list-disc list-inside text-xs text-muted-foreground">
                                            {testcase.preconditions.map((p, i) => <li key={i}>{p}</li>)}
                                        </ul>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}
                    
                    {report && isFinished && (
                        <Card className="flex-shrink-0">
                            <CardHeader className="py-2 px-3 border-b">
                                <CardTitle className="text-xs flex items-center gap-2">
                                    <FileText className="h-3 w-3" />测试报告
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-3 space-y-3">
                                <div className="flex items-center gap-2">
                                    {report.status === 'PASS' ? (
                                        <Badge className="bg-green-500 text-white text-xs gap-1"><CheckCircle className="h-3 w-3" />通过</Badge>
                                    ) : (
                                        <Badge variant="destructive" className="text-xs gap-1"><XCircle className="h-3 w-3" />失败</Badge>
                                    )}
                                    <span className="text-xs text-muted-foreground">{report.summary}</span>
                                </div>
                                
                                {report.assertions && report.assertions.length > 0 && (
                                    <div className="space-y-2">
                                        <span className="text-[10px] text-muted-foreground">断言详情</span>
                                        {report.assertions.map((a, i) => (
                                            <div key={i} className="text-xs p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border space-y-2">
                                                <div className="flex items-center gap-2">
                                                    {a.status === 'PASS' ? (
                                                        <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                                                    ) : (
                                                        <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                                                    )}
                                                    <span className="font-mono font-bold">{a.id}</span>
                                                    <Badge variant={a.status === 'PASS' ? 'default' : 'destructive'} className="text-[10px] h-5">
                                                        {a.status}
                                                    </Badge>
                                                </div>
                                                {a.expected && (
                                                    <div className="pl-6">
                                                        <span className="text-[10px] text-muted-foreground">期望: </span>
                                                        <span className="text-[11px]">{a.expected}</span>
                                                    </div>
                                                )}
                                                {a.actual && (
                                                    <div className="pl-6">
                                                        <span className="text-[10px] text-muted-foreground">实际: </span>
                                                        <span className="text-[11px] font-medium">{a.actual}</span>
                                                    </div>
                                                )}
                                                {a.why && (
                                                    <div className="pl-6 text-[10px] text-muted-foreground">{a.why}</div>
                                                )}
                                                {a.evidence && (
                                                    <div className="pl-6">
                                                        <a href={a.evidence.startsWith('/') ? a.evidence : `/artifacts/${runId}/${a.evidence}`} 
                                                           target="_blank" className="text-[10px] text-blue-500 hover:underline">📷 查看截图证据</a>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {isFinished && artifacts.filter(a => a.type === 'screenshot').length > 0 && (
                        <Card className="flex-shrink-0">
                            <CardHeader className="py-2 px-3 border-b">
                                <CardTitle className="text-xs flex items-center gap-2"><Image className="h-3 w-3" />截图证据</CardTitle>
                            </CardHeader>
                            <CardContent className="p-2">
                                <div className="grid grid-cols-4 gap-1">
                                    {artifacts.filter(a => a.type === 'screenshot').slice(0, 8).map((art, i) => (
                                        <a key={i} href={art.path} target="_blank" className="aspect-[9/16] rounded border overflow-hidden hover:ring-2 ring-primary">
                                            <img src={art.path} className="h-full w-full object-cover" />
                                        </a>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
}
