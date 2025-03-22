import requests
import json

def test_api():
    url = "http://localhost:8000/api/tasks"
    headers = {"Content-Type": "application/json"}
    data = {
        "task_type": "read",
        "data": {
            "url": "https://metacatalyst.in"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_api() 