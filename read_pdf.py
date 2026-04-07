import sys

file_path = 'gateway_swagger_guide.pdf'
text = ''

try:
    import fitz
    doc = fitz.open(file_path)
    for i in range(len(doc)):
        text += doc[i].get_text()
    print('PyMuPDF Success:\n', text[:10000])
    sys.exit(0)
except Exception as e:
    print('fitz failed:', e)

try:
    import PyPDF2
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for i in range(len(reader.pages)):
            text += reader.pages[i].extract_text()
        print('PyPDF2 Success:\n', text[:10000])
        sys.exit(0)
except Exception as e:
    print('PyPDF2 failed:', e)
