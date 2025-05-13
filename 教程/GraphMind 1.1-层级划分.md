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
