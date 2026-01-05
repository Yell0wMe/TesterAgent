"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    Play,
    StopCircle,
    Smartphone,
    Terminal,
    Eye,
    Send,
    Loader2,
    CheckCircle,
    XCircle,
    AlertCircle
} from 'lucide-react';
import { toast } from "sonner";

interface Device {
    id: string;
    model: string;
    status: string;
    type: string;
}

interface LogEntry {
    ts: string;
    content: string;
}

export default function DirectAgentPage() {
    const router = useRouter();

    const [devices, setDevices] = useState<Device[]>([]);
    const [selectedDevice, setSelectedDevice] = useState<string>('');
    const [instruction, setInstruction] = useState<string>('');
    const [isRunning, setIsRunning] = useState(false);
    const [runId, setRunId] = useState<string | null>(null);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [liveViewUrl, setLiveViewUrl] = useState<string | null>(null);
    const [status, setStatus] = useState<string>('idle');

    const scrollRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // Fetch online devices
    useEffect(() => {
        const fetchDevices = async () => {
            try {
                const res = await axios.get('/api/devices');
                const online = res.data.filter((d: Device) => d.status !== 'offline');
                setDevices(online);
                if (online.length > 0 && !selectedDevice) {
                    setSelectedDevice(online[0].id);
                }
            } catch (err) {
                console.error("Failed to fetch devices", err);
            }
        };
        fetchDevices();
    }, []);

    // WebSocket connection for real-time updates
    useEffect(() => {
        if (!runId) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/runs/${runId}`);
        wsRef.current = ws;

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'log') {
                setLogs(prev => [...prev, { ts: new Date().toISOString(), content: msg.content }]);
            } else if (msg.type === 'status') {
                setStatus(msg.status);
                if (msg.status === 'done' || msg.status === 'failed' || msg.status === 'stopped') {
                    setIsRunning(false);
                }
            } else if (msg.type === 'live_update') {
                setLiveViewUrl(msg.url);
            } else if (msg.type === 'step') {
                // Optional: track step progress
            }
        };

        return () => {
            if (wsRef.current) wsRef.current.close();
        };
    }, [runId]);

    // Auto-scroll logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const handleStart = async () => {
        if (!selectedDevice || !instruction) {
            toast.error("请选择设备并输入指令");
            return;
        }

        try {
            setIsRunning(true);
            setLogs([]);
            setLiveViewUrl(null);
            setStatus('pending');

            const res = await axios.post('/api/runs/direct', {
                device_id: selectedDevice,
                instruction: instruction
            });

            setRunId(res.data.run_id);
            toast.success(`任务已启动: ${res.data.run_id}`);
        } catch (err: any) {
            setIsRunning(false);
            const errorDetail = err.response?.data?.detail || err.message || "未知错误";
            toast.error(`启动任务失败: ${errorDetail}`);
            console.error("Task start failed", err);
        }

    };

    const handleStop = async () => {
        if (!runId) return;
        try {
            await axios.post(`/api/runs/${runId}/stop`);
        } catch (err) {
            console.error("Failed to stop run", err);
        }
    };

    return (
        <div className="container mx-auto py-6 space-y-6 max-w-7xl">
            <div className="flex justify-between items-center bg-white/50 p-4 rounded-xl backdrop-blur-sm border shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg">
                        <Send className="text-white w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">快捷 AI 任务</h1>
                        <p className="text-sm text-muted-foreground italic">Direct AI Agent Instruction</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-lg border">
                        <Smartphone className="w-4 h-4 text-slate-500" />
                        <select
                            className="bg-transparent text-sm font-medium focus:outline-none min-w-[150px]"
                            value={selectedDevice}
                            onChange={(e) => setSelectedDevice(e.target.value)}
                            disabled={isRunning}
                        >
                            {devices.length === 0 ? (
                                <option value="">无在线设备</option>
                            ) : (
                                devices.map(d => (
                                    <option key={d.id} value={d.id}>{d.model || d.id}</option>
                                ))
                            )}
                        </select>
                    </div>

                    {isRunning ? (
                        <Button variant="destructive" onClick={handleStop} className="shadow-lg animate-pulse hover:animate-none group">
                            <StopCircle className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" /> 停止任务
                        </Button>
                    ) : (
                        <Button
                            onClick={handleStart}
                            disabled={!selectedDevice || !instruction}
                            className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg hover:shadow-indigo-500/20 group"
                        >
                            <Play className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" /> 开始执行
                        </Button>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-220px)]">
                {/* Left: Input & Logs */}
                <div className="lg:col-span-7 flex flex-col gap-6 h-full">
                    <Card className="shadow-sm border-slate-200">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-semibold text-slate-500 uppercase flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" /> 您的需求指令
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex gap-2">
                                <Input
                                    placeholder="例如：打开应用商店，搜索并安装微信，然后返回首页..."
                                    value={instruction}
                                    onChange={(e) => setInstruction(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && !isRunning && handleStart()}
                                    disabled={isRunning}
                                    className="h-12 text-base shadow-sm border-slate-300 focus:ring-indigo-500"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="flex-1 shadow-md border-slate-200 overflow-hidden flex flex-col">
                        <CardHeader className="py-3 bg-slate-50 border-b flex flex-row items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Terminal className="w-4 h-4 text-emerald-600" />
                                <CardTitle className="text-sm font-bold">执行日志</CardTitle>
                            </div>
                            <Badge variant={status === 'running' ? 'default' : 'secondary'} className="rounded-full">
                                {status.toUpperCase()}
                            </Badge>
                        </CardHeader>
                        <CardContent className="p-0 flex-1 overflow-hidden">
                            <ScrollArea className="h-full p-4 font-mono text-xs bg-slate-900 text-slate-300" ref={scrollRef}>
                                {logs.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-500 italic opacity-50 py-20">
                                        <Terminal className="w-12 h-12 mb-4 animate-pulse" />
                                        <p>等待任务启动以接收实时日志...</p>
                                    </div>
                                ) : (
                                    logs.map((log, i) => (
                                        <div key={i} className="mb-1.5 flex gap-2 hover:bg-white/5 p-1 rounded transition-colors group">
                                            <span className="text-slate-500 shrink-0 select-none">[{log.ts.split('T')[1].split('.')[0]}]</span>
                                            <span className={log.content.includes('错误') || log.content.includes('故障') ? 'text-rose-400 font-bold' : ''}>
                                                {log.content}
                                            </span>
                                        </div>
                                    ))
                                )}
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Live View */}
                <div className="lg:col-span-5 h-full">
                    <Card className="h-full shadow-lg border-slate-200 flex flex-col overflow-hidden group">
                        <CardHeader className="py-3 bg-indigo-50/50 border-b flex flex-row items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Eye className="w-4 h-4 text-indigo-600" />
                                <CardTitle className="text-sm font-bold text-indigo-900">实时画面 (Live View)</CardTitle>
                            </div>
                            {isRunning && (
                                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-100 border border-emerald-200">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                                    <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Live</span>
                                </div>
                            )}
                        </CardHeader>
                        <CardContent className="flex-1 bg-slate-100 flex items-center justify-center p-0 relative overflow-hidden">
                            {liveViewUrl ? (
                                <div className="relative w-full h-full flex items-center justify-center group-hover:scale-[1.02] transition-transform duration-500 ease-out">
                                    <img
                                        src={liveViewUrl}
                                        alt="Live View"
                                        className="max-w-full max-h-full object-contain shadow-2xl rounded-sm border-4 border-slate-800"
                                    />
                                    <div className="absolute inset-0 bg-indigo-600/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                                </div>
                            ) : (
                                <div className="text-center space-y-4 max-w-[200px]">
                                    {isRunning ? (
                                        <div className="flex flex-col items-center">
                                            <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" />
                                            <p className="text-sm text-slate-500 font-medium">正在获取实时画面...</p>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center opacity-40">
                                            <Smartphone className="w-16 h-16 text-slate-400 mb-4" />
                                            <p className="text-sm text-slate-500">画面投屏已就绪</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                        {runId && !isRunning && (
                            <div className="absolute bottom-4 right-4 animate-in fade-in slide-in-from-bottom-2 duration-700">
                                <Button variant="outline" size="sm" onClick={() => router.push(`/runs/${runId}`)} className="bg-white/80 backdrop-blur shadow-md">
                                    查看任务报告 <CheckCircle className="ml-2 w-4 h-4 text-emerald-500" />
                                </Button>
                            </div>
                        )}
                    </Card>
                </div>
            </div>
        </div>
    );
}
