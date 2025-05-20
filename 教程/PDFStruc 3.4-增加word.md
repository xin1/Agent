当然可以 ✅，将 `.doc` / `.docx` 转换为 `.pdf` 是一个稳妥的方案，特别适合你现有项目的结构（因为已支持 PDF 的裁剪与提取）。以下是你可以采用的完整方案，支持：

* `.pdf`：直接处理
* `.docx` / `.doc`：先转换为 `.pdf`，再统一处理

---

## ✅ 一、依赖库安装（一次性）

你需要安装 [`docx2pdf`](https://github.com/AlJohri/docx2pdf) 或 `comtypes`（Windows 专用）：

```bash
pip install docx2pdf
```

注意：

* `docx2pdf` 仅支持 **Windows** 和 **macOS**（Linux 下可选 LibreOffice）
* Windows 上它通过调用 Word 来转换，所以本地需安装 Microsoft Word

---

## ✅ 二、修改 `process.py`

我们在 `process_pdf_and_extract()` 函数外层包装一个统一入口 `process_file_and_extract()`，如下：

```python
import os
import fitz  # PyMuPDF
import csv
import re
import tempfile
from uuid import uuid4
from docx2pdf import convert

os.makedirs("outputs", exist_ok=True)

def convert_to_pdf(input_path: str) -> str:
    temp_dir = tempfile.mkdtemp()
    output_pdf_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(input_path))[0] + ".pdf")
    convert(input_path, output_pdf_path)
    return output_pdf_path

def process_pdf_and_extract(pdf_path: str, filename_hint: str, top_cm, bottom_cm):
    pdf = fitz.open(pdf_path)
    csv_path = f"outputs/{uuid4().hex}_{filename_hint}.csv"

    heading_pattern = re.compile(r'^(\d+(\.\d+)*)(\s+)(.+)')
    current_heading = None
    content_dict = {}

    for page in pdf:
        rect = page.rect
        top = top_cm * 28.35
        bottom = bottom_cm * 28.35
        clip = fitz.Rect(rect.x0, rect.y0 + top, rect.x1, rect.y1 - bottom)
        blocks = page.get_text("blocks", clip=clip)

        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        for block in sorted_blocks:
            text = block[4].strip()
            if not text:
                continue
            match = heading_pattern.match(text)
            if match:
                current_heading = f"{match.group(1)} {match.group(4).strip()}"
                content_dict[current_heading] = ""
            elif current_heading:
                content_dict[current_heading] += text + " "

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for heading, content in content_dict.items():
            writer.writerow([heading, content.strip()])

    return csv_path

def process_file_and_extract(file, top_cm, bottom_cm):
    suffix = file.filename.lower().split(".")[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    if suffix == "pdf":
        return process_pdf_and_extract(tmp_path, file.filename.rsplit('.', 1)[0], top_cm, bottom_cm)
    elif suffix in ["docx", "doc"]:
        pdf_path = convert_to_pdf(tmp_path)
        return process_pdf_and_extract(pdf_path, file.filename.rsplit('.', 1)[0], top_cm, bottom_cm)
    else:
        raise ValueError("不支持的文件类型，仅支持 PDF / DOCX / DOC")
```

---

## ✅ 三、修改 `app.py` 中调用方式

把 `process_pdf_and_extract` 改为新的 `process_file_and_extract`：

```python
from process import process_file_and_extract

# ...

@app.post("/process_batch/")
async def process_batch(files: List[UploadFile] = File(...), top_cm: float = Form(...), bottom_cm: float = Form(...)):
    csv_paths = []
    for file in files:
        csv_path = process_file_and_extract(file, top_cm, bottom_cm)
        csv_paths.append(csv_path)

    if len(csv_paths) == 1:
        return {"path": csv_paths[0], "is_zip": False}
    else:
        zip_path = zip_csvs(csv_paths)
        return {"path": zip_path, "is_zip": True}
```

---

## ✅ 四、效果说明

| 文件类型    | 处理方式              |
| ------- | ----------------- |
| `.pdf`  | 原生支持，直接处理         |
| `.docx` | 用 Word 转为 PDF，再处理 |
| `.doc`  | 同上                |

---

## 如遇问题

* 如果你使用的是 **Linux** 环境，请告知，我可以提供基于 LibreOffice 的转换方案。
* 如果你希望不依赖 Word，也可以使用 `unoconv` 或 `pandoc`（但布局可能不如 Word 精准）。

需要我进一步帮你自动化部署、Docker化或容错处理也可以继续提。是否现在就试试这个方案？
