# Dockerfile untuk Glucoin API (Detection + Chatbot)
FROM python:3.10-slim

WORKDIR /app

# Copy requirements first (untuk cache layer)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY main.py .
COPY api_detection.py .
COPY api_chatbot.py .
COPY diabetes_chatbot/ ./diabetes_chatbot/

# Create models directory (model will be mounted/downloaded later)
RUN mkdir -p models

# Expose port
EXPOSE 8000

# Run combined API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
