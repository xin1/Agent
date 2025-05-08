# 📚 PDFStruc 1.0 开发手记  

### 🚀 初始想法  
> "Dify处理分段效果不佳，如何才能让PDF文档结构化，使分段时更好划分，大模型更好理解？"  
> "🤔似乎可以用标题来划分。"  

### 🛠️ 干  
**代码初体验** 🔗：[三级标题提取_生成csv.py](../code/base/Remove_extraction.py)  
看了看要处理的文档，大模型需要理解的主要内容几乎都在三级标题内，想着先试试提取出类似1.1.1的三级标题到第一列，三级标题后内容提取到第二列。
```python
# 实现功能：将Pdf三级标题提取到一列，后内容提取到第二列，生成Csv文件

import re
import csv
from pathlib import Path
import pdfplumber

def extract_third_level_sections(pdf_path, output_csv):
    
    # 初始化CSV文件
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['三级标题', '内容'])  # CSV表头
        
        with pdfplumber.open(pdf_path) as pdf:
            current_section = None
            current_content = []
            
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                    
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 检测三级标题（1.1.1格式）
                    if is_third_level_header(line):
                        # 保存前一章节
                        if current_section:
                            writer.writerow([
                                current_section,
                                '\n'.join(clean_content(current_content))
                            ])
                        
                        current_section = line
                        current_content = []
                    elif current_section:  # 只收集三级标题下的内容
                        current_content.append(line)
            
            # 写入最后一个章节
            if current_section:
                writer.writerow([
                    current_section,
                    '\n'.join(clean_content(current_content))
                ])

def is_third_level_header(line):
    """严格匹配三级标题（1.1.1格式）"""
    return bool(re.match(r'^\d+\.\d+\.\d+\b', line.strip()))

def clean_content(content_lines):
    """清洗内容文本"""
    cleaned = []
    for line in content_lines:
        line = line.strip()
        if not line:
            continue
        
        # 合并被错误分割的行（如结尾没有标点）
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

# 使用示例
if __name__ == "__main__":
    pdf_path = r"D:\Files\xFusion\1.pdf"
    output_csv = r"D:\Files\xFusion\1.csv"
    
    try:
        extract_third_level_sections(pdf_path, output_csv)
        print(f"成功提取三级标题内容到: {output_csv}")
    except Exception as e:
        print(f"处理失败: {str(e)}")

```
**成果**：导出三级标题 CSV（）  

### 🤯 遇到的问题：页眉页脚捣乱  
**发现问题**：  
- 每页顶部的「XX公司」被当成了标题  
- 页脚的页码和下一段数字连在了一起，原本的数字3变成了333  

**暴力解决** 🔗：[裁剪边距_处理页眉页尾.py](../code/base/Remove_extraction.py)  
```python
# 实现功能：裁剪页眉页尾，初始上下裁剪60pt
# 简单粗暴的裁剪逻辑
# 上下各切60单位（像素）

import fitz  # PyMuPDF
import os

# 输入输出路径
input_path = r"F:\Fusion\.py\input.pdf"
output_path = r"F:\Fusion\.py\output_no_header_footer.pdf"

# 打开 PDF
doc = fitz.open(input_path)

# 对每一页裁剪（上 50pt，下 50pt 可调）
for page in doc:
    rect = page.rect
    crop_rect = fitz.Rect(
        rect.x0, rect.y0 + 60,  # 去掉顶部 60pt
        rect.x1, rect.y1 - 60   # 去掉底部 60pt
    )
    page.set_cropbox(crop_rect)

# 保存处理后的 PDF
doc.save(output_path)
doc.close()

print("处理完成，保存为：", output_path)
```
**副作用**：切太狠导致正文文字被砍掉  
**解决**让用户输入来输入要切除的边距  

### 🧠 合并两个功能  

**初方案合并** 🔗：[处理页眉页尾_提取标题后生成csv.py](../code/base/Remove_extraction.py)  
```python
# 实现功能：裁剪页眉页尾后，提取例 1 / 1.1 / 1.1.1 开头的标题为第一列，后内容为第二列，生成csv文件，
import fitz  # PyMuPDF
import re
import csv

def extract_multilevel_from_cropped_pdf(input_pdf, output_csv, top_crop=55, bottom_crop=55):
    doc = fitz.open(input_pdf)

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        current_title = None
        current_content = []

        for page in doc:
            rect = page.rect
            crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
            text = page.get_text(clip=crop_rect)

            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                header = get_smart_header(line)
                if header:
                    # 写入上一节
                    if current_title:
                        writer.writerow([
                            current_title,
                            '\n'.join(clean_content(current_content))
                        ])
                    current_title = line
                    current_content = []
                elif current_title:
                    current_content.append(line)

        # 写入最后一节
        if current_title:
            writer.writerow([
                current_title,
                '\n'.join(clean_content(current_content))
            ])

    doc.close()

def get_smart_header(line):
    """
    更智能的标题识别：
    - 以 1 / 1.1 / 1.1.1 开头
    - 总长度不超过50字符（防止正文误判为标题）
    """
    line = line.strip()
    if len(line) > 50:
        return None
    if re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line):
        return line
    return None

def clean_content(content_lines):
    """
    合并断开的句子行：如果前一行没有标点，和下一行合并
    """
    cleaned = []
    for line in content_lines:
        if not line:
            continue
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

# ======== 主程序入口 =========
if __name__ == "__main__":
    input_pdf = r"D:\Files\xFusion\Tu.pdf"
    output_csv = r"D:\Files\xFusion\Tu_structured_output_2.csv"

    try:
        extract_multilevel_from_cropped_pdf(input_pdf, output_csv)
        print(f"✅ 成功提取并导出至 CSV：{output_csv}")
    except Exception as e:
        print(f"❌ 出错：{str(e)}")
```
**成果**：提取出干净的结构化 CSV 文件🎉  


### 📸 开发效果截图  
机密文件，可不敢上传🤭  

### 🔮 下一步计划  
1. 🔍 有些文档除了三级标题内容重要，一级二级也重要，有些文档没有1.1.1咋办呀  
2. 📊 别人咋用嘞，光你自己用  
3. 🤖 冗余内容有点多，自动裁的估计还得手动改一下
