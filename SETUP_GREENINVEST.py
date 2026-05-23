"""
╔══════════════════════════════════════════════════════════════════╗
║          GreenInvest — SETUP COMPLET EN UN SEUL FICHIER          ║
║  Résout les 404 + crée le Super Admin + configure tout Django    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  INSTRUCTIONS :                                                  ║
║  1. Copie ce fichier dans :                                      ║
║     C:\Users\HP\Desktop\MEMOIRE\Vrai\greeninvest_backend\        ║
║  2. Lance : python SETUP_GREENINVEST.py                          ║
║  3. C'est tout !                                                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import textwrap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────
# COULEURS TERMINAL
# ─────────────────────────────────────────────────────────────────
G  = '\033[92m'   # vert
Y  = '\033[93m'   # jaune
R  = '\033[91m'   # rouge
B  = '\033[94m'   # bleu
P  = '\033[95m'   # violet
W  = '\033[97m'   # blanc
RS = '\033[0m'    # reset

def ok(msg):   print(f"{G}  ✓  {msg}{RS}")
def warn(msg): print(f"{Y}  ⚠  {msg}{RS}")
def err(msg):  print(f"{R}  ✗  {msg}{RS}")
def info(msg): print(f"{B}  →  {msg}{RS}")
def title(msg):print(f"\n{P}{'═'*60}\n  {msg}\n{'═'*60}{RS}")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 1 — Détecter le nom du package Django (dossier settings)
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 1 — Détection du projet Django")

DJANGO_PKG = None
for name in os.listdir(BASE_DIR):
    path = os.path.join(BASE_DIR, name)
    if os.path.isdir(path) and os.path.exists(os.path.join(path, 'settings.py')):
        DJANGO_PKG = name
        break

if not DJANGO_PKG:
    err("Impossible de trouver le dossier settings.py. Lance ce script depuis la racine du projet Django.")
    sys.exit(1)

ok(f"Package Django détecté : {W}{DJANGO_PKG}{RS}")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 2 — Détecter l'app d'authentification
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 2 — Détection de l'app d'authentification")

AUTH_APP = None
for candidate in ['authentication', 'auth_app', 'accounts', 'users']:
    if os.path.isdir(os.path.join(BASE_DIR, candidate)):
        AUTH_APP = candidate
        break

if not AUTH_APP:
    warn("Aucune app d'authentification trouvée. Création de l'app 'authentication'...")
    AUTH_APP = 'authentication'
    app_dir = os.path.join(BASE_DIR, AUTH_APP)
    os.makedirs(os.path.join(app_dir, 'migrations'), exist_ok=True)
    # __init__.py
    for f in [
        os.path.join(app_dir, '__init__.py'),
        os.path.join(app_dir, 'migrations', '__init__.py'),
    ]:
        open(f, 'w').close()
    ok(f"App '{AUTH_APP}' créée.")
else:
    ok(f"App d'authentification : {W}{AUTH_APP}{RS}")

APP_DIR = os.path.join(BASE_DIR, AUTH_APP)

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 3 — Écrire models.py
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 3 — Modèle utilisateur")

MODELS_PY = textwrap.dedent(f"""\
from django.contrib.auth.models import AbstractUser
from django.db import models

ROLES = [
    ('analyste',      'Analyste'),
    ('investisseur',  'Investisseur'),
    ('admin',         'Admin'),
    ('superadmin',    'Super Admin'),
]

class GreenUser(AbstractUser):
    prenom       = models.CharField(max_length=100, blank=True)
    nom          = models.CharField(max_length=100, blank=True)
    organisation = models.CharField(max_length=200, blank=True)
    pays         = models.CharField(max_length=10,  blank=True)
    role         = models.CharField(max_length=20, choices=ROLES, default='analyste')
    message      = models.TextField(blank=True)
    otp_code     = models.CharField(max_length=6,  blank=True)
    otp_expires  = models.DateTimeField(null=True,  blank=True)

    def __str__(self):
        return f"{{self.username}} ({{self.role}})"
""")

models_path = os.path.join(APP_DIR, 'models.py')
with open(models_path, 'w', encoding='utf-8') as f:
    f.write(MODELS_PY)
ok("models.py écrit")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 4 — Écrire serializers.py
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 4 — Serializers")

SERIALIZERS_PY = textwrap.dedent(f"""\
from rest_framework import serializers
from .models import GreenUser

