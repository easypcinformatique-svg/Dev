import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

keep = ["Coca-Cola", "Fanta", "Ice Tea"]
pattern = r"\{name:'([^']*)',price:[0-9.]+\}"

for m in list(re.finditer(pattern, c)):
    full = m.group(0)
    name = m.group(1)
    if not any(k.lower() in name.lower() for k in keep):
        c = c.replace(full + ",", "")
        c = c.replace("," + full, "")
        c = c.replace(full, "")
        print("Removed: " + name)
    else:
        print("Kept: " + name)

while ",," in c:
    c = c.replace(",,", ",")
c = c.replace(",]", "]")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Done!")
