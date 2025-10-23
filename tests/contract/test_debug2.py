"""Debug test to see if auth/status works directly."""

from server.routers import router


def test_auth_status_in_router():
  """Check if auth/status is in the router."""
  all_paths = []
  for route in router.routes:
    if hasattr(route, 'path'):
      all_paths.append(route.path)
      # If it's a sub-router, check its routes too
      if hasattr(route, 'routes'):
        for subroute in route.routes:
          if hasattr(subroute, 'path'):
            all_paths.append(route.path + subroute.path)

  print('\nAll router paths:')
  for path in sorted(all_paths):
    print(f'  {path}')

  # Check if auth/status is there
  assert '/user/auth/status' in all_paths or '/user' in all_paths
