# Python file: dashboard_setup.py
import subprocess
import time
import webbrowser

# Launch Node-RED
process = subprocess.Popen(["node-red"])

# Wait for Node-RED launched
time.sleep(10)

# Open Dashboard Page
webbrowser.open("http://localhost:1880")
webbrowser.open("http://localhost:1880/ui")

#If cannot open, please open python library and choose 'subprocess.py', find class Popen and change 'shell=False' to 'shell=True' in 'def _init_'.

