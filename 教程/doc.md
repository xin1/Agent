请用下面的完整版 `preview.py`（覆盖原文件），它能够兼容三种输入类型：

* 字符串路径（转换后的 PDF 文件）
* FastAPI 的 `UploadFile`
* 任何带 `.read()` 方法的二进制流（例如 `open(..., "rb")`）

并确保在 `app.py` 的 `/preview/` 路由中直接传入路径或 `UploadFile`，而 **不再** 对文件做 `open()`，这样就不会出现 `BufferedReader` 没有 `.file` 的问题。

---

### 完整替换：`preview.py`

```python
import fitz
from uuid import uuid4
import os
from fastapi import UploadFile

def generate_preview_image(source, top_cm: float, bottom_cm: float) -> str:
    """
    source: 
      - UploadFile      （file.file.read() 可用）
      - str             （PDF 文件路径）
      - 文件二进制流对象（.read() 可用，如 open(..., "rb")）
    返回：生成的预览 PNG 相对路径
    """
    os.makedirs("outputs", exist_ok=True)

    # 打开 PDF
    if isinstance(source, str):
        pdf = fitz.open(source)
    elif isinstance(source, UploadFile):
        data = source.file.read()
        pdf = fitz.open(stream=data, filetype="pdf")
    else:
        # 任何有 .read() 方法的流
        data = source.read()
        pdf = fitz.open(stream=data, filetype="pdf")

    # 取第一页
    page = pdf.load_page(0)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_filename = f"{uuid4().hex}_preview.png"
    preview_path = os.path.join("outputs", preview_filename)
    pix.save(preview_path)

    return preview_path
```

---

### 修改 `/preview/` 路由：`app.py`

找到 `app.py` 中的 `/preview/`，改成这样——注意 **不使用** `open()`, 直接传路径或 `UploadFile`:

```python
from convert_doc import convert_doc_to_pdf
from preview import generate_preview_image

@app.post("/preview/")
async def preview(
    file: UploadFile = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext in ("doc", "docx"):
        # Word 先转换为 PDF，得到文件路径
        pdf_path = convert_doc_to_pdf(file)
        # 直接传路径给 generate_preview_image
        preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
    else:
        # 对 PDF 上传文件，直接传 UploadFile
        preview_path = generate_preview_image(file, top_cm, bottom_cm)

    return {"preview_path": preview_path}
```

---

完成上述两处：

1. **覆盖 `preview.py`**
2. **更新 `app.py` 中的 `/preview/` 处理**

然后重建并运行容器，你就能对 `.doc/.docx` 和 `.pdf` 文件正常生成预览了。



```
INFO:     192.168.65.1:18770 - "GET / HTTP/1.1" 200 OK
convert /tmp/tmpuhxmh7bp/imm领料指导书.docx -> /tmp/tmpuhxmh7bp/imm领料指导书.pdf using filter : writer_pdf_Export
INFO:     192.168.65.1:22621 - "POST /preview/ HTTP/1.1" 500 Internal Server Error
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/uvicorn/protocols/http/h11_impl.py", line 403, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
  File "/usr/local/lib/python3.9/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/fastapi/applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/errors.py", line 187, in __call__
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/middleware/exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/usr/local/lib/python3.9/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/usr/local/lib/python3.9/site-packages/starlette/routing.py", line 73, in app
    response = await f(request)
  File "/usr/local/lib/python3.9/site-packages/fastapi/routing.py", line 301, in app
    raw_response = await run_endpoint_function(
  File "/usr/local/lib/python3.9/site-packages/fastapi/routing.py", line 212, in run_endpoint_function
    return await dependant.call(**values)
  File "/app/app.py", line 35, in preview
    preview_path = generate_preview_image(f, top_cm, bottom_cm)
  File "/app/preview.py", line 7, in generate_preview_image
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
AttributeError: '_io.BufferedReader' object has no attribute 'file'
```

