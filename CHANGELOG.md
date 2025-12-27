Changelog
Todas as alterações notáveis neste projeto serão documentadas neste arquivo.
O formato baseia-se em Keep a Changelog,
e este projeto adere ao versionamento semântico.
​​[v13.2.0-onboarding] - 19-12-2025 (CURRENT)
​Melhorias na experiência de primeiro acesso e correções visuais.
​🌟 Experiência do Utilizador (UX)
​Onboarding Inteligente: Adicionados modais explicativos automáticos na primeira visita a cada tela importante (Histórico, Agenda, Lucro Real, etc.), guiando o novo utilizador.
​Tela de Boas-Vindas: Redesign completo com visual moderno, ícone 3D e destaque dos benefícios chave.
​Tour Guiado: Correção na biblioteca de tour para garantir que o guia passo-a-passo apareça corretamente no primeiro login.
​Cookies: Banner de consentimento LGPD implementado e visível.
​⚙️ Ajustes e Correções
​Período de Teste: Ajustado de 6 para 7 dias completos de Trial.
​Tag Premium: O menu lateral agora diferencia visualmente quem está em "Teste Grátis" (Tag Azul/Roxo) de quem é "Assinante Premium" (Tag Dourada).
​Backup: Botões de Exportar/Importar dados restaurados na tela de Configurações.
​Semanas: Calendário ajustado para considerar semanas de Domingo a Sábado, alinhado com o padrão de pagamentos dos aplicativos.
[v13.1.0-launch-ready] - 19-12-2025 (VERSÃO DE LANÇAMENTO)
​Versão final polida e otimizada para produção em massa. Foco total em performance de base de dados, SEO e conformidade legal.
​🚀 Performance & Infraestrutura
​Índices de Base de Dados: Adicionados índices estratégicos (index=True) em todas as colunas de alta frequência (user_id, data, email, status). Isso garante consultas instantâneas mesmo com milhares de registos.
​Cache Busting Automático: Implementado sistema inteligente que adiciona ?v=v13.1 a todos os ficheiros CSS e JS. Os utilizadores nunca mais verão versões antigas/quebradas do app após uma atualização.
​Refatoração de Código: Criação do Blueprint dashboard.py para desacoplar a lógica pesada de cálculo financeiro das rotas de CRUD (main.py), facilitando manutenção futura.
​🛡️ Segurança & Conformidade
​Aviso de Cookies: Adicionado banner de consentimento (LGPD/GDPR) para conformidade legal no primeiro acesso.
​Robots.txt: Configuração de SEO para impedir que o Google indexe páginas privadas (admin, histórico) e foque apenas na Landing Page.
​Sanitização: Remoção de scripts de depuração (debug_urls.py, force_fix.py) da árvore de produção.
​📱 Experiência do Utilizador (UX)
​Carregamento Otimizado: Gamificação agora é calculada apenas em eventos de escrita (Salvar/Editar), removendo a latência no carregamento do Dashboard.
​Feedback Visual: Indicadores de carregamento refinados para operações assíncronas.
[v12.1.0-polish] - 19-12-2025 (CURRENT)
Refinamento final de funcionalidades e experiência do utilizador.
🛠️ Funcionalidades e Melhorias
 * Manutenção Completa: Agora, ao concluir uma manutenção, o sistema solicita também o Valor do Serviço (R$), além da quilometragem, permitindo um histórico financeiro exato no Livro de Revisões.
 * Interface (UI):
   * Título da secção de configuração alterado para "Custo Fixo" (mais direto).
   * Aviso informativo adicionado na tela de Lucro Real: "Os valores apresentados referem-se ao período selecionado".
   * Identidade Premium: Utilizadores PRO têm destaque visual elegante na barra lateral (Badge PRO) sem elementos excessivos.
[v12.0.0-business-class] - 18-12-2025 (MAJOR RELEASE)
Transformação do app num sistema completo de gestão de frota pessoal.
💼 Gestão de Custos Fixos (Premium)
 * Controle Empresarial: Nova secção nas configurações do veículo para lançar custos recorrentes que não dependem da rodagem:
   * Seguro (Mensal)
   * IPVA (Anual)
   * Aluguel (Semanal)
   * Financiamento (Mensal)
 * Reserva Operacional: O cálculo do Lucro Real agora deduz automaticamente estes custos (pro-rata dia) além dos custos variáveis (pneus/óleo), oferecendo a visão financeira mais precisa do mercado.
 * Toggle Inteligente: Opção na tela de Lucro Real para ativar/desativar a dedução dos custos fixos na visualização dos dados.
💲 Vendas
 * Lista de Benefícios: Atualizada a tela de assinatura para destacar a gestão de custos fixos e o livro de revisões.
[v11.1.0-premium-plus] - 18-12-2025 (FEATURE PACK)
Refinamento da identidade visual e documentos.
✨ Novidades
 * Livro de Revisões Digital (PDF): Exportação do histórico completo de manutenção em formato PDF profissional.
 * Marca d'Água: Autenticidade garantida em todos os documentos gerados (Relatórios e Recibos) com a marca oficial do app.
 * Ajuste de Quilometragem: Edição manual do odómetro ao finalizar serviços de manutenção para corrigir divergências entre o GPS e o painel do carro.
