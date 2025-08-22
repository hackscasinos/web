from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_cors import CORS
import random
import string
import smtplib
import ssl
from email.message import EmailMessage
import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import hashlib
import time

app = Flask(__name__)

# Configurar CORS para desarrollo local - permitir cualquier origen
CORS(app, origins="*", supports_credentials=True)

# Generar clave secreta más segura basada en timestamp y hash
# Para desarrollo local, usar clave fija para sincronización con WebSocket
if os.getenv('FLASK_ENV') == 'development' or not os.getenv('FLASK_SECRET_KEY'):
    app.config['SECRET_KEY'] = 'hacks_casino_development_key_2025'
else:
    secret_base = f"hacks_casino_2025_{int(time.time())}"
    app.config['SECRET_KEY'] = hashlib.sha256(secret_base.encode()).hexdigest()

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hacks_casinos_bagq_user:zD4uYoThdVzwbkxB0EQNM0C11JEM2yTa@dpg-d2bnv4er433s73a0an3g-a.oregon-postgres.render.com/hacks_casinos_bagq'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar protección CSRF
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora
csrf = CSRFProtect(app)

# Nota: Las rutas API están exentas de CSRF usando @csrf.exempt en cada ruta

# Configurar Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # En producción usar Redis
)
limiter.init_app(app)

# Configurar logging de seguridad
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)
security_logger = logging.getLogger('security')

db = SQLAlchemy(app)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configuración SMTP
SMTP_CONFIG = {
    'server': 'mail.spacemail.com',
    'port': 465,
    'username': 'security@hacks.casino',
    'password': 'Welcome2050@'
}

ROLES = ['pending', 'signals_bot', 'community_bots', 'Admin']
SUPER_ADMIN_EMAIL = 'msukjimao@gmail.com'
ALL_ROLES = ['Admin', 'signals_bot', 'community_bots']  # Todos los roles que tendrá el super admin

# Productos disponibles
PRODUCTS = {
    'signals_bot': {
        'name': 'Signals Bot',
        'description': 'Bot para obtener señales de casino en vivo para apostar de uso personal',
        'price': 30,
        'currency': 'USD'
    },
    'community_bots': {
        'name': 'Community Signals',
        'description': 'Bot para ofrecer señales a la comunidad del usuario',
        'price': 180,
        'currency': 'USD'
    }
}

# Métodos de pago disponibles
PAYMENT_METHODS = {
    'binance': {
        'name': 'Binance Pay',
        'description': 'Pago con Binance Pay',
        'icon': 'binance-icon.svg'
    },
    'paypal': {
        'name': 'PayPal',
        'description': 'Pago con PayPal',
        'icon': 'paypal-icon.svg'
    },
    'airtm': {
        'name': 'Airtm',
        'description': 'Pago con Airtm',
        'icon': 'airtm-icon.svg'
    }
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default='pending', nullable=False)
    roles = db.Column(db.Text, default='')  # Múltiples roles separados por comas
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, active, suspended
    is_super_admin = db.Column(db.Boolean, default=False)  # Flag para el super admin
    pin_code = db.Column(db.String(255), nullable=True)  # PIN de 4 dígitos (hash)
    pin_created_at = db.Column(db.DateTime, nullable=True)  # Fecha de creación del PIN
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def get_roles_list(self):
        """Obtiene la lista de roles del usuario"""
        if self.is_super_admin:
            return ALL_ROLES
        if self.roles:
            return [role.strip() for role in self.roles.split(',') if role.strip()]
        return [self.role] if self.role != 'pending' else []
    
    def has_role(self, role):
        """Verifica si el usuario tiene un rol específico"""
        if self.is_super_admin:
            return True
        return role in self.get_roles_list()
    
    def add_role(self, new_role):
        """Agrega un nuevo rol al usuario"""
        if self.is_super_admin:
            return  # Super admin ya tiene todos los roles
        current_roles = self.get_roles_list()
        if new_role not in current_roles:
            current_roles.append(new_role)
            self.roles = ','.join(current_roles)
            # Actualizar el rol principal si era pending
            if self.role == 'pending':
                self.role = new_role
    
    def get_roles_display(self):
        """Obtiene una representación legible de los roles del usuario"""
        if self.is_super_admin:
            return "Super Admin (Todos los roles)"
        roles = self.get_roles_list()
        if not roles:
            return "Sin roles asignados"
        return ", ".join(roles)
    
    def set_pin(self, pin):
        """Establece un PIN de 4 dígitos para el usuario"""
        if len(pin) == 4 and pin.isdigit():
            self.pin_code = generate_password_hash(pin)
            self.pin_created_at = datetime.now(timezone.utc)
            return True
        return False
    
    def verify_pin(self, pin):
        """Verifica si el PIN proporcionado es correcto"""
        if not self.pin_code or not pin:
            return False
        return check_password_hash(self.pin_code, pin)
    
    def has_pin(self):
        """Verifica si el usuario tiene un PIN configurado"""
        return self.pin_code is not None

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    proof_file = db.Column(db.String(255))  # Ruta del archivo de comprobante
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relación con User
    user = db.relationship('User', backref=db.backref('purchases', lazy=True))

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    method_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    account_info = db.Column(db.Text)  # Información de la cuenta para pagos
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class VerificationCode(db.Model):
    """Modelo para almacenar códigos de verificación de forma segura"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)  # Código hasheado
    purpose = db.Column(db.String(50), nullable=False)  # 'login', 'register', 'reset_pin'
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)  # Contador de intentos
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    @staticmethod
    def create_code(email, purpose, expiry_minutes=10):
        """Crea un nuevo código de verificación"""
        # Limpiar códigos expirados del mismo email y propósito
        VerificationCode.query.filter_by(
            email=email, 
            purpose=purpose
        ).delete()
        
        # Generar código de 6 dígitos
        code = "".join(random.choices(string.digits, k=6))
        code_hash = generate_password_hash(code)
        
        # Crear registro
        verification_code = VerificationCode(
            email=email,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        )
        
        db.session.add(verification_code)
        db.session.commit()
        
        return code  # Retornar código plano para enviar por email
    
    @staticmethod
    def verify_code(email, code, purpose, max_attempts=3):
        """Verifica un código de verificación"""
        verification_code = VerificationCode.query.filter_by(
            email=email,
            purpose=purpose,
            is_used=False
        ).filter(
            VerificationCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not verification_code:
            return False, "Código expirado o no encontrado"
        
        # Verificar intentos máximos
        if verification_code.attempts >= max_attempts:
            return False, "Demasiados intentos fallidos"
        
        # Verificar código
        if check_password_hash(verification_code.code_hash, code):
            verification_code.is_used = True
            db.session.commit()
            return True, "Código verificado correctamente"
        else:
            verification_code.attempts += 1
            db.session.commit()
            remaining = max_attempts - verification_code.attempts
            return False, f"Código incorrecto. Intentos restantes: {remaining}"


class SecurityLog(db.Model):
    """Modelo para logging de eventos de seguridad"""
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), index=True)
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    success = db.Column(db.Boolean, nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    @staticmethod
    def log_event(email, action, success, details=None, ip_address=None, user_agent=None):
        """Registra un evento de seguridad"""
        log_entry = SecurityLog(
            user_email=email,
            action=action,
            success=success,
            details=details,
            ip_address=ip_address or request.remote_addr,
            user_agent=user_agent or request.headers.get('User-Agent', '')
        )
        db.session.add(log_entry)
        db.session.commit()
        
        # También log a archivo
        log_message = f"Action: {action}, Email: {email}, Success: {success}, IP: {ip_address}"
        if success:
            security_logger.info(log_message)
        else:
            security_logger.warning(log_message)

def send_email(to_email, subject, body_text, body_html=None):
    """Envía email usando SMTP"""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_CONFIG['username']
    msg['To'] = to_email
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype='html')

    try:
        with smtplib.SMTP_SSL(SMTP_CONFIG['server'], SMTP_CONFIG['port'], context=ssl.create_default_context()) as server:
            server.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False

def jwt_login_required(f):
    """Decorador para proteger rutas que requieren login con JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            SecurityLog.log_event(None, 'access_denied_no_token', False, 'Intento de acceso sin token')
            flash("Debes iniciar sesión para acceder a esta página.")
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(data['user_id'])
            if not user:
                SecurityLog.log_event(data.get('email'), 'access_denied_user_not_found', False, 'Usuario en token no existe')
                flash("Usuario no encontrado.")
                return redirect(url_for('login'))
            
            SecurityLog.log_event(user.email, 'successful_access', True, f'Acceso a {request.endpoint}')
            return f(user=user, *args, **kwargs)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            SecurityLog.log_event(None, 'access_denied_invalid_token', False, f'Token inválido: {str(e)}')
            flash("Sesión expirada o token inválido. Por favor, inicia sesión de nuevo.")
            return redirect(url_for('login'))
    return decorated_function

