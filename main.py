from core.app import create_app
from tenant.routes import router

app = create_app(title="Tenant")

app.include_router(router=router)
