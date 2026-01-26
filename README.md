# API Endpoints

## 1. Auth

### 1.1 POST `/auth/login`

Логин по email + password.

**Body:**

```json
{
  "email": "student1@kit.local",
  "password": "123456"
}
```

```json
{
  "email": "admin@kit.local",
  "password": "admin123"
}
```

**200 OK:**

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": { "id": 1, "email": "student1@kit.local", "role": "student" }
}
```

**Ошибки:**

| Код | Описание           |
| --- | ------------------ |
| 400 | Нет email/password |
| 401 | Неверные данные    |

---

### 1.2 POST `/auth/refresh`

Обновление access token по refresh token.

**Headers:**

```
Authorization: Bearer <refresh_token>
```

**200 OK:**

```json
{ "access_token": "..." }
```

---

### 1.3 GET `/auth/me`

Информация о текущем пользователе.

**Headers:**

```
Authorization: Bearer <access_token>
```

**200 OK:**

```json
{ "id": 1, "email": "student1@kit.local", "role": "student" }
```

---

### 1.4 POST `/auth/register`

Регистрация нового пользователя (только для студентов).

**Body:**

```json
{
  "email": "student2@kit.local",
  "password": "123456"
}
```

**201 Created:**

```json
{
  "message": "registered successfully",
  "access_token": "...",
  "refresh_token": "...",
  "user": { "id": 2, "email": "student2@kit.local", "role": "student" }
}
```

**Ошибки:**

| Код | Описание                          |
| --- | --------------------------------- |
| 400 | Нет email/password или пароль < 6 символов |
| 409 | Email уже зарегистрирован        |

---

### 1.5 POST `/auth/register-admin`

Регистрация нового администратора.

**Важно:** Первый админ создаётся **без авторизации**. Последующие админы могут создаваться только существующими админами (требуется Bearer token).

**Body:**

```json
{
  "email": "admin@kit.local",
  "password": "admin123",
  "full_name": "Иван Иванов",
  "position": "Системный администратор"
```

> `full_name` и `position` опциональны

**201 Created:**

```json
{
  "message": "admin registered successfully",
  "access_token": "...",
  "refresh_token": "...",
  "user": { "id": 2, "email": "admin@kit.local", "role": "admin" }
}
```

**Ошибки:**

| Код | Описание                          |
| --- | --------------------------------- |
| 400 | Нет email/password или пароль < 6 символов |
| 401 | Требуется авторизация (если админы уже есть) |
| 403 | Только существующие админы могут создавать новых |
| 409 | Email уже зарегистрирован        |

---

## 2. Student Profile

### 2.1 GET `/students/me`

Получить профиль студента (создаст пустой профиль, если его нет).

**Headers:** Bearer access token

**200 OK:**

```json
{
  "id": 1,
  "user_id": 1,
  "email": "student1@kit.local",
  "first_name": "Amina",
  "last_name": "Test",
  "group_name": "IS-11"
}
```

**Ошибки:**

| Код | Описание                     |
| --- | ---------------------------- |
| 403 | Роль пользователя не student |
| 404 | User не найден               |

---

### 2.2 PATCH `/students/me`

Частичное обновление профиля студента.

**Headers:** Bearer access token

**Body (любые из полей):**

```json
{
  "first_name": "Амина",
  "last_name": "Тестова",
  "group_name": "ИС-11"
}
```

**200 OK:** возвращает обновлённый профиль (как в GET).

---

## 3. Справочники

### 3.1 GET `/skill-categories`

Список категорий навыков.

**Headers:** Bearer access token

**200 OK:**

```json
[
  { "id": 1, "name": "Разработка" },
  { "id": 2, "name": "Дизайн" }
]
```

---

### 3.2 GET `/skills`

Список навыков со ссылкой на категорию.

**Headers:** Bearer access token

**200 OK:**

```json
[
  {
    "id": 1,
    "name": "Python",
    "category": { "id": 1, "name": "Разработка" }
  }
]
```

---

### 3.3 GET `/interests`

Список интересов.

**Headers:** Bearer access token

**200 OK:**

```json
[
  { "id": 1, "name": "AI" },
  { "id": 2, "name": "Web-разработка" }
]
```

---

### 3.4 GET `/roles`

Список ролей в команде.

**Headers:** Bearer access token

**200 OK:**

```json
[
  { "id": 1, "code": "teamlead", "name": "Тимлид" },
  { "id": 2, "code": "backend", "name": "Backend-разработчик" }
]
```

---

## 4. Анкета студента (полная замена списков)

### 4.1 PUT `/students/me/skills`

Полная замена навыков студента.

**Headers:** Bearer access token

**Body:**

```json
[
  { "skill_id": 1, "level": 4 },
  { "skill_id": 3, "level": 2 }
]
```

**Правила:**

- `level` строго 1..5
- Список полностью перезаписывается (можно `[]`)

**200 OK:**

```json
{ "message": "skills updated" }
```

---

### 4.2 PUT `/students/me/interests`

Полная замена интересов.

**Headers:** Bearer access token

**Body:**

```json
[1, 3]
```

**200 OK:**

```json
{ "message": "interests updated" }
```

---

### 4.3 PUT `/students/me/roles`

Полная замена ролей.

**Headers:** Bearer access token

**Body (role_id):**

```json
[1, 4]
```

**200 OK:**

```json
{ "message": "roles updated" }
```

---

## 5. Skill-map

### 5.1 GET `/students/me/skill-map`

Возвращает "карту навыков" единым объектом.

**Headers:** Bearer access token

**200 OK:**

```json
{
  "profile": {
    "id": 1,
    "user_id": 1,
    "email": "student1@kit.local",
    "first_name": "Амина",
    "last_name": "Тестова",
    "group_name": "ИС-11"
  },
  "interests": [{ "id": 1, "name": "AI" }],
  "roles": [{ "id": 1, "code": "teamlead", "name": "Тимлид" }],
  "skills": [
    {
      "id": 1,
      "name": "Python",
      "level": 4,
      "category": { "id": 1, "name": "Разработка" }
    }
  ]
}
```

---

## 6. Admin Profile

### 6.1 GET `/admins/me`

Получить профиль администратора (создаст пустой профиль, если его нет).

**Headers:** Bearer access token

**200 OK:**

```json
{
  "id": 1,
  "user_id": 2,
  "email": "admin@kit.local",
  "full_name": "Иван Иванов",
  "position": "Системный администратор"
}
```

**Ошибки:**

| Код | Описание                   |
| --- | -------------------------- |
| 403 | Роль пользователя не admin |
| 404 | User не найден             |

---

### 6.2 PATCH `/admins/me`

Частичное обновление профиля администратора.

**Headers:** Bearer access token

**Body (любые из полей):**

```json
{
  "full_name": "Иван Петров",
  "position": "Главный администратор"
}
```

**200 OK:** возвращает обновлённый профиль (как в GET).

---

## 7. Форум

### 7.1 GET `/forum/topics`

Получить список тем форума.

**Headers:** Bearer access token

**Query params:**

| Параметр     | Тип  | По умолчанию | Описание                         |
| ------------ | ---- | ------------ | -------------------------------- |
| page         | int  | 1            | Номер страницы                   |
| per_page     | int  | 20           | Количество на странице (max 100) |
| pinned_first | bool | true         | Закреплённые темы сверху         |

**200 OK:**

```json
{
  "topics": [
    {
      "id": 1,
      "title": "Как начать изучать Python?",
      "description": "Делитесь ресурсами и советами",
      "is_closed": false,
      "is_pinned": true,
      "messages_count": 15,
      "author": {
        "id": 1,
        "email": "student1@kit.local",
        "role": "student",
        "name": "Амина Тестова"
      },
      "created_at": "2026-01-10T12:00:00",
      "updated_at": "2026-01-10T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### 7.2 POST `/forum/topics`

Создать новую тему.

**Headers:** Bearer access token

**Body:**

```json
{
  "title": "Как начать изучать Python?",
  "description": "Делитесь ресурсами и советами"
}
```

**201 Created:** возвращает созданную тему

**Ошибки:**

| Код | Описание                             |
| --- | ------------------------------------ |
| 400 | title обязателен или слишком длинный |

---

### 7.3 GET `/forum/topics/{id}`

Получить тему по ID.

**Headers:** Bearer access token

**200 OK:** возвращает тему

**Ошибки:**

| Код | Описание        |
| --- | --------------- |
| 404 | Тема не найдена |

---

### 7.4 PATCH `/forum/topics/{id}`

Обновить тему. Только автор или админ.

**Headers:** Bearer access token

**Body:**

```json
{
  "title": "Новый заголовок",
  "description": "Новое описание",
  "is_closed": true,
  "is_pinned": true
}
```

> `is_closed` и `is_pinned` доступны только админам

**200 OK:** возвращает обновлённую тему

**Ошибки:**

| Код | Описание        |
| --- | --------------- |
| 403 | Нет прав        |
| 404 | Тема не найдена |

---

### 7.5 DELETE `/forum/topics/{id}`

Удалить тему. Только автор или админ.

**Headers:** Bearer access token

**200 OK:**

```json
{ "message": "topic deleted" }
```

**Ошибки:**

| Код | Описание        |
| --- | --------------- |
| 403 | Нет прав        |
| 404 | Тема не найдена |

---

### 7.6 GET `/forum/topics/{id}/messages`

Получить сообщения темы. Возвращает корневые сообщения с вложенными ответами.

**Headers:** Bearer access token

**Query params:**

| Параметр | Тип | По умолчанию | Описание                         |
| -------- | --- | ------------ | -------------------------------- |
| page     | int | 1            | Номер страницы                   |
| per_page | int | 50           | Количество на странице (max 100) |

**200 OK:**

```json
{
  "topic": { ... },
  "messages": [
    {
      "id": 1,
      "content": "Начните с официальной документации",
      "topic_id": 1,
      "parent_id": null,
      "is_edited": false,
      "author": {
        "id": 2,
        "email": "admin@kit.local",
        "role": "admin",
        "name": "Администратор"
      },
      "created_at": "2026-01-10T12:05:00",
      "updated_at": "2026-01-10T12:05:00",
      "replies": [
        {
          "id": 2,
          "content": "Спасибо за совет!",
          "topic_id": 1,
          "parent_id": 1,
          "is_edited": false,
          "author": { ... },
          "created_at": "2026-01-10T12:10:00",
          "updated_at": "2026-01-10T12:10:00"
        }
      ]
    }
  ],
  "pagination": { ... }
}
```

---

### 7.7 POST `/forum/topics/{id}/messages`

Создать сообщение в теме.

**Headers:** Bearer access token

**Body:**

```json
{
  "content": "Текст сообщения",
  "parent_id": 1
}
```

> `parent_id` — опционально, для ответа на сообщение (только 1 уровень вложенности)

**201 Created:** возвращает созданное сообщение

**Ошибки:**

| Код | Описание                                      |
| --- | --------------------------------------------- |
| 400 | content обязателен / нельзя ответить на ответ |
| 403 | Тема закрыта                                  |
| 404 | Тема или родительское сообщение не найдено    |

---

### 7.8 GET `/forum/messages/{id}`

Получить сообщение по ID.

**Headers:** Bearer access token

**200 OK:** возвращает сообщение с ответами

---

### 7.9 PATCH `/forum/messages/{id}`

Обновить сообщение. Только автор.

**Headers:** Bearer access token

**Body:**

```json
{
  "content": "Обновлённый текст"
}
```

**200 OK:** возвращает обновлённое сообщение (is_edited = true)

**Ошибки:**

| Код | Описание             |
| --- | -------------------- |
| 403 | Нет прав             |
| 404 | Сообщение не найдено |

---

### 7.10 DELETE `/forum/messages/{id}`

Удалить сообщение. Только автор или админ.

**Headers:** Bearer access token

**200 OK:**

```json
{ "message": "message deleted" }
```

**Ошибки:**

| Код | Описание             |
| --- | -------------------- |
| 403 | Нет прав             |
| 404 | Сообщение не найдено |

---

## 8. Служебный

### GET `/health`

Проверка, что API жив.

**200 OK:**

```json
{ "status": "ok" }
```
