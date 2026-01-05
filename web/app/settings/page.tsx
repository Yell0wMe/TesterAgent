"use client"

import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { toast } from 'sonner';
import { Settings, Save, Key, Loader2, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function SettingsPage() {
    const [apiKey, setApiKey] = useState("");
    const [originalKey, setOriginalKey] = useState("");
    const [model, setModel] = useState("glm-4");
    const [originalModel, setOriginalModel] = useState("glm-4");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showKey, setShowKey] = useState(false);
    const [hasKey, setHasKey] = useState(false);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const res = await axios.get('/api/settings');
            if (res.data.has_api_key) {
                setApiKey(res.data.zhipu_api_key_masked); // 显示脱敏的 key
                setOriginalKey(res.data.zhipu_api_key_masked);
                setHasKey(true);
            }
            if (res.data.zhipu_model) {
                setModel(res.data.zhipu_model);
                setOriginalModel(res.data.zhipu_model);
            }
        } catch (err) {
            console.error(err);
            toast.error("加载设置失败");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!apiKey) {
            toast.error("API Key 不能为空");
            return;
        }

        // 如果没有修改（还是脱敏状态），就不提交
        if (apiKey === originalKey && model === originalModel && hasKey) {
            toast.info("没有检测到修改");
            return;
        }

        setSaving(true);
        try {
            const payload: any = {};
            // 只有当 Key 发生变化（且不是脱敏状态）时才提交
            if (apiKey !== originalKey) {
                payload.zhipu_api_key = apiKey;
            }
            if (model !== originalModel) {
                payload.zhipu_model = model;
            }

            if (Object.keys(payload).length === 0) {
                toast.info("没有需要保存的修改");
                setSaving(false);
                return;
            }

            await axios.put('/api/settings', payload);
            toast.success("设置已保存");

            if (payload.zhipu_api_key) {
                setOriginalKey(apiKey);
                setHasKey(true);
            }
            if (payload.zhipu_model) {
                setOriginalModel(model);
            }

            // 重新加载
            loadSettings();
        } catch (err) {
            console.error(err);
            toast.error("保存失败");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="container mx-auto py-6 space-y-6 max-w-7xl">
            {/* Header */}
            <div className="flex items-center gap-4 mb-4">
                <Link href="/">
                    <Button variant="ghost" size="icon" className="rounded-full bg-white shadow-sm hover:bg-slate-50">
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                </Link>
                <div className="w-10 h-10 rounded-lg bg-slate-900 flex items-center justify-center shadow-md">
                    <Settings className="text-white w-6 h-6" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">系统设置</h1>
                    <p className="text-sm text-muted-foreground">配置系统全局参数</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="shadow-sm border-slate-200">
                    <CardHeader className="bg-slate-50/50 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                            <Key className="h-4 w-4 text-slate-500" />
                            <CardTitle className="text-base">模型配置</CardTitle>
                        </div>
                        <CardDescription>配置大模型 API 密钥，用于驱动 AI Agent</CardDescription>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">智谱 GLM-4 API Key</label>
                            <div className="relative">
                                <Input
                                    type={showKey ? "text" : "password"}
                                    placeholder="请输入 API Key (sk-...)"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    className="pr-10"
                                    disabled={loading}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowKey(!showKey)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
                                >
                                    {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                密钥将存储在服务器端，前端仅显示脱敏信息。
                            </p>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">模型名称 (Model)</label>
                            <Input
                                type="text"
                                placeholder="例如: glm-4, glm-4-flash"
                                value={model}
                                onChange={(e) => setModel(e.target.value)}
                                disabled={loading}
                            />
                            <p className="text-xs text-muted-foreground">
                                指定使用的智谱模型版本，默认为 glm-4。
                            </p>
                        </div>

                        <div className="pt-2 flex justify-end">
                            <Button
                                onClick={handleSave}
                                disabled={loading || saving}
                                className="bg-slate-900 text-white hover:bg-slate-800"
                            >
                                {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                                保存配置
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
