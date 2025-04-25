**Docker 部署一个稳定、纯后端的 PDF 裁剪与结构化提取工具**

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
docker build --build-arg HTTP_PROXY=http://proxy.example.com:8080 --build-arg HTTPS_PROXY=http://proxy.example.com:8080 .


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
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PDF 剪裁工具</title>
  <style>
    body {
      font-family: sans-serif;
      padding: 20px;
    }
    input, button {
      margin: 10px 0;
      padding: 8px;
    }
  </style>
</head>
<body>
  <h1>PDF 剪裁与结构化提取工具</h1>

  <form id="uploadForm">
    <label>选择 PDF 文件：
      <input type="file" id="pdfFile" accept=".pdf" required />
    </label><br>

    <label>上边距 (cm)：
      <input type="number" id="topCm" value="2.5" step="0.1" required />
    </label><br>

    <label>下边距 (cm)：
      <input type="number" id="bottomCm" value="2.5" step="0.1" required />
    </label><br>

    <button type="submit">上传并处理</button>
  </form>

  <div id="result" style="margin-top:20px;"></div>

  <script>
    const form = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const file = document.getElementById('pdfFile').files[0];
      const top_cm = document.getElementById('topCm').value;
      const bottom_cm = document.getElementById('bottomCm').value;

      if (!file) return alert("请选择 PDF 文件");

      const formData = new FormData();
      formData.append("file", file);
      formData.append("top_cm", top_cm);
      formData.append("bottom_cm", bottom_cm);

      resultDiv.innerHTML = "⏳ 正在处理，请稍等...";

      try {
        const response = await fetch("http://localhost:8090/process/", {
          method: "POST",
          body: formData
        });

        const data = await response.json();

        if (response.ok) {
          resultDiv.innerHTML = `
            ✅ 处理完成：<br>
            <a href="http://localhost:8090/download/?path=${encodeURIComponent(data.pdf)}" target="_blank">下载裁剪后的 PDF</a><br>
            <a href="http://localhost:8090/download/?path=${encodeURIComponent(data.csv)}" target="_blank">下载结构化 CSV</a>
          `;
        } else {
          resultDiv.innerHTML = "❌ 出错：" + JSON.stringify(data);
        }
      } catch (err) {
        resultDiv.innerHTML = "❌ 网络错误：" + err.message;
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
