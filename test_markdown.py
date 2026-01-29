import markdown as md

text = r"양이온교환용량($\text{CEC}$)이 증가합니다."
html = md.markdown(text, extensions=['extra', 'nl2br', 'sane_lists'])
print(f"Original: {text}")
print(f"HTML: {html}")

text2 = r"**$\text{pH}$ 증가**"
html2 = md.markdown(text2, extensions=['extra', 'nl2br', 'sane_lists'])
print(f"Original2: {text2}")
print(f"HTML2: {html2}")
