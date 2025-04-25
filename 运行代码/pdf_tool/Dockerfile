FROM python:3.10
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install pdfplumber jinja2 fastapi uvicorn python-multipart fitz PyMuPDF --trust...(公司源）

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
