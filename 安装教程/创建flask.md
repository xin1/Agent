 **前端页面做成 Flask 静态页面服务**

---

## ✅ 一、完整项目结构

```
pdf_tool_app/
├── app.py                # Flask 后端主程序
├── pdf_processor.py      # PDF 裁剪与提取逻辑
├── static/
│   └── style.css         # 可选的 CSS
├── templates/
│   └── index.html        # 前端页面 HTML
├── requirements.txt      # 所需依赖
└── Dockerfile            # Docker 部署文件（可选）
```

---

## ✅ 二、前端页面（`templates/index.html`）

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>PDF 裁剪工具</title>
</head>
<body style="max-width: 600px; margin: 40px auto; font-family: sans-serif;">
  <h2>📄 PDF 裁剪与提取工具</h2>
  <form action="/process" method="post" enctype="multipart/form-data">
    <label>选择 PDF 文件：</label><br>
    <input type="file" name="file" accept="application/pdf" required><br><br>
    <label>删除顶部（厘米）：</label><br>
    <input type="number" name="top_cm" value="2.5" step="0.1" required><br><br>
    <label>删除底部（厘米）：</label><br>
    <input type="number" name="bottom_cm" value="2.5" step="0.1" required><br><br>
    <button type="submit">开始处理</button>
  </form>
</body>
</html>
```

---

## ✅ 三、Flask 后端代码（`app.py`）

```python
from flask import Flask, request, render_template, send_file
from pdf_processor import process_pdf
import os
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def handle_upload():
    file = request.files["file"]
    top_cm = float(request.form["top_cm"])
    bottom_cm = float(request.form["bottom_cm"])

    filename = secure_filename(file.filename)
    temp_path = os.path.join("temp_" + filename)
    file.save(temp_path)

    cropped_pdf, csv_file = process_pdf(temp_path, top_cm, bottom_cm)
    os.remove(temp_path)

    return f"""
        ✅ 处理完成！<br>
        <a href="/download?path={cropped_pdf}">📥 下载 PDF</a><br>
        <a href="/download?path={csv_file}">📥 下载 CSV</a>
    """

@app.route("/download")
def download():
    path = request.args.get("path")
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

---

## ✅ 四、`requirements.txt`

```txt
flask
pymupdf
```

---

## ✅ 五、运行项目（不需要 Docker）

```bash
# 1. 创建虚拟环境（可选）
python -m venv venv
venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python app.py
```

然后在浏览器打开：[http://localhost:8000](http://localhost:8000)

---

