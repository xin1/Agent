# PDF剪裁和结构提取工具部署总结

## 项目目标

建立一套支持 PDF 页眉页尾剪裁和标题结构提取功能的工具，支持:

- gradio网页前端，可多人访问（不稳定，3-5s就断开）❌  
- 本地 .exe 框架（太麻烦，如果其他人使用还需要安装）❌  
- FastAPI + Flask 后端（未成功）❌  
- Docker 完整托管部署✅  

---

## 开发流程

### 1. 主功能实现
- 删除 PDF 的页眉页尾 (fitz 剪裁)
- 分析 1/1.1/1.1.1 类型标题，提取标题+内容到 CSV
- CSV 格式：["标题", "内容"]

### 2. FastAPI 后端
- `/process/` 接口处理上传PDF
- `/download/` 接口提供文件下载

### 3. Flask 静态网页
- 给用户的前端界面，支持 PDF 上传，输入剪裁值，下载结果

---

## Docker 部署

### 目录结构
```
pdf_tool/
├── app.py                  # FastAPI 应用主程序
├── pdf_processor.py        # PDF 剪裁+结构提取逻辑
├── templates/
│   └── index.html          # 静态网页（上传文件和下载结果）
├── static/                 # 静态资源（可留空）
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建配置
└── output/                 # 生成文件保存目录（Docker 会挂载）
```

### Dockerfile 示例
```dockerfile
FROM python:3.10
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install pdfplumber jinja2 fastapi uvicorn python-multipart fitz PyMuPDF --trust...(公司源）

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt 示例
```
fastapi
uvicorn
python-multipart
jinja2
pdfplumber
PyMuPDF
```

### Docker 构建
```bash
# 构建镜像
docker build -t pdf-tool-app .

# 启动容器（指定端口映射）
docker run -d -p 8090:8000 --name pdf_tool_app_v9 pdf-tool-app
```

---

## 网页访问

- 如果是公司内网，使用服务器的 **IPv4 地址**
- 如果是公网服务器，访问地址为:

```
http://<公网IP>:8090
```

---

## 应对问题

- 「localhost 断开」：因公司 HTTP/HTTPS 代理阻止
- 「Gradio 断开」：同上，建议用 Docker 部署
- 「经常停止」：缺失 app 路径、缺失 asgi 调用或 Dockerfile 错误

---

## 经典命令

```bash
# 查看云服务器 IP
curl ifconfig.me

# 启动 docker 容器
docker run -d -p 8090:8000 --name pdf_tool_app_v9 pdf-tool-app

# 查看容器日志
docker logs pdf_tool_api
```

---

## 完成故事

> 从 Windows 本地运行 PDF 脚本开始，连续解决了代理断连、gradio 问题、.exe 化异常，最终选择 Docker + FastAPI + Flask 简单结合，完成了可多人访问、安全稳定、自动化的公司管理系统。

