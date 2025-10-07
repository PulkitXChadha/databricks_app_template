"""Test chat endpoint with correct OpenAI-compatible format.

For Databricks foundation models with task="llm/v1/chat", use OpenAI chat format.
"""

import asyncio
import json
from databricks.sdk import WorkspaceClient
import httpx


async def test_chat_endpoint(endpoint_name: str):
    """Test chat endpoint with OpenAI-compatible format."""
    
    client = WorkspaceClient()
    
    print(f"\n{'='*80}")
    print(f"Testing Chat Endpoint: {endpoint_name}")
    print(f"{'='*80}\n")
    
    # Get endpoint details
    try:
        endpoint = client.serving_endpoints.get(endpoint_name)
        workspace_url = client.config.host.rstrip('/')
        url = f"{workspace_url}/serving-endpoints/{endpoint_name}/invocations"
        print(f"URL: {url}\n")
    except Exception as e:
        print(f"✗ Error getting endpoint: {e}")
        return
    
    # Get authentication headers
    auth_headers = client.config.authenticate()
    if not auth_headers:
        print("✗ Failed to authenticate")
        return
    
    headers = {
        **auth_headers,  # Unpack auth headers (includes Authorization)
        'Content-Type': 'application/json'
    }
    
    print(f"Using Authorization: {list(auth_headers.keys())}")
    print()
    
    # Test case: OpenAI-compatible chat completion format
    # This is the correct format for llm/v1/chat endpoints
    test_body = {
        "messages": [
            {
                "role": "user",
                "content": "Say hello in exactly one word"
            }
        ],
        "max_tokens": 10,
        "temperature": 0.1
    }
    
    print("Request Body:")
    print(json.dumps(test_body, indent=2))
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            print("Sending request...")
            response = await http_client.post(
                url,
                json=test_body,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            print()
            
            if response.status_code == 200:
                print("✓ SUCCESS!")
                result = response.json()
                print("\nResponse:")
                print(json.dumps(result, indent=2))
            else:
                print("✗ FAILED")
                print(f"\nResponse Text:")
                print(response.text[:500])
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_chat_format.py <endpoint_name>")
        print("\nExample:")
        print("  python test_chat_format.py databricks-app-template-serving")
        sys.exit(1)
    
    endpoint_name = sys.argv[1]
    asyncio.run(test_chat_endpoint(endpoint_name))


if __name__ == "__main__":
    main()

