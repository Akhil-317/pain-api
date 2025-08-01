FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# ✅ Clean pip cache & force aiohttp from PyPI
RUN pip install --upgrade pip \
    && pip cache purge \
    && pip install --no-cache-dir aiohttp==3.9.0 \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "pain001_API:app", "--host", "0.0.0.0", "--port", "8000"]