[v11.0.0-social] - 18-12-2025 (FEATURE UPDATE)
Implementação de autenticação moderna e rebranding.
🚀 Acesso
 * Login Social (Google): Cadastro e Login com 1 clique (sem senha).
 * Gestão Híbrida de Imagens: Suporte simultâneo a fotos do Google e uploads manuais (ImgBB).
 * Branding: Ícones genéricos substituídos pela logomarca oficial em todo o fluxo de entrada e nova Landing Page focada em conversão mobile.
[v10.1.0-release] - 18-12-2025 (STABILITY PATCH)
Estabilidade de Infraestrutura.
🐛 Correções
 * PIX Dev: Supressão de webhook em ambiente local (localhost) para permitir testes de geração de QR Code sem erros do Mercado Pago.
 * Rotas: Correção de erro 404 na rota /assinar.
 * Stripe: Leitura dinâmica de IDs de cupão via variáveis de ambiente.
 * Limpeza: Remoção de ferramentas de depuração (botões de teste) da interface final.
[v10.0.0-security] - 18-12-2025 (MAJOR UPDATE)
Blindagem de segurança e precisão matemática.
🛡️ Segurança
 * Credenciais: Remoção de todas as URLs de banco de dados e senhas do código fonte.
 * Admin: Senha administrativa agora exige configuração via Variável de Ambiente.
 * Infra: Modo Debug forçado para False em produção.
💰 Precisão Financeira
 * Core: Migração total de Float para Decimal em todo o sistema financeiro para precisão absoluta de centavos.
 * Webhooks: Conversão segura de valores monetários na confirmação de pagamento (Stripe/MP).
⚡ Performance
 * Render Otimizado: Configuração do Gunicorn ajustada com threads e 2 workers para baixo consumo de memória (512MB).
 * BI Rápido: Dashboard administrativo reescrito com agregações SQL, corrigindo problemas de lentidão (N+1).
[v9.2.0-hotfix] - 18-12-2025
Corrigido
 * Rotas: Restauradas as rotas /gerenciar_assinatura e /relatorios que estavam inacessíveis.
 * Histórico: Implementada restrição no backend para que utilizadores Basic recebam apenas os registos dos últimos 30 dias.
Melhorado (UX)
 * Agenda: Botão "Concluir" restaurado para todos os utilizadores. Gatilho de Upsell movido para a geração de recibo.
[v9.1.0-hotfix] - 18-12-2025
Corrigido
 * Rotas Críticas: Correção de erro 404 ao salvar meta e acessar "Meu Plano".
 * Histórico de Manutenção: A aba "Livro de Revisões" agora exibe corretamente a lista de manutenções passadas.
 * Dev Tools: Adicionado botão temporário para alternar planos em desenvolvimento.
[v9.0.0-hotfix] - 18-12-2025
Corrigido
 * Base de Dados: Adicionado modelo MaintenanceLog.
 * Login: Reforçada a validação do FIREBASE_CONFIG_FRONTEND.
 * Metas: Lógica ajustada para considerar Lucro Operacional.
Melhorado
 * Manutenção: Alertas nativos substituídos por modais SweetAlert2.
 * Suporte: Sistema de Chat ativado.
[v8.0.0-production] - 17-12-2025 (GO LIVE)
Sistema
 * Base de Dados: Migração estrutural para Postgres e suporte a múltiplos planos.
 * Migração: Assinantes antigos migrados para Premium.
 * Pagamentos: Webhooks reais implementados.
[v7.0.0-hotfix] - 17-12-2025
Adicionado
 * BI: Painel administrativo com cálculo de MRR e LTV.
 * Admin: Métricas de contagem de assinantes.
[v6.0.0-hotfix] - 17-12-2025
Alterado
 * Metas: Reformulação da "Meta Inteligente" com objectivo diário dinâmico.
[v5.7.0] a [v5.0.0] - 17-12-2025
Interface e Upsell
 * Agenda: Barra de pesquisa instantânea.
 * UX Relatórios: Modais de Upsell estilizados ("Glassmorphism").
 * Upsell Recibos: Gatilho movido para conclusão.
 * Upsell Lucro Real: Bloqueio duplo na secção "Custo Invisível".
 * Lançamentos: Tela redesenhada.
 * Histórico: Paginação HTMX.
 * Assinatura: Redesign completo da tela de pagamento.
[v4.0.0-hotfix] - 17-12-2025
Adicionado
 * Relatórios: Gerador de PDF Operacional.
 * Gráficos: Gráfico de Rosca (Volume de Corridas).
[v3.0.0-hotfix] - 17-12-2025
Adicionado
 * Gamificação: Sistema de Conquistas e "Lenda Viva".
 * Suporte: Botão WhatsApp VIP.
 * UX: Efeito de desfoque no bloqueio de Lucro Real.
[v2.0.0] - 17-12-2025
Crescimento
 * Indicação: Sistema "Indique e Ganhe" com códigos únicos.
 * Pagamento: Rota mock para testes iniciais.
[v1.0.0-hotfix] - 17-12-2025
Lançamento
 * Correções: Trial de 7 dias exactos, Notificações semanais.
 * MVP: Funcionalidades base de lançamento.

