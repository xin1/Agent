错误
```
TypeError: draw_networkx_labels() got an unexpected keyword argument 'font_properties'
```
思路总结（支持中文标题、结构识别、知识图谱构建和可视化）

---

### ✅ 一、当前的结构化思路分析：

| 第一列标题      | 第二列内容（可选） |
| ---------- | --------- |
| 1 一级标题     | ...       |
| 1.1 二级标题   | ...       |
| 1.1.1 三级标题 | ...       |
| ...        | ...       |

希望构建的关系是：

```
1.1.1 → 1.1 → 1 → 文档名（根节点）
```

---

### ✅ 二、改进建议与说明：

1. **编号结构本身即为层级依据**（如 1.1.1 属于 1.1）。
2. **你可以将文档名作为根节点 `root`，编号为其子节点**。
3. **节点只显示标题，不显示内容**，内容可以保留在图中属性中，便于后期使用。
4. **图结构支持导出 GML 可用于 Gephi 等图形工具进一步分析**。

---

### ✅ 三、完整代码（请放在有你CSV文件的同级目录下）

需要把你的CSV文件命名为例如：`my_doc.csv`（第一列为标题，第二列为内容），并运行下面的代码：

```python
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
import os

# 设置全局中文字体（推荐：simhei、msyh、SimSun）
matplotlib.rcParams['font.family'] = 'SimHei'  # 黑体。你可以替换为系统中的其他中文字体

# 读取 CSV 文件（第一列是标题，第二列是内容）
csv_path = 'your_file.csv'  # 修改为你的CSV文件路径
df = pd.read_csv(csv_path, encoding='utf-8')
df.columns = ['Title', 'Content']

# 获取标题层级（1、1.1、1.2.3等）
def get_title_level(title):
    return len(str(title).split('.'))

# 构建层级关系
def build_hierarchy(df):
    df['Level'] = df['Title'].apply(get_title_level)
    df['Node'] = df['Title'] + ' ' + df['Content'].str.slice(0, 15)  # 每个节点显示前15个字符内容
    edges = []
    stack = []

    for _, row in df.iterrows():
        current_level = row['Level']
        while stack and stack[-1]['Level'] >= current_level:
            stack.pop()
        if stack:
            parent = stack[-1]
            edges.append((parent['Node'], row['Node']))
        stack.append(row)
    return df, edges

# 构建图
df, edges = build_hierarchy(df)
G = nx.DiGraph()
for _, row in df.iterrows():
    G.add_node(row['Node'])

for src, dst in edges:
    G.add_edge(src, dst, relation='包含')

# 可视化
plt.figure(figsize=(14, 12))
pos = nx.spring_layout(G, k=0.5)
nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1000)
nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15)
nx.draw_networkx_labels(G, pos, font_size=10)  # 中文显示依赖于全局 font.family 设置

plt.title("中文知识图谱：标题层级包含关系", fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.savefig("knowledge_graph_cn_fixed.png", dpi=300)
plt.show()

# 可选：保存为 GML 图
nx.write_gml(G, "knowledge_graph_cn.gml")

```

---

### ✅ 四、你可以做的扩展：

* 用颜色区分层级。
* 导出 JSON/Neo4j 格式。
* 加入内容摘要或关键词。

---
