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
        
        # 获取 OCR 结果
        ocr_text = self._get_ocr_text(evidence_path)
        
        # 根据断言类型判定
        if assertion_type == "ocr_text_contains":
            passed = target in ocr_text
            why = f"OCR 命中 '{target}'" if passed else f"OCR 未找到 '{target}'"
            
        elif assertion_type == "ocr_text_not_contains":
            passed = target not in ocr_text
            why = f"OCR 未包含 '{target}'（期望）" if passed else f"OCR 意外包含 '{target}'"
            
        elif assertion_type == "ocr_text_equals":
            passed = ocr_text.strip() == target.strip()
            why = f"OCR 完全匹配 '{target}'" if passed else f"OCR 不匹配: '{ocr_text}' != '{target}'"
            
        else:
            passed = False
            why = f"不支持的断言类型: {assertion_type}"
        
        return AssertionResult(
            id=assertion_id,
            must=must,
            status=VerdictStatus.PASS if passed else VerdictStatus.FAIL,
            evidence=evidence_path,
            why=why,
            confidence=1.0 if self.mock else 0.9
        )
    
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
            
            api_key = self.api_key or os.getenv("ZHIPU_API_KEY")
            if not api_key:
                print("[警告] 未配置 ZHIPU_API_KEY，OCR 无法通过 VLM 执行")
                return ""
            
            client = ZhipuAI(api_key=api_key)
            
            with open(evidence_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                
            response = client.chat.completions.create(
                model="glm-4v",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请识别图中的所有文字，按顺序输出，不要添加任何解释。"},
                            {"type": "image_url", "image_url": {"url": img_b64}}
                        ]
                    }
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[警告] VLM OCR 失败: {e}")
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
