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
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0',
               "block Google Advertising ID provider")

# Disable Android App Set ID retrieval and callback persistence.
APP_SET_PROVIDER = ROOT / "smali/gkl.smali"
replace_method(APP_SET_PROVIDER, 'public final b()V',
               '    .locals 0\n\n    return-void',
               "disable App Set ID retrieval")
replace_method(APP_SET_PROVIDER, 'public final a(ILjava/lang/String;Lcom/google/android/gms/appset/AppSetIdInfo;)V',
               '    .locals 0\n\n    return-void',
               "disable App Set ID persistence callback")

# Disable Huawei OAID retrieval as a second advertising-ID provider.
HUAWEI_AD_ID_PROVIDER = ROOT / "smali/zsl.smali"
replace_method(HUAWEI_AD_ID_PROVIDER, 'public static a(Landroid/app/Application;)Lnpf;',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0',
               "block Huawei OAID retrieval")

# Stop scanning other installed apps for a shared VKPNS device identifier.
VK_PUSH_PROVIDER = ROOT / "smali/bu5.smali"
replace_method(VK_PUSH_PROVIDER, 'public a(Lbx4;)Ljava/lang/Object;',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0',
               "disable cross-app VKPNS package scan")

# Remove permissions used only for advertising identity and install attribution.
import re
MANIFEST = ROOT / "AndroidManifest.xml"
manifest_text = MANIFEST.read_text(encoding="utf-8")
for permission in (
    "com.google.android.gms.permission.AD_ID",
    "com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE",
    "android.permission.REQUEST_INSTALL_PACKAGES",
):
    lines = manifest_text.splitlines(keepends=True)
    matches = [line for line in lines if "<uses-permission" in line and f'android:name="{permission}"' in line]
    if len(matches) != 1:
        raise SystemExit(f"FAIL: expected exactly one manifest permission {permission}, got {len(matches)}")
    manifest_text = "".join(line for line in lines if line not in matches)
    print(f"REMOVED: manifest permission {permission}")
MANIFEST.write_text(manifest_text, encoding="utf-8")

# Suppress the daily permission-status analytics event while completing the worker normally.
DAILY_ANALYTICS = ROOT / "smali/one/me/android/DailyAnalyticsWorker.smali"
replace_method(DAILY_ANALYTICS, 'public final d()Lvo9;',
               '    .locals 1\n\n    new-instance v0, Luo9;\n\n    invoke-direct {v0}, Luo9;-><init>()V\n\n    return-object v0',
               "disable daily permission-status analytics")
# Disable Firebase Analytics instance-ID retrieval.
FIREBASE_HELPER = ROOT / "smali/esl.smali"
replace_method(FIREBASE_HELPER, 'public static a(Landroid/app/Application;Lr9f;)V',
               '    .locals 0\n\n    invoke-static {}, Lr9f;->i()V\n\n    return-void',
               "disable Firebase Analytics app-instance-ID retrieval")

# Suppress host/web-app analytics uploads without affecting their caller flow.
HOST_ANALYTICS = ROOT / "smali/ad8.smali"
replace_method(HOST_ANALYTICS, 'public final d(Lur0;Ljava/util/LinkedHashMap;Lvr0;)Ljava/lang/Object;',
               '    .locals 1\n\n    sget-object v0, Lsej;->a:Lsej;\n\n    return-object v0',
               "disable HostAnalyticsSender upload")

# Suppress call-quality telemetry event; this is separate from call setup/media.
CALL_ANALYTICS = ROOT / "smali_classes2/h88.smali"
replace_method(CALL_ANALYTICS, 'public static X(Lme1;)V',
               '    .locals 0\n\n    return-void',
               "disable vchat.clientStats analytics event")

# Disable the independent Tracer SDK startup, including crash/performance/heap/disk collectors.
manifest_text = MANIFEST.read_text(encoding="utf-8")
manifest_lines = manifest_text.splitlines(keepends=True)
tracer_provider = [line for line in manifest_lines
                   if '<provider' in line and 'android:name="ru.ok.tracer.startup.InitializationProvider"' in line]
