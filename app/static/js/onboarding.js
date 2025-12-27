document.addEventListener('DOMContentLoaded', () => {
    
    // Configuração das Dicas por Página
    const ONBOARDING_STEPS = [
        {
            path: '/historico',
            key: 'seen_historico',
            icon: 'fas fa-book-open',
            title: 'Livro Caixa',
            text: 'Aqui fica o registo de todos os seus dias de trabalho. Pode tocar em qualquer cartão para <b>editar</b> ou <b>apagar</b> um lançamento.'
        },
        {
            path: '/agenda',
            key: 'seen_agenda',
            icon: 'far fa-calendar-alt',
            title: 'Agenda de Corridas',
            text: 'Organize corridas particulares. Defina horário, valor e endereço. Ao concluir, pode gerar um <b>Recibo Profissional (PDF)</b> para o passageiro.'
        },
        {
            path: '/adicionar',
            key: 'seen_adicionar',
            icon: 'fas fa-plus-circle',
            title: 'Fechar o Dia',
            text: 'Use esta tela ao final do turno. Lance o total ganho nos apps, a quilometragem e os gastos. O app calcula o lucro líquido automaticamente.'
        },
        {
            path: '/relatorios',
            key: 'seen_relatorios',
            icon: 'fas fa-chart-pie',
            title: 'Relatórios de Performance',
            text: 'Visão de águia. Analise gráficos de faturamento, compare o desempenho semanal ou mensal e exporte tudo para PDF (Premium).'
        },
        {
            path: '/manutencao',
            key: 'seen_manutencao',
            icon: 'fas fa-wrench',
            title: 'Manutenção Inteligente',
            text: 'Cadastre itens como Óleo ou Pneus. O app monitoriza a sua rodagem diária e avisa a data prevista da próxima troca automaticamente.'
        },
        {
            path: '/calculadora',
            key: 'seen_calculadora',
            icon: 'fas fa-calculator',
            title: 'Ferramentas Rápidas',
            text: '<b>Flex:</b> Saiba qual combustível compensa no posto.<br><b>Corrida:</b> Calcule o preço justo para cobrar em viagens particulares.'
        },
        {
            path: '/lucro_real',
            key: 'seen_lucro_real',
            icon: 'fas fa-chart-line',
            title: 'Lucro Real',
            text: 'A visão mais importante. Aqui descontamos o desgaste invisível do carro (pneus, óleo, mecânica) e custos fixos (IPVA/Seguro) para mostrar o <b>lucro verdadeiro</b>.'
        }
    ];

    const currentPath = window.location.pathname;

    // Procura se a página atual tem uma dica configurada
    const step = ONBOARDING_STEPS.find(s => currentPath.includes(s.path));

    if (step) {
        // Verifica se o usuário já viu esta dica no navegador
        const hasSeen = localStorage.getItem(step.key);

        if (!hasSeen) {
            // Pequeno delay para a interface carregar antes do modal aparecer
            setTimeout(() => {
                // Função global definida no base.html
                if (window.openGlobalModal) {
                    const iconEl = document.getElementById('infoIcon');
                    const titleEl = document.getElementById('infoTitle');
                    const textEl = document.getElementById('infoText');

                    if (iconEl && titleEl && textEl) {
                        iconEl.className = step.icon;
                        titleEl.innerHTML = step.title;
                        textEl.innerHTML = step.text;
                        
                        // Abre o modal
                        window.openGlobalModal('infoModal');
                        
                        // Marca como visto para não incomodar novamente
                        localStorage.setItem(step.key, 'true');
                    }
                }
            }, 800);
        }
    }
});


