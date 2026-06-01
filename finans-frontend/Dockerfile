FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Streamlit varsayılan olarak 8501 portunda çalışır
EXPOSE 8501

# Streamlit'i dışarıya açık ve başsız (tarayıcıyı otomatik açmaya çalışmayan) modda başlatıyoruz
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
