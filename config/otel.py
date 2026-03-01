"""
Optional OpenTelemetry setup. Enabled via OTEL_ENABLED=true env var.
Install optional deps: uv sync --extra otel
"""

import os


def setup_otel() -> None:
    if not os.environ.get("OTEL_ENABLED", "false").lower() == "true":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise ImportError(
            "OpenTelemetry packages not installed. Run: uv sync --extra otel"
        ) from exc

    service_name = os.environ.get("OTEL_SERVICE_NAME", "__SERVICE_NAME__")
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
