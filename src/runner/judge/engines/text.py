"""
Text Engine - 文本断言引擎

使用 OCR 或模拟方式判定文本断言。
"""

import re
from pathlib import Path

from runner.judge.engines.base import AssertionEngine
from runner.models.verdict import AssertionResult, VerdictStatus


# 模拟 OCR 结果（Mock 模式）
# 真实模式应使用 OCR 库或 VLM
MOCK_OCR_RESULTS = {
    "首页": True,
    "我的": True,
    "登录成功": True,
    "退出登录": True,
    "输出至少 1 条 TestSpec": True,
    "验证码已发送": True,
    "登录": True,
}


class TextEngine(AssertionEngine):
    """文本断言引擎"""
    
    def __init__(self, mock: bool = True, api_key: str = ""):
        """
        初始化
        
        Args:
            mock: 是否使用模拟 OCR
            api_key: API Key
        """
        self.mock = mock
        self.api_key = api_key
    
    @property
    def name(self) -> str:
        return "text_engine"
    
    def supported_types(self) -> list[str]:
        return [
            "ocr_text_contains",
            "ocr_text_not_contains",
            "ocr_text_equals",
        ]
    
    def evaluate(
        self,
        assertion_type: str,
        target: str,
        evidence_path: str,
        assertion_id: str = "",
        must: bool = True,
        **kwargs
    ) -> AssertionResult:
        """评估文本断言"""
        
        if self.mock:
            # Mock 模式：使用传统 OCR 文本匹配
            ocr_text = self._get_mock_ocr_text()
            passed = target in ocr_text
            expected = target
            actual = "Mock OCR 结果"
            why = f"OCR 命中 '{target}'" if passed else f"OCR 未找到 '{target}'"
        else:
            # 真实模式：使用 VLM 语义验证
            passed, expected, actual, why = self._evaluate_via_vlm(target, evidence_path)
        
        return AssertionResult(
            id=assertion_id,
            must=must,
            status=VerdictStatus.PASS if passed else VerdictStatus.FAIL,
            expected=expected,
            actual=actual,
            evidence=evidence_path,
            why=why,
            confidence=1.0 if self.mock else 0.9
        )
    
    def _evaluate_via_vlm(self, assertion_description: str, evidence_path: str) -> tuple[bool, str, str, str]:

        """使用 VLM 语义验证断言"""
        try:
            import os
            import base64
            from zhipuai import ZhipuAI
            
            if not evidence_path or not os.path.exists(evidence_path):
                return False, "", "", f"证据文件不存在: {evidence_path}"
            
            api_key = self.api_key or os.getenv("ZHIPU_API_KEY")
            if not api_key:
                return False, "", "", "未配置 ZHIPU_API_KEY"
            
            client = ZhipuAI(api_key=api_key)
            
            with open(evidence_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            mime_type = "image/png" if evidence_path.lower().endswith(".png") else "image/jpeg"
            data_uri = f"data:{mime_type};base64,{img_b64}"
            
            prompt = f"""你是一个移动端UI测试断言验证器。请仔细分析这张手机截图。

【断言条件】
{assertion_description}

【分析步骤】
第一步：详细描述截图中看到的所有内容
- 页面标题是什么？
- 有哪些按钮、输入框、列表项？
- 输入框中有什么文字？
- 列表或卡片中显示了哪些内容？
- 底部导航栏当前选中的是什么？

第二步：判断断言是否成立
- 断言条件是否在截图中得到体现？
- 采用宽松的语义理解，只要截图内容能够满足断言的核心意图即可判为通过
- 例如：如果断言说"显示热搜词"，那么显示了搜索历史、搜索建议、推荐词等都可以视为满足

【输出格式】（必须严格按以下格式，每项一行）
结果: PASS 或 FAIL
期望: <用一句话简述断言期望看到什么>
实际: <列出截图中观察到的关键内容，用逗号分隔>
说明: <判定理由>"""


            print(f"[Judge] 评估断言: {assertion_description}")
            
            response = client.chat.completions.create(
                model="glm-4v-flash",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}}
                        ]
                    }
                ]
            )
            
            result_text = response.choices[0].message.content.strip()
            print(f"[Judge] VLM 响应:\n{result_text}")
            
            # 解析结果
            lines = result_text.split("\n")
            passed = False
            expected = assertion_description
            actual = ""
            why = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith("结果:") or line.startswith("结果："):
                    passed = "PASS" in line.upper()
                elif line.startswith("期望:") or line.startswith("期望："):
                    expected = line.split(":", 1)[-1].strip() if ":" in line else line.split("：", 1)[-1].strip()
                elif line.startswith("实际:") or line.startswith("实际："):
                    actual = line.split(":", 1)[-1].strip() if ":" in line else line.split("：", 1)[-1].strip()
                elif line.startswith("说明:") or line.startswith("说明："):
                    why = line.split(":", 1)[-1].strip() if ":" in line else line.split("：", 1)[-1].strip()
            
            # 如果没解析到实际，用完整响应
            if not actual:
                actual = result_text.split("\n")[-1] if result_text else "无法解析"
            if not why:
                why = f"{'通过' if passed else '失败'}: {actual}"
            
            return passed, expected, actual, why

            
        except Exception as e:
            print(f"[Judge] VLM 评估失败: {e}")
            import traceback
            traceback.print_exc()
            return False, f"VLM 评估失败: {str(e)}"


    
    def _get_ocr_text(self, evidence_path: str) -> str:
        """
        获取 OCR 文本
        
        Args:
            evidence_path: 截图路径
            
        Returns:
            OCR 识别的文本
        """
        if self.mock:
            # Mock 模式：返回预定义的模拟文本
            return self._get_mock_ocr_text()
        
        # 真实模式：调用 OCR
        return self._get_ocr_text_via_vlm(evidence_path)
    
    def _get_ocr_text_via_vlm(self, evidence_path: str) -> str:
        """调用 VLM 进行 OCR"""
        try:
            import os
            import base64
            from zhipuai import ZhipuAI
            
            # 检查文件是否存在
            if not evidence_path or not os.path.exists(evidence_path):
                print(f"[警告] OCR 证据文件不存在: {evidence_path}")
                return ""
            
            api_key = self.api_key or os.getenv("ZHIPU_API_KEY")
            if not api_key:
                print("[警告] 未配置 ZHIPU_API_KEY，OCR 无法通过 VLM 执行")
                return ""
            
            client = ZhipuAI(api_key=api_key)
            
            # 读取并编码图片
            with open(evidence_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            # 判断图片格式
            if evidence_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif evidence_path.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/png"
            
            # 使用正确的 data URI 格式
            data_uri = f"data:{mime_type};base64,{img_b64}"
            
            print(f"[OCR] 正在分析截图: {evidence_path}")
                
            response = client.chat.completions.create(
                model="glm-4v-flash",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请识别图片中的所有可见文字，直接输出文字内容，每行一个，不要添加任何解释、标点或格式。"},
                            {"type": "image_url", "image_url": {"url": data_uri}}
                        ]
                    }
                ]
            )
            
            ocr_text = response.choices[0].message.content
            print(f"[OCR] 识别结果: {ocr_text[:100]}..." if len(ocr_text) > 100 else f"[OCR] 识别结果: {ocr_text}")
            return ocr_text
            
        except Exception as e:
            print(f"[警告] VLM OCR 失败: {e}")
            import traceback
            traceback.print_exc()
            return ""

    
    def _get_mock_ocr_text(self) -> str:
        """获取模拟 OCR 文本"""
        # 返回一个包含常见成功文案的模拟文本
        return """
        首页
        我的
        登录成功
        退出登录
        输出至少 1 条 TestSpec
        验证码已发送
        登录
        设置
        消息
        """
    
    def check_text(self, target: str) -> bool:
        """快速检查文本是否存在（Mock）"""
        if self.mock:
            return MOCK_OCR_RESULTS.get(target, False)
        return False
