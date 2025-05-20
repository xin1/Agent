为了支持 `.doc` 和 `.docx` 文件，我们需要对以下两部分进行修改：

---

## ✅ 一、修改 `process.py`：统一处理 PDF、DOCX 和 DOC

### 安装依赖（如未安装）：

```bash
pip install python-docx pypandoc
```

> `pypandoc` 会调用系统中的 pandoc，因此你需要 [安装 pandoc](https://pandoc.org/installing.html)。

---

### 🔧 修改 `process.py` 支持多格式

```python
import os
import fitz  # PyMuPDF
import csv
import re
import tempfile
from uuid import uuid4
from docx import Document
import pypandoc

os.makedirs("outputs", exist_ok=True)

heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')  # 1 总则、1.1 标题

def extract_headings_and_content(text_lines):
    content_dict = {}
    current_heading = None

    for text in text_lines:
        text = text.strip()
        if not text:
            continue

        match = heading_pattern.match(text)
        if match:
            current_heading = f"{match.group(1)} {match.group(4).strip()}"
            content_dict[current_heading] = ""
        elif current_heading:
            content_dict[current_heading] += text + " "

    return content_dict

def process_pdf(file, top_cm, bottom_cm):
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    text_lines = []

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)
        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        for block in sorted_blocks:
            text_lines.append(block[4])

    return text_lines

def process_docx(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file.file.read())
        tmp.flush()
        doc = Document(tmp.name)

    text_lines = [p.text for p in doc.paragraphs if p.text.strip()]
    return text_lines

def convert_doc_to_docx(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp_doc:
        tmp_doc.write(file.file.read())
        tmp_doc.flush()
        docx_path = tmp_doc.name + ".docx"
        pypandoc.convert_file(tmp_doc.name, 'docx', outputfile=docx_path)
    return docx_path

def process_pdf_and_extract(file, top_cm=0, bottom_cm=0):
    filename = file.filename.rsplit('.', 1)[0]
    ext = file.filename.lower().split('.')[-1]

    if ext == "pdf":
        text_lines = process_pdf(file, top_cm, bottom_cm)
    elif ext == "docx":
        text_lines = process_docx(file)
    elif ext == "doc":
        docx_path = convert_doc_to_docx(file)
        doc = Document(docx_path)
        text_lines = [p.text for p in doc.paragraphs if p.text.strip()]
        os.remove(docx_path)  # 清理临时文件
    else:
        raise ValueError("Unsupported file type")

    content_dict = extract_headings_and_content(text_lines)
    csv_path = f"outputs/{uuid4().hex}_{filename}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path
```

---

## ✅ 二、修改 `app.py`：无需额外改动，只要 `process_pdf_and_extract` 能处理不同格式

`app.py` 中的 `/process_batch/` 会自动调用 `process_pdf_and_extract`，支持了 DOC、DOCX 后无需额外更改。

---

## ✅ 测试支持文件类型

你现在的系统支持：

* PDF 文件（原生）
* DOCX 文件（直接读取）
* DOC 文件（先转 DOCX，再处理）

---

是否需要我帮你一并修改 `preview.py` 支持 DOCX 或 DOC 预览（如转换为图像）？这会更复杂一些。
