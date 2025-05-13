错误
```
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import re

# 设置中文字体，防止乱码
font_path = 'C:/Windows/Fonts/simhei.ttf'  # 你可以改成你系统中其他中文字体路径
my_font = fm.FontProperties(fname=font_path)

# 读取所有CSV文件
folder = 'csv_files/my_doc'
dfs = []

for filename in os.listdir(folder):
    if filename.endswith('.csv'):
        path = os.path.join(folder, filename)
        try:
            df = pd.read_csv(path, encoding='utf-8', on_bad_lines='skip')
            df.columns = ['Title', 'Content']  # 保证统一列名
            df['Document'] = os.path.splitext(filename)[0]  # 加上所属文件名
            dfs.append(df)
        except Exception as e:
            print(f"读取失败 {filename}：{e}")

all_df = pd.concat(dfs, ignore_index=True)

# 提取标题层级
def extract_level(title):
    match = re.match(r'^(\d+(\.\d+)*)', str(title).strip())
    return match.group(1) if match else None

all_df['Level'] = all_df['Title'].apply(extract_level)
all_df = all_df.dropna(subset=['Level'])  # 只保留有层级结构的标题

# 构建知识图谱图结构
G = nx.DiGraph()
max_display_level = 2  # 只显示到第2级：例如“1.1”

for _, row in all_df.iterrows():
    doc = row['Document']
    full_title = row['Title']
    level_code = row['Level']
    level_parts = level_code.split('.')
    display = len(level_parts) <= max_display_level

    current_node = f"{level_code} {full_title}"
    if display:
        G.add_node(current_node, label=full_title)

    if len(level_parts) == 1:
        parent_node = doc  # 最顶层属于文档
    else:
        parent_code = '.'.join(level_parts[:-1])
        parent_title = all_df[all_df['Level'] == parent_code]['Title']
        parent_title = parent_title.values[0] if not parent_title.empty else parent_code
        parent_node = f"{parent_code} {parent_title}"

    if display and len(level_parts) <= max_display_level:
        G.add_edge(parent_node, current_node)

# 添加文档名为根节点
for doc in all_df['Document'].unique():
    G.add_node(doc, label=doc)

# 可视化图谱
plt.figure(figsize=(14, 10))
pos = nx.spring_layout(G, k=0.6, seed=42)

# 只绘制包含的子图
nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue')
nx.draw_networkx_edges(G, pos, arrows=True)
nx.draw_networkx_labels(G, pos,
                        labels={n: d['label'] for n, d in G.nodes(data=True) if 'label' in d},
                        font_properties=my_font,
                        font_size=10)

plt.title("中文标题层级知识图谱", fontproperties=my_font, fontsize=16)
plt.axis('off')
plt.tight_layout()
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
