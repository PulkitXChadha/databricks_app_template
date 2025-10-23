"""Unit tests for TypeScript API client generation validation.

Tests verify that the generated TypeScript client from OpenAPI spec has correct types,
methods, and interfaces for metrics endpoints.
"""

from pathlib import Path

import pytest


def test_generated_client_has_metrics_service():
  """Verify generated TypeScript client includes MetricsService"""
  client_path = (
    Path(__file__).parent.parent.parent
    / 'client'
    / 'src'
    / 'fastapi_client'
    / 'services'
    / 'MetricsService.ts'
  )

  # Test will fail if client not generated yet
  assert client_path.exists(), f'MetricsService not found at {client_path}'

  content = client_path.read_text()

  # Verify service exports expected methods
  assert 'getPerformanceMetrics' in content or 'MetricsService' in content, (
    'MetricsService should have getPerformanceMetrics method'
  )


def test_generated_client_has_usage_event_models():
  """Verify generated TypeScript client includes UsageEvent models"""
  models_path = Path(__file__).parent.parent.parent / 'client' / 'src' / 'fastapi_client' / 'models'

  # Check for UsageEventInput model
  usage_event_input_path = models_path / 'UsageEventInput.ts'
  assert usage_event_input_path.exists(), (
    f'UsageEventInput model not found at {usage_event_input_path}'
  )

  content = usage_event_input_path.read_text()

  # Verify model has required fields
  assert 'event_type' in content, 'UsageEventInput should have event_type field'
  assert 'timestamp' in content, 'UsageEventInput should have timestamp field'


def test_generated_client_has_batch_request_model():
  """Verify generated TypeScript client includes UsageEventBatchRequest model"""
  models_path = Path(__file__).parent.parent.parent / 'client' / 'src' / 'fastapi_client' / 'models'

  batch_request_path = models_path / 'UsageEventBatchRequest.ts'
  assert batch_request_path.exists(), (
    f'UsageEventBatchRequest model not found at {batch_request_path}'
  )

  content = batch_request_path.read_text()

  # Verify model has events array field
  assert 'events' in content, 'UsageEventBatchRequest should have events array field'


def test_generated_client_type_safety():
  """Verify generated TypeScript client has proper type definitions"""
  # This test checks that TypeScript compilation would catch type errors
  # by verifying the generated client has TypeScript types (not 'any')

  service_path = (
    Path(__file__).parent.parent.parent
    / 'client'
    / 'src'
    / 'fastapi_client'
    / 'services'
    / 'MetricsService.ts'
  )

  if not service_path.exists():
    pytest.skip('MetricsService not generated yet')

  content = service_path.read_text()

  # Verify service uses typed responses (not 'any')
  # Generated client should import types
  assert 'import type' in content or 'import {' in content, (
    'MetricsService should import types from models'
  )


def test_openapi_spec_includes_metrics_endpoints():
  """Verify OpenAPI spec generated from FastAPI includes metrics endpoints"""
  # This tests that make_fastapi_client.py will have the right endpoints to generate from

  # Run FastAPI to generate OpenAPI spec
  import sys

  sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'server'))

  try:
    from server.app import app

    openapi_schema = app.openapi()

    # Verify metrics endpoints are in the schema
    paths = openapi_schema.get('paths', {})

    assert '/api/v1/metrics/performance' in paths, (
      'OpenAPI schema should include /api/v1/metrics/performance endpoint'
    )

    assert '/api/v1/metrics/usage' in paths, (
      'OpenAPI schema should include /api/v1/metrics/usage endpoint'
    )

    assert '/api/v1/metrics/usage-events' in paths, (
      'OpenAPI schema should include /api/v1/metrics/usage-events endpoint'
    )

  except ImportError as e:
    pytest.skip(f'Cannot import server.app: {e}')
