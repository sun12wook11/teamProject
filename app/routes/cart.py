from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dbfactory import get_db
from app.model.cart import Cart as CartModel
from app.model.product import Product as ProductModel

cart_router = APIRouter()

@cart_router.post("/cart/add")
async def add_to_cart(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    prdno = data.get('prdno')
    qty = data.get('qty')

    userid = request.session.get("userid")
    if not userid:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    product = db.query(ProductModel).filter(ProductModel.prdno == prdno).first()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    if product.qty < qty:
        raise HTTPException(status_code=400, detail="재고가 부족합니다.")

    cart_item = db.query(CartModel).filter(CartModel.mno == userid, CartModel.prdno == prdno).first()

    if cart_item:
        cart_item.qty += qty
        cart_item.price += product.price * qty
    else:
        cart_item = CartModel(mno=userid, prdno=prdno, qty=qty, price=product.price * qty)
        db.add(cart_item)

    product.qty -= qty

    db.commit()

    return {"message": "장바구니에 추가되었습니다."}
