import markdown

text = r"$\text{SO}_2$, $\text{O}_3$, $\text{NO}_x$"
html = markdown.markdown(text, extensions=["fenced_code", "tables"])
print(f"Original: {text}")
print(f"HTML: {html}")

text2 = r"$\text{SO}2$"
html2 = markdown.markdown(text2, extensions=["fenced_code", "tables"])
print(f"Original2: {text2}")
print(f"HTML2: {html2}")
