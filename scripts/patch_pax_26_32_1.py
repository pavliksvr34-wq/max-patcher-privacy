#!/usr/bin/env python3
"""Strict, version-specific PAX patch for MAX 26.32.1 (6831)."""
from pathlib import Path
import sys

ROOT = Path("apk_workdir")
PATCH_ROOT = Path("patches")
PARAMS = ROOT / "smali/com/my/tracker/MyTrackerParams.smali"
INIT = ROOT / "smali/d6.smali"

def replace_method(path: Path, declaration: str, body: str, label: str):
    text = path.read_text(encoding="utf-8")
    marker = ".method " + declaration
    start = text.find(marker)
    if start < 0 or text.find(marker, start + 1) >= 0:
        raise SystemExit(f"FAIL: {label}: expected exactly one method declaration")
    end = text.find(".end method", start)
    if end < 0:
        raise SystemExit(f"FAIL: {label}: method terminator missing")
    header_end = text.find("\n", start)
    if header_end < 0:
        raise SystemExit(f"FAIL: {label}: method header malformed")
    replacement = text[start:header_end + 1] + body + "\n.end method"
    text = text[:start] + replacement + text[end + len(".end method"):]
    path.write_text(text, encoding="utf-8")
    print(f"PATCHED: {label}")

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

# Disable MyTracker custom events and user lifecycle events.
TRACKER = ROOT / "smali/com/my/tracker/MyTracker.smali"
USER_LIFECYCLE = ROOT / "smali/com/my/tracker/userlifecycle/MyTrackerUserLifecycle.smali"
# Keep MyTracker configuration objects available, but never start its engine.
replace_method(TRACKER, 'public static initTracker(Ljava/lang/String;Landroid/app/Application;)V',
               '    .locals 0\n\n    return-void', "disable MyTracker engine initialization")
replace_method(TRACKER, 'public static handleDeeplink(Landroid/content/Intent;)Ljava/lang/String;',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0',
               "disable MyTracker attribution deeplinks")
replace_method(TRACKER, 'public static flush()V',
               '    .locals 0\n\n    return-void', "disable MyTracker event flush")
replace_method(TRACKER, 'public static trackEvent(Ljava/lang/String;)V',
               '    .locals 0\n\n    return-void', "disable MyTracker trackEvent(String)")
replace_method(TRACKER, 'public static trackEvent(Ljava/lang/String;Ljava/util/Map;)V',
               '    .locals 0\n\n    return-void', "disable MyTracker trackEvent(String, Map)")
replace_method(TRACKER, 'public static getInstanceId(Landroid/app/Application;)Ljava/lang/String;',
               '    .locals 1\n\n    const-string v0, ""\n\n    return-object v0',
               "disable persistent MyTracker instance ID")
for declaration, label in [
    ('public static trackInviteEvent()V', "trackInviteEvent()"),
    ('public static trackInviteEvent(Ljava/util/Map;)V', "trackInviteEvent(Map)"),
    ('public static trackLoginEvent(Ljava/lang/String;Ljava/lang/String;)V', "trackLoginEvent(String, String)"),
    ('public static trackLoginEvent(Ljava/lang/String;Ljava/lang/String;Ljava/util/Map;)V', "trackLoginEvent(String, String, Map)"),
    ('public static trackRegistrationEvent(Ljava/lang/String;Ljava/lang/String;)V', "trackRegistrationEvent(String, String)"),
    ('public static trackRegistrationEvent(Ljava/lang/String;Ljava/lang/String;Ljava/util/Map;)V', "trackRegistrationEvent(String, String, Map)"),
]:
    replace_method(USER_LIFECYCLE, declaration, '    .locals 0\n\n    return-void',
                   "disable MyTracker " + label)

# Disable independent Google Advertising ID retrieval.
AD_ID_PROVIDER = ROOT / "smali_classes3/x18.smali"
replace_method(AD_ID_PROVIDER, 'public final v(Ljava/lang/Object;)Ljava/lang/Object;',
               '    .locals 1\\n\\n    const/4 v0, 0x0\\n\\n    return-object v0',
               "block Google Advertising ID provider")

# Stop scanning other installed apps for a shared VKPNS device identifier.
VK_PUSH_PROVIDER = ROOT / "smali/bu5.smali"
replace_method(VK_PUSH_PROVIDER, 'public a(Lbx4;)Ljava/lang/Object;',
               '    .locals 1\\n\\n    const/4 v0, 0x0\\n\\n    return-object v0',
               "disable cross-app VKPNS package scan")

