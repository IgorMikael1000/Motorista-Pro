import os
import shutil
import subprocess
import sys

def run(cmd):
    try:
        # Roda comando e captura saída
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return None

def main():
    print("🚀 INICIANDO MIGRAÇÃO LIMPA (FRESH START)...")
    print("Este script vai reiniciar o Git do zero para eliminar erros de histórico e permissões.\n")

    repo_url = "https://github.com/IgorMikael1000/Motorista-Pro.git"
    
    # 1. REMOVER PASTAS PROBLEMÁTICAS
    print("🧹 Limpando configurações antigas...")
    
    # Remove .git (Histórico antigo que causa conflito)
    if os.path.exists(".git"):
        shutil.rmtree(".git")
        print("   -> Histórico Git antigo (.git) removido.")
    
    # Remove .github (Workflows ocultos que bloqueiam o push)
    if os.path.exists(".github"):
        shutil.rmtree(".github")
        print("   -> Pasta oculta de workflows (.github) removida.")

    # 2. TRATAR ARQUIVOS DE BLOQUEIO (Segurança)
    print("\n🛡️  Verificando arquivos bloqueados pelo GitHub...")
    sensitive_files = ["motorista.jks", "app/motorista.jks", "google-services.json"]
    backup_dir = "../backup_segredos"
    
    if not os.path.exists(backup_dir): os.makedirs(backup_dir)

    for file_path in sensitive_files:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            dest = os.path.join(backup_dir, file_name)
            # Move o arquivo para fora
            shutil.move(file_path, dest)
            print(f"   -> '{file_path}' movido para '{backup_dir}' (Segurança).")
            print("      (Você deve colocar este arquivo manualmente no servidor ou via Upload seguro depois)")

    # 3. CRIAR GITIGNORE
    with open(".gitignore", "w") as f:
        f.write("*.jks\n*.keystore\n.env\n__pycache__/\n*.pyc\n.DS_Store\n")

    # 4. INICIAR NOVO REPOSITÓRIO
    print("\n✨ Iniciando novo repositório limpo...")
    run("git init")
    
    # Configura user genérico para evitar erro de email privado
    run('git config user.email "deploy@motoristapro.app"')
    run('git config user.name "Migracao Script"')
    
    run("git branch -m main")
    run("git add .")
    run('git commit -m "Versao Estavel: Migracao de Conta"')
    
    print(f"🔗 Conectando ao remoto: {repo_url}")
    run(f"git remote add origin {repo_url}")

    # 5. ENVIAR
    print("\n🚀 ENVIANDO CÓDIGO...")
    # Usa --force para garantir que sobrescreva qualquer lixo no remoto
    result = run("git push -u origin main --force")

    if result:
        print("\n✅ SUCESSO TOTAL! Seu projeto foi enviado.")
        print("   Acesse: https://github.com/IgorMikael1000/Motorista-Pro")
    else:
        print("\n❌ FALHA NO ENVIO.")
        print("   Possível causa: Senha/Token incorreto no Termux.")
        print("   Tente rodar manualmente agora: git push -u origin main --force")

if __name__ == "__main__":
    main()


