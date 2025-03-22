import requests
import json

# Task data
task = {
    "task_type": "read",
    "data": {
        "url": "http://metacatalyst.in",
        "analysis_type": "full"
    },
    "priority": 1
}

# Send request
response = requests.post(
    "http://localhost:8000/api/tasks",
    json=task,
    headers={"Content-Type": "application/json"}
)

# Print response
print("Status Code:", response.status_code)
print("Response:", json.dumps(response.json(), indent=2)) 