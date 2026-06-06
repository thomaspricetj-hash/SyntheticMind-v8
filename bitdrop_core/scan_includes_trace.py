import os
import re

ROOT = r"C:\Users\thomas price\Desktop\bitdrop\include"
include_re = re.compile(r'#include\s+"(.+)"')

def resolve(path, inc):
    # Normalize and join include path
    full = os.path.join(os.path.dirname(path), inc)
    if os.path.exists(full):
        return os.path.abspath(full)
    # Try include root
    full = os.path.join(ROOT, inc)
    if os.path.exists(full):
        return os.path.abspath(full)
    return None

def trace(path, stack):
    if path in stack:
        print("\n🔥 INCLUDE LOOP FOUND:")
        for f in stack:
            print("   " + f)
        print("   " + path)
        return True

    stack.append(path)

    with open(path, "r", errors="ignore") as f:
        for line in f:
            m = include_re.search(line)
            if not m:
                continue

            inc = m.group(1)
            target = resolve(path, inc)

            if target:
                print(f"[TRACE] {path} includes {target} via line: {line.strip()}")

                if trace(target, stack):
                    return True

    stack.pop()
    return False

print("Tracing include recursion...\n")

start = os.path.join(ROOT, "bitdrop_cache_manager.h")
trace(start, [])

