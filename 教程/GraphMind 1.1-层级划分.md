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
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# 修改为你的CSV文件名
csv_path = "my_doc.csv"

# 读取 CSV（假设第一列是标题，第二列是内容）
df = pd.read_csv(csv_path, encoding='utf-8', header=None)
df.columns = ['Title', 'Content']

# 自动识别编号、标题名、层级和父节点
def parse_title(title):
    title = str(title).strip()
    if ' ' in title:
        number, name = title.split(' ', 1)
    elif '　' in title:
        number, name = title.split('　', 1)
    else:
        number, name = title, ''
    level = number.count('.') + 1 if number != 'root' else 0
    parent = '.'.join(number.split('.')[:-1]) if level > 1 else 'root'
    return pd.Series([number, name, level, parent])

df[['Number', 'Name', 'Level', 'Parent']] = df['Title'].apply(parse_title)

# 初始化图
G = nx.DiGraph()

# 添加根节点（文档名）
doc_name = os.path.splitext(os.path.basename(csv_path))[0]
G.add_node('root', label=doc_name, content='文档根')

# 添加每个段落为节点并连接关系
for _, row in df.iterrows():
    node_id = row['Number']
    label = row['Name']
    content = row['Content']
    G.add_node(node_id, label=label, content=content)
    G.add_edge(row['Parent'], node_id)

# 输出图信息
print(f"节点数: {G.number_of_nodes()}")
print(f"边数: {G.number_of_edges()}")

# 可视化
plt.figure(figsize=(14, 10))
pos = nx.spring_layout(G, k=0.7, seed=42)
labels = nx.get_node_attributes(G, 'label')
nx.draw(G, pos, labels=labels, with_labels=True, node_size=1000,
        node_color='lightblue', font_size=9, arrows=True, edge_color='gray')
plt.title("中文结构知识图谱（层级关系）", fontsize=14)
plt.tight_layout()
plt.show()

# 可导出为 .gml 用 Gephi 打开
nx.write_gml(G, f"{doc_name}_knowledge_graph.gml")
```

---

### ✅ 四、你可以做的扩展：

* 用颜色区分层级。
* 导出 JSON/Neo4j 格式。
* 加入内容摘要或关键词。

---