class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = GreenUser
        fields = ['prenom','nom','organisation','pays','username','email',
                  'password','password2','role','message']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({{'password': 'Les mots de passe ne correspondent pas.'}})
        if data.get('role') == 'superadmin':
            if GreenUser.objects.filter(role='superadmin').exists():
                raise serializers.ValidationError({{'role': 'Un Super Admin existe déjà.'}})
        if data.get('role') == 'admin':
            raise serializers.ValidationError({{'role': 'Le rôle Admin ne peut être octroyé que par un Super Admin.'}})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        role = validated_data.get('role', 'analyste')
        user = GreenUser(**validated_data)
        user.set_password(password)
        if role == 'superadmin':
            user.is_staff     = True
            user.is_superuser = True
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GreenUser
        fields = ['id','username','email','prenom','nom','role','organisation','pays']
""")

serializers_path = os.path.join(APP_DIR, 'serializers.py')
with open(serializers_path, 'w', encoding='utf-8') as f:
    f.write(SERIALIZERS_PY)
ok("serializers.py écrit")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 5 — Écrire views.py
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 5 — Vues API")

VIEWS_PY = textwrap.dedent(f"""\
import random, string
from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import GreenUser
from .serializers import RegisterSerializer, UserSerializer


def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {{'refresh': str(refresh), 'access': str(refresh.access_token)}}


# ── Vérifier si un super admin existe ──────────────────────────
class SuperAdminExistsView(APIView):
    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        exists = GreenUser.objects.filter(role='superadmin').exists()
        return Response({{'exists': exists}})


