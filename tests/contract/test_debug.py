"""Debug test to see what routes are registered."""


def test_list_routes(app):
  """List all registered routes."""
  routes = []
  for route in app.routes:
    if hasattr(route, 'path'):
      routes.append(route.path)
  print('\nRegistered routes:')
  for route in sorted(routes):
    print(f'  {route}')

  # This test always passes, it's just for debugging
  assert True