tracer_metadata = [line for line in manifest_lines
                   if '<meta-data' in line and 'android:name="ru.ok.tracer.startup.Initializer@' in line]
if len(tracer_provider) != 1 or len(tracer_metadata) != 7:
    raise SystemExit(f"FAIL: Tracer startup manifest entries changed: provider={len(tracer_provider)}, metadata={len(tracer_metadata)}")
manifest_text = "".join(line for line in manifest_lines if line not in tracer_provider and line not in tracer_metadata)
MANIFEST.write_text(manifest_text, encoding="utf-8")
print("REMOVED: Tracer SDK startup provider and 7 diagnostic initializers")

# Prevent the app from exposing its VKPNS device identifier to other apps.
manifest_text = MANIFEST.read_text(encoding="utf-8")
manifest_lines = manifest_text.splitlines(keepends=True)
provider_matches = [line for line in manifest_lines
                    if '<provider' in line and 'android:name="com.vk.push.core.deviceid.contentprovider.VkpnsDeviceIdContentProvider"' in line]
if len(provider_matches) != 1 or 'android:exported="true"' not in provider_matches[0]:
    raise SystemExit(f"FAIL: unexpected VKPNS provider declaration: {len(provider_matches)}")
manifest_text = manifest_text.replace(provider_matches[0],
                                      provider_matches[0].replace('android:exported="true"', 'android:exported="false"', 1),
                                      1)
MANIFEST.write_text(manifest_text, encoding="utf-8")
print("PATCHED: VKPNS device-ID provider is no longer exported")

# Disable active root/emulator-detection result providers.
ROOT_CHECK = ROOT / "smali/dql.smali"
replace_method(ROOT_CHECK, 'static constructor <clinit>()V',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    sput v0, Ldql;->a:I\n\n    return-void',
               "disable root-check static detector")
ROOT_ENV_CHECK = ROOT / "smali/xtb.smali"
replace_method(ROOT_ENV_CHECK, 'public static final M(Landroid/content/Context;)Z',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0',
               "disable root/emulator environment check")

# Disable the central in-app analytics event dispatcher.
APP_ANALYTICS = ROOT / "smali/vu9.smali"
replace_method(APP_ANALYTICS, 'public final h(Ljava/lang/String;Ljava/lang/String;Ljava/util/Map;Z)V',
               '    .locals 0\n\n    return-void',
               "disable central app analytics event dispatcher")

# Disable call diagnostics upload, without touching call signaling or media services.
CALL_UPLOAD = ROOT / "smali_classes3/ru/ok/android/externcalls/analytics/internal/upload/UploadService.smali"
replace_method(CALL_UPLOAD, 'public static a(Landroid/content/Intent;)V',
               '    .locals 0\n\n    return-void', "disable call analytics upload scheduling")
replace_method(CALL_UPLOAD, 'public final onHandleWork(Landroid/content/Intent;)V',
               '    .locals 0\n\n    return-void', "disable call analytics upload worker")

# Disable OneLog collection and all of its network upload entry points.
ONELOG_IMPL = ROOT / "smali/ru/ok/android/onelog/OneLogImpl.smali"
for declaration, label in [
    ('public static upload(Ljava/lang/String;Lru/ok/android/onelog/OneLogTrigger;)V', "static upload"),
    ('public append(Lru/ok/android/onelog/OneLogItem;)V', "append"),
    ('public upload(Ljava/util/Collection;)V', "upload collection"),
    ('public upload(Lru/ok/android/onelog/OneLogItem;)V', "upload item"),
]:
    replace_method(ONELOG_IMPL, declaration, '    .locals 0\n\n    return-void',
                   "disable OneLog " + label)

ONELOG_UPLOAD = ROOT / "smali_classes3/ru/ok/android/onelog/UploadService.smali"
replace_method(ONELOG_UPLOAD, 'public static startUpload(Ljava/lang/String;)V',
               '    .locals 0\n\n    return-void', "disable OneLog upload scheduling")