def admin_required(f):
    """Decorador para rutas que requieren rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(data['user_id'])
            if not user or not user.has_role('Admin'):
                flash("Acceso denegado. Solo los administradores pueden acceder a esta sección.")
                return redirect(url_for('dashboard'))
            return f(user=user, *args, **kwargs)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return redirect(url_for('login'))
    return decorated_function

@app.route("/")
def index():
    # Verificar si hay una sesión activa a través del token JWT
    token = request.cookies.get('token')
    if token:
        try:
            # Decodificar el token para obtener la información del usuario
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(data['user_id'])
            
            if user:
                # Usuario con sesión activa - redirigir según su rol y estado
                
                # Super admin va al dashboard de administración
                if user.is_super_admin:
                    return redirect('/dashboard')
                
                # Admin va al dashboard de administración
                if user.has_role('Admin'):
                    return redirect('/dashboard')
                
                # Usuario activo con roles específicos
                if user.status == 'active':
                    if user.has_role('signals_bot'):
                        return redirect('/signals-casino')
                    elif user.has_role('community_bots'):
                        return redirect('/community-bots')
                
                # Usuario pendiente o sin roles específicos va a user-dashboard
                return redirect('/user-dashboard')
                
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Token inválido o expirado - limpiar cookie y continuar al index
            resp = make_response(render_template("index.html", products=PRODUCTS))
            resp.delete_cookie('token')
            return resp
    
    # No hay sesión activa o token inválido - mostrar página index normal
    return render_template("index.html", products=PRODUCTS)

@app.route("/favicon.ico")
def favicon():
    """Ruta para manejar favicon y evitar error 404"""
    return '', 204  # No Content

@app.route("/api/auth")
def api_auth_index():
    """Página de autenticación - redirige al index con modal de login"""
    return redirect(url_for('index') + '#login')

@app.route("/dashboard")
@jwt_login_required
def dashboard(user):
    # Solo admins y super admins pueden acceder
    if not user.has_role('Admin'):
        flash("Acceso denegado. Solo los administradores pueden acceder a esta sección.")
        return redirect(url_for('user_dashboard'))
    
    # Obtener todos los usuarios
    users = User.query.all()
    
    # Obtener todas las compras
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    
    # Filtrar compras por estado
    pending_purchases = [p for p in purchases if p.status == 'pending']
    approved_purchases = [p for p in purchases if p.status == 'approved']
    
    return render_template("dashboard.html", 
                         user=user, 
                         users=users, 
                         purchases=purchases,
                         pending_purchases=pending_purchases,
                         approved_purchases=approved_purchases,
                         products=PRODUCTS)

@app.route("/admin-panel")
@admin_required
def admin_panel(user):
    users = User.query.all()
    return render_template("admin_panel.html", user=user, users=users, roles=ROLES)

@app.route("/admin/update-role/<int:user_id>", methods=['POST'])
@csrf.exempt
@admin_required
def update_role(user, user_id):
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == user.id:
        return jsonify({"error": "No puedes cambiar tu propio rol"}), 400

    new_role = request.form.get('role')
    if new_role not in ROLES:
        return jsonify({"error": "Rol inválido"}), 400

    target_user.role = new_role
    db.session.commit()

    return jsonify({"success": f"Rol actualizado a {new_role} para {target_user.email}"}), 200

@app.route("/send-code", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")  # Máximo 5 códigos por minuto por IP
@limiter.limit("10 per hour")   # Máximo 10 códigos por hora por IP
def send_code():
    data = request.json
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        SecurityLog.log_event(email, 'send_code_invalid_email', False, 'Email inválido proporcionado')
        return jsonify({"success": False, "message": "Correo inválido"}), 400

    if User.query.filter_by(email=email).first():
        SecurityLog.log_event(email, 'send_code_existing_user', False, 'Intento de registro con email existente')
        return jsonify({"success": False, "message": "El correo ya está registrado"}), 400

    # Crear código usando el sistema seguro
    try:
        code = VerificationCode.create_code(email, 'register', expiry_minutes=10)
    except Exception as e:
        SecurityLog.log_event(email, 'send_code_error', False, f'Error creando código: {str(e)}')
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500
    
    subject = "Tu código de verificación para Hacks Casino"
    body_text = f"Tu código de verificación es: {code}"
    body_html = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:#f9f9f9; padding: 20px; color:#333;">
        <div style="max-width:600px; margin:auto; background:#fff; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1); padding:30px;">
          <h2 style="color:#222; text-align:center;">Código de Verificación</h2>
          <p style="font-size:16px; text-align:center;">Hola,</p>
          <p style="font-size:18px; text-align:center; margin: 30px 0;">
            Tu código para verificar tu correo en <strong>Hacks Casino</strong> es:
          </p>
          <div style="font-size: 40px; font-weight: 700; text-align:center; letter-spacing: 8px; background:#000; color:#fff; padding: 15px 0; border-radius: 6px; user-select: all;">
            {code}
          </div>
          <p style="font-size:14px; color:#666; margin-top:40px; text-align:center;">
            Si no solicitaste este código, puedes ignorar este correo.
          </p>
          <hr style="border:none; border-top:1px solid #eee; margin:40px 0;">
          <p style="font-size:12px; color:#999; text-align:center;">
            &copy; 2025 Hacks Casino. Todos los derechos reservados.
          </p>
        </div>
      </body>
    </html>
    """

    if send_email(email, subject, body_text, body_html):
        SecurityLog.log_event(email, 'send_code_success', True, 'Código de verificación enviado exitosamente')
        return jsonify({"success": True, "message": "Código enviado a tu correo"})
    else:
        SecurityLog.log_event(email, 'send_code_email_error', False, 'Error enviando email')
        return jsonify({"success": False, "message": "Error al enviar el correo"}), 500

