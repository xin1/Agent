可以处理多个 CSV 文件，具有不同的文件名和结构，并通过内容识别段落之间的关系，构建跨文档的知识图谱。

---

## 🧭 项目概览

1. **读取多个 CSV 文件**：加载所有 CSV 文件，并统一列名。
2. **段落分割**：将内容字段分割为多个段落。
3. **关系提取**：使用 GPT-3.5 模型提取段落之间的关系。
4. **构建知识图谱**：基于提取的关系构建图谱数据结构。
5. **可视化展示**：使用 D3.js 等工具可视化知识图谱。

---

## 📂 第一步：读取多个 CSV 文件

假设您的 CSV 文件位于同一目录下，且每个文件包含两列：标题和内容。

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

## ✂️ 第二步：段落分割

将每个文档的内容字段按段落进行分割。

```python
# 定义段落分割函数
def split_into_paragraphs(text):
    return [para.strip() for para in text.split('\n') if para.strip()]

# 应用段落分割
combined_df['Paragraphs'] = combined_df['Content'].apply(split_into_paragraphs)
```

---

## 🤖 第三步：关系提取

使用 OpenAI 的 GPT-3.5 模型提取段落之间的关系。

```python
import openai
import time

# 设置 OpenAI API 密钥
openai.api_key = 'your-openai-api-key'

# 定义关系提取函数
def extract_relationships(paragraphs, title, document):
    relationships = []
    for i, para in enumerate(paragraphs):
        prompt = f"""
文档标题：{title}
文档名称：{document}
段落内容：{para}

请识别该段落与其他段落之间的关系，并以 JSON 格式返回，格式如下：
[
  {{
    "source": "当前段落内容",
    "target": "相关段落内容",
    "relation": "关系描述"
  }},
  ...
]
如果没有相关关系，请返回空列表。
"""
        try:
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            result = response['choices'][0]['message']['content']
            relationships.extend(eval(result))  # 注意：使用 eval 需确保返回内容的安全性
            time.sleep(1)  # 避免触发速率限制
        except Exception as e:
            print(f"Error processing paragraph {i} in document '{document}': {e}")
    return relationships

# 提取所有文档的关系
all_relationships = []
for index, row in combined_df.iterrows():
    title = row['Title']
    document = row['Document']
    paragraphs = row['Paragraphs']
    relationships = extract_relationships(paragraphs, title, document)
    all_relationships.extend(relationships)
```

---

## 🧠 第四步：构建知识图谱

根据提取的关系构建知识图谱的数据结构。

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

## 📊 第五步：可视化展示

使用 D3.js 等前端工具可视化知识图谱。以下是一个简单的 HTML 示例：

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

请将上述脚本中的 `nodes` 和 `edges` 数据替换为您从 Python 脚本中生成的实际数据。

---

## 🔗 参考资源

* **OpenAI API 文档**：[https://platform.openai.com/docs](https://platform.openai.com/docs)
* **D3.js 官方文档**：[https://d3js.org/](https://d3js.org/)

---

如果您需要进一步的帮助，例如如何部署此应用或处理更复杂的文档结构，请随时提问！
