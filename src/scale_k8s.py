import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from confluent_kafka import Consumer, KafkaException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk._logs import LogEmitterProvider, set_log_emitter_provider
from opentelemetry.sdk._logs.export import BatchLogProcessor
from opentelemetry.exporter.otlp.proto.grpc._logs_exporter import OTLPLogExporter
import logging
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Initialize OpenTelemetry Tracer
trace.set_tracer_provider(TracerProvider(resource=Resource.create({SERVICE_NAME: "kafka-scaler"})))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(OTLPSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)

# Initialize OpenTelemetry Meter
metrics.set_meter_provider(MeterProvider(resource=Resource.create({SERVICE_NAME: "kafka-scaler"})))
meter = metrics.get_meter(__name__)
exporter = OTLPMetricExporter()
meter_provider = metrics.get_meter_provider()
meter_provider.start_pipeline(meter, exporter, 5)

# Initialize OpenTelemetry Logger
log_emitter_provider = LogEmitterProvider(resource=Resource.create({SERVICE_NAME: "kafka-scaler"})))
set_log_emitter_provider(log_emitter_provider)
log_emitter = log_emitter_provider.get_log_emitter(__name__)
log_processor = BatchLogProcessor(OTLPLogExporter())
log_emitter_provider.add_log_processor(log_processor)

# Instrument standard logging library
LoggingInstrumentor().instrument(set_logging_format=True)
logger = logging.getLogger(__name__)

# Environment variables for Kafka and Kubernetes
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'my_topic')
NAMESPACE = os.getenv('NAMESPACE', 'default')
DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME', 'my-deployment')
MESSAGES_PER_POD = int(os.getenv('MESSAGES_PER_POD', 10))  # Number of messages per pod
MIN_REPLICAS = int(os.getenv('MIN_REPLICAS', 1))  # Minimum number of pods
MAX_REPLICAS = int(os.getenv('MAX_REPLICAS', 10))  # Maximum number of pods
HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', 8000))  # Port for health check server
MIN_TTL_SECONDS = int(os.getenv('MIN_TTL_SECONDS', 300))  # Minimum time-to-live in seconds before scaling down below MIN_REPLICAS
SCALE_INTERVAL_SECONDS = int(os.getenv('SCALE_INTERVAL_SECONDS', 60))  # Interval in seconds between scaling operations
MESSAGE_COUNT_THRESHOLD = int(os.getenv('MESSAGE_COUNT_THRESHOLD', 1000))  # Threshold for warning about message count

# Health status
kafka_health = False
kubernetes_health = False
last_scale_down_time = time.time()
last_message_count = 0
last_check_time = time.time()

# Create OpenTelemetry metrics
message_count_metric = meter.create_observable_gauge(
name="kafka_message_count",
description="The current number of messages in the Kafka topic",
unit="1",
callback=lambda result: result.observe(get_topic_length(), {}))

pod_count_metric = meter.create_observable_gauge(
name="k8s_pod_count",
description="The current number of pods in the deployment",
unit="1",
callback=lambda result: result.observe(get_current_pod_count(), {}))

throughput_metric = meter.create_observable_gauge(
name="kafka_message_throughput",
description="Message throughput per minute in the Kafka topic",
unit="1",
callback=lambda result: result.observe(calculate_throughput(), {}))

# Function to get the current number of pods in the deployment
def get_current_pod_count():
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
    return deployment.status.replicas

# Function to check Kafka health
def check_kafka_health():
    global kafka_health
    with tracer.start_as_current_span("check_kafka_health"):
        try:
            consumer = Consumer({
                'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                'group.id': 'healthcheck_group',
                'auto.offset.reset': 'earliest'
            })
            metadata = consumer.list_topics(timeout=10)
            consumer.close()
            kafka_health = True
            logger.info("Kafka health check succeeded.")
        except KafkaException as e:
            logger.error(f"Kafka health check failed: {e}")
            kafka_health = False

# Function to check Kubernetes health
def check_kubernetes_health():
    global kubernetes_health
    with tracer.start_as_current_span("check_kubernetes_health"):
        try:
            config.load_kube_config()
            apps_v1 = client.AppsV1Api()
            apps_v1.list_deployment_for_all_namespaces(timeout_seconds=10)
            kubernetes_health = True
            logger.info("Kubernetes health check succeeded.")
        except ApiException as e:
            logger.error(f"Kubernetes health check failed: {e}")
            kubernetes_health = False

# Function to get the number of messages in the Kafka topic
def get_topic_length():
    with tracer.start_as_current_span("get_topic_length"):
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'monitoring_group',
            'auto.offset.reset': 'earliest'
        })

        metadata = consumer.list_topics(KAFKA_TOPIC)
        topic = metadata.topics[KAFKA_TOPIC]
        partition = topic.partitions[0]  # Assuming single partition
        high = consumer.get_watermark_offsets(partition, timeout=10)[1]

        consumer.close()
        return high

# Function to calculate message throughput per minute
def calculate_throughput():
    global last_message_count, last_check_time
    current_message_count = get_topic_length()
    current_time = time.time()
    elapsed_minutes = (current_time - last_check_time) / 60

    if elapsed_minutes == 0:
        throughput = 0
    else:
        throughput = (current_message_count - last_message_count) / elapsed_minutes

    last_message_count = current_message_count
    last_check_time = current_time

    return throughput

# Function to scale the Kubernetes deployment
def scale_deployment(replicas):
    global last_scale_down_time
    with tracer.start_as_current_span("scale_deployment"):
        config.load_kube_config()
        apps_v1 = client.AppsV1Api()

        try:
            deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
            deployment.spec.replicas = replicas
            apps_v1.replace_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=deployment)
            logger.info(f"Scaled {DEPLOYMENT_NAME} to {replicas} replicas")

            # Update last scale down time if scaling down below MIN_REPLICAS
            if replicas < MIN_REPLICAS:
                last_scale_down_time = time.time()
        except ApiException as e:
            logger.error(f"Exception when scaling deployment: {e}")

# Main function to monitor the queue and scale the deployment
def main():
    check_kafka_health()
    check_kubernetes_health()

    if not kafka_health:
        logger.warning("Kafka is not healthy. Exiting...")
        return

    if not kubernetes_health:
        logger.warning("Kubernetes is not healthy. Exiting...")
        return

    message_count = get_topic_length()
    logger.info(f"Message count: {message_count}")

    if message_count > MESSAGE_COUNT_THRESHOLD:
        recommended_replicas = (message_count // MESSAGES_PER_POD) + 1
        logger.warning(f"Message count {message_count} exceeds threshold. "
                       f"Recommended replicas: {recommended_replicas}")

    desired_replicas = (message_count // MESSAGES_PER_POD) + 1  # Add one to ensure at least one pod is running

    # Ensure within min and max bounds
    if desired_replicas < MIN_REPLICAS:
        # Check if enough time has passed to scale below MIN_REPLICAS
        if time.time() - last_scale_down_time > MIN_TTL_SECONDS:
            desired_replicas = max(0, min(desired_replicas, MAX_REPLICAS))
        else:
            desired_replicas = MIN_REPLICAS
    else:
        desired_replicas = min(desired_replicas, MAX_REPLICAS)

    scale_deployment(desired_replicas)

# HTTP server for health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if kafka_health and kubernetes_health:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"Service Unavailable")

def run_health_check_server():
    server_address = ('', HEALTH_CHECK_PORT)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Starting health check server on port {HEALTH_CHECK_PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Run the health check server in a separate thread
    health_check_thread = threading.Thread(target=run_health_check_server)
    health_check_thread.daemon = True
    health_check_thread.start()

    # Run the main function
    while True:
        main()
        time.sleep(SCALE_INTERVAL_SECONDS)  # Wait between scaling operations
