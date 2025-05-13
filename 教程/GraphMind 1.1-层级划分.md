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
import os
from matplotlib.font_manager import FontProperties

# 设置中文字体（根据系统路径自行修改）
# Windows系统中文字体路径举例（仿宋、微软雅黑等）
font_path = "C:/Windows/Fonts/simhei.ttf"  # 你可以改成你系统有的字体路径
font_prop = FontProperties(fname=font_path)

# 读取 CSV 文件
csv_path = 'your_file.csv'  # 修改为你的文件路径
df = pd.read_csv(csv_path, encoding='utf-8')

# 标准化列名
df.columns = ['Title', 'Content']

# 提取标题层级
def get_title_level(title):
    parts = str(title).split('.')
    return len(parts)

# 建立包含层级映射关系
def build_hierarchy(df):
    df['Level'] = df['Title'].apply(get_title_level)
    df['Node'] = df['Title'] + ' ' + df['Content'].str.slice(0, 15)  # 节点显示前15字
    edges = []

    stack = []  # 存储当前各级别的上一个标题
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
    G.add_node(row['Node'], label=row['Title'])

for src, dst in edges:
    G.add_edge(src, dst, relation='包含')

# 可视化图
plt.figure(figsize=(14, 12))
pos = nx.spring_layout(G, k=0.5, iterations=50)
nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='lightblue')
nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15)
nx.draw_networkx_labels(G, pos, font_size=10, font_properties=font_prop)

plt.title("知识图谱：层级包含关系", fontproperties=font_prop, fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.savefig("knowledge_graph_cn.png", dpi=300)
plt.show()

# 可选：保存为 GML 图文件
nx.write_gml(G, "knowledge_graph_cn.gml")

```

---

### ✅ 四、你可以做的扩展：

* 用颜色区分层级。
* 导出 JSON/Neo4j 格式。
* 加入内容摘要或关键词。

---
