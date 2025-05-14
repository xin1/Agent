错误
```
ModuleNotFoundError: No module named 'frontend'
File "D:\Gradio\code\Graph_Mind\document_graph_project\app\extract_text.py", line 1, in <module>
    import fitz  # PyMuPDF
  File "D:\Gradio\code\.venv\lib\site-packages\fitz\__init__.py", line 1, in <module>
    from frontend import *
ModuleNotFoundError: No module named 'frontend'
```
好的，以下是基于本地大模型（如 [ChatGLM3](https://github.com/THUDM/ChatGLM3)）分析多个 PDF 文档、生成文档标签与关系图谱，并导出为 Dify 可读格式的完整开发流程和参考代码框架：

---

## 🧠 项目目标

构建一个可部署的本地系统，具备以下功能：

1. **解析多个 PDF 文档**。
2. **调用本地大模型抽取每篇文档的关键信息与标签**。
3. **基于语义相似性、标签、内容等分析文档间的关系（如同一公司、相似主题）**。
4. **生成交互式知识图谱**（网页可视化，悬停查看摘要，支持放缩/拖动）。
5. **导出 Dify 可读的知识库格式（Markdown + metadata）**。

---

## 🏗️ 项目结构

```
document_graph_project/
├── data/
│   └── pdfs/                    # 存放待处理 PDF
├── outputs/
│   ├── html_graph/              # 生成的知识图谱网页
│   └── dify_knowledge_base/     # Dify 格式的输出
├── models/
│   └── chatglm3/                # 下载的本地模型
├── app/
│   ├── extract_text.py          # PDF 文字抽取模块
│   ├── analyze_docs.py          # 大模型分析模块
│   ├── build_graph.py           # 图谱生成与可视化模块
│   └── export_dify.py           # Dify 格式导出模块
├── requirements.txt
└── run.py                       # 主流程入口
```

---

## 🔧 开发步骤与代码概览

### 1️⃣ PDF 文本抽取（`extract_text.py`）

```python
import fitz  # PyMuPDF
import os

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])

def load_all_pdfs(folder):
    texts = {}
    for fname in os.listdir(folder):
        if fname.endswith(".pdf"):
            full_path = os.path.join(folder, fname)
            texts[fname] = extract_text_from_pdf(full_path)
    return texts
```

---

### 2️⃣ 本地模型调用与标签分析（`analyze_docs.py`）

使用 [ChatGLM3](https://github.com/THUDM/ChatGLM3) 本地运行，推荐使用 Transformers 推理接口或官方 WebUI API 模式。

```python
from transformers import AutoTokenizer, AutoModel
import torch

tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True).half().cuda()
model.eval()

def summarize_and_tag(doc_text):
    prompt = f"""
请阅读以下文档内容，提炼关键信息，并为其打上合适的标签：
文档内容如下：
{doc_text[:2000]}  # 截断防止溢出
输出格式：
文档摘要：
标签（逗号分隔）：
"""
    response, _ = model.chat(tokenizer, prompt, history=[])
    return response
```

---

### 3️⃣ 分析文档关系（构建图谱边，`build_graph.py`）

```python
from pyvis.network import Network

def parse_summary_and_labels(raw_response):
    summary = ""
    tags = []
    for line in raw_response.splitlines():
        if line.startswith("文档摘要"):
            summary = line.split("：", 1)[-1].strip()
        elif line.startswith("标签"):
            tags = line.split("：", 1)[-1].split("，")
    return summary, [t.strip() for t in tags]

def build_doc_graph(doc_infos, output_path="outputs/html_graph/index.html"):
    net = Network(height="750px", width="100%", directed=True)
    tag_map = {}

    for fname, info in doc_infos.items():
        net.add_node(fname, label=fname, title=info['summary'])
        for tag in info['tags']:
            tag_node = f"标签:{tag}"
            tag_map.setdefault(tag_node, []).append(fname)
            net.add_node(tag_node, label=tag_node, color='orange')
            net.add_edge(tag_node, fname)

    # 生成“相似标签”关系
    for tag, files in tag_map.items():
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                net.add_edge(files[i], files[j], label="同标签")

    net.show(output_path)
```

---

### 4️⃣ 导出为 Dify 可读格式（`export_dify.py`）

```python
import os
import json

def export_to_dify_format(doc_infos, output_folder="outputs/dify_knowledge_base"):
    os.makedirs(output_folder, exist_ok=True)
    for fname, info in doc_infos.items():
        data = {
            "metadata": {
                "source": fname,
                "tags": info['tags'],
            },
            "content": info['summary']
        }
        out_path = os.path.join(output_folder, f"{fname}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

---

### 5️⃣ 主流程（`run.py`）

```python
from app.extract_text import load_all_pdfs
from app.analyze_docs import summarize_and_tag, parse_summary_and_labels
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format

pdf_texts = load_all_pdfs("data/pdfs")
doc_infos = {}

for fname, text in pdf_texts.items():
    raw = summarize_and_tag(text)
    summary, tags = parse_summary_and_labels(raw)
    doc_infos[fname] = {"summary": summary, "tags": tags}

build_doc_graph(doc_infos)
export_to_dify_format(doc_infos)
```

---

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 内容：

```text
transformers
torch
pyvis
fitz  # pymupdf
```

---

## 📝 补充说明

* **使用 GPU 加速**：确保 `torch.cuda.is_available()` 返回 True。
* **生成图谱交互页面**：pyvis 可直接在浏览器中打开 `html_graph/index.html`。
* **Dify 兼容**：输出的 `json` 格式可作为文档上传至 Dify 的“知识库”模块。
* **模型替代建议**：如需轻量化模型，可替换为 MiniCPM、Yi-1.5、Mistral-Chinese 等。

---

是否需要我为你打包为可部署的 Docker 项目？或加一个简单网页上传页面？
