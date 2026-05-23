# Green Invest — Backend Django
## Données satellitaires Copernicus / Sentinel-2 pour la zone UEMOA

---

## 1. Installation des dépendances

Ouvre un terminal dans ce dossier et tape :

```bash
pip install -r requirements.txt
```

---

## 2. Configure tes clés Copernicus

Ouvre le fichier `greeninvest/settings.py` et remplace :

```python
COP_CLIENT_ID     = 'sh-REMPLACE-MOI'
COP_CLIENT_SECRET = 'SECRET-REMPLACE-MOI'
```

Par tes vraies clés OAuth Copernicus (celles qui commencent par `sh-`).

---

## 3. Lance le serveur

```bash
python manage.py runserver
```

Le serveur démarre sur : http://127.0.0.1:8000

---

## 4. Connecte le dashboard

Dans ton fichier `index.html`, les appels API vont maintenant vers :

| Endpoint                              | Ce qu'il fait                          |
|---------------------------------------|----------------------------------------|
| GET /api/status/                      | Vérifie la connexion Copernicus        |
| GET /api/ndvi/?pays=BEN&index=ndvi    | NDVI pour le Bénin                     |
| GET /api/ndvi/all/?index=ndvi         | NDVI pour les 8 pays UEMOA             |
| GET /api/humidity/?period=2024-09     | Humidité des sols (MSI + NDWI)         |

---

## 5. Structure du projet

```
greeninvest_backend/
├── manage.py
├── requirements.txt
├── greeninvest/
│   ├── settings.py      ← Mets tes clés Copernicus ici
│   ├── urls.py
│   └── wsgi.py
└── api/
    ├── copernicus_service.py   ← Logique Sentinel-2
    ├── views.py                ← Endpoints JSON
    └── urls.py
```

---

## 6. Test rapide

Ouvre ton navigateur sur :
```
http://127.0.0.1:8000/api/status/
```

Tu dois voir :
```json
{"ok": true, "message": "Copernicus connecté", "token_preview": "eyJ..."}
```

Si tu vois une erreur, vérifie tes clés dans `settings.py`.
