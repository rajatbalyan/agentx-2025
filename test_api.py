import requests
import json
import time

def test_api():
    # Base URL
    base_url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    
    try:
        # Test health endpoint
        print("\nTesting health endpoint...")
        health_response = requests.get(f"{base_url}/api/health")
        print(f"Health Status: {json.dumps(health_response.json(), indent=2)}")
        
        # Test initial system status
        print("\nChecking initial system status...")
        status_response = requests.get(f"{base_url}/api/status")
        print("System Status:")
        print(json.dumps(status_response.json(), indent=2))
        
        # Create first task with performance issues
        print("\nCreating first task (with performance issues)...")
        task1_data = {
            "task_type": "read",
            "data": {
                "url": "https://metacatalyst.in"
            },
            "priority": 1
        }
        
        task1_response = requests.post(
            f"{base_url}/api/tasks",
            headers=headers,
            json=task1_data
        )
        print(f"Status Code: {task1_response.status_code}")
        print("First Task Response:")
        print(json.dumps(task1_response.json(), indent=2))
        
        # Wait a bit for processing
        time.sleep(2)
        
        # Check task list
        print("\nChecking task list...")
        tasks_response = requests.get(f"{base_url}/api/tasks")
        print("Tasks:")
        print(json.dumps(tasks_response.json(), indent=2))
        
        # Create second task
        print("\nCreating second task...")
        task2_data = {
            "task_type": "read",
            "data": {
                "url": "https://example.com"
            },
            "priority": 2
        }
        
        task2_response = requests.post(
            f"{base_url}/api/tasks",
            headers=headers,
            json=task2_data
        )
        print(f"Status Code: {task2_response.status_code}")
        print("Second Task Response:")
        print(json.dumps(task2_response.json(), indent=2))
        
        # Wait a bit for processing
        time.sleep(2)
        
        # Get task summary
        print("\nGetting task summary...")
        summary_response = requests.get(f"{base_url}/api/tasks/summary")
        print("Task Summary:")
        print(json.dumps(summary_response.json(), indent=2))
        
        # Final system status
        print("\nFinal system status...")
        final_status = requests.get(f"{base_url}/api/status")
        print("Final Status:")
        print(json.dumps(final_status.json(), indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_api() 