from flask import Blueprint, current_app
from flask_jwt_extended import get_jwt

from app.services.dashboard_service import DashboardService
from app.utils.response import success_response
from app.utils.decorators import roles_required
from app.utils.cache import dashboard_cache

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1/dashboard')


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/admin — admin KPI overview (admin only)
#
# SMS-064: results are cached per-tenant for DASHBOARD_CACHE_TTL seconds
# (default 300). A TTL of 0 disables caching (used in tests).
# ---------------------------------------------------------------------------

@dashboard_bp.route('/admin', methods=['GET'], strict_slashes=False)
@roles_required('admin')
def admin_kpis():
    ttl = current_app.config.get('DASHBOARD_CACHE_TTL', 300)
    if ttl and ttl > 0:
        # Namespace by school so tenants never share cached aggregates.
        school_slug = get_jwt().get('school_slug', 'default')
        cache_key = f'admin_kpis:{school_slug}'
        cached = dashboard_cache.get(cache_key)
        if cached is not None:
            return success_response(data=cached, message='Admin dashboard retrieved (cached)')
        data = DashboardService.get_admin_kpis()
        dashboard_cache.set(cache_key, data, ttl)
        return success_response(data=data, message='Admin dashboard retrieved')

    data = DashboardService.get_admin_kpis()
    return success_response(data=data, message='Admin dashboard retrieved')
