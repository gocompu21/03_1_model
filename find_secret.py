
filename = r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\chapter_2_3.html"
try:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start = 0
    count = 0
    while True:
        index = content.find("AIza", start)
        if index == -1:
            break
        
        count += 1
        # Find line number
        line_num = content.count('\n', 0, index) + 1
        
        # Checking context
        ctx_start = max(0, index - 20)
        ctx_end = min(len(content), index + 60)
        context_snippet = content[ctx_start:ctx_end]
        
        print(f"Match #{count}: Line {line_num}, Index {index}")
        print(f"Context: {context_snippet}")
        
        start = index + 4
        
    if count == 0:
        print("No matches found.")

except Exception as e:
    print(f"Error: {e}")
