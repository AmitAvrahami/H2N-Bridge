import sys
import os
import ctypes
from PyQt6.QtCore import QLibraryInfo

print("=== PyQt6 Diagnosis ===")
print(f"Python: {sys.version}")
print(f"Prefix: {sys.prefix}")
print(f"Site Packages: {sys.path}")

print("\n=== Environment Variables ===")
for k, v in os.environ.items():
    if "QT" in k or "DYLD" in k:
        print(f"{k}={v}")

print("\n=== Qt Configuration ===")
print(f"Plugins Path: {QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)}")
# print(f"Platforms Path: {QLibraryInfo.path(QLibraryInfo.LibraryPath.PlatformPluginsPath)}")
platforms_path = os.path.join(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath), "platforms")
print(f"Platforms Path: {platforms_path}")

print("\n=== Testing Plugin Load ===")
plugin_path = os.path.join(platforms_path, "libqcocoa.dylib")
print(f"Checking for cocoa plugin at: {plugin_path}")

if os.path.exists(plugin_path):
    print("Example: Found libqcocoa.dylib")
    try:
        # Try to load it explicitly to see dlopen errors
        ctypes.CDLL(plugin_path)
        print("Successfully loaded libqcocoa.dylib via ctypes")
    except OSError as e:
        print(f"FAILED to load libqcocoa.dylib: {e}")
else:
    print("libqcocoa.dylib NOT FOUND at expected path")

print("\n=== Attempting App Launch ===")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("QApplication initialized successfully")
except Exception as e:
    print(f"QApplication failed: {e}")