replace_method(ONELOG_UPLOAD, 'public static startUpload(Ljava/lang/String;Lru/ok/android/onelog/OneLogTrigger;)V',
               '    .locals 0\n\n    return-void', "disable OneLog upload scheduling with trigger")
replace_method(ONELOG_UPLOAD, 'public onHandleWork(Landroid/content/Intent;)V',
               '    .locals 0\n\n    return-void', "disable OneLog upload worker")

ONELOG_DIRECT = ROOT / "smali_classes3/ru/ok/android/onelog/OneLogDirect.smali"
replace_method(ONELOG_DIRECT, 'public final flush()V',
               '    .locals 0\n\n    return-void', "disable OneLog direct flush")
replace_method(ONELOG_DIRECT, 'private final send-B_83SRM(Lru/ok/android/onelog/OneLogItem;Ljava/lang/String;Lps7;)V',
               '    .locals 0\n\n    return-void', "disable OneLog direct sender")
replace_method(ONELOG_DIRECT, 'public final send-PCEVtD0(Lru/ok/android/onelog/OneLogItem;Ljava/lang/String;)V',
               '    .locals 0\n\n    return-void', "disable OneLog direct event sender")

# Disable RuStore metrics background job. This does not affect app-store updates or push.
RUSTORE_METRICS = ROOT / "smali/ru/rustore/sdk/metrics/internal/presentation/SendMetricsEventJobService.smali"
replace_method(RUSTORE_METRICS, 'public final onStartJob(Landroid/app/job/JobParameters;)Z',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0',
               "disable RuStore metrics job")
replace_method(RUSTORE_METRICS, 'public final onStopJob(Landroid/app/job/JobParameters;)Z',
               '    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0',
               "disable RuStore metrics reschedule")

# Remove the three telemetry-only background services from the manifest.
manifest_text = MANIFEST.read_text(encoding="utf-8")
def remove_manifest_service(text, class_name):
    lines = text.splitlines(keepends=True)
    starts = [i for i,line in enumerate(lines)
              if '<service' in line and f'android:name="{class_name}"' in line]
    if len(starts) != 1:
        raise SystemExit(f"FAIL: expected one service {class_name}, got {len(starts)}")
    start = starts[0]
    if '/>' in lines[start]:
        end = start
    else:
        ends = [i for i in range(start, len(lines)) if '</service>' in lines[i]]
        if not ends:
            raise SystemExit(f"FAIL: service closing tag missing: {class_name}")
        end = ends[0]
    del lines[start:end+1]
    print(f"REMOVED: manifest service {class_name}")
    return "".join(lines)
for declaration in (
    'public final onStartJob(Landroid/app/job/JobParameters;)Z',
    'public final onStopJob(Landroid/app/job/JobParameters;)Z',
):
    data = RUSTORE_METRICS.read_text(encoding="utf-8")
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or "return v0" not in data[pos:stop] or "invoke-" in data[pos:stop]:
        raise SystemExit(f"FAIL: RuStore metrics job remains active: {declaration}")
for class_name in (
    "ru.ok.android.externcalls.analytics.internal.upload.UploadService",
    "ru.ok.android.onelog.UploadService",
    "ru.rustore.sdk.metrics.internal.presentation.SendMetricsEventJobService",
):
    manifest_text = remove_manifest_service(manifest_text, class_name)
MANIFEST.write_text(manifest_text, encoding="utf-8")

# Block VKPNS/ClientAnalyticsSender network submissions; push registration remains intact.
CLIENT_ANALYTICS = ROOT / "smali_classes3/nal.smali"
replace_method(CLIENT_ANALYTICS, 'public final d(Lur0;Ljava/util/LinkedHashMap;Lvr0;)Ljava/lang/Object;',
               '    .locals 1\n\n    sget-object v0, Lsej;->a:Lsej;\n\n    return-object v0',
               "disable ClientAnalyticsSender network submissions")

