"""
Скрипт для заполнения справочников (роли, интересы, категории навыков, навыки).
Запускать через flask shell:
    flask shell
    >>> exec(open('seed_data.py', encoding='utf-8').read())
"""

from app.extensions import db
from app.models.roles import Role
from app.models.interests import Interest
from app.models.skills import SkillCategory, Skill

# Очистка существующих данных (опционально)
# db.session.query(Skill).delete()
# db.session.query(SkillCategory).delete()
# db.session.query(Interest).delete()
# db.session.query(Role).delete()

# 1. Роли в команде
roles_data = [
    {"code": "teamlead", "name": "Тимлид"},
    {"code": "backend", "name": "Backend-разработчик"},
    {"code": "frontend", "name": "Frontend-разработчик"},
    {"code": "fullstack", "name": "Fullstack-разработчик"},
    {"code": "designer", "name": "Дизайнер"},
    {"code": "analyst", "name": "Аналитик"},
    {"code": "qa", "name": "QA-инженер"},
    {"code": "devops", "name": "DevOps-инженер"},
    {"code": "mobile", "name": "Mobile-разработчик"},
    {"code": "pm", "name": "Product Manager"},
]

for role_data in roles_data:
    existing = Role.query.filter_by(code=role_data["code"]).first()
    if not existing:
        role = Role(**role_data)
        db.session.add(role)
        print(f"Добавлена роль: {role_data['name']}")

