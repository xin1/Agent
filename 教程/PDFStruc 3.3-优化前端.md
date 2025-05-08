# PDFStruc 3.3 优化前端，增加预览功能
## code : pdf_tool_v1
以下是完整的 PDF 剪裁与结构提取工具（支持预览、CSV 提取、进度条、多文档打包下载）前后端 + Docker 部署方案：

---

## ✅ 一、功能总览

支持功能：

* ✅ 拖拽/多选上传 PDF；
* ✅ 设置上下裁剪距离；
* ✅ 剪裁效果预览；
* ✅ 结构化数据提取为 CSV；
* ✅ 多文档压缩打包；
* ✅ 下载按钮动态显示；
* ✅ 进度条；
* ✅ Docker 一键部署。

---

## 📁 二、目录结构

```
pdf-tool/
├── app.py
├── process.py
├── preview.py
├── zip_util.py
├── static/
│   ├── index.html
│   └── style.css
├── outputs/                  # 自动生成的预览图和CSV
├── Dockerfile
└── requirements.txt
```

---

## 🐍 三、后端核心代码（FastAPI）

### ✅ 1. `app.py`

```python
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from process import process_pdf_and_extract
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

@app.post("/preview/")
async def preview(file: UploadFile = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    preview_path = generate_preview_image(file, top_cm, bottom_cm)
    return {"preview_path": preview_path}

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        csv_path = process_pdf_and_extract(file, top_cm, bottom_cm)
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

### ✅ 2. `process.py`

```python
import os
import fitz  # PyMuPDF
import csv
import re
from uuid import uuid4

os.makedirs("outputs", exist_ok=True)

def process_pdf_and_extract(file, top_cm, bottom_cm):
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    filename = file.filename.rsplit('.', 1)[0]
    csv_path = f"outputs/{uuid4().hex}_{filename}.csv"

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

---

### ✅ 3. `preview.py`

```python
import fitz
from uuid import uuid4
import os

def generate_preview_image(file, top_cm, bottom_cm):
    os.makedirs("outputs", exist_ok=True)
    pdf = fitz.open(stream=file.file.read(), filetype="pdf")
    page = pdf.load_page(2)
    rect = page.rect
    top = top_cm * 28.35
    bottom = bottom_cm * 28.35
    clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)

    pix = page.get_pixmap(dpi=150, clip=clip)
    path = f"outputs/{uuid4().hex}_preview.png"
    pix.save(path)
    return path
```

---

### ✅ 4. `zip_util.py`

```python
import zipfile
from uuid import uuid4
import os

def zip_csvs(paths):
    zip_name = f"outputs/{uuid4().hex}_csvs.zip"
    with zipfile.ZipFile(zip_name, 'w') as z:
        for path in paths:
            z.write(path, os.path.basename(path))
    return zip_name
```

---

## 🌐 四、前端文件（静态资源）

