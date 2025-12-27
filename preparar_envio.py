import os
import sqlite3

# Nome do arquivo de saída
OUTPUT_FILE = "PROJETO_COMPLETO.txt"

# Extensões que queremos ler
TEXT_EXTENSIONS = {'.py', '.html', '.css', '.js', '.txt', '.json', '.md'}

def get_sqlite_schema(db_path):
    """Tenta extrair o esquema (CREATE TABLE) de um arquivo .db"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_text = f"\n--- ESQUEMA DO BANCO DE DADOS ({os.path.basename(db_path)}) ---\n"
        if not tables:
            schema_text += "Nenhuma tabela encontrada ou banco vazio.\n"
        
        for table in tables:
            if table[0]: # Ignora tabelas sem SQL (ex: sqlite_sequence as vezes)
                schema_text += table[0] + ";\n"
        
        conn.close()
        return schema_text + "------------------------------------------\n\n"
    except Exception as e:
        return f"\n[ERRO AO LER BANCO DE DADOS {db_path}: {e}]\n\n"

def merge_files():
    project_dir = os.getcwd()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write(f"Projeto exportado de: {project_dir}\n")
        outfile.write("="*50 + "\n\n")

        # Percorre todos os arquivos e pastas
        for root, dirs, files in os.walk(project_dir):
            # Ignorar pastas comuns que não precisamos
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            if '.git' in dirs:
                dirs.remove('.git')
            if 'venv' in dirs:
                dirs.remove('venv')

            for file in files:
                if file == OUTPUT_FILE or file == "preparar_envio.py":
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, project_dir)
                _, ext = os.path.splitext(file)

                print(f"Processando: {relative_path}")

                # Se for arquivo de texto/código
                if ext in TEXT_EXTENSIONS:
                    outfile.write(f"\n{'='*20} INICIO ARQUIVO: {relative_path} {'='*20}\n")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"[Erro ao ler arquivo: {e}]")
                    outfile.write(f"\n{'='*20} FIM ARQUIVO: {relative_path} {'='*20}\n")
                
                # Se for banco de dados SQLite, tenta pegar o esquema
                elif ext == '.db':
                    outfile.write(get_sqlite_schema(file_path))

    print(f"\nConcluído! Todos os arquivos foram salvos em: {OUTPUT_FILE}")
    print("Agora você pode enviar esse arquivo único para o Gemini.")

if __name__ == "__main__":
    merge_files()


