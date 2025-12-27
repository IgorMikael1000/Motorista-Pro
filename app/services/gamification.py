from app.models import Achievement, UserAchievement, Diario, Agendamentos
from app.extensions import db
from sqlalchemy import func

class AchievementService:
    @staticmethod
    def calculate_level(user):
        return "Motorista Pro", 100

    @staticmethod
    def get_badges_with_progress(user):
        try:
            # OTIMIZAÇÃO: Busca todas as conquistas do usuário de uma vez só em memória
            all_badges = Achievement.query.all()
            
            # Se não houver conquistas cadastradas no sistema, retorna vazio sem erro
            if not all_badges:
                return [], []
            
            user_badges_query = UserAchievement.query.filter_by(user_id=user.id).all()
            user_badges = {ua.achievement_id: ua for ua in user_badges_query}
            
            badges_list = []
            new_unlocks = []
            
            stats = db.session.query(
                func.count(Diario.id),
                func.coalesce(func.sum(Diario.km_percorrido), 0),
                func.coalesce(func.sum(Diario.ganho_bruto), 0)
            ).filter_by(user_id=user.id).first()
            
            total_dias = stats[0] or 0
            total_km = stats[1]
            total_faturamento = stats[2]
            
            total_agendamentos = Agendamentos.query.filter_by(user_id=user.id, status='concluido').count()
            
            filtered_badges = []
            palavras_proibidas = ['bronze', 'prata', 'ouro', 'nível', 'investidor']
            for badge in all_badges:
                nome_lower = badge.nome.lower()
                id_lower = badge.id.lower()
                if any(p in nome_lower for p in palavras_proibidas) or any(p in id_lower for p in palavras_proibidas):
                    continue
                filtered_badges.append(badge)

            for badge in filtered_badges:
                if badge.id == 'lenda_viva': continue

                unlocked = badge.id in user_badges
                current = 0; target = 1
                
                if badge.id == 'primeira_marcha': current, target = total_dias, 1
                elif badge.id == 'maratonista': current, target = total_dias, 30
                elif badge.id == 'veterano': current, target = total_dias, 365
                elif badge.id == 'viajante': current, target = int(total_km), 1000
                elif badge.id == 'estradeiro': current, target = int(total_km), 10000
                elif badge.id == 'rei_da_pista': current, target = int(total_km), 50000
                elif badge.id == 'agenda_lotada': current, target = total_agendamentos, 5
                elif badge.id == 'executivo': current, target = total_agendamentos, 50
                elif badge.id == 'primeiro_k': current, target = int(total_faturamento), 1000
                elif badge.id == 'faturou_10k': current, target = int(total_faturamento), 10000
                elif badge.id == 'magnata': current, target = int(total_faturamento), 100000
                elif badge.id == 'empreendedor': current = 1 if unlocked else 0 
                elif badge.id == 'expert_manutencao': current = 1 if unlocked else 0
                
                progress = min(100, int((current / target) * 100)) if target > 0 else 0
                
                badges_list.append({
                    'id': badge.id,
                    'nome': badge.nome,
                    'descricao': badge.descricao,
                    'icone': badge.icone,
                    'categoria': badge.categoria,
                    'unlocked': unlocked,
                    'progress': progress if not unlocked else 100,
                    'current': current,
                    'target': target
                })
                
                if unlocked and not user_badges[badge.id].visto: new_unlocks.append(badge.id)

            total_possiveis = len(filtered_badges) - 1
            total_ganhos = len([b for b in badges_list if b['unlocked']])
            
            lenda_unlocked = 'lenda_viva' in user_badges
            if total_ganhos >= total_possiveis and not lenda_unlocked and total_possiveis > 0:
                 db.session.add(UserAchievement(user_id=user.id, achievement_id='lenda_viva'))
                 db.session.commit()
                 lenda_unlocked = True
                 new_unlocks.append('lenda_viva')

            badges_list.append({
                'id': 'lenda_viva',
                'nome': 'Lenda Viva',
                'descricao': 'Zere o jogo completando todas as conquistas.',
                'icone': '👑',
                'categoria': 'master',
                'unlocked': lenda_unlocked,
                'progress': int((total_ganhos / total_possiveis) * 100) if total_possiveis > 0 else 0,
                'current': total_ganhos,
                'target': total_possiveis
            })

            return badges_list, new_unlocks
        except Exception as e:
            print(f"Erro Gamification Service: {e}")
            # Em caso de erro, retorna listas vazias para não travar a aplicação
            return [], []

    @staticmethod
    def check_new_entries(user):
        try:
            unlocks = []
            stats = db.session.query(
                func.count(Diario.id),
                func.coalesce(func.sum(Diario.km_percorrido), 0),
                func.coalesce(func.sum(Diario.ganho_bruto), 0)
            ).filter_by(user_id=user.id).first()
            
            total_dias = stats[0] or 0
            total_km = stats[1]
            total_fat = stats[2]
            
            existing_ids = {ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user.id).all()}
            
            def give(bid):
                if bid not in existing_ids:
                    # Verifica se o achievement existe antes de dar
                    if db.session.query(Achievement.id).filter_by(id=bid).first():
                        db.session.add(UserAchievement(user_id=user.id, achievement_id=bid))
                        unlocks.append(bid)
                        existing_ids.add(bid)

            if total_dias >= 1: give('primeira_marcha')
            if total_dias >= 30: give('maratonista')
            if total_dias >= 365: give('veterano')
            
            if total_km >= 1000: give('viajante')
            if total_km >= 10000: give('estradeiro')
            if total_km >= 50000: give('rei_da_pista')
            
            if total_fat >= 1000: give('primeiro_k')
            if total_fat >= 10000: give('faturou_10k')
            if total_fat >= 100000: give('magnata')

            if unlocks:
                db.session.commit()
            return unlocks
        except:
            return []

    @staticmethod
    def check_usage(user, action_type):
        try:
            unlocks = []
            existing_ids = {ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user.id).all()}
            
            if action_type == 'agenda_concluir':
                total = Agendamentos.query.filter_by(user_id=user.id, status='concluido').count()
                if total >= 5 and 'agenda_lotada' not in existing_ids:
                    if db.session.query(Achievement.id).filter_by(id='agenda_lotada').first():
                        db.session.add(UserAchievement(user_id=user.id, achievement_id='agenda_lotada'))
                        unlocks.append('agenda_lotada')
                if total >= 50 and 'executivo' not in existing_ids:
                    if db.session.query(Achievement.id).filter_by(id='executivo').first():
                        db.session.add(UserAchievement(user_id=user.id, achievement_id='executivo'))
                        unlocks.append('executivo')
            
            elif action_type == 'recibo':
                 if 'empreendedor' not in existing_ids:
                    if db.session.query(Achievement.id).filter_by(id='empreendedor').first():
                        db.session.add(UserAchievement(user_id=user.id, achievement_id='empreendedor'))
                        unlocks.append('empreendedor')

            if unlocks:
                db.session.commit()
            return unlocks
        except:
            return []
        
    @staticmethod
    def check_meta(user): return []
    @staticmethod
    def check_setup(user): return []