# Disable the remaining file-based CallAnalyticsUploaderV2 collection and upload methods.
CALL_ANALYTICS_V2 = ROOT / "smali_classes3/snb.smali"
for declaration, label in [
    ('public final b()V', "upload trigger"),
    ('public final i(Ljava/io/File;)V', "local analytics file collection"),
    ('public final m()V', "file upload loop"),
]:
    replace_method(CALL_ANALYTICS_V2, declaration, '    .locals 0\n\n    return-void',
                   "disable CallAnalyticsUploaderV2 " + label)

# Suppress MyTracker device/session report serialization, the path that reads
# DeviceParamsDataProvider (model, manufacturer, OS, locale, timezone, display,
# storage, root flag, App Set ID, OAID/GAID and Firebase App Instance ID).
MYTRACKER_DEVICE_REPORT = ROOT / "smali/ktf.smali"
replace_method(MYTRACKER_DEVICE_REPORT,
               'public declared-synchronized d(Lo91;Lg2j;Lee4;JJLnk6;)V',
               '    .locals 0\n\n    return-void',
               "disable MyTracker device/session report serialization")

# Force the optional TracerLite library telemetry to remain disabled even if instantiated.
TRACER_LITE = ROOT / "smali/ru/ok/tracer/lite/TracerLite.smali"
replace_method(TRACER_LITE, 'public final isDisabled()Z',
               '    .locals 1\n\n    const/4 v0, 0x1\n\n    return v0',
               "force TracerLite disabled")

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
data = DAILY_ANALYTICS.read_text(encoding="utf-8")
pos = data.find(".method public final d()Lvo9;")
stop = data.find(".end method", pos)
worker_method = data[pos:stop]
if pos < 0 or stop < 0 or "Luo9;-><init>()V" not in worker_method or "permission_status" in worker_method or "Lvu9;->i" in worker_method:
    raise SystemExit("FAIL: daily permission analytics worker is not inert")
for path, declaration, token in [
    (FIREBASE_HELPER, 'public static a(Landroid/app/Application;Lr9f;)V', 'Lr9f;->i()V'),
    (HOST_ANALYTICS, 'public final d(Lur0;Ljava/util/LinkedHashMap;Lvr0;)Ljava/lang/Object;', 'Lsej;->a:Lsej;'),
    (CALL_ANALYTICS, 'public static X(Lme1;)V', 'return-void'),
]:
    data = path.read_text(encoding="utf-8")
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or token not in data[pos:stop] or "invoke-" in data[pos:stop] and token != "Lr9f;->i()V":
        raise SystemExit(f"FAIL: analytics channel remains active: {declaration}")
manifest_text = MANIFEST.read_text(encoding="utf-8")
if "ru.ok.tracer.startup.InitializationProvider" in manifest_text or "ru.ok.tracer.startup.Initializer@" in manifest_text:
    raise SystemExit("FAIL: Tracer SDK startup metadata remains")
manifest_text = MANIFEST.read_text(encoding="utf-8")
provider_matches = [line for line in manifest_text.splitlines()
                    if '<provider' in line and 'android:name="com.vk.push.core.deviceid.contentprovider.VkpnsDeviceIdContentProvider"' in line]
if len(provider_matches) != 1 or 'android:exported="false"' not in provider_matches[0]:
    raise SystemExit("FAIL: VKPNS device-ID provider is still exported")
for path, declaration, token in [
    (ROOT_CHECK, 'static constructor <clinit>()V', 'sput v0, Ldql;->a:I'),
    (ROOT_ENV_CHECK, 'public static final M(Landroid/content/Context;)Z', 'return v0'),
]:
    data = path.read_text(encoding="utf-8")
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or token not in data[pos:stop] or "invoke-" in data[pos:stop]:
        raise SystemExit(f"FAIL: root detection remains active: {declaration}")
# Verify central app analytics and telemetry upload paths are inert.
data = CLIENT_ANALYTICS.read_text(encoding="utf-8")
pos = data.find(".method public final d(Lur0;Ljava/util/LinkedHashMap;Lvr0;)Ljava/lang/Object;")
stop = data.find(".end method", pos)
if pos < 0 or stop < 0 or "Lsej;->a:Lsej;" not in data[pos:stop] or "Lqg6;->z" in data[pos:stop]:
    raise SystemExit("FAIL: ClientAnalyticsSender still sends events")
