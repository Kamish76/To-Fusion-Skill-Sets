import json
import urllib.request
import base64
import os

URL = "http://localhost:9100/"

def execute_api_script(script_str):
    """Executes a self-contained Python script inside Autodesk Fusion 360 via JSON-RPC."""
    req_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "execute_api_script",
            "arguments": {"script": script_str}
        }
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(req_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if res.get("result", {}).get("isError"):
            print("ERROR:", res["result"])
        else:
            for item in res.get("result", {}).get("content", []):
                print(item.get("text", ""))
        return res

def get_screenshot(output_path, view="current", width=1024, height=1024):
    """Captures a screenshot of the active Autodesk Fusion 360 viewport."""
    req_data = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_screenshot",
            "arguments": {"view": view, "width": width, "height": height}
        }
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(req_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        for item in res.get("result", {}).get("content", []):
            if item.get("type") == "image":
                img_data = base64.b64decode(item["data"])
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"Saved screenshot to {output_path}")
                return output_path
    return None
