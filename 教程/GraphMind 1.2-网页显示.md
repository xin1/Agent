```python
import os
import pandas as pd
import re
from pyvis.network import Network

folder = 'csv_files/my_doc'
dfs = []

# 读取所有 CSV 文件
for filename in os.listdir(folder):
    if filename.endswith('.csv'):
        try:
            df = pd.read_csv(os.path.join(folder, filename), encoding='utf-8', on_bad_lines='skip')
            df.columns = ['Title', 'Content']  # 确保列命名一致
            df['Document'] = os.path.splitext(filename)[0]
            dfs.append(df)
        except Exception as e:
            print(f"读取失败: {filename}, 错误: {e}")

# 合并所有文件
df_all = pd.concat(dfs, ignore_index=True)

# 提取标题层级编号
def extract_level(title):
    match = re.match(r'^(\d+(\.\d+)*)', str(title).strip())
    return match.group(1) if match else None

df_all['Level'] = df_all['Title'].apply(extract_level)
df_all = df_all.dropna(subset=['Level'])

# 创建 PyVis 网络图
net = Network(height='750px', width='100%', directed=True, font_color='black')
net.force_atlas_2based()

# 设置最大层级（例如只展示到 1.1 层）
max_level = 2

# 构建图谱
for _, row in df_all.iterrows():
    doc = row['Document']
    title = row['Title']
    content = row['Content']
    level_code = row['Level']
    level_parts = level_code.split('.')

    if len(level_parts) > max_level:
        continue

    current_node = f"{level_code} {title}"
    net.add_node(current_node, label=title, title=content)

    if len(level_parts) == 1:
        parent_node = doc
        net.add_node(doc, label=doc, title=f"文档：{doc}")
    else:
        parent_code = '.'.join(level_parts[:-1])
        parent_row = df_all[df_all['Level'] == parent_code]
        parent_title = parent_row['Title'].values[0] if not parent_row.empty else parent_code
        parent_node = f"{parent_code} {parent_title}"

    net.add_edge(parent_node, current_node)

# 保存为交互式 HTML 网页
net.show("knowledge_graph.html")
```
