"""Test script to diagnose Model Serving endpoint input format.

This script helps determine what input format your endpoint expects by:
1. Getting endpoint details
2. Testing different input formats
3. Showing detailed error messages
"""

import asyncio
import json
from databricks.sdk import WorkspaceClient
import httpx


async def test_endpoint_formats(endpoint_name: str):
    """Test different input formats for a model serving endpoint."""
    
    client = WorkspaceClient()
    
    print(f"\n{'='*80}")
    print(f"Testing endpoint: {endpoint_name}")
    print(f"{'='*80}\n")
    
    # Get endpoint details
    try:
        endpoint = client.serving_endpoints.get(endpoint_name)
        print("✓ Endpoint Details:")
        print(f"  Name: {endpoint.name}")
        print(f"  State: {endpoint.state.config_update if endpoint.state else 'UNKNOWN'}")
        
        if endpoint.config and endpoint.config.served_models:
            model = endpoint.config.served_models[0]
            print(f"  Model: {model.model_name}")
            print(f"  Version: {model.model_version}")
            print(f"  Workload Size: {model.workload_size}")
        
        # Build endpoint URL
        workspace_url = client.config.host.rstrip('/')
        url = f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations"
        print(f"  URL: {url}")
        
    except Exception as e:
        print(f"✗ Error getting endpoint details: {e}")
        return
    
    # Get authentication token
    token = client.config.authenticate()
    if not token:
        print("✗ Failed to authenticate")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test different input formats
    test_cases = [
        {
            "name": "Foundation Model (Chat) - Direct Format",
            "body": {
                "messages": [{"role": "user", "content": "Say hello in one word"}],
                "max_tokens": 10
            }
        },
        {
            "name": "Foundation Model (Chat) - With Temperature",
            "body": {
                "messages": [{"role": "user", "content": "Say hello in one word"}],
                "max_tokens": 10,
                "temperature": 0.7
            }
        },
        {
            "name": "Traditional ML Model - Inputs Wrapper",
            "body": {
                "inputs": [[1.0, 2.0, 3.0, 4.0]]
            }
        },
        {
            "name": "Traditional ML Model - Dataframe Split",
            "body": {
                "dataframe_split": {
                    "columns": ["feature1", "feature2"],
                    "data": [[1.0, 2.0]]
                }
            }
        },
        {
            "name": "Custom - Input Parameter",
            "body": {
                "input": "Hello, how are you?"
            }
        }
    ]
    
    print(f"\n{'='*80}")
    print("Testing Input Formats")
    print(f"{'='*80}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. {test_case['name']}")
            print(f"   Request Body: {json.dumps(test_case['body'], indent=6)}")
            
            try:
                response = await http_client.post(
                    url,
                    json=test_case['body'],
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"   ✓ SUCCESS (200)")
                    result = response.json()
                    print(f"   Response keys: {list(result.keys())}")
                    print(f"   Response preview: {json.dumps(result, indent=6)[:200]}...")
                    print(f"\n   🎉 THIS FORMAT WORKS! Use this format in your UI.\n")
                    break  # Found working format
                else:
                    print(f"   ✗ FAILED ({response.status_code})")
                    print(f"   Error: {response.text[:200]}")
                    
            except httpx.HTTPStatusError as e:
                print(f"   ✗ FAILED ({e.response.status_code})")
                try:
                    error_detail = e.response.json()
                    print(f"   Error: {json.dumps(error_detail, indent=6)[:300]}")
                except:
                    print(f"   Error: {e.response.text[:200]}")
                    
            except Exception as e:
                print(f"   ✗ ERROR: {str(e)[:200]}")
            
            print()
    
    print(f"{'='*80}")
    print("Test Complete")
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_model_endpoint.py <endpoint_name>")
        print("\nExample:")
        print("  python test_model_endpoint.py databricks-app-template-serving")
        sys.exit(1)
    
    endpoint_name = sys.argv[1]
    asyncio.run(test_endpoint_formats(endpoint_name))


if __name__ == "__main__":
    main()

