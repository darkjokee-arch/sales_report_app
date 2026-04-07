import pdfplumber
import sys

pdf_path = r"C:\Users\hspt8\Desktop\S22C-6e26031810520.pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- PAGE {i+1} ---")
            
            # Try extracting tables first
            tables = page.extract_tables()
            if tables:
                print("Found Tables:")
                for r in tables[0]:
                    print(r)
            else:
                print("Found Text:")
                print(page.extract_text())
                
except Exception as e:
    print(f"Error reading PDF: {e}")
