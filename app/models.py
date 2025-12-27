from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class DictMixin:
    def __getitem__(self, key): return getattr(self, key)
    def get(self, key, default=None): return getattr(self, key, default)
    def to_dict(self):
        d = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if isinstance(val, (datetime, date)): d[c.name] = str(val)
            else: d[c.name] = val
        return d

class User(UserMixin, db.Model, DictMixin):
    # Tabela principal 'user' com aspas para compatibilidade Postgres
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True) # INDEX ADICIONADO
    nome = db.Column(db.String(150))
    whatsapp = db.Column(db.String(20))
    password_hash = db.Column(db.String(200), nullable=False)
    
    category = db.Column(db.String(20), default='trial', index=True) # INDEX ADICIONADO
    validade = db.Column(db.Date, index=True) # INDEX ADICIONADO
    data_cadastro = db.Column(db.Date, default=datetime.utcnow)
    
    payment_method = db.Column(db.String(20))
    is_confirmed = db.Column(db.Boolean, default=True)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    last_seen_version = db.Column(db.String(5))
    is_temp_password = db.Column(db.Boolean, default=False)
    
    profile_image = db.Column(db.String(500), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    
    # PLAN TYPE REAL
    plan_type = db.Column(db.String(20), default='premium') 
    
    # INDICAÇÃO
    referral_code = db.Column(db.String(10), unique=True, index=True) 
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), index=True) # INDEX ADICIONADO
    referral_balance = db.Column(db.Integer, default=0)
    referral_bonus_given = db.Column(db.Boolean, default=False)

    referrer = db.relationship('User', remote_side=[id], backref='referrals')

    diarios = db.relationship('Diario', backref='dono', lazy=True, cascade="all, delete-orphan")
    configs = db.relationship('Config', backref='dono', lazy=True, cascade="all, delete-orphan")
    manutencoes = db.relationship('Manutencao', backref='dono', lazy=True, cascade="all, delete-orphan")
    agendamentos = db.relationship('Agendamentos', backref='dono', lazy=True, cascade="all, delete-orphan")
    notificacoes = db.relationship('Notification', backref='recipient', lazy=True, cascade="all, delete-orphan")
    tickets = db.relationship('SupportTicket', backref='dono', lazy=True, cascade="all, delete-orphan")
    conquistas_desbloqueadas = db.relationship('UserAchievement', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class MaintenanceLog(db.Model, DictMixin):
    # Histórico de Manutenção (Item 2)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # INDEX ADICIONADO
    item_name = db.Column(db.String(100), nullable=False)
    service_date = db.Column(db.Date, default=datetime.utcnow, index=True) # INDEX ADICIONADO
    service_km = db.Column(db.Float, default=0.0)
    cost = db.Column(db.Numeric(10,2), default=0.00)
    notes = db.Column(db.Text, nullable=True)

class Notification(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True) 
    message = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.now) 
    is_read = db.Column(db.Boolean, default=False, index=True) # INDEX ADICIONADO
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # INDEX ADICIONADO

class SupportTicket(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True) 
    motivo = db.Column(db.String(100), nullable=False) 
    mensagem = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.now) 
    updated_at = db.Column(db.DateTime, default=datetime.now) 
    status = db.Column(db.String(30), default='Aberto', index=True) # INDEX ADICIONADO
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # INDEX ADICIONADO
    messages = db.relationship('TicketMessage', backref='ticket', lazy=True, cascade="all, delete-orphan")

class TicketMessage(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True) 
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False, index=True) # INDEX ADICIONADO
    sender_type = db.Column(db.String(10), nullable=False) 
    message = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.now)

class Diario(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True) # INDEX EXISTENTE
    ganho_bruto = db.Column(db.Numeric(10,2), default=0.00)
    ganho_uber = db.Column(db.Numeric(10,2), default=0.00)
    ganho_99 = db.Column(db.Numeric(10,2), default=0.00)
    ganho_part = db.Column(db.Numeric(10,2), default=0.00)
    ganho_outros = db.Column(db.Numeric(10,2), default=0.00)
    despesa_combustivel = db.Column(db.Numeric(10,2), default=0.00)
    despesa_alimentacao = db.Column(db.Numeric(10,2), default=0.00)
    despesa_manutencao = db.Column(db.Numeric(10,2), default=0.00)
    qtd_uber = db.Column(db.Integer, default=0)
    qtd_99 = db.Column(db.Integer, default=0)
    qtd_part = db.Column(db.Integer, default=0)
    qtd_outros = db.Column(db.Integer, default=0)
    km_percorrido = db.Column(db.Float, default=0.0)
    horas_trabalhadas = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # INDEX ADICIONADO

class Agendamentos(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    data_hora = db.Column(db.DateTime, index=True) # INDEX EXISTENTE
    origem = db.Column(db.String(200))
    parada = db.Column(db.String(200), nullable=True) 
    destino = db.Column(db.String(200))
    valor = db.Column(db.Numeric(10,2))
    observacao = db.Column(db.Text)
    status = db.Column(db.String(20), default='pendente', index=True) # INDEX ADICIONADO
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True) # INDEX ADICIONADO

class Manutencao(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True) 
    item = db.Column(db.String(100)) 
    km_troca = db.Column(db.Float) 
    km_proxima = db.Column(db.Float) 
    status = db.Column(db.String(20)) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True) # INDEX ADICIONADO

class Config(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True) 
    chave = db.Column(db.String(50), index=True) # INDEX ADICIONADO
    valor = db.Column(db.Text) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True) # INDEX ADICIONADO
    
class CustosFixos(db.Model, DictMixin):
    id = db.Column(db.Integer, primary_key=True) 
    nome = db.Column(db.String(100)) 
    valor = db.Column(db.Numeric(10,2)) 
    tipo = db.Column(db.String(20)) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True) # INDEX ADICIONADO

class Achievement(db.Model, DictMixin):
    __tablename__ = 'achievement'
    id = db.Column(db.String(50), primary_key=True) 
    nome = db.Column(db.String(100), nullable=False) 
    descricao = db.Column(db.String(255), nullable=False) 
    icone = db.Column(db.String(20), default='🏆') 
    categoria = db.Column(db.String(30), default='geral') 
    xp = db.Column(db.Integer, default=10)

class UserAchievement(db.Model, DictMixin):
    __tablename__ = 'user_achievement'
    id = db.Column(db.Integer, primary_key=True) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # INDEX ADICIONADO
    achievement_id = db.Column(db.String(50), db.ForeignKey('achievement.id'), nullable=False) 
    conquistado_em = db.Column(db.DateTime, default=datetime.utcnow) 
    visto = db.Column(db.Boolean, default=False) 
    detalhes = db.relationship('Achievement', lazy='joined')



