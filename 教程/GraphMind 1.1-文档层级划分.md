# GraphMind 1.1-文档层级划分
> 中文文档标题层级知识图谱生成思路总结
> 支持中文标题、结构识别、知识图谱构建和可视化

---
## 一、往期回顾
### ✅ 结构化思路分析：
之前的结构化文件

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
### ✅ 目标：

1. **编号结构本身即为层级依据**（如 1.1.1 属于 1.1）。
2. **你可以将文档名作为根节点 `root`，编号为其子节点**。
3. **节点只显示标题，不显示内容**，内容可以保留在图中属性中，便于后期使用。
4. **图结构支持导出 GML 可用于 Gephi 等图形工具进一步分析**。

---
## 二、准备工作

### 环境要求
- Python 3.x
- 安装必要的Python库：
  ```
  pip install pandas networkx matplotlib
  ```

### 输入文件格式
- 将所有CSV文件放在名为`csv_files`的文件夹中
- 每个CSV文件应包含至少两列：标题(Title)和内容(Content)
- 标题应包含层级编号（如"1 概述"、"1.1 背景"、"1.1.1 历史"等）

## 使用方法

1. **准备CSV文件**：
   - 创建`csv_files`文件夹
   - 将所有要处理的CSV文件放入该文件夹
   - 确保每个CSV文件有'Title'和'Content'列（或代码会自动重命名）

2. **运行代码**：
   - 将代码保存为.py文件（如`knowledge_graph.py`）
   - 在命令行运行：`python knowledge_graph.py`

3. **调整参数**：
   - 修改`max_level`变量可以控制显示的层级深度
   - 调整图形大小(figsize)可以改变输出图像的尺寸
   - 修改节点大小(node_size)和字体大小(font_size)可以改善可视化效果

### ✅ 三、完整代码（请放在有你CSV文件的同级目录下）

```python
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib

# 强制设置 matplotlib 使用中文字体，避免乱码
matplotlib.rcParams['font.sans-serif'] = ['SimHei']     # 设置中文字体
matplotlib.rcParams['axes.unicode_minus'] = False       # 解决负号乱码

import re

# 读取 CSV 文件夹
folder = 'csv_files'
dfs = []

for filename in os.listdir(folder):
    if filename.endswith('.csv'):
        try:
            df = pd.read_csv(os.path.join(folder, filename), encoding='utf-8', on_bad_lines='skip')
            df.columns = ['Title', 'Content']  # 保证标题和内容列统一
            df['Document'] = os.path.splitext(filename)[0]
            dfs.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

# 合并所有文件
df_all = pd.concat(dfs, ignore_index=True)

# 提取层级编号
def extract_level(title):
    match = re.match(r'^(\d+(\.\d+)*)', str(title).strip())
    return match.group(1) if match else None

df_all['Level'] = df_all['Title'].apply(extract_level)
df_all = df_all.dropna(subset=['Level'])

# 构建图谱
G = nx.DiGraph()
max_level = 2  # 设置只显示到几级标题，例如 1.1 是两级

for _, row in df_all.iterrows():
    doc = row['Document']
    full_title = row['Title']
    level_code = row['Level']
    level_parts = level_code.split('.')

    # 控制图谱最大显示层级
    if len(level_parts) > max_level:
        continue

    current_node = f"{level_code} {full_title}"
    G.add_node(current_node, label=full_title)

    if len(level_parts) == 1:
        parent_node = doc
    else:
        parent_code = '.'.join(level_parts[:-1])
        parent_row = df_all[df_all['Level'] == parent_code]
        parent_title = parent_row['Title'].values[0] if not parent_row.empty else parent_code
        parent_node = f"{parent_code} {parent_title}"

    G.add_edge(parent_node, current_node)

# 添加文档名为根节点
for doc in df_all['Document'].unique():
    G.add_node(doc, label=doc)

# 可视化
plt.figure(figsize=(14, 10))
pos = nx.spring_layout(G, k=0.6, seed=42)

nx.draw_networkx_nodes(G, pos, node_size=800, node_color='lightblue')
nx.draw_networkx_edges(G, pos, arrows=True)

# 使用 label 参数绘制中文标签，避免 font_properties 报错
labels = {n: d['label'] for n, d in G.nodes(data=True) if 'label' in d}
nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_family='SimHei')

plt.title("中文文档标题层级知识图谱", fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.show()

```

---

## 四、代码使用说明

### 1. 代码结构

```python
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
import re
```

