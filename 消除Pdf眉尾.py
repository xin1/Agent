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
        rect.x0, rect.y0 + 60,  # 去掉顶部 50pt
        rect.x1, rect.y1 - 60   # 去掉底部 50pt
    )
    page.set_cropbox(crop_rect)

# 保存处理后的 PDF
doc.save(output_path)
doc.close()

print("处理完成，保存为：", output_path)
