# GraphMind 2.4-csv处理
> 下面是一个完整文档间项目流程与代码，读取 CSV 文件的第一列内容作为文档内容，通过大模型（如 ChatGLM3）提取总结、标签、类型，归属组并生成知识图谱和 Dify 可识别格式导出。

## 🔃 1 流程

### 📄 1.1 文档预处理  
先提取csv第一列（为什么不用pdf：文章太大，读不全，chatgml3模型最大输入8192字，文件大处理不了）  

### 🤖 1.2 用大模型（chatgml3）读取  
抓住关键信息，梳理文章内容  
```
    "请阅读以下文档内容，并“严格”按照格式输出：\n"
    "【总结】30字简洁总结全文核心内容；\n"
    "【标签】提取5~10个主题相关标签，使用顿号或逗号分隔，标签参考工厂工艺，打印机关系维护、打印日志管理、标签补印、工序调整、打散标签；\n"
    "【类型】从以下类别中选择最贴近的一个：\n"
    "综述，具体业务，产品基础知识，操作指导书，维修文档；\n"
    "【归属组】请提取本文件属于哪一组（如工艺，...），如无法判断则填“未知”。\n\n"
```
> 可手动更改
```python
{
    "部门A": {
        "summary": "负责A业务",
        "type": "部门具体业务",
        "tags": [...],
        "group": "A"
    },
    ...
}
```

### ↪️ 1.3 生成文档名的“节点” & “边”
节点为文件名，文档打上标签，在同一归属组下，通过类型的层级来处理（综述->业务讲解->产品基础知识->操作指导书->维修文档）  

### ✏️ 1.4 绘制知识图谱
用可用网页观看（双击居中，放大缩小，鼠标悬停显示段落内容）  

### 📁 1.5 保存
保存html & Dify可读格式文档（csv）  

---

## 2 代码

### 📁 2.0 项目结构

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
│   └── dify_dataset.csv
```

---

### 🔧 2.1 `run.py`

```python
from app.extract_csv import load_all_csvs
from app.analyze_docs import process_document
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format
import json, os

def main():
    csv_dir = "data/csvs"
    docs = load_all_csvs(csv_dir)
    current_names = set(docs.keys())  # 当前存在的文件名
    done_file = "output/processed.json"
    doc_infos = {}

    # 加载已处理文档信息
    if os.path.exists(done_file):
        with open(done_file, "r", encoding="utf-8") as f:
            doc_infos = json.load(f)

        # ✅ 自动删除已不存在的文档信息
        removed = []
        for name in list(doc_infos.keys()):
            if name not in current_names:
                removed.append(name)
                del doc_infos[name]

        if removed:
            print(f"🗑️ 以下文档已被删除，相关信息也已移除: {removed}")
            with open(done_file, "w", encoding="utf-8") as f:
                json.dump(doc_infos, f, ensure_ascii=False, indent=2)

    # 处理新文档
    for name, text in docs.items():
        if name in doc_infos:
            print(f"✅ 已处理: {name}，跳过")
            continue
        print(f"\n🚀 处理中: {name}")
        summary, tags, doc_type, group = process_document(text, fname=name)
        if summary:
            doc_infos[name] = {
                "summary": summary,
                "tags": tags,
                "type": doc_type,
                "group": group
            }
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

### 📄 2.2 `app/extract_csv.py`

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

### 🧠 2.3 `app/analyze_docs.py`

