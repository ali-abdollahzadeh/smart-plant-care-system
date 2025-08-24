FROM python:3.10-slim
WORKDIR /app

COPY database/requirements.txt ./database-requirements.txt
COPY services/user-service/requirements.txt .

RUN pip install --no-cache-dir -r database-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Copy the shared database package and service code
COPY database/ ./database/
COPY services/user-service/ .

EXPOSE 5500
CMD ["python", "main.py"]