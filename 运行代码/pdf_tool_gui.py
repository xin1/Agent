import fitz  # PyMuPDF
import re
import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def extract_pdf(input_pdf, top_percent, bottom_percent):
    output_csv = os.path.splitext(input_pdf)[0] + "_output.csv"
    cropped_pdf = os.path.splitext(input_pdf)[0] + "_cropped.pdf"
    
    doc = fitz.open(input_pdf)
    cropped_doc = fitz.open()
    
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        current_title = None
        current_content = []

        for i, page in enumerate(doc):
            h = page.rect.height
            top_crop = h * top_percent / 100
            bottom_crop = h * bottom_percent / 100
            crop_rect = fitz.Rect(page.rect.x0, page.rect.y0 + top_crop, page.rect.x1, page.rect.y1 - bottom_crop)
            text = page.get_text(clip=crop_rect)

            new_page = cropped_doc.new_page(width=page.rect.width, height=crop_rect.height)
            new_page.show_pdf_page(fitz.Rect(0, 0, page.rect.width, crop_rect.height), doc, i, clip=crop_rect)

            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                header = get_smart_header(line)
                if header:
                    if current_title:
                        writer.writerow([current_title, '\n'.join(clean_content(current_content))])
                    current_title = line
                    current_content = []
                elif current_title:
                    current_content.append(line)

        if current_title:
            writer.writerow([current_title, '\n'.join(clean_content(current_content))])

    cropped_doc.save(cropped_pdf)
    cropped_doc.close()
    doc.close()
    return output_csv, cropped_pdf

def get_smart_header(line):
    if len(line) > 50:
        return None
    if re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line):
        return line
    return None

def clean_content(lines):
    cleaned = []
    for line in lines:
        if not line:
            continue
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

def browse_file():
    path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if path:
        entry_pdf.delete(0, tk.END)
        entry_pdf.insert(0, path)

def run_extraction():
    path = entry_pdf.get()
    if not os.path.isfile(path):
        messagebox.showerror("错误", "请提供有效的PDF文件路径")
        return

    try:
        top = float(entry_top.get())
        bottom = float(entry_bottom.get())
    except:
        messagebox.showerror("错误", "裁剪比例请输入数字")
        return

    try:
        csv_out, pdf_out = extract_pdf(path, top, bottom)
        messagebox.showinfo("成功", f"已生成:\n{csv_out}\n{pdf_out}")
    except Exception as e:
        messagebox.showerror("错误", str(e))

# ========= GUI 界面 ===========
root = tk.Tk()
root.title("PDF标题内容提取工具")

tk.Label(root, text="选择PDF文件:").grid(row=0, column=0, sticky="e")
entry_pdf = tk.Entry(root, width=40)
entry_pdf.grid(row=0, column=1)
tk.Button(root, text="浏览", command=browse_file).grid(row=0, column=2)

tk.Label(root, text="上裁剪比例（%）:").grid(row=1, column=0, sticky="e")
entry_top = tk.Entry(root, width=10)
entry_top.insert(0, "10")
entry_top.grid(row=1, column=1, sticky="w")

tk.Label(root, text="下裁剪比例（%）:").grid(row=2, column=0, sticky="e")
entry_bottom = tk.Entry(root, width=10)
entry_bottom.insert(0, "10")
entry_bottom.grid(row=2, column=1, sticky="w")

tk.Button(root, text="开始处理", command=run_extraction, bg="#4CAF50", fg="white").grid(row=3, column=1, pady=10)

root.mainloop()