### ✅ `static/index.html`

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PDF预处理工具</title>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" />
  <style>
    .row {
      display: flex;
      gap: 20px;
    }

    .left-panel {
      flex: 2;
    }

    .right-panel {
      flex: 1.5;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    #preview-img {
      max-width: 100%;
      max-height: 500px;
      border-radius: var(--border-radius);
      box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2); /* 调整阴影 */
      border: 1px solid #eee;
      display: none;
    }

    :root {
      --primary-color: #4a6bff;
      --secondary-color: #6c757d;
      --success-color: #28a745;
      --danger-color: #dc3545;
      --light-color: #f8f9fa;
      --dark-color: #343a40;
      --border-radius: 8px;
      --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      --transition: all 0.3s ease;
    }
    
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Roboto', sans-serif;
      line-height: 1.6;
      color: #333;
      background-color: #f5f7fa;
      padding: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    
    .container {
      background-color: white;
      border-radius: var(--border-radius);
      box-shadow: var(--box-shadow);
      padding: 30px;
      margin-top: 20px;
    }
    
    h1 {
      color: var(--primary-color);
      text-align: center;
      margin-bottom: 20px;
      font-weight: 500;
    }
    
    .section {
      margin-bottom: 15px;
      padding: 15px;
      border-radius: var(--border-radius);
      background-color: var(--light-color);
    }
    
    .section-title {
      font-size: 1.1rem;
      margin-bottom: 15px;
      color: var(--dark-color);
      display: flex;
      align-items: center;
    }
    
    .section-title i {
      margin-right: 10px;
      color: var(--primary-color);
    }
    
    .file-upload {
      border: 2px dashed #ccc;
      border-radius: var(--border-radius);
      padding: 30px;
      text-align: center;
      transition: var(--transition);
      margin-bottom: 15px;
      cursor: pointer;
    }
    
    .file-upload:hover {
      border-color: var(--primary-color);
      background-color: rgba(74, 107, 255, 0.05);
    }
    
    .file-upload.active {
      border-color: var(--success-color);
      background-color: rgba(40, 167, 69, 0.05);
    }
    
    #file-names {
      font-size: 0.9rem;
      color: var(--secondary-color);
      margin-top: 10px;
      word-break: break-all;
    }
    
    .form-group {
      margin-bottom: 20px;
    }
    
    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: var(--dark-color);
    }
    
    input[type="number"],
    input[type="file"] {
      width: 100%;
      padding: 10px 15px;
      border: 1px solid #ddd;
      border-radius: var(--border-radius);
      font-size: 1rem;
      transition: var(--transition);
    }
    
    input[type="number"]:focus,
    input[type="file"]:focus {
      outline: none;
      border-color: var(--primary-color);
      box-shadow: 0 0 0 3px rgba(74, 107, 255, 0.2);
    }
    
    .input-group {
      display: flex;
      gap: 15px;
    }
    
    .input-group .form-group {
      flex: 1;
    }
    
    .btn {
      display: inline-block;
      padding: 12px 24px;
      background-color: var(--primary-color);
      color: white;
      border: none;
      border-radius: var(--border-radius);
      cursor: pointer;
      font-size: 1rem;
      font-weight: 500;
      transition: var(--transition);
      text-align: center;
      margin-right: 10px;
      margin-bottom: 10px;
    }
    
    .btn:hover {
      background-color: #3a5bef;
      transform: translateY(-2px);
    }
    
    .btn-secondary {
      background-color: var(--secondary-color);
    }
    
    .btn-secondary:hover {
      background-color: #5a6268;
    }
    
    .btn-block {
      display: block;
      width: 100%;
    }
    
    #preview-container {
      width: 400px;
      height: 465px;
      margin: 10px 20px;
      text-align: center;
    }
    
    #preview-img {
      max-width: 100%;
      max-height: 450px;
      border-radius: var(--border-radius);      
      border: 1px solid #eee;
      display: none;
    }
    
    .progress-container {
      margin: 25px 0;
    }
    
    progress {
      width: 100%;
      height: 10px;
      border-radius: 5px;
      margin-bottom: 10px;
    }
    
    progress::-webkit-progress-bar {
      background-color: #eee;
      border-radius: 5px;
    }
    
    progress::-webkit-progress-value {
      background-color: var(--primary-color);
      border-radius: 5px;
      transition: var(--transition);
    }
    
    #download-links {
      margin-top: 25px;
      text-align: center;
    }
    
    .download-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 24px;
      background-color: var(--success-color);
      color: white;
      text-decoration: none;
      border-radius: var(--border-radius);
      transition: var(--transition);
    }
    
    .download-btn:hover {
      background-color: #218838;
      transform: translateY(-2px);
    }
    
    .download-btn i {
      margin-right: 8px;
    }
    
    .hidden {
      display: none !important;
    }
    

    @media (max-width: 768px) {
      .row {
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1><i class="fas fa-file-pdf"></i> PDF预处理工具</h1>
    
    <div class="row">
      <!-- 左侧部分 -->
      <div class="left-panel">
        <div class="section">
          <h2 class="section-title"><i class="fas fa-cloud-upload-alt"></i> 上传PDF文件</h2>
          <div class="file-upload" id="file-upload-area">
            <input type="file" id="pdf-input" multiple accept=".pdf" hidden>
            <p><i class="fas fa-upload"></i> 点击或拖放PDF文件到此处</p>
            <p class="text-muted">支持一次性多文件上传</p>
          </div>
          <p id="file-names" class="text-muted"></p>
        </div>
        
        <div class="section">
          <h2 class="section-title"><i class="fas fa-cut"></i> 裁剪设置 <p class="text-muted">（请根据需要裁除页眉页尾）</p> </h2>
          
          <div class="input-group">
            <div class="form-group">
              <label for="top"><i class="fas fa-arrow-up"></i> 上（页眉）裁剪距离 (cm)</label>
              <input type="number" id="top" value="2.5" step="0.1" min="0">
            </div>
            <div class="form-group">
              <label for="bottom"><i class="fas fa-arrow-down"></i> 下（页尾）裁剪距离 (cm)</label>
              <input type="number" id="bottom" value="2.5" step="0.1" min="0">
            </div>
          </div>
        </div>
        
        <div class="section">
          <h2 class="section-title"><i class="fas fa-cog"></i> 处理</h2>
          <div class="progress-container" id="progress-container" style="display: none;">
            <progress id="progress-bar" value="0" max="100"></progress>
            <p class="text-muted" id="progress-text">处理中，请稍候...</p>
          </div>
          <div class="row" style="display: flex; gap: 10px;">
            <button class="btn btn-secondary" style="flex: 1;" onclick="previewPDF()">
              <i class="fas fa-image"></i> 预览剪裁效果
            </button>
            <button class="btn btn-secondary" style="flex: 1;" onclick="processPDFs()">
              <i class="fas fa-play"></i> 开始处理PDF文件
            </button>
          </div>
        </div>
        
        
      </div>
      
      <!-- 右侧部分 -->
      <div class="right-panel">
        <div class="section">
          <h2 class="section-title"><i class="fas fa-eye"></i> 预览</h2>
          <div id="preview-container">

            <img id="preview-img" style="margin-top: 15px;" />
          </div>
        </div>
        <div id="download-links" class="hidden">          
          <a id="csv-link" href="#" class="download-btn">
            <i class="fas fa-file-csv"></i> <span id="download-text">下载CSV文件</span>
          </a>
        </div>
      </div>
    </div>
  </div>

  <script>
    // 文件上传区域交互
    const fileInput = document.getElementById("pdf-input");
    const fileUploadArea = document.getElementById("file-upload-area");
    
    fileUploadArea.addEventListener("click", () => {
      fileInput.click();
    });
    
    fileInput.addEventListener("change", () => {
      const names = Array.from(fileInput.files).map(f => f.name).join("；");
      document.getElementById("file-names").textContent = `已选择 ${fileInput.files.length} 个文件`;
      fileUploadArea.classList.add("active");
      
      // 显示前几个文件名
      if (fileInput.files.length > 0) {
        const sampleNames = Array.from(fileInput.files)
          .slice(0, 3)
          .map(f => f.name)
          .join(", ");
        document.getElementById("file-names").textContent = 
          `已选择 ${fileInput.files.length} 个文件 (示例: ${sampleNames}${fileInput.files.length > 3 ? "..." : ""})`;
      }
    });
    
    // 拖放功能
    fileUploadArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      fileUploadArea.classList.add("active");
    });
    
    fileUploadArea.addEventListener("dragleave", () => {
      fileUploadArea.classList.remove("active");
    });
    
    fileUploadArea.addEventListener("drop", (e) => {
      e.preventDefault();
      fileUploadArea.classList.remove("active");
      
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        const event = new Event("change");
        fileInput.dispatchEvent(event);
      }
    });
    
    // 预览功能
    function previewPDF() {
      const file = fileInput.files[0];
      if (!file) return alert("请选择一个文件进行预览");
      
      const form = new FormData();
      form.append("file", file);
      form.append("top_cm", document.getElementById("top").value);
      form.append("bottom_cm", document.getElementById("bottom").value);

      const previewBtn = document.querySelector('.btn-secondary[onclick="previewPDF()"]');
      previewBtn.disabled = true;
      previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成预览...';
      
      fetch("/preview/", { method: "POST", body: form })
        .then(res => res.json())
        .then(data => {
          const img = document.getElementById("preview-img");
          img.src = "/" + data.preview_path;
          img.style.display = "block";
          previewBtn.disabled = false;
          previewBtn.innerHTML = '<i class="fas fa-image"></i> 预览剪裁效果';
        })
        .catch(() => {
          previewBtn.disabled = false;
          previewBtn.innerHTML = '<i class="fas fa-image"></i> 预览剪裁效果';
          alert("预览生成失败，请重试");
        });
    }
    
    // 处理功能
    function processPDFs() {
      const files = fileInput.files;
      if (files.length === 0) return alert("请上传PDF文件");
      
      const form = new FormData();
      for (let i = 0; i < files.length; i++) form.append("files", files[i]);
      form.append("top_cm", document.getElementById("top").value);
      form.append("bottom_cm", document.getElementById("bottom").value);

      const processBtn = document.querySelector('.btn-secondary[onclick="processPDFs()"]');
      processBtn.disabled = true;
      processBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
      
      document.getElementById("progress-container").style.display = "block";
      document.getElementById("download-links").classList.add("hidden");

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/process_batch/", true);

      const bar = document.getElementById("progress-bar");
      const progressText = document.getElementById("progress-text");
      
      bar.value = 0;
      progressText.textContent = "准备上传文件...";

      xhr.upload.onprogress = e => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          bar.value = percent;
          progressText.textContent = `上传中: ${percent}%`;
        }
      };

      xhr.onload = () => {
        try {
          const res = JSON.parse(xhr.responseText);
          document.getElementById("download-links").classList.remove("hidden");
          const csvLink = document.getElementById("csv-link");
          csvLink.href = `/download/?path=${res.path}`;
          
          if (res.is_zip) {
            document.getElementById("download-text").textContent = "下载CSV压缩包";
            csvLink.innerHTML = '<i class="fas fa-file-archive"></i> 下载CSV压缩包';
          } else {
            document.getElementById("download-text").textContent = "下载CSV文件";
            csvLink.innerHTML = '<i class="fas fa-file-csv"></i> 下载CSV文件';
          }
          
          progressText.textContent = "处理完成！";
          bar.value = 100;
        } catch (e) {
          progressText.textContent = "处理出错！";
          alert("处理过程中出错，请重试");
        }
        
        processBtn.disabled = false;
        processBtn.innerHTML = '<i class="fas fa-play"></i> 开始处理PDF文件';
      };

      xhr.onerror = () => {
        progressText.textContent = "网络错误！";
        alert("网络错误，请检查连接后重试");
        processBtn.disabled = false;
        processBtn.innerHTML = '<i class="fas fa-play"></i> 开始处理PDF文件';
      };

      xhr.send(form);
    }
  </script>
</body>
</html>
```

---

### ✅ `static/style.css`（可选）

```css

```

---

## 🐳 五、Docker部署

### ✅ `requirements.txt`

```txt
# pandas
# flask
# PyMuPDF

pdfplumber
fastapi
uvicorn
PyPDF2
pdf2image
jinja2
python-multipart
pillow
pymupdf
```

### ✅ `Dockerfile`

```Dockerfile



FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
# RUN pip install jinja2 PyPDF2 pdf2image pdfplumber fastapi uvicorn pymupdf python--multipart --公司源

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧪 六、一键运行流程

### ✅ 构建并运行容器：

```bash
docker build -t pdf-tool .
docker run -d -p 8010:8000 --name pdf_tool_v1 pdf-tool
```

访问：[http://localhost:8010](http://localhost:8010)

---

## ✅ 七、总结

你现在拥有一个完整的前后端 PDF 剪裁与结构提取工具，支持：

* 单/多文档上传；
* 裁剪预览；
* CSV结构提取；
* 动态下载按钮；
* 多文档自动压缩；
* Docker 一键部署。