@app.route("/verify-code", methods=["POST"])
@csrf.exempt
@limiter.limit("10 per minute")  # Máximo 10 intentos de verificación por minuto
def verify_code():
    data = request.json
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip()
    product_id = data.get("product_id", "").strip()

    if not email or not code:
        SecurityLog.log_event(email, 'verify_code_missing_data', False, 'Datos faltantes en verificación')
        return jsonify({"success": False, "message": "Faltan datos"}), 400

    # Verificar código usando el sistema seguro
    is_valid, message = VerificationCode.verify_code(email, code, 'register')
    
    if is_valid:
        
        # Crear o actualizar usuario
        user = User.query.filter_by(email=email).first()
        if not user:
            # Configurar super admin automáticamente
            if email == SUPER_ADMIN_EMAIL:
                role = 'Admin'
                status = 'active'
                is_super_admin = True
                roles = ','.join(ALL_ROLES)  # Todos los roles
            else:
                role = 'pending'  # Todos los usuarios quedan pendientes hasta aprobación
                status = 'pending'
                is_super_admin = False
                roles = ''
            
            user = User(email=email, role=role, status=status, is_super_admin=is_super_admin, roles=roles)
            db.session.add(user)
            db.session.commit()
        else:
            # Si el usuario ya existe pero es el super admin, asegurar que tenga todos los privilegios
            if email == SUPER_ADMIN_EMAIL and not user.is_super_admin:
                user.is_super_admin = True
                user.role = 'Admin'
                user.status = 'active'
                user.roles = ','.join(ALL_ROLES)
                db.session.commit()

        # Hacer login del usuario
        login_user(user)

        # Generar token JWT
        token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        SecurityLog.log_event(email, 'verify_code_success', True, 'Código verificado y usuario logueado')
        resp = make_response(jsonify({"success": True, "message": "Código verificado correctamente"}))
        resp.set_cookie('token', token, httponly=True, samesite='Strict')
        return resp
    else:
        SecurityLog.log_event(email, 'verify_code_failed', False, f'Verificación fallida: {message}')
        return jsonify({"success": False, "message": message}), 400

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")  # Máximo 10 intentos de login por minuto
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        
        if not email:
            SecurityLog.log_event(email, 'login_missing_email', False, 'Email faltante en login')
            flash("Correo es requerido.")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()
        if user:
            try:
                # Generar código de verificación usando sistema seguro
                code = VerificationCode.create_code(email, 'login', expiry_minutes=10)
            except Exception as e:
                SecurityLog.log_event(email, 'login_code_error', False, f'Error generando código: {str(e)}')
                flash("Error interno del servidor.")
                return render_template("login.html")
            
            subject = "Tu código de acceso para Hacks Casino"
            body_text = f"Tu código de acceso es: {code}"
            body_html = f"""
            <html>
              <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:#f9f9f9; padding: 20px; color:#333;">
                <div style="max-width:600px; margin:auto; background:#fff; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1); padding:30px;">
                  <h2 style="color:#222; text-align:center;">Código de Acceso</h2>
                  <p style="font-size:16px; text-align:center;">Hola,</p>
                  <p style="font-size:18px; text-align:center; margin: 30px 0;">
                    Tu código para acceder a <strong>Hacks Casino</strong> es:
                  </p>
                  <div style="font-size: 40px; font-weight: 700; text-align:center; letter-spacing: 8px; background:#000; color:#fff; padding: 15px 0; border-radius: 6px; user-select: all;">
                    {code}
                  </div>
                  <p style="font-size:14px; color:#666; margin-top:40px; text-align:center;">
                    Si no solicitaste este código, puedes ignorar este correo.
                  </p>
                  <hr style="border:none; border-top:1px solid #eee; margin:40px 0;">
                  <p style="font-size:12px; color:#999; text-align:center;">
                    &copy; 2025 Hacks Casino. Todos los derechos reservados.
                  </p>
                </div>
              </body>
            </html>
            """
            
            if send_email(email, subject, body_text, body_html):
                SecurityLog.log_event(email, 'login_code_sent', True, 'Código de login enviado')
                flash("Código de acceso enviado a tu correo.")
            else:
                SecurityLog.log_event(email, 'login_code_email_error', False, 'Error enviando código de login')
                flash("Error al enviar el código de acceso.")
        else:
            SecurityLog.log_event(email, 'login_user_not_found', False, 'Intento de login con email no registrado')
            flash("Correo no registrado.")
        
        return render_template("login.html")

    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    resp = make_response(redirect(url_for('index')))
    resp.delete_cookie('token')
    flash("Has cerrado sesión.")
    return resp

