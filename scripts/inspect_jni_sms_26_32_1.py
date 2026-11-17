#!/usr/bin/env python3
"""Read-only inspection of MAX 26.32.1 smali for the JNI/SMS fingerprint path."""
from pathlib import Path
import re

ROOT = Path("apk_workdir")
OUT = Path("jni-sms-report.txt")
TARGET_OUT = Path("jni-sms-target-classes.txt")
KEYS = (
    "initializeSessionSeed",
    "fingerprint",
    "getSigningCertificateHistory",
    "GET_SIGNING_CERTIFICATES",
    "GET_SIGNATURES",
    "MessageDigest",
    "Certificate",
    "Signature;",
    "SHA-256",
    "sha256",
    "signingInfo",
    "hasSigningCertificate",
)

files = sorted(ROOT.glob("smali*/**/*.smali"))
hits = []
seen = set()
for path in files:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    class_line = next((x.strip() for x in lines if x.startswith(".class ")), "<class not found>")
    methods = []
    i = 0
    while i < len(lines):
        if lines[i].startswith(".method "):
            start = i
            while i < len(lines) and not lines[i].startswith(".end method"):
                i += 1
            end = min(i + 1, len(lines))
            block = lines[start:end]
            matched = [k for k in KEYS if any(k.lower() in x.lower() for x in block)]
            if matched:
                key = (str(path), start)
                if key not in seen:
                    seen.add(key)
                    hits.append((str(path), class_line, matched, block))
        i += 1

target = []
for path in files:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    for i, line in enumerate(lines):
        if "initializeSessionSeed" in line and not any(
            p == str(path) and start <= i < start + len(block)
            for p, _, _, block in hits
        ):
            lo, hi = max(0, i - 12), min(len(lines), i + 13)
            target.append((str(path), i + 1, lines[lo:hi]))

with OUT.open("w", encoding="utf-8") as f:
    f.write("MAX 26.32.1 / 6831 JNI + SMS fingerprint static inspection\n")
    f.write(f"Smali files scanned: {len(files)}\n")
    f.write(f"Methods with relevant tokens: {len(hits)}\n\n")
    for path, cls, matched, block in hits:
        f.write(f"===== {path} =====\n{cls}\nTOKENS: {', '.join(matched)}\n")
        f.write("\n".join(block) + "\n\n")
    for path, line_no, context in target:
        f.write(f"===== RAW initializeSessionSeed context: {path}:{line_no} =====\n")
        f.write("\n".join(context) + "\n\n")

print(f"JNI_SMS_REPORT: {OUT} ({OUT.stat().st_size} bytes)")
# Preserve complete target classes and every caller of the package-signature checker.
target_paths = {
    ROOT / "smali/lz8.smali",
    ROOT / "smali/one/me/callssdk/CallsSdkInitializer.smali",
    ROOT / "smali_classes2/yt0.smali",
}
callers = []
meta_callers = []
for path in files:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    if any("Lyt0;->a(" in line for line in lines) or any("CallsSdkInitializer;->calculateMeta(" in line for line in lines):
        target_paths.add(path)
        for i, line in enumerate(lines):
            if "Lyt0;->a(" in line or "CallsSdkInitializer;->calculateMeta(" in line:
                callers.append((path, i + 1, lines[max(0, i-35):min(len(lines), i+25)]))
            if "CallsSdkInitializer;->calculateMeta(" in line:
                meta_callers.append((path, i + 1, lines[max(0, i-45):min(len(lines), i+30)]))

with TARGET_OUT.open("w", encoding="utf-8") as f:
    f.write("Complete target classes and callsites for JNI/SMS investigation\\n")
    for path in sorted(target_paths):
        if path.is_file():
            f.write(f"\\n===== FULL CLASS {path} =====\\n")
            f.write(path.read_text(encoding="utf-8", errors="replace"))
            f.write("\\n")
    for path, line_no, context in callers:
        f.write(f"\\n===== CALLER {path}:{line_no} =====\\n")
        f.write("\\n".join(context) + "\\n")

print(f"Scanned {len(files)} smali files; captured {len(hits)} relevant methods, {len(target)} raw contexts, {len(target_paths)} full classes and {len(callers)} yt0 callsites.")
print(f"TARGET_CLASS_REPORT: {TARGET_OUT} ({TARGET_OUT.stat().st_size} bytes)")
print(f"calculateMeta callers: {len(meta_callers)}")