此时 `f` 是一个 \_io.BufferedReader，没有 `.file` 属性，而你在 `generate_preview_image` 里写的是 `source.file.read()`。最简单也是最干净的做法是：

1. **不要在路由里 open() 再传文件对象**，而是直接把字符串路径传给 `generate_preview_image`；
2. **让 `generate_preview_image` 同时兼容“UploadFile”、“文件路径”** 和\*\*“任意文件流”\*\* 三种情况。

---

## 具体修改步骤

### 1. `preview.py`：更新 `generate_preview_image`

把原来的实现删掉，替换为下面这个：

```python
import fitz
from uuid import uuid4
import os
from fastapi import UploadFile

def generate_preview_image(source, top_cm, bottom_cm):
    """
    source: UploadFile | 文件路径(str) | bytes 流(二进制)
    """
    os.makedirs("outputs", exist_ok=True)

    # 1) 根据类型打开 PDF
    if isinstance(source, str):
        # 文件路径
        pdf = fitz.open(source)
    elif isinstance(source, UploadFile):
        # FastAPI 上传文件
        pdf = fitz.open(stream=source.file.read(), filetype="pdf")
    else:
        # 假设是 open(..., "rb") 或者 bytes
        # 如果是 BufferedReader，则 .read() 也能用
        data = source.read() if hasattr(source, "read") else source
        pdf = fitz.open(stream=data, filetype="pdf")

    # 2) 典型做法：预览第一页
    page = pdf.load_page(0)

    # 3) 裁剪坐标
    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    # 4) 渲染并保存
    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_path = f"outputs/{uuid4().hex}_preview.png"
    pix.save(preview_path)

    return preview_path
```

> 这样，无论你传入的是路径、`UploadFile` 还是已经 `open()` 的文件流，它都能正确处理。

---

### 2. `app.py`：调整 `/preview/` 调用

把这一段：

```python
if ext in ("doc", "docx"):
    pdf_path = convert_doc_to_pdf(file)
    with open(pdf_path, "rb") as f:
        preview_path = generate_preview_image(f, top_cm, bottom_cm)
else:
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
```

改为 **直接** 传路径或 `UploadFile`：

```python
if ext in ("doc", "docx"):
    # 转出来的 PDF 是路径
    pdf_path = convert_doc_to_pdf(file)
    preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
else:
    # 直接传 UploadFile
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
```

---

### 3. 重建并测试

```bash
docker build -t pdfstruc:v3.5 .
docker run -p 8000:8000 pdfstruc:v3.5
```

* 对 **.doc/.docx** 点击“预览剪裁”，后台会先转 PDF（路径），再生成预览图；
* 对 **.pdf** 文件，直接用上传流生成预览。

这样就彻底避免了 `_io.BufferedReader` 没有 `.file` 的问题，也让预览功能在所有格式上一致可用。

你不需要把整个 `convert_doc.py` 重写，只要在它里对上传文件名做一次 “清洗”，把空格、`&`、`/` 等字符替换掉，就能让 LibreOffice CLI 正常工作，也方便后续路径处理。下面是改动示例。

---

### 原 `convert_doc.py`

```python
def convert_doc_to_pdf(uploaded_file) -> str:
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, uploaded_file.filename)
    ...
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)
    output_pdf = os.path.join(tmp_dir,
                              os.path.splitext(uploaded_file.filename)[0] + ".pdf")
    return output_pdf
```

---

### 修改后（带文件名清洗）

