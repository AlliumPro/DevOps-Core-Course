# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Install dependencies first (layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the app code
COPY app.py ./

# Switch to non-root user
USER app

EXPOSE 5000

CMD ["python", "app.py"]
