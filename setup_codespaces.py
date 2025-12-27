import os
import json

def create_file(path, content):
    try:
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Criado: {path}")
    except Exception as e:
        print(f"❌ Erro ao criar {path}: {e}")

def main():
    print("🚀 CONFIGURANDO AMBIENTE GITHUB CODESPACES...\n")

    # 1. Configuração do DevContainer (O cérebro do Codespace)
    # Define Python 3.10, instala Postgres (opcional), e extensões do VS Code
    devcontainer_content = {
        "name": "Motorista Pro Dev",
        "image": "mcr.microsoft.com/devcontainers/python:3.10",
        "features": {
            "ghcr.io/devcontainers/features/github-cli:1": {},
            "ghcr.io/devcontainers/features/sshd:1": {},
            "ghcr.io/devcontainers/features/postgres:1": {
                "version": "latest",
                "username": "postgres",
                "password": "password",
                "dbName": "motorista_dev"
            }
        },
        "customizations": {
            "vscode": {
                "settings": {
                    "python.defaultInterpreterPath": "/usr/local/bin/python"
                },
                "extensions": [
                    "ms-python.python",
                    "ms-python.vscode-pylance",
                    "donjayamanne.python-extension-pack",
                    "formulahendry.code-runner",
                    "mtxr.sqltools",
                    "mtxr.sqltools-driver-pg",
                    "mtxr.sqltools-driver-sqlite"
                ]
            }
        },
        "forwardPorts": [5000],
        "postCreateCommand": "pip install --upgrade pip && pip install -r requirements.txt && python -c 'from app import db, create_app; app=create_app(); app.app_context().push(); db.create_all(); print(\"Banco de dados inicializado!\")'",
        "remoteUser": "vscode"
    }

    create_file(".devcontainer/devcontainer.json", json.dumps(devcontainer_content, indent=4))

    # 2. Criar um .env de exemplo (para você saber o que preencher no Codespace)
    env_example = """# CONFIGURAÇÕES DO MOTORISTA PRO (CODESPACE)
# Copie estes valores para os 'Secrets' do Codespaces no GitHub

FLASK_APP=run.py
FLASK_DEBUG=1
SECRET_KEY=chave_dev_codespace

# Banco de Dados (Opcional - se vazio usa SQLite local)
# DATABASE_URL=postgresql://postgres:password@localhost:5432/motorista_dev

# Chaves de API (Preencher no GitHub)
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
MP_ACCESS_TOKEN=
FIREBASE_CREDENTIALS=
FIREBASE_CONFIG_FRONTEND=
"""
    create_file(".env.example", env_example)

    print("\n🎉 Configuração concluída!")
    print("------------------------------------------------")
    print("PRÓXIMOS PASSOS OBRIGATÓRIOS:")
    print("1. Envie estes novos arquivos para o GitHub:")
    print("   git add .devcontainer/devcontainer.json .env.example")
    print("   git commit -m 'Configurando GitHub Codespaces'")
    print("   git push origin main")
    print("\n2. No site do GitHub:")
    print("   - Vá no seu repositório.")
    print("   - Clique no botão verde '<> Code'.")
    print("   - Escolha a aba 'Codespaces' e clique em 'Create codespace on main'.")
    print("------------------------------------------------")

if __name__ == "__main__":
    main()


