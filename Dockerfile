# Dockerfile untuk Glucoin API (Detection + Chatbot)
FROM python:3.10-slim

WORKDIR /app

# Copy requirements first (untuk cache layer)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY api_detection.py .
COPY api_chatbot.py .
COPY diabetes_chatbot/ ./diabetes_chatbot/

# Create models directory (model will be mounted/downloaded later)
RUN mkdir -p models

# Expose ports
EXPOSE 8001 8002

# Default: run detection API (bisa override di docker-compose)
CMD ["uvicorn", "api_detection:app", "--host", "0.0.0.0", "--port", "8001"]
