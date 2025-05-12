报错
```
config.json: 100%|███████████████████████████████████████████████████████████████████████| 570/570 [00:00<00:00, 3.79MB/s]
D:\Software\Anaconda3\lib\site-packages\huggingface_hub\file_download.py:143: UserWarning: `huggingface_hub` cache-system uses symlinks by default to efficiently store duplicated files but your machine does not support them in C:\Users\l50011746\.cache\huggingface\hub\models--bert-base-cased. Caching files will still work but in a degraded version that might require more space on your disk. This warning can be disabled by setting the `HF_HUB_DISABLE_SYMLINKS_WARNING` environment variable. For more details, see https://huggingface.co/docs/huggingface_hub/how-to-cache#limitations.
    return func(*args, **kwargs)  File "D:\Software\Anaconda3\lib\site-packages\transformers\modeling_utils.py", line 4260, in from_pretrained    checkpoint_files, sharded_metadata = _get_resolved_checkpoint_files(
  File "D:\Software\Anaconda3\lib\site-packages\transformers\modeling_utils.py", line 1080, in _get_resolved_checkpoint_files    raise EnvironmentError(
OSError: bert-base-cased does not appear to have a file named pytorch_model.bin but there is a file for TensorFlow weights. Use `from_tf=True` to load this model from those weights.

distilbert/distilbert-base-cased-distilled-squad does not appear to have a file named pytorch_model.bin but there is a file for TensorFlow weights. Use `from_tf=True` to load this model from those weights.

RuntimeError: Failed to import transformers.pipelines because of the following error (look up to see its traceback):       
No module named 'torch.distributed.tensor'

ValueError: Could not load model distilbert-base-cased-distilled-squad with any of the following classes: (<class 'transformers.models.auto.modeling_auto.AutoModelForQuestionAnswering'>, <class 'transformers.models.distilbert.modeling_distilbert.DistilBertForQuestionAnswering'>).
```
```python
import os
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import networkx as nx

# 加载预训练模型
model_name = "distilbert-base-uncased"  # 可以根据需要调整
model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 读取多个 CSV 文件并合并为一个 DataFrame
directory = 'path_to_your_csv_files'
dataframes = []

for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        filepath = os.path.join(directory, filename)
        df = pd.read_csv(filepath)
        df.columns = ['Title', 'Content']  # 确保列名一致
        df['Document'] = filename  # 添加一个列记录文件名
        dataframes.append(df)

combined_df = pd.concat(dataframes, ignore_index=True)

# 定义段落分割函数
def split_into_paragraphs(text):
    return [para.strip() for para in text.split('\n') if para.strip()]

combined_df['Paragraphs'] = combined_df['Content'].apply(split_into_paragraphs)

# 使用 BERT 模型提取段落之间的关系
def extract_relationships(paragraphs, title, document):
    relationships = []
    for i, para in enumerate(paragraphs):
        # 每个段落和其它段落之间进行关系推理
        for j, other_para in enumerate(paragraphs):
            if i != j:
                # 构造输入文本对
                inputs = tokenizer(para, other_para, return_tensors="pt", padding=True, truncation=True)
                outputs = model(**inputs)
                score = outputs.logits[0][1].item()  # 假设我们关心的是相关性的分数
                if score > 0.5:  # 选择一个阈值来判断是否为相关段落
                    relationships.append({
                        'source': para,
                        'target': other_para,
                        'relation': 'related',  # 可以根据具体的任务修改关系描述
                        'score': score,
                        'document': document
                    })
    return relationships

# 构建知识图谱
all_relationships = []
for _, row in combined_df.iterrows():
    title = row['Title']
    document = row['Document']
    paragraphs = row['Paragraphs']
    relationships = extract_relationships(paragraphs, title, document)
    all_relationships.extend(relationships)

# 创建 NetworkX 图
G = nx.Graph()

# 添加节点和边
for rel in all_relationships:
    G.add_node(rel['source'], label=rel['source'])
    G.add_node(rel['target'], label=rel['target'])
    G.add_edge(rel['source'], rel['target'], relation=rel['relation'], score=rel['score'])

# 输出知识图谱的一些基本信息
print(f"Number of nodes: {G.number_of_nodes()}")
print(f"Number of edges: {G.number_of_edges()}")

# 可选：保存为图数据文件
nx.write_gml(G, 'knowledge_graph.gml')

# 可视化知识图谱（可选）
import matplotlib.pyplot as plt
pos = nx.spring_layout(G)
plt.figure(figsize=(12, 12))
nx.draw(G, pos, with_labels=True, node_size=500, node_color='skyblue', font_size=10, font_weight='bold')
plt.title('Knowledge Graph')
plt.show()

```
使用 `transformers` 库来替代 GPT 模型进行关系提取是一个非常好的选择。你可以使用 Hugging Face 提供的预训练模型来进行文本分析和关系提取。以下是如何使用 `transformers` 和 `pipeline` 来完成关系提取的完整流程。

