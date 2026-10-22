import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
title="Smart City NOC Cloud API",
version="1.0.0",
description="Cloud backend for the Smart City NOC simulation",
)



API_TOKEN = os.environ.get("API_TOKEN", "")

zones = {
f"zone_{i}": {
"online": True,
"temperature_c": round(24 + i * 0.7, 1),
"humidity_percent": 50 + i,
"power_w": 80 + i * 15,
"water_flow_l_min": 1.2 + i * 0.2,
}
for i in range(1, 7)
}

devices = {
"street_lights": True,
"traffic_system": True,
"water_pump": True,
"greenhouse_pump": True,
"garage_gate": False,
}

commands: list[dict[str, Any]] = []
next_command_id = 1

class Telemetry(BaseModel):
zones: dict[str, dict[str, Any]] | None = None
devices: dict[str, bool] | None = None

class CommandRequest(BaseModel):
device: str
value: bool
source: str = "mobile"

def check_token(authorization: str | None):
if authorization != f"Bearer {API_TOKEN}":
raise HTTPException(status_code=401, detail="Invalid API token")

@app.get("/")
def home():
return {
"service": "Smart City NOC Cloud API",
"status": "online",
"docs": "/docs",
}

@app.get("/api/health")
def health():
return {
"status": "online",
"timestamp": datetime.now(timezone.utc).isoformat(),
}

@app.get("/api/city")
def get_city():
return {
"timestamp": datetime.now(timezone.utc).isoformat(),
"zones": zones,
"devices": devices,
"pending_commands": sum(
1 for command in commands if command["status"] == "pending"
),
}

@app.post("/api/telemetry")
def update_telemetry(
data: Telemetry,
authorization: str | None = Header(default=None),
):
check_token(authorization)


if data.zones is not None:
    for zone_id, values in data.zones.items():
        if zone_id in zones:
            zones[zone_id].update(values)

if data.devices is not None:
    for device, value in data.devices.items():
        if device in devices:
            devices[device] = value

return {"success": True, "message": "Telemetry updated"}


@app.post("/api/commands")
def create_command(
request: CommandRequest,
authorization: str | None = Header(default=None),
):
global next_command_id
check_token(authorization)


if request.device not in devices:
    raise HTTPException(status_code=400, detail="Unknown device")

command = {
    "id": next_command_id,
    "device": request.device,
    "value": request.value,
    "source": request.source,
    "status": "pending",
    "created_at": datetime.now(timezone.utc).isoformat(),
}

next_command_id += 1
commands.append(command)

return {"success": True, "command": command}


@app.get("/api/commands/pending")
def get_pending_commands(
authorization: str | None = Header(default=None),
):
check_token(authorization)


return {
    "commands": [
        command for command in commands if command["status"] == "pending"
    ]
}


@app.post("/api/commands/{command_id}/result")
def report_command_result(
command_id: int,
success: bool,
authorization: str | None = Header(default=None),
):
check_token(authorization)


for command in commands:
    if command["id"] == command_id:
        if command["status"] != "pending":
            raise HTTPException(
                status_code=409, detail="Command already processed"
            )

        command["status"] = "executed" if success else "failed"

        if success:
            devices[command["device"]] = command["value"]

        return {"success": True, "command": command}

raise HTTPException(status_code=404, detail="Command not found")

