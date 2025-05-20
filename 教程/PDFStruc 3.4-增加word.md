以下是完整整合的支持 `.doc`, `.docx`, `.pdf` 文件的结构化提取处理流程，包含：

1. 支持上传 `.doc/.docx/.pdf` 的前端页面
2. 后端 `app.py`，统一处理所有格式
3. `process.py`，处理 PDF 提取结构
4. `convert_doc.py`，Word 转 PDF 模块

---

### ✅ 目录结构建议

```
project/
├── app.py
├── convert_doc.py
├── process.py
├── preview.py
├── zip_util.py
├── static/
│   └── index.html
├── outputs/
└── uploads/
```

---

### ✅ convert\_doc.py（新增模块：Word 转 PDF）

```python
import os
import uuid
from docx import Document
import comtypes.client  # Windows 专用，确保安装 comtypes
from tempfile import NamedTemporaryFile

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_doc_to_pdf(input_file, suffix):
    if suffix == ".docx":
        output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.pdf")
        word = comtypes.client.CreateObject("Word.Application")
        doc = word.Documents.Open(input_file)
        doc.SaveAs(output_path, FileFormat=17)  # 17 是 PDF 格式
        doc.Close()
        word.Quit()
        return output_path
    elif suffix == ".doc":
        output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.pdf")
        word = comtypes.client.CreateObject("Word.Application")
        doc = word.Documents.Open(input_file)
        doc.SaveAs(output_path, FileFormat=17)
        doc.Close()
        word.Quit()
        return output_path
    return None
```

---

### ✅ process.py（处理 PDF 文件）

保持不变：

```python
# ...省略原代码
def process_pdf_and_extract(file, top_cm, bottom_cm):
    # file 可以是 UploadFile 或 文件路径（str）
    if isinstance(file, str):
        pdf = fitz.open(file)
        filename = os.path.splitext(os.path.basename(file))[0]
    else:
        pdf = fitz.open(stream=file.file.read(), filetype="pdf")
        filename = file.filename.rsplit('.', 1)[0]

    # ...保持原逻辑
```

---

### ✅ app.py（支持 doc/docx/pdf 自动处理）

```python
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import shutil
from process import process_pdf_and_extract
from convert_doc import convert_doc_to_pdf
from preview import generate_preview_image
from zip_util import zip_csvs

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

@app.get("/")
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

def save_upload_file(upload_file: UploadFile):
    temp_path = os.path.join("uploads", upload_file.filename)
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return temp_path

def convert_if_needed(upload_file: UploadFile):
    suffix = os.path.splitext(upload_file.filename)[1].lower()
    if suffix in [".doc", ".docx"]:
        saved_path = save_upload_file(upload_file)
        return convert_doc_to_pdf(saved_path, suffix)
    elif suffix == ".pdf":
        return upload_file
    else:
        raise ValueError("Unsupported file type")

@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    pdf_path_or_file = convert_if_needed(file)
    preview_path = generate_preview_image(pdf_path_or_file, top_cm, bottom_cm)
    return {"preview_path": preview_path}

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        pdf_path_or_file = convert_if_needed(file)
        csv_path = process_pdf_and_extract(pdf_path_or_file, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}

@app.get("/download/")
async def download(path: str):
    return FileResponse(path, filename=os.path.basename(path))
```

---

### ✅ static/index.html（更新文件选择器）

```html
<input id="fileInput" type="file" name="files" multiple accept=".pdf,.doc,.docx">
```

---

### 📌 注意事项

1. ✅ `comtypes` 仅支持 Windows，如需跨平台需用 LibreOffice 替代；
2. ✅ 确保机器安装了 Microsoft Word；
3. ✅ `uploads/` 用于临时保存上传的 Word 文件和转换后的 PDF；
4. ✅ 如果你部署在 Docker 中，请说明，我会帮你切换为 LibreOffice 转换方案。

---

是否需要我打包生成一份完整代码 zip，或进一步帮你部署成 Docker 项目？


非常好，保持职责单一是个好习惯。我们可以新建一个模块，比如：

```
convert_doc.py
```

专门负责将 `.doc`、`.docx` 文件转换为 `.pdf`，再由你的主处理逻辑统一处理 PDF。

---

## ✅ convert\_doc.py 示例代码

```python
import os
import tempfile
from pathlib import Path
from docx2pdf import convert
from uuid import uuid4
import shutil

os.makedirs("temp_uploads", exist_ok=True)

def save_upload_file(upload_file) -> str:
    """
    将 UploadFile 保存为临时本地文件，返回文件路径
    """
    temp_filename = f"{uuid4().hex}_{upload_file.filename}"
    temp_path = os.path.join("temp_uploads", temp_filename)
    with open(temp_path, "wb") as f:
        f.write(upload_file.file.read())
    return temp_path


def convert_word_to_pdf(doc_path: str) -> str:
    """
    将 Word 文件（.doc/.docx）转换为 PDF，返回 PDF 路径
    """
    output_dir = tempfile.mkdtemp()
    convert(doc_path, output_dir)
    
    # 找到转换后的 PDF 文件
    for f in Path(output_dir).glob("*.pdf"):
        pdf_temp_path = os.path.join("temp_uploads", f"{uuid4().hex}_{f.name}")
        shutil.move(str(f), pdf_temp_path)
        return pdf_temp_path

    raise RuntimeError("转换 Word 到 PDF 失败")
```

