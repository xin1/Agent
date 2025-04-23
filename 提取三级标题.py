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

# import re
# import csv
# from pathlib import Path
# import pdfplumber

# def extract_third_level_sections(pdf_path, output_csv, header_pattern, footer_pattern):
#     """
#     提取PDF中的三级标题及其内容，并保存到CSV文件。
    
#     参数:
#     - pdf_path: PDF文件路径
#     - output_csv: 输出CSV文件路径
#     - header_pattern: 页眉的正则表达式模式
#     - footer_pattern: 页尾的正则表达式模式
#     """
#     # 初始化CSV文件
#     with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(['标题', '内容'])  # CSV表头
        
#         with pdfplumber.open(pdf_path) as pdf:
#             current_section = None
#             current_content = []
            
#             for page in pdf.pages:
#                 text = page.extract_text()
#                 if not text:
#                     continue
                
#                 # 删除页眉和页尾
#                 text = remove_header_footer(text, header_pattern, footer_pattern)
                
#                 for line in text.split('\n'):
#                     line = line.strip()
#                     if not line:
#                         continue
                    
#                     # 检测三级标题（1.1.1格式）
#                     if is_third_level_header(line):
#                         # 保存前一章节
#                         if current_section:
#                             writer.writerow([
#                                 current_section,
#                                 '\n'.join(clean_content(current_content))
#                             ])
                        
#                         current_section = line
#                         current_content = []
#                     elif current_section:  # 只收集三级标题下的内容
#                         current_content.append(line)
            
#             # 写入最后一个章节
#             if current_section:
#                 writer.writerow([
#                     current_section,
#                     '\n'.join(clean_content(current_content))
#                 ])

# def is_third_level_header(line):
#     """严格匹配三级标题（1.1.1格式）"""
#     return bool(re.match(r'^\d+\.\d+\.\d+\b', line.strip()))

# def clean_content(content_lines):
#     """清洗内容文本"""
#     cleaned = []
#     for line in content_lines:
#         line = line.strip()
#         if not line:
#             continue
        
#         # 合并被错误分割的行（如结尾没有标点）
#         if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
#             cleaned[-1] += ' ' + line
#         else:
#             cleaned.append(line)
#     return cleaned

# def remove_header_footer(text, header_pattern, footer_pattern):
#     """
#     删除文本中的页眉和页尾。
    
#     参数:
#     - text: 页面文本
#     - header_pattern: 页眉的正则表达式模式
#     - footer_pattern: 页尾的正则表达式模式
    
#     返回:
#     - 删除页眉和页尾后的文本
#     """
#     lines = text.split('\n')
#     header_match = None
#     footer_match = None
    
#     # 检测页眉
#     for i, line in enumerate(lines):
#         if re.match(header_pattern, line.strip()):
#             header_match = i
#             break
    
#     # 检测页尾（从后往前匹配）
#     for i in range(len(lines) - 1, -1, -1):
#         if re.match(footer_pattern, lines[i].strip()):
#             footer_match = i
#             break
    
#     # 删除页眉和页尾
#     if header_match is not None:
#         lines = lines[header_match + 1:]  # 删除页眉及之前的行
#     if footer_match is not None:
#         lines = lines[:footer_match]  # 删除页尾及之后的行
    
#     return '\n'.join(lines)

# # 使用示例
# if __name__ == "__main__":
#     pdf_path = input("请输入PDF文件路径: ").strip()
#     output_csv = input("请输入输出CSV文件路径: ").strip()
    
#     # 用户输入页眉和页尾的正则表达式模式
#     header_pattern = input("请输入页眉的正则表达式模式（如：'^公司名称'）: ").strip()
#     footer_pattern = input("请输入页尾的正则表达式模式（如：'^第\\d+页 共\\d+页'）: ").strip()
    
#     try:
#         extract_third_level_sections(pdf_path, output_csv, header_pattern, footer_pattern)
#         print(f"成功提取三级标题内容到: {output_csv}")
#     except Exception as e:
#         print(f"处理失败: {str(e)}")
