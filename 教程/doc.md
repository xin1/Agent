```
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/starlette/responses.py", line 343, in __call__
    stat_result = await anyio.to_thread.run_sync(os.stat, self.path)
  File "/usr/local/lib/python3.9/site-packages/anyio/to_thread.py", line 56, in run_sync
    return await get_async_backend().run_sync_in_worker_thread(
  File "/usr/local/lib/python3.9/site-packages/anyio/_backends/_asyncio.py", line 2470, in run_sync_in_worker_thread
    return await future
  File "/usr/local/lib/python3.9/site-packages/anyio/_backends/_asyncio.py", line 967, in run
    result = context.run(func, *args)
FileNotFoundError: [Errno 2] No such file or directory: 'outputs/FusionOS 23.1.3安装BF3驱动'
```
是的，预览也需要加上对 Word 文档的转换，思路和批量处理保持一致：先把 `.doc/.docx` 转成临时 PDF，再传给 `generate_preview_image`。下面给出最小化的改动，只改 `app.py` 的 `/preview/` 路由，和（可选）微调 `preview.py` 以接受文件路径：

---

### 1. 在 `app.py` 的头部引入转换函数

```python
from convert_doc import convert_doc_to_pdf
```

### 2. 修改 `/preview/` 接口

把原来的

```python
@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
    return {"preview_path": preview_path}
```

替换为

```python
@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    # 如果是 Word，先转 PDF
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext in ("doc", "docx"):
        # convert_doc_to_pdf 会保存临时 PDF 并返回路径
        pdf_path = convert_doc_to_pdf(file)
        # 打开转换后的文件作为二进制流
        with open(pdf_path, "rb") as f:
            preview_path = generate_preview_image(f, top_cm, bottom_cm)
    else:
        preview_path = generate_preview_image(file, top_cm, bottom_cm)

    return {"preview_path": preview_path}
```

这样：

* **PDF** 文件直接走原逻辑；
* **Word** 文件先用 LibreOffice 转为 PDF，再生成预览图。

---

### 3. （可选）微调 `preview.py` 接口签名

如果你希望 `generate_preview_image` 接受一个文件路径而不是 `UploadFile`，也可以把它改成：

```python
def generate_preview_image(file_or_path, top_cm, bottom_cm):
    os.makedirs("outputs", exist_ok=True)
    # 支持传入路径或 UploadFile
    if isinstance(file_or_path, str):
        pdf = fitz.open(file_or_path)
    else:
        pdf = fitz.open(stream=file_or_path.read(), filetype="pdf")
    ...
```

但其实不改也没问题——我们在上面已经把 Word 的流换成了文件流。

---

完成以上改动后，前端“预览”按钮就能同时预览 PDF 和 Word 文件（转成 PDF 后的片段）了。

下面给出最小化的改动方案，只更新或新增几个文件、几段代码，不用全部重写。

---

## 1. 安装 LibreOffice 与中文字体（修改 `Dockerfile`）

在你的 `Dockerfile` 中，找到安装依赖的地方，替换为下面内容：

```dockerfile
FROM python:3.10-slim

# 开启 UTF-8 环境，安装 LibreOffice 及字体
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update && \
    apt-get install -y libreoffice fonts-noto-cjk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **说明**：
>
> * `libreoffice` 用于 Word→PDF 转换；
> * `fonts-noto-cjk` 解决中文渲染和提取乱码；
> * 保留原有 Python 依赖安装。

---

## 2. 新增 Word→PDF 转换模块 `convert_doc.py`

在项目根或 `app/` 目录下新建 `convert_doc.py`，内容如下：

```python
import subprocess
import os
import tempfile

def convert_doc_to_pdf(uploaded_file) -> str:
    """
    接收 UploadFile，保存到临时文件，再调用 LibreOffice 转 PDF，
    返回生成的 PDF 路径。
    """
    # 保存上传的 Word 文件到临时目录
    suffix = os.path.splitext(uploaded_file.filename)[1].lower()
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, uploaded_file.filename)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.file.read())

    # 调用 libreoffice CLI 转 PDF
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)

    # 返回 PDF 路径
    output_pdf = os.path.join(tmp_dir, os.path.splitext(uploaded_file.filename)[0] + ".pdf")
    if not os.path.exists(output_pdf):
        raise RuntimeError(f"Failed to convert {uploaded_file.filename} to PDF")
    return output_pdf
```

---

## 3. 修改 `process.py`：接入转换逻辑

在文件开头 `import` 区域下方添加：

```python
from convert_doc import convert_doc_to_pdf
```

然后把原来的 `process_pdf_and_extract(file, ...)` 函数改成以下形式，只在开头多处理 Word 文档，后续不变：

```python
def process_pdf_and_extract(file, top_cm, bottom_cm):
    # —— 新增：如果是 .doc/.docx，先转换为 PDF ——  
    filename = file.filename
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ("doc", "docx"):
        pdf_path = convert_doc_to_pdf(file)
        # 打开转换后的 PDF
        pdf = fitz.open(pdf_path)
    else:
        # 直接打开上传的 PDF 流
        pdf = fitz.open(stream=file.file.read(), filetype="pdf")

    # 原来的剪裁 + 提取逻辑不变
    base = filename.rsplit(".", 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{base}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)
        for b in sorted(blocks, key=lambda b: (b[1], b[0])):
            text = b[4].strip()
            if not text: continue
            m = heading_pattern.match(text)
            if m:
                current_heading = f"{m.group(1)} {m.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    # UTF-8 BOM 写入，防止乱码
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for h, c in content_dict.items():
            writer.writerow([h, c.strip()])

    return csv_path
```

> **说明**：
>
> * `.doc/.docx` 上传后调用 `convert_doc_to_pdf` 得到 PDF 文件路径；
> * 直接读取流的部分保留。

---

## 4. 修改 `app.py`：处理多文件时也支持 Word

在 `from process import ...` 之下加上引入转换模块（可选）：

```python
from convert_doc import convert_doc_to_pdf
```

然后把 `/process_batch/` 接口里的循环改为：

```python
@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        # 直接调用原有函数即可，process_pdf_and_extract 已处理 Word
        csv_path = process_pdf_and_extract(file, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    # 其余不变……
```

预览接口 `/preview/` 保持处理 PDF 流即可；如果想也支持 Word 预览，可以同样转换后再调用 `generate_preview_image`。

---

## 5. 更新 `requirements.txt`

在末尾补充（若尚未添加）：

```txt
# LibreOffice CLI 已由系统安装，这里只需 Python 库
# 无需额外 Python 包
```

无需额外 pip 库改动，只要 `convert_doc.py` 不依赖新包。

---

## 6. 重建并测试

```bash
docker build -t pdfstruc_v3.4 .
docker run -p 8000:8000 pdfstruc_v3.4
```

* 在前端上传 `.docx` 或 `.doc`：会后台自动转 PDF → 剪裁 → 提取 → 返回 CSV。
* 原有上传 PDF 流程未经更改。

---

这样，你只需新增一个模块 `convert_doc.py`、改动 `process.py` 的开头，以及调整 `Dockerfile` 安装 LibreOffice，即可 **无缝集成 Word 转 PDF**，保留所有现有的裁剪预览和 CSV 提取功能。
