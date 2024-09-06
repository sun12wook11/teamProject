import hashlib
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.model.member import Member
from app.schema.member import NewMember
from app.model.order import Order
from app.model.product import Cart

class MemberService:
    @staticmethod
    def sha256_hash(passwd: str) -> str:
        """
        SHA-256 암호화 함수
        """
        hash_object = hashlib.sha256()
        hash_object.update(passwd.encode('utf-8'))
        return hash_object.hexdigest()

    @staticmethod
    def insert_member(db: Session, member: NewMember):
        """
        새로운 회원을 데이터베이스에 삽입
        """
        try:
            # 비밀번호 해시 처리
            hashed_password = MemberService.sha256_hash(member.password)

            # Member 모델 객체 생성
            stmt = Member(
                username=member.username,
                userid=member.userid,
                email=member.email,
                password=hashed_password,
                phone=member.phone,
                address=member.address,
                postcode=member.postcode,
                birthdate=member.birthdate,
                gender=member.gender
            )

            # 데이터베이스에 삽입
            db.add(stmt)
            db.commit()
            db.refresh(stmt)  # 데이터베이스에서 새로 삽입된 데이터 새로 고침

            print(f"Inserted member: {stmt}")
            return stmt
        except SQLAlchemyError as ex:
            db.rollback()
            print(f'Insert Member Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")



    @staticmethod
    def is_userid_taken(db: Session, userid: str) -> bool:
        """
        주어진 userid가 이미 사용 중인지 확인
        """
        try:
            existing_user = db.query(Member).filter(Member.userid == userid).first()
            return existing_user is not None
        except SQLAlchemyError as ex:
            print(f'Check UserID Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def get_member_by_userid(db: Session, userid: str) -> Member:
        """
        사용자의 ID로 회원 정보를 가져오기
        """
        try:
            member = db.query(Member).filter(Member.userid == userid).first()
            if not member:
                raise HTTPException(status_code=404, detail="User not found")
            return member
        except SQLAlchemyError as ex:
            print(f'Get Member Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def update_member_info(db: Session, userid: str, update_data: dict):
        """
        회원 정보를 업데이트
        """
        try:
            member = db.query(Member).filter(Member.userid == userid).first()
            if not member:
                raise HTTPException(status_code=404, detail="User not found")

            for key, value in update_data.items():
                if key == "password" and value:
                    value = MemberService.sha256_hash(value)
                setattr(member, key, value)

            db.commit()
            return member
        except SQLAlchemyError as ex:
            db.rollback()
            print(f'Update Member Info Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def login_member(db: Session, data: dict):
        """
        사용자가 입력한 ID와 비밀번호를 이용하여 로그인 시도
        """
        try:
            hashed_password = MemberService.sha256_hash(data['password'])
            member = db.query(Member).filter(
                Member.userid == data['userid'],
                Member.password == hashed_password
            ).first()

            if member:
                return member
            return None  # 일반 사용자 로그인 실패
        except SQLAlchemyError as ex:
            print(f'Login Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def login_admin(db: Session, data: dict):
        """
        관리자 로그인 함수: mno가 1인 사용자를 관리자 계정으로 간주하여 로그인 처리
        """
        try:
            hashed_password = MemberService.sha256_hash(data['password'])
            admin = db.query(Member).filter(
                Member.userid == data['userid'],
                Member.password == hashed_password,
                Member.mno == 1  # mno가 1인 사용자를 관리자로 설정
            ).first()

            if not admin:
                return None  # 관리자 로그인 실패
            return admin
        except SQLAlchemyError as ex:
            print(f'Admin Login Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def delete_member(db: Session, mno: int):
        try:
            # 회원 정보 조회
            member = db.query(Member).filter(Member.mno == mno).first()

            if not member:
                raise HTTPException(status_code=404, detail="User not found")

            # 회원 정보 삭제
            db.delete(member)
            db.commit()

            print(f"Deleted member with mno: {mno}")
            return {"message": "Member deleted successfully"}

        except SQLAlchemyError as ex:
            db.rollback()
            print(f'Delete Member Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Internal Server Error")

