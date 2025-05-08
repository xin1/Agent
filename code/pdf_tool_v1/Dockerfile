FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install jinja2 PyPDF2 pdf2image pdfplumber fastapi uvicorn pymupdf python--multipart --trusted-host /mirrors.xfusion.com -i https://mirrors.xfusion.com/pypi/simple

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]