# ── Inscription ────────────────────────────────────────────────
class RegisterView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user   = serializer.save()
            tokens = get_tokens(user)
            return Response(
                {{'user': UserSerializer(user).data, 'tokens': tokens}},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Connexion ──────────────────────────────────────────────────
class LoginView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        identifier = request.data.get('username', '').strip()
        password   = request.data.get('password', '')

        # Chercher par username ou email
        user = None
        try:
            u = GreenUser.objects.get(email=identifier)
            user = authenticate(request, username=u.username, password=password)
        except GreenUser.DoesNotExist:
            user = authenticate(request, username=identifier, password=password)

        if user:
            tokens = get_tokens(user)
            data   = UserSerializer(user).data
            data['tokens'] = tokens
            return Response(data)
        return Response(
            {{'detail': 'Identifiants incorrects.'}},
            status=status.HTTP_401_UNAUTHORIZED
        )


# ── Mot de passe oublié — envoi OTP ────────────────────────────
class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        email = request.data.get('email', '').strip()
        try:
            user = GreenUser.objects.get(email=email)
        except GreenUser.DoesNotExist:
            # Réponse neutre pour ne pas révéler si l'email existe
            return Response({{'detail': 'Si cet e-mail est enregistré, un code vous a été envoyé.'}})

        # Générer OTP 6 chiffres
        otp = ''.join(random.choices(string.digits, k=6))
        user.otp_code    = otp
        user.otp_expires = timezone.now() + timedelta(minutes=10)
        user.save()

        # Envoyer l'email (configure settings.py pour l'email)
        try:
            send_mail(
                subject='GreenInvest — Code de vérification',
                message=f'Votre code de vérification est : {{otp}}\\nIl expire dans 10 minutes.',
                from_email=None,
                recipient_list=[email],
            )
        except Exception:
            # En dev sans email configuré — afficher le code dans la réponse
            return Response({{'detail': 'Code envoyé.', 'dev_otp': otp}})

        return Response({{'detail': 'Code envoyé.'}})


# ── Vérification OTP ───────────────────────────────────────────
class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        email = request.data.get('email', '').strip()
        otp   = request.data.get('otp',   '').strip()
        try:
            user = GreenUser.objects.get(email=email)
        except GreenUser.DoesNotExist:
            return Response({{'detail': 'Email introuvable.'}}, status=400)

        if not user.otp_code or user.otp_code != otp:
            return Response({{'detail': 'Code incorrect.'}}, status=400)
        if user.otp_expires and timezone.now() > user.otp_expires:
            return Response({{'detail': 'Code expiré. Recommencez.'}}, status=400)

        return Response({{'detail': 'Code valide.', 'email': email}})


# ── Réinitialisation du mot de passe ──────────────────────────
class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        email    = request.data.get('email',    '').strip()
        otp      = request.data.get('otp',      '').strip()
        password = request.data.get('password', '')

        try:
            user = GreenUser.objects.get(email=email)
        except GreenUser.DoesNotExist:
            return Response({{'detail': 'Email introuvable.'}}, status=400)

        if not user.otp_code or user.otp_code != otp:
            return Response({{'detail': 'Code invalide.'}}, status=400)
        if user.otp_expires and timezone.now() > user.otp_expires:
            return Response({{'detail': 'Code expiré.'}}, status=400)
        if len(password) < 8:
            return Response({{'detail': 'Mot de passe trop court.'}}, status=400)

        user.set_password(password)
        user.otp_code    = ''
        user.otp_expires = None
        user.save()
        return Response({{'detail': 'Mot de passe mis à jour avec succès.'}})
""")

views_path = os.path.join(APP_DIR, 'views.py')
with open(views_path, 'w', encoding='utf-8') as f:
    f.write(VIEWS_PY)
ok("views.py écrit")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 6 — Écrire urls.py de l'app
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 6 — URLs de l'app")

URLS_APP_PY = textwrap.dedent(f"""\
from django.urls import path
from .views import (
    RegisterView, LoginView, ForgotPasswordView,
    VerifyOTPView, ResetPasswordView, SuperAdminExistsView
)

urlpatterns = [
    path('register/',           RegisterView.as_view(),          name='register'),
    path('login/',              LoginView.as_view(),              name='login'),
    path('forgot-password/',    ForgotPasswordView.as_view(),     name='forgot-password'),
    path('verify-otp/',         VerifyOTPView.as_view(),          name='verify-otp'),
    path('reset-password/',     ResetPasswordView.as_view(),      name='reset-password'),
    path('superadmin-exists/',  SuperAdminExistsView.as_view(),   name='superadmin-exists'),
]
""")

urls_app_path = os.path.join(APP_DIR, 'urls.py')
with open(urls_app_path, 'w', encoding='utf-8') as f:
    f.write(URLS_APP_PY)
ok("authentication/urls.py écrit")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 7 — Patcher urls.py principal
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 7 — URLs principales du projet")

URLS_MAIN_PY = textwrap.dedent(f"""\
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('{AUTH_APP}.urls')),
]
""")

urls_main_path = os.path.join(BASE_DIR, DJANGO_PKG, 'urls.py')
with open(urls_main_path, 'w', encoding='utf-8') as f:
    f.write(URLS_MAIN_PY)
ok(f"{DJANGO_PKG}/urls.py mis à jour")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 8 — Patcher settings.py
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 8 — Settings Django")

settings_path = os.path.join(BASE_DIR, DJANGO_PKG, 'settings.py')
with open(settings_path, 'r', encoding='utf-8') as f:
    settings_content = f.read()

# AUTH_USER_MODEL
if 'AUTH_USER_MODEL' not in settings_content:
    settings_content += f"\n\nAUTH_USER_MODEL = '{AUTH_APP}.GreenUser'\n"
    ok("AUTH_USER_MODEL ajouté")
else:
    warn("AUTH_USER_MODEL déjà présent — vérifie qu'il pointe vers GreenUser")

# INSTALLED_APPS — ajouter les apps manquantes
apps_to_add = [AUTH_APP, 'rest_framework', 'corsheaders', 'rest_framework_simplejwt']
for app in apps_to_add:
    if app not in settings_content:
        settings_content = settings_content.replace(
            "INSTALLED_APPS = [",
            f"INSTALLED_APPS = [\n    '{app}',"
        )
        ok(f"'{app}' ajouté à INSTALLED_APPS")
    else:
        info(f"'{app}' déjà dans INSTALLED_APPS")

# CORS
if 'CORS_ALLOW_ALL_ORIGINS' not in settings_content:
    settings_content += "\n\n# CORS\nCORS_ALLOW_ALL_ORIGINS = True\n"
    ok("CORS_ALLOW_ALL_ORIGINS ajouté")

# MIDDLEWARE corsheaders
if 'CorsMiddleware' not in settings_content:
    settings_content = settings_content.replace(
        "MIDDLEWARE = [",
        "MIDDLEWARE = [\n    'corsheaders.middleware.CorsMiddleware',"
    )
    ok("CorsMiddleware ajouté")

# REST_FRAMEWORK
if 'REST_FRAMEWORK' not in settings_content:
    settings_content += """
