# Инструкция по заполнению справочников

## Способ 1: Через flask shell (рекомендуется)

1. Открой терминал в папке `backend`
2. Активируй виртуальное окружение (если нужно):
   ```
   .venv\Scripts\activate
   ```

3. Установи переменные окружения (если нужно):
   ```
   $env:FLASK_APP = "wsgi.py"
   $env:DATABASE_URL = "postgresql://postgres:пароль@localhost:5432/kit_db"
   ```

4. Запусти flask shell:
   ```
   flask shell
   ```

5. Выполни команды из файла `seed_data.py`:
   ```
   >>> exec(open('seed_data.py', encoding='utf-8').read())
   ```

6. Выйди из shell:
   ```
   >>> exit()
   ```

## Способ 2: Прямое выполнение команд в shell

Если хочешь выполнить команды напрямую, скопируй и вставь в `flask shell`:

```python
from app.extensions import db
from app.models.roles import Role
from app.models.interests import Interest
from app.models.skills import SkillCategory, Skill

# Роли
roles = [
    Role(code="teamlead", name="Тимлид"),
    Role(code="backend", name="Backend-разработчик"),
    Role(code="frontend", name="Frontend-разработчик"),
    Role(code="fullstack", name="Fullstack-разработчик"),
    Role(code="designer", name="Дизайнер"),
    Role(code="analyst", name="Аналитик"),
    Role(code="qa", name="QA-инженер"),
    Role(code="devops", name="DevOps-инженер"),
    Role(code="mobile", name="Mobile-разработчик"),
    Role(code="pm", name="Product Manager"),
]

for role in roles:
    if not Role.query.filter_by(code=role.code).first():
        db.session.add(role)

# Интересы
interests = [
    "Frontend-разработка",
    "Backend-разработка",
    "Fullstack-разработка",
    "Mobile-разработка",
    "Дизайн",
    "UI/UX",
    "AI и машинное обучение",
    "Data Science",
    "Кибербезопасность",
    "DevOps",
    "Blockchain",
    "Game Development",
    "Web3",
    "Аналитика данных",
    "Тестирование",
    "Проектный менеджмент",
]

for name in interests:
    if not Interest.query.filter_by(name=name).first():
        db.session.add(Interest(name=name))

# Категории навыков
categories = [
    SkillCategory(name="Разработка"),
    SkillCategory(name="Дизайн"),
    SkillCategory(name="Аналитика"),
    SkillCategory(name="Управление"),
    SkillCategory(name="Инфраструктура"),
]

categories_map = {}
for cat in categories:
    existing = SkillCategory.query.filter_by(name=cat.name).first()
    if not existing:
        db.session.add(cat)
        db.session.flush()
        categories_map[cat.name] = cat
    else:
        categories_map[cat.name] = existing

# Навыки (примеры - полный список в seed_data.py)
skills = [
    Skill(name="Python", category_id=categories_map["Разработка"].id),
    Skill(name="JavaScript", category_id=categories_map["Разработка"].id),
    Skill(name="React", category_id=categories_map["Разработка"].id),
    Skill(name="Figma", category_id=categories_map["Дизайн"].id),
    # ... добавь остальные из seed_data.py
]

for skill in skills:
    if not Skill.query.filter_by(name=skill.name).first():
        db.session.add(skill)

# Сохранение
db.session.commit()
print("✅ Данные добавлены!")
```

## Что будет добавлено

- **10 ролей** (Тимлид, Backend, Frontend, и т.д.)
- **16 интересов** (Frontend-разработка, AI, и т.д.)
- **5 категорий навыков** (Разработка, Дизайн, Аналитика, Управление, Инфраструктура)
- **~80 навыков** (Python, JavaScript, React, Figma, и т.д.)

## Проверка

После выполнения можно проверить:

```python
>>> Role.query.count()
>>> Interest.query.count()
>>> SkillCategory.query.count()
>>> Skill.query.count()
```
