"""
Mine 模块 - 需求挖掘（LLM A阶段）

从标准化文档中提取可测试需求，输出 RequirementItem 列表。
这是两段式编译的第一阶段。
"""

import json
import logging
from typing import TYPE_CHECKING

from doc2spec.models.requirement import RequirementItem, RequirementBatch, SourceLoc
from doc2spec.modules.normalize import NormalizedDoc, Paragraph
from doc2spec.prompts.mining import get_mining_prompt, MINING_SYSTEM_PROMPT

if TYPE_CHECKING:
    from doc2spec.adapters.base import LLMAdapter


logger = logging.getLogger(__name__)


class MiningError(Exception):
    """需求挖掘错误"""
    pass


class RequirementMiner:
    """
    需求挖掘器
    
    从文档段落中提取可测试的需求声明，转换为 RequirementItem。
    """
    
    def __init__(
        self, 
        adapter: "LLMAdapter",
        max_retries: int = 2,
        chunk_size: int = 5000
    ):
        """
        初始化挖掘器
        
        Args:
            adapter: LLM 适配器
            max_retries: 最大重试次数
            chunk_size: 文本分块大小（字符数）
        """
        self.adapter = adapter
        self.max_retries = max_retries
        self.chunk_size = chunk_size
    
    def mine(self, doc: NormalizedDoc) -> RequirementBatch:
        """
        从标准化文档中挖掘需求
        
        Args:
            doc: 标准化文档
            
        Returns:
            RequirementBatch: 需求批次
        """
        all_items: list[RequirementItem] = []
        
        # 将段落分组处理
        chunks = self._chunk_paragraphs(doc.all_paragraphs)
        
        for chunk_idx, chunk in enumerate(chunks, start=1):
            logger.info(f"处理文档 {doc.doc_id} 的第 {chunk_idx}/{len(chunks)} 个分块...")
            
            try:
                items = self._mine_chunk(doc.doc_id, doc.title or doc.doc_id, chunk)
                all_items.extend(items)
            except MiningError as e:
                logger.error(f"分块 {chunk_idx} 处理失败: {e}")
                # 继续处理其他分块
        
        return RequirementBatch(doc_id=doc.doc_id, items=all_items)
    
    def mine_from_docs(self, docs: list[NormalizedDoc]) -> list[RequirementBatch]:
        """
        批量从多个文档挖掘需求
        
        Args:
            docs: 标准化文档列表
            
        Returns:
            list[RequirementBatch]: 需求批次列表
        """
        batches = []
        for doc in docs:
            batch = self.mine(doc)
            batches.append(batch)
        return batches
    
    def _chunk_paragraphs(self, paragraphs: list[Paragraph]) -> list[list[Paragraph]]:
        """
        将段落分块，避免超过 LLM 上下文限制
        
        Args:
            paragraphs: 段落列表
            
        Returns:
            list[list[Paragraph]]: 分块后的段落列表
        """
        chunks: list[list[Paragraph]] = []
        current_chunk: list[Paragraph] = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para.content)
            
            if current_size + para_size > self.chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            
            current_chunk.append(para)
            current_size += para_size
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _mine_chunk(self, doc_id: str, doc_title: str, paragraphs: list[Paragraph]) -> list[RequirementItem]:
        """
        挖掘单个分块的需求
        
        Args:
            doc_id: 文档标识符
            doc_title: 文档标题
            paragraphs: 段落列表
            
        Returns:
            list[RequirementItem]: 需求条目列表
        """
        # 构建输入文本
        input_text = f"【文档标题/上下文】: {doc_title}\n\n" + self._format_paragraphs(paragraphs)
        
        # 获取 prompt
        prompt = get_mining_prompt(doc_id)
        
        # 调用 LLM
        response = self._call_llm_with_retry(prompt, input_text)
        
        # 解析响应
        items = self._parse_response(doc_id, response, paragraphs)
        
        return items
    
    def _format_paragraphs(self, paragraphs: list[Paragraph]) -> str:
        """格式化段落为输入文本"""
        parts = []
        for para in paragraphs:
            parts.append(f"[段落 {para.index}] [位置: {para.loc}]")
            parts.append(para.content)
            parts.append("")
        return "\n".join(parts)
    
    def _call_llm_with_retry(self, prompt: str, input_text: str) -> str:
        """带重试的 LLM 调用"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 组合 system prompt 和 user prompt
                full_prompt = f"{MINING_SYSTEM_PROMPT}\n\n{prompt}"
                response = self.adapter.complete(full_prompt, input_text)
                
                # 尝试验证返回的是有效 JSON
                self._validate_json_response(response)
                
                return response
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"第 {attempt + 1} 次尝试: JSON 解析失败，重试...")
                
                if attempt < self.max_retries:
                    # 添加格式强化提示
                    prompt = f"{prompt}\n\n【重要】你必须只输出 JSON 数组，不要包含任何其他文字。"
                    
            except Exception as e:
                last_error = e
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                
                if attempt >= self.max_retries:
                    break
        
        raise MiningError(f"LLM 调用失败（已重试 {self.max_retries} 次）: {last_error}")
    
    def _validate_json_response(self, response: str) -> None:
        """验证响应是有效的 JSON 数组"""
        # 尝试提取 JSON 部分
        cleaned = self._extract_json(response)
        parsed = json.loads(cleaned)
        
        if not isinstance(parsed, list):
            raise json.JSONDecodeError("响应必须是 JSON 数组", response, 0)
    
    def _extract_json(self, response: str) -> str:
        """从响应中提取 JSON 部分"""
        response = response.strip()
        
        # 如果被代码块包裹，提取内容
        if response.startswith("```"):
            lines = response.split("\n")
            # 移除首尾的代码块标记
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        # 找到 JSON 数组的边界
        start = response.find("[")
        end = response.rfind("]")
        
        if start != -1 and end != -1 and end > start:
            return response[start:end + 1]
        
        return response
    
    def _parse_response(
        self, 
        doc_id: str, 
        response: str, 
        paragraphs: list[Paragraph]
    ) -> list[RequirementItem]:
        """解析 LLM 响应为 RequirementItem 列表"""
        cleaned = self._extract_json(response)
        
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise MiningError(f"无法解析 LLM 响应为 JSON: {e}")
        
        if not isinstance(data, list):
            raise MiningError("LLM 响应必须是数组")
        
        items = []
        para_map = {p.index: p for p in paragraphs}
        
        for idx, item_data in enumerate(data):
            try:
                item = self._parse_item(doc_id, item_data, para_map, idx)
                items.append(item)
            except Exception as e:
                logger.warning(f"解析第 {idx + 1} 个需求项失败: {e}")
        
        return items
    
    def _parse_item(
        self, 
        doc_id: str, 
        data: dict, 
        para_map: dict[int, Paragraph],
        idx: int
    ) -> RequirementItem:
        """解析单个需求项"""
        # 获取段落索引
        para_idx = data.get("paragraph_index", idx + 1)
        para = para_map.get(para_idx)
        
        # 构建 SourceLoc
        if para:
            source_loc = SourceLoc(
                doc_id=doc_id,
                section=para.section_path,
                paragraph=para.index,
                quote=data.get("quote")
            )
        else:
            source_loc = SourceLoc(
                doc_id=doc_id,
                section="未知",
                paragraph=idx + 1,
                quote=data.get("quote")
            )
        
        # 确保 success_ui 是列表
        success_ui = data.get("success_ui", [])
        if isinstance(success_ui, str):
            success_ui = [success_ui]
        if not success_ui:
            success_ui = ["操作成功"]  # 默认值
        
        # 确保简单的字符串字段不是列表
        def ensure_str(val):
            if isinstance(val, list):
                return ", ".join([str(v) for v in val])
            return val

        return RequirementItem(
            req_id=data.get("req_id"),
            req_title=data.get("req_title", f"需求 {idx + 1}"),
            user_goal=data.get("user_goal", "完成操作"),
            target_app=ensure_str(data.get("target_app")),
            target_url=ensure_str(data.get("target_url")),
            target_page=ensure_str(data.get("target_page")),
            env_specs=ensure_str(data.get("env_specs")),
            success_ui=success_ui,
            explicit_steps=data.get("explicit_steps", []),
            preconditions=data.get("preconditions", []),
            verifiable_signals=data.get("verifiable_signals", []),
            exceptions=data.get("exceptions", []),
            danger_ops=data.get("danger_ops", []),
            source_loc=source_loc,
            priority=data.get("priority"),
            category=data.get("category")
        )
