"use client"

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchDevices, Device } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCw, MonitorSmartphone, ArrowLeft, Edit2 } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

export default function DevicesPage() {
    const [devices, setDevices] = useState<Device[]>([]);
    const [loading, setLoading] = useState(true);

    const loadDevices = async () => {
        setLoading(true);
        try {
            const data = await fetchDevices();
            setDevices(data);
        } catch (error) {
            console.error("Failed to load devices", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDevices();
        const interval = setInterval(loadDevices, 5000);
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'free': return 'bg-green-500 hover:bg-green-600';
            case 'reserved': return 'bg-yellow-500 hover:bg-yellow-600';
            case 'running': return 'bg-blue-500 hover:bg-blue-600';
            case 'offline': return 'bg-gray-500 hover:bg-gray-600';
            default: return 'bg-gray-500';
        }
    };

    const getStatusText = (status: string) => {
        switch (status) {
            case 'free': return '空闲';
            case 'reserved': return '占用';
            case 'running': return '运行中';
            case 'offline': return '离线';
            default: return '未知';
        }
    };

    return (
        <div className="container mx-auto py-10">
            <div className="flex items-center mb-8 gap-4">
                <Link href="/">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                </Link>
                <div className="flex-1">
                    <h1 className="text-3xl font-bold tracking-tight">设备管理</h1>
                    <p className="text-muted-foreground mt-2">管理已连接的自动化测试设备</p>
                </div>
                <Button onClick={loadDevices} variant="outline" disabled={loading}>
                    <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    刷新
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {devices.map((device) => (
                    <Card key={device.id} className="relative overflow-hidden group hover:shadow-md transition-shadow">
                        <div className={`absolute top-0 left-0 w-1 h-full ${getStatusColor(device.status)}`} />
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-lg font-medium flex-1 flex items-center gap-2">
                                {device.remark || device.model || "未知设备"}
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={async () => {
                                        const newRemark = prompt('修改设备备注:', device.remark || '');
                                        if (newRemark !== null) {
                                            try {
                                                await axios.put(`/api/devices/${device.id}/remark`, { remark: newRemark });
                                                toast.success('备注已更新');
                                                loadDevices();
                                            } catch (err) {
                                                toast.error('更新备注失败');
                                            }
                                        }
                                    }}
                                >
                                    <Edit2 className="h-3 w-3" />
                                </Button>
                            </CardTitle>
                            <MonitorSmartphone className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold font-mono text-sm mt-2">{device.id}</div>
                            <div className="mt-4 flex items-center gap-2">
                                <Badge variant="secondary" className={getStatusColor(device.status) + " text-white border-0"}>
                                    {getStatusText(device.status)}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                    {device.type.toUpperCase()}
                                </span>
                            </div>
                            {device.locked_by && (
                                <div className="mt-4 text-xs text-yellow-600 bg-yellow-50 p-2 rounded">
                                    锁定者: {device.locked_by}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}

                {devices.length === 0 && !loading && (
                    <div className="col-span-full text-center py-10 text-muted-foreground">
                        未发现 ADB 连接设备
                    </div>
                )}
            </div>
        </div>
    );
}
