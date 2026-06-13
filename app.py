from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
from ebooklib import epub
import os
import tempfile
import cloudconvert

app = Flask(__name__)
CORS(app)

# ==========================================
# Configuração CloudConvert
# ==========================================
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiNTc2MTMyNTFjMzU3NDQwMmExM2RlYzk4MjM3YzdjYTY5Y2I0Y2MxNjJjZjU1ZjRmOTIwMWY0MTRhNzZlMjY1NTY0Mjc3YmJmZmEzYTljYmMiLCJpYXQiOjE3ODEzNzU2MzkuNTYyMTY2LCJuYmYiOjE3ODEzNzU2MzkuNTYyMTY3LCJleHAiOjQ5MzcwNDkyMzkuNTU1NzA3LCJzdWIiOiI3NTk2MTEzOCIsInNjb3BlcyI6WyJwcmVzZXQud3JpdGUiLCJwcmVzZXQucmVhZCIsIndlYmhvb2sud3JpdGUiLCJ3ZWJob29rLnJlYWQiLCJ0YXNrLndyaXRlIiwidGFzay5yZWFkIiwidXNlci5yZWFkIiwidXNlci53cml0ZSJdfQ.Aq1u9RzcrotHhuYgWlbE411giHB8Di1QNBVevDGhZkPH2yyGu71LLfeXDEKPalIpgKf1x2p_PQVC5lv90mOBUYo8317Sn_OQSLOvJoiDwLsATYyY4qcxJ23mUGK-eALZZN0eZKMO4-ytFgGDPSxgwSTajMcM-VwtSh0JqRP10sRqo96UBD-MVn0R00pb4F3V1MkJCjBUhc7qBeG5gdVJFlULSiV1nvHpg5Z2iyuDD2mJfZYAgpJXnqSnMnnuIeC3tUlkyej4ypd89LiJCeSdDDVTxtJtXi_6HgxlXovPgSBdI4OKjS-2J39vknTJ8n5aTErfKd2HexuB8184BWbXESajKMhJvBUqbuOhJCLxTR2U6GnjksqrcgZKpTov3Bgo4tnXl3r98MhvYJ5tGdjccuoR6Y_uYDxUhNiKHFHGXUNf8S1UrRmbYV6hSAUFZEyDuDrtBVgXEmdBXj-Hd2ZIKvONhqBYWmYcy3HuJr4c_VOuvq7_po1iG8m4kMaoiMxT7lpDsTAdR-oG7WC_wK_-ri0iV272_tr_8MIM_um_jl1SsFrjPI0BJ0k85bjS3qDz6I-Y7P4uYAcUWcGcIgia3YkKaYhdw-PXI3AeJBgA3p8bCAmZwoygvbRezZw79VCYrAbWL0HIQBQ_YVf4aTK29LwZzeGHz2rNCzYBRPeVNIQ"
cloudconvert.configure(api_key=API_KEY, sandbox=False)

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
# ROTA 2: PDF para WORD (.docx) - ROTEAMENTO INTELIGENTE (RENDER/CLOUD)
# ==========================================
@app.route('/convert/word', methods=['POST'])
def convert_pdf_to_word():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
        
    file = request.files['file']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        file.save(temp_pdf.name)
        temp_path = temp_pdf.name

    # 1. Verifica o tamanho do arquivo em Megabytes (MB)
    tamanho_mb = os.path.getsize(temp_path) / (1024 * 1024)
    print(f"Tamanho do arquivo recebido: {tamanho_mb:.2f} MB")

    # 2. Define o limite (em MB) para decidir quem vai processar
    LIMITE_MB = 3.0

    # 3. Função isolada para rodar a conversão localmente no Render
    def converter_via_render():
        from pdf2docx import Converter
        word_filename = f"convertido_{os.path.basename(temp_path)}.docx"
        word_path = f"/tmp/{word_filename}"
        
        cv = Converter(temp_path)
        cv.convert(word_path)
        cv.close()
        
        fallback_download_url = f"{request.host_url}download/{word_filename}"
        return jsonify({"success": True, "download_url": fallback_download_url, "engine": "render_local"}), 200

    try:
        # Se for menor que 3MB, usa o Render (Economiza cota do CloudConvert)
        if tamanho_mb <= LIMITE_MB:
            print("➡️ Arquivo LEVE detectado. Processando localmente no Render...")
            resultado = converter_via_render()
            os.remove(temp_path)
            return resultado
            
        # Se for maior que 3MB, manda pro CloudConvert (Evita travar o Render)
        else:
            print("➡️ Arquivo PESADO detectado. Enviando para o CloudConvert...")
            try:
                job = cloudconvert.Job.create(payload={
                    "tasks": {
                        "import-file": {"operation": "import/upload"},
                        "convert-file": {
                            "operation": "convert",
                            "input": "import-file",
                            "input_format": "pdf",
                            "output_format": "docx"
                        },
                        "export-file": {
                            "operation": "export/url",
                            "input": "convert-file"
                        }
                    }
                })

                upload_task = next(task for task in job['tasks'] if task['name'] == 'import-file')
                cloudconvert.Task.upload(file_name=temp_path, task=upload_task)

                job = cloudconvert.Job.wait(id=job['id'])

                export_task = next(task for task in job['tasks'] if task['name'] == 'export-file')
                download_url = export_task['result']['files'][0]['url']

                os.remove(temp_path)
                return jsonify({"success": True, "download_url": download_url, "engine": "cloudconvert"}), 200

            # Se o CloudConvert falhar (ou acabar o limite), tenta o Render como último recurso
            except Exception as cloud_err:
                print(f"⚠️ CloudConvert falhou ou sem limite: {str(cloud_err)}. Acionando Render por segurança...")
                resultado = converter_via_render()
                os.remove(temp_path)
                return resultado

    except Exception as fatal_err:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Erro fatal na conversão: {str(fatal_err)}"}), 500

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

# ==========================================
# ROTA EXTRA: Para o Render entregar o arquivo (Usado pela Rota 2)
# ==========================================
@app.route('/download/<filename>', methods=['GET'])
def download_local_file(filename):
    file_path = f"/tmp/{filename}"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name="VertoryHub_Convertido.docx")
    return jsonify({"error": "Arquivo expirou ou não existe"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
