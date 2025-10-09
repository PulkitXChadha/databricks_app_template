"""Check Model Serving endpoint details to understand input format.

This script retrieves detailed information about a serving endpoint
to help determine the correct input format.
"""

import json
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config


def _create_workspace_client() -> WorkspaceClient:
    """Create WorkspaceClient with explicit OAuth configuration.
    
    This explicitly uses OAuth credentials to avoid conflicts with PAT tokens
    that might be present in the environment.
    
    Returns:
        WorkspaceClient configured with OAuth or default auth
    """
    databricks_host = os.getenv('DATABRICKS_HOST')
    client_id = os.getenv('DATABRICKS_CLIENT_ID')
    client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')
    
    # If OAuth credentials are available, use them explicitly
    if databricks_host and client_id and client_secret:
        cfg = Config(
            host=databricks_host,
            client_id=client_id,
            client_secret=client_secret,
            auth_type="oauth-m2m"  # Explicitly force OAuth to ignore PAT tokens
        )
        return WorkspaceClient(config=cfg)
    
    # Otherwise, let SDK auto-configure (will use single available method)
    return WorkspaceClient()


def check_endpoint(endpoint_name: str):
    """Check endpoint details."""
    
    client = _create_workspace_client()
    
    print(f"\n{'='*80}")
    print(f"Endpoint Details: {endpoint_name}")
    print(f"{'='*80}\n")
    
    try:
        endpoint = client.serving_endpoints.get(endpoint_name)
        
        print(f"Name: {endpoint.name}")
        print(f"ID: {endpoint.id if hasattr(endpoint, 'id') else 'N/A'}")
        print(f"State: {endpoint.state.config_update if endpoint.state else 'UNKNOWN'}")
        print(f"Creator: {endpoint.creator if hasattr(endpoint, 'creator') else 'N/A'}")
        
        if endpoint.config:
            print(f"\n--- Configuration ---")
            print(f"Config object: {endpoint.config}")
            print(f"Config dict keys: {dir(endpoint.config)}")
            
            if endpoint.config.served_models:
                print(f"\nServed Models: {len(endpoint.config.served_models)}")
                
                for i, model in enumerate(endpoint.config.served_models, 1):
                    print(f"\n  Model {i}:")
                    print(f"    Name: {model.name}")
                    print(f"    Model Name (Registry): {model.model_name if hasattr(model, 'model_name') else 'N/A'}")
                    print(f"    Model Version: {model.model_version if hasattr(model, 'model_version') else 'N/A'}")
                    print(f"    Workload Size: {model.workload_size}")
                    print(f"    Workload Type: {model.workload_type if hasattr(model, 'workload_type') else 'N/A'}")
                    print(f"    Scale to Zero: {model.scale_to_zero_enabled}")
                    
                    # Check for external model (foundation models like Claude)
                    if hasattr(model, 'external_model'):
                        print(f"    External Model: YES")
                        ext = model.external_model
                        print(f"      Provider: {ext.provider if hasattr(ext, 'provider') else 'N/A'}")
                        print(f"      Name: {ext.name if hasattr(ext, 'name') else 'N/A'}")
                        print(f"      Task: {ext.task if hasattr(ext, 'task') else 'N/A'}")
                    else:
                        print(f"    External Model: NO (Custom/MLflow model)")
                    
                    # Environment variables (may contain hints about model type)
                    if hasattr(model, 'environment_vars'):
                        print(f"    Environment Variables: {model.environment_vars}")
            
            if endpoint.config.traffic_config:
                print(f"\n--- Traffic Configuration ---")
                for route in endpoint.config.traffic_config.routes:
                    print(f"  Route: {route.served_model_name} → {route.traffic_percentage}%")
        
        # Tags
        if hasattr(endpoint, 'tags') and endpoint.tags:
            print(f"\n--- Tags ---")
            for tag in endpoint.tags:
                print(f"  {tag.key}: {tag.value}")
        
        print(f"\n{'='*80}")
        print("Recommendations:")
        print(f"{'='*80}\n")
        
        # Provide recommendations based on model type
        if endpoint.config and endpoint.config.served_models:
            model = endpoint.config.served_models[0]
            
            if hasattr(model, 'external_model') and model.external_model:
                print("✓ This is an EXTERNAL/FOUNDATION MODEL (e.g., Claude, GPT)")
                print("\n  Recommended Input Format:")
                print('  {')
                print('    "messages": [')
                print('      {"role": "user", "content": "Your question here"}')
                print('    ],')
                print('    "max_tokens": 150,')
                print('    "temperature": 0.7  // optional')
                print('  }')
            else:
                print("✓ This is a CUSTOM/MLFLOW MODEL")
                print("\n  Common Input Formats:")
                print("\n  1. For sklearn/simple models:")
                print('     {"inputs": [[feature1, feature2, ...]]}')
                print("\n  2. For dataframe-based models:")
                print('     {"dataframe_split": {"columns": [...], "data": [[...]]}}')
                print("\n  3. For pandas models:")
                print('     {"dataframe_records": [{"col1": val1, "col2": val2}, ...]}')
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python check_endpoint_details.py <endpoint_name>")
        print("\nExample:")
        print("  python check_endpoint_details.py databricks-app-template-serving")
        sys.exit(1)
    
    endpoint_name = sys.argv[1]
    check_endpoint(endpoint_name)


if __name__ == "__main__":
    main()

