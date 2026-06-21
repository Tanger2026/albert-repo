import os
import subprocess
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import requests
import json
import csv
import base64
import plistlib
import threading

SERVER_URL = "http://127.0.0.1:8080"

# --- Helper Functions ---
def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode("utf-8")
    else:
        return obj

def log_message(msg):
    log_panel.insert(tk.END, msg + "\n")
    log_panel.see(tk.END)

# --- Device Functions ---
def detect_devices():
    try:
        response = requests.get(f"{SERVER_URL}/devices")
        if response.status_code == 200:
            devices = response.json()
            if devices:
                device_dropdown['values'] = devices
                device_dropdown.current(0)
                status_label.config(text="Devices detected.")
                log_message(f"Devices found: {devices}")
            else:
                device_dropdown['values'] = []
                status_label.config(text="⚠️ No devices connected.")
                log_message("No devices detected.")
        else:
            status_label.config(text="⚠️ No devices connected.")
            log_message("Server returned no devices.")
    except Exception as e:
        status_label.config(text=f"Error: {e}")
        log_message(f"Error detecting devices: {e}")

def read_device_info():
    udid = device_var.get()
    if not udid:
        messagebox.showwarning("Warning", "No device selected.")
        return
    try:
        response = requests.get(f"{SERVER_URL}/device/{udid}")
        if response.status_code == 200:
            data = sanitize_for_json(response.json())
            show_json(data)
            log_message("Device info loaded.")
        else:
            log_message("Failed to read device info.")
    except Exception as e:
        log_message(f"Error: {e}")

def load_plist():
    file_path = filedialog.askopenfilename(filetypes=[("Plist files", "*.plist")])
    if not file_path:
        return
    try:
        with open(file_path, "rb") as f:
            plist_data = plistlib.load(f)
        data = sanitize_for_json(plist_data)
        show_json(data)
        log_message(f"Plist loaded: {file_path}")
    except Exception as e:
        log_message(f"Error loading plist: {e}")

def show_json(data):
    json_viewer.delete("1.0", tk.END)
    json_viewer.insert(tk.END, json.dumps(data, indent=4))

def clear_viewer():
    json_viewer.delete("1.0", tk.END)
    log_panel.delete("1.0", tk.END)

def save_json():
    file_path = filedialog.asksaveasfilename(defaultextension=".json")
    if not file_path:
        return
    try:
        content = json_viewer.get("1.0", tk.END)
        with open(file_path, "w") as f:
            f.write(content)
        log_message(f"JSON saved: {file_path}")
    except Exception as e:
        log_message(f"Error saving JSON: {e}")

def export_csv():
    file_path = filedialog.asksaveasfilename(defaultextension=".csv")
    if not file_path:
        return
    try:
        content = json.loads(json_viewer.get("1.0", tk.END))
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            if isinstance(content, dict):
                writer.writerow(content.keys())
                writer.writerow(content.values())
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        writer.writerow(item.values())
        log_message(f"CSV exported: {file_path}")
    except Exception as e:
        log_message(f"Error exporting CSV: {e}")

# --- AutoRemove Git Function ---
def auto_remove_tokens():
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        commits = subprocess.check_output(["git", "rev-list", "--count", "HEAD"]).decode().strip()
    except Exception as e:
        branch = "Unknown"
        commits = "Unknown"
        log_message(f"Error fetching branch/commits: {e}")

    confirm = messagebox.askyesno(
        "Confirm AutoRemove",
        f"هل أنت متأكد أنك تريد تنفيذ AutoRemove؟\n\n"
        f"⚠️ هذا سيعيد كتابة تاريخ الـ Git ويدفع التغييرات بالقوة.\n\n"
        f"الفرع الحالي: {branch}\n"
        f"عدد الكوميتات: {commits}"
    )
    if not confirm:
        log_message("AutoRemove cancelled by user.")
        return

    OLD_TOKEN = "YOUR_TOKEN_HERE"
    NEW_TOKEN = "REDACTED_TOKEN_PLACEHOLDER"
    mapping_content = f"{OLD_TOKEN}==>{NEW_TOKEN}\n"
    mapping_file = "../filter_rules.txt"

    try:
        with open(mapping_file, "w") as f:
            f.write(mapping_content)
        log_message("[1/4] Created text replacement map...")

        log_message("[2/4] Rewriting history...")
        subprocess.run(["git", "filter-repo", "--force", "--replace-text", mapping_file], check=True)

        log_message("[3/4] Purging old git caches...")
        subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"], check=True)
        subprocess.run(["git", "gc", "--prune=now", "--aggressive"], check=True)

        log_message("[4/4] Force pushing updated history...")
        subprocess.run(["git", "push", "origin", "--force", "--all"], check=True)
        subprocess.run(["git", "push", "origin", "--force", "--tags"], check=True)

        messagebox.showinfo("Success", "✅ History purged and remote updated!")

    except Exception as e:
        messagebox.showerror("Error", f"AutoRemove failed: {e}")
    finally:
        if os.path.exists(mapping_file):
            os.remove(mapping_file)

# --- GUI Setup ---
root = tk.Tk()
root.title("Apple Device Info - Neon Soft UI")
root.geometry("1000x600")
root.configure(bg="#1e1e2f")

sidebar = tk.Frame(root, bg="#2a2a3d", width=200)
sidebar.pack(side="left", fill="y")

main_frame = tk.Frame(root, bg="#1e1e2f")
main_frame.pack(side="right", expand=True, fill="both")

device_var = tk.StringVar()
device_dropdown = ttk.Combobox(sidebar, textvariable=device_var, state="readonly")
device_dropdown.pack(pady=10, padx=10)

btn_read = tk.Button(sidebar, text="Read Device Info", command=read_device_info, bg="#3a3a4d", fg="white")
btn_read.pack(fill="x", padx=10, pady=5)

btn_plist = tk.Button(sidebar, text="Load Plist", command=load_plist, bg="#3a3a4d", fg="white")
btn_plist.pack(fill="x", padx=10, pady=5)

btn_save = tk.Button(sidebar, text="Save JSON", command=save_json, bg="#3a3a4d", fg="white")
btn_save.pack(fill="x", padx=10, pady=5)

btn_csv = tk.Button(sidebar, text="Export CSV", command=export_csv, bg="#3a3a4d", fg="white")
btn_csv.pack(fill="x", padx=10, pady=5)

btn_clear = tk.Button(sidebar, text="Clear Viewer", command=clear_viewer, bg="#3a3a4d", fg="white")
btn_clear.pack(fill="x", padx=10, pady=5)

btn_auto_remove = tk.Button(sidebar, text="AutoRemove", command=auto_remove_tokens, bg="#a83232", fg="white")
btn_auto_remove.pack(fill="x", padx=10, pady=5)

status_label = tk.Label(sidebar, text="Status: Idle", bg="#2a2a3d", fg="lightgray")
status_label.pack(pady=10)

json_viewer = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, bg="#1e1e2f", fg="lightgreen", insertbackground="white")
json_viewer.pack(expand=True, fill="both", padx=10, pady=10)

log_panel = scrolledtext.ScrolledText(main_frame, height=8, bg="#1e1e2f", fg="lightblue", insertbackground="white")
log_panel.pack(expand=False, fill="x", padx=10, pady=10)

threading.Thread(target=detect_devices, daemon=True).start()

root.mainloop()
