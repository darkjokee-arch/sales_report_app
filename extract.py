try:
    from pypdf import PdfReader
    reader = PdfReader('gateway_swagger_guide.pdf')
    with open('pdf_content.txt', 'w', encoding='utf-8') as f:
        for page in reader.pages:
            f.write(page.extract_text() + '\n---PAGE---\n')
    print("Extraction to pdf_content.txt successful")
except Exception as e:
    print('Failed:', e)
