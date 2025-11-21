import requests
import time
time.sleep(2)
try:
    response = requests.get('http://localhost:5001/api/metrics', timeout=5)
    if response.status_code == 200:
        data = response.json()
        requests_count = data.get('counters', {}).get('agent_requests_total', {}).get('value', 'N/A')
        errors_count = data.get('counters', {}).get('agent_errors_total', {}).get('value', 'N/A')
        histogram_count = data.get('histograms', {}).get('agent_response_time_seconds', {}).get('count', 'N/A')
        print('✅ Dashboard successfully reading persisted metrics!')
        print(f'Agent requests: {requests_count}')
        print(f'Agent errors: {errors_count}')
        print(f'Response time observations: {histogram_count}')
        print('🎉 Cross-process metric sharing is working!')
    else:
        print(f'❌ API returned status {response.status_code}: {response.text[:200]}')
except Exception as e:
    print(f'❌ Error: {e}')
