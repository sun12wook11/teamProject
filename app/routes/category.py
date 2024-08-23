from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

category_router = APIRouter()
templates = Jinja2Templates(directory='views/templates')


@category_router.get("/shop", response_class=HTMLResponse)
async def shop(request: Request):
    return templates.TemplateResponse("category/shop.html", {"request": request})
