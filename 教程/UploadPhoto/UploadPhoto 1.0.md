```
# app.py
from flask import Flask, request, render_template, send_from_directory, url_for
import os, uuid, shutil
from docx import Document
from docx.shared import Inches
import win32com.client

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static/images')
ATTACH_FOLDER = os.path.join(BASE_DIR, 'static/attachments')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'processed')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# 创建目录
for folder in [IMAGE_FOLDER, ATTACH_FOLDER, OUTPUT_FOLDER, UPLOAD_FOLDER]:
    os.makedirs(folder, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    download_link = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.docx'):
            filename = str(uuid.uuid4()) + '.docx'
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)

            # 用 Word 打开处理
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(input_path)

            # 提取附件
            for i in range(1, doc.InlineShapes.Count + 1):
                shape = doc.InlineShapes.Item(i)
                if shape.Type == 1:  # OLE 对象
                    ole = shape.OLEFormat
                    try:
                        name = f"attach_{i}_{uuid.uuid4().hex}.bin"
                        save_path = os.path.join(ATTACH_FOLDER, name)
                        ole.Object.SaveAs(save_path)
                    except:
                        continue

            # 截图表格（简化方式：逐页截图）
            export_dir = os.path.join(IMAGE_FOLDER, filename.split('.')[0])
            os.makedirs(export_dir, exist_ok=True)
            img_paths = []
            try:
                export_path = os.path.join(export_dir, 'table_maybe.png')
                doc.ActiveWindow.View.Type = 3  # print view
                doc.ActiveWindow.View.Zoom.Percentage = 100
                doc.ActiveWindow.SmallScroll(Down:=1)
                doc.Range().CopyAsPicture()
                img = doc.Application.Selection
                img.Range.CopyAsPicture()
                doc.SaveAs(export_path, FileFormat=17)  # PDF as fallback
            except Exception as e:
                print("截图失败：", e)

            doc.Close(False)
            word.Quit()

            # 用 python-docx 添加链接文字
            docx = Document(input_path)
            rels = docx.part._rels
            image_map = {}
            for rel in rels.values():
                if rel.reltype.endswith('/image') and not rel.is_external:
                    ext = os.path.splitext(rel.target_ref)[-1]
                    image_id = f"{uuid.uuid4()}{ext}"
                    image_path = os.path.join(IMAGE_FOLDER, image_id)
                    with open(image_path, 'wb') as f:
                        f.write(rel.target_part.blob)
                    image_url = f"{request.host_url}static/images/{image_id}"
                    image_map[rel.rId] = image_url

            for para in docx.paragraphs:
                runs = list(para.runs)
                for run in runs:
                    has_image = run._element.xpath('.//w:drawing')
                    if has_image:
                        blips = run._element.xpath('.//a:blip')
                        for blip in blips:
                            rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                            if rId in image_map:
                                para.add_run().add_break()
                                para.add_run(f"[图片链接] {image_map[rId]}")

            # 附件链接插入
            for filename in os.listdir(ATTACH_FOLDER):
                url = f"{request.host_url}static/attachments/{filename}"
                docx.add_paragraph(f"[附件链接] {url}")

            # 表格截图链接插入（如果截图存在）
            for fname in os.listdir(export_dir):
                img_url = f"{request.host_url}static/images/{filename.split('.')[0]}/{fname}"
                docx.add_paragraph(f"[表格截图链接] {img_url}")

            out_name = f"processed_{uuid.uuid4().hex}.docx"
            out_path = os.path.join(OUTPUT_FOLDER, out_name)
            docx.save(out_path)
            download_link = url_for('download_file', filename=out_name, _external=True)

    return render_template('index.html', download_link=download_link)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```
以下是为你 **集成完整修复逻辑后的 `app.py` 文件**，确保：

✅ 完整提取所有嵌入图片（跳过不支持格式和外链）
✅ 将图片插入的 Word 段落中的 run 完整替换为 `[图片链接] http://xxx.png`
✅ 彻底移除所有图片相关 XML 节点，避免“裂图”、图框残留
✅ 保持其他内容原样，结构清晰