# Remove permissions used only for advertising identity and install attribution.
import re
MANIFEST = ROOT / "AndroidManifest.xml"
manifest_text = MANIFEST.read_text(encoding="utf-8")
for permission in (
    "com.google.android.gms.permission.AD_ID",
    "com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE",
):
    pattern = re.compile(r'<uses-permission\\b(?=[^>]*android:name="' + re.escape(permission) + r'")[^>]*/>\\s*')
    manifest_text, count = pattern.subn("", manifest_text)
    if count != 1:
        raise SystemExit(f"FAIL: expected exactly one manifest permission {permission}, got {count}")
    print(f"REMOVED: manifest permission {permission}")
MANIFEST.write_text(manifest_text, encoding="utf-8")

# Verify the account-ID setter itself is now inert. The MAX call site remains
# intentionally intact so account initialization keeps its original control flow.
params = PARAMS.read_text(encoding="utf-8")
method_start = params.find(".method public setCustomUserId(")
method_end = params.find(".end method", method_start)
if method_start < 0 or method_end < 0:
    raise SystemExit("FAIL: setCustomUserId method not found after patch")
method = params[method_start:method_end]
if "return-object p0" not in method or "invoke-" in method:
    raise SystemExit("FAIL: setCustomUserId is not a no-op")
config = (ROOT / "smali/com/my/tracker/MyTrackerConfig.smali").read_text(encoding="utf-8")
for api in ("setTrackingLaunchEnabled(Z)", "setTrackingEnvironmentEnabled(Z)",
            "setTrackingPreinstallEnabled(Z)", "setTrackingPreinstallThirdPartyEnabled(Z)",
            "setAutotrackingPurchaseEnabled(Z)", "setLocationTrackingMode(I)"):
    if api not in config:
        raise SystemExit(f"FAIL: MyTrackerConfig API missing: {api}")
for path, declaration in [
    (AD_ID_PROVIDER, 'public final v(Ljava/lang/Object;)Ljava/lang/Object;'),
    (VK_PUSH_PROVIDER, 'public a(Lbx4;)Ljava/lang/Object;'),
]:
    data = path.read_text(encoding="utf-8")
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or "return-object v0" not in data[pos:stop] or "invoke-" in data[pos:stop]:
        raise SystemExit(f"FAIL: privacy provider still active: {declaration}")
manifest_text = MANIFEST.read_text(encoding="utf-8")
for permission in ("com.google.android.gms.permission.AD_ID",
                   "com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE"):
    if permission in manifest_text:
        raise SystemExit(f"FAIL: sensitive manifest permission remains: {permission}")
for declaration, return_token in [
    ('public static initTracker(Ljava/lang/String;Landroid/app/Application;)V', 'return-void'),
    ('public static handleDeeplink(Landroid/content/Intent;)Ljava/lang/String;', 'return-object v0'),
    ('public static flush()V', 'return-void'),
]:
    data = TRACKER.read_text(encoding="utf-8")
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or return_token not in data[pos:stop] or "invoke-" in data[pos:stop]:
        raise SystemExit(f"FAIL: MyTracker engine boundary not inert: {declaration}")
for path, declarations in [
    (TRACKER, [
        'public static trackEvent(Ljava/lang/String;)V',
        'public static trackEvent(Ljava/lang/String;Ljava/util/Map;)V',
    ]),
    (USER_LIFECYCLE, [
        'public static trackInviteEvent()V',
        'public static trackInviteEvent(Ljava/util/Map;)V',
        'public static trackLoginEvent(Ljava/lang/String;Ljava/lang/String;)V',
        'public static trackLoginEvent(Ljava/lang/String;Ljava/lang/String;Ljava/util/Map;)V',
        'public static trackRegistrationEvent(Ljava/lang/String;Ljava/lang/String;)V',
        'public static trackRegistrationEvent(Ljava/lang/String;Ljava/lang/String;Ljava/util/Map;)V',
    ]),
]:
    data = path.read_text(encoding="utf-8")
    for declaration in declarations:
        pos = data.find(".method " + declaration)
        stop = data.find(".end method", pos)
        method = data[pos:stop]
        if "return-void" not in method or "invoke-" in method:
            raise SystemExit(f"FAIL: method not inert: {declaration}")
data = TRACKER.read_text(encoding="utf-8")
pos = data.find(".method public static getInstanceId(Landroid/app/Application;)Ljava/lang/String;")
stop = data.find(".end method", pos)
if 'const-string v0, ""' not in data[pos:stop]:
    raise SystemExit("FAIL: MyTracker instance ID is not blank")
print("PASS: custom user ID setter is inert; MAX call flow preserved")
print("PASS: all six MyTrackerConfig APIs exist in this bundled SDK")
print("PASS: strict PAX 26.32.1 patch stage completed")
