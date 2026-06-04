from flask import Flask, request, send_file
from flask_cors import CORS
import fitz  # PyMuPDF
from ebooklib import epub
from pdf2docx import Converter
import os
import tempfile

app = Flask(__name__)
CORS(app)

# ==========================================
# ROTA 1: PDF para EPUB
# ==========================================
@app.route('/convert/epub', methods=['POST'])
def convert_pdf_to_epub():
    if 'file' not in request.files:
        return "Nenhum arquivo enviado", 400
        
    pdf_file = request.files['file']
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf_file.save(temp_pdf.name)
        pdf_path = temp_pdf.name

    epub_path = pdf_path.replace('.pdf', '.epub')
    book = epub.EpubBook()
    book.set_title('Documento Convertido - VertoryHub')
    book.set_language('pt')

    doc = fitz.open(pdf_path)
    chapters = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("html")
        c = epub.EpubHtml(title=f'Página {page_num + 1}', file_name=f'page_{page_num}.xhtml', lang='pt')
        c.content = f'<html><body>{text}</body></html>'
        book.add_item(c)
        chapters.append(c)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters

    epub.write_epub(epub_path, book, {})
    doc.close()
    
    return send_file(epub_path, as_attachment=True, download_name="convertido.epub", mimetype='application/epub+zip')

# ==========================================
# ROTA 2: PDF para WORD (.docx)
# ==========================================
@app.route('/convert/word', methods=['POST'])
def convert_pdf_to_word():
    if 'file' not in request.files:
        return "Nenhum arquivo enviado", 400
        
    pdf_file = request.files['file']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf_file.save(temp_pdf.name)
        pdf_path = temp_pdf.name

    word_path = pdf_path.replace('.pdf', '.docx')
    
    # Motor de conversão para manter o layout do Word
    cv = Converter(pdf_path)
    cv.convert(word_path)
    cv.close()
    
    return send_file(word_path, as_attachment=True, download_name="convertido.docx", mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# ==========================================
# ROTA 3: PDF para TXT (Texto Limpo)
# ==========================================
@app.route('/convert/txt', methods=['POST'])
def convert_pdf_to_txt():
    if 'file' not in request.files:
        return "Nenhum arquivo enviado", 400
        
    pdf_file = request.files['file']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf_file.save(temp_pdf.name)
        pdf_path = temp_pdf.name

    txt_path = pdf_path.replace('.pdf', '.txt')
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    with open(txt_path, "w", encoding="utf-8") as text_file:
        text_file.write(text)
        
    return send_file(txt_path, as_attachment=True, download_name="convertido.txt", mimetype='text/plain')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
