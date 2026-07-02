import subprocess, sys
p = subprocess.Popen(
    [sys.executable, "-c", "from betting_bot.cli import main; main()", "serve"],
    cwd="C:\\Users\\miche\\desktop\\sport-betting",
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print(f"Server PID: {p.pid}")
