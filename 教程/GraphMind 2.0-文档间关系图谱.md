## ✅ 项目结构

```
document_graph_project/
├── app/
│   ├── extract_text.py         # 提取 PDF 文本
│   ├── analyze_docs.py         # 使用 ChatGLM3 总结内容并打标签
│   ├── build_graph.py          # 构建知识图谱
│   └── export_dify.py          # 导出 Dify 格式
├── data/
│   └── pdfs/                   # 存放 PDF 文档
├── run.py                      # 主运行脚本
└── requirements.txt
```

---

## 📦 安装依赖（requirements.txt）

```txt
transformers==4.38.3
# 按理说应该>=4.39.3，但是出现报错AttributeError: 'ChatGLMForConditionalGeneration' object has no attribute '_extract_past_from_model_output'，所以改成4.38.3了
torch>=2.1.0
cpm_kernels
sentence-transformers
pymupdf
networkx
pyvis
tqdm
```

---

## 🧠 模型调用部分（`app/analyze_docs.py`）

```python
from transformers import AutoTokenizer, AutoModel
import torch

# 加载本地 ChatGLM3 模型（需要提前下载到本地）
tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True, device_map="auto").eval()

def chunk_text(text, max_tokens=2048):
    """将长文本按最大token数切分为多段"""
    import re
    sentences = re.split(r'(。|！|\!|\.|？|\?)', text)
    chunks, current = [], ""
    for i in range(0, len(sentences), 2):
        sent = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
        if len(tokenizer(current + sent).input_ids) < max_tokens:
            current += sent
        else:
            chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks

def summarize_and_tag(text):
    chunks = chunk_text(text)
    combined_summary = ""
    for i, chunk in enumerate(chunks):
        prompt = f"请总结以下文档内容并提取3-5个标签，输出格式：【总结】xxx【标签】xxx：\n{chunk}"
        response, _ = model.chat(tokenizer, prompt, history=[])
        combined_summary += f"\n第{i+1}段：{response}\n"
    return combined_summary

def parse_summary_and_labels(text):
    summary = ""
    tags = []
    if "【总结】" in text and "【标签】" in text:
        summary = text.split("【总结】")[1].split("【标签】")[0].strip()
        tag_text = text.split("【标签】")[1].strip()
        tags = [t.strip("，, ") for t in tag_text.split() if t.strip()]
    return summary, tags
```

---

## 📄 文本提取（`app/extract_text.py`）

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

## 🧩 构建图谱（`app/build_graph.py`）

```python
import networkx as nx
from pyvis.network import Network
import os

def build_doc_graph(doc_infos, output_path="output/graph.html"):
    G = nx.Graph()
    for fname, info in doc_infos.items():
        G.add_node(fname, title=info["summary"], label=fname)

    # 关系边
    files = list(doc_infos.keys())
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            f1, f2 = files[i], files[j]
            tags1, tags2 = set(doc_infos[f1]["tags"]), set(doc_infos[f2]["tags"])
            common = tags1 & tags2
            if common:
                G.add_edge(f1, f2, label="、".join(common))

    # 可视化
    net = Network(height="800px", width="100%", directed=False)
    net.from_nx(G)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    net.show(output_path,notebook=False)
    # 注意不加 notebook= 容易报AttributeError:'NoneType' object has no attribute 'render'错误，可以换成 notebook=Ture
    # 如果设为 True，会在 Jupyter Notebook 中直接显示图像（不保存到文件）。
    # 如果设为 False（默认），仅将图像保存到 output_path，不弹出显示。
```

---

## 📤 导出为 Dify 格式（`app/export_dify.py`）

```python
import json
import os

def export_to_dify_format(doc_infos, output_file="output/dify_dataset.json"):
    data = []
    for fname, info in doc_infos.items():
        data.append({
            "id": fname,
            "question": info["summary"],
            "answer": "，".join(info["tags"]),
        })
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 🚀 主运行脚本（`run.py`）

```python
from app.extract_text import load_all_pdfs
from app.analyze_docs import summarize_and_tag, parse_summary_and_labels
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format
from tqdm import tqdm

pdf_texts = load_all_pdfs("data/pdfs")
doc_infos = {}

for fname, text in tqdm(pdf_texts.items(),desc="处理文档中"):
    raw = summarize_and_tag(text)
    summary, tags = parse_summary_and_labels(raw)
    doc_infos[fname] = {"summary": summary, "tags": tags}

build_doc_graph(doc_infos)
export_to_dify_format(doc_infos)
```

---

## ✅ 最后运行说明

```bash
cd document_graph_project
python run.py
```

运行后会在 `output/` 下生成：

* `graph.html`：可交互知识图谱
* `dify_dataset.json`：可用于 Dify 导入的数据集

---
