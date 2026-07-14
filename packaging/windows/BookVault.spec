# PyInstaller spec for the BookVault Windows desktop app (onedir).
#
# Produces dist/BookVault/ -- a folder holding BookVault.exe + _internal/. This
# is a onedir build (COLLECT, no --onefile): --onefile would unpack to a temp
# dir on every launch and make GUI startup slow. The bundle is self-contained
# EXCEPT for Playwright's Chromium, which is downloaded on first run (see
# bookvault_desktop.app._ensure_chromium). We DO bundle Playwright's Node driver
# (collect_all below), which is what makes that first-run install work in a
# frozen app.
#
# Build (from packaging/windows/):
#   pyinstaller --noconfirm --clean BookVault.spec
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# The bookvault_* packages are installed EDITABLE, so PyInstaller's import
# analysis can't find their sources by name alone -- point it at the source
# roots. (SPECPATH is the dir containing this spec: packaging/windows/.)
_ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
pathex = [os.path.join(_ROOT, p) for p in ("core", "web", "desktop")]

# The frozen entry point is the cross-platform launcher shared with the macOS
# and Linux builds: packaging/entry.py (one level up from this spec).
_ENTRY = os.path.join(SPECPATH, "..", "entry.py")

# Version stamped into the build; the tag-driven CI build passes the release
# version, local builds default to this.
_VERSION = os.environ.get("BOOKVAULT_VERSION", "1.0.0")

datas = []
binaries = []
hiddenimports = []

# Third-party packages that ship data/binaries PyInstaller won't find by import
# analysis alone: Playwright (its bundled Node driver + package json), pywebview
# (its JS shims +, on Windows, the WebView2 lib/ DLLs), curl_cffi (native libs),
# keyring (backends). On Windows the auto-discovered pywebview + pythonnet hooks
# additionally bundle Python.Runtime.dll and the WinForms/EdgeChromium interop.
for pkg in ("playwright", "webview", "curl_cffi", "keyring"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# bookvault_web ships Jinja templates + static CSS/JS as package data.
datas += collect_data_files("bookvault_web")

# uvicorn resolves its event-loop / protocol / lifespan implementations by
# string import at runtime, so they must be pulled in explicitly.
hiddenimports += collect_submodules("uvicorn")
# The app's own (editable) packages and all their submodules.
for pkg in ("bookvault_core", "bookvault_web", "bookvault_desktop"):
    hiddenimports += collect_submodules(pkg)

# Windows-specific hidden imports:
#  - clr / clr_loader: pythonnet, required by pywebview's edgechromium backend.
#    Belt-and-suspenders alongside pythonnet's own hook -- the documented fix
#    for the "Failed to resolve Python.Runtime" frozen-app failure.
#  - webview.platforms.*: pywebview resolves the backend by string at runtime.
#  - _cffi_backend: curl_cffi's compiled cffi backend, not always caught by
#    import analysis on Windows.
hiddenimports += [
    "clr",
    "clr_loader",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "_cffi_backend",
]

a = Analysis(
    [_ENTRY],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: binaries live alongside, not inside the exe
    name="BookVault",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI app: no cmd window
    icon=None,  # optional: "BookVault.ico"
)

# onedir output -> dist\BookVault\. No BUNDLE on Windows (that is macOS-only).
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BookVault",
)
