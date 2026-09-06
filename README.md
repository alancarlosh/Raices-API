# Raíces API

Backend (Django + DRF) de "Raíces": plataforma para enseñanza y práctica de lenguas
originarias mediante un videojuego 2D de exploración de una casa. Ver el repo hermano
`Raices-Front` (React + Phaser) para el cliente.

## Setup local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Por defecto usa SQLite. Para PostgreSQL define `DATABASE_URL` en `.env`.

## Estructura

Patrón **Services + Selectors** (Django Styleguide de HackSoft): `models.py` solo
estructura, `selectors.py` consultas de solo lectura, `services.py` lógica de negocio
y escritura, `views.py` delgadas (solo orquestan).

- `apps/accounts` — usuario custom con rol (aprendiz / hablante_revisor / admin), JWT.
- `apps/languages` — catálogo de lenguas originarias.
- `apps/content` — `Escena` (cuarto) → `ObjetoInteractivo`, con flujo de moderación
  (borrador / en_revision / publicado) vía el admin de Django.
- `apps/progress` — `ProgresoUsuario` (objetos descubiertos) e `IntentoEscritura`
  (histórico de intentos de escritura).

**Restricción lingüística crítica:** la validación de escritura normaliza ambos
strings a Unicode NFC antes de comparar, pero nunca usa `unidecode` ni elimina
diacríticos — el saltillo (Ꞌ) y las vocales largas cambian el significado de la
palabra en varias lenguas originarias. Ver `apps/progress/services.py`.

## Endpoints

- `POST /api/token/` / `POST /api/token/refresh/` — JWT.
- `GET /api/escenas/<id>/` — escena con sus objetos publicados (cacheada 15 min).
- `POST /api/objetos/<id>/descubrir/` — marca un objeto como descubierto.
- `POST /api/objetos/<id>/intento-escritura/` — body `{"texto_ingresado": "..."}`.
- `GET /api/progreso/` — % de objetos descubiertos por escena.

## Tests

```bash
python -m pytest
```