```python
import os
import re
import subprocess
import tempfile

def convert_doc_to_pdf(uploaded_file) -> str:
    """
    把上传的 .doc/.docx 文件保存到临时目录，先给它一个“安全”不含空格/特殊字符的名字，
    再用 LibreOffice 转 PDF，返回转换后的 PDF 路径。
    """
    # 1) 清洗文件名（去掉空格、&、/，替换为下划线）
    raw = os.path.splitext(uploaded_file.filename)[0]
    safe_stem = re.sub(r'[ \t/&\\\\]+', '_', raw)
    ext = os.path.splitext(uploaded_file.filename)[1]  # 包含“.”的后缀

    # 2) 准备临时目录和文件路径
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, safe_stem + ext)

    # 3) 写入上传内容
    with open(input_path, "wb") as f:
        f.write(uploaded_file.file.read())

    # 4) 调用 LibreOffice CLI 转 PDF
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)

    # 5) 输出 PDF 文件路径（同样用 safe_stem）
    output_pdf = os.path.join(tmp_dir, safe_stem + ".pdf")
    if not os.path.exists(output_pdf):
        raise RuntimeError(f"File at path {output_pdf} does not exist.")
    return output_pdf
```

**改动要点**：

1. **清洗 `uploaded_file.filename`**，生成 `safe_stem`，去除空格和 `&` 等特殊字符；
2. 保存和转换时使用 `safe_stem + ext`，保证 LibreOffice 能正确处理文件；
3. 输出 PDF 也用同样的 `safe_stem`，后续取预览或提取都不会再遇到路径解析问题。

完成这一改动，重建镜像后所有带空格或特殊字符的 Word 文档都能正常转换、预览和提取了。

在你贴的日志里，真正的错误是：你生成的 `csv_path` 里含有 **空格** 和 **`&`**，导致后续文件查找不到：

```
outputs/FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.csv
```

但 `os.path.exists` 自然找不到这种名字（同时浏览器又 URL 编码得不靠谱），所以报 `File at path ... does not exist`。

---

### 核心思路

* **把原始文件名做一次 “清洗”**（sanitize），把空格、`&`、`/` 等不安全字符替换成下划线或减号；
* 生成的文件名再拼接到 `outputs/` 下，就一定能读写到了。

---

## 1. 修改 `process.py`

在文件开头 `import` 区域，确保有：

```python
import os
import re
import fitz
import csv
from uuid import uuid4
```

然后把你的 `process_pdf_and_extract` 里的这一段：

```python
    # 原来的剪裁 + 提取逻辑不变
    base = filename.rsplit(".", 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{base}.csv"
```

**替换为**：

```python
    # —— 清洗文件名：去掉空格、&、/ 等，并用下划线代替 ——  
    raw = filename.rsplit(".", 1)[0]
    safe = re.sub(r'[ \t/&\\\\]+', '_', raw)  # 空格、制表符、/ 和 & 全部替换
    # 确保 outputs 目录存在
    os.makedirs("outputs", exist_ok=True)
    csv_path = os.path.join("outputs", f"{uuid4().hex}_{safe}.csv")
```

这样，无论上传文件叫啥，你最终在 `outputs/` 里看到的就都是类似：

```
outputs/5f8c9ab2_FusionOS_23.1.3安装BF3驱动_Nvqual测试指导书V1.0-zhangfeng_20250412.csv
```

---

## 2. 对 `/download/` 接口的 URL 编码（前端已做，但后端也可以更健壮）

当前你的前端是：

```js
csvLink.href = `/download/?path=${encodeURIComponent(res.path)}`;
```

后端可以继续保留原先逻辑，FastAPI 会自动 URL 解码。只要 `res.path`（也就是 `csv_path` ）里没有空格和特殊字符，就不会再解析错误。

---

## 3. （可选）日志打印调试

如果你想在后台确认文件确实存在，可以临时在 `app.py` 的 `download` 里加：

```python
@app.get("/download/")
async def download(path: str):
    print("Download requested for:", path, "exists?", os.path.exists(path))
    return FileResponse(path, filename=os.path.basename(path))
```

重启后看控制台，会告诉你到底哪个路径不存在。

---

完成以上 **文件名清洗** 改动，重新构建并重启服务：

