FROM python:3.10-slim
WORKDIR /app
COPY database/requirements.txt ./database-requirements.txt
COPY services/catalogue-service/requirements.txt .
RUN pip install --no-cache-dir -r database-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ ./database/
COPY services/catalogue-service/ .
EXPOSE 5000
CMD ["python", "main.py"]