---

## ✅ 如何在 process.py 中使用

在 `process.py` 顶部引入：

```python
from convert_doc import save_upload_file, convert_word_to_pdf
```

然后在 `process_pdf_and_extract()` 中这样用：

```python
def process_pdf_and_extract(file, top_cm, bottom_cm):
    filename = file.filename
    suffix = filename.lower().split('.')[-1]

    # 保存文件
    local_path = save_upload_file(file)

    # 如果是 Word 文件，先转成 PDF
    if suffix in ["doc", "docx"]:
        try:
            local_path = convert_word_to_pdf(local_path)
        except Exception as e:
            raise RuntimeError(f"Word 转换失败: {str(e)}")

    # 打开 PDF 并处理
    pdf = fitz.open(local_path)
    ...
```

---

## ✅ 总结

你现在有了：

* `convert_doc.py`：负责文档保存与 Word 转 PDF
* `process.py`：负责 PDF 剪裁与内容结构提取

结构更清晰、职责更明确。是否需要我一并生成 `convert_doc.py` 文件？或者还想兼容 Linux 的转换方法？


以下是完整的支持 `.pdf`、`.docx` 和 `.doc` 文件的流程及相关代码模块，包括：

* `app.py`：主 FastAPI 接口
* `convert_doc.py`：将 Word 文档（doc/docx）转为 PDF
* `process.py`：结构化处理 PDF 内容并生成 CSV
* `preview.py`：生成 PDF 页面裁剪预览

---

### ✅ 1. `convert_doc.py`（新增：Word 转 PDF）

```python
import os
import uuid
from pathlib import Path

def convert_to_pdf(uploaded_file) -> str:
    from tempfile import NamedTemporaryFile
    from docx import Document
    import subprocess

    suffix = uploaded_file.filename.rsplit('.', 1)[-1].lower()
    tmp_dir = "temp_docs"
    os.makedirs(tmp_dir, exist_ok=True)

    with NamedTemporaryFile(delete=False, dir=tmp_dir, suffix=f".{suffix}") as temp_file:
        temp_file.write(uploaded_file.file.read())
        temp_file_path = temp_file.name

    if suffix == "docx":
        output_path = temp_file_path.replace(".docx", ".pdf")
        try:
            import docx2pdf
            docx2pdf.convert(temp_file_path, output_path)
        except Exception as e:
            raise RuntimeError(f"docx 转换失败: {e}")
    elif suffix == "doc":
        output_path = temp_file_path.replace(".doc", ".pdf")
        # 用 LibreOffice 转换 doc -> pdf
        result = subprocess.run([
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", tmp_dir, temp_file_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError("LibreOffice 转换 doc 失败：" + result.stderr.decode())
    else:
        raise ValueError("不支持的文件类型")

    return output_path
```

> ⚠️ Linux 上需安装 `libreoffice`，Windows 上推荐用 `docx2pdf`。确保 `.docx` 安装了 `docx2pdf`，`.doc` 则使用 LibreOffice。

---

### ✅ 2. `process.py`

```python
import os
import fitz  # PyMuPDF
import csv
import re
from uuid import uuid4

os.makedirs("outputs", exist_ok=True)

def process_pdf_and_extract(file_path, top_cm, bottom_cm):
    pdf = fitz.open(file_path)
    filename = os.path.basename(file_path).rsplit('.', 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{filename}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

        for block in sorted_blocks:
            text = block[4].strip()
            if not text:
                continue
            match = heading_pattern.match(text)
            if match:
                current_heading = f"{match.group(1)} {match.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path
```

---

### ✅ 3. `preview.py`

```python
import fitz  # PyMuPDF
import uuid
from convert_doc import convert_to_pdf

def generate_preview_image(file, top_cm, bottom_cm):
    suffix = file.filename.rsplit('.', 1)[-1].lower()
    if suffix in ['doc', 'docx']:
        file_path = convert_to_pdf(file)
    else:
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.file.read())
            file_path = tmp.name

    pdf = fitz.open(file_path)
    page = pdf.load_page(0)
    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(clip=clip)
    preview_path = f"outputs/{uuid.uuid4().hex}_preview.png"
    pix.save(preview_path)

    return preview_path
```

---

### ✅ 4. `app.py`

```python
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from preview import generate_preview_image
from convert_doc import convert_to_pdf
from process import process_pdf_and_extract
from zip_util import zip_csvs
import tempfile

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

@app.get("/")
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
    return {"preview_path": preview_path}

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext in ['pdf']:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.file.read())
                path = tmp.name
        elif ext in ['doc', 'docx']:
            path = convert_to_pdf(file)
        else:
            continue
        csv_path = process_pdf_and_extract(path, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}

@app.get("/download/")
async def download(path: str):
    return FileResponse(path, filename=os.path.basename(path))
```

---

### ✅ 补充说明：

1. 安装依赖（部分 Linux 可选）：

```bash
pip install python-docx docx2pdf pymupdf
sudo apt install libreoffice  # 处理 .doc 转换
```

2. 支持文件扩展：
   前端 `<input type="file">` 允许添加 `accept=".pdf,.doc,.docx"` 支持多格式选择。

---

如需我一起更新 `zip_util.py` 或 `index.html` 前端部分，也可以继续告诉我。