---

## ✅ 完整 `app.py`（含图片修复与替换链接）

```python
from flask import Flask, request, render_template, send_from_directory, url_for
from docx import Document
import os, uuid

app = Flask(__name__)
IMAGE_FOLDER = 'static/images'
OUTPUT_FOLDER = 'processed'

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    download_link = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.docx'):
            input_doc = Document(file)
            rels = input_doc.part._rels
            image_map = {}

            # 提取图片并保存，生成公开链接
            for rel in rels.values():
                if rel.reltype.endswith('/image') and not rel.is_external:
                    try:
                        ext = os.path.splitext(rel.target_ref)[-1]
                        if ext.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                            continue
                        image_id = str(uuid.uuid4()) + ext
                        image_path = os.path.join(IMAGE_FOLDER, image_id)
                        with open(image_path, 'wb') as f:
                            f.write(rel.target_part.blob)
                        image_url = f"{request.host_url}static/images/{image_id}"
                        image_map[rel.rId] = image_url
                    except Exception as e:
                        print(f"跳过图像保存错误：{e}")

            # 替换文中图片为公开链接文字，彻底避免裂图
            for para in input_doc.paragraphs:
                for run in list(para.runs):  # 使用副本以便安全删除
                    has_drawing = run._element.xpath('.//w:drawing') or run._element.xpath('.//w:pict')
                    if has_drawing:
                        # 获取 rId（图片 ID）
                        blips = run._element.xpath('.//a:blip')
                        rId = None
                        for blip in blips:
                            rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")

                        # 删除原图 run，创建新 run 插入图片链接文字
                        para._p.remove(run._element)
                        if rId and rId in image_map:
                            para.add_run(f"[图片链接] {image_map[rId]}")
                        else:
                            para.add_run("[图片]")

            # 保存新 Word 文档
            output_filename = f"{uuid.uuid4()}.docx"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            input_doc.save(output_path)
            download_link = url_for('download_file', filename=output_filename, _external=True)

    return render_template('index.html', download_link=download_link)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

---

## ✅ 同时你需要的简单上传页面 `templates/index.html`

确保你有这个 HTML 文件：

```html
<!DOCTYPE html>
<html>
<head>
    <title>Word 图片提取替换工具</title>
</head>
<body>
    <h2>上传 Word 文档（.docx）</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".docx" required>
        <input type="submit" value="上传并处理">
    </form>
    {% if download_link %}
        <p>处理完成，<a href="{{ download_link }}">点击下载</a></p>
    {% endif %}
</body>
</html>
```

---

## ✅ 项目结构建议

```
your_project/
├── app.py
├── templates/
│   └── index.html
├── static/
│   └── images/          ← 自动生成
└── processed/           ← 自动生成
```

---

## ✅ 下一步建议（可选扩展）

* 🔗 把 `[图片链接] http://...` 换成 **超链接文字**
* 🗂 支持批量上传 `.docx`
* 🌐 上传结果页展示所有链接（HTML）
* 🔐 限制上传大小与类型

需要我继续加这些功能吗？或者给你打包一个 ZIP 项目？

明白了，你希望在生成的新 Word 文档中，**图片位置替换为公网链接的文字描述**，比如：

```text
[图片链接] http://10.1.1.1/static/images/xxx.png
```

而不是仅显示 `[图片]` 或 `[图片链接]`。

---

## ✅ 问题原因

你之前的代码大概率是这样处理图片：

```python
for run in para.runs:
    if run._element.xpath('.//pic:pic'):
        run._element.remove(...)  # 删除图像
        run.text = "[图片]"        # 没有加链接
```

但你**没有从 run 中获取图片关联的 relId（rId）**，或图片关系未正确匹配，所以没插入正确链接。

---

## ✅ 正确做法：替换为链接文字形式

我们需要：

