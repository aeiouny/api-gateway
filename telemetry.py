from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry import trace

def setup_telemetry(app):
    
    

    resource = Resource.create({
        "service.name": "API-Gateway-Project",
        "service.version": "1.0.0",
        "environment": "local-minikube"
    })

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    span_processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(span_processor)

    FastAPIInstrumentor.instrument_app(app)
    
    print("INFO: OpenTelemetry Tracing Initialized.")