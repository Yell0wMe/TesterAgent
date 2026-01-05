"use client"

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchDevices, Device } from '@/lib/api';
import axios from 'axios';
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { toast } from 'sonner';
import { ArrowLeft, Upload, Smartphone, Play, Loader2, CheckCircle2, FileText, Zap, FolderOpen, AlertCircle } from 'lucide-react';

export default function NewRunPage() {
    const router = useRouter();
    const [devices, setDevices] = useState<Device[]>([]);
    const [selectedDevice, setSelectedDevice] = useState<string>("");
    const [docId, setDocId] = useState<string>("examples/wechat_ts.yaml");
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadedFileName, setUploadedFileName] = useState<string>("");

    useEffect(() => {
        fetchDevices().then(setDevices);
    }, []);

    const handleCreate = async () => {
        if (!selectedDevice) {
            toast.error("请选择一个设备");
            return;
        }
        if (!docId) {
            toast.error("请输入文档 ID 或路径");
            return;
        }

        setLoading(true);
        try {
            const res = await axios.post('/api/runs', {
                doc_id: docId,
                device_id: selectedDevice,
                config: {}
            });
            toast.success("任务创建成功！");
            router.push(`/runs/${res.data.run_id}`);
        } catch (e: any) {
            toast.error("创建任务失败: " + (e.response?.data?.detail || e.message));
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            const file = e.target.files[0];
            const formData = new FormData();
            formData.append('file', file);

            setUploading(true);
            try {
                const res = await axios.post('/api/docs', formData);
                setDocId(res.data.doc_id);
                setUploadedFileName(file.name);
                toast.success(`已上传: ${file.name}`);
            } catch (err) {
                toast.error("上传失败");
                console.error(err);
            } finally {
                setUploading(false);
            }
        }
    };

    const activeDevices = devices.filter(d => d.status !== 'offline');
    const canStart = selectedDevice && docId && !loading;

    return (
        <div className="container mx-auto py-6 space-y-6 max-w-7xl">
            {/* Header */}
            <div className="flex justify-between items-center bg-white/50 p-4 rounded-xl backdrop-blur-sm border shadow-sm">
                <div className="flex items-center gap-4">
                    <Link href="/">
                        <Button variant="ghost" size="icon" className="rounded-full bg-white shadow-sm hover:bg-slate-50">
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                    </Link>
                    <div className="w-10 h-10 rounded-lg bg-orange-500 flex items-center justify-center shadow-lg">
                        <Zap className="text-white w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">新建测试任务</h1>
                        <p className="text-sm text-muted-foreground italic">New Automated Test Run</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column: Document Selection */}
                <Card className="shadow-sm border-slate-200">
                    <CardHeader className="bg-slate-50/50 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">1</div>
                            <CardTitle className="text-base">选择测试文档</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                        <div className="flex gap-2">
                            <div className="flex-1 relative">
                                <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <Input
                                    placeholder="输入 Bundle 路径，或 PRD 文档 URL (http://...)"
                                    value={docId}
                                    onChange={e => setDocId(e.target.value)}
                                    className="pl-9 bg-slate-50 border-slate-200"
                                />
                            </div>
                            <label className={`inline-flex items-center gap-2 px-4 h-10 rounded-md text-sm font-medium cursor-pointer transition-colors ${uploading
                                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                    : 'bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 shadow-sm'
                                }`}>
                                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                                {uploading ? '上传中' : '上传'}
                                <input
                                    type="file"
                                    className="hidden"
                                    accept=".md,.txt,.docx,.pdf,.html,.htm,.yaml,.yml"
                                    onChange={handleFileUpload}
                                    disabled={uploading}
                                />
                            </label>
                        </div>

                        {uploadedFileName && (
                            <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 px-3 py-2 rounded-md border border-emerald-100">
                                <CheckCircle2 className="h-4 w-4" />
                                已上传: {uploadedFileName}
                            </div>
                        )}

                        <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                            <FileText className="h-3.5 w-3.5" />
                            支持 .md, .txt, .docx, .pdf, .html, .yaml 等格式
                        </div>
                    </CardContent>
                </Card>

                {/* Right Column: Device Selection */}
                <Card className="shadow-sm border-slate-200">
                    <CardHeader className="bg-slate-50/50 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">2</div>
                            <CardTitle className="text-base">选择测试设备</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        {activeDevices.length === 0 ? (
                            <div className="py-8 text-center bg-slate-50 rounded-lg border border-dashed border-slate-200">
                                <Smartphone className="h-8 w-8 mx-auto text-slate-300 mb-2" />
                                <p className="font-medium text-slate-900">未发现设备</p>
                                <p className="text-xs text-slate-500 mt-1">请连接设备并确保 ADB 已授权</p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {activeDevices.map(device => (
                                    <div
                                        key={device.id}
                                        className={`p-3 rounded-lg cursor-pointer flex items-center justify-between border transition-all ${selectedDevice === device.id
                                                ? 'bg-indigo-50 border-indigo-200 shadow-sm'
                                                : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                                            }`}
                                        onClick={() => setSelectedDevice(device.id)}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${selectedDevice === device.id
                                                    ? 'bg-indigo-100 text-indigo-600'
                                                    : 'bg-slate-100 text-slate-500'
                                                }`}>
                                                <Smartphone className="h-5 w-5" />
                                            </div>
                                            <div>
                                                <div className="font-medium text-sm text-slate-900">{device.remark || device.model || "未知设备"}</div>
                                                <div className="text-xs text-slate-500 font-mono">{device.id}</div>
                                            </div>
                                        </div>
                                        <Badge
                                            variant="secondary"
                                            className={`text-xs ${device.status === 'free'
                                                    ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100'
                                                    : 'bg-amber-100 text-amber-700 hover:bg-amber-100'
                                                }`}
                                        >
                                            {device.status === 'free' ? '空闲' : '使用中'}
                                        </Badge>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Bottom Action Bar */}
            <Card className="shadow-sm border-slate-200 bg-slate-50/50">
                <CardContent className="p-4 flex items-center justify-between">
                    <div className="text-sm text-slate-500 flex items-center gap-2">
                        <AlertCircle className="h-4 w-4" />
                        {!docId ? '请先选择测试文档' : !selectedDevice ? '请选择一个测试设备' : '准备就绪'}
                    </div>
                    <Button
                        size="lg"
                        className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200 min-w-[200px]"
                        onClick={handleCreate}
                        disabled={!canStart}
                    >
                        {loading ? (
                            <>
                                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                                创建任务...
                            </>
                        ) : (
                            <>
                                <Play className="h-5 w-5 mr-2" />
                                开始测试
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}
