import logging

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.databast import SessionLocal
from models import User

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def delete_inactive_users():
    print("Inactive user deleting...")
    with Session(get_db()) as db:
        current_time = datetime.utcnow()
        threshold_date = current_time - timedelta(days=30)
        inactive_users = db.query(User).filter(User.is_active == False, User.inactive_date <= threshold_date).all()

        for user in inactive_users:
            db.delete(user)

        db.commit()


scheduler = BackgroundScheduler()

# -- 스케줄러 작업 목록 --
scheduler.add_job(delete_inactive_users, trigger='interval', days=30)

scheduler.start()

try:
    while True:
        pass
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
