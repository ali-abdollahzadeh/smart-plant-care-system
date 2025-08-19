FROM python:3.10-slim
WORKDIR /app

# Install shared database deps and service deps
COPY database/requirements.txt ./database-requirements.txt
COPY services/analytics-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r database-requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

# Copy shared database package and service code
COPY database/ ./database/
COPY services/analytics-service/ .

EXPOSE 5000
CMD ["python", "main.py"]
