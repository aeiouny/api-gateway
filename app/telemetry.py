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

def get_formatted_metrics():
    """Returns formatted, human-readable metrics"""
    global metrics_reader
    
    if metrics_reader is None:
        return "Metrics not ready\n"
    
    try:
        from prometheus_client import generate_latest, REGISTRY
        raw_metrics = generate_latest(REGISTRY).decode('utf-8')
        
        lines = raw_metrics.split('\n')
        output = []
        output.append("API GATEWAY METRICS")
        output.append("=" * 60)
        output.append("")
        
        # Collect endpoint data
        endpoint_data = {}
        for line in lines:
            if 'http_server_duration_milliseconds_count{' in line and 'http_target=' in line:
                # Extract endpoint and status code
                if 'http_target="' in line and 'http_status_code=' in line:
                    target_start = line.find('http_target="') + 13
                    target_end = line.find('"', target_start)
                    endpoint = line[target_start:target_end]
                    
                    status_start = line.find('http_status_code="') + 18
                    status_end = line.find('"', status_start)
                    status_code = line[status_start:status_end]
                    
                    count = float(line.split('} ')[-1].strip())
                    
                    key = f"{endpoint}|{status_code}"
                    if key not in endpoint_data:
                        endpoint_data[key] = {'endpoint': endpoint, 'status': status_code, 'count': 0, 'sum': 0}
                    endpoint_data[key]['count'] += count
            
            if 'http_server_duration_milliseconds_sum{' in line and 'http_target=' in line:
                if 'http_target="' in line and 'http_status_code=' in line:
                    target_start = line.find('http_target="') + 13
                    target_end = line.find('"', target_start)
                    endpoint = line[target_start:target_end]
                    
                    status_start = line.find('http_status_code="') + 18
                    status_end = line.find('"', status_start)
                    status_code = line[status_start:status_end]
                    
                    sum_val = float(line.split('} ')[-1].strip())
                    
                    key = f"{endpoint}|{status_code}"
                    if key in endpoint_data:
                        endpoint_data[key]['sum'] += sum_val
        
        # Display endpoint metrics
        if endpoint_data:
            output.append("ENDPOINT METRICS")
            output.append("-" * 60)
            output.append(f"{'Endpoint':<25} {'Status':<10} {'Requests':<10} {'Avg Time':<12}")
            output.append("-" * 60)
            
            # Group by endpoint
            endpoint_summary = {}
            for key, data in endpoint_data.items():
                endpoint = data['endpoint']
                if endpoint not in endpoint_summary:
                    endpoint_summary[endpoint] = {'total_requests': 0, 'total_time': 0, 'status_codes': {}}
                
                endpoint_summary[endpoint]['total_requests'] += int(data['count'])
                endpoint_summary[endpoint]['total_time'] += data['sum']
                endpoint_summary[endpoint]['status_codes'][data['status']] = int(data['count'])
            
            for endpoint, summary in sorted(endpoint_summary.items()):
                avg_time = (summary['total_time'] / summary['total_requests']) if summary['total_requests'] > 0 else 0
                # Show status codes: "200" or "200,429" if multiple
                status_codes = sorted(summary['status_codes'].keys())
                status_str = ','.join(status_codes) if len(status_codes) <= 2 else f"{len(status_codes)} codes"
                
                output.append(f"{endpoint:<25} {status_str:<10} {summary['total_requests']:<10} {avg_time:.2f} ms")
        else:
            output.append("No requests yet")
        
        output.append("")
        
        # Detailed breakdown by endpoint and status code
        if endpoint_data:
            output.append("DETAILED BREAKDOWN")
            output.append("-" * 60)
            output.append(f"{'Endpoint':<25} {'Status':<10} {'Count':<10} {'Avg Time':<12}")
            output.append("-" * 60)
            
            # Group by endpoint first, then status
            detailed_list = []
            for key, data in endpoint_data.items():
                if data['count'] > 0:
                    avg_time = (data['sum'] / data['count']) if data['count'] > 0 else 0
                    detailed_list.append({
                        'endpoint': data['endpoint'],
                        'status': data['status'],
                        'count': int(data['count']),
                        'avg_time': avg_time
                    })
            
            # Sort by endpoint, then status
            detailed_list.sort(key=lambda x: (x['endpoint'], x['status']))
            
            for item in detailed_list:
                output.append(f"{item['endpoint']:<25} {item['status']:<10} {item['count']:<10} {item['avg_time']:.2f} ms")
        
        output.append("")
        
        # System Health
        output.append("SYSTEM HEALTH")
        output.append("-" * 60)
        memory = None
        cpu = None
        for line in lines:
            if line.startswith('process_resident_memory_bytes '):
                memory_bytes = float(line.split()[-1])
                memory_mb = memory_bytes / 1024 / 1024
                memory = f"{memory_mb:.1f} MB"
            elif line.startswith('process_cpu_seconds_total '):
                cpu_seconds = float(line.split()[-1])
                cpu = f"{cpu_seconds:.2f}"
        
        if memory:
            output.append(f"Memory: {memory}")
        if cpu:
            output.append(f"CPU:    {cpu} seconds")
        output.append("")
        
        # Active Requests
        active = 0
        for line in lines:
            if line.startswith('http_server_active_requests{') and not line.startswith('#'):
                try:
                    active += float(line.split('} ')[-1])
                except:
                    pass
        
        output.append(f"Active Requests: {int(active)}")
        output.append("")
        output.append("=" * 60)
        
        return '\n'.join(output)
    except Exception as e:
        return f"Error formatting metrics: {e}\n"