```bash
docker build -t pdfstruc:v3 .
docker run -p 8000:8000 pdfstruc:v3
```

之后再试：

1. 上传 `FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.docx`；
2. 从前端下载 CSV 链接，应该能成功拿到 `outputs/<uuid>_FusionOS_23.1.3安装BF3驱动_Nvqual测试指导书V1.0-zhangfeng_20250412.csv`。

这样就彻底解决 “找不到文件” 的问题了。

要让预览也支持 Word 文档，最好把 `generate_preview_image` 做两方面改造：

1. **让它能接收 PDF 文件路径**（而不是只接收 `UploadFile` 流）；
2. 在 `/preview/` 路由里，对 `.doc/.docx` 先转换，然后再把路径交给它。

下面是精准的改动步骤。

---

## 1. 修改 `preview.py`

把原来的

```python
import fitz
from uuid import uuid4
import os

def generate_preview_image(file, top_cm, bottom_cm):
    os.makedirs("outputs", exist_ok=True)
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    page = pdf.load_page(2)
    ...
```

替换为：

```python
import fitz
from uuid import uuid4
import os

def generate_preview_image(source, top_cm, bottom_cm):
    """
    source: 要么是 UploadFile，要么是 PDF 文件路径字符串
    """
    os.makedirs("outputs", exist_ok=True)

    # 1) 打开 PDF
    if isinstance(source, str):
        pdf = fitz.open(source)
    else:
        pdf = fitz.open(stream=source.file.read(), filetype="pdf")

    # 2) 取第 1 页（或你要的页数）
    page = pdf.load_page(0)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_path = f"outputs/{uuid4().hex}_preview.png"
    pix.save(preview_path)
    return preview_path
```

> **要点：**
>
> * 传入字符串时直接 `fitz.open(path)`；
> * 传入 `UploadFile` 时保持原逻辑。

---

## 2. 修改 `app.py` 的 `/preview/` 路由

在文件顶部加入：

```python
from convert_doc import convert_doc_to_pdf
```

然后把 `/preview/` 改为：

```python
@app.post("/preview/")
async def preview(
    file: UploadFile = File(...),
    top_cm: float = Form(...),
    bottom_cm: float = Form(...)
):
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext in ("doc", "docx"):
        # 先转换成 PDF，得到临时路径
        pdf_path = convert_doc_to_pdf(file)
        # 直接用路径调用预览
        preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
    else:
        # PDF 直接走流
        preview_path = generate_preview_image(file, top_cm, bottom_cm)

    return {"preview_path": preview_path}
```

> **注意：** `convert_doc_to_pdf` 需要返回文件路径（字符串），不是 `UploadFile`。

---

### 重启测试

1. 重新构建镜像：

   ```bash
   docker build -t pdfstruc:v3 .
   ```
2. 启动容器并打开页面。
3. 试上传一个 `.docx` 或 `.doc`，点“预览剪裁”，应该在右侧显示生成的 PNG。

这样就能保证 **PDF** 和 **Word** 都能生成预览了。

```
RuntimeError: File at path outputs/FusionOS 23.1.3安装BF3驱动 does not exist.
convert /tmp/tmpjzyi5xil/FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.docx -> /tmp/tmpjzyi5xil/FusionOS 23.1.3安装BF3驱动&Nvqual测试指导书V1.0-zhangfeng_20250412.pdf using filter : writer_pdf_Export
INFO:     192.168.65.1:52855 - "POST /process_batch/ HTTP/1.1" 200 OK
INFO:     192.168.65.1:52855 - "GET /download/?path=outputs/FusionOS%2023.1.3%E5%AE%89%E8%A3%85BF3%E9%A9%B1%E5%8A%A8&Nvqual%E6%B5%8B%E8%AF%95%E6%8C%87%E5%AF%BC%E4%B9%A6V1.0-zhangfeng_20250412.csv HTTP/1.1" 500 Internal Server Error
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
