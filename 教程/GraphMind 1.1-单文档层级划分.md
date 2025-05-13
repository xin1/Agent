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
from matplotlib import font_manager as fm
import os

# 中文字体路径（换成你系统中的路径）
font_path = "C:/Windows/Fonts/msyh.ttc"  # Windows 下的微软雅黑路径
my_font = fm.FontProperties(fname=font_path)

# 加载 CSV 数据
df = pd.read_csv("your_file.csv", encoding='utf-8')
df.columns = ['Title', 'Content']

# 提取标题层级
def get_title_level(title):
    return len(str(title).split('.'))

def build_hierarchy(df):
    df['Level'] = df['Title'].apply(get_title_level)
    df['Node'] = df['Title'] + ' ' + df['Content'].str.slice(0, 10)
    edges = []
    stack = []
    for _, row in df.iterrows():
        level = row['Level']
        while stack and stack[-1]['Level'] >= level:
            stack.pop()
        if stack:
            parent = stack[-1]
            edges.append((parent['Node'], row['Node']))
        stack.append(row)
    return df, edges

df, edges = build_hierarchy(df)

# 构建图
G = nx.DiGraph()
for _, row in df.iterrows():
    G.add_node(row['Node'])

for src, dst in edges:
    G.add_edge(src, dst, relation='包含')

# 可视化
plt.figure(figsize=(14, 12))
pos = nx.spring_layout(G, k=0.8)
nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1000)
nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15)
nx.draw_networkx_labels(G, pos, font_properties=my_font, font_size=10)

plt.title("中文知识图谱：标题层级结构", fontproperties=my_font, fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.savefig("knowledge_graph_fixed_cn.png", dpi=300)
plt.show()

```

---

### ✅ 四、你可以做的扩展：

* 用颜色区分层级。
* 导出 JSON/Neo4j 格式。
* 加入内容摘要或关键词。

---