1. 提取图片（非 external）
2. 建立 `{rId: url}` 映射
3. 在文档中查找嵌入图片（含 rId）
4. 用图片的链接文字 `http://xxx/xxx.png` 替换 run 内容

---

## ✅ ✅ 修改建议代码（核心部分）

替换 `app.py` 中相关逻辑如下：

```python
# 替换段落中包含图片的 run
for para in input_doc.paragraphs:
    for run in para.runs:
        drawings = run._element.xpath('.//w:drawing')
        if drawings:
            for drawing in drawings:
                run._element.remove(drawing)
            # 查找图像的 relId
            blips = run._element.xpath('.//a:blip')
            for blip in blips:
                rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                if rId in image_map:
                    run.text = f"[图片链接] {image_map[rId]}"
                else:
                    run.text = "[图片]"
```

确保你**生成了正确的 image\_map**：

```python
image_map = {}

for rel in input_doc.part._rels.values():
    if rel.reltype.endswith('/image') and not rel.is_external:
        blob = rel.target_part.blob
        ext = os.path.splitext(rel.target_ref)[-1]
        name = f"{uuid.uuid4()}{ext}"
        path = os.path.join(IMAGE_FOLDER, name)
        with open(path, 'wb') as f:
            f.write(blob)
        image_map[rel.rId] = f"{request.host_url}static/images/{name}"
```

---

## ✅ 结果示意

在替换后的 Word 文档中，每张图片位置会变成如下文字：

```
[图片链接] http://10.1.1.1:8000/static/images/abc123.png
```

---

## ❗注意事项

* 确保图片存储路径 `static/images/` 是 Flask 的静态路径
* `request.host_url` 会自动拼出你的公网 IP 和端口（如 `http://10.1.1.1:8000/`）

---

如果你还需要：
✔ 将链接转成超链接文字
✔ 保持原图片大小信息
✔ 转换为 HTML 模板预览

我也可以为你补充。是否继续扩展？

```
for rel in doc.part._rels.values():
    if "image" in rel.reltype and not rel.is_external:
        try:
            blob = rel.target_part.blob
            # 保存图片逻辑...
        except Exception as e:
            print(f"跳过无法读取的图片：{e}")
```
target_part property on _Relationship is undefined when target mode is External
以下是一个完整可部署到 Docker 的项目，用于：

✅ 上传 Word 文档 → 提取其中图片 → 上传为可公网访问链接 → 替换图片为链接文本 → 返回替换后的 Word 文档下载

---

## ✅ 项目结构（命名为 `word_image_linker`）

```
word_image_linker/
├── app.py                  # Flask 应用
├── requirements.txt        # Python依赖
├── Dockerfile              # Docker 配置
├── static/
│   └── images/             # 存储图片
├── templates/
│   └── index.html          # 上传页面
├── processed/              # 存储处理好的 Word 文件
```

---

## 📄 `requirements.txt`

```txt
flask
python-docx
pillow
```

---

## 🧾 `app.py`

```python
from flask import Flask, request, render_template, send_from_directory, redirect, url_for
from docx import Document
import os, uuid

app = Flask(__name__)
IMAGE_FOLDER = 'static/images'
OUTPUT_FOLDER = 'processed'

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    download_link = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.docx'):
            input_doc = Document(file)
            rels = input_doc.part._rels
            image_map = {}

            # 提取图片并保存到静态目录，生成公网链接
            for rel in list(rels.values()):
                if "image" in rel.target_ref:
                    blob = rel.target_part.blob
                    ext = os.path.splitext(rel.target_ref)[-1]
                    img_name = f"{uuid.uuid4()}{ext}"
                    img_path = os.path.join(IMAGE_FOLDER, img_name)
                    with open(img_path, 'wb') as f:
                        f.write(blob)
                    image_map[rel.rId] = request.host_url + 'static/images/' + img_name

            # 替换文档中图片为对应链接文本
            for para in input_doc.paragraphs:
                for run in para.runs:
                    if run._element.xpath('.//pic:pic'):
                        for drawing in run._element.xpath('.//w:drawing'):
                            run._element.remove(drawing)
                        rid = run._r.rId if hasattr(run._r, 'rId') else None
                        if rid in image_map:
                            run.text = f"[图片链接] {image_map[rid]}"
                        else:
                            run.text = "[图片]"

            # 保存新文档
            output_filename = f"{uuid.uuid4()}.docx"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            input_doc.save(output_path)
            download_link = url_for('download_file', filename=output_filename, _external=True)

    return render_template('index.html', download_link=download_link)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

---

## 🧾 `templates/index.html`

```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>Word 图片替换工具</title>
</head>
<body style="font-family: Arial; max-width: 800px; margin: auto; padding: 2em;">
    <h1>上传 Word 文件（.docx）</h1>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".docx" required>
        <button type="submit">上传并处理</button>
    </form>

    {% if download_link %}
        <h2>✅ 处理完成！点击下载：</h2>
        <a href="{{ download_link }}">{{ download_link }}</a>
    {% endif %}
