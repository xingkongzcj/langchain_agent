"""测试自动出题逻辑。

前提：
1. MySQL 已启动：docker-compose up -d
2. .env 已配置有效的 SILICONFLOW_API_KEY
3. 已创建课程并上传过文档（知识库非空）

用法：python tests/test_quiz.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db.mysql import SessionLocal, init_db
from app.models.course import Course
from app.models.quiz import Question
from app.services.quiz_service import generate_quiz


def main() -> None:
    if not settings.siliconflow_api_key:
        print("[错误] 请在 .env 中配置 SILICONFLOW_API_KEY 后再运行。")
        return

    init_db()

    db = SessionLocal()
    try:
        # 取第一个课程（请确保该课程已上传过文档）
        course = db.query(Course).first()
        if not course:
            print("[错误] 请先创建课程并上传文档。")
            return
        print(f"使用课程: id={course.id}, name={course.name}")
        print("开始生成题目（单选 · 中等难度 · 3 道）...\n")

        batch = generate_quiz(
            db=db,
            course_id=course.id,
            topic=None,
            question_type="single",
            difficulty="medium",
            count=3,
        )

        print(f"[成功] 出题批次: batch_id={batch.id}, 题目数={batch.count}\n")

        questions = db.query(Question).filter(Question.batch_id == batch.id).all()
        for q in questions:
            print(f"--- 题目 {q.id}（{q.type}）---")
            print(f"题干: {q.question}")
            if q.options:
                print(f"选项: {q.options}")
            print(f"答案: {q.answer}")
            print(f"解析: {q.explanation}\n")
    except Exception as exc:
        print(f"[失败] {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
