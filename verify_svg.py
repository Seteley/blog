import re
path = "D:/26-1/Janjachi/blog/src/pages/articulos/articulo-1.md"
content = open(path, "rb").read().decode("utf-8")
svgs = re.findall(r"<svg[^>]*>.*?</svg>", content, re.DOTALL)
print(f"SVG blocks: {len(svgs)}")
for i, svg in enumerate(svgs):
    blank_lines = sum(1 for l in svg.split(chr(10)) if l.strip() == "")
    comments = len(re.findall(r"<!--", svg))
    print(f"  SVG {i+1}: blank_lines={blank_lines}, comments={comments}")
fences = content.count("```svg")
print(f"Remaining fences: {fences}")
