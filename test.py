import json
from app import app  

with app.test_client() as client:

    data = {"request": " attractions in Jeddah"}

    # Send request
    response = client.post('/chat', json=data)

    #JSON response
    print(json.dumps(response.json, indent=2))
