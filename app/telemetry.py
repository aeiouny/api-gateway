"""
TELEMETRY BASICS - What is this code doing?

WHAT IS TELEMETRY?
------------------
Telemetry = collecting data about how your application is running. Think of it like a car's dashboard:
  - Speedometer (how fast are requests?)
  - Fuel gauge (how much memory/CPU are we using?)
  - Warning lights (are there errors?)
  - Trip odometer (how many requests have we handled?)

Without telemetry, you're running blind - you don't know if your API is slow, broken, or overloaded.

WHAT IS OPENTELEMETRY?
-----------------------
OpenTelemetry is a standard way to collect telemetry data. It's like a universal adapter that lets you:
  - Collect data from your application (tracing, metrics)
  - Send it to monitoring tools (Prometheus, Grafana, etc.)
  - Use the same code regardless of which tool you choose

It's "open" because it's a standard that many companies use, so you're not locked into one vendor.

WHAT IS TRACING?
----------------
Tracing tracks a single request as it flows through your system. Think of it like a package tracking number:
  - Request arrives at API Gateway → trace starts
  - Request forwarded to User Service → trace continues
  - User Service queries database → trace continues
  - Response sent back → trace ends

Each step is called a "span". Together, all spans form a "trace" showing the complete journey.
This helps you find bottlenecks: "Oh, the database query takes 2 seconds!"

WHAT ARE METRICS?
-----------------
Metrics are numbers that tell you about your system's health and performance:
  - Request count: How many requests per second?
  - Response time: How long does each request take?
  - Error rate: What percentage of requests fail?
  - Memory usage: How much RAM is the app using?
  - CPU usage: How much processing power is being used?

Metrics are like a health checkup - they give you a snapshot of your system's condition.

HOW DOES IT WORK? (The Complete Flow)
--------------------------------------
1. SETUP (setup_telemetry function):
   - Create a TracerProvider: This is the "recorder" for traces
   - Create a MeterProvider: This is the "recorder" for metrics
   - Add exporters: Where to send the data (console, Prometheus, etc.)
   - Instrument FastAPI: Automatically track all HTTP requests

2. AUTOMATIC TRACKING:
   - When a request comes in, OpenTelemetry automatically:
     * Starts a trace (records the request)
     * Records metrics (counts requests, measures response time)
     * Tracks errors (if something goes wrong)

3. METRICS EXPORT:
   - Metrics are collected in Prometheus format (industry standard)
   - Prometheus is a monitoring tool that scrapes metrics from endpoints
   - Our /metrics endpoint exposes raw Prometheus format metrics for Prometheus to collect
   - The /metrics endpoint always returns raw Prometheus format (no formatting/parsing)

WHAT IS PROMETHEUS?
-------------------
Prometheus is a popular monitoring tool that:
  - Scrapes metrics from your application (pulls data from /metrics endpoint)
  - Stores them in a time-series database
  - Lets you create dashboards and alerts
  - Can send alerts when something goes wrong (e.g., "Error rate > 5%")

Think of it like a security camera system that records everything and lets you review footage.

WHAT IS A SPAN?
---------------
A span is one unit of work in a trace. For example:
  - Span 1: "Received HTTP request GET /users"
  - Span 2: "Forwarded request to User Service"
  - Span 3: "User Service processed request"
  - Span 4: "Sent response back to client"

Each span has:
  - Start time and end time (how long it took)
  - Name (what operation it was)
  - Status (success or error)
  - Attributes (extra info like URL, status code, etc.)

WHY DO WE NEED THIS?
--------------------
1. DEBUGGING: When something breaks, traces show you exactly where it failed
2. PERFORMANCE: Find slow endpoints and optimize them
3. MONITORING: Know if your API is healthy or struggling
4. ALERTING: Get notified when errors spike or response times increase
5. CAPACITY PLANNING: See if you need more servers based on request volume

EXAMPLE SCENARIO:
----------------
Without telemetry:
  - User: "The API is slow!"
  - You: "Which endpoint? How slow? When did it happen?" 🤷

With telemetry:
  - You: "I can see /api/payments/create is taking 3 seconds on average"
  - You: "The database query inside it takes 2.5 seconds"
  - You: "Let me optimize that query" ✅

WHAT DATA DO WE COLLECT?
------------------------
- HTTP requests: URL, method, status code, response time
- System resources: Memory usage, CPU usage
- Request counts: How many requests per endpoint
- Error rates: How many requests fail
- Active requests: How many requests are currently being processed
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import Resource

# ============================================================================
# GLOBAL STATE
# ============================================================================
# Store the metrics reader globally so we can access it from /metrics endpoint
# ============================================================================

metrics_reader = None

# ============================================================================
# TELEMETRY SETUP FUNCTION
# ============================================================================
# This function configures OpenTelemetry to automatically collect metrics
# It's called once when the FastAPI app starts
# ============================================================================

def setup_telemetry(app):
    """
    Initialize OpenTelemetry for the FastAPI application.
    
    This function:
    1. Sets up tracing (tracks request flow through the system)
    2. Sets up metrics (counts requests, measures response times)
    3. Instruments FastAPI to automatically collect data from all HTTP requests
    
    After this runs, every HTTP request is automatically tracked without
    needing to add code to each endpoint.
    """
    global metrics_reader
    
    # Create service metadata (identifies this service in telemetry data)
    # This helps when you have multiple services - you can filter by service name
    service_info = Resource.create({
        "service.name": "api-gateway",  # Name of this service
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),  # Version for tracking
        "deployment.environment": os.getenv("ENVIRONMENT", "development")  # dev/staging/prod
    })

    # ========================================================================
    # TRACING SETUP
    # ========================================================================
    # Tracing tracks individual requests as they flow through the system
    # Each request gets a "trace" with multiple "spans" (steps in the request)
    
    # Create tracer provider - this is the "recorder" for traces
    tracer = TracerProvider(resource=service_info)
    # Set it as the global tracer provider (OpenTelemetry uses this)
    trace.set_tracer_provider(tracer)

    # Console exporter - outputs traces to console (for development/debugging)
    # In production, you'd use an exporter that sends to a tracing backend
    console_exporter = ConsoleSpanExporter()
    # Batch processor - collects spans and exports them in batches (more efficient)
    processor = BatchSpanProcessor(console_exporter)
    # Add processor to tracer (now traces will be exported to console)
    tracer.add_span_processor(processor)

    # ========================================================================
    # METRICS SETUP
    # ========================================================================
    # Metrics are numbers about system performance (request count, duration, etc.)
    
    # PrometheusMetricReader - collects metrics in Prometheus format
    # Prometheus is a popular monitoring tool that scrapes metrics from /metrics endpoint
    metrics_reader = PrometheusMetricReader()
    
    # Create meter provider - this is the "recorder" for metrics
    # It uses the PrometheusMetricReader to store metrics
    meter = MeterProvider(resource=service_info, metric_readers=[metrics_reader])
    # Set it as the global meter provider
    set_meter_provider(meter)

    # ========================================================================
    # FASTAPI INSTRUMENTATION
    # ========================================================================
    # This automatically instruments FastAPI to collect telemetry from all requests
    # After this, every HTTP request automatically:
    # - Creates a trace span
    # - Records metrics (duration, status code, etc.)
    # - No manual code needed in endpoints!
    FastAPIInstrumentor.instrument_app(app)
    print("OpenTelemetry initialized")

# ============================================================================
# METRICS EXPORT FUNCTION
# ============================================================================
# This function is called by the /metrics endpoint to get Prometheus metrics
# ============================================================================

def get_metrics():
    """
    Returns raw Prometheus format metrics for the /metrics endpoint.
    
    Prometheus format is a text-based format that looks like:
    # HELP http_server_duration_milliseconds HTTP server request duration
    # TYPE http_server_duration_milliseconds histogram
    http_server_duration_milliseconds_bucket{...} 1.0
    
    Prometheus scrapes this endpoint periodically to collect metrics.
    """
    global metrics_reader
    
    # If telemetry hasn't been initialized yet, return error message
    if metrics_reader is None:
        return "# Metrics not ready\n"
    
    try:
        # prometheus_client is the library that formats metrics for Prometheus
        # REGISTRY contains all the metrics collected by OpenTelemetry
        from prometheus_client import generate_latest, REGISTRY
        
        # Generate Prometheus-formatted text from all metrics in the registry
        result = generate_latest(REGISTRY)
        # Decode bytes to string (Prometheus expects text/plain)
        return result.decode('utf-8')
    except Exception as e:
        # If something goes wrong, return error in Prometheus comment format
        return f"# Error: {e}\n"
