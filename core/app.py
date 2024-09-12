from fastapi import FastAPI


def create_app(title: str, lifespan=None):
    app = FastAPI(title=title, lifespan=lifespan)
    return app