### 步骤概览

1. **加载多个 CSV 文件并读取数据**
2. **将内容分割为段落**
3. **使用 Hugging Face 的 `transformers` 进行关系提取**
4. **构建知识图谱的数据结构**
5. **可视化知识图谱**

---

### 1. 读取多个 CSV 文件

假设你有多个 CSV 文件，每个文件的格式是：第一列是标题，第二列是内容。首先需要读取这些文件并合并成一个统一的 DataFrame。

```python
import os
import pandas as pd

# 设置包含 CSV 文件的目录路径
directory = 'path_to_csv_files'

# 初始化一个空的 DataFrame 列表
dataframes = []

# 遍历目录中的所有文件
for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        filepath = os.path.join(directory, filename)
        df = pd.read_csv(filepath)
        # 统一列名为 'Title' 和 'Content'
        df.columns = ['Title', 'Content']
        # 添加一个列记录文件名
        df['Document'] = filename
        dataframes.append(df)

# 合并所有 DataFrame
combined_df = pd.concat(dataframes, ignore_index=True)
```

---

### 2. 将内容分割为段落

每个文档的内容字段可能包含多个段落，因此需要将其按段落进行分割。

```python
# 定义段落分割函数
def split_into_paragraphs(text):
    return [para.strip() for para in text.split('\n') if para.strip()]

# 应用段落分割
combined_df['Paragraphs'] = combined_df['Content'].apply(split_into_paragraphs)
```

---

### 3. 使用 Hugging Face 的 `transformers` 进行关系提取

你可以使用 Hugging Face 提供的模型（如 BERT 或 RoBERTa）来提取段落之间的关系。这里我们使用问答模型来生成关系信息。

**安装依赖：**

```bash
pip install transformers torch
```

**代码示例：**

```python
from transformers import pipeline

# 加载预训练的问答模型
qa_pipeline = pipeline("question-answering")

def extract_relationships_with_transformers(paragraphs, title, document):
    relationships = []
    for para in paragraphs:
        question = f"该段落与其他段落的关系是什么？\n段落：{para}"
        context = "请通过上下文给出相关的关系"
        
        # 使用问答模型提取关系
        result = qa_pipeline(question=question, context=context)
        relationships.append({
            'source': para,
            'target': result['answer'],
            'relation': 'related'
        })
    return relationships

# 提取所有文档的关系
all_relationships = []
for index, row in combined_df.iterrows():
    title = row['Title']
    document = row['Document']
    paragraphs = row['Paragraphs']
    relationships = extract_relationships_with_transformers(paragraphs, title, document)
    all_relationships.extend(relationships)
```

---

### 4. 构建知识图谱的数据结构

通过提取的关系构建知识图谱的节点和边结构。

```python
# 构建节点和边
nodes = set()
edges = []

for rel in all_relationships:
    source = rel['source']
    target = rel['target']
    relation = rel['relation']
    nodes.update([source, target])
    edges.append({'source': source, 'target': target, 'relation': relation})

# 转换为列表
nodes = [{'id': node} for node in nodes]
```

---

### 5. 可视化知识图谱

你可以将构建的知识图谱通过可视化库如 `D3.js` 展示。以下是一个简单的 HTML 示例，展示了如何用 `D3.js` 渲染图谱。

```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>知识图谱可视化</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        .node circle { fill: #69b3a2; }
        .link { stroke: #999; stroke-opacity: 0.6; }
    </style>
</head>
<body>
    <svg width="800" height="600"></svg>
    <script>
        // 假设您已将 nodes 和 edges 数据嵌入到此处
        const graph = {
            nodes: /* 插入 nodes 数据 */,
            links: /* 插入 edges 数据 */
        };

        const svg = d3.select("svg"),
              width = +svg.attr("width"),
              height = +svg.attr("height");

        const simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));

        const link = svg.append("g")
            .attr("stroke", "#999")
            .selectAll("line")
            .data(graph.links)
            .enter().append("line")
            .attr("stroke-width", 2);

        const node = svg.append("g")
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .selectAll("circle")
            .data(graph.nodes)
            .enter().append("circle")
            .attr("r", 10)
            .attr("fill", "#69b3a2")
            .call(drag(simulation));

        node.append("title")
            .text(d => d.id);

        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
        });

        function drag(simulation) {
            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }

            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }

            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }

            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }
    </script>
</body>
</html>
```

---

### 总结

* 使用 `transformers` 库中的 `pipeline` 可以方便地提取文本之间的关系。
* 你可以从多个 CSV 文件中加载数据，分割成段落，使用模型提取每个段落之间的关系。
* 然后可以构建知识图谱，最后通过可视化工具如 `D3.js` 展示该图谱。

如果你遇到任何问题，随时提问！

---

如果您需要进一步的帮助，例如如何部署此应用或处理更复杂的文档结构，请随时提问！
