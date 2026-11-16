#!/usr/bin/env python3
"""Strict, version-specific PAX patch for MAX 26.32.1 (6831)."""
from pathlib import Path
import sys

ROOT = Path("apk_workdir")
PATCH_ROOT = Path("patches")
PARAMS = ROOT / "smali/com/my/tracker/MyTrackerParams.smali"
INIT = ROOT / "smali/d6.smali"

def replace_once(path: Path, old: str, new: str, label: str):
    if not path.is_file():
        raise SystemExit(f"FAIL: missing {path}")
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"FAIL: {label}: expected exactly 1 match, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED: {label}")

# Apply only patch pairs that were proven to match this exact MAX build.
names = [
    "MyTrackerParams_setCustomUserId.smali-snippet",
    "MyTrackerParams_setEmail.smali-snippet",
    "MyTrackerParams_setIcqId.smali-snippet",
    "MyTrackerParams_setLang.smali-snippet",
    "MyTrackerParams_setOkId.smali-snippet",
    "MyTrackerParams_setPhone.smali-snippet",
    "MyTrackerParams_setVkConnectId.smali-snippet",
    "MyTrackerParams_setVkId.smali-snippet",
]
for name in names:
    original = (PATCH_ROOT / "original" / name).read_text(encoding="utf-8")
    patched = (PATCH_ROOT / "patched" / name).read_text(encoding="utf-8")
    replace_once(PARAMS, original, patched, name)

# Explicitly disable MyTracker collection categories while retaining SDK init
# and instance-id APIs that the MAX app itself calls.
anchor = """    invoke-virtual {v10, v7}, Lcom/my/tracker/MyTrackerConfig;->setKidMode(Z)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10
"""
insert = anchor + """    const/4 v11, 0x0

    invoke-virtual {v10, v11}, Lcom/my/tracker/MyTrackerConfig;->setTrackingLaunchEnabled(Z)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10

    invoke-virtual {v10, v11}, Lcom/my/tracker/MyTrackerConfig;->setTrackingEnvironmentEnabled(Z)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10

    invoke-virtual {v10, v11}, Lcom/my/tracker/MyTrackerConfig;->setTrackingPreinstallEnabled(Z)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10

    invoke-virtual {v10, v11}, Lcom/my/tracker/MyTrackerConfig;->setTrackingPreinstallThirdPartyEnabled(Z)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10

    invoke-virtual {v10, v11}, Lcom/my/tracker/MyTrackerConfig;->setAutotrackingPurchaseEnabled(Z)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10

    invoke-virtual {v10, v11}, Lcom/my/tracker/MyTrackerConfig;->setLocationTrackingMode(I)Lcom/my/tracker/MyTrackerConfig;

    move-result-object v10
"""
replace_once(INIT, anchor, insert, "disable MyTracker launch/environment/preinstall/purchase/location collection")

# Verify no direct account ID setter remains in the app's account initializer.
d6 = INIT.read_text(encoding="utf-8")
if "->setCustomUserId(" in d6:
    raise SystemExit("FAIL: account initializer still passes a custom user ID")
print("PASS: account initializer no longer passes MyTracker custom user ID")
print("PASS: strict PAX 26.32.1 patch stage completed")