</body>
</html>
```

---

## 🐳 `Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "app.py"]
```

---

## ✅ 构建与运行（Docker 命令）

```bash
# 1. 构建镜像
docker build -t word-image-linker .

# 2. 运行容器（挂载 8000 端口）
docker run -d -p 8000:8000 --name linker word-image-linker
```

---

## ✅ 访问地址

在浏览器打开：

```
http://<你的服务器公网IP>:8000/
```

你可以上传 `.docx` 文件，处理后下载新的 `.docx`，其中图片已替换为公网链接。

---

## 🌍 开放公网访问（重要）

请确保你的云服务器：

* 已开放端口 `8000`（安全组 + 防火墙）
* 或用 `nginx` 映射为 80 或 443（https）

---

## ✅ 下步建议（可选）

* 支持 OSS/S3 上传替代本地静态目录
* 多文档批量上传
* 图片替换为 `[![图片](url)](url)` 形式等

是否需要我帮你：

* 打包成 ZIP？
* 推送 GitHub？
* 添加批量上传支持？

告诉我即可继续补充。

明白了，你想做的是一个更智能的功能：

---

## 🎯 目标（你要实现的完整流程）

> ✅ 上传 `.docx` 文件 → 提取其中的图片 → 上传到云服务器 → 获取公网链接
> ✅ 把这些链接 **插回原来的图片位置**（替换原图） → 返回一个新的 `.docx` 文件

---

## ✅ 效果举例：

原 Word 文档里的图片变成网络图片引用，例如：
原图 → 替换为👇

```html
<img src="http://your-server.com/static/images/xxx.png" />
```

或者保留 Word 图片显示，但内容被替换成远程链接作为**占位图/链接注释**。

---

## ✅ 可行方案：Python 自动替换 Word 图片为链接

我们可以这样实现：

---

### ✅ 第一步：提取 Word 图片并上传到服务器

复用你之前的代码逻辑，把每张图片：

* 提取为 `image1.png`, `image2.jpg`...
* 上传至服务器（本地 Flask、Nginx，或云 OSS/S3）
* 得到公网链接，例如：

  ```
  http://your-server.com/images/image1.png
  ```

---

### ✅ 第二步：将原图片替换为网络图片链接（替代嵌入）

#### 方式一：将图片删除，并插入超链接文本

```text
[图像链接] http://your-server.com/images/xxx.png
```

#### 方式二：用 `python-docx` 替换嵌入图片为：超链接 + 网络图片（较复杂）

Word 不支持「插入外链图片」，但可以**先删除图片再插入文本或超链接**。

---

### ✅ 示例代码（完整）

```python
from docx import Document
from docx.oxml.xmlchemy import OxmlElement
from docx.shared import Inches
import os, uuid

