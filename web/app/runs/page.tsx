"use client"

import { useEffect, useState } from 'react';
import Link from 'next/link';
import axios from 'axios';
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Play, Clock, Smartphone, FileText, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { toast } from 'sonner';

export default function RunsPage() {
    const [runs, setRuns] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const loadRuns = async () => {
        setLoading(true);
        try {
            const res = await axios.get('/api/runs');
            setRuns(res.data);
        } catch (e) {
            console.error("Failed to load runs", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadRuns();
        const interval = setInterval(loadRuns, 10000);
        return () => clearInterval(interval);
    }, []);

    const handleDelete = async (e: React.MouseEvent, runId: string) => {
        e.preventDefault();
        e.stopPropagation();

        if (!confirm(`确定要删除任务 ${runId} 吗？此操作不可恢复。`)) {
            return;
        }

        try {
            await axios.delete(`/api/runs/${runId}`);
            toast.success("任务已删除");
            setRuns(runs.filter(r => r.id !== runId));
        } catch (err) {
            toast.error("删除失败");
            console.error(err);
        }
    };

    const handleClearAll = async () => {
        if (!confirm('确定要清除所有历史任务吗？\n注意：正在运行中的任务将被保留。此操作不可恢复。')) {
            return;
        }

        try {
            const res = await axios.delete('/api/runs');
            toast.success(`已清除 ${res.data.deleted_count} 个历史任务`);
            loadRuns();
        } catch (err) {
            toast.error("清除失败");
            console.error(err);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'running': return 'bg-blue-500 hover:bg-blue-600';
            case 'done': return 'bg-green-500 hover:bg-green-600';
            case 'failed': return 'bg-red-500 hover:bg-red-600';
            default: return 'bg-gray-500';
        }
    }

    const getStatusText = (status: string) => {
        switch (status) {
            case 'running': return '运行中';
            case 'done': return '已完成';
            case 'failed': return '失败';
            case 'pending': return '等待中';
            default: return status;
        }
    }

    return (
        <div className="container mx-auto py-10">
            <div className="flex items-center mb-8 gap-4">
                <Link href="/">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                </Link>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold tracking-tight">任务列表</h1>
                    <p className="text-muted-foreground mt-2">查看所有运行中和已完成的任务</p>
                </div>
                <div className="flex gap-2">
                    {runs.length > 0 && (
                        <Button variant="outline" className="text-destructive hover:bg-destructive/10 border-destructive/50" onClick={handleClearAll}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            清除历史
                        </Button>
                    )}
                    <Link href="/runs/new">
                        <Button>
                            <Play className="mr-2 h-4 w-4" />
                            新建任务
                        </Button>
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {runs.map(run => (
                    <Link key={run.id} href={`/runs/${run.id}`}>
                        <Card className="hover:bg-accent transition-colors cursor-pointer group">
                            <CardHeader className="p-4 md:p-6 flex flex-row items-center justify-between space-y-0">
                                <div className="flex items-center gap-4">
                                    <Badge className={getStatusColor(run.status)}>{getStatusText(run.status)}</Badge>
                                    <div>
                                        <CardTitle className="text-base font-mono">{run.id}</CardTitle>
                                        <CardDescription className="flex items-center gap-4 mt-1">
                                            <span className="flex items-center gap-1">
                                                <FileText className="h-3 w-3" />
                                                {run.doc_id || run.instruction?.slice(0, 20) + '...' || 'N/A'}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Smartphone className="h-3 w-3" />
                                                {run.device_id}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock className="h-3 w-3" />
                                                {run.created_at && formatDistanceToNow(new Date(run.created_at), { addSuffix: true, locale: zhCN })}
                                            </span>
                                        </CardDescription>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive hover:bg-destructive/10"
                                    onClick={(e) => handleDelete(e, run.id)}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </CardHeader>
                        </Card>
                    </Link>
                ))}

                {runs.length === 0 && !loading && (
                    <Card className="p-8 text-center text-muted-foreground bg-muted/50 border-dashed">
                        暂无任务记录
                    </Card>
                )}
            </div>
        </div>
    );
}