\n# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
"""
    ok("REST_FRAMEWORK ajouté")

with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(settings_content)
ok("settings.py mis à jour")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 9 — Installer les dépendances manquantes
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 9 — Vérification des dépendances Python")

packages = ['djangorestframework', 'django-cors-headers', 'djangorestframework-simplejwt']
for pkg in packages:
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', pkg, '-q'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            ok(f"{pkg} installé/vérifié")
        else:
            warn(f"Problème avec {pkg}: {result.stderr[:80]}")
    except Exception as e:
        warn(f"Impossible d'installer {pkg}: {e}")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 10 — Migrations
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 10 — Migrations")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{DJANGO_PKG}.settings')

def run_manage(args, label):
    result = subprocess.run(
        [sys.executable, 'manage.py'] + args,
        cwd=BASE_DIR, capture_output=True, text=True
    )
    if result.returncode == 0:
        ok(label)
    else:
        warn(f"{label} — attention: {result.stderr[-200:]}")
    return result

run_manage(['makemigrations', AUTH_APP], "makemigrations authentication")
run_manage(['makemigrations'],           "makemigrations global")
run_manage(['migrate'],                  "migrate")

# ─────────────────────────────────────────────────────────────────
# ÉTAPE 11 — Créer le Super Admin
# ─────────────────────────────────────────────────────────────────
title("ÉTAPE 11 — Création du Super Admin")

print(f"""
{W}Renseignez les informations du Super Admin :{RS}
""")

import django
django.setup()

from authentication.models import GreenUser  # noqa — après setup

# Vérifier s'il en existe déjà un
existing_sa = GreenUser.objects.filter(role='superadmin').first()
if existing_sa:
    warn(f"Un Super Admin existe déjà : {existing_sa.username} ({existing_sa.email})")
    print(f"{Y}  Voulez-vous en créer un nouveau quand même ? (o/N) :{RS} ", end='')
    choice = input().strip().lower()
    if choice != 'o':
        info("Création ignorée.")
        existing_sa = existing_sa
        new_sa = None
    else:
        existing_sa = None
else:
    existing_sa = None

if existing_sa is None:
    print(f"{W}  Prénom         :{RS} ", end=''); prenom = input().strip()
    print(f"{W}  Nom            :{RS} ", end=''); nom    = input().strip()
    print(f"{W}  Username       :{RS} ", end=''); uname  = input().strip()
    print(f"{W}  Email          :{RS} ", end=''); email  = input().strip()
    print(f"{W}  Mot de passe   :{RS} ", end='')
    import getpass
    pwd = getpass.getpass('')

    if not uname or not pwd:
        err("Username et mot de passe sont obligatoires.")
    else:
        try:
            sa = GreenUser.objects.create_superuser(
                username     = uname,
                email        = email,
                password     = pwd,
                prenom       = prenom,
                nom          = nom,
                role         = 'superadmin',
                is_staff     = True,
                is_superuser = True,
            )
            ok(f"Super Admin créé : {W}{sa.username}{RS} ({sa.email})")
        except Exception as e:
            err(f"Erreur lors de la création : {e}")

# ─────────────────────────────────────────────────────────────────
# RÉSUMÉ FINAL
# ─────────────────────────────────────────────────────────────────
title("✅ SETUP TERMINÉ")

print(f"""
{G}  Routes API disponibles :{RS}
  POST  http://localhost:8000/api/auth/register/
  POST  http://localhost:8000/api/auth/login/
  POST  http://localhost:8000/api/auth/forgot-password/
  POST  http://localhost:8000/api/auth/verify-otp/
  POST  http://localhost:8000/api/auth/reset-password/
  GET   http://localhost:8000/api/auth/superadmin-exists/
  GET   http://localhost:8000/admin/

{W}  Lance le serveur avec :{RS}
  python manage.py runserver

{P}  Clé Super Admin (frontend) :{RS} GI-SUPER-2024
{P}  Interface admin Django     :{RS} http://127.0.0.1:8000/admin/
""")
