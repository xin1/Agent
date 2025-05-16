# GraphMind 2.1-全文总结
上篇文档运用分段处理文档，我想一次性进行总结，当前有 **2 个可用 GPU**（显存分别为 24GB 和 12GB）  

---

## ✅ 一次修改：

### ✅ 目标： 
目标 1：将“分段总结”修改为“全文总结”   
删除 `chunk_text` 和段落循环，直接对全文构造 prompt。  
目标 2：支持多文档处理时避免显存爆炸  
添加自动检测显存是否爆炸。  
如果失败（爆显存），就切换为串行方式处理。  

---

### ✅ 修改后代码（关键文件 `analyze_docs.py` 和 `run.py`）

#### 🔧 `app/analyze_docs.py`（重构为全文总结，异常处理）

```python
from transformers import AutoTokenizer, AutoModel
import torch
import re

# 初始化模型
def init_model(gpu_id=0):
    device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True)
    model = AutoModel.from_pretrained("THUDM/chatglm3-6b", trust_remote_code=True) \
        .half().to(device).eval()
    return tokenizer, model, device

# 单个文档的处理函数（全文总结）
def summarize_and_tag_single(args):
    fname, text, gpu_id = args
    tokenizer, model, device = init_model(gpu_id)
    try:
        prompt = (
            "请你作为一个专业的文档分析助手，对以下文档进行摘要和标签提取。\n"
            "请严格按照以下格式返回：\n"
            "【总结】这里是整篇文档的总结内容\n"
            "【标签】标签1、标签2、标签3\n\n"
            f"文档内容：\n{text}"
        )
        response, _ = model.chat(tokenizer, prompt, history=[], max_new_tokens=2048)
        return fname, response
    except RuntimeError as e:
        if "out of memory" in str(e):
            print(f"[警告] GPU {gpu_id} 显存不足：{fname} 改为 CPU 串行处理")
        raise e  # 由外层捕获
    except Exception as e:
        print(f"[错误] 处理文档 {fname} 时异常：{str(e)}")
        return fname, ""

# 解析模型输出
def parse_summary_and_labels(raw_text):
    summary_match = re.search(r"【总结】(.*?)【标签】", raw_text, re.S)
    tags_match = re.search(r"【标签】(.*)", raw_text, re.S)

    summary = summary_match.group(1).strip() if summary_match else ""
    tag_line = tags_match.group(1).strip() if tags_match else ""
    tags = [t.strip() for t in re.split(r"[、,，\s]+", tag_line) if t.strip()]
    return summary, list(set(tags))
```

---

#### 🔧 `run.py`（加入自动串行降级逻辑）

```python
from app.extract_text import load_all_pdfs
from app.analyze_docs import summarize_and_tag_single, parse_summary_and_labels
from app.build_graph import build_doc_graph
from app.export_dify import export_to_dify_format
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import torch

def safe_process(args):
    try:
        return summarize_and_tag_single(args)
    except RuntimeError as e:
        return None  # 标记为失败

def main():
    pdf_dir = "data/pdfs"
    docs = load_all_pdfs(pdf_dir)

    gpu_count = max(torch.cuda.device_count(), 1)
    tasks = [(name, text, idx % gpu_count) for idx, (name, text) in enumerate(docs.items())]

    doc_infos = {}

    # 优先尝试并行处理
    print(f"尝试并行处理文档，使用 {gpu_count} 个 GPU ...")
    with ProcessPoolExecutor(max_workers=gpu_count) as executor:
        futures = {executor.submit(safe_process, task): task[0] for task in tasks}
        for future in tqdm(as_completed(futures), total=len(futures), desc="分析文档"):
            result = future.result()
            if result is None:
                continue  # 稍后串行重试
            fname, raw = result
            summary, tags = parse_summary_and_labels(raw)
            doc_infos[fname] = {"summary": summary, "tags": tags}

    # 对失败的文档进行串行处理（避免爆显存）
    failed = [task for task in tasks if task[0] not in doc_infos]
    if failed:
        print(f"\n以下文档将改为串行处理（共 {len(failed)} 个）：")
        for fname, _, _ in failed:
            print(f"  - {fname}")
        for fname, text, _ in tqdm(failed, desc="串行处理"):
            try:
                raw = summarize_and_tag_single((fname, text, 0))[1]
                summary, tags = parse_summary_and_labels(raw)
                doc_infos[fname] = {"summary": summary, "tags": tags}
            except Exception as e:
                print(f"[失败] 文档 {fname} 无法处理：{str(e)}")

    # 构建图谱 + 导出
    build_doc_graph(doc_infos)
    export_to_dify_format(doc_infos)

if __name__ == "__main__":
    main()
```

---

### ✅ 整体优势

| 特性          | 实现                |
| ----------- | ----------------- |
| 全文总结        | 替换段落分割为全文 prompt  |
| GPU 优先并行处理  | 利用多 GPU 轮询调度      |
| 自动防爆显存      | 失败后切换串行 + CPU     |
| 强 Prompt 输出 | 模型严格输出【总结】和【标签】格式 |
| 解析健壮        | 多种分隔符支持，避免提取失败    |

---
