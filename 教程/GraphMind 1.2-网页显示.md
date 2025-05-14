```python
import os
import pandas as pd
import re
from pyvis.network import Network

# 设置 CSV 文件夹路径
folder = 'csv_files/my_doc'
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
net.show(output_path)
print(f"✅ 交互式知识图谱已生成：{output_path}")

```
