import os
import re
import subprocess
import tempfile

def convert_doc_to_pdf(uploaded_file) -> str:
    """
    把上传的 .doc/.docx 文件保存到临时目录，先给它一个“安全”不含空格/特殊字符的名字，
    再用 LibreOffice 转 PDF，返回转换后的 PDF 路径。
    """
    # 1) 清洗文件名（去掉空格、&、/，替换为下划线）
    raw = os.path.splitext(uploaded_file.filename)[0]
    safe_stem = re.sub(r'[ \t/&\\\\]+', '_', raw)
    ext = os.path.splitext(uploaded_file.filename)[1]  # 包含“.”的后缀

    # 2) 准备临时目录和文件路径
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, safe_stem + ext)

    # 3) 写入上传内容
    with open(input_path, "wb") as f:
        f.write(uploaded_file.file.read())

    # 4) 调用 LibreOffice CLI 转 PDF
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", "pdf",
        "--outdir", tmp_dir,
        input_path
    ], check=True)

    # 5) 输出 PDF 文件路径（同样用 safe_stem）
    output_pdf = os.path.join(tmp_dir, safe_stem + ".pdf")
    if not os.path.exists(output_pdf):
        raise RuntimeError(f"File at path {output_pdf} does not exist.")
    return output_pdf
