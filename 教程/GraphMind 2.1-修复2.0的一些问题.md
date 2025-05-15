```
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

