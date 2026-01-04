"use client"

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Smartphone, Play, FileText, Clock, ArrowRight, Zap } from 'lucide-react';
import axios from 'axios';

interface RunSummary {
  id: string;
  status: string;
  device_id: string;
  created_at: string;
}

export default function Home() {
  const [recentRuns, setRecentRuns] = useState<RunSummary[]>([]);
  const [deviceCount, setDeviceCount] = useState(0);
  const [runningCount, setRunningCount] = useState(0);
  const [totalRuns, setTotalRuns] = useState(0);

  useEffect(() => {
    // Fetch recent runs with a larger limit to get accurate total
    axios.get('/api/runs?limit=100').then(res => {
      const runs = res.data || [];
      setRecentRuns(runs.slice(0, 5)); // Show only 5 recent
      setTotalRuns(runs.length);
      setRunningCount(runs.filter((r: RunSummary) => r.status === 'running').length);
    }).catch(() => {});

    // Fetch device count
    axios.get('/api/devices').then(res => {
      setDeviceCount(res.data?.filter((d: any) => d.status !== 'offline').length || 0);
    }).catch(() => {});
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running': return <Badge className="bg-blue-500 text-white">运行中</Badge>;
      case 'done': return <Badge className="bg-green-500 text-white">已完成</Badge>;
      case 'failed': return <Badge variant="destructive">失败</Badge>;
      case 'stopped': return <Badge variant="secondary">已停止</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <main className="container mx-auto py-8 px-4">
      {/* Hero Section */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-1.5 rounded-full text-sm font-medium mb-4">
          <Zap className="h-4 w-4" />
          AI 驱动的真机测试
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl mb-4">
          TesterAgent 控制台
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          基于 PhoneAgent 的真机自动化测试平台
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-1">在线设备</p>
              <p className="text-3xl font-bold">{deviceCount}</p>
            </div>
            <div className="p-3 bg-blue-500/10 rounded-full">
              <Smartphone className="h-6 w-6 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-1">进行中任务</p>
              <p className="text-3xl font-bold">{runningCount}</p>
            </div>
            <div className="p-3 bg-green-500/10 rounded-full">
              <Activity className="h-6 w-6 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-1">历史任务</p>
              <p className="text-3xl font-bold">{totalRuns}</p>
            </div>
            <div className="p-3 bg-purple-500/10 rounded-full">
              <FileText className="h-6 w-6 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
        <Link href="/runs/new" className="block group">
          <Card className="h-full transition-all hover:shadow-lg hover:border-primary cursor-pointer">
            <CardContent className="p-6 flex items-center gap-5">
              <div className="p-4 rounded-2xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground group-hover:scale-105 transition-transform">
                <Play className="h-8 w-8" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold mb-1">新建测试任务</h3>
                <p className="text-muted-foreground text-sm">上传 PRD 文档并开始自动化测试</p>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
            </CardContent>
          </Card>
        </Link>

        <Link href="/devices" className="block group">
          <Card className="h-full transition-all hover:shadow-lg hover:border-blue-500 cursor-pointer">
            <CardContent className="p-6 flex items-center gap-5">
              <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 text-white group-hover:scale-105 transition-transform">
                <Smartphone className="h-8 w-8" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold mb-1">设备管理</h3>
                <p className="text-muted-foreground text-sm">查看连接的设备状态与信息</p>
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Recent Runs */}
      {recentRuns.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-lg">最近任务</CardTitle>
              <CardDescription>最近执行的测试任务</CardDescription>
            </div>
            <Link href="/runs">
              <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-foreground">
                查看全部
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentRuns.map(run => (
                <Link key={run.id} href={`/runs/${run.id}`} className="block">
                  <div className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/50 transition-colors cursor-pointer group">
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-muted rounded-lg group-hover:bg-background transition-colors">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div>
                        <div className="font-mono text-sm font-medium">{run.id}</div>
                        <div className="text-xs text-muted-foreground">{run.device_id}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {getStatusBadge(run.status)}
                      <span className="text-xs text-muted-foreground hidden sm:block">
                        {new Date(run.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {recentRuns.length === 0 && (
        <Card className="text-center py-12">
          <CardContent>
            <FileText className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-2">还没有任务记录</h3>
            <p className="text-muted-foreground mb-6">创建您的第一个测试任务开始体验</p>
            <Link href="/runs/new">
              <Button size="lg" className="gap-2">
                <Play className="h-4 w-4" />
                创建第一个任务
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
