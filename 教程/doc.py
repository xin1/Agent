# convert_doc.py
import os
import subprocess
from uuid import uuid4


def convert_to_pdf(upload_file, save_dir="converted_pdfs"):
    os.makedirs(save_dir, exist_ok=True)
    filename = upload_file.filename
    file_ext = filename.lower().split('.')[-1]

    unique_name = f"{uuid4().hex}_{filename}"
    input_path = os.path.join(save_dir, unique_name)

    with open(input_path, "wb") as f:
        f.write(upload_file.file.read())

    if file_ext == "pdf":
        return input_path  # 已是 PDF
    elif file_ext in ["doc", "docx"]:
        output_pdf = input_path.rsplit('.', 1)[0] + ".pdf"
        try:
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf", "--outdir", save_dir, input_path
            ], check=True)
            return output_pdf
        except Exception as e:
            raise RuntimeError(f"转换失败: {e}")
    else:
        raise ValueError("不支持的文件类型")
