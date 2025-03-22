@echo off
powershell -Command "$body = @{task_type='read';data=@{url='http://metacatalyst.in';analysis_type='full'};priority=1} | ConvertTo-Json; $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/tasks' -Method Post -Body $body -ContentType 'application/json'; Write-Host 'Status Code:' $response.StatusCode; Write-Host 'Response:' $response.Content"
pause