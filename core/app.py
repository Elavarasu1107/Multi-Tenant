from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


async def db_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        content={"message": str(exc), "status": "fail"},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        content={"message": exc.detail, "status": "fail"},
        status_code=exc.status_code,
    )


async def base_exc(request: Request, exc: Exception):
    return JSONResponse(
        content={"message": str(exc), "status": "error"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def create_app(title: str, lifespan=None):
    app = FastAPI(title=title, lifespan=lifespan)
    app.add_exception_handler(SQLAlchemyError, db_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, base_exc)
    return app
