from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.templating import Jinja2Templates
from app.dbfactory import get_db
from app.model.member import Member
from app.schema.member import NewMember
from app.service.member import MemberService
from pydantic import ValidationError

member_router = APIRouter()
templates = Jinja2Templates(directory='views/templates')

@member_router.get("/join", response_class=HTMLResponse)
async def join(req: Request):
    return templates.TemplateResponse("member/join.html", {"request": req})


@member_router.post("/join", response_class=HTMLResponse)
async def joinok(req: Request, db: Session = Depends(get_db)):
    try:
        data = await req.json()
        if MemberService.is_userid_taken(db, data["userid"]):
            return JSONResponse(status_code=400, content={"message": "이미 사용 중인 아이디입니다."})

        try:
            new_member = NewMember(**data)
        except ValidationError as e:
            # 오류 메시지를 한글로 수정하여 반환
            errors = {}
            for error in e.errors():
                field = error['loc'][0]
                if field == 'username':
                    errors[field] = '이름을 입력해주세요.'
                elif field == 'userid':
                    errors[field] = '아이디를 입력해주세요.'
                elif field == 'email':
                    errors[field] = '올바른 이메일 주소를 입력해주세요.'
                elif field == 'password':
                    errors[field] = '비밀번호를 입력해주세요.'
                elif field == 'phone':
                    errors[field] = '전화번호를 입력해주세요.'
                elif field == 'address':
                    errors[field] = '주소를 입력해주세요.'
                elif field == 'postcode':
                    errors[field] = '우편번호를 입력해주세요.'
                elif field == 'birthdate':
                    errors[field] = '생년월일을 입력해주세요.'
                elif field == 'gender':
                    errors[field] = '성별을 선택해주세요.'
                else:
                    errors[field] = error['msg']  # 기타 메시지는 기본 메시지 사용

            return JSONResponse(status_code=422, content={"errors": errors})

        MemberService.insert_member(db, new_member)
        return RedirectResponse(url='/member/login', status_code=303)

    except Exception as ex:
        return RedirectResponse(url='/member/login', status_code=303)

@member_router.get("/login", response_class=HTMLResponse)
async def login(req: Request):
    return templates.TemplateResponse("member/login.html", {"request": req})

@member_router.post("/login", response_class=HTMLResponse)
async def loginok(req: Request, db: Session = Depends(get_db)):
    try:
        body = await req.body()
        print(f"Request body: {body}")  # 로그에 요청 본문 출력
        data = await req.json()  # JSON 데이터로 변경
        userid = data.get("userid")
        password = data.get("password")

        # 관리자 로그인 시도
        admin_user = MemberService.login_admin(db, {"userid": userid, "password": password})
        if admin_user:
            req.session['userid'] = userid  # 세션에 userid 저장
            req.session['is_admin'] = True  # 관리자 세션 설정
            print(f"Admin session userid set: {req.session['userid']}")  # 세션에 저장된 userid 출력
            return RedirectResponse(url='/admin/admin', status_code=303)

        # 일반 사용자 로그인 시도
        user = MemberService.login_member(db, {"userid": userid, "password": password})
        if user:
            req.session['userid'] = userid  # 세션에 userid 저장
            req.session['mno'] = user.mno
            req.session['is_admin'] = False  # 일반 사용자 세션 설정
            print(f"Session userid set: {req.session['userid']}")  # 세션에 저장된 userid 출력
            return RedirectResponse(url='/', status_code=303)

        # 로그인 실패 처리
        return RedirectResponse(url='/member/loginfail', status_code=303)
    except ValidationError as e:
        # Pydantic 유효성 검사 오류를 처리
        errors = e.errors()
        return JSONResponse(status_code=422, content={"errors": errors})
    except Exception as ex:
        print(f'로그인 오류: {str(ex)}')
        return RedirectResponse(url='/member/error', status_code=303)

@staticmethod
def login_member(db: Session, data: dict):
    try:
        # 비밀번호 해시 처리
        hashed_password = MemberService.sha256_hash(data['password'])

        # 회원 정보 조회
        member = db.query(Member).filter(
            Member.userid == data['userid'],
            Member.password == hashed_password
        ).first()

        # 로그인 성공 여부 반환
        if member:
            Request.session['mno'] = member.mno
            return member
        else:
            raise HTTPException(status_code=400, detail="Invalid username or password")
    except SQLAlchemyError as ex:
        print(f'Login Error: {str(ex)}')
        raise HTTPException(status_code=500, detail="Internal Server Error")



@member_router.get("/myinfo", response_class=HTMLResponse)
async def myinfo(req: Request, db: Session = Depends(get_db)):
    try:
        userid = req.session.get('userid')
        if not userid:
            return RedirectResponse(url='/member/login', status_code=303)

        user = db.query(Member).filter(Member.userid == userid).first()
        if user is None:
            return RedirectResponse(url='/member/loginfail', status_code=303)

        print(f"[INFO] Fetched info for user: {userid}")
        return templates.TemplateResponse("member/myinfo.html", {"request": req, "user": user})
    except Exception as ex:
        print(f'[ERROR] 회원 정보 페이지 오류: {str(ex)}')
        return RedirectResponse(url='/member/error', status_code=303)

@member_router.post("/modify", response_class=HTMLResponse)
async def modify_user_info(req: Request, db: Session = Depends(get_db)):
    try:
        form_data = await req.form()
        userid = req.session.get('userid')

        if not userid:
            return RedirectResponse(url='/member/login', status_code=303)

        user = db.query(Member).filter(Member.userid == userid).first()

        if user:
            if 'password' in form_data and form_data.get('password'):
                user.password = MemberService.sha256_hash(form_data.get('password'))
                print(f"[INFO] Password updated for user: {userid}")

            user.email = form_data.get('email')
            user.phone = form_data.get('phone')
            user.address = form_data.get('address')
            print(f"[INFO] User information updated for user: {userid}")

            db.commit()
            return HTMLResponse(content="Success", status_code=200)
        else:
            print("[WARNING] User not found during update")
            return HTMLResponse(content="User not found", status_code=404)

    except Exception as ex:
        db.rollback()
        print(f'[ERROR] 업데이트 오류: {str(ex)}')
        return HTMLResponse(content="Error", status_code=500)

@member_router.get("/logout", response_class=HTMLResponse)
async def logout(req: Request):
    req.session.clear()
    print(f"[INFO] User logged out")
    return RedirectResponse(url='/', status_code=303)

@member_router.get("/error", response_class=HTMLResponse)
async def error(req: Request):
    return templates.TemplateResponse("member/error.html", {"request": req})


# @member_router.delete("/{mno}", response_class=HTMLResponse)
# async def delete_user(req: Request, mno: int, db: Session = Depends(get_db)):
#     try:
#         session_mno = req.session.get('mno')  # 세션에서 mno 가져오기
#         if session_mno != mno:
#             return JSONResponse(status_code=403, content={"message": "Unauthorized"})
#
#         # 회원 탈퇴 실행
#         MemberService.delete_member(db, mno)
#
#         # 로그아웃 처리
#         req.session.clear()  # 세션에서 사용자 정보 제거
#         return JSONResponse(status_code=200, content={"message": "회원 탈퇴가 완료되었습니다."})
#
#     except Exception as ex:
#         print(f'[ERROR] 회원 탈퇴 오류: {str(ex)}')
#         return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

