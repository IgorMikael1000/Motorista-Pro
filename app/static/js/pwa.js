// Variáveis Globais
let deferredPrompt;
const btnInstallId = 'btnInstall';

// 1. Captura o evento de instalação (Android/Chrome)
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('PWA: Evento de instalação capturado!');
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showInstallButton);
    } else {
        showInstallButton();
    }
});

// 2. Inicialização
document.addEventListener('DOMContentLoaded', () => {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('SW Registado'))
            .catch(err => console.error('Erro SW:', err));
    }

    checkInstallState();
});

function checkInstallState() {
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    
    // Se já estiver instalado, esconde o botão
    if (isStandalone) {
        const btn = document.getElementById(btnInstallId);
        if(btn) btn.style.display = 'none';
        return;
    }
    
    // Se o evento foi capturado antes do DOM carregar
    if (deferredPrompt) {
        showInstallButton();
    }
}

function showInstallButton() {
    const btn = document.getElementById(btnInstallId);
    if (btn) {
        // Exibe como flex para alinhar ícone e texto
        btn.style.display = 'flex'; 
    }
}

// 3. Ação do Botão
function installApp(e) {
    if (e) e.preventDefault();
    
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('PWA: Instalação aceita');
                const btn = document.getElementById(btnInstallId);
                if(btn) btn.style.display = 'none';
            } else {
                console.log('PWA: Instalação recusada');
            }
            deferredPrompt = null;
        });
    } else {
        console.log('PWA: Instalação não disponível neste navegador/dispositivo.');
    }
}



