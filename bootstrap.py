import importlib
import subprocess
import sys

REQUIRED_PACKAGES = {
    "aiohttp": "aiohttp",
    "websockets": "websockets",
    "pyfiglet": "pyfiglet",
    "pytz": "pytz",
    "colorama": "colorama",
    "psutil": "psutil",
}

def ensure_packages():
    missing = []
    for import_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    print(f"[crime] missing packages detected: {', '.join(missing)}")
    print("[crime] installing now...")
    for pip_name in missing:
        print(f"[crime]   installing {pip_name}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pip_name, "--break-system-packages"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name],
                capture_output=True, text=True
            )
        if result.returncode != 0:
            print(f"[crime]   FAILED to install {pip_name}")
            print(result.stderr[-500:])
            sys.exit(1)
        print(f"[crime]   {pip_name} installed.")
    print("[crime] all packages installed, continuing startup...\n")