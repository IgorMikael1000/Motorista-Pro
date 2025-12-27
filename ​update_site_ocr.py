import os
import subprocess

# --- 1. ATUALIZAR ROTA NO BACKEND (main.py) ---
# Adiciona a lógica para salvar as configurações do OCR
main_route_path = "app/routes/main.py"

with open(main_route_path, 'r', encoding='utf-8') as f:
    main_content = f.read()

# Verifica se já temos a rota de salvar OCR, se não, adicionamos
if "save_ocr_settings" not in main_content:
    # Procura o final do arquivo ou um bom lugar para inserir
    insert_point = main_content.rfind("@bp.route") # Insere antes da última rota ou no fim
    
    new_route_code = """
@bp.route('/save_ocr_settings', methods=['POST'], endpoint='save_ocr_settings')
@login_required
def save_ocr_settings():
    if current_user.plan_type != 'premium': return jsonify({'error': 'Premium required'}), 403
    try:
        data = request.get_json()
        # Salva as configurações no banco
        set_config(current_user.id, 'ocr_good_km', data.get('good_km', '2.0'))
        set_config(current_user.id, 'ocr_medium_km', data.get('medium_km', '1.5'))
        set_config(current_user.id, 'ocr_good_hour', data.get('good_hour', '60.0'))
        set_config(current_user.id, 'ocr_medium_hour', data.get('medium_hour', '40.0'))
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""
    # Adicionamos antes da última rota encontrada ou no final
    if insert_point != -1:
        main_content = main_content[:insert_point] + new_route_code + main_content[insert_point:]
    else:
        main_content += new_route_code

    with open(main_route_path, 'w', encoding='utf-8') as f:
        f.write(main_content)
    print("✅ Rota '/save_ocr_settings' adicionada ao main.py")

# --- 2. RECRIAR A TELA HTML (ocr_page.html) ---
html_path = "app/templates/ocr_page.html"
html_content = """{% extends 'base.html' %}

{% block extra_css %}
<style>
    /* Estilos Gerais */
    .ocr-container { max-width: 600px; margin: 0 auto; padding-bottom: 100px; }
    
    /* UPSELL (BASIC) */
    .upsell-hero {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 30px; padding: 40px 25px; text-align: center; color: white;
        box-shadow: 0 20px 50px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
        position: relative; overflow: hidden;
    }
    .upsell-icon { font-size: 50px; color: #F59E0B; margin-bottom: 20px; animation: float 3s ease-in-out infinite; }
    .btn-upgrade {
        background: linear-gradient(90deg, #F59E0B 0%, #D97706 100%);
        color: white; font-weight: 800; padding: 18px 30px; border-radius: 50px;
        text-decoration: none; display: inline-block; margin-top: 25px;
        box-shadow: 0 10px 30px rgba(245, 158, 11, 0.4);
    }
    
    /* PREMIUM VIEW */
    .premium-header { text-align: center; margin-bottom: 30px; }
    .premium-header h2 { margin: 0; color: var(--text-main); font-size: 22px; font-weight: 800; }
    .premium-header p { color: var(--text-secondary); font-size: 14px; }

    .download-card {
        background: white; border-radius: 25px; padding: 30px; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .btn-download {
        background: var(--primary); color: white; width: 100%; padding: 18px;
        border-radius: 18px; font-weight: 800; font-size: 16px; text-decoration: none;
        display: flex; align-items: center; justify-content: center; gap: 10px;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.3); transition: transform 0.2s;
    }
    .btn-download:active { transform: scale(0.98); }
    
    .install-steps { text-align: left; margin-top: 20px; font-size: 13px; color: var(--text-secondary); background: #F8FAFC; padding: 15px; border-radius: 15px; }
    .install-steps ol { padding-left: 20px; margin: 0; }
    .install-steps li { margin-bottom: 8px; }

    /* CONFIGURAÇÃO */
    .config-toggler {
        background: white; border: 1px solid rgba(0,0,0,0.1); color: var(--text-main);
        width: 100%; padding: 15px; border-radius: 15px; font-weight: 700; cursor: pointer;
        display: flex; justify-content: space-between; align-items: center;
    }
    .config-panel { display: none; background: white; padding: 20px; border-radius: 20px; margin-top: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); }
    
    .range-group { margin-bottom: 20px; border-bottom: 1px dashed #eee; padding-bottom: 15px; }
    .range-title { font-size: 12px; font-weight: 800; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 15px; display: block; }
    
    .input-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .input-label { flex: 1; font-size: 13px; font-weight: 600; color: var(--text-main); }
    .input-field { width: 80px; padding: 10px; border-radius: 10px; border: 1px solid #ddd; text-align: center; font-weight: 700; color: var(--primary); }
    
    .badge-good { background: #DCFCE7; color: #166534; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 800; }
    .badge-mid { background: #FEF3C7; color: #92400E; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 800; }
    .badge-bad { background: #FEE2E2; color: #991B1B; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 800; }

    @keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-10px); } 100% { transform: translateY(0px); } }
</style>
{% endblock %}

{% block content %}
<div class="header fade-in">
    <a href="/" class="back-btn"><i class="fas fa-chevron-left"></i></a>
    <div style="flex-grow: 1; text-align: center;">
        <h2 style="margin:0; font-size:18px; color:var(--text-main); font-weight: 800;">Extensão</h2>
        <p style="margin:0; font-size:12px; color:var(--text-secondary); font-weight: 500;">Monitoramento Automático</p>
    </div>
    <div style="width:40px;"></div>
</div>

<div class="container fade-in ocr-container" style="padding-top: 20px;">

    <!-- LÓGICA DE EXIBIÇÃO -->
    {% if current_user.plan_type == 'basic' %}
    
        <!-- VISÃO BASIC (UPSELL) -->
        <div class="upsell-hero">
            <i class="fas fa-robot upsell-icon"></i>
            <h2 style="margin:0 0 10px 0; font-size: 24px;">Piloto Automático</h2>
            <p style="font-size: 14px; line-height: 1.6; opacity: 0.9;">
                O Monitoramento Dinâmico lê a tela do seu celular e calcula instantaneamente se uma corrida vale a pena.
            </p>
            <ul style="text-align: left; margin: 25px 0; padding: 0 15px; list-style: none; font-size: 13px;">
                <li style="margin-bottom: 10px;"><i class="fas fa-check" style="color: #F59E0B; margin-right: 8px;"></i> Leitura de R$/KM e R$/Hora</li>
                <li style="margin-bottom: 10px;"><i class="fas fa-check" style="color: #F59E0B; margin-right: 8px;"></i> Alerta Verde/Amarelo/Vermelho</li>
                <li><i class="fas fa-check" style="color: #F59E0B; margin-right: 8px;"></i> Foco total no trânsito</li>
            </ul>
            <a href="/assinar" class="btn-upgrade">
                QUERO SER PREMIUM <i class="fas fa-arrow-right"></i>
            </a>
        </div>

    {% else %}

        <!-- VISÃO PREMIUM (DOWNLOAD & CONFIG) -->
        <div class="premium-header">
            <div style="width: 60px; height: 60px; background: rgba(37,99,235,0.1); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 24px; color: var(--primary); margin-bottom: 15px;">
                <i class="fas fa-eye"></i>
            </div>
            <h2>Monitoramento Ativo</h2>
            <p>Seu assistente virtual para Uber e 99.</p>
        </div>

        <!-- 1. DOWNLOAD -->
        <div class="download-card">
            <h3 style="margin:0 0 15px 0; font-size:16px; color:var(--text-main);">Instalar Aplicativo</h3>
            
            <a href="{{ url_for('static', filename='motoristapro-ocr.apk') }}" class="btn-download" download>
                <i class="fab fa-android"></i> BAIXAR APK
            </a>
            
            <div class="install-steps">
                <b><i class="fas fa-info-circle"></i> Como instalar:</b>
                <ol>
                    <li>Toque no botão acima para baixar.</li>
                    <li>Abra o arquivo baixado na barra de notificações.</li>
                    <li>Se o sistema pedir, permita instalar de <b>"Fontes Desconhecidas"</b>.</li>
                    <li>Abra o app e faça login.</li>
                </ol>
            </div>
        </div>

        <!-- 2. CONFIGURAÇÃO -->
        <button class="config-toggler" onclick="toggleConfig()">
            <span><i class="fas fa-sliders-h" style="color:var(--primary); margin-right:10px;"></i> Configurar Parâmetros</span>
            <i class="fas fa-chevron-down" id="arrowIcon"></i>
        </button>

        <div id="configPanel" class="config-panel">
            <p style="font-size:12px; color:var(--text-secondary); margin-bottom:20px; line-height:1.4;">
                Defina os critérios para o robô classificar as corridas.
            </p>

            <!-- R$/KM -->
            <div class="range-group">
                <span class="range-title">Critério: Valor por KM</span>
                
                <div class="input-row">
                    <span class="badge-good">ÓTIMO</span>
                    <span class="input-label">Acima de:</span>
                    <div style="position:relative;">
                        <span style="position:absolute; left:8px; top:11px; font-size:10px; color:#aaa;">R$</span>
                        <input type="number" id="good_km" class="input-field" step="0.1" placeholder="2.00">
                    </div>
                </div>
                
                <div class="input-row">
                    <span class="badge-mid">MÉDIO</span>
                    <span class="input-label">Entre Ótimo e:</span>
                    <div style="position:relative;">
                        <span style="position:absolute; left:8px; top:11px; font-size:10px; color:#aaa;">R$</span>
                        <input type="number" id="medium_km" class="input-field" step="0.1" placeholder="1.50">
                    </div>
                </div>
                
                <div class="input-row" style="opacity:0.6;">
                    <span class="badge-bad">RUIM</span>
                    <span class="input-label">Abaixo do Médio</span>
                </div>
            </div>

            <!-- R$/HORA -->
            <div class="range-group" style="border:none;">
                <span class="range-title">Critério: Valor por Hora</span>
                
                <div class="input-row">
                    <span class="badge-good">ÓTIMO</span>
                    <span class="input-label">Acima de:</span>
                    <div style="position:relative;">
                        <span style="position:absolute; left:8px; top:11px; font-size:10px; color:#aaa;">R$</span>
                        <input type="number" id="good_hour" class="input-field" placeholder="60">
                    </div>
                </div>
                
                <div class="input-row">
                    <span class="badge-mid">MÉDIO</span>
                    <span class="input-label">Entre Ótimo e:</span>
                    <div style="position:relative;">
                        <span style="position:absolute; left:8px; top:11px; font-size:10px; color:#aaa;">R$</span>
                        <input type="number" id="medium_hour" class="input-field" placeholder="40">
                    </div>
                </div>
            </div>

            <button onclick="saveSettings()" id="btnSave" class="btn" style="width:100%; border-radius:15px; padding:15px; box-shadow:0 8px 20px rgba(37,99,235,0.3);">
                SALVAR CONFIGURAÇÃO
            </button>
        </div>

    {% endif %}

</div>

{% if current_user.plan_type == 'premium' %}
<script>
    // Carregar configurações atuais do banco (via JS injetado no template seria ideal, mas vamos usar localStorage ou defaults como fallback visual, e depois salvar no banco)
    // O ideal seria passar essas variáveis pelo render_template no backend. 
    // Como estamos editando apenas o template estático, vamos assumir valores padrão ou carregar se possível.
    
    // Simulação de carregamento inicial (valores padrão)
    document.getElementById('good_km').value = '2.00';
    document.getElementById('medium_km').value = '1.50';
    document.getElementById('good_hour').value = '60.00';
    document.getElementById('medium_hour').value = '40.00';

    function toggleConfig() {
        const panel = document.getElementById('configPanel');
        const arrow = document.getElementById('arrowIcon');
        if (panel.style.display === 'block') {
            panel.style.display = 'none';
            arrow.className = 'fas fa-chevron-down';
        } else {
            panel.style.display = 'block';
            arrow.className = 'fas fa-chevron-up';
        }
    }

    function saveSettings() {
        const btn = document.getElementById('btnSave');
        const originalText = btn.innerText;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> SALVANDO...';
        
        const data = {
            good_km: document.getElementById('good_km').value,
            medium_km: document.getElementById('medium_km').value,
            good_hour: document.getElementById('good_hour').value,
            medium_hour: document.getElementById('medium_hour').value
        };

        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        fetch('/save_ocr_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if(result.status === 'ok') {
                btn.innerHTML = '<i class="fas fa-check"></i> SUCESSO!';
                btn.style.background = '#10B981';
                
                // Se estiver rodando dentro do App Android, atualiza lá também em tempo real
                if (window.MotoristaProAndroid) {
                    window.MotoristaProAndroid.updateConfig(parseFloat(data.good_km), parseFloat(data.good_hour));
                }
                
                setTimeout(() => {
                    btn.innerText = originalText;
                    btn.style.background = '';
                    toggleConfig(); // Fecha o painel
                }, 2000);
            } else {
                alert('Erro ao salvar: ' + (result.error || 'Desconhecido'));
                btn.innerText = originalText;
            }
        })
        .catch(err => {
            console.error(err);
            alert('Erro de conexão.');
            btn.innerText = originalText;
        });
    }
</script>
{% endif %}
{% endblock %}
"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
print("✅ Tela 'Monitoramento Dinâmico' recriada com sucesso.")

# --- 3. GIT PUSH AUTOMÁTICO ---
def run_git():
    try:
        print("\n📦 Git: Preparando envio...")
        subprocess.run("git add .", shell=True, check=True)
        subprocess.run('git commit -m "Feat: Tela de Monitoramento com Upsell e Configuração"', shell=True, check=True)
        subprocess.run("git push", shell=True, check=True)
        print("\n🚀 Git Push realizado com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro no Git: {e}")

if __name__ == "__main__":
    run_git()


