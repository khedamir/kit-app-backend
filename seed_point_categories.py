# -*- coding: utf-8 -*-
"""
Скрипт для создания категорий начисления баллов.
Запуск: flask shell, затем exec(open('seed_point_categories.py', encoding='utf-8').read())
"""

from app.extensions import db
from app.models.points import PointCategory

# Категории наград (положительные баллы)
REWARD_CATEGORIES = [
    {"name": "Участие в проекте", "points": 10},
    {"name": "Победа в хакатоне", "points": 50},
    {"name": "Призовое место в хакатоне", "points": 30},
    {"name": "Участие в хакатоне", "points": 15},
    {"name": "Выступление на мероприятии", "points": 20},
    {"name": "Организация мероприятия", "points": 25},
    {"name": "Помощь другим студентам", "points": 5},
    {"name": "Активность в сообществе", "points": 5},
    {"name": "Публикация статьи/материала", "points": 15},
    {"name": "Отличная работа в команде", "points": 10},
]

# Категории штрафов (отрицательные баллы)
PENALTY_CATEGORIES = [
    {"name": "Пропуск мероприятия без уважительной причины", "points": -5},
    {"name": "Невыполнение обязательств в проекте", "points": -10},
    {"name": "Нарушение правил сообщества", "points": -15},
]

# Кастомная категория (для произвольных начислений)
CUSTOM_CATEGORY = {
    "name": "Прочее",
    "points": 0,  # баллы указываются вручную
    "is_custom": True,
}


def seed_point_categories():
    """Создаёт категории начисления баллов."""
    created_count = 0
    
    # Награды
    for cat_data in REWARD_CATEGORIES:
        existing = PointCategory.query.filter_by(name=cat_data["name"]).first()
        if not existing:
            category = PointCategory(
                name=cat_data["name"],
                points=cat_data["points"],
                is_penalty=False,
                is_custom=False,
            )
            db.session.add(category)
            created_count += 1
            print(f"+ Создана категория: {cat_data['name']} (+{cat_data['points']} баллов)")
    
    # Штрафы
    for cat_data in PENALTY_CATEGORIES:
        existing = PointCategory.query.filter_by(name=cat_data["name"]).first()
        if not existing:
            category = PointCategory(
                name=cat_data["name"],
                points=cat_data["points"],
                is_penalty=True,
                is_custom=False,
            )
            db.session.add(category)
            created_count += 1
            print(f"+ Создана категория штрафа: {cat_data['name']} ({cat_data['points']} баллов)")
    
    # Кастомная категория
    existing = PointCategory.query.filter_by(name=CUSTOM_CATEGORY["name"], is_custom=True).first()
    if not existing:
        category = PointCategory(
            name=CUSTOM_CATEGORY["name"],
            points=CUSTOM_CATEGORY["points"],
            is_penalty=False,
            is_custom=True,
        )
        db.session.add(category)
        created_count += 1
        print(f"+ Создана кастомная категория: {CUSTOM_CATEGORY['name']}")
    
    db.session.commit()
    print(f"\n✓ Создано категорий: {created_count}")


# Запуск
seed_point_categories()
