import os
import pyodbc


def get_conn():
    server = os.getenv("JOURNAL_DB_SERVER")
    db_name = os.getenv("JOURNAL_DB_NAME")
    user = os.getenv("JOURNAL_DB_USER")
    password = os.getenv("JOURNAL_DB_PASSWORD")
    encrypt = os.getenv("JOURNAL_DB_ENCRYPT")
    trust_cert = os.getenv("JOURNAL_DB_TRUST_SERVER_CERT")

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={db_name};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_cert};"
    )

    conn = pyodbc.connect(conn_str, timeout=5)
    print(f"[journal_service] Connected to journal DB {db_name} at {server}")
    return conn


class StudentNotFound(Exception):
    pass


class MultipleStudentsFound(Exception):
    pass


def confirm_student_in_journal(
    last_name: str,
    first_name: str,
    middle_name: str | None,
    group_code: str,
    birthday: str | None,
) -> int:
    """
    Ищет студента в базе сетевого журнала и возвращает его StudentWorkFlowId.

    Поведение полностью повторяет эндпоинт /confirm-student из localdb.py:
      - если студент не найден -> StudentNotFound
      - если найдено несколько -> MultipleStudentsFound
      - если найден ровно один -> возвращается StudentWorkFlowId (int)
    """
    if not all([last_name, first_name, group_code]):
        raise ValueError("Недостаточно данных для подтверждения студента")

    sql = """
        SELECT
            swf.Id AS StudentWorkFlowId,
            up.LastName,
            up.FirstName,
            up.MiddleName,
            up.Birthday,
            sg.Code AS GroupCode
        FROM dbo.StudentWorkFlow swf
        JOIN dbo.UserProfile up
            ON up.Id = swf.UserProfileId

        LEFT JOIN dbo.StudentEntryWorkFlow sewf
            ON sewf.StudentWorkFlowId = swf.Id
           AND sewf.EndId IS NULL

        LEFT JOIN dbo.StudentGroupEntryWorkFlow sgewf
            ON sgewf.Id = sewf.StudentGroupEntryWorkFlowId

        LEFT JOIN dbo.StudentGroup sg
            ON sg.Id = sgewf.StudentGroupId

        WHERE swf.EndId IS NULL
          AND up.LastName = ?
          AND up.FirstName = ?
          AND ISNULL(up.MiddleName,'') = ISNULL(?, '')
          AND sg.Code = ?
          AND (? IS NULL OR up.Birthday = ?)
    """

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            sql,
            last_name,
            first_name,
            middle_name,
            group_code,
            birthday,
            birthday,
        )

        rows = cur.fetchall()

    if len(rows) == 0:
        raise StudentNotFound("Студент не найден")

    if len(rows) > 1:
        raise MultipleStudentsFound(
            "Найдено несколько студентов. Уточните дату рождения."
        )

    student_workflow_id = int(rows[0][0])
    return student_workflow_id