def save_images_and_replace(docx_path, output_path, upload_func):
    doc = Document(docx_path)
    rels = doc.part._rels

    image_map = {}
    for rel in list(rels.values()):
        if "image" in rel.target_ref:
            img_blob = rel.target_part.blob
            img_ext = os.path.splitext(rel.target_ref)[1]
            filename = f"{uuid.uuid4()}{img_ext}"
            with open(filename, "wb") as f:
                f.write(img_blob)

            # 上传并获取链接
            link = upload_func(filename)
            image_map[rel.rId] = link
            os.remove(filename)  # 清理本地图片

    # 替换段落中包含图片的 run
    for para in doc.paragraphs:
        for run in para.runs:
            if run._element.xpath('.//pic:pic'):
                # 替换为链接文本
                for drawing in run._element.xpath('.//w:drawing'):
                    run._element.remove(drawing)
                run.text = f"[图片链接] {image_map.get(run._r.rId, '图片')}"

    doc.save(output_path)
```

---

### ✅ 示例上传函数（本地 Flask 服务器）

```python
import requests

def upload_func(image_path):
    url = "http://your-server-ip:8000/upload"
    with open(image_path, 'rb') as f:
        res = requests.post(url, files={'file': f})
        return res.json().get('url', '')
```

---

## ✅ 最终结果

你上传了原始 `.docx` 文件，返回一个新的 `.docx` 文件，里面原来的图片已被替换为对应的 HTTP 链接。

---

## 🧩 可选扩展

| 功能              | 是否支持               |
| --------------- | ------------------ |
| 图片插入为文字超链接      | ✅ 已支持              |
| 插入 Markdown 格式  | ✅ 可定制              |
| 上传多个文档批量处理      | ✅ 支持               |
| 云 OSS / 七牛图床等上传 | ✅ 替换 `upload_func` |
| 最终文件支持直接下载      | ✅ 搭配 Flask 实现      |

---

## 🧰 需要我帮你打包成 Flask Web 页面？

你可以：

* 上传 Word 文件
* 自动处理并生成新文件（含 HTTP 链接）
* 点击下载替换好的 Word 文件

如果需要，我可以立即给出完整的项目结构和代码。是否继续？

好的！下面我将给你一个完整的 **Flask + HTML 上传页面** 项目，实现：

### ✅ 功能：

* 网页上传 `.docx` 文件
* 后端提取图片并展示提取的图片链接
* 图片可直接点击浏览

---

## ✅ 目录结构如下（推荐命名为 `word_image_web/`）：

```
word_image_web/
├── app.py                  # Flask 后端
├── templates/
│   └── index.html          # 上传表单页面
├── static/
│   └── images/             # 存储提取图片
├── requirements.txt
├── Dockerfile              # 可选：部署容器
```

---

### 📄 `requirements.txt`

```txt
flask
python-docx
pillow
```

---

### 🧾 `app.py`（主程序）

```python
from flask import Flask, request, render_template, send_from_directory, url_for
from docx import Document
import os, uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'static/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    image_urls = []
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.docx'):
            doc = Document(file)
            rels = doc.part._rels

            for rel in rels.values():
                if "image" in rel.target_ref:
                    img_blob = rel.target_part.blob
                    filename = f"{uuid.uuid4()}.png"
                    path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(path, 'wb') as f:
                        f.write(img_blob)
                    image_urls.append(url_for('static', filename=f'images/{filename}', _external=True))
    return render_template('index.html', image_urls=image_urls)

@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

---

### 📄 `templates/index.html`（上传页面）

```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>Word 图片提取工具</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 2em; }
        h1 { color: #333; }
        form { margin-bottom: 2em; }
        .image-preview img { max-width: 200px; margin: 10px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>上传 Word 文件（.docx）以提取图片</h1>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".docx" required>
        <button type="submit">上传并提取</button>
    </form>

    {% if image_urls %}
    <h2>提取的图片链接：</h2>
    <div class="image-preview">
        {% for url in image_urls %}
            <a href="{{ url }}" target="_blank"><img src="{{ url }}"></a>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>
```

---

