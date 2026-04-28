#!/usr/bin/env python3
"""
mysql CLI wrapper: runs mysql via docker exec.
Translates host port 3307 to container port 3306.
"""
import subprocess
import sys

args = sys.argv[1:]
# Translate host port to container port when running inside docker exec
translated = []
for a in args:
    if a.startswith("-P"):
        a = "-P3306"
    translated.append(a)

cmd = ["docker", "exec", "-i", "chatbi-demo-mysql", "mysql"] + translated
proc = subprocess.run(cmd)
sys.exit(proc.returncode)
