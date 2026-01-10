import re
import pandas as pd
import os

def extract_index():
    input_file = '병리학index.txt'
    output_file = 'pathology_index.xlsx'
    
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex pattern:
    # 1. Term: Any char that is NOT a digit (to stop at the page number).
    #    We'll clean up newlines later.
    # 2. Page: Digits, commas, and spaces, but must start and end with digit.
    #    e.g., "56", "292,299,307"
    
    # Using finditer to handle it sequentially
    # We treat headers like 'ㄱ', '찾아보기' as terms initially, will filter by length/content.
    
    # Improved Regex:
    # We want to capture the text preceding a number group.
    # But handling the concatenated case "Term 123Term 456"
    
    pattern = re.compile(r'([^\d]+?)\s+(\d+(?:[\s,]*\d+)*)')
    
    matches = pattern.findall(content)
    
    data = []
    
    for term_raw, page_raw in matches:
        # Clean term
        term = term_raw.strip()
        
        # If term contains newlines, it might be capturing previous lines.
        # usually the term is just the last part after the last newline.
        # e.g., "\n\nTerm" -> "Term"
        if '\n' in term:
            term = term.split('\n')[-1].strip()
            
        # Filter junk
        if not term:
            continue
        if len(term) == 1 and not term.encode().isalpha(): # Skip headers like ㄱ, ㄴ, A, B (if single char)
             # keeping English single chars A, B? Usually headers.
             # Korean headers are single char.
             continue
             
        # Clean page numbers
        # Remove spaces around commas
        page = re.sub(r'\s*,\s*', ',', page_raw).strip()
        
        data.append({'Term': term, 'Page': page})
        
    df = pd.DataFrame(data)
    
    # Filter out likely noise
    # e.g., "INDEX"
    df = df[df['Term'] != 'INDEX']
    df = df[df['Term'] != '찾아보기']
    
    print(f"Extracted {len(df)} terms.")
    print(df.head(10))
    
    df.to_excel(output_file, index=False)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    extract_index()
