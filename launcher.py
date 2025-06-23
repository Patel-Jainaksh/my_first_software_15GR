import os
import zipfile
import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess

# Define file paths
PYTHON_ZIP = "python.zip"
PYTHON_TARGET_PATH = r"C:\AI_VIGILNET"
OFFLINE_PACKAGES = "offline_packages"

# PostgreSQL setup
POSTGRES_INSTALL_PATH = r"C:\Program Files\PostgreSQL\17"
POSTGRES_PASSWORD = "rootroot"
POSTGRES_PORT = "5432"

# Create necessary folders
folder_path = r"C:\AI_VIGILNET\detections"
os.makedirs(folder_path, exist_ok=True)
folder_path = r"C:\AI_VIGILNET\auto_recordings"
os.makedirs(folder_path, exist_ok=True)
folder_path = r"C:\AI_VIGILNET\manual_recordings"
os.makedirs(folder_path, exist_ok=True)


# Log function to display messages in the GUI
def log(msg):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)


# Function to check if Python exists in the target directory
def check_python():
    return os.path.exists(os.path.join(PYTHON_TARGET_PATH, "python.exe"))


# Function to unzip the python.zip to the target directory
def unzip_python():
    if not os.path.exists(PYTHON_ZIP):
        log(f"[ERROR] Missing file: {PYTHON_ZIP}")
        return False

    log("Unzipping Python...")
    try:
        # Unzipping the python.zip to the target directory
        with zipfile.ZipFile(PYTHON_ZIP, 'r') as zip_ref:
            zip_ref.extractall(PYTHON_TARGET_PATH)
        log("✅ Python extraction complete.")
        return True
    except Exception as e:
        log(f"[ERROR] Python unzip failed: {e}")
        return False


# Function to setup PostgreSQL database and user
def setup_database():
    psql_path = os.path.join(POSTGRES_INSTALL_PATH, "bin", "psql.exe")
    if not os.path.exists(psql_path):
        log("[ERROR] psql not found after PostgreSQL install.")
        return False

    log("Setting up PostgreSQL user and database...")

    sql_commands = [
        f"CREATE USER agx WITH PASSWORD '{POSTGRES_PASSWORD}';",
        f"CREATE DATABASE ai_sur OWNER agx;",
        f"GRANT ALL PRIVILEGES ON DATABASE ai_sur TO agx;"
    ]

    try:
        for cmd in sql_commands:
            env = os.environ.copy()
            env["PGPASSWORD"] = POSTGRES_PASSWORD

            subprocess.run([psql_path,
                            "-U", "postgres",
                            "-h", "127.0.0.1",
                            "-p", POSTGRES_PORT,
                            "-d", "postgres",
                            "-c", cmd],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW, env=env)

            log(f"✅ Executed: {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"[ERROR] DB setup failed: {e.stderr.decode().strip()}")
        return False


# Function to run the setup process
def run_setup():
    def _threaded():
        start_btn.config(state=tk.DISABLED)

        # Unzip Python and check if successful
        if not unzip_python():
            start_btn.config(state=tk.NORMAL)
            return

        # Set up PostgreSQL database
        if not setup_database():
            start_btn.config(state=tk.NORMAL)
            return

        log("Setup is complete.")

        start_btn.config(state=tk.NORMAL)

    # Start the setup in a separate thread to avoid blocking the UI
    threading.Thread(target=_threaded).start()


# === GUI SETUP ===
root = tk.Tk()
root.title("AI VigilNet Setup")
root.geometry("600x400")
root.resizable(False, False)

# Title Label
tk.Label(root, text="AI VigilNet Setup", font=("Arial", 16)).pack(pady=10)

# Start Setup Button
start_btn = tk.Button(root, text="Start Setup", command=run_setup, font=("Arial", 12), width=20)
start_btn.pack(pady=5)

# Log Area
log_text = scrolledtext.ScrolledText(root, width=80, height=15, state=tk.DISABLED, font=("Courier", 9))
log_text.pack(padx=10, pady=10)

# Exit Button
tk.Button(root, text="Exit", command=root.quit, width=10).pack(pady=5)

# Run the GUI
root.mainloop()
