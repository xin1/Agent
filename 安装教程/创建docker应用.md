好的，这里给出**完整详细的代码和部署流程**，你将得到一个可以通过 **Docker 部署** 的 Gradio 网页版工具，用于：

- ✅ 上传 PDF 文件  
- ✅ 输入裁剪上/下边距（cm）
- ✅ 自动裁剪 PDF、提取结构（标题 + 内容）到 CSV  
- ✅ 生成并下载两个文件：裁剪后的 PDF + 提取结构的 CSV

---

## 📁 目录结构建议

你可以在任意位置创建一个文件夹，例如：

```bash
F:\Fusion\pdf_tool_web
```

然后把以下文件创建进去：

```
pdf_tool_web/
├── app.py                # 主程序（Gradio Web 接口）
├── pdf_processor.py      # 核心 PDF 裁剪 + 提取逻辑
├── requirements.txt      # Python 依赖包
└── Dockerfile            # Docker 构建脚本
```

---

## 🧠 核心处理逻辑 `pdf_processor.py`

```python
import fitz  # PyMuPDF
import re
import os
import uuid
import pandas as pd

def cm_to_px(cm):
    return int(cm * 28.35)  # 1 cm ≈ 28.35 px

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

        # 提取结构化内容
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

    # 保存文件
    unique_id = str(uuid.uuid4())[:8]
    base_dir = "outputs"
    os.makedirs(base_dir, exist_ok=True)

    cropped_pdf = os.path.join(base_dir, f"cropped_{unique_id}.pdf")
    csv_file = os.path.join(base_dir, f"output_{unique_id}.csv")

    new_doc.save(cropped_pdf)
    new_doc.close()

    df = pd.DataFrame(data, columns=["标题", "内容"])
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')

    return cropped_pdf, csv_file
```

---

## 🌐 Gradio 网页前端 `app.py`

```python
import gradio as gr
from pdf_processor import process_pdf

def process(file, top_cm, bottom_cm):
    cropped_pdf, csv_file = process_pdf(file.name, top_cm, bottom_cm)
    return cropped_pdf, csv_file

with gr.Blocks() as demo:
    gr.Markdown("## 📄 PDF 自动裁剪 + 标题内容提取工具")

    with gr.Row():
        file_input = gr.File(label="上传 PDF 文件", file_types=[".pdf"])
        top_crop = gr.Number(label="上裁剪距离 (cm)", value=2.5)
        bottom_crop = gr.Number(label="下裁剪距离 (cm)", value=2.5)

    btn = gr.Button("处理 PDF")

    with gr.Row():
        out_pdf = gr.File(label="裁剪后的 PDF")
        out_csv = gr.File(label="结构化 CSV")

    btn.click(fn=process, inputs=[file_input, top_crop, bottom_crop], outputs=[out_pdf, out_csv])

demo.queue()
demo.launch(server_name="0.0.0.0", server_port=7860)
```

---

## 📦 `requirements.txt`

```txt
gradio==4.25.0
pymupdf
pandas
```

---

## 🐳 `Dockerfile`

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["python", "app.py"]
```

---

## 🚀 构建并运行 Docker

进入目录（例如命令行输入）：

```bash
cd F:\Fusion\pdf_tool_web
```

### 构建镜像

```bash
docker build -t pdf-tool .
```

### 启动容器

```bash
docker run -d -p 7860:7860 --name pdf_tool_container pdf-tool
```

---

## ✅ 使用方式

浏览器打开：

```
http://localhost:7860/
```

或在公司内网使用你本机的 IP 地址，例如：

```
http://10.53.4.65:7860/
```

---

如果你希望我直接打包一份 `.zip` 的 Docker 项目发你使用，也可以说一声，我可以帮你打整套资源！需要我继续帮你构建吗？
