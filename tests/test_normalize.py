"""
Normalize 模块单元测试
"""

import pytest
from doc2spec.modules.normalize import Normalizer, DocFormat


class TestNormalizer:
    """Normalizer 测试"""
    
    def test_detect_markdown(self):
        """测试 Markdown 格式检测"""
        normalizer = Normalizer()
        
        md_content = """# 标题
这是内容
## 二级标题
更多内容
"""
        doc = normalizer.normalize(md_content, "test")
        assert doc.format == DocFormat.MARKDOWN
    
    def test_detect_text(self):
        """测试纯文本格式检测"""
        normalizer = Normalizer()
        
        text_content = """这是一段纯文本
没有任何 Markdown 语法
只是普通的文字"""
        
        doc = normalizer.normalize(text_content, "test")
        assert doc.format == DocFormat.TEXT
    
    def test_parse_markdown_sections(self):
        """测试 Markdown 章节解析"""
        normalizer = Normalizer()
        
        content = """# 一级标题

第一段内容

## 二级标题A

A的内容

## 二级标题B

B的内容
"""
        doc = normalizer.normalize(content, "test")
        
        assert doc.title == "一级标题"
        assert len(doc.sections) >= 1
        assert len(doc.all_paragraphs) >= 3
    
    def test_paragraph_loc(self):
        """测试段落位置信息"""
        normalizer = Normalizer()
        
        content = """# 功能说明

这是第一段

这是第二段
"""
        doc = normalizer.normalize(content, "test")
        
        for para in doc.all_paragraphs:
            assert para.loc is not None
            assert "P" in para.loc
    
    def test_section_path(self):
        """测试章节路径"""
        normalizer = Normalizer()
        
        content = """# 顶级

## 二级

### 三级

内容
"""
        doc = normalizer.normalize(content, "test")
        
        # 最后一个段落应该有完整的章节路径
        if doc.all_paragraphs:
            last_para = doc.all_paragraphs[-1]
            assert "H1" in last_para.section_path or "H2" in last_para.section_path
    
    def test_empty_content(self):
        """测试空内容"""
        normalizer = Normalizer()
        doc = normalizer.normalize("", "empty")
        
        assert doc.doc_id == "empty"
        assert len(doc.all_paragraphs) == 0


class TestNormalizerFile:
    """文件操作测试"""
    
    def test_file_not_found(self):
        """测试文件不存在"""
        normalizer = Normalizer()
        
        with pytest.raises(FileNotFoundError):
            normalizer.normalize_file("/nonexistent/path/file.md")
