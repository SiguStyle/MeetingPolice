"""Generate .env.example from .env by stripping values."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = root / '.env'
dest = root / '.env.example'

lines = []
for line in src.read_text().splitlines():
    if line.startswith('#') or not line.strip():
        lines.append(line)
    elif '=' in line:
        key, _sep, _value = line.partition('=')
        lines.append(f"{key}=")
    else:
        lines.append(line)

dest.write_text('\n'.join(lines) + '\n')
print(f'Wrote template to {dest}')
