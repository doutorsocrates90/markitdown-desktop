# -*- mode: python ; coding: utf-8 -*-
# MarkItDown Desktop - GPL-3.0-or-later
# Build with:  pyinstaller --noconfirm packaging/MarkItDownDesktop.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
VERSION = "1.0.0"

datas = [(os.path.join(SRC, "markitdown_desktop", "ui"), "ui")]
binaries = []
hiddenimports = collect_submodules("markitdown") + ["webview.platforms.cocoa"]

for pkg in ("magika", "pdfminer"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
datas += collect_data_files("markitdown")

# Ship license metadata of every bundled runtime dependency.
RUNTIME_PACKAGES = [
    "markitdown", "pdfminer.six", "pdfplumber", "pypdfium2", "magika", "onnxruntime", "numpy",
    "protobuf", "flatbuffers", "pillow", "pywebview", "proxy_tools", "bottle", "pyobjc-core",
    "pyobjc-framework-Cocoa", "pyobjc-framework-WebKit", "pyobjc-framework-Quartz",
    "pyobjc-framework-Security", "pyobjc-framework-UniformTypeIdentifiers", "beautifulsoup4",
    "soupsieve", "markdownify", "six", "charset-normalizer", "requests", "urllib3", "idna",
    "certifi", "defusedxml", "cryptography", "cffi", "pycparser", "click", "python-dotenv",
    "typing_extensions",
]
for pkg in RUNTIME_PACKAGES:
    datas += copy_metadata(pkg)
datas += [(os.path.join(ROOT, "LICENSE"), "."), (os.path.join(ROOT, "THIRD_PARTY_NOTICES.md"), ".")]

a = Analysis(
    [os.path.join(ROOT, "packaging", "launcher.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarkItDown Desktop",
    console=False,
    argv_emulation=False,
    target_arch=None,
    icon=os.path.join(ROOT, "assets", "AppIcon.icns"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="MarkItDown Desktop")

app = BUNDLE(
    coll,
    name="MarkItDown Desktop.app",
    icon=os.path.join(ROOT, "assets", "AppIcon.icns"),
    bundle_identifier="io.github.markitdown-desktop",
    version=VERSION,
    info_plist={
        "CFBundleName": "MarkItDown Desktop",
        "CFBundleDisplayName": "MarkItDown Desktop",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHumanReadableCopyright": "Copyright © 2026 MarkItDown Desktop contributors. GPL-3.0-or-later.",
    },
)
