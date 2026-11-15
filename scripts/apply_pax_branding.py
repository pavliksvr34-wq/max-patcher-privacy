#!/usr/bin/env python3
"""Apply PAX name and launcher artwork to the decoded APK."""
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path("apk_workdir")
MANIFEST = ROOT / "AndroidManifest.xml"
SOURCE = Path("PAX.png")
ANDROID = "{http://schemas.android.com/apk/res/android}"

if not MANIFEST.is_file():
    raise SystemExit("ERROR: apk_workdir/AndroidManifest.xml is missing")
if not SOURCE.is_file():
    raise SystemExit("ERROR: PAX.png is missing from repository root")

ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
tree = ET.parse(MANIFEST)
application = tree.getroot().find("application")
if application is None:
    raise SystemExit("ERROR: manifest has no application element")

application.set(ANDROID + "label", "PAX")
application.set(ANDROID + "icon", "@mipmap/pax_launcher")
application.set(ANDROID + "roundIcon", "@mipmap/pax_launcher")

# Explicit activity/activity-alias attributes override the application defaults.
for component in list(application):
    if component.tag not in ("activity", "activity-alias"):
        continue
    for intent_filter in component.findall("intent-filter"):
        actions = {node.get(ANDROID + "name") for node in intent_filter.findall("action")}
        categories = {node.get(ANDROID + "name") for node in intent_filter.findall("category")}
        if "android.intent.action.MAIN" in actions and "android.intent.category.LAUNCHER" in categories:
            component.set(ANDROID + "label", "PAX")
            component.set(ANDROID + "icon", "@mipmap/pax_launcher")
            break

tree.write(MANIFEST, encoding="utf-8", xml_declaration=True)

densities = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
with Image.open(SOURCE) as source:
    artwork = source.convert("RGBA")
    if artwork.width != artwork.height:
        raise SystemExit(f"ERROR: PAX icon must be square, got {artwork.size}")
    for density, size in densities.items():
        directory = ROOT / f"res/mipmap-{density}"
        directory.mkdir(parents=True, exist_ok=True)
        artwork.resize((size, size), Image.Resampling.LANCZOS).save(directory / "pax_launcher.png")

print("PAX branding applied successfully.")
