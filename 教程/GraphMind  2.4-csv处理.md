下面是一个完整项目流程与代码，读取 CSV 文件的第一列内容作为文档内容，通过大模型（如 ChatGLM3）提取摘要、标签、类型，并生成知识图谱和 Dify 格式导出。

---

### 📁 项目结构

```
project/
├── run.py
├── app/
│   ├── extract_csv.py
│   ├── analyze_docs.py
│   ├── build_graph.py
│   └── export_dify.py
├── data/
│   └── csvs/         # 存放CSV文件
├── output/
│   ├── processed.json
│   ├── graph.html
│   └── dify_dataset.json
```

---

## 🔧 1. `run.py`

```python
from app.extract_csv import load_all_csvs
from app.analyze_docs import process_document
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format
import json, os

def main():
    csv_dir = "data/csvs"
    docs = load_all_csvs(csv_dir)
    done_file = "output/processed.json"
    doc_infos = {}

    if os.path.exists(done_file):
        with open(done_file, "r", encoding="utf-8") as f:
            doc_infos = json.load(f)

    for name, text in docs.items():
        if name in doc_infos:
            print(f"✅ 已处理: {name}，跳过")
            continue
        print(f"\n🚀 处理中: {name}")
        summary, tags, doc_type = process_document(text, fname=name)
        if summary:
            doc_infos[name] = {"summary": summary, "tags": tags, "type": doc_type}
            with open(done_file, "w", encoding="utf-8") as f:
                json.dump(doc_infos, f, ensure_ascii=False, indent=2)
        else:
            print(f"❌ 处理失败: {name}，可稍后手动重试")

    build_doc_graph(doc_infos)
    export_to_dify_format(doc_infos)

if __name__ == "__main__":
    main()
```

---

## 📄 2. `app/extract_csv.py`

```python
import csv
import os

def extract_first_column_from_csv(csv_path):
    texts = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 1:
                texts.append(row[0].strip())  # 只保留第一列
    return "\n".join(texts)

def load_all_csvs(folder):
    data = {}
    for fn in os.listdir(folder):
        if fn.lower().endswith(".csv"):
            path = os.path.join(folder, fn)
            content = extract_first_column_from_csv(path)
            data[fn] = content
    return data

```

---

## 🧠 3. `app/analyze_docs.py`

```python
from transformers import AutoTokenizer, AutoModel
import torch
import time
import re

def init_model(device='cpu'):
    tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = model.float().to(device).eval()
    return tokenizer, model, device

def safe_chat(tokenizer, model, prompt, max_tokens=1024):
    try:
        response, _ = model.chat(tokenizer, prompt, history=[], max_new_tokens=max_tokens)
        return response
    except Exception as e:
        print(f"⚠️ 推理失败: {e}")
        return None

def process_document(text, fname="文档"):
    device = "cpu"  # 强制使用CPU
    tokenizer, model, device = init_model(device)

    prompt = (
        "请阅读以下文档内容，并严格按照格式输出：\n"
        "【总结】简洁总结全文核心内容；\n"
        "【标签】提取3~5个主题相关标签，使用顿号或逗号分隔；\n"
        "【类型】从以下类别中选择最贴近的一个：综述、措施、政策、报告、通知、其它。\n\n"
        f"文档内容如下：\n{text[:6000]}"
    )

    response = safe_chat(tokenizer, model, prompt)
    if not response:
        return None, [], "其它"

    return parse_summary_and_labels(response)

def parse_summary_and_labels(raw_text):
    sum_match = re.search(r"【总结】(.*?)\n", raw_text, re.S)
    tag_match = re.search(r"【标签】(.*?)\n", raw_text, re.S)
    type_match = re.search(r"【类型】(综述|措施|政策|报告|通知|其它)", raw_text)

    summary = sum_match.group(1).strip() if sum_match else "无总结"
    tags = [t.strip() for t in re.split(r"[、,，\s]+", tag_match.group(1)) if t.strip()] if tag_match else ["未提取"]
    doc_type = type_match.group(1).strip() if type_match else "其它"

    return summary, tags, doc_type
```

---

## 🌐 4. `app/build_graph.py`

```python
import networkx as nx
from pyvis.network import Network
import os

def build_doc_graph(doc_infos, output_path="output/graph.html"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    G = nx.Graph()

    for name, info in doc_infos.items():
        label = f"{name}\n({info.get('type', '未知')})"
        G.add_node(name, title=info["summary"], label=label)

    names = list(doc_infos.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            n1, n2 = names[i], names[j]
            tags1, tags2 = set(doc_infos[n1]["tags"]), set(doc_infos[n2]["tags"])
            common = tags1 & tags2
            if common:
                G.add_edge(n1, n2, label="、".join(common))

    net = Network(height="800px", width="100%", directed=False, notebook=False)
    net.from_nx(G)
    net.show_buttons(filter_=['physics'])
    net.show(output_path)
    print("图谱已生成:", output_path)
```

---

## 📤 5. `app/export_dify.py`

```python
import json, os

def export_to_dify_format(doc_infos, output_file="output/dify_dataset.json"):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    arr = []
    for name, info in doc_infos.items():
        arr.append({
            "id": name,
            "content": info["summary"],
            "metadata": {
                "tags": info["tags"],
                "type": info.get("type", "其它")
            }
        })
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)
    print("✅ Dify 数据已导出:", output_file)
```

---

## ✅ 运行方式

1. 确保已安装依赖：

```bash
pip install transformers torch pandas networkx pyvis pymupdf
```

2. 将 CSV 文件放入 `data/csvs/` 目录。

3. 运行主程序：

```bash
python run.py
```

---

需要我打包成 ZIP 或进一步添加 Web 页面/接口吗？