data = CALL_ANALYTICS_V2.read_text(encoding="utf-8")
for declaration in ('public final b()V',
                    'public final i(Ljava/io/File;)V',
                    'public final m()V'):
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or "return-void" not in data[pos:stop] or "invoke-" in data[pos:stop]:
        raise SystemExit(f"FAIL: CallAnalyticsUploaderV2 still active: {declaration}")
for path, declarations in [
    (APP_ANALYTICS, ['public final h(Ljava/lang/String;Ljava/lang/String;Ljava/util/Map;Z)V']),
    (CALL_UPLOAD, ['public static a(Landroid/content/Intent;)V',
                   'public final onHandleWork(Landroid/content/Intent;)V']),
    (ONELOG_IMPL, ['public static upload(Ljava/lang/String;Lru/ok/android/onelog/OneLogTrigger;)V',
                   'public append(Lru/ok/android/onelog/OneLogItem;)V',
                   'public upload(Ljava/util/Collection;)V',
                   'public upload(Lru/ok/android/onelog/OneLogItem;)V']),
    (ONELOG_UPLOAD, ['public static startUpload(Ljava/lang/String;)V',
                     'public static startUpload(Ljava/lang/String;Lru/ok/android/onelog/OneLogTrigger;)V',
                     'public onHandleWork(Landroid/content/Intent;)V']),
    (ONELOG_DIRECT, ['public final flush()V',
                     'private final send-B_83SRM(Lru/ok/android/onelog/OneLogItem;Ljava/lang/String;Lps7;)V',
                     'public final send-PCEVtD0(Lru/ok/android/onelog/OneLogItem;Ljava/lang/String;)V']),
]:
    data = path.read_text(encoding="utf-8")
    for declaration in declarations:
        pos = data.find(".method " + declaration)
        stop = data.find(".end method", pos)
        if pos < 0 or stop < 0 or "return-void" not in data[pos:stop] or "invoke-" in data[pos:stop]:
            raise SystemExit(f"FAIL: telemetry sender remains active: {declaration}")
for class_name in (
    "ru.ok.android.externcalls.analytics.internal.upload.UploadService",
    "ru.ok.android.onelog.UploadService",
    "ru.rustore.sdk.metrics.internal.presentation.SendMetricsEventJobService",
):
    if class_name in MANIFEST.read_text(encoding="utf-8"):
        raise SystemExit(f"FAIL: telemetry service remains in manifest: {class_name}")
data = MYTRACKER_DEVICE_REPORT.read_text(encoding="utf-8")
pos = data.find(".method public declared-synchronized d(Lo91;Lg2j;Lee4;JJLnk6;)V")
stop = data.find(".end method", pos)
if pos < 0 or stop < 0 or "return-void" not in data[pos:stop] or "invoke-" in data[pos:stop]:
    raise SystemExit("FAIL: MyTracker device/session report serializer remains active")
data = TRACER_LITE.read_text(encoding="utf-8")
pos = data.find(".method public final isDisabled()Z")
stop = data.find(".end method", pos)
if pos < 0 or stop < 0 or "const/4 v0, 0x1" not in data[pos:stop] or "invoke-" in data[pos:stop]:
    raise SystemExit("FAIL: TracerLite telemetry is not forced disabled")
for path, declaration in [
    (APP_SET_PROVIDER, 'public final b()V'),
    (APP_SET_PROVIDER, 'public final a(ILjava/lang/String;Lcom/google/android/gms/appset/AppSetIdInfo;)V'),
    (HUAWEI_AD_ID_PROVIDER, 'public static a(Landroid/app/Application;)Lnpf;'),
]:
    data = path.read_text(encoding="utf-8")
    pos = data.find(".method " + declaration)
    stop = data.find(".end method", pos)
    if pos < 0 or stop < 0 or "return-" not in data[pos:stop] or "invoke-" in data[pos:stop]:
        raise SystemExit(f"FAIL: identifier provider remains active: {declaration}")
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
