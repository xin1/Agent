```
index 9290 is out of bounds for dimension 0 with size 8192
```
```
from transformers import AutoTokenizer, AutoModel
import torch
import time
import re

def init_model(device='cuda'):
    tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = model.half().to(device).eval()
    return tokenizer, model, device

def safe_chat(tokenizer, model, prompt, max_tokens=1024):
    for attempt in range(3):
        try:
            return model.chat(tokenizer, prompt, history=[], max_new_tokens=max_tokens)[0]
        except Exception as e:
            print(f"⚠️ 模型推理失败 attempt {attempt+1}: {e}")
            time.sleep(2)
            max_tokens = max(512, max_tokens // 2)
            prompt = prompt[:4000]
    return None

def process_document(text, fname="文档"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
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
    def extract_field(pattern, text, fallback=""):
        match = re.search(pattern, text, re.S)
        return match.group(1).strip() if match else fallback

    summary = extract_field(r"【总结】(.*?)\n", raw_text)
    tags_str = extract_field(r"【标签】(.*?)\n", raw_text)
    type_raw = extract_field(r"【类型】(.*?)\n", raw_text)

    # 提取标签列表
    tags = [t.strip() for t in re.split(r"[、,，\s]+", tags_str) if t.strip()]
    tags = tags[:5] if len(tags) > 5 else tags

    # 类型必须在白名单中
    allowed_types = {"综述", "措施", "政策", "报告", "通知", "其它"}
    doc_type = type_raw if type_raw in allowed_types else "其它"

    return summary, tags, doc_type


```

---

## ✅ 自动降级处理策略总结

| 场景      | 降级策略                                     |
| ------- | ---------------------------------------- |
| 显存爆掉    | 截短输入文本（例如 `[:3000]`）、降低 `max_new_tokens` |
| 模型失败    | 捕捉异常、重试                                  |
| 无标签/无摘要 | 允许返回空，主流程中跳过处理即可                         |
| 中断后续跑   | 通过保存 `processed.json` 记录已完成文档            |

---

## ✅ 可选进阶（文档间关系判断）

你提到“有些是综述，有些是措施”，可以加一段模型判断类型：

在 prompt 中加入：

```
请判断该文档是“综述性总结”还是“具体措施”，并输出：
【类型】综述 / 措施
```

解析函数中加提取即可。是否需要我帮你加进来？

---

需要我打包为 ZIP 项目结构或整合自动重试日志系统也可以，告诉我即可。

好的，以下是完整更新后的项目代码，具备以下特性：

* ✅ 串行处理文档，避免显存爆炸；
* ✅ 使用 ChatGLM3 模型，对全文进行总结与标签提取；
* ✅ 自动识别文档类型（综述 / 措施）；
* ✅ 分析文档间的语义关系（例如：某综述对应了哪些措施）；
* ✅ 构建交互式图谱；
* ✅ 导出为 Dify 格式。

---

## ✅ 1. 项目结构

```
document_graph_project/
├── app/
│   ├── extract_text.py
│   ├── analyze_docs.py
│   ├── build_graph.py
│   └── export_dify.py
├── data/
│   └── pdfs/
├── output/
│   └── graph.html
├── run.py
└── requirements.txt
```

---

## ✅ 2. `app/extract_text.py`

```python
import fitz
import os

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texts = []
    for page in doc:
        txt = page.get_text().strip()
        if txt:
            texts.append(txt)
    return "\n".join(texts)

def load_all_pdfs(folder):
    data = {}
    for fn in os.listdir(folder):
        if fn.lower().endswith(".pdf"):
            path = os.path.join(folder, fn)
            data[fn] = extract_text_from_pdf(path)
    return data
```

---

## ✅ 3. `app/analyze_docs.py`

