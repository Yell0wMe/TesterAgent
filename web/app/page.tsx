import Link from 'next/link';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Activity, Smartphone, Play, FileText } from 'lucide-react';

export default function Home() {
  return (
    <main className="container mx-auto py-10">
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl mb-4">
          TesterAgent 控制台
        </h1>
        <p className="text-xl text-muted-foreground">
          基于 PhoneAgent 的真机自动化测试平台
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              开始测试
            </CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">新建任务</div>
            <p className="text-xs text-muted-foreground mt-1">
              上传 PRD 或运行 Bundle
            </p>
            <div className="mt-4">
              <Link href="/runs/new">
                <Button className="w-full">创建任务</Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              设备管理
            </CardTitle>
            <Smartphone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">设备列表</div>
            <p className="text-xs text-muted-foreground mt-1">
              查看设备状态与占用情况
            </p>
            <div className="mt-4">
              <Link href="/devices">
                <Button variant="outline" className="w-full">管理设备</Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              进行中任务
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground mt-1">
              当前运行的任务
            </p>
            <div className="mt-4">
              <Link href="/runs">
                <Button variant="ghost" className="w-full">查看全部</Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              历史记录
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">测试报告</div>
            <p className="text-xs text-muted-foreground mt-1">
              查看历史运行结果与证据
            </p>
            <div className="mt-4">
              <Link href="/history">
                <Button variant="ghost" className="w-full">浏览历史</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
