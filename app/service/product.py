from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import os
from datetime import datetime
from fastapi import Form
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from app.model.product import Product, PrdAttach
from app.schema.product import NewProduct

UPLOAD_PATH = '/usr/share/nginx/html/cdn/img/'

class ProductService:
    @staticmethod
    def get_all_products(db: Session):
        try:
            products = db.query(Product).all()
            return products
        except Exception as ex:
            print(f'Get All Products Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Failed to retrieve products")

    @staticmethod
    def get_product_detail(db: Session, prdno: int):
        try:
            product = db.query(Product).filter(Product.prdno == prdno).first()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            return product
        except Exception as ex:
            print(f'Get Product Detail Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Failed to retrieve product detail")

    @staticmethod
    def update_product_qty(db: Session, prdno: int, qty: int):
        try:
            product = db.query(Product).filter(Product.prdno == prdno).first()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            product.qty -= qty
            db.commit()
            return product
        except Exception as ex:
            db.rollback()
            print(f'Update Product Quantity Error: {str(ex)}')
            raise HTTPException(status_code=500, detail="Failed to update product quantity")

    @staticmethod
    def get_product_data(prdname: str = Form(...),
                         price: int = Form(...), type: str = Form(...),
                         qty: int = Form(...), description: str = Form(...)):
        return NewProduct(prdname=prdname, price=price, type=type, qty=qty, description=description)

    @staticmethod
    async def process_upload(files):
        attachs = []  # 업로드된 파일정보를 저장하기 위해 리스트 생성

        today = datetime.today().strftime('%Y%m%d%H%M') # UUID 생성
        for file in files:
            if file.filename != '' and file.size > 0:
                nfname = f'{today}{file.filename}'
                # os.path.join(A,B) => A/B (경로생성)
                fname = os.path.join(UPLOAD_PATH, nfname) # 업로드할 파일경로 생성
                content = await file.read()  # 업로드할 파일의 내용을 비동기로 읽음
                with open(fname, 'wb') as f:
                    f.write(content)
                attach = [nfname, file.size] # 업로드된 파일 정보를 리스트에 저장
                attachs.append(attach)

        return attachs

    @staticmethod
    def insert_product(prd, attachs, db):
        try:
            stmt = insert(Product).values(prdname=prd.prdname, price=prd.price, type=prd.type,
                                          qty=prd.qty, description=prd.description)
            result = db.execute(stmt)

            # 방금 insert된 레코드의 기본키 값 : inserted_primary_key
            inserted_prdno = result.inserted_primary_key[0]
            for attach in attachs:
                data = {'fname': attach[0], 'fsize': attach[1], 'prdno': inserted_prdno}
                stmt = insert(PrdAttach).values(data)
                result = db.execute(stmt)

            db.commit()

            return result

        except SQLAlchemyError as ex:
            print(f'▶▶▶ insert_product에서 오류발생 : {str(ex)} ')
            db.rollback()

    @staticmethod
    def select_product(db, category=None):
        try:
            # 기본 쿼리 작성
            stmt = select(Product.prdno, Product.prdname, Product.price, Product.type, PrdAttach.fname) \
                .join(PrdAttach)

            # 카테고리가 주어졌을 경우, 필터링
            if category:
                if category == "기타":
                    # 의자, 테이블, 소파가 아닌 항목 필터링
                    stmt = stmt.where(~Product.type.in_(["의자", "테이블", "소파"]))
                else:
                    # 특정 카테고리 필터링
                    stmt = stmt.where(Product.type == category)

            # 나머지 쿼리 설정
            stmt = stmt.group_by(Product.prdno, PrdAttach.fname) \
                .order_by(Product.prdno.desc()).limit(25)

            print(f'Executing query: {stmt}')  # 실행되는 쿼리 로그 출력
            result = db.execute(stmt).all()

            return result

        except SQLAlchemyError as ex:
            print(f'▶▶▶ select_product에서 오류발생 : {str(ex)}')
            db.rollback()
            return None

    @staticmethod
    def selectone_product(prdno, db):
        try:
            stmt = select(Product).options(joinedload(Product.attachs)) \
                .where(Product.prdno == prdno)
            result = db.execute(stmt).scalars().first()

            return result

        except SQLAlchemyError as ex:
            print(f'▶▶▶ selectone_product 오류발생 : {str(ex)}')
            db.rollback()