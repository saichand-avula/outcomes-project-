"""Authoring helper: tag nurse phone read-back lines, then fill turns. Usage: postfix.py file..."""
import subprocess, sys
for p in sys.argv[1:]:
    s = open(p).read(); out = []
    for line in s.split('\n'):
        if line.startswith('  Nurse ->') and 'five five five' in line and '||' not in line:
            line += ' || callback_phone'
        out.append(line)
    open(p, 'w').write('\n'.join(out))
subprocess.run([sys.executable, 'code/data/fill_turns.py', '--force', *sys.argv[1:]])
