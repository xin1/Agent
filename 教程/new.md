# 10
为了支持多个文件上传并且每个文件使用不同的裁剪参数（`top_cm` / `bottom_cm`），且**尽可能不改动现有结构**，你需要做以下修改：

---

## ✅ **前端修改方式**

### 如果你使用的是原生 HTML + JS（未使用框架），那么上传多个文件和多个参数的方法如下：

```html
<form id="previewForm" enctype="multipart/form-data" method="post">
  <input type="file" name="files" multiple>

  <div id="params">
    <!-- 动态生成参数对 -->
    <div>
      <input type="number" step="0.1" name="top_cm" placeholder="Top(cm)">
      <input type="number" step="0.1" name="bottom_cm" placeholder="Bottom(cm)">
    </div>
  </div>

  <button type="submit">生成预览</button>
</form>

<script>
document.getElementById("previewForm").addEventListener("submit", async function(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData();

  const files = form.querySelector('input[name="files"]').files;
  const topCmList = form.querySelectorAll('input[name="top_cm"]');
  const bottomCmList = form.querySelectorAll('input[name="bottom_cm"]');

  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
    formData.append("top_cm_list", topCmList[i].value);
    formData.append("bottom_cm_list", bottomCmList[i].value);
  }

  const response = await fetch("/preview/", {
    method: "POST",
    body: formData
  });

  const result = await response.json();
  console.log(result);
});
</script>
```

> 每个文件配一个 top\_cm 和 bottom\_cm 输入框即可。你可以用 JS 动态生成这些输入框。

---

## ✅ **后端 FastAPI 修改（预览接口）**

### 文件：`preview.py`

```python
from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Union
from convert_doc import convert_doc_to_pdf
from process import generate_preview_image

router = APIRouter()

@router.post("/preview/")
async def preview_multiple(
    files: List[UploadFile] = File(...),
    top_cm_list: List[float] = Form(...),
    bottom_cm_list: List[float] = Form(...)
):
    """
    同时预览多个文件，每个文件对应一个裁剪参数
    """
    results = []

    for i, file in enumerate(files):
        top_cm = top_cm_list[i]
        bottom_cm = bottom_cm_list[i]
        ext = file.filename.rsplit(".", 1)[-1].lower()

        if ext in ("doc", "docx"):
            pdf_path = convert_doc_to_pdf(file)
            preview_path = generate_preview_image(pdf_path, top_cm, bottom_cm)
        else:
            preview_path = generate_preview_image(file, top_cm, bottom_cm)

        results.append({
            "filename": file.filename,
            "preview_path": preview_path
        })

    return {"previews": results}
```

---

## ✅ `convert_doc.py`：无需改动

你已有的 `convert_doc_to_pdf` 函数逻辑是可以复用的。

---

## ✅ `process.py`：无需修改

你的 `generate_preview_image()` 函数本身就支持单个文件的处理。多个文件的支持是由 `preview.py` 的循环实现的。

---

### ✅ 最终总结

| 部分               | 是否需要修改 | 说明                                      |
| ---------------- | ------ | --------------------------------------- |
| 前端 HTML / JS     | ✅      | 使用 FormData 传多个文件和参数数组                  |
| `preview.py`     | ✅      | 修改为支持 `List[UploadFile]`, `List[float]` |
| `convert_doc.py` | ❌      | 保持不变                                    |
| `process.py`     | ❌      | 保持不变                                    |

如你确认你使用的是某个框架（如 Vue、React 或 Bootstrap Template），也可以告诉我，我能针对性提供前端代码。是否需要我将整个项目结构或 Docker 也一起更新？

# 9
```
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

    # 取第4页
    page = pdf.load_page(3)

    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    preview_filename = f"{uuid4().hex}_preview.png"
    preview_path = os.path.join("outputs", preview_filename)
    pix.save(preview_path)

    return preview_path

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

import os
import fitz  # PyMuPDF
import csv
import re
from uuid import uuid4

os.makedirs("outputs", exist_ok=True)

def process_pdf_and_extract(file, top_cm, bottom_cm):
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    filename = file.filename.rsplit('.', 1)[0]
    csv_path = f"outputs/{filename}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')  # 1 总则、1.1 标题
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))  # 从上到下排序

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

    # ✅ 写入 CSV：使用 utf-8-sig 编码防止乱码
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # writer.writerow(["标题", "内容"])
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path

```
# 8
为了实现“**多个文件预览切换功能**”，你需要：

* **记录当前预览的是哪个文件**
* 使用左右箭头按钮来切换预览的文件（即不同文件的第一页截图）
* 每当切换时，更新右侧 `<img id="preview-img">` 的 `src` 来源

---

### ✅ 前端功能实现方案如下：

#### 🔧 1. HTML 中添加左右按钮

在 `<div class="right-panel">` 中的 `#preview-container` 旁边加入左右按钮（Font Awesome 的箭头图标）：

```html
<div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
  <button class="btn btn-secondary" onclick="prevPreview()"><i class="fas fa-arrow-left"></i></button>
  <div id="preview-container">
    <img id="preview-img" src="" alt="预览图像">
    <p id="preview-file-name" style="margin-top: 8px; color: #666;"></p>
  </div>
  <button class="btn btn-secondary" onclick="nextPreview()"><i class="fas fa-arrow-right"></i></button>
</div>
```

