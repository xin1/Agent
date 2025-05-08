---

# 📚 PDFStruc 1.0 开发手记  
## 💡 灵机一动  

### 🚀 初始想法  
> "Dify处理分段效果不佳，如何才能让PDF文档结构化，使分段时更好划分，大模型更好理解？"  
> "🤔似乎可以用标题来划分。"  

### 🛠️ 第一个动手实验  
**代码初体验** 🔗：[三级标题提取_生成csv.py](../code/base/Remove_extraction.py)  
看了看要处理的文档，大模型需要理解的主要内容几乎都在三级标题内，想着先试试提取出类似1.1.1的三级标题到第一列，三级标题后内容提取到第二列。
**成果**：导出三级标题 CSV（）  

### 🤯 遇到的问题：页眉页脚捣乱  
**发现问题**：  
- 每页顶部的「XX公司」被当成了标题  
- 页脚的页码和下一段数字连在了一起，原本的数字3变成了333  

**暴力解决** 🔗：[裁剪边距_处理页眉页尾.py](../code/base/Remove_extraction.py)  
```python
# 简单粗暴的裁剪逻辑
# 上下各切60单位（像素）
```
**副作用**：切太狠导致正文文字被砍掉  
**解决**让用户输入来输入要切除的边距  

### 🧠 合并两个功能  

**初方案合并** 🔗：[处理页眉页尾_提取标题后生成csv.py](../code/base/Remove_extraction.py)  
```python
def smart_process(pdf_path):
    # 1. 智能裁剪（保留正文安全区）
    cleaned_pages = crop_smartly(pdf_path)  # 改进版裁剪算法
    
    # 2. 标题侦探模式
    all_titles = []
    for page in cleaned_pages:
        titles = find_titles_with_context(page)  # 加入上下文判断
        all_titles.extend(titles)
    
    # 3. 生成带层级的CSV
    export_with_hierarchy(all_titles, "output.csv")
```
**成果**：提取出干净的结构化 CSV 文件🎉  


### 📸 开发效果截图  
机密文件，可不敢上传🤭  

### 🔮 下一步计划  
1. 🔍 有些文档除了三级标题内容重要，一级二级也重要，有些文档没有1.1.1咋办呀  
2. 📊 别人咋用嘞，光你自己用  
3. 🤖 冗余内容有点多，自动裁的估计还得手动改一下

---
