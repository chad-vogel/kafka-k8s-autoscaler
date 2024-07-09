# Use the official Python Alpine image from the Docker Hub
FROM python:3.9-alpine

# Install necessary dependencies
RUN apk add --no-cache \
    gcc \
    python3-dev \
    libc-dev \
    libffi-dev \
    musl-dev \
    make

# Set environment variables
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ENV KAFKA_TOPIC=my_topic
ENV NAMESPACE=default
ENV DEPLOYMENT_NAME=my-deployment
ENV MESSAGES_PER_POD=10
ENV MIN_REPLICAS=1
ENV MAX_REPLICAS=10
ENV HEALTH_CHECK_PORT=8000
ENV MIN_TTL_SECONDS=300  # Minimum time-to-live in seconds
ENV SCALE_INTERVAL_SECONDS=60  # Interval in seconds between scaling operations
ENV MESSAGE_COUNT_THRESHOLD=1000  # Threshold for warning about message count

# Create app directory
WORKDIR /app

# Copy the script into the container
COPY scale_k8s.py .

# Install Python dependencies
RUN pip install --no-cache-dir confluent-kafka kubernetes opentelemetry-sdk opentelemetry-api opentelemetry-exporter-otlp opentelemetry-instrumentation-logging

# Expose the health check port
EXPOSE 8000

# Command to run the script
CMD ["python", "scale_k8s.py"]