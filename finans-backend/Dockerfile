# 1. Hafif ve güvenli bir Python imajı seçiyoruz
FROM python:3.11-slim

# 2. Konteyner içinde çalışma dizini oluşturuyoruz
WORKDIR /code

# 3. Önce bağımlılıkları kopyalayıp yüklüyoruz (Docker derleme hızını artırmak için)
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 4. app klasörümüzün tamamını konteyner içine aktarıyoruz
COPY ./app /code/app

# 5. Uygulamayı dış dünyaya açacak şekilde uvicorn ile başlatıyoruz
# K8s ağında çalışabilmesi için host adresinin '0.0.0.0' olması şarttır
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
