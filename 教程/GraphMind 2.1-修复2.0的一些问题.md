```
[
  {
    "id": "p-AI技术入门分享-五不同模式智能体 0316.pdf",
    "summary": "本文档介绍了AI智能体系统中的四种关键模式：链式工作流、并行化工作流、路由工作流和编排器-工作者模式。每种模式都有其适用场景和优点，可以根据任务的特点和需求选择合适的工作模式以提高效率和准确性。",
    "tags": ""
  },
  {
    "id": "p-供应制造自有知识库（DeepSeek R1）模型部署及工程数字人方案0225-2.pdf",
    "summary": "本文主要介绍了Security Level为confidential的供应制造自有知识库（DeepSeek R1）模型部署及工程数字人方案，并结合智能制造未来规划，打造智能制造领域“小战颅”和“小千手观音”系统。主要内容包括AI在军事系统中的应用成果，结合智能制造未来规划，以及“小战颅”系统的知识体系架构。",
    "tags": ""
  },
  {
    "id": "p-制造工艺概述.pdf",
    "summary": "这是一份关于产品制造工艺的概述，内容包括单板制造工艺、整机制造工艺和SMT制造工艺。通过对各工序工艺过程和关键质量风险管控要点的介绍，提升了全流程质量意识。主要标签为：制造工艺、产品制造、SMT工艺、PCB制造。\n\n第2段：【总结】该文档主要介绍了单板制造工艺中的SMT焊接/压接制造工艺、整机制造工艺以及SMT制造工艺的相关内容，包括焊接/压接制造工艺、单板装配制造工艺、测试/维修等环节。其中，又详细介绍了各种制造工艺的过程、原理、设备及关键质量控制要点。此外，还提到了回流焊工艺、AOI自动光学检测、X-Ray设备及检测原理等相关内容。",
    "tags": ""
  }
]


Both `max_new_tokens` (=512) and `max_length`(=8192) seem to have been set. `max_new_tokens` will take precedence. Please refer to the documentation for more information. (https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)

RuntimeError: The following operation failed in the TorchScript interpreter.
Traceback of TorchScript (most recent call last):
  File "C:\Users\Administrator\.cache\huggingface\modules\transformers_modules\THUDM\chatglm3-6b\e9e0406d062cdb887444fe5bd546833920abd4ac\modeling_chatglm.py", line 182, in apply_rotary_pos_emb
    )
    x_out2 = x_out2.flatten(3)
    return torch.cat((x_out2, x_pass), dim=-1)
           ~~~~~~~~~ <--- HERE
RuntimeError: CUDA out of memory. Tried to allocate 20.00 MiB. GPU 0 has a total capacity of 44.67 GiB of which 18.94 MiB is free. Of the allocated memory 12.13 GiB is allocated by PyTorch, and 27.33 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)   


RuntimeError:
        An attempt has been made to start a new process before the
        current process has finished its bootstrapping phase.

        This probably means that you are not using fork to start your
        child processes and you have forgotten to use the proper idiom
        in the main module:

            if __name__ == '__main__':
                freeze_support()
                ...

        The "freeze_support()" line can be omitted if the program
        is not going to be frozen to produce an executable.
```
以下是完整支持 **多 GPU 并行** 的代码版本。我们会对 `analyze_docs.py` 和 `run.py` 两个模块做修改，并保证每个进程自动分配不同 GPU，以避免重复占用同一块显卡内存。

---

## 📁 目录结构（保持一致）：

```
your_project/
├── app/
│   ├── extract_text.py
│   ├── analyze_docs.py       ← ✅ 修改
│   ├── build_graph.py
│   ├── export_dify.py
├── data/
│   └── pdfs/                 ← 存放 PDF 文档
├── run.py                    ← ✅ 修改
```

---

## ✅ `app/analyze_docs.py`（支持 GPU ID 自动分配）

```python
# app/analyze_docs.py
from transformers import AutoTokenizer, AutoModel
import torch

def init_model(gpu_id=0):
    device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True).half().to(device).eval()
    return tokenizer, model, device

def chunk_text(text, max_len=1500):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]

def summarize_and_tag_single(args):
    filename, text, gpu_id = args
    tokenizer, model, device = init_model(gpu_id)
    chunks = chunk_text(text)
    combined_summary = ""
    for i, chunk in enumerate(chunks):
        prompt = f"请总结以下文档内容并提取3-5个标签，输出格式：【总结】xxx【标签】xxx：\n{chunk}"
        response, _ = model.chat(tokenizer, prompt, history=[], max_new_tokens=512)
        combined_summary += f"\n第{i+1}段：{response}\n"
    return filename, combined_summary

def parse_summary_and_labels(text):
    import re
    summary_match = re.search(r"【总结】(.*?)【标签】", text, re.S)
    tags_match = re.findall(r"【标签】(.*?)\n?", text, re.S)

    summary = summary_match.group(1).strip() if summary_match else text
    tags = []
    for tag_line in tags_match:
        tags += [t.strip("：:，, ") for t in tag_line.split("、") if t.strip()]
    return summary.strip(), list(set(tags))
```

---

## ✅ `run.py`（自动分配 GPU 给不同进程）