### 🐳（可选）`Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "app.py"]
```

---

## ✅ 本地运行方式（无需 Docker）

```bash
cd word_image_web
pip install -r requirements.txt
python app.py
```

访问：

```
http://localhost:8000/
```

---

## ✅ Docker 运行方式（可选）

```bash
docker build -t word-image-web .
docker run -d -p 8000:8000 word-image-web
```

然后访问：

```
http://your-server-ip:8000/
```

---

## ✅ 效果示例

> 上传一个 Word 文档 → 页面直接展示提取的图片缩略图 → 点击即可打开查看

---

需要我为这个项目打包 zip 或上传 GitHub 吗？或者希望扩展支持上传多个文件？欢迎继续提需求！

当然可以，**用 Docker 在 Windows 云服务器上部署一个支持上传 Word 图片并提供公网访问链接的服务**是完全可行的，而且非常干净、便于管理。你可以用 **Flask + Docker** 构建这个服务。

---

## ✅ 项目目标

你最终可以通过这样的方式工作：

1. 向 Docker 服务上传 `.docx` 文件（POST）
2. 服务提取图片并保存到容器内静态目录 `/app/static/images/`
3. 自动返回公网链接：

   ```
   http://your-server-ip:8000/static/images/xxx.png
   ```

---

## ✅ 一次性完整方案（Flask + Docker）

### 📁 项目目录结构如下：

```
word_image_server/
├── app.py
├── requirements.txt
├── Dockerfile
├── static/
│   └── images/
```

---

### 📄 1. `requirements.txt`

```txt
flask
python-docx
pillow
```

---

### 🧾 2. `app.py`

```python
from flask import Flask, request, jsonify, send_from_directory
from docx import Document
import os, uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'static/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return 'Word 图片提取服务已启动'

@app.route('/upload', methods=['POST'])
def upload_word():
    if 'file' not in request.files:
        return jsonify({'error': '未提供文件'}), 400

    file = request.files['file']
    if not file.filename.endswith('.docx'):
        return jsonify({'error': '仅支持 .docx'}), 400

    # 读取 Word 文档
    doc = Document(file)
    rels = doc.part._rels
    urls = []

    for rel in rels.values():
        if "image" in rel.target_ref:
            img_blob = rel.target_part.blob
            filename = f"{uuid.uuid4()}.png"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(save_path, 'wb') as f:
                f.write(img_blob)
            url = request.host_url + 'static/images/' + filename
            urls.append(url)

    return jsonify({'image_urls': urls})

@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

---

### 🐳 3. `Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python", "app.py"]
```

---

## ✅ 构建并运行 Docker 容器

1. 在你服务器上安装 Docker（如果还没装）
   👉 官方教程：[https://docs.docker.com/desktop/install/windows/](https://docs.docker.com/desktop/install/windows/)

2. 构建镜像：

```bash
cd word_image_server
docker build -t word-image-server .
```

3. 运行容器（映射 8000 端口）：

```bash
docker run -d -p 8000:8000 --name word-img word-image-server
```

4. 测试访问：

* 上传接口（POST `/upload`）；
* 图片访问路径：

```
http://your-server-ip:8000/static/images/xxx.png
```

---

## 🌍 让公网能访问（重要）

* **公网访问的前提**：

  * 云服务器要开放 TCP 8000 端口
  * 安全组允许外部访问 8000
  * 或将端口映射为 80（生产环境）

例如：

```bash
docker run -d -p 80:8000 word-image-server
```

---

## ✅ 测试上传（Postman 或 cURL）

```bash
curl -X POST -F "file=@your.docx" http://your-server-ip:8000/upload
```

---

## 🧠 补充建议

* 如果你后续希望上传图片到云存储（如 OSS/S3）而非容器内部，也可以替换保存逻辑；
* 可以再添加前端网页上传 UI；
* 若容器重启图片会丢失，可挂载主机卷：

```bash
docker run -d -p 8000:8000 -v /your/data/path:/app/static/images word-image-server
```

---

是否需要我为你打包：

* 🔧 Windows 下可直接运行的 Docker Compose？
* 🧰 Flask+HTML 简单上传页面？

只需告诉我，我可以完整给你生成。
