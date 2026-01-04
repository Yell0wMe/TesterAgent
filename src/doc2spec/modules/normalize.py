"""
Normalize 模块 - 文档标准化

解析 Markdown/TXT 文件，提取标题层级和段落，
生成带位置信息的 NormalizedDoc 结构。
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class DocFormat(str, Enum):
    """文档格式"""
    MARKDOWN = "markdown"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class Paragraph:
    """段落"""
    index: int  # 段落编号（1-indexed）
    content: str  # 段落内容
    section_path: str  # 所属章节路径
    start_line: int  # 起始行号
    end_line: int  # 结束行号
    
    @property
    def loc(self) -> str:
        """生成位置字符串"""
        return f"{self.section_path} / P{self.index}"


@dataclass
class Section:
    """章节"""
    level: int  # 标题级别（1-6）
    title: str  # 标题文本
    path: str  # 章节路径（如 'H1: 背景 > H2: 问题'）
    start_line: int  # 起始行号
    paragraphs: list[Paragraph] = field(default_factory=list)
    subsections: list["Section"] = field(default_factory=list)


@dataclass
class NormalizedDoc:
    """标准化文档结构"""
    doc_id: str  # 文档标识符
    format: DocFormat  # 文档格式
    title: str | None  # 文档标题
    raw_content: str  # 原始内容
    sections: list[Section]  # 章节列表
    all_paragraphs: list[Paragraph]  # 所有段落的扁平列表
    
    @property
    def paragraph_count(self) -> int:
        """段落总数"""
        return len(self.all_paragraphs)
    
    def get_paragraph_by_loc(self, loc: str) -> Paragraph | None:
        """根据位置字符串获取段落"""
        for p in self.all_paragraphs:
            if p.loc == loc:
                return p
        return None


class Normalizer:
    """文档标准化器"""
    
    # Markdown 标题正则
    MD_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
    
    def __init__(self):
        self._paragraph_counter = 0
    
    def normalize(self, content: str, doc_id: str) -> NormalizedDoc:
        """
        标准化文档内容
        
        Args:
            content: 文档内容
            doc_id: 文档标识符
            
        Returns:
            NormalizedDoc: 标准化后的文档结构
        """
        self._paragraph_counter = 0
        
        # 检测格式
        doc_format = self._detect_format(content)
        
        if doc_format == DocFormat.MARKDOWN:
            return self._normalize_markdown(content, doc_id)
        else:
            return self._normalize_text(content, doc_id)
    
    def normalize_file(self, path: str | Path) -> NormalizedDoc:
        """
        从文件标准化文档
        
        Args:
            path: 文件路径
            
        Returns:
            NormalizedDoc: 标准化后的文档结构
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        
        if not path.is_file():
            raise ValueError(f"不是文件: {path}")
        
        content = path.read_text(encoding="utf-8")
        doc_id = path.stem  # 使用文件名作为 doc_id
        
        return self.normalize(content, doc_id)
    
    def normalize_directory(self, path: str | Path) -> list[NormalizedDoc]:
        """
        批量标准化目录下的所有文档
        
        Args:
            path: 目录路径
            
        Returns:
            list[NormalizedDoc]: 标准化后的文档列表
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")
        
        if not path.is_dir():
            raise ValueError(f"不是目录: {path}")
        
        docs = []
        for file_path in sorted(path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in (".md", ".txt", ".markdown"):
                try:
                    doc = self.normalize_file(file_path)
                    docs.append(doc)
                except Exception as e:
                    print(f"警告: 无法解析文件 {file_path}: {e}")
        
        return docs
    
    def _detect_format(self, content: str) -> DocFormat:
        """检测文档格式"""
        # 检查是否有 Markdown 标题（逐行检查）
        for line in content.split("\n"):
            if self.MD_HEADING_PATTERN.match(line):
                return DocFormat.MARKDOWN
        
        # 检查其他 Markdown 特征
        md_patterns = [
            r"\*\*.*\*\*",  # 粗体
            r"\*.*\*",  # 斜体
            r"\[.*\]\(.*\)",  # 链接
            r"^-\s+",  # 无序列表
            r"^\d+\.\s+",  # 有序列表
            r"^```",  # 代码块
        ]
        
        for pattern in md_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return DocFormat.MARKDOWN
        
        return DocFormat.TEXT
    
    def _normalize_markdown(self, content: str, doc_id: str) -> NormalizedDoc:
        """标准化 Markdown 文档"""
        lines = content.split("\n")
        sections: list[Section] = []
        all_paragraphs: list[Paragraph] = []
        
        # 使用栈来跟踪章节层级
        section_stack: list[Section] = []
        current_paragraph_lines: list[str] = []
        current_paragraph_start = 1
        doc_title: str | None = None
        
        for line_num, line in enumerate(lines, start=1):
            heading_match = self.MD_HEADING_PATTERN.match(line)
            
            if heading_match:
                # 先保存之前的段落
                if current_paragraph_lines:
                    para = self._create_paragraph(
                        current_paragraph_lines,
                        section_stack,
                        current_paragraph_start,
                        line_num - 1
                    )
                    if para:
                        all_paragraphs.append(para)
                        if section_stack:
                            section_stack[-1].paragraphs.append(para)
                    current_paragraph_lines = []
                
                # 处理标题
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 第一个 H1 作为文档标题
                if level == 1 and doc_title is None:
                    doc_title = title
                
                # 构建章节路径
                path = self._build_section_path(section_stack, level, title)
                
                section = Section(
                    level=level,
                    title=title,
                    path=path,
                    start_line=line_num
                )
                
                # 更新章节栈
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                
                if section_stack:
                    section_stack[-1].subsections.append(section)
                else:
                    sections.append(section)
                
                section_stack.append(section)
                current_paragraph_start = line_num + 1
                
            else:
                # 累积段落内容
                stripped = line.strip()
                
                # 空行分隔段落
                if not stripped:
                    if current_paragraph_lines:
                        para = self._create_paragraph(
                            current_paragraph_lines,
                            section_stack,
                            current_paragraph_start,
                            line_num - 1
                        )
                        if para:
                            all_paragraphs.append(para)
                            if section_stack:
                                section_stack[-1].paragraphs.append(para)
                        current_paragraph_lines = []
                    current_paragraph_start = line_num + 1
                else:
                    current_paragraph_lines.append(line)
        
        # 处理最后一个段落
        if current_paragraph_lines:
            para = self._create_paragraph(
                current_paragraph_lines,
                section_stack,
                current_paragraph_start,
                len(lines)
            )
            if para:
                all_paragraphs.append(para)
                if section_stack:
                    section_stack[-1].paragraphs.append(para)
        
        return NormalizedDoc(
            doc_id=doc_id,
            format=DocFormat.MARKDOWN,
            title=doc_title,
            raw_content=content,
            sections=sections,
            all_paragraphs=all_paragraphs
        )
    
    def _normalize_text(self, content: str, doc_id: str) -> NormalizedDoc:
        """标准化纯文本文档"""
        lines = content.split("\n")
        all_paragraphs: list[Paragraph] = []
        
        current_paragraph_lines: list[str] = []
        current_paragraph_start = 1
        
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            if not stripped:
                if current_paragraph_lines:
                    self._paragraph_counter += 1
                    para = Paragraph(
                        index=self._paragraph_counter,
                        content="\n".join(current_paragraph_lines),
                        section_path="文档正文",
                        start_line=current_paragraph_start,
                        end_line=line_num - 1
                    )
                    all_paragraphs.append(para)
                    current_paragraph_lines = []
                current_paragraph_start = line_num + 1
            else:
                current_paragraph_lines.append(line)
        
        # 处理最后一个段落
        if current_paragraph_lines:
            self._paragraph_counter += 1
            para = Paragraph(
                index=self._paragraph_counter,
                content="\n".join(current_paragraph_lines),
                section_path="文档正文",
                start_line=current_paragraph_start,
                end_line=len(lines)
            )
            all_paragraphs.append(para)
        
        return NormalizedDoc(
            doc_id=doc_id,
            format=DocFormat.TEXT,
            title=None,
            raw_content=content,
            sections=[],
            all_paragraphs=all_paragraphs
        )
    
    def _build_section_path(
        self, 
        section_stack: list[Section], 
        level: int, 
        title: str
    ) -> str:
        """构建章节路径"""
        # 获取父级路径
        parent_parts = []
        for s in section_stack:
            if s.level < level:
                parent_parts.append(f"H{s.level}: {s.title}")
        
        current_part = f"H{level}: {title}"
        
        if parent_parts:
            return " > ".join(parent_parts) + " > " + current_part
        return current_part
    
    def _create_paragraph(
        self,
        lines: list[str],
        section_stack: list[Section],
        start_line: int,
        end_line: int
    ) -> Paragraph | None:
        """创建段落对象"""
        content = "\n".join(lines).strip()
        
        # 跳过空内容和纯分隔线
        if not content or content == "---" or all(c == "-" for c in content):
            return None
        
        self._paragraph_counter += 1
        
        # 获取章节路径
        if section_stack:
            section_path = section_stack[-1].path
        else:
            section_path = "文档开头"
        
        return Paragraph(
            index=self._paragraph_counter,
            content=content,
            section_path=section_path,
            start_line=start_line,
            end_line=end_line
        )