@app.route("/purchase/<product_id>", methods=["POST"])
@csrf.exempt
@jwt_login_required
@limiter.limit("5 per minute")  # Máximo 5 compras por minuto
def purchase_product(user, product_id):
    if product_id not in PRODUCTS:
        return jsonify({"success": False, "error": "Producto no encontrado"}), 404
    
    product = PRODUCTS[product_id]
    
    # Crear la compra en estado pendiente
    purchase = Purchase(
        user_id=user.id,
        product_id=product_id,
        amount=product['price'],
        currency=product['currency'],
        payment_method='pending',
        status='pending'
    )
    
    db.session.add(purchase)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Compra de {product['name']} creada exitosamente",
        "purchase_id": purchase.id
    })

@app.route("/payment-methods", methods=["GET"])
def get_payment_methods():
    """Obtener métodos de pago disponibles"""
    return jsonify({
        "success": True,
        "methods": PAYMENT_METHODS
    })

@app.route("/payment-details/<method_id>", methods=["GET"])
def get_payment_details(method_id):
    """Obtener detalles de pago para un método específico"""
    if method_id not in PAYMENT_METHODS:
        return jsonify({"success": False, "error": "Método de pago no encontrado"}), 404
    
    # En producción, esto vendría de la base de datos
    payment_details = {
        'binance': {
            'account': 'hacks.casino@binance.com',
            'qr_code': '/static/qr/binance.png',
            'instructions': 'Escanea el código QR o envía el pago a la cuenta especificada'
        },
        'paypal': {
            'account': 'payments@hacks.casino',
            'qr_code': '/static/qr/paypal.png',
            'instructions': 'Envía el pago a través de PayPal usando el email especificado'
        },
        'airtm': {
            'account': 'hacks.casino@airtm.com',
            'qr_code': '/static/qr/airtm.png',
            'instructions': 'Realiza el pago a través de Airtm usando la cuenta especificada'
        }
    }
    
    return jsonify({
        "success": True,
        "method": PAYMENT_METHODS[method_id],
        "details": payment_details.get(method_id, {})
    })

@app.route("/upload-proof", methods=["POST"])
@csrf.exempt
@jwt_login_required
@limiter.limit("10 per hour")  # Máximo 10 uploads por hora
def upload_proof(user):
    """Subir comprobante de pago"""
    print(f"DEBUG upload_proof: Usuario {user.email} iniciando subida")
    print(f"DEBUG upload_proof: Files en request: {list(request.files.keys())}")
    print(f"DEBUG upload_proof: Form data: {dict(request.form)}")
    
    if 'proof_file' not in request.files:
        print("DEBUG upload_proof: No se encontró 'proof_file' en request.files")
        SecurityLog.log_event(user.email, 'upload_proof_no_file', False, 'Intento de subida sin archivo')
        return jsonify({"success": False, "error": "No se encontró archivo"}), 400
    
    file = request.files['proof_file']
    purchase_id = request.form.get('purchase_id')
    
    print(f"DEBUG upload_proof: purchase_id recibido: '{purchase_id}'")
    print(f"DEBUG upload_proof: archivo: {file.filename}")
    
    if not purchase_id:
        print("DEBUG upload_proof: purchase_id está vacío o None")
        SecurityLog.log_event(user.email, 'upload_proof_no_purchase_id', False, 'Intento de subida sin ID de compra')
        return jsonify({"success": False, "error": "ID de compra requerido"}), 400
    
    # Verificar que la compra pertenece al usuario
    purchase = Purchase.query.filter_by(id=purchase_id, user_id=user.id).first()
    print(f"DEBUG upload_proof: Búsqueda de compra - ID: {purchase_id}, User ID: {user.id}")
    print(f"DEBUG upload_proof: Compra encontrada: {purchase is not None}")
    
    if not purchase:
        print(f"DEBUG upload_proof: Compra no encontrada para ID {purchase_id} y usuario {user.id}")
        SecurityLog.log_event(user.email, 'upload_proof_invalid_purchase', False, f'Intento de subida para compra {purchase_id} no válida')
        return jsonify({"success": False, "error": "Compra no encontrada"}), 404
    
    print(f"DEBUG upload_proof: Compra encontrada - Status: {purchase.status}, Product: {purchase.product_id}")
    
    if file.filename == '':
        print("DEBUG upload_proof: Nombre de archivo está vacío")
        return jsonify({"success": False, "error": "No se seleccionó archivo"}), 400
    
    # Verificar tipo de archivo por extensión
    allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        SecurityLog.log_event(user.email, 'upload_proof_invalid_extension', False, f'Extensión no permitida: {file.filename}')
        return jsonify({"success": False, "error": "Tipo de archivo no permitido"}), 400
    
    # Leer archivo para validaciones
    file_content = file.read()
    file.seek(0)  # Resetear el puntero del archivo
    
    # Verificar tamaño del archivo (máximo 10MB)
    if len(file_content) > 10 * 1024 * 1024:  # 10MB
        SecurityLog.log_event(user.email, 'upload_proof_file_too_large', False, f'Archivo demasiado grande: {len(file_content)} bytes')
        return jsonify({"success": False, "error": "Archivo demasiado grande. Máximo 10MB"}), 400
    
    # Validación adicional: verificar magic numbers (firmas de archivo)
    def is_valid_file_type(content, filename):
        """Verifica el tipo de archivo por magic numbers"""
        if len(content) < 4:
            return False
            
        # Magic numbers para tipos permitidos
        magic_numbers = {
            b'\x89\x50\x4E\x47': 'png',  # PNG
            b'\xFF\xD8\xFF': 'jpg',       # JPEG
            b'\x25\x50\x44\x46': 'pdf',   # PDF
        }
        
        for magic, file_type in magic_numbers.items():
            if content.startswith(magic):
                # Verificar que la extensión coincida
                ext = filename.rsplit('.', 1)[1].lower()
                if file_type == 'jpg' and ext in ['jpg', 'jpeg']:
                    return True
                elif file_type == ext:
                    return True
        return False
    
    if not is_valid_file_type(file_content, file.filename):
        SecurityLog.log_event(user.email, 'upload_proof_invalid_file_type', False, f'Tipo de archivo no válido: {file.filename}')
        return jsonify({"success": False, "error": "El archivo no es válido o no coincide con su extensión"}), 400
    
    # Generar nombre único para el archivo
    timestamp = int(datetime.now(timezone.utc).timestamp())
    filename = f"proof_{purchase_id}_{timestamp}_{file.filename}"
    
    # Asegurar que la carpeta uploads existe
    upload_folder = 'uploads'
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Guardar archivo
    try:
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Actualizar la compra con la ruta del archivo
        purchase.proof_file = filename
        purchase.status = 'pending'
        purchase.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        SecurityLog.log_event(user.email, 'upload_proof_success', True, f'Comprobante subido para compra {purchase_id}')
        return jsonify({
            "success": True,
            "message": "Comprobante subido exitosamente",
            "filename": filename
        })
    except Exception as e:
        SecurityLog.log_event(user.email, 'upload_proof_error', False, f'Error guardando archivo: {str(e)}')
        return jsonify({"success": False, "error": f"Error al guardar archivo: {str(e)}"}), 500

