"""
Word文档导出模块
将Markdown计算书转换为Word格式
"""
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re


def create_word_report(md_text: str) -> bytes:
    """将 Markdown 计算书转换为 Word 二进制流"""
    doc = Document()

    # 设置全文字体样式
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading('自承式管线桥结构设计计算书', 0)

    lines = md_text.split('\n')
    in_table = False
    table_data = []

    def flush_table():
        nonlocal in_table, table_data
        if table_data:
            # 清理 Markdown 表格分隔符
            valid_rows = [r for r in table_data if not re.match(r'^[\s\|-]*$', r)]
            if valid_rows:
                try:
                    col_count = len([c for c in valid_rows[0].split('|') if c.strip()])
                    table = doc.add_table(rows=len(valid_rows), cols=col_count)
                    table.style = 'Table Grid'
                    for i, row in enumerate(valid_rows):
                        cols = [c.strip() for c in row.split('|')[1:-1]]
                        for j, text in enumerate(cols):
                            if j < col_count:
                                table.cell(i, j).text = text
                except:
                    pass
            table_data = []
        in_table = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 处理表格
        if line.startswith('|'):
            in_table = True
            table_data.append(line)
            continue
        else:
            if in_table:
                flush_table()

        # 处理标题
        if line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=1)
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=2)
        elif line.startswith('* **') or line.startswith('- **'):
            clean_text = line.replace('* **', '').replace('- **', '').replace('**', '')
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(clean_text)
        else:
            # 普通段落，清洗基础Markdown符号
            clean_text = line.replace('**', '').replace('$', '').replace('\\', '')
            if clean_text:
                doc.add_paragraph(clean_text)

    if in_table:
        flush_table()

    # 将文档保存到内存字节流
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
