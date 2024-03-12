from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sinks import InfluxDBSink
import asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


sink = InfluxDBSink(url="https://us-east-1-1.aws.cloud2.influxdata.com",
                    token="8KcwFmBCTahxXRbq9gsjHTfHmHfSUgw2f8Ym78zXidI3hk9VShc97zL81Hu36_DBVy5q35heEBzt_-CAO3pNZA==",
                    org="Benz",
                    bucket="test_mark2")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await fetch_data()
            await websocket.send_json({"data": data})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")

async def fetch_data():
    query = '''SELECT * FROM "sample" WHERE time >= now() - interval '7 days' ORDER BY time DESC LIMIT 10'''
    loop = asyncio.get_running_loop()
    table = await loop.run_in_executor(None, lambda: sink.client.query(query))
    data = remove_timestamp(table.to_pylist())
    return data

def remove_timestamp(data):
    return [{k: v for k, v in item.items() if k != 'time'} for item in data]