@app.route("/purchase-status/<int:purchase_id>", methods=["GET"])
@jwt_login_required
def get_purchase_status(user, purchase_id):
    """Obtener estado de una compra"""
    purchase = Purchase.query.filter_by(id=purchase_id, user_id=user.id).first()
    if not purchase:
        return jsonify({"success": False, "error": "Compra no encontrada"}), 404
    
    return jsonify({
        "success": True,
        "purchase": {
            "id": purchase.id,
            "product_id": purchase.product_id,
            "amount": purchase.amount,
            "currency": purchase.currency,
            "status": purchase.status,
            "created_at": purchase.created_at.isoformat(),
            "updated_at": purchase.updated_at.isoformat()
        }
    })

# Rutas para administradores
@app.route("/admin/purchases", methods=["GET"])
@admin_required
def admin_purchases(user):
    """Panel de administración de compras"""
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template("admin_purchases.html", purchases=purchases)

@app.route("/admin/purchase/<int:purchase_id>/update-status", methods=["POST"])
@csrf.exempt
@admin_required
def update_purchase_status(user, purchase_id):
    """Actualizar estado de una compra (admin)"""
    purchase = Purchase.query.get_or_404(purchase_id)
    new_status = request.json.get('status')
    
    if new_status not in ['pending', 'approved', 'rejected']:
        return jsonify({"success": False, "error": "Estado inválido"}), 400
    
    purchase.status = new_status
    purchase.updated_at = datetime.utcnow()
    
    # Si se aprueba la compra, actualizar el rol del usuario
    if new_status == 'approved':
        user_to_update = purchase.user
        # No modificar el super admin
        if not user_to_update.is_super_admin:
            # Asignar rol basado en el producto comprado
            if purchase.product_id == 'signals_bot':
                user_to_update.add_role('signals_bot')
            elif purchase.product_id == 'community_bots':
                user_to_update.add_role('community_bots')
            
            user_to_update.status = 'active'
        
    elif new_status == 'rejected':
        # Si se rechaza, mantener como pending para que pueda intentar de nuevo
        user_to_update = purchase.user
        user_to_update.status = 'pending'
    
    db.session.commit()
    
    # Enviar email al usuario sobre el cambio de estado
    if new_status == 'approved':
        send_email(
            purchase.user.email,
            "Compra Aprobada - Hacks.Casino",
            f"Tu compra de {PRODUCTS[purchase.product_id]['name']} ha sido aprobada. Ya puedes acceder a tu cuenta.",
            f"""
            <html>
            <body>
                <h2>¡Compra Aprobada!</h2>
                <p>Tu compra de <strong>{PRODUCTS[purchase.product_id]['name']}</strong> ha sido aprobada.</p>
                <p>Ya puedes acceder a tu cuenta. Solo inicia sesión para comenzar a usar tu servicio.</p>
                <p>Gracias por confiar en Hacks.Casino</p>
            </body>
            </html>
            """
        )
    elif new_status == 'rejected':
        send_email(
            purchase.user.email,
            "Compra Rechazada - Hacks.Casino",
            f"Tu compra de {PRODUCTS[purchase.product_id]['name']} ha sido rechazada. Por favor, contacta soporte.",
            f"""
            <html>
            <body>
                <h2>Compra Rechazada</h2>
                <p>Tu compra de <strong>{PRODUCTS[purchase.product_id]['name']}</strong> ha sido rechazada.</p>
                <p>Por favor, contacta nuestro equipo de soporte para más información.</p>
                <p>Hacks.Casino</p>
            </body>
            </html>
            """
        )
    
    return jsonify({
        "success": True,
        "message": f"Estado actualizado a {new_status}",
        "purchase_id": purchase.id
    })

