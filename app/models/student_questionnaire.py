from ..extensions import db

class StudentSkill(db.Model):
    __tablename__ = "student_skills"

    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id", ondelete="CASCADE"), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True)

    level = db.Column(db.Integer, nullable=False)  # 1..5

    skill = db.relationship("Skill")


class StudentInterest(db.Model):
    __tablename__ = "student_interests"

    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id", ondelete="CASCADE"), primary_key=True)
    interest_id = db.Column(db.Integer, db.ForeignKey("interests.id", ondelete="RESTRICT"), primary_key=True)

    interest = db.relationship("Interest")


class StudentRole(db.Model):
    __tablename__ = "student_roles"

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    role = db.relationship("Role")
