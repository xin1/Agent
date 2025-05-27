# Stage 2: 构建你的 Python 应用
FROM python:3.9-slim

# 设定工作目录
WORKDIR /app

# 替换 APT 源
RUN echo 'deb https://mirrors.公司源 bookworm main contrib non-free'> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y libreoffice --fix-missing && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


COPY . .
RUN pip install comtypes aiofiles python-docx pypandoc jinja2 PyPDF2 pdf2image pdfplumber fastapi uvicorn pymupdf python-multipart --trusted-host /mirrors.公司.com -i https://mirrors.公司.com/pypi/simple


# 启动服务
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