@app.route("/products")
def products():
    return jsonify(PRODUCTS)

# ===============================================
# RUTAS API PARA AUTENTICACIÓN CON PIN
# ===============================================

@app.route("/api/auth/check-user", methods=["POST"])
@csrf.exempt
@limiter.limit("20 per minute")  # Máximo 20 verificaciones por minuto
def api_check_user():
    """Verifica si un usuario existe y si tiene PIN configurado"""
    data = request.json
    email = data.get("email", "").strip().lower()
    
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Correo inválido"}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({
            "success": False, 
            "message": "Usuario no registrado",
            "user_exists": False
        }), 404
    
    return jsonify({
        "success": True,
        "user_exists": True,
        "has_pin": user.has_pin(),
        "email": user.email
    })

@app.route("/api/auth/send-pin-verification", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")  # Máximo 5 códigos por minuto por IP
def api_send_pin_verification():
    """Envía un código de verificación antes de crear PIN"""
    data = request.json
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        SecurityLog.log_event(email, 'send_pin_verification_invalid_email', False, 'Email inválido proporcionado')
        return jsonify({"success": False, "message": "Correo inválido"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        SecurityLog.log_event(email, 'send_pin_verification_user_not_found', False, 'Usuario no encontrado')
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
    
    if user.has_pin():
        SecurityLog.log_event(email, 'send_pin_verification_pin_exists', False, 'Usuario ya tiene PIN')
        return jsonify({"success": False, "message": "El usuario ya tiene un PIN configurado"}), 400

    # Crear código usando el sistema seguro
    try:
        code = VerificationCode.create_code(email, 'create_pin', expiry_minutes=10)
    except Exception as e:
        SecurityLog.log_event(email, 'send_pin_verification_error', False, f'Error creando código: {str(e)}')
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500
    
    subject = "Código de verificación para crear PIN - Hacks Casino"
    body_text = f"Tu código de verificación para crear PIN es: {code}"
    body_html = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:#f9f9f9; padding: 20px; color:#333;">
        <div style="max-width:600px; margin:auto; background:#fff; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1); padding:30px;">
          <h2 style="color:#222; text-align:center;">Verificación para Crear PIN</h2>
          <p style="font-size:16px; text-align:center;">Hola,</p>
          <p style="font-size:18px; text-align:center; margin: 30px 0;">
            Tu código para crear tu PIN de seguridad en <strong>Hacks Casino</strong> es:
          </p>
          <div style="font-size: 40px; font-weight: 700; text-align:center; letter-spacing: 8px; background:#000; color:#fff; padding: 15px 0; border-radius: 6px; user-select: all;">
            {code}
          </div>
          <p style="font-size:14px; color:#666; margin-top:40px; text-align:center;">
            Este código es necesario por seguridad al crear tu PIN por primera vez.
          </p>
          <hr style="border:none; border-top:1px solid #eee; margin:40px 0;">
          <p style="font-size:12px; color:#999; text-align:center;">
            &copy; 2025 Hacks Casino. Todos los derechos reservados.
          </p>
        </div>
      </body>
    </html>
    """

    if send_email(email, subject, body_text, body_html):
        SecurityLog.log_event(email, 'send_pin_verification_success', True, 'Código de verificación para PIN enviado exitosamente')
        return jsonify({"success": True, "message": "Código enviado a tu correo"})
    else:
        SecurityLog.log_event(email, 'send_pin_verification_email_error', False, 'Error enviando email')
        return jsonify({"success": False, "message": "Error al enviar el correo"}), 500

@app.route("/api/auth/verify-pin-code", methods=["POST"])
@csrf.exempt
@limiter.limit("10 per minute")  # Máximo 10 intentos de verificación por minuto
def api_verify_pin_code():
    """Verifica el código antes de permitir crear PIN"""
    data = request.json
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip()

    if not email or not code:
        SecurityLog.log_event(email, 'verify_pin_code_missing_data', False, 'Datos faltantes en verificación')
        return jsonify({"success": False, "message": "Faltan datos"}), 400

    # Verificar código usando el sistema seguro
    is_valid, message = VerificationCode.verify_code(email, code, 'create_pin')
    
    if is_valid:
        SecurityLog.log_event(email, 'verify_pin_code_success', True, 'Código de PIN verificado correctamente')
        return jsonify({"success": True, "message": "Código verificado correctamente"})
    else:
        SecurityLog.log_event(email, 'verify_pin_code_failed', False, f'Verificación de PIN fallida: {message}')
        return jsonify({"success": False, "message": message}), 400

@app.route("/api/auth/create-pin", methods=["POST"])
@csrf.exempt
@limiter.limit("10 per minute")  # Máximo 10 creaciones de PIN por minuto
def api_create_pin():
    """Crea un PIN para un usuario existente (requiere código de verificación)"""
    data = request.json
    email = data.get("email", "").strip().lower()
    pin = data.get("pin", "").strip()
    verification_code = data.get("verification_code", "").strip()
    
    if not email or not pin:
        return jsonify({"success": False, "message": "Email y PIN son requeridos"}), 400
    
    if len(pin) != 4 or not pin.isdigit():
        return jsonify({"success": False, "message": "El PIN debe tener exactamente 4 dígitos"}), 400
    
    # Verificar código de verificación nuevamente por seguridad
    if not verification_code:
        return jsonify({"success": False, "message": "Código de verificación requerido"}), 400
    
    # Verificar que el código existe y está marcado como usado (ya fue verificado anteriormente)
    verification_record = VerificationCode.query.filter_by(
        email=email,
        purpose='create_pin',
        is_used=True
    ).filter(
        VerificationCode.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not verification_record or not check_password_hash(verification_record.code_hash, verification_code):
        SecurityLog.log_event(email, 'create_pin_invalid_verification', False, 'Código de verificación inválido al crear PIN')
        return jsonify({"success": False, "message": "Verificación de seguridad requerida"}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
    
    if user.has_pin():
        return jsonify({"success": False, "message": "El usuario ya tiene un PIN configurado"}), 400
    
    if user.set_pin(pin):
        db.session.commit()
        
        # Generar token JWT
        token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        SecurityLog.log_event(email, 'create_pin_success', True, 'PIN creado exitosamente con verificación')
        resp = make_response(jsonify({
            "success": True, 
            "message": "PIN creado exitosamente",
            "redirect": "/user-dashboard"
        }))
        resp.set_cookie('token', token, httponly=True, samesite='Strict')
        return resp
    else:
        return jsonify({"success": False, "message": "Error al crear el PIN"}), 500

@app.route("/api/auth/login-pin", methods=["POST"])
@csrf.exempt
@limiter.limit("15 per minute")  # Máximo 15 intentos de login por minuto
def api_login_pin():
    """Autentica un usuario usando email y PIN"""
    data = request.json
    email = data.get("email", "").strip().lower()
    pin = data.get("pin", "").strip()
    
    if not email or not pin:
        return jsonify({"success": False, "message": "Email y PIN son requeridos"}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
    
    if not user.has_pin():
        return jsonify({"success": False, "message": "El usuario no tiene PIN configurado"}), 400
    
    if not user.verify_pin(pin):
        SecurityLog.log_event(email, 'login_pin_failed', False, 'PIN incorrecto')
        return jsonify({"success": False, "message": "PIN incorrecto"}), 401
    
    # Generar token JWT
    token = jwt.encode({
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    SecurityLog.log_event(email, 'login_pin_success', True, 'Login exitoso con PIN')
    resp = make_response(jsonify({
        "success": True, 
        "message": "Inicio de sesión exitoso",
        "redirect": "/user-dashboard"
    }))
    resp.set_cookie('token', token, httponly=True, samesite='Strict')
    return resp

@app.route("/api/auth/reset-pin", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")  # Máximo 5 intentos de reset por minuto
def api_reset_pin():
    """Restablece el PIN de un usuario (requiere código de verificación)"""
    data = request.json
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip()
    new_pin = data.get("new_pin", "").strip()
    
    if not email or not code or not new_pin:
        SecurityLog.log_event(email, 'reset_pin_missing_data', False, 'Datos faltantes en reset PIN')
        return jsonify({"success": False, "message": "Email, código y nuevo PIN son requeridos"}), 400
    
    if len(new_pin) != 4 or not new_pin.isdigit():
        SecurityLog.log_event(email, 'reset_pin_invalid_format', False, 'PIN con formato inválido')
        return jsonify({"success": False, "message": "El PIN debe tener exactamente 4 dígitos"}), 400
    
    # Verificar código de verificación usando sistema seguro
    is_valid, message = VerificationCode.verify_code(email, code, 'reset_pin')
    if not is_valid:
        SecurityLog.log_event(email, 'reset_pin_invalid_code', False, f'Código inválido: {message}')
        return jsonify({"success": False, "message": message}), 401
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        SecurityLog.log_event(email, 'reset_pin_user_not_found', False, 'Usuario no encontrado en reset PIN')
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
    
    # Actualizar PIN
    if user.set_pin(new_pin):
        db.session.commit()
        SecurityLog.log_event(email, 'reset_pin_success', True, 'PIN actualizado exitosamente')
        return jsonify({"success": True, "message": "PIN actualizado exitosamente"})
    else:
        SecurityLog.log_event(email, 'reset_pin_error', False, 'Error al actualizar PIN')
        return jsonify({"success": False, "message": "Error al actualizar el PIN"}), 500

# ===============================================
# RUTAS API PARA WEBSOCKET SEGURO
# ===============================================

@app.route("/api/websocket/auth", methods=["POST"])
@csrf.exempt
@jwt_login_required
@limiter.limit("30 per minute")  # Máximo 30 tokens por minuto
def websocket_auth(user):
    """Genera token de autenticación para WebSocket seguro"""
    
    # Verificar que el usuario tenga el rol necesario
    if not user.has_role('signals_bot'):
        SecurityLog.log_event(user.email, 'websocket_auth_role_denied', False, f'Usuario sin rol signals_bot intentó acceder a WebSocket')
        return jsonify({"success": False, "error": "Rol insuficiente. Se requiere rol signals_bot"}), 403
    
    # Verificar que el usuario esté activo
    if user.status != 'active':
        SecurityLog.log_event(user.email, 'websocket_auth_status_denied', False, f'Usuario inactivo intentó acceder a WebSocket')
        return jsonify({"success": False, "error": "Cuenta inactiva. Contacta soporte"}), 403
    
    # Generar token específico para WebSocket con información del usuario
    ws_token = jwt.encode({
        'user_id': user.id,
        'email': user.email,
        'roles': user.get_roles_list(),
        'status': user.status,
        'is_super_admin': user.is_super_admin,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1),  # Token válido por 1 hora
        'type': 'websocket_auth'  # Tipo específico para WebSocket
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    # Log de acceso exitoso
    SecurityLog.log_event(user.email, 'websocket_auth_success', True, f'Token WebSocket generado para usuario {user.email}')
    
    return jsonify({
        "success": True,
        "ws_token": ws_token,
        "expires_in": 3600,  # 1 hora en segundos
        "user_info": {
            "email": user.email,
            "roles": user.get_roles_list(),
            "status": user.status
        }
    })

@app.route("/api/websocket/verify", methods=["POST"])
@csrf.exempt
@limiter.limit("100 per minute")  # Máximo 100 verificaciones por minuto
def websocket_verify():
    """Verifica un token WebSocket (para validación externa)"""
    data = request.json
    ws_token = data.get("ws_token", "").strip()
    
    if not ws_token:
        return jsonify({"success": False, "error": "Token requerido"}), 400
    
    try:
        # Decodificar token
        payload = jwt.decode(ws_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        
        # Verificar que sea un token de WebSocket
        if payload.get('type') != 'websocket_auth':
            return jsonify({"success": False, "error": "Tipo de token inválido"}), 400
        
        # Verificar que el usuario existe y está activo
        user = User.query.get(payload.get('user_id'))
        if not user or user.status != 'active':
            return jsonify({"success": False, "error": "Usuario no válido"}), 400
        
        # Verificar que tenga el rol necesario
        if 'signals_bot' not in payload.get('roles', []):
            return jsonify({"success": False, "error": "Rol insuficiente"}), 403
        
        return jsonify({
            "success": True,
            "valid": True,
            "user_info": {
                "user_id": user.id,
                "email": user.email,
                "roles": user.get_roles_list(),
                "status": user.status
            },
            "expires_at": payload.get('exp')
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({"success": False, "error": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "error": "Token inválido"}), 401
    except Exception as e:
        SecurityLog.log_event(None, 'websocket_verify_error', False, f'Error verificando token: {str(e)}')
        return jsonify({"success": False, "error": "Error interno del servidor"}), 500

@app.route("/api/websocket/status", methods=["GET"])
@jwt_login_required
@limiter.limit("60 per minute")  # Máximo 60 consultas por minuto
def websocket_status(user):
    """Obtiene el estado de conexión WebSocket del usuario"""
    
    if not user.has_role('signals_bot'):
        return jsonify({"success": False, "error": "Rol insuficiente"}), 403
    
    # Aquí podrías implementar lógica para verificar si el usuario está conectado
    # Por ahora retornamos información básica
    return jsonify({
        "success": True,
        "websocket_available": True,
        "user_authorized": True,
        "roles": user.get_roles_list(),
        "status": user.status
    })

@app.route("/api/security/audit-log", methods=["GET"])
@jwt_login_required
@limiter.limit("10 per minute")  # Máximo 10 consultas por minuto
def security_audit_log(user):
    """Obtiene el log de auditoría de seguridad del usuario (solo admins)"""
    
    if not user.has_role('Admin'):
        SecurityLog.log_event(user.email, 'audit_log_access_denied', False, 'Usuario no admin intentó acceder a log de auditoría')
        return jsonify({"success": False, "error": "Acceso denegado. Solo administradores"}), 403
    
    # Obtener logs de seguridad del usuario
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)  # Máximo 100 por página
    
    logs = SecurityLog.query.filter_by(user_email=user.email)\
        .order_by(SecurityLog.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "success": True,
        "logs": [{
            "id": log.id,
            "action": log.action,
            "success": log.success,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        } for log in logs.items],
        "pagination": {
            "page": logs.page,
            "pages": logs.pages,
            "per_page": logs.per_page,
            "total": logs.total
        }
    })

@app.route("/user-dashboard")
@jwt_login_required
def user_dashboard(user):
    # Si es super admin, redirigir directamente al dashboard de admin
    if user.is_super_admin:
        return redirect('/dashboard')
    
    # Si el usuario está pendiente, mostrar página de espera
    if user.role == 'pending' or user.status == 'pending':
        # Obtener compras del usuario para mostrar historial
        purchases = Purchase.query.filter_by(user_id=user.id).order_by(Purchase.created_at.desc()).all()
        return render_template('pending_approval.html', user=user, purchases=purchases, products=PRODUCTS)
    
    # Verificar roles específicos para usuarios activos
    if user.status == 'active':
        if user.has_role('signals_bot'):
            return render_template('signals_casino.html', user=user)
        elif user.has_role('community_bots'):
            return render_template('community_bots.html', user=user)
        elif user.has_role('Admin'):
            # Si es admin, redirigir al dashboard de admin
            return redirect('/dashboard')
    
    # Por seguridad, si no cumple ninguna condición, enviar a página de espera
    purchases = Purchase.query.filter_by(user_id=user.id).order_by(Purchase.created_at.desc()).all()
    return render_template('pending_approval.html', user=user, purchases=purchases, products=PRODUCTS)

@app.route("/signals-casino")
@jwt_login_required
def signals_casino(user):
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('signals_casino.html', user=user)

@app.route("/community-bots")
@jwt_login_required
def community_bots(user):
    if not user.has_role('community_bots'):
        return redirect('/user-dashboard')
    return render_template('community_bots.html', user=user)

# ===============================================
# RUTAS ESPECÍFICAS PARA CADA JUEGO
# ===============================================

@app.route("/aviator-signals")
@jwt_login_required
def aviator_signals(user):
    """Página de señales específicas para Aviator"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('aviator_signals.html', user=user)

@app.route("/1win-aviator")
@jwt_login_required
def onewin_aviator(user):
    """Página de señales específicas para 1Win Aviator"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('1win_aviator.html', user=user)

@app.route("/888starz-aviator")
@jwt_login_required
def eighteighteightstarz_aviator(user):
    """Página de señales específicas para 888starz Aviator"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('888starz_aviator.html', user=user)

@app.route("/roulette-signals")
@jwt_login_required
def roulette_signals(user):
    """Página de señales específicas para Ruleta en Vivo"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('roulette_signals.html', user=user)

@app.route("/mega-roulette")
@jwt_login_required
def mega_roulette(user):
    """Página de señales específicas para Mega Roulette (Puerto 8865)"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('mega_roulette.html', user=user, puerto=8865, ruleta_id=204)

@app.route("/roulette-azure")
@jwt_login_required
def roulette_azure(user):
    """Página de señales específicas para Roulette Azure (Puerto 8866)"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('roulette_azure.html', user=user, puerto=8866, ruleta_id=227)

@app.route("/roulette-ruby")
@jwt_login_required
def roulette_ruby(user):
    """Página de señales específicas para Roulette Ruby (Puerto 8867)"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('roulette_ruby.html', user=user, puerto=8867, ruleta_id=230)

@app.route("/auto-roulette")
@jwt_login_required
def auto_roulette(user):
    """Página de señales específicas para Auto Roulette (Puerto 8868)"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('auto_roulette.html', user=user, puerto=8868, ruleta_id=225)

@app.route("/spaceman-signals")
@jwt_login_required
def spaceman_signals(user):
    """Página de señales específicas para Spaceman"""
    if not user.has_role('signals_bot'):
        return redirect('/user-dashboard')
    return render_template('spaceman_signals.html', user=user)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)