# 2. Интересы
interests_data = [
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

for interest_name in interests_data:
    existing = Interest.query.filter_by(name=interest_name).first()
    if not existing:
        interest = Interest(name=interest_name)
        db.session.add(interest)
        print(f"Добавлен интерес: {interest_name}")

# 3. Категории навыков
categories_data = [
    {"name": "Разработка"},
    {"name": "Дизайн"},
    {"name": "Аналитика"},
    {"name": "Управление"},
    {"name": "Инфраструктура"},
]

categories_map = {}
for cat_data in categories_data:
    existing = SkillCategory.query.filter_by(name=cat_data["name"]).first()
    if not existing:
        category = SkillCategory(**cat_data)
        db.session.add(category)
        db.session.flush()  # Получаем ID
        categories_map[cat_data["name"]] = category
        print(f"Добавлена категория: {cat_data['name']}")
    else:
        categories_map[cat_data["name"]] = existing

# 4. Навыки
skills_data = [
    # Разработка
    {"name": "Python", "category": "Разработка"},
    {"name": "JavaScript", "category": "Разработка"},
    {"name": "TypeScript", "category": "Разработка"},
    {"name": "Java", "category": "Разработка"},
    {"name": "C++", "category": "Разработка"},
    {"name": "C#", "category": "Разработка"},
    {"name": "Go", "category": "Разработка"},
    {"name": "Rust", "category": "Разработка"},
    {"name": "PHP", "category": "Разработка"},
    {"name": "Ruby", "category": "Разработка"},
    {"name": "React", "category": "Разработка"},
    {"name": "Vue.js", "category": "Разработка"},
    {"name": "Angular", "category": "Разработка"},
    {"name": "Node.js", "category": "Разработка"},
    {"name": "Django", "category": "Разработка"},
    {"name": "Flask", "category": "Разработка"},
    {"name": "FastAPI", "category": "Разработка"},
    {"name": "Spring Boot", "category": "Разработка"},
    {"name": "Express.js", "category": "Разработка"},
    {"name": "Laravel", "category": "Разработка"},
    {"name": "SQL", "category": "Разработка"},
    {"name": "PostgreSQL", "category": "Разработка"},
    {"name": "MySQL", "category": "Разработка"},
    {"name": "MongoDB", "category": "Разработка"},
    {"name": "Redis", "category": "Разработка"},
    {"name": "Docker", "category": "Разработка"},
    {"name": "Kubernetes", "category": "Разработка"},
    {"name": "Git", "category": "Разработка"},
    {"name": "REST API", "category": "Разработка"},
    {"name": "GraphQL", "category": "Разработка"},
    {"name": "WebSocket", "category": "Разработка"},
    {"name": "React Native", "category": "Разработка"},
    {"name": "Flutter", "category": "Разработка"},
    {"name": "Swift", "category": "Разработка"},
    {"name": "Kotlin", "category": "Разработка"},
    
    # Дизайн
    {"name": "Figma", "category": "Дизайн"},
    {"name": "Adobe Photoshop", "category": "Дизайн"},
    {"name": "Adobe Illustrator", "category": "Дизайн"},
    {"name": "Adobe XD", "category": "Дизайн"},
    {"name": "Sketch", "category": "Дизайн"},
    {"name": "UI Design", "category": "Дизайн"},
    {"name": "UX Design", "category": "Дизайн"},
    {"name": "Прототипирование", "category": "Дизайн"},
    {"name": "Веб-дизайн", "category": "Дизайн"},
    {"name": "Мобильный дизайн", "category": "Дизайн"},
    {"name": "Графический дизайн", "category": "Дизайн"},
    {"name": "Брендинг", "category": "Дизайн"},
    
    # Аналитика
    {"name": "Анализ данных", "category": "Аналитика"},
    {"name": "Python (Data Science)", "category": "Аналитика"},
    {"name": "R", "category": "Аналитика"},
    {"name": "Pandas", "category": "Аналитика"},
    {"name": "NumPy", "category": "Аналитика"},
    {"name": "Matplotlib", "category": "Аналитика"},
    {"name": "Seaborn", "category": "Аналитика"},
    {"name": "Tableau", "category": "Аналитика"},
    {"name": "Power BI", "category": "Аналитика"},
    {"name": "Excel", "category": "Аналитика"},
    {"name": "SQL для аналитики", "category": "Аналитика"},
    {"name": "Статистика", "category": "Аналитика"},
    {"name": "Машинное обучение", "category": "Аналитика"},
    {"name": "Deep Learning", "category": "Аналитика"},
    {"name": "TensorFlow", "category": "Аналитика"},
    {"name": "PyTorch", "category": "Аналитика"},
    
    # Управление
    {"name": "Agile", "category": "Управление"},
    {"name": "Scrum", "category": "Управление"},
    {"name": "Kanban", "category": "Управление"},
    {"name": "Управление проектами", "category": "Управление"},
    {"name": "Jira", "category": "Управление"},
    {"name": "Trello", "category": "Управление"},
    {"name": "Asana", "category": "Управление"},
    {"name": "Лидерство", "category": "Управление"},
    {"name": "Командная работа", "category": "Управление"},
    
    # Инфраструктура
    {"name": "Linux", "category": "Инфраструктура"},
    {"name": "AWS", "category": "Инфраструктура"},
    {"name": "Azure", "category": "Инфраструктура"},
    {"name": "Google Cloud", "category": "Инфраструктура"},
    {"name": "CI/CD", "category": "Инфраструктура"},
    {"name": "Jenkins", "category": "Инфраструктура"},
    {"name": "GitLab CI", "category": "Инфраструктура"},
    {"name": "GitHub Actions", "category": "Инфраструктура"},
    {"name": "Terraform", "category": "Инфраструктура"},
    {"name": "Ansible", "category": "Инфраструктура"},
    {"name": "Nginx", "category": "Инфраструктура"},
    {"name": "Мониторинг", "category": "Инфраструктура"},
]

for skill_data in skills_data:
    category = categories_map.get(skill_data["category"])
    if not category:
        print(f"Ошибка: категория '{skill_data['category']}' не найдена")
        continue
    
    existing = Skill.query.filter_by(name=skill_data["name"]).first()
    if not existing:
        skill = Skill(name=skill_data["name"], category_id=category.id)
        db.session.add(skill)
        print(f"Добавлен навык: {skill_data['name']} ({skill_data['category']})")

# Сохранение всех изменений
db.session.commit()
print("\n✅ Все данные успешно добавлены в базу данных!")