```python
from transformers import AutoTokenizer, AutoModel
import torch
import time
import re

def init_model(device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
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
    # device = "cpu"  # 强制使用CPU
    tokenizer, model, device = init_model(device)

    prompt = (
        "请阅读以下文档内容，并“严格”按照格式输出：\n"
        "【总结】30字简洁总结全文核心内容；\n"
        "【标签】提取5~10个主题相关标签，使用顿号或逗号分隔；\n"
        "【类型】从以下类别中选择最贴近的一个：\n"
        "部门具体业务、业务下产品基础知识、操作指导书、其他；\n"
        "【归属组】请提取本文件属于哪一组（如供应制作部门、星星海部门、AI部门...），如无法判断则填“未知”。\n\n"
        f"文档内容如下：\n{text[:6000]}"
    )

    response = safe_chat(tokenizer, model, prompt)
    if not response:
        return None, [], "其它"

    return parse_summary_tags_type_group(response)

def parse_summary_tags_type_group(raw_text):
    sum_match = re.search(r"[【\[]总结[】\]]\s*(.*?)(?:\n|【|\[)", raw_text, re.S)
    tag_match = re.search(r"[【\[]标签[】\]]\s*(.*?)(?:\n|【|\[)", raw_text, re.S)
    type_match = re.search(
        r"[【\[]类型[】\]]\s*(部门具体业务|业务下产品基础知识|操作指导书|其他)", raw_text)
    group_match = re.search(r"[【\[]归属组[】\]]\s*([A-Za-z0-9\u4e00-\u9fa5]+)", raw_text)

    summary = sum_match.group(1).strip() if sum_match else "无总结"
    tags = [t.strip() for t in re.split(r"[、,，\s]+", tag_match.group(1)) if t.strip()] if tag_match else ["未提取"]
    doc_type = type_match.group(1).strip() if type_match else "其他"
    group = group_match.group(1).strip() if group_match else "未知"

    print(f"✅ 解析成功：类型={doc_type}，标签={tags}，归属组={group}")
    return summary, tags, doc_type, group

```

---

### 🌐 2.4 `app/build_graph.py`

```python
import networkx as nx
from pyvis.network import Network
import os

# 定义文档类型层级顺序
TYPE_ORDER = [
    "部门具体业务",
    "业务下产品基础知识",
    "操作指导书"
]

def build_doc_graph(doc_infos, output_path="output/graph.html"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    G = nx.DiGraph()

    # 添加节点
    for name, info in doc_infos.items():
        label = f"{name}\n({info.get('type', '未知')})"
        G.add_node(name, title=info.get("summary", ""), label=label)

    # 分组处理每条线索（比如 A线、B线）
    groups = {}
    for name, info in doc_infos.items():
        group = info.get("group", "default")
        groups.setdefault(group, []).append((name, info))

    # 根据 TYPE_ORDER 添加组内层级边
    for group_docs in groups.values():
        # 建立 type ➝ name 映射
        type_to_name = {info["type"]: name for name, info in group_docs}
        for i in range(len(TYPE_ORDER) - 1):
            t1, t2 = TYPE_ORDER[i], TYPE_ORDER[i + 1]
            if t1 in type_to_name and t2 in type_to_name:
                G.add_edge(type_to_name[t1], type_to_name[t2], label=f"{t1} ➝ {t2}")

    # 添加：根据相同标签连接所有文档（跨组也可以）
    names = list(doc_infos.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1, n2 = names[i], names[j]
            tags1 = set(doc_infos[n1].get("tags", []))
            tags2 = set(doc_infos[n2].get("tags", []))
            common_tags = tags1 & tags2
            if common_tags:
                # 为避免和层级边混淆，使用不同颜色/样式（在可视化中定义）
                G.add_edge(n1, n2, label="、".join(common_tags), color="#888888", arrows="")

    # 可视化
    net = Network(height="800px", width="100%", directed=True, notebook=False)
    net.from_nx(G)
    net.show_buttons(filter_=['physics'])
    net.show(output_path, notebook=False)
    print("图谱已生成:", output_path)

```

---

### 📤 2.5 `app/export_dify.py`

```python
import json
import os
import csv

def export_to_dify_format(doc_infos, output_file="output/dify_dataset.csv"):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 将数据写入CSV文件
    with open(output_file, "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # 写入CSV文件的表头
        writer.writerow(["id", "content", "tags", "type", "group"])
        # 写入数据
        for name, info in doc_infos.items():
            writer.writerow([
                name,
                info["summary"],
                ", ".join(info["tags"]),
                info.get("type", "其它"),
                info.get("group", "无")
            ])
    
    print("Dify 数据已导出:", output_file)

```

---

### ✅ 2.6 运行方式

1. 确保已安装依赖：

```bash
pip install transformers torch pandas networkx pyvis pymupdf csv
```

2. 将 CSV 文件放入 `data/csvs/` 目录。

3. 运行主程序：

```bash
python run.py
```

---