---

#### 🧠 2. JavaScript 脚本逻辑：管理当前预览索引

在 `<script>` 标签或外部 JS 文件中添加以下逻辑：

```html
<script>
let previewImages = [];  // 存储所有上传文件对应的预览图路径
let previewFileNames = [];
let currentPreviewIndex = 0;

function previewPDF() {
  const input = document.getElementById('pdf-input');
  const files = input.files;
  if (!files || files.length === 0) return;

  previewImages = [];
  previewFileNames = [];

  for (let i = 0; i < files.length; i++) {
    // 后端预览图片路径应为 `/preview/filename.png` 格式，与你 FastAPI 后端匹配
    const file = files[i];
    const fileName = file.name;
    const safeName = encodeURIComponent(fileName);
    previewImages.push(`/preview/${safeName}.png`);
    previewFileNames.push(fileName);
  }

  currentPreviewIndex = 0;
  updatePreviewImage();
}

function updatePreviewImage() {
  const img = document.getElementById('preview-img');
  const name = document.getElementById('preview-file-name');
  if (previewImages.length === 0) return;

  img.src = previewImages[currentPreviewIndex];
  img.style.display = 'block';
  name.innerText = previewFileNames[currentPreviewIndex];
}

function nextPreview() {
  if (previewImages.length === 0) return;
  currentPreviewIndex = (currentPreviewIndex + 1) % previewImages.length;
  updatePreviewImage();
}

function prevPreview() {
  if (previewImages.length === 0) return;
  currentPreviewIndex = (currentPreviewIndex - 1 + previewImages.length) % previewImages.length;
  updatePreviewImage();
}
</script>
```

---

#### 🖼️ 3. 后端图片准备

你 FastAPI 后端需要保证 `/preview/xxx.pdf.png` 文件在浏览器中可以访问。比如这样处理：

```python
from fastapi.staticfiles import StaticFiles
app.mount("/preview", StaticFiles(directory="preview_images"), name="preview")
```

---

### ✅ 效果预期：

1. 用户上传多个 PDF
2. 点击“预览剪裁效果”按钮会自动加载每个 PDF 对应的 `.png` 预览图
3. 点击左右箭头切换查看不同文件的预览图像

---

如果你希望我同时更新一整段完整 HTML 和 JS 的合并代码，我也可以为你生成。是否需要？

# 7
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

# 6
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

# 5
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

# 4
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

# 3
要解决这两个问题，需要做两件事：

1. **在生成 CSV 时，把文件名里的 `&`、空格等 URL 保留字符替换掉**，避免在 URL 中被当成分隔符。
2. **前端用 `encodeURIComponent`** 来构造下载链接。

下面给出最小化改动（基于你现有的 `process.py`、`app.py` 和 `static/index.html`）。

---

### 1. `process.py`：给 CSV 文件名做一次基本“清洗”

在文件顶部引入 `re`，然后把：

```python
    filename = file.filename.rsplit('.', 1)[0]
```

改成：

```python
    import re
    raw = file.filename.rsplit('.', 1)[0]
    # 把 & 和 空格 替成下划线，其他非法 URL 字符也可以一起替换
    safe = re.sub(r'[\s&]+', '_', raw)
    filename = safe
```

完整示例片段：

```python
def process_pdf_and_extract(file, top_cm, bottom_cm):
    import re
    raw = file.filename.rsplit('.', 1)[0]
    safe = re.sub(r'[\s&]+', '_', raw)
    filename = safe
    csv_path = f"outputs/{uuid4().hex}_{filename}.csv"
    ...
```

这样生成的 CSV 名就没有 `&`、空格了，比如

```
outputs/abcd1234_FusionOS_23.1.3安装BF3驱动_Nvqual测试指导书V1.0-zhangfeng_20250412.csv
```

---

### 2. 前端 `static/index.html`：用 `encodeURIComponent`

在生成下载链接处，把

```js
csvLink.href = `/download/?path=${res.path}`;
```

替换为

```js
csvLink.href = `/download/?path=${encodeURIComponent(res.path)}`;
```

如果你也有预览 URL（`data.preview_path`），同样做一次编码：

```js
img.src = "/" + encodeURIComponent(data.preview_path);
```

---

### （可选）把下载改成路径参数方式

如果你愿意，也可以把下载接口从 `GET /download/?path=…` 改为

```python
@app.get("/download/{file_path:path}")
async def download(file_path: str):
    return FileResponse(f"outputs/{file_path}", filename=os.path.basename(file_path))
```

然后前端只传 `outputs/xxx.csv` 的 basename：

```js
const name = res.path.split('/').pop();
csvLink.href = `/download/${encodeURIComponent(name)}`;
```

这一步可选，但可以彻底避免 `&` 或 `?` 拆分 query.

---

以上两步修改后，就能保证：

* 生成的 CSV 文件名里没有会破坏 URL 的字符；
* 前端下载链接也会被正确 URL 编码。

重新构建并运行即可解决 `FileNotFoundError` 与 500 错误。

# 2
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

# 1
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
