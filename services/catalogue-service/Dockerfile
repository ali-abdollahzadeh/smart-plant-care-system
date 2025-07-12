FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/data && chown -R nobody:nogroup /app/data
COPY . .
EXPOSE 5000
USER nobody
ENV CATALOGUE_DB_PATH=/app/data/catalogue_data.db
CMD ["python", "main.py"]