```python
from transformers import AutoTokenizer, AutoModel
import torch
import re

def init_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True).half().to(device).eval()
    return tokenizer, model, device

def analyze_document(text):
    tokenizer, model, device = init_model()

    prompt = (
        "请你作为科研助理，阅读以下PDF全文内容，提取核心摘要，总结3-7个高质量标签，"
        "并判断这篇文章是【综述】还是【具体措施】，最后尝试分析该文档可能与哪些其他主题存在关系。\n\n"
        "请严格按照以下格式输出：\n"
        "【总结】这里是文章的整体摘要\n"
        "【标签】标签1、标签2、标签3\n"
        "【类型】综述 / 措施\n"
        "【可能相关主题】主题1、主题2\n\n"
        f"文档全文如下：\n{text}"
    )

    response, _ = model.chat(tokenizer, prompt, history=[], max_new_tokens=1024)
    return response

def parse_response(response):
    summary = re.search(r"【总结】(.*?)\n", response, re.S)
    tags = re.search(r"【标签】(.*?)\n", response, re.S)
    dtype = re.search(r"【类型】(.*?)\n", response, re.S)
    related = re.search(r"【可能相关主题】(.*?)\n", response, re.S)

    def split_tags(s):
        return [t.strip() for t in re.split(r"[、,，\s]+", s) if t.strip()]

    return {
        "summary": summary.group(1).strip() if summary else "",
        "tags": split_tags(tags.group(1)) if tags else [],
        "type": dtype.group(1).strip() if dtype else "未知",
        "related": split_tags(related.group(1)) if related else [],
    }
```

---

## ✅ 4. `app/build_graph.py`

```python
import networkx as nx
from pyvis.network import Network
import os

def build_doc_graph(doc_infos, output_path="output/graph.html"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    G = nx.DiGraph()

    # 添加节点
    for name, info in doc_infos.items():
        G.add_node(name, title=info["summary"], label=f"{name}\n[{info['type']}]")

    # 建立“标签相交”边
    names = list(doc_infos.keys())
    for i in range(len(names)):
        for j in range(len(names)):
            if i == j: continue
            n1, n2 = names[i], names[j]
            doc1, doc2 = doc_infos[n1], doc_infos[n2]

            # 如果 n1 是综述，且 n2 的标签与 n1 的相关主题有交集
            if doc1["type"] == "综述":
                if set(doc2["tags"]) & set(doc1["related"]):
                    G.add_edge(n1, n2, label="综述→措施")

    net = Network(height="800px", width="100%", directed=True, notebook=False)
    net.from_nx(G)
    net.show_buttons(filter_=['physics'])
    net.show(output_path)
    print("图谱已生成:", output_path)
```

---

## ✅ 5. `app/export_dify.py`

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
                "type": info["type"],
                "related_topics": info["related"]
            }
        })
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)
    print("Dify 数据已导出:", output_file)
```

---

## ✅ 6. `run.py`

```python
from app.extract_text import load_all_pdfs
from app.analyze_docs import analyze_document, parse_response
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format
from tqdm import tqdm

def main():
    docs = load_all_pdfs("data/pdfs")
    doc_infos = {}

    for name, text in tqdm(docs.items(), desc="分析文档"):
        try:
            response = analyze_document(text)
            info = parse_response(response)
            doc_infos[name] = info
            print(f"{name} → 标签: {info['tags']} 类型: {info['type']}")
        except Exception as e:
            print(f"{name} 分析失败:", e)

    build_doc_graph(doc_infos)
    export_to_dify_format(doc_infos)

if __name__ == "__main__":
    main()
```

---

## ✅ 7. `requirements.txt`

```txt
transformers
torch
pymupdf
networkx
pyvis
tqdm
```

---

## ✅ 8. 使用说明

1. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

2. 将 PDF 文档放入：

   ```
   data/pdfs/
   ```

3. 运行主程序：

   ```bash
   python run.py
   ```

4. 输出结果：

* 可视化图谱：`output/graph.html`
* Dify 数据集：`output/dify_dataset.json`

---

如需进一步支持图片、音频、结构化表格提取等扩展，也可以继续集成。是否需要我为此提供 Docker 部署版本？
