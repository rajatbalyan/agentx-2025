import requests
import json
import time

def send_task(task_type, data):
    url = "http://localhost:8000/api/tasks"
    headers = {"Content-Type": "application/json"}
    task = {
        "task_type": task_type,
        "data": data,
        "priority": 1
    }
    response = requests.post(url, headers=headers, json=task)
    print(f"\nSending {task_type} task:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()

def get_task_details():
    response = requests.get("http://localhost:8000/api/tasks")
    return response.json()

# Step 1: Send a read task that will trigger multiple specialized agents
print("\nStep 1: Sending read task to analyze the website...")
read_task = {
    "url": "http://metacatalyst.in",
    "analysis_type": "full",
    "requirements": {
        "analyze_seo": True,
        "analyze_performance": True,
        "analyze_content": True,
        "check_errors": True,
        "track_files": True  # Enable file tracking
    },
    "workspace": {
        "path": "d:/Programming/Projects/landing-page",
        "track_changes": True
    }
}

read_result = send_task("read", read_task)
print("\nWaiting for Manager Agent to create and assign tasks...")
time.sleep(5)

# Step 2: Get task details to see what specialized agents are doing
print("\nStep 2: Checking specialized agent tasks...")
task_details = get_task_details()

# Step 3: Monitor file changes and task completion
print("\nStep 3: Monitoring specialized agent activities...")
for task in task_details.get("tasks", []):
    if "subtasks" in task:
        for subtask in task["subtasks"]:
            print(f"\nSubtask Type: {subtask['type']}")
            print(f"Priority: {subtask['priority']}")
            if "files_to_modify" in subtask:
                print("Files to be modified:")
                for file in subtask["files_to_modify"]:
                    print(f"- {file}")
            if "task_results" in subtask:
                print("\nTask Results:")
                print(json.dumps(subtask["task_results"], indent=2))

# Step 4: Check CI/CD notifications
print("\nStep 4: Checking CI/CD notifications...")
for task in task_details.get("tasks", []):
    if "ci_cd_notification" in task:
        print("\nCI/CD Notification:")
        print(json.dumps(task["ci_cd_notification"], indent=2)) 