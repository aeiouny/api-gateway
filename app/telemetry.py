import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import Resource

metrics_reader = None

def setup_telemetry(app):
    global metrics_reader
    
    service_info = Resource.create({
        "service.name": "api-gateway",
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })

    tracer = TracerProvider(resource=service_info)
    trace.set_tracer_provider(tracer)

    console_exporter = ConsoleSpanExporter()
    processor = BatchSpanProcessor(console_exporter)
    tracer.add_span_processor(processor)

    metrics_reader = PrometheusMetricReader()
    meter = MeterProvider(resource=service_info, metric_readers=[metrics_reader])
    set_meter_provider(meter)

    FastAPIInstrumentor.instrument_app(app)
    print("OpenTelemetry initialized")

def get_metrics():
    global metrics_reader
    
    if metrics_reader is None:
        return "# Metrics not ready\n"
    
    try:
        from prometheus_client import generate_latest, REGISTRY
        result = generate_latest(REGISTRY)
        return result.decode('utf-8')
    except Exception as e:
        return f"# Error: {e}\n"