导入必要的库，包括文件操作、数据处理、图网络构建和可视化工具。

### 2. 中文显示配置

```python
# 强制设置 matplotlib 使用中文字体，避免乱码
matplotlib.rcParams['font.sans-serif'] = ['SimHei']     # 设置中文字体
matplotlib.rcParams['axes.unicode_minus'] = False       # 解决负号乱码
```

配置matplotlib以正确显示中文字符和负号。

### 3. 读取CSV文件

```python
folder = 'csv_files'
dfs = []

for filename in os.listdir(folder):
    if filename.endswith('.csv'):
        try:
            df = pd.read_csv(os.path.join(folder, filename), encoding='utf-8', on_bad_lines='skip')
            df.columns = ['Title', 'Content']  # 保证标题和内容列统一
            df['Document'] = os.path.splitext(filename)[0]
            dfs.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

# 合并所有文件
df_all = pd.concat(dfs, ignore_index=True)
```

- 遍历`csv_files`文件夹中的所有CSV文件
- 读取每个文件并统一列名为'Title'和'Content'
- 添加'Document'列记录文件来源
- 合并所有数据到一个DataFrame中

### 4. 提取层级编号

```python
def extract_level(title):
    match = re.match(r'^(\d+(\.\d+)*)', str(title).strip())
    return match.group(1) if match else None

df_all['Level'] = df_all['Title'].apply(extract_level)
df_all = df_all.dropna(subset=['Level'])
```

- 使用正则表达式从标题中提取层级编号（如"1.1.2"）
- 过滤掉没有层级编号的标题

### 5. 构建图谱

```python
G = nx.DiGraph()
max_level = 2  # 设置只显示到几级标题，例如 1.1 是两级

for _, row in df_all.iterrows():
    doc = row['Document']
    full_title = row['Title']
    level_code = row['Level']
    level_parts = level_code.split('.')

    # 控制图谱最大显示层级
    if len(level_parts) > max_level:
        continue

    current_node = f"{level_code} {full_title}"
    G.add_node(current_node, label=full_title)

    if len(level_parts) == 1:
        parent_node = doc
    else:
        parent_code = '.'.join(level_parts[:-1])
        parent_row = df_all[df_all['Level'] == parent_code]
        parent_title = parent_row['Title'].values[0] if not parent_row.empty else parent_code
        parent_node = f"{parent_code} {parent_title}"

    G.add_edge(parent_node, current_node)

# 添加文档名为根节点
for doc in df_all['Document'].unique():
    G.add_node(doc, label=doc)
```

- 创建一个有向图(DiGraph)
- 设置最大显示层级(max_level)，例如2表示只显示到1.1这样的层级
- 遍历所有标题，为每个标题创建节点
- 根据层级编号确定父节点，并添加边
- 将每个文档名也添加为根节点

### 6. 可视化

```python
plt.figure(figsize=(14, 10))
pos = nx.spring_layout(G, k=0.6, seed=42)

nx.draw_networkx_nodes(G, pos, node_size=800, node_color='lightblue')
nx.draw_networkx_edges(G, pos, arrows=True)

# 使用 label 参数绘制中文标签，避免 font_properties 报错
labels = {n: d['label'] for n, d in G.nodes(data=True) if 'label' in d}
nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_family='SimHei')

plt.title("中文文档标题层级知识图谱", fontsize=16)
plt.axis('off')
plt.tight_layout()
plt.show()
```

- 设置图形大小
- 使用spring布局算法计算节点位置
- 绘制节点和边
- 使用节点数据中的'label'字段显示中文标题
- 添加标题并关闭坐标轴
- 显示图形
## 五、示例输出

生成的图形将显示：
- 每个文档名作为根节点
- 文档内的标题按照层级关系连接
- 箭头表示父子关系（从父节点指向子节点）
- 中文标题正确显示

## 六、注意事项

1. 标题中的层级编号必须使用点号分隔（如1.1.1），不能使用其他分隔符
2. 如果标题没有层级编号，将被过滤掉
3. 对于大型文档集，可能需要调整spring布局的k参数以获得更好的布局效果
4. 如果遇到中文显示问题，确保系统已安装"SimHei"字体或修改为其他中文字体

## 七、扩展建议

1. 可以将生成的图形保存为图片文件：
   ```python
   plt.savefig('knowledge_graph.png', dpi=300, bbox_inches='tight')
   ```

2. 可以添加交互功能，如点击节点展开/折叠子节点

3. 可以添加节点颜色编码，根据文档来源或标题类型着色

