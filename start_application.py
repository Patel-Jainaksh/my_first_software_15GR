import subprocess
import webbrowser
import os
import time

# === CONFIGURATION ===
PYTHON_PATH = r"C:\AI_VIGILNET\python\python.exe"

APP_1 = r"project01\app.py"
PORT_1 = 8080
URL_1 = f"http://127.0.0.1:{PORT_1}"

APP_2 = r"annotator02\app.py"
PORT_2 = 8082
URL_2 = f"http://127.0.0.1:{PORT_2}"

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
STATE_FILE = "AppStatus.json"

# === FUNCTIONS ===

def close_ports(*ports):
    """Kill any process using the given ports using Windows netstat and taskkill."""
    for port in ports:
        try:
            # Run netstat and filter for the port
            result = subprocess.check_output(
                f'netstat -ano | findstr :{port}', shell=True
            ).decode()

            lines = result.strip().split('\n')
            pids = set()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    pids.add(pid)

            for pid in pids:
                if pid != "0":
                    print(f"⚠️ Killing PID {pid} using port {port}")
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except subprocess.CalledProcessError:
            # No process using the port
            print(f"✅ Port {port} is free.")

def open_browser_app_mode(url):
    """Open Chrome in app mode."""
    if os.path.exists(CHROME_PATH):
        try:
            subprocess.Popen([CHROME_PATH, f'--app={url}'])
        except Exception as e:
            print(f"❌ Chrome launch failed: {e}")
            webbrowser.open(url)
    else:
        webbrowser.open(url)

def mark_app_as_started():
    with open(STATE_FILE, "w") as f:
        f.write("started")

def app_started_before():
    return os.path.exists(STATE_FILE)

def launch_in_new_terminal(python_exe, script_path):
    """Launch the Python app in a new terminal window."""
    return subprocess.Popen(
        ["start", "cmd", "/k", f"{python_exe} {script_path}"],
        shell=True
    )

# === MAIN ===

def main():
    if not os.path.exists(PYTHON_PATH):
        print("❌ Python not found.")
        return
    if not os.path.exists(APP_1):
        print("❌ App 1 not found.")
        return
    if not os.path.exists(APP_2):
        print("❌ App 2 not found.")
        return

    if app_started_before():
        print("🔁 Cleaning ports...")
        close_ports(PORT_1, PORT_2)

    try:
        print(f"🚀 Launching Flask App 1 on port {PORT_1}")
        launch_in_new_terminal(PYTHON_PATH, APP_1)

        print(f"🚀 Launching Flask App 2 on port {PORT_2}")
        launch_in_new_terminal(PYTHON_PATH, APP_2)

        mark_app_as_started()

        time.sleep(2)
        open_browser_app_mode(URL_1)
        open_browser_app_mode(URL_2)

        print("✅ Both apps launched. Check browser windows.")
    except Exception as e:
        print(f"❌ Error launching apps: {e}")

    input("Press Enter to close this launcher...")

if __name__ == "__main__":
    main()
