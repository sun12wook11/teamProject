from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.model import member, board, gallery, order, product  # 필요한 모델들을 임포트
from app.settings import config

engine = create_engine(config.dbconn, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def db_startup():
    # 데이터베이스 테이블을 생성
    member.Base.metadata.create_all(bind=engine)
    board.Base.metadata.create_all(bind=engine)
    gallery.Base.metadata.create_all(bind=engine)
    product.Base.metadata.create_all(bind=engine)
    order.Base.metadata.create_all(bind=engine)


async def db_shutdown():
    # 여기에 데이터베이스 연결 종료 등의 처리가 필요하면 추가하세요
    pass
