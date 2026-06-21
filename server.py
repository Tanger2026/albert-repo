from flask import Flask, jsonify, request
import subprocess
import plistlib
import base64
import os

app = Flask(__name__)

# --- Sensitive fields to hide ---
SENSITIVE_KEYS = {"DeviceCertificate", "HostPrivateKey", "RootPrivateKey", "EscrowBag"}

def sanitize_data(data):
    if isinstance(data, dict):
        return {k: ("***HIDDEN***" if k in SENSITIVE_KEYS else sanitize_data(v)) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(v) for v in data]
    elif isinstance(data, bytes):
        return base64.b64encode(data).decode("utf-8")
    else:
        return data

# --- Endpoints ---
@app.route("/devices", methods=["GET"])
def list_devices():
    try:
        result = subprocess.check_output(["idevice_id", "-l"]).decode().strip().splitlines()
        if not result:
            return jsonify({"error": "No devices detected"}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/device/<udid>", methods=["GET"])
def device_info(udid):
    try:
        result = subprocess.check_output(["ideviceinfo", "-u", udid, "-x"]).decode()
        plist_data = plistlib.loads(result.encode())
        safe_data = sanitize_data(plist_data)
        return jsonify(safe_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload_plist():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files["file"]
        plist_data = plistlib.load(file)
        safe_data = sanitize_data(plist_data)
        return jsonify(safe_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
