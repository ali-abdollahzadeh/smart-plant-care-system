# Use official Python image
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the port (matches docker-compose.yml, e.g., 5001)
EXPOSE 5001

# Default command to run the service
CMD ["python", "main.py"]