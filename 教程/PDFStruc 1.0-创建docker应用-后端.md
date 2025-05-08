# PDFStruc 1.0 Docker部署纯后端

### ✅ 后端 API 工具（推荐用 [FastAPI]）
更轻量、部署稳定、支持并发调用，适合局域网/Web 服务：

---

## 🧩 整体功能需求总结

- 接收 PDF 文件和裁剪参数（上/下边距）
- 自动裁剪页眉/页脚并提取结构化标题+内容
- 输出两个文件：裁剪后的 PDF + CSV（结构化）

---

## 🧱 项目结构

你可以创建一个目录，比如 `F:\Fusion\pdf_api_tool`，结构如下：

```
pdf_api_tool/
├── app.py                 # FastAPI 应用入口
├── pdf_processor.py       # PDF 处理逻辑
├── requirements.txt       # 依赖
├── Dockerfile             # Docker 构建文件
└── outputs/               # 保存生成的文件
```

---

## 📄 `pdf_processor.py`

（逻辑与你之前的相似）

```python
import fitz
import re
import os
import uuid
import pandas as pd

def cm_to_px(cm):
    return int(cm * 28.35)

def is_title(line):
    return bool(re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line.strip())) and len(line.strip()) <= 50

def clean_content(lines):
    result = []
    for line in lines:
        if result and not result[-1][-1] in ('。', '；', '.', '”', '?', '!'):
            result[-1] += ' ' + line
        else:
            result.append(line)
    return result

def process_pdf(file_path, top_cm=2.5, bottom_cm=2.5):
    doc = fitz.open(file_path)
    top_px, bottom_px = cm_to_px(top_cm), cm_to_px(bottom_cm)
    new_doc = fitz.open()

    data = []
    current_title = None
    current_content = []

    for page in doc:
        rect = page.rect
        crop_rect = fitz.Rect(rect.x0, rect.y0 + top_px, rect.x1, rect.y1 - bottom_px)
        new_page = new_doc.new_page(width=rect.width, height=rect.height - top_px - bottom_px)
        text = page.get_text(clip=crop_rect)

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if is_title(line):
                if current_title:
                    data.append([current_title, "\n".join(clean_content(current_content))])
                current_title = line
                current_content = []
            elif current_title:
                current_content.append(line)

    if current_title:
        data.append([current_title, "\n".join(clean_content(current_content))])

    uid = str(uuid.uuid4())[:8]
    os.makedirs("outputs", exist_ok=True)
    out_pdf = f"outputs/cropped_{uid}.pdf"
    out_csv = f"outputs/structured_{uid}.csv"

    new_doc.save(out_pdf)
    new_doc.close()

    pd.DataFrame(data, columns=["标题", "内容"]).to_csv(out_csv, index=False, encoding='utf-8-sig')

    return out_pdf, out_csv
```

---

## 🚀 `app.py`（FastAPI 服务）

```python
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from pdf_processor import process_pdf
import shutil
import os

app = FastAPI()

@app.post("/process/")
async def process_pdf_endpoint(
    file: UploadFile = File(...),
    top_cm: float = Form(2.5),
    bottom_cm: float = Form(2.5)
):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    cropped_pdf, csv_file = process_pdf(temp_path, top_cm, bottom_cm)
    os.remove(temp_path)

    return {
        "pdf": cropped_pdf,
        "csv": csv_file
    }

@app.get("/download/")
def download_file(path: str):
    return FileResponse(path, filename=os.path.basename(path))
```

---

## 📦 `requirements.txt`

```txt
fastapi
uvicorn
pymupdf
pandas
```

---

## 🐳 Dockerfile

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧪 构建 & 运行（命令行操作）

```bash
cd F:\Fusion\pdf_api_tool

# 构建镜像
docker build -t pdf-api-tool .

# 运行容器（挂载 outputs 目录）
docker run -d -p 8000:8000 --name pdf_tool_api pdf-api-tool
```

---

## 🌐 使用方式

你可以用 Postman、curl 或简单 Python 脚本访问这个服务：

### 上传并处理：
```
POST http://localhost:8000/process/
FormData:
- file: 选择你的 PDF
- top_cm: 2.5
- bottom_cm: 2.5
```

### 下载：
```
GET http://localhost:8000/download/?path=outputs/cropped_XXXX.pdf
```

---

FastAPI + Docker 部署，**端口是 8090**：

---

### ✅ `index.html`
```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>PDF 裁剪工具</title>
  <style>
    body {
      font-family: sans-serif;
      max-width: 600px;
      margin: 40px auto;
    }
    label, input {
      display: block;
      margin-top: 10px;
    }
    button {
      margin-top: 20px;
      padding: 10px 20px;
    }
  </style>
</head>
<body>
  <h1>PDF 裁剪并提取工具</h1>
  <form id="uploadForm">
    <label>上传 PDF 文件：
      <input type="file" name="file" accept=".pdf" required>
    </label>
    <label>上边距裁剪（cm）：
      <input type="number" name="top_cm" step="0.1" value="2.5" required>
    </label>
    <label>下边距裁剪（cm）：
      <input type="number" name="bottom_cm" step="0.1" value="2.5" required>
    </label>
    <button type="submit">提交处理</button>
  </form>

  <p id="status"></p>

  <script>
    document.getElementById('uploadForm').addEventListener('submit', async function (e) {
      e.preventDefault();

      const form = e.target;
      const formData = new FormData(form);
      const status = document.getElementById('status');
      status.textContent = '⏳ 正在处理，请稍候...';

      try {
        const response = await fetch('http://localhost:8000/process/', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error('处理失败，可能服务未启动或文件不合法');
        }

        const result = await response.json();
        const download = (url, name) => {
          const a = document.createElement('a');
          a.href = 'http://localhost:8000/download/?path=' + encodeURIComponent(url);
          a.download = name;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        };

        download(result.pdf, '裁剪后.pdf');
        download(result.csv, '结构化内容.csv');
        status.textContent = '✅ 成功处理并下载文件';
      } catch (err) {
        console.error(err);
        status.textContent = '❌ 处理失败：' + err.message;
      }
    });
  </script>
</body>
</html>

```

---

### 📌 说明：

- HTML 会上传 PDF、输入上下边距，提交给 `/process/` 接口。
- 后端返回裁剪后的 PDF 和 CSV 路径，再用 `/download/` 实现点击下载。
- `localhost:8090` 是你部署映射的端口，请根据实际端口替换。

---
