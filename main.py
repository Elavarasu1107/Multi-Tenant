from core.app import create_app
from tenant.routes import user
from tenant.routes_stats import statistics

app = create_app(title="Tenant")

app.include_router(router=user)
app.include_router(router=statistics)