```python
# run.py
# run.py
import os
from app.extract_text import extract_text_from_pdf
from app.analyze_docs import summarize_and_tag_single, parse_summary_and_labels
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format
from concurrent.futures import ProcessPoolExecutor
import torch
from tqdm import tqdm

def main():
    pdf_dir = "data/pdfs"
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]

    # Step 1: 提取文本
    pdf_texts = {}
    for file in tqdm(pdf_files, desc="提取PDF文本"):
        text = extract_text_from_pdf(os.path.join(pdf_dir, file))
        pdf_texts[file] = text

    # Step 2: 多GPU并行调用
    gpu_count = torch.cuda.device_count()
    print(f"🖥️ 检测到 {gpu_count} 块 GPU，准备并行处理...")

    task_args = []
    for idx, (fname, text) in enumerate(pdf_texts.items()):
        assigned_gpu = idx % gpu_count
        task_args.append((fname, text, assigned_gpu))

    doc_infos = {}
    with ProcessPoolExecutor(max_workers=gpu_count) as executor:
        results = executor.map(summarize_and_tag_single, task_args)
        for fname, result in tqdm(results, total=len(task_args), desc="分析文档"):
            summary, tags = parse_summary_and_labels(result)
            print(f"📄 {fname} 标签：{tags}")
            doc_infos[fname] = {"summary": summary, "tags": tags}

    # Step 3: 构建图谱
    build_doc_graph(doc_infos)

    # Step 4: 导出为 Dify 格式
    export_to_dify_format(doc_infos)

if __name__ == "__main__":
    main()

```


---

## ⚠️ 注意事项

| 事项    | 内容                                               |
| ----- | ------------------------------------------------ |
| 多卡环境  | 默认轮流分配 GPU，例如文档 0 → GPU0，文档 1 → GPU1，文档 2 → GPU0 |
| 内存限制  | 每个进程独立加载一次模型，每个显卡约占用 13GB 显存（chatglm3-6b 半精度）    |
| 单卡也兼容 | 如果只有一块 GPU，仍然支持，只是不会真正并行                         |

---

## ✅ 效果示例（输出）：

```bash
🖥️ 检测到 2 块 GPU，准备并行处理...
分析文档: 100%|████████████████| 4/4 [00:38<00:00,  9.61s/it]
📄 doc1.pdf 标签：['算法', '深度学习']
📄 doc2.pdf 标签：['电机控制', '自动化']
...
```

---

如需支持显卡手动指定，或结合 `ray` / `deepspeed` / `accelerate` 优化模型加载，也可以再进一步升级。是否需要我提供 `ray` 并行框架的版本？
明白了！你已经解决了并行多GPU执行问题，但**生成的知识图谱中，文档节点之间没有“边”**（如“同属产品”、“内容相关”、“包含”等关系）。

---

## 🧠 问题本质：

目前的 `build_doc_graph.py` 脚本 **只是将每个文档作为一个独立节点**，并未分析文档间的语义关系，因此图中是“无边孤岛”。

---

## ✅ 目标：

你希望自动判断 **文档之间的语义关系（如主题相近、内容包含、来自同一产品线）**，并在图中添加 **边（Edge）** 表示这些关系。

---

## ✅ 改进思路：

我们新增一段逻辑来：

1. 通过 BERT 等模型提取每篇文档的 embedding（向量表示）
2. 计算 **文档间相似度**
3. 当相似度高于某阈值（如 0.7）时添加边（关系名可默认是“内容相关”或“产品相关”）

---

## ✅ 改进后的 `build_doc_graph.py`

以下是完整可运行的版本（含边生成逻辑）：

```python
# app/build_graph.py
from pyvis.network import Network
import networkx as nx
from sentence_transformers import SentenceTransformer, util
import torch
import os

def build_doc_graph_web(doc_infos, sim_threshold=0.7, output_path="output/graph.html"):
    os.makedirs("output", exist_ok=True)
    G = nx.Graph()
    doc_names = list(doc_infos.keys())
    summaries = [doc_infos[name]["summary"] for name in doc_names]

    # 加载轻量模型用于相似度
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cuda" if torch.cuda.is_available() else "cpu")
    embeddings = model.encode(summaries, convert_to_tensor=True)

    # 添加节点
    for name in doc_names:
        G.add_node(name, label=name)

    # 添加边（基于语义相似度）
    for i in range(len(doc_names)):
        for j in range(i + 1, len(doc_names)):
            sim = util.cos_sim(embeddings[i], embeddings[j]).item()
            if sim >= sim_threshold:
                G.add_edge(doc_names[i], doc_names[j], weight=round(sim, 2), label="相似")

    # 用 pyvis 可视化为网页
    net = Network(height="800px", width="100%", notebook=False, font_color="black", directed=False)
    net.from_nx(G)
    net.show_buttons(filter_=['physics'])  # 显示布局调节按钮
    net.show(output_path,notbook=Flase)

    print(f"✅ 交互式知识图谱网页已生成：{output_path}")

```

---

## 🧪 示例效果（含边）：

* **节点**：PDF 文档文件名
* **边**：相似度 > 0.7 时加“相关”边
* **支持中文摘要**

---

## ✅ 依赖说明（新用到）：

```bash
pip install sentence-transformers
```

---

## 🚀 可选增强功能：

| 功能       | 描述                                  |
| -------- | ----------------------------------- |
| 自定义关系边类型 | 使用规则或大模型判断“包含”、“引用”、“产品相关”等         |
| 显示相似度分数  | 边标签加上相似度，如 "内容相关(0.82)"             |
| 交互式图谱    | 用 pyvis / D3.js / Streamlit 显示可点击图谱 |
| 多语种支持    | 当前模型支持中英文混合文档                       |

---

是否希望我继续帮你构建交互式可视化（如网页点击展示）？

