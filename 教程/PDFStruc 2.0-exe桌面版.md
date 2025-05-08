# PDFStruc 2.0-exe桌面版
## code🔗 : [exe](../code/exe/pdf_tool_gui)
把 PDF 工具封装成一个本地 `.exe` 桌面版，**双击即可运行、选择文件、输出结果，无需网页上传，完全离线**

---

## ✅ 功能（.exe 将具备）

- 📂 选择 PDF 文件  
- ✂️ 手动输入裁剪上下边距（单位像素）  
- 🧠 自动裁剪页眉页脚  
- 📑 提取标题+内容到 CSV 文件  
- 📥 输出两个文件：裁剪后 PDF 和 CSV（保存在同一目录）

---

## 🧰 一次性准备工作（本机配置）

### ✅ 1. 安装必要依赖

用命令行运行：

```bash
pip install pymupdf pdfplumber tkinter
```

---

## 🧠 步骤一：Python 脚本 `pdf_tool_gui.py`

创建一个名为 `pdf_tool_gui.py` 的文件，内容如下：

```python
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz
import pdfplumber
import re
import csv
import os

def crop_pdf(input_pdf, output_pdf, top_crop, bottom_crop):
    doc = fitz.open(input_pdf)
    for page in doc:
        rect = page.rect
        crop_rect = fitz.Rect(rect.x0, rect.y0 + top_crop, rect.x1, rect.y1 - bottom_crop)
        page.set_cropbox(crop_rect)
    doc.save(output_pdf)
    doc.close()

def extract_pdf_sections(input_pdf, output_csv):
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['标题', '内容'])

        current_title = None
        current_content = []

        with pdfplumber.open(input_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    header = get_smart_header(line)
                    if header:
                        if current_title:
                            writer.writerow([
                                current_title,
                                '\n'.join(clean_content(current_content))
                            ])
                        current_title = line
                        current_content = []
                    elif current_title:
                        current_content.append(line)

            if current_title:
                writer.writerow([
                    current_title,
                    '\n'.join(clean_content(current_content))
                ])

def get_smart_header(line):
    line = line.strip()
    if len(line) > 50:
        return None
    if re.match(r'^\d+(\.\d+){0,2}(\s+|$)', line):
        return line
    return None

def clean_content(content_lines):
    cleaned = []
    for line in content_lines:
        if not line:
            continue
        if cleaned and not cleaned[-1][-1] in ('。', '；', '!', '?', '.', '”'):
            cleaned[-1] += ' ' + line
        else:
            cleaned.append(line)
    return cleaned

def run_tool():
    file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if not file_path:
        return

    try:
        top_crop = int(entry_top.get())
        bottom_crop = int(entry_bottom.get())
    except ValueError:
        messagebox.showerror("错误", "请输入有效的数字！")
        return

    base = os.path.splitext(file_path)[0]
    cropped_pdf = base + "_cropped.pdf"
    output_csv = base + "_output.csv"

    crop_pdf(file_path, cropped_pdf, top_crop, bottom_crop)
    extract_pdf_sections(cropped_pdf, output_csv)

    messagebox.showinfo("完成", f"✅ 裁剪后的PDF和CSV已生成：\n\n{cropped_pdf}\n{output_csv}")

# ===== GUI界面 =====
root = tk.Tk()
root.title("📄 PDF裁剪 + 标题提取工具 (.exe桌面版)")
root.geometry("400x200")

tk.Label(root, text="裁剪上边距 (px):").pack(pady=(10, 0))
entry_top = tk.Entry(root)
entry_top.insert(0, "50")
entry_top.pack()

tk.Label(root, text="裁剪下边距 (px):").pack(pady=(10, 0))
entry_bottom = tk.Entry(root)
entry_bottom.insert(0, "50")
entry_bottom.pack()

tk.Button(root, text="选择PDF并运行", command=run_tool, bg="#4CAF50", fg="white").pack(pady=20)

root.mainloop()
```

---

## 🧾 步骤二：将其打包为 `.exe`

### ✅ 安装 PyInstaller（只需一次）：

```bash
pip install pyinstaller
```

### ✅ 在脚本目录运行打包命令：

```bash
pyinstaller --noconsole --onefile pdf_tool_gui.py
```

解释：

- `--noconsole`：打包为纯 GUI 程序，不弹出命令行窗口  
- `--onefile`：打包为一个独立 `.exe` 文件

---

## 📁 打包成功后

你会在 `dist` 文件夹下看到：

```
pdf_tool_gui.exe
```

💡 双击运行这个文件，就是你自己的桌面 PDF 工具！

---

### ✅ 如果你不方便打包 `.exe`

我也可以帮你远程打好后发给你（你需要可以下载的渠道，比如邮箱、网盘等）。

要不要我帮你直接打好 `.exe`？还是你自己动手试试？
