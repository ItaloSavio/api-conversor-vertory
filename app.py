from flask import Flask, request, send_file
from flask_cors import CORS
import fitz  # PyMuPDF
from ebooklib import epub
import os
import tempfile

app = Flask(__name__)
CORS(app) # Permite que o seu site no Lovable acesse este servidor

@app.route('/convert', methods=['POST'])
def convert_pdf_to_epub():
    # Verifica se um arquivo foi enviado
    if 'file' not in request.files:
        return "Nenhum arquivo enviado", 400
        
    pdf_file = request.files['file']
    
    # Cria arquivos temporários para processar em segurança na nuvem
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf_file.save(temp_pdf.name)
        pdf_path = temp_pdf.name

    epub_path = pdf_path.replace('.pdf', '.epub')
    
    # Prepara a estrutura base do livro digital (EPUB)
    book = epub.EpubBook()
    book.set_title('Documento Convertido - VertoryHub')
    book.set_language('pt')

    # Abre o PDF usando a biblioteca PyMuPDF
    doc = fitz.open(pdf_path)
    chapters = []
    
    # Passa página por página extraindo o conteúdo
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("html") # Mantém formatações básicas de quebra de linha
        
        # Cria um capítulo no EPUB para cada página do PDF original
        c = epub.EpubHtml(title=f'Página {page_num + 1}', file_name=f'page_{page_num}.xhtml', lang='pt')
        c.content = f'<html><body>{text}</body></html>'
        book.add_item(c)
        chapters.append(c)

    # Monta o menu de navegação (obrigatório para EPUBs válidos)
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters

    # Salva e empacota o arquivo final
    epub.write_epub(epub_path, book, {})
    
    # Fecha o documento PDF original
    doc.close()
    
    # Devolve o arquivo EPUB pela internet direto para o usuário baixar
    return send_file(epub_path, as_attachment=True, download_name="convertido.epub", mimetype='application/epub+zip')

if __name__ == '__main__':
    # Roda o servidor na porta que o Render definir
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
