Kafka Topic-Driven Kubernetes Auto-Scaler with OpenTelemetry
============================================================

This project provides a Kubernetes auto-scaler that dynamically adjusts the number of pods in a deployment based on the message count in a Kafka topic. It integrates with OpenTelemetry for tracing, metrics, and logging, ensuring you can monitor the auto-scaling behavior effectively.

Components
----------

### 1\. Python Script (`scale_k8s.py`)

The core of this project is the `scale_k8s.py` script. It:

*   Connects to a Kafka topic to get the message count.
*   Dynamically adjusts the number of pods in a Kubernetes deployment based on the message count.
*   Logs a warning if the message count exceeds a specified threshold.
*   Calculates and logs the message throughput per minute.
*   Integrates with OpenTelemetry for tracing, metrics, and logging.
*   Exposes a health check endpoint for monitoring.

Key features:

*   **Scaling logic**: Scales up/down the number of pods based on the number of messages in the Kafka topic.
*   **Warning system**: Logs a warning if the message count exceeds a specified threshold and provides the recommended number of pods.
*   **Throughput calculation**: Calculates and logs the message throughput per minute in the Kafka topic.
*   **OpenTelemetry integration**: Provides tracing for key operations, metrics for Kafka message count and pod count, and structured logging.
*   **Health check server**: Allows external tools to monitor the health of the auto-scaler.

### 2\. Dockerfile

The `Dockerfile` builds a Docker image that runs the `scale_k8s.py` script. It uses the Alpine base image to keep the image size small and installs necessary dependencies for Kafka, Kubernetes, and OpenTelemetry.

### 3\. Kubernetes Manifest (`manifest.yaml`)

The `manifest.yaml` file combines the necessary Kubernetes resources to deploy the auto-scaler:

*   **ServiceAccount**: Allows the pod to manage the deployment.
*   **Role**: Grants permissions to get, list, watch, and update deployments.
*   **RoleBinding**: Binds the ServiceAccount to the Role.
*   **Deployment**: Deploys the auto-scaler pod.
*   **Service**: Exposes the health check endpoint.

Getting Started
---------------

### Prerequisites

*   Docker
*   Kubernetes cluster
*   Kafka cluster
*   OpenTelemetry Collector

### Step-by-Step Guide

1.  **Build the Docker image**

    bash

    Copy code

    `docker build -t your-username/k8s-scaler .`

2.  **Push the Docker image to a container registry**

    bash

    Copy code

    `docker push your-username/k8s-scaler`

3.  **Apply the Kubernetes Manifest**

    bash

    Copy code

    `kubectl apply -f manifest.yaml`

4.  **Verify the Deployment**

    Check the status of the deployment:

    bash

    Copy code

    `kubectl get deployments kubectl get pods`

5.  **Monitor the Health Check**

    The health check endpoint is exposed on port `8000`. You can use tools like `curl` or integrate with monitoring systems to check the health:

    bash

    Copy code

    `curl http://<pod-ip>:8000`


Environment Variables
---------------------

The script uses the following environment variables for configuration:

*   `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: `localhost:9092`).
*   `KAFKA_TOPIC`: Kafka topic to monitor (default: `my_topic`).
*   `NAMESPACE`: Kubernetes namespace of the deployment (default: `default`).
*   `DEPLOYMENT_NAME`: Name of the Kubernetes deployment to scale (default: `my-deployment`).
*   `MESSAGES_PER_POD`: Number of messages per pod (default: `10`).
*   `MIN_REPLICAS`: Minimum number of pods (default: `1`).
*   `MAX_REPLICAS`: Maximum number of pods (default: `10`).
*   `HEALTH_CHECK_PORT`: Port for the health check server (default: `8000`).
*   `MIN_TTL_SECONDS`: Minimum time-to-live in seconds before scaling down below `MIN_REPLICAS` (default: `300`).
*   `SCALE_INTERVAL_SECONDS`: Interval in seconds between scaling operations (default: `60`).
*   `MESSAGE_COUNT_THRESHOLD`: Threshold for warning about message count (default: `1000`).

OpenTelemetry Integration
-------------------------

The auto-scaler integrates with OpenTelemetry to provide detailed tracing, metrics, and logging. Make sure you have an OpenTelemetry Collector running and configured to receive data from the auto-scaler.

### Key Metrics

*   `kafka_message_count`: The current number of messages in the Kafka topic.
*   `k8s_pod_count`: The current number of pods in the deployment.
*   `kafka_message_throughput`: Message throughput per minute in the Kafka topic.

### Key Traces

*   `check_kafka_health`
*   `check_kubernetes_health`
*   `get_topic_length`
*   `scale_deployment`

### Logging

All logs are structured and exported using OpenTelemetry, providing a more centralized and manageable way to handle logs.

Contributing
------------

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

License
-------

This project is licensed under the MIT License. See the LICENSE file for details.

* * *

This README now includes information about the message throughput calculation and other updates to the script. If you need any further adjustments, feel free to let me know!