# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .

# Expose port (Zeabur will set PORT env var)
ENV PORT=8000

# Run the MCP server
CMD uvicorn server:mcp.app --host 0.0.0.0 --port ${PORT}