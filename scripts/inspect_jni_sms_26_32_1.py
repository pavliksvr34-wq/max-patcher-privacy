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
    for path, line_no, context in meta_callers:
        f.write(f"\\n===== CALCULATE_META CALLER {path}:{line_no} =====\\n")
        f.write("\\n".join(context) + "\\n")

print(f"Scanned {len(files)} smali files; captured {len(hits)} relevant methods, {len(target)} raw contexts, {len(target_paths)} full classes and {len(callers)} yt0 callsites.")
print(f"TARGET_CLASS_REPORT: {TARGET_OUT} ({TARGET_OUT.stat().st_size} bytes)")
print(f"calculateMeta callers: {len(meta_callers)}")

# Read-only SMS authorization trace: preserve complete login screens,
# integrity-protection classes, and methods that invoke or reference them.
AUTH_OUT = Path("sms-auth-flow-report.txt")
AUTH_CLASS_TOKENS = (
    "Lone/me/login/inputphone/InputPhoneScreen;",
    "Lone/me/login/confirm/ConfirmPhoneScreen;",
    "IntegrityProtectionInteractor",
    "SmsAttemptExceed",
    "AUTH_OTP",
    "verifyIntegrity",
)
auth_classes = []
auth_callers = []
for path in files:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    class_line = next((x.strip() for x in source.splitlines() if x.startswith(".class ")), "")
    if any(token in source for token in AUTH_CLASS_TOKENS) or any(
        token.rsplit("/", 1)[-1].split(";")[0] in class_line for token in AUTH_CLASS_TOKENS[:2]
    ):
        auth_classes.append((path, source))
        continue
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if any(token in line for token in AUTH_CLASS_TOKENS):
            start = i
            while start > 0 and not lines[start].startswith(".method "):
                start -= 1
            if lines[start].startswith(".method "):
                end = i
                while end < len(lines) and not lines[end].startswith(".end method"):
                    end += 1
                auth_callers.append((path, start + 1, lines[start:min(end + 1, len(lines))]))
with AUTH_OUT.open("w", encoding="utf-8") as f:
    f.write("MAX 26.32.1 / 6831 SMS authorization and integrity static inspection\\n")
    f.write(f"Smali files scanned: {len(files)}\\n")
    f.write(f"Target classes: {len(auth_classes)}\\n")
    f.write(f"Caller methods: {len(auth_callers)}\\n\\n")
    for path, source in auth_classes:
        f.write(f"===== AUTH CLASS {path} =====\\n{source}\\n\\n")
    for path, line_no, method in auth_callers:
        f.write(f"===== AUTH CALLER {path}:{line_no} =====\\n")
        f.write("\\n".join(method) + "\\n\\n")
print(f"SMS_AUTH_REPORT: {AUTH_OUT} ({AUTH_OUT.stat().st_size} bytes)")

# Capture the actual login ViewModels and all methods that reference them.
# The previous screen-only report did not include these classes, so it could
# not establish the path from the UI action to the authentication request.
VM_OUT = Path("sms-auth-viewmodels-report.txt")
VM_DESCRIPTORS = ("Lox8;", "Lhi4;")
vm_classes = []
vm_callers = []
for path in files:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    class_line = next((x.strip() for x in lines if x.startswith(".class ")), "")
    if any(desc in class_line for desc in VM_DESCRIPTORS):
        vm_classes.append((path, lines))
        continue
    for i, line in enumerate(lines):
        if any(desc + "->" in line for desc in VM_DESCRIPTORS):
            start = i
            while start > 0 and not lines[start].startswith(".method "):
                start -= 1
            if lines[start].startswith(".method "):
                end = i
                while end < len(lines) and not lines[end].startswith(".end method"):
                    end += 1
                vm_callers.append((path, start + 1, lines[start:min(end + 1, len(lines))]))
with VM_OUT.open("w", encoding="utf-8") as f:
    f.write("MAX 26.32.1 / 6831 SMS auth ViewModels and callsites\\n")
    f.write(f"Smali files scanned: {len(files)}\\n")
    f.write(f"ViewModel classes: {len(vm_classes)}\\n")
    f.write(f"Caller methods: {len(vm_callers)}\\n\\n")
    for path, lines in vm_classes:
        f.write(f"===== VIEWMODEL {path} =====\\n")
        f.write("\\n".join(lines) + "\\n\\n")
    for path, line_no, method in vm_callers:
        f.write(f"===== VIEWMODEL CALLER {path}:{line_no} =====\\n")
        f.write("\\n".join(method) + "\\n\\n")
print(f"SMS_AUTH_VIEWMODELS_REPORT: {VM_OUT} ({VM_OUT.stat().st_size} bytes)")

# Follow the phone-validation result into the domain/repository/network layer.
# These classes are selected from concrete callsites in Lox8.d1(), not by
# broad keyword matching. This remains read-only and does not modify the APK.
FLOW_OUT = Path("sms-auth-domain-network-report.txt")
FLOW_DESCRIPTORS = ("Loe0;", "Lnx9;", "Lme0;", "Lgig;", "Lrf0;", "Lmf5;", "Lle0;", "Ld5e;")
flow_classes = []
flow_callers = []
for path in files:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    class_line = next((x.strip() for x in lines if x.startswith(".class ")), "")
    if any(desc in class_line for desc in FLOW_DESCRIPTORS):
        flow_classes.append((path, lines))
        continue
    for i, line in enumerate(lines):
        if any(desc + "->" in line for desc in FLOW_DESCRIPTORS):
            start = i
            while start > 0 and not lines[start].startswith(".method "):
                start -= 1
            if lines[start].startswith(".method "):
                end = i
                while end < len(lines) and not lines[end].startswith(".end method"):
                    end += 1
                flow_callers.append((path, start + 1, lines[start:min(end + 1, len(lines))]))
with FLOW_OUT.open("w", encoding="utf-8") as f:
    f.write("MAX 26.32.1 / 6831 phone validation -> auth domain/network layer\\n")
    f.write(f"Smali files scanned: {len(files)}\\n")
    f.write(f"Target classes: {len(flow_classes)}\\n")
    f.write(f"Caller methods: {len(flow_callers)}\\n\\n")
    for path, lines in flow_classes:
        f.write(f"===== FLOW CLASS {path} =====\\n")
        f.write("\\n".join(lines) + "\\n\\n")
    for path, line_no, method in flow_callers:
        f.write(f"===== FLOW CALLER {path}:{line_no} =====\\n")
        f.write("\\n".join(method) + "\\n\\n")
print(f"SMS_AUTH_DOMAIN_NETWORK_REPORT: {FLOW_OUT} ({FLOW_OUT.stat().st_size} bytes)")


# Focused auth repository trace: include exact files discovered from real callsites.
FOCUSED_OUT = Path("sms-auth-focused-trace.txt")
NL = chr(10)
focused_paths = (
    ROOT / "smali_classes2/sn.smali",
    ROOT / "smali_classes3/oe0.smali",
    ROOT / "smali_classes2/lyx9.smali",
    ROOT / "smali_classes2/logc.smali",
    ROOT / "smali_classes2/jif.smali",
    ROOT / "smali_classes2/lki.smali",
    ROOT / "smali_classes2/aki.smali",
    ROOT / "smali_classes2/alc.smali",
    ROOT / "smali_classes2/me0.smali",
    ROOT / "smali_classes2/nx9.smali",
    ROOT / "smali/ox8.smali",
)
out = ["MAX 26.32.1 / 6831 focused SMS auth trace", f"Smali files scanned: {len(files)}"]
for path in focused_paths:
    out.append(NL + f"===== FULL CLASS {path} =====")
    if path.is_file():
        out.append(path.read_text(encoding="utf-8", errors="replace"))
    else:
        out.append("FILE NOT FOUND")
# Resolve obfuscated class names from their actual .class declarations.
for class_name in ("f0d", "he0", "jif", "lki", "logc", "lyx9", "aki", "alc"):
    descriptor = "L" + class_name + ";"
    for candidate in files:
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        first = next((line.strip() for line in content.splitlines() if line.startswith(".class ")), "")
        if first.endswith(descriptor):
            out.append(NL + f"===== RESOLVED CLASS {descriptor} ({candidate}) =====")
            out.append(content)
            break
# Enumerate every callsite of oe0.a and me0 in all decoded dex directories.
for desc in ("Loe0;->a(", "Lme0;"):
    out.append(NL + f"===== CALLSITES {desc} =====")
    count = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if desc in line:
                count += 1
                lo, hi = max(0, i-35), min(len(lines), i+45)
                out.append(f"--- {path}:{i+1} ---")
                out.extend(lines[lo:hi])
    out.append(f"CALLSITE COUNT: {count}")
# Trace creation and confirmation operations which precede AUTH_BY_TRACK.
for token in ('"AUTH_REQUEST"', '"AUTH_CREATE_TRACK"', '"AUTH_CONFIRM"', '"AUTH_CHECK_CALL"'):
    out.append(NL + f"===== AUTH OPERATION REFERENCES {token} =====")
    count = 0
    for source_path in files:
        try:
            source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(source_lines):
            if token in line:
                count += 1
                lo, hi = max(0, line_no-45), min(len(source_lines), line_no+65)
                out.append(f"--- {source_path}:{line_no+1} ---")
                out.extend(source_lines[lo:hi])
    out.append(f"REFERENCE COUNT: {count}")
# Find actual callsites by enum field references, not just enum string declarations.
for field_ref in ("Lf0d;->v:Lf0d;", "Lf0d;->l:Lf0d;", "Lf0d;->u:Lf0d;", "Lf0d;->I3:Lf0d;"):
    out.append(NL + f"===== AUTH ENUM CALLSITES {field_ref} =====")
    count = 0
    for source_path in files:
        try:
            source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(source_lines):
            if field_ref in line:
                count += 1
                lo, hi = max(0, line_no-50), min(len(source_lines), line_no+75)
                out.append(f"--- {source_path}:{line_no+1} ---")
                out.extend(source_lines[lo:hi])
    out.append(f"CALLSITE COUNT: {count}")
# Resolve AUTH_CREATE_TRACK request construction and all qdc constructors.
for token in ("Lqdc;-><init>()V", "Lqdc;-><init>(Lf0d;B)V", "new-instance Lqdc"):
    out.append(NL + f"===== TRACK REQUEST CONSTRUCTION {token} =====")
    count = 0
    for source_path in files:
        try:
            source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(source_lines):
            if token in line:
                count += 1
                lo, hi = max(0, line_no-65), min(len(source_lines), line_no+100)
                out.append(f"--- {source_path}:{line_no+1} ---")
                out.extend(source_lines[lo:hi])
    out.append(f"REFERENCE COUNT: {count}")
# Trace phone-auth START_AUTH / RESEND request constructor and callers.
for token in ("Ljg0;-><init>(IILjava/lang/String;[B)V", "Ljg0;"):
    out.append(NL + f"===== PHONE AUTH REQUEST CALLSITES {token} =====")
    count = 0
    for source_path in files:
        try:
            source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(source_lines):
            if token in line and not source_path.name == "jg0.smali":
                count += 1
                lo, hi = max(0, line_no-65), min(len(source_lines), line_no+95)
                out.append(f"--- {source_path}:{line_no+1} ---")
                out.extend(source_lines[lo:hi])
    out.append(f"CALLSITE COUNT: {count}")
# Full request/response and crypto context for AUTH_REQUEST.
for class_path in (
    ROOT / "smali_classes3/lg0.smali",
    ROOT / "smali_classes3/jg0.smali",
    ROOT / "smali_classes3/ng0.smali",
    ROOT / "smali_classes2/gf0.smali",
    ROOT / "smali_classes2/llz8.smali",
    ROOT / "smali_classes2/qzb.smali",
):
    out.append(NL + f"===== PHONE AUTH SUPPORT CLASS {class_path} =====")
    if class_path.is_file():
        out.append(class_path.read_text(encoding="utf-8", errors="replace"))
    else:
        out.append("FILE NOT FOUND")
# Resolve actual obfuscated descriptors used by the phone-auth transport.
for class_name in ("ng0", "gf0", "llz8", "qzb", "c", "lg0", "lgc", "lgc"):
    descriptor = "L" + class_name + ";"
    for candidate in files:
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        first = next((line.strip() for line in content.splitlines() if line.startswith(".class ")), "")
        if first.endswith(descriptor):
            out.append(NL + f"===== RESOLVED PHONE AUTH CLASS {descriptor} ({candidate}) =====")
            out.append(content)
            break
for token in ("Llg0;-><init>(Ljava/lang/Object;Ljava/lang/String;ILzw4;B)V", "Llg0;-><init>(Lng0;Ljava/lang/String;ILzw4;B)V"):
    out.append(NL + f"===== PHONE AUTH COROUTINE CALLSITES {token} =====")
    count = 0
    for source_path in files:
        try:
            source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(source_lines):
            if token in line:
                count += 1
                lo, hi = max(0, line_no-55), min(len(source_lines), line_no+85)
                out.append(f"--- {source_path}:{line_no+1} ---")
                out.extend(source_lines[lo:hi])
    out.append(f"CALLSITE COUNT: {count}")
# Trace the use case entry point which triggers AUTH_REQUEST.
for token in ("Lng0;->a(Ljava/lang/String;ILkfi;)Ljava/lang/Object;", "new-instance Lng0", "Llg0;-><init>(Ljava/lang/Object;Ljava/lang/String;ILzw4;B)V"):
    out.append(NL + f"===== AUTH REQUEST ENTRY CALLSITES {token} =====")
    count = 0
    for source_path in files:
        try:
            source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(source_lines):
            if token in line:
                count += 1
                lo, hi = max(0, line_no-70), min(len(source_lines), line_no+100)
                out.append(f"--- {source_path}:{line_no+1} ---")
                out.extend(source_lines[lo:hi])
    out.append(f"CALLSITE COUNT: {count}")
FOCUSED_OUT.write_text(NL.join(out) + NL, encoding="utf-8")
print(f"SMS_AUTH_FOCUSED_TRACE: {FOCUSED_OUT} ({FOCUSED_OUT.stat().st_size} bytes)")
