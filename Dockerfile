FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY run.py .

# Expose port (Zeabur will set PORT env var)
ENV PORT=8000

# Run the application
CMD ["python", "run.py"]