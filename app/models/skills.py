from ..extensions import db

class SkillCategory(db.Model):
    __tablename__ = "skill_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)

    skills = db.relationship("Skill", back_populates="category", cascade="all, delete-orphan")


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey("skill_categories.id", ondelete="RESTRICT"), nullable=False)
    category = db.relationship("SkillCategory", back_populates="skills")
