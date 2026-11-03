# Project conventions

- Keep the existing Flask application factory in `app/__init__.py`; initialize
  extensions there and register new route modules as blueprints.
- Put shared Flask extensions in `app/extensions.py`. Define database models
  and their relationships in `app/models.py`.
- Keep route handlers in `app/blueprints/` and reusable analytics or data
  processing in `app/services/`. Avoid putting substantial business logic in
  routes.
- Extend `app/templates/base.html` for new pages and reuse the existing
  templates in `app/templates/partials/`.
- Use `url_for` for internal links and endpoint references.
- Follow PEP 8, use clear beginner-friendly names, and keep changes focused.
- Read configuration from environment variables. Do not add hardcoded secrets
  or commit `.env` files; use `.env.example` for safe placeholders.
- Keep SQLite databases, virtual environments, caches, Spark work directories,
  and other local runtime files out of commits. Keep project sample CSV files
  under `data/` tracked.
- Create feature branches named `feature/<name>`. Submit changes through a
  Pull Request; do not push feature work directly to `main`.
