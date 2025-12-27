import os

# Configurações para Render Free Tier (512MB RAM)
# Fórmula segura: (2 x NUM_CORES) + 1, mas limitado pela RAM
# 2 workers é o ideal para 512MB. Mais que isso arrisca "Out of Memory"
workers = 2 

# Threads ajudam a processar requisições IO-bound (banco de dados)
# sem consumir tanta memória quanto processos separados.
threads = 4 

worker_class = 'gthread' 

# Timeout aumentado para lidar com "cold starts" do Render (hibernação)
timeout = 120 
keepalive = 5

# Logs direcionados para a saída padrão (stdout) para o painel do Render capturar
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Preload para carregar a app antes de fazer o fork dos workers (economiza RAM)
preload_app = True

def on_starting(server):
    print("🚀 Gunicorn iniciando: Configuração Otimizada para Render (Low RAM)")


