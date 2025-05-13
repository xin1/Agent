gpu
```
import os
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from tqdm import tqdm
import networkx as nx
import matplotlib.pyplot as plt

# =================== 环境配置 ===================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# 加载中文预训练模型
model_name = "uer/roberta-base-finetuned-dianping-chinese"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device)

# =================== 加载CSV文件 ===================
directory = 'csv_files'
dataframes = []

for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        filepath = os.path.join(directory, filename)
        try:
            df = pd.read_csv(filepath, on_bad_lines='skip', encoding='utf-8')
            df.columns = ['Title', 'Content']  # 确保列名一致
            df['Document'] = filename
            dataframes.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

combined_df = pd.concat(dataframes, ignore_index=True)

# =================== 分段函数 ===================
def split_into_paragraphs(text):
    if isinstance(text, str):
        return [para.strip() for para in text.split('\n') if para.strip()]
    else:
        return []

combined_df['Paragraphs'] = combined_df['Content'].apply(split_into_paragraphs)

# =================== 段落关系抽取 ===================
def extract_relationships(paragraphs, title, document):
    relationships = []
    for i, para in enumerate(tqdm(paragraphs, desc=f'处理 {document}')):
        for j, other_para in enumerate(paragraphs):
            if i != j:
                inputs = tokenizer(para, other_para, return_tensors="pt", padding=True, truncation=True).to(device)
                with torch.no_grad():
                    outputs = model(**inputs)
                    score = torch.softmax(outputs.logits, dim=1)[0][1].item()  # 获取正类分数
                if score > 0.5:
                    relationships.append({
                        'source': title,
                        'target': title,  # 可选：都用标题作为节点，也可以加段落序号区分
                        'relation': '相关',
                        'score': round(score, 2),
                        'text_pair': (para[:20], other_para[:20])  # 仅供可选可视化用
                    })
    return relationships

# =================== 知识图谱构建 ===================
all_relationships = []
for _, row in tqdm(combined_df.iterrows(), total=len(combined_df), desc="总文档进度"):
    title = row['Title']
    document = row['Document']
    paragraphs = row['Paragraphs']
    if len(paragraphs) < 2:
        continue
    relationships = extract_relationships(paragraphs, title, document)
    all_relationships.extend(relationships)

# =================== 构建 NetworkX 图 ===================
G = nx.Graph()

for rel in all_relationships:
    G.add_node(rel['source'], label=rel['source'])
    G.add_node(rel['target'], label=rel['target'])
    G.add_edge(rel['source'], rel['target'], label=rel['relation'], weight=rel['score'])

# =================== 设置中文字体（解决乱码） ===================
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置为黑体
plt.rcParams['axes.unicode_minus'] = False    # 负号正常显示

# =================== 可视化 ===================
plt.figure(figsize=(12, 12))
pos = nx.spring_layout(G, k=0.5)

nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='skyblue')
nx.draw_networkx_labels(G, pos, font_size=10)
nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7)

# 显示边标签（关系）
edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)

plt.title("知识图谱（中文标题节点 + 段落关系）")
plt.axis('off')
plt.tight_layout()
plt.show()

# =================== 保存为 GML 图文件 ===================
nx.write_gml(G, "knowledge_graph.gml")

```
new
```
import os
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import networkx as nx
import torch
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib

# 设置中文字体（避免节点标签显示空方框）
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
matplotlib.rcParams['axes.unicode_minus'] = False

# 加载预训练模型
model_name = "bert-base-chinese"
model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 读取多个 CSV 文件
directory = 'csv_files'
dataframes = []

for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        filepath = os.path.join(directory, filename)
        try:    
            df = pd.read_csv(filepath, on_bad_lines='skip', encoding='utf-8')
            df.columns = ['Title', 'Content']  # 假设每个 CSV 都是两列：标题、内容
            df['Document'] = filename
            dataframes.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

combined_df = pd.concat(dataframes, ignore_index=True)

# 定义段落分割函数
def split_into_paragraphs(text):
    if isinstance(text, str):
        return [para.strip() for para in text.split('\n') if para.strip()]
    else:
        return []

combined_df['Paragraphs'] = combined_df['Content'].apply(lambda x: split_into_paragraphs(str(x)))

# 使用 BERT 模型提取段落之间的关系
def extract_relationships(paragraphs, title, document):
    relationships = []
    for i, para in enumerate(tqdm(paragraphs, desc=f'处理段落: {title}')):
        for j, other_para in enumerate(paragraphs):
            if i != j:
                inputs = tokenizer(para, other_para, return_tensors="pt", padding=True, truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = model(**inputs)
                score = outputs.logits[0][1].item()
                if score > 0.5:
                    relationships.append({
                        'source': title,
                        'target': title,  # 所有段落都归属这个标题，所以显示同一个标题
                        'relation': '相关段落',
                        'score': score,
                        'document': document
                    })
    return relationships

# 构建知识图谱，只保留标题作为节点
all_relationships = []
node_titles = set()

for _, row in tqdm(combined_df.iterrows(), total=len(combined_df), desc="总进度"):
    title = row['Title']
    document = row['Document']
    paragraphs = row['Paragraphs']
    node_titles.add(title)
    relationships = extract_relationships(paragraphs, title, document)
    all_relationships.extend(relationships)

# 构建 NetworkX 图
G = nx.Graph()

# 添加节点
for title in node_titles:
    G.add_node(title, label=title)

# 添加边（按标题连接）
for rel in all_relationships:
    G.add_edge(rel['source'], rel['target'], relation=rel['relation'], score=rel['score'])

# 输出图信息
print(f"节点数量: {G.number_of_nodes()}")
print(f"边数量: {G.number_of_edges()}")

# 保存图为 GML 文件
nx.write_gml(G, 'knowledge_graph.gml')

# 可视化（仅显示标题作为节点标签）
plt.figure(figsize=(12, 12))
pos = nx.spring_layout(G, k=0.5)
nx.draw(
    G,
    pos,
    with_labels=True,
    labels={node: node for node in G.nodes()},
    node_size=800,
    node_color='lightblue',
    font_size=10,
    font_weight='bold',
    edge_color='gray'
)
plt.title('知识图谱（按标题）')
plt.show()


```
```python
import os
import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple

class KnowledgeGraphBuilder:
    def __init__(self):
        # 初始化NLP模型
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModelForSequenceClassification.from_pretrained("bert-base-uncased")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 初始化知识图谱
        self.graph = nx.Graph()
        self.document_metadata = {}
        self.paragraph_embeddings = {}
        
    def load_csv_files(self, file_paths: List[str]) -> None:
        """加载多个CSV文件"""
        for file_path in file_paths:
            df = pd.read_csv(file_path)
            # 假设CSV有'title'和'content'列
            if 'title' in df.columns and 'content' in df.columns:
                for _, row in df.iterrows():
                    doc_id = row['title']
                    content = row['content']
                    self.document_metadata[doc_id] = {
                        'file_path': file_path,
                        'content': content
                    }
            else:
                print(f"Warning: CSV file {file_path} does not have required columns (title, content)")
    
    def split_into_paragraphs(self, content: str, min_length: int = 50) -> List[str]:
        """将文档内容分割成段落"""
        # 简单的分割方法：按换行符分割
        paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) > min_length]
        return paragraphs
    
    def compute_paragraph_embeddings(self) -> None:
        """计算所有段落的嵌入向量"""
        paragraphs = []
        doc_ids = []
        
        # 收集所有段落
        for doc_id, metadata in self.document_metadata.items():
            content = metadata['content']
            paragraphs_in_doc = self.split_into_paragraphs(content)
            for para in paragraphs_in_doc:
                paragraphs.append(para)
                doc_ids.append(doc_id)
        
        # 计算嵌入
        if paragraphs:
            embeddings = self.embedding_model.encode(paragraphs)
            for i, (para, doc_id) in enumerate(zip(paragraphs, doc_ids)):
                self.paragraph_embeddings[para] = {
                    'embedding': embeddings[i],
                    'doc_id': doc_id
                }
    
    def build_relationships(self, threshold: float = 0.7) -> None:
        """基于嵌入相似度构建段落间关系"""
        paragraphs = list(self.paragraph_embeddings.keys())
        embeddings = [self.paragraph_embeddings[para]['embedding'] for para in paragraphs]
        
        # 计算相似度矩阵
        similarity_matrix = cosine_similarity(embeddings)
        
        # 添加边到图谱
        for i in range(len(paragraphs)):
            para1 = paragraphs[i]
            self.graph.add_node(para1, 
                               type='paragraph',
                               doc_id=self.paragraph_embeddings[para1]['doc_id'])
            
            for j in range(i+1, len(paragraphs)):
                para2 = paragraphs[j]
                similarity = similarity_matrix[i][j]
                
                if similarity > threshold:
                    # 添加边，权重为相似度分数
                    self.graph.add_edge(para1, para2, weight=similarity)
                    
                    # 如果是同一文档的不同段落，可以添加特定关系
                    if self.paragraph_embeddings[para1]['doc_id'] == self.paragraph_embeddings[para2]['doc_id']:
                        self.graph.add_edge(para1, para2, weight=similarity, relation='same_document')
    
    def add_document_nodes(self) -> None:
        """添加文档节点到图谱"""
        for doc_id in self.document_metadata.keys():
            self.graph.add_node(doc_id, type='document')
            
            # 连接文档和其包含的段落
            for para in self.paragraph_embeddings:
                if self.paragraph_embeddings[para]['doc_id'] == doc_id:
                    self.graph.add_edge(doc_id, para, relation='contains')
    
    def visualize_graph(self, max_nodes: int = 50) -> None:
        """可视化知识图谱"""
        if len(self.graph.nodes) == 0:
            print("Graph is empty, nothing to visualize")
            return
            
        # 限制节点数量以便可视化
        subgraph = self.graph.copy()
        if len(subgraph.nodes) > max_nodes:
            # 随机采样子图
            nodes = list(subgraph.nodes())
            np.random.seed(42)
            selected_nodes = np.random.choice(nodes, size=max_nodes, replace=False)
            subgraph = subgraph.subgraph(selected_nodes).copy()
            
        pos = nx.spring_layout(subgraph, k=0.5)
        node_colors = []
        
        # 根据节点类型设置颜色
        for node in subgraph.nodes():
            node_type = subgraph.nodes[node].get('type', 'unknown')
            if node_type == 'document':
                node_colors.append('lightblue')
            elif node_type == 'paragraph':
                node_colors.append('lightgreen')
            else:
                node_colors.append('pink')
                
        plt.figure(figsize=(12, 12))
        nx.draw(subgraph, pos, with_labels=True, node_color=node_colors, 
                font_size=8, node_size=500, edge_color='gray', width=0.5)
        plt.title("Knowledge Graph Visualization")
        plt.show()
    
    def export_to_csv(self, output_path: str) -> None:
        """将知识图谱导出为CSV文件"""
        # 节点信息
        nodes_data = []
        for node in self.graph.nodes(data=True):
            nodes_data.append({
                'node_id': node[0],
                'type': node[1].get('type', 'unknown'),
                'doc_id': node[1].get('doc_id', '')
            })
        
        # 边信息
        edges_data = []
        for edge in self.graph.edges(data=True):
            edges_data.append({
                'source': edge[0],
                'target': edge[1],
                'relation': edge[2].get('relation', 'similarity'),
                'weight': edge[2].get('weight', 0.0)
            })
        
        # 保存到CSV
        pd.DataFrame(nodes_data).to_csv(os.path.join(output_path, 'nodes.csv'), index=False)
        pd.DataFrame(edges_data).to_csv(os.path.join(output_path, 'edges.csv'), index=False)
        
        print(f"Knowledge graph exported to {output_path}")
    
    def build_graph(self, csv_paths: List[str], threshold: float = 0.7) -> None:
        """构建知识图谱的主流程"""
        # 1. 加载CSV文件
        self.load_csv_files(csv_paths)
        
        # 2. 计算段落嵌入
        self.compute_paragraph_embeddings()
        
        # 3. 构建段落间关系
        self.build_relationships(threshold)
        
        # 4. 添加文档节点
        self.add_document_nodes()
        
        print(f"Knowledge graph built with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")

# 使用示例
if __name__ == "__main__":
    # 初始化构建器
    kg_builder = KnowledgeGraphBuilder()
    
    # 假设CSV文件在当前目录的data文件夹中
    csv_files = [
        "data/document1.csv",
        "data/document2.csv",
        # 添加更多CSV文件路径...
    ]
    
    # 构建知识图谱
    kg_builder.build_graph(csv_files, threshold=0.6)
    
    # 可视化图谱
    kg_builder.visualize_graph(max_nodes=30)
    
    # 导出到CSV
    kg_builder.export_to_csv("output/knowledge_graph")

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
