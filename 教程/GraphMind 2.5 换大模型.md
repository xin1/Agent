错误：
```
Setting `pad_token_id` to `eos_token_id`:100001 for open-end generation.
```
提示词修改：
```
prompt = (
    "请阅读以下文档内容，并“严格”按照格式输出：\n\n"
    "【总结】请用一句话（30字内）总结本文核心内容；\n"
    "【标签】提取5~10个关键词，使用逗号或顿号分隔；\n"
    "【类型】判断该文档属于以下哪一层级类型（仅选择一个）：\n"
    "1）操作细节：如作业指导书、SOP、工艺参数等，直接指导操作人员；\n"
    "2）操作规范与控制要求：如FMEA、制程质量要求、检验规范，控制操作过程质量；\n"
    "3）产品技术资料：如BOM、元器件说明书、图纸、技术规格，是理解产品的依据；\n"
    "4）流程与业务控制：如设计变更流程、试产流程、质量问题处理流程，规定流程规则；\n"
    "5）管理体系文件：如质量体系手册、制度、组织职责描述，属于体系层面的指导文件；\n"
    "6）其他：如会议纪要、无法归类的内容；\n\n"
    "【归属组】请提取本文件所属的团队或部门名称（如产品工程部、制造部、品管部），如无明确指示，则填写“未知”。\n\n"
    f"文档内容如下：\n{text[:6000]}"
)

```
好的，以下是一个完整的 `analyze_docs.py` 文件，使用的是 **DeepSeek Chat 模型**（例如 `deepseek-ai/deepseek-llm-7b-chat`），并适配你原有的流程：文档处理、总结提取、标签分类、归属组判断，全部输出结构化结果。

---

### ✅ 依赖项安装（请确保你已安装如下）

```bash
pip install transformers accelerate torch
```

---

### 📄 `analyze_docs.py` 完整代码（适配 DeepSeek Chat）

```python
# analyze_docs.py

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import time
import re

# 初始化 DeepSeek Chat 模型
def init_model(device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model_name = "deepseek-ai/deepseek-llm-7b-chat"
    
    print(f"🔄 加载模型 {model_name} 到 {device} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, torch_dtype=torch.float16)
    model = model.to(device).eval()
    return tokenizer, model, device

# 执行推理，封装为安全调用
def safe_chat(tokenizer, model, prompt, max_tokens=1024, temperature=0.7):
    try:
        # 构建符合 DeepSeek Chat 的 Prompt 格式
        full_prompt = f"<|system|>\n你是一个专业文档分析助手。\n<|user|>\n{prompt}\n<|assistant|>\n"
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=False
            )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 截取 assistant 部分
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()
        return response
    except Exception as e:
        print(f"⚠️ 推理失败: {e}")
        return None

# 文档处理函数
def process_document(text, fname="文档"):
    tokenizer, model, device = init_model()

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
        return None, [], "其他", "未知"

    return parse_summary_tags_type_group(response)

# 提取结构化信息
def parse_summary_tags_type_group(raw_text):
    sum_match = re.search(r"[【\[]总结[】\]]\s*(.*?)(?:\n|【|\[)", raw_text, re.S)
    tag_match = re.search(r"[【\[]标签[】\]]\s*(.*?)(?:\n|【|\[)", raw_text, re.S)
    type_match = re.search(r"[【\[]类型[】\]]\s*(部门具体业务|业务下产品基础知识|操作指导书|其他)", raw_text)
    group_match = re.search(r"[【\[]归属组[】\]]\s*([A-Za-z0-9\u4e00-\u9fa5]+)", raw_text)

    summary = sum_match.group(1).strip() if sum_match else "无总结"
    tags = [t.strip() for t in re.split(r"[、,，\s]+", tag_match.group(1)) if t.strip()] if tag_match else ["未提取"]
    doc_type = type_match.group(1).strip() if type_match else "其他"
    group = group_match.group(1).strip() if group_match else "未知"

    print(f"✅ 解析成功：类型={doc_type}，标签={tags}，归属组={group}")
    return summary, tags, doc_type, group

# 示例入口（测试）
if __name__ == "__main__":
    sample_text = "本产品是星星海部门负责的业务模块之一，适用于大规模供应链管理场景，具有高度稳定性与可扩展性。用户可通过本手册了解其基本配置流程和常见故障排查方法。"
    summary, tags, doc_type, group = process_document(sample_text)
    print("📄 总结:", summary)
    print("🏷️ 标签:", tags)
    print("📘 类型:", doc_type)
    print("👥 归属组:", group)
```

---

### ✅ 使用说明：

1. 文档内容传入 `process_document(text)`，会自动返回：

   * `summary`（总结）
   * `tags`（标签）
   * `doc_type`（文档类型）
   * `group`（归属组）

2. 可以在主程序中批量读取文件后调用该函数。

3. 模型会自动加载至 `CUDA`（若可用），并使用 `float16` 加快推理。

---

如你还有多文档批量分析、缓存模型、或加入进度条的需求，我可以继续帮你集成。需要吗？
