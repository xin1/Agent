
# 📚 GraphMind 1.2-网页显示
> 中文知识图谱自动生成工具（基于标题层级）

## 🎯 项目目标

旨在从多个带有层级标题结构的中文 CSV 文档中提取段落标题，并根据其层级结构（如 1、1.1、1.1.1）构建可交互式的知识图谱，用以展示文档结构、段落隶属关系和语义组织。

通过交互式图谱（基于 PyVis 实现），用户可以：

- 直观浏览文档结构
- 展开或折叠任意层级
- 查看每个段落的内容（鼠标悬停）
- 支持多文件批量处理
- 控制显示的最大层级深度（如仅显示到 1.1）

---

## 🧠 功能概览

- ✅ 支持批量读取 `csv_files/` 文件夹内的多个 `.csv` 文档
- ✅ 自动提取标题的层级编号，如 `1`, `1.1`, `1.1.1` 等
- ✅ 构建段落之间的“包含”层级关系，并关联源文档
- ✅ 生成带标题、内容说明的交互式知识图谱（HTML）
- ✅ 支持用户自定义最大显示层级
- ✅ 完整中文支持，不乱码不报错

---

## 📁 输入格式说明

输入文件夹：`csv_files/`

每个 CSV 文件需包含以下格式（**不需要标题行**）：

| 标题              | 内容                      |
|-------------------|---------------------------|
| 1 项目介绍        | 本文档主要介绍……         |
| 1.1 系统目标      | 系统目标包括……           |
| 1.1.1 用户需求分析 | 包括用户权限、角色等内容 |
| 2 技术方案        | 采用BERT嵌入、深度学习等  |

> 注意：第一列必须是带有类似“1”、“1.1”、“1.1.1”结构的标题，第二列为该段正文内容。

---

## 📄 输出结果

生成一个交互式 HTML 网页图谱文件：

- 文件名：`knowledge_graph.html`
- 点击可缩放、拖动图谱
- 鼠标悬停可查看段落内容
- 节点包括文档名、标题、子标题等
- 支持自动打开浏览器预览（可选）

---

## ⚙️ 自定义参数

你可以修改脚本中这行来限制显示的最大层级（如只显示 `1.1`）：

```python
max_level = 2  # 设置为1只显示一级标题，设置为2则显示到1.1，设置为3显示到1.1.1
````

---

## 🔧 依赖安装

```bash
pip install pandas pyvis
```

---

## 📌 使用方法

```bash
python Graph_Mind_view.py
```

运行后将生成 `knowledge_graph.html`，用浏览器打开即可查看。

---

## Graph_Mind_view.py代码
```python
import os
import pandas as pd
import re
from pyvis.network import Network

# 设置 CSV 文件夹路径
folder = 'csv_files'
dfs = []

# 遍历文件夹读取所有 CSV 文件
for filename in os.listdir(folder):
    if filename.endswith('.csv'):
        try:
            file_path = os.path.join(folder, filename)
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
            df.columns = ['Title', 'Content']  # 确保列一致
            df['Document'] = os.path.splitext(filename)[0]
            dfs.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

# 合并所有数据
if not dfs:
    raise ValueError("未找到任何有效的 CSV 文件。请检查文件夹路径和内容。")

df_all = pd.concat(dfs, ignore_index=True)

# 提取标题编号（如 1、1.1、1.1.1）
def extract_level(title):
    if isinstance(title, str):
        match = re.match(r'^(\d+(\.\d+)*)', title.strip())
        return match.group(1) if match else None
    return None

df_all['Level'] = df_all['Title'].apply(extract_level)
df_all = df_all.dropna(subset=['Level'])

# 避免 float 类型 content 导致报错
df_all['Content'] = df_all['Content'].astype(str).fillna("")

# 设置最大层级（如 2 表示只显示到 1.1）
max_level = 2

# 创建 pyvis 图
net = Network(height='750px', width='100%', directed=True, font_color='black', notebook=False)
net.force_atlas_2based()

# 添加节点和边
for _, row in df_all.iterrows():
    doc = str(row['Document'])
    title = str(row['Title'])
    content = str(row['Content']) if pd.notna(row['Content']) else ""
    level_code = str(row['Level'])

    # 层级控制
    level_parts = level_code.split('.')
    if len(level_parts) > max_level:
        continue

    # 当前节点
    current_node = f"{level_code} {title}"
    net.add_node(current_node, label=title, title=content)

    # 父节点
    if len(level_parts) == 1:
        parent_node = doc
        net.add_node(parent_node, label=doc, title=f"文档：{doc}")
    else:
        parent_code = '.'.join(level_parts[:-1])
        parent_row = df_all[df_all['Level'] == parent_code]
        parent_title = parent_row['Title'].values[0] if not parent_row.empty else parent_code
        parent_node = f"{parent_code} {parent_title}"

    net.add_edge(parent_node, current_node)

# 生成交互式 HTML 文件
output_path = 'knowledge_graph.html'
net.write_html(output_path)
print(f"✅ 交互式知识图谱已成功生成：{output_path}，请用浏览器打开查看。")

```
