错误
```
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from tqdm import tqdm
from matplotlib.font_manager import FontProperties

# 设置中文字体
font_path = "C:/Windows/Fonts/simhei.ttf"  # SimHei 中文字体路径（Windows）
font_prop = FontProperties(fname=font_path)

# 设置目录
directory = 'csv_files/my_doc'

# 合并多个 CSV 文件
all_nodes = []
all_edges = []

for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        filepath = os.path.join(directory, filename)
        try:
            df = pd.read_csv(filepath, encoding='utf-8', on_bad_lines='skip')
            df.columns = ['Title', 'Content']  # 确保列名一致
            df['Document'] = filename[:-4]  # 移除 .csv
            all_nodes.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

# 合并所有数据
combined_df = pd.concat(all_nodes, ignore_index=True)

# 提取层级函数
def get_level(title):
    try:
        parts = title.split()[0].split('.')  # 例如 '1.2.3 xxx'
        return len(parts)
    except:
        return 0

# 创建图
G = nx.DiGraph()

# 构建图谱
for _, row in tqdm(combined_df.iterrows(), total=len(combined_df), desc="构建图谱"):
    title = str(row['Title']).strip()
    content = str(row['Content']).strip()
    document = row['Document']
    
    if not title or '.' not in title:
        continue
    
    # 提取编号和标题
    number = title.split()[0]
    label = title
    level = get_level(title)
    
    # 根节点（文档名）为0级
    if level == 1:
        parent = document
    else:
        parent = '.'.join(number.split('.')[:-1])
    
    # 添加节点和边（限制显示到1.1层）
    G.add_node(number, label=label, content=content, level=level)
    if level <= 2:
        G.add_edge(parent, number)

# 删除不在可视层级范围内的节点
max_level_to_show = 2
nodes_to_remove = [n for n, d in G.nodes(data=True) if d.get('level', 0) > max_level_to_show]
G.remove_nodes_from(nodes_to_remove)

# 可视化图谱
pos = nx.spring_layout(G, k=1.5)
plt.figure(figsize=(14, 12))

nx.draw(G, pos, with_labels=False, node_size=1500, node_color='lightblue', edge_color='gray')

# 中文标签绘制
labels = {node: G.nodes[node]['label'] for node in G.nodes()}
for node, (x, y) in pos.items():
    plt.text(x, y, labels[node], fontsize=10, fontproperties=font_prop, ha='center', va='center')

plt.title("知识图谱（仅展示到1.1层级）", fontproperties=font_prop, fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.savefig("knowledge_graph_limited.png", dpi=300)
plt.show()


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
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
from tqdm import tqdm

# 设置中文字体（Windows 推荐使用 SimHei 或 Microsoft YaHei）
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 中文显示
matplotlib.rcParams['axes.unicode_minus'] = False     # 负号不乱码

# 路径设置
folder = 'csv_files/my_doc'
dataframes = []

# 读取 CSV 文件
for filename in os.listdir(folder):
    if filename.endswith('.csv'):
        filepath = os.path.join(folder, filename)
        try:
            df = pd.read_csv(filepath, on_bad_lines='skip', encoding='utf-8')
            df.columns = ['Title', 'Content']  # 假设标题列在前
            df['Document'] = filename.replace('.csv', '')
            dataframes.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

combined_df = pd.concat(dataframes, ignore_index=True)

# 提取层级关系
def get_parent_title(title):
    parts = title.split('.')
    if len(parts) == 1:
        return None
    return '.'.join(parts[:-1])

# 构建图谱
G = nx.DiGraph()

for _, row in tqdm(combined_df.iterrows(), total=len(combined_df), desc="构建知识图谱"):
    raw_title = str(row['Title']).strip()
    content = str(row['Content']).strip()
    doc = row['Document']

    # 节点名称可为“标题名 + 内容摘要”，也可只用标题名
    full_title = f"{raw_title}"  # 只显示编号 + 标题，不展示正文内容
    parent = get_parent_title(raw_title)

    # 添加节点
    G.add_node(full_title, label=full_title, content=content)

    # 添加文档顶层链接
    if parent:
        G.add_edge(parent, full_title)
    else:
        G.add_edge(doc, full_title)
        G.add_node(doc)  # 文档名作为最上层节点

# 图谱信息
print(f"共 {G.number_of_nodes()} 个节点，{G.number_of_edges()} 条边")

# 可视化
plt.figure(figsize=(15, 10))
pos = nx.spring_layout(G, k=0.5)
nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightblue')
nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15)
nx.draw_networkx_labels(G, pos, labels={n: n for n in G.nodes()}, font_size=10)

plt.title("中文知识图谱：标题层级结构", fontsize=14)
plt.axis('off')
plt.tight_layout()
plt.show()

# 可选：保存图数据
nx.write_gml(G, 'title_knowledge_graph.gml')

```

---

### ✅ 四、你可以做的扩展：

* 用颜色区分层级。
* 导出 JSON/Neo4j 格式。
* 加入内容摘要或关键词。

---
