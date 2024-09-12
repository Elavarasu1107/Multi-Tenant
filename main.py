from core.app import create_app
from tenant.routes import user

app = create_app(title="Tenant")

app.include_router(router=user)
