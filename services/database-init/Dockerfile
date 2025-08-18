FROM python:3.10-slim
WORKDIR /app
COPY services/database-init/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ ./database/
COPY services/database-init/ .
CMD ["python", "main.py"] 