document.addEventListener('DOMContentLoaded', () => {
    // Atualizei a chave para forçar o tour a aparecer nesta nova versão
    const tourKey = 'motorista_pro_tour_v14_final';
    const urlParams = new URLSearchParams(window.location.search);
    
    // Verifica se deve rodar o tour:
    // 1. Se vier do onboarding (?start_tour=true)
    // 2. OU se a chave não existir no localStorage
    const shouldRun = urlParams.get('start_tour') === 'true' || !localStorage.getItem(tourKey);

    if (shouldRun) {
        // Limpa a URL
        if(urlParams.get('start_tour')) {
            const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
            window.history.replaceState({path:newUrl},'',newUrl);
        }

        // Aguarda a biblioteca carregar
        const checkDriver = setInterval(() => {
            if (window.driver && window.driver.driver) {
                clearInterval(checkDriver);
                initTour();
            }
        }, 200);
        
        setTimeout(() => clearInterval(checkDriver), 5000);
    }

    function initTour() {
        const driver = window.driver.driver;
        
        const driverObj = driver({
            showProgress: true,
            nextBtnText: 'Próximo',
            prevBtnText: 'Voltar',
            doneBtnText: 'Começar!',
            steps: [
                { 
                    element: '.header', 
                    popover: { 
                        title: 'Seu Painel de Comando', 
                        description: 'Aqui vê o seu perfil e as notificações importantes.' 
                    } 
                },
                { 
                    element: '.filter-group', 
                    popover: { 
                        title: 'Filtros de Tempo', 
                        description: 'Alterne entre Dia, Semana e Mês para ver os seus ganhos.' 
                    } 
                },
                { 
                    element: '.hero-clickable', 
                    popover: { 
                        title: 'Lucro Real', 
                        description: 'O valor que realmente sobra no bolso após descontar a manutenção.' 
                    } 
                },
                { 
                    element: '.nav-fab-menu', 
                    popover: { 
                        title: 'Adicionar Dia', 
                        description: 'Toque no botão + para lançar os seus ganhos e despesas diários.' 
                    } 
                },
                { 
                    element: '.floating-nav', 
                    popover: { 
                        title: 'Menu Principal', 
                        description: 'Aceda a Relatórios, Calculadora, Manutenção e Agenda por aqui.' 
                    } 
                }
            ],
            onDestroyed: () => {
                localStorage.setItem(tourKey, 'true');
            }
        });

        // Pequeno delay para garantir que o DOM renderizou
        setTimeout(() => driverObj.drive(), 800);
    }
});



