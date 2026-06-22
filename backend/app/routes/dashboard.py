from flask import Blueprint

from app.services.dashboard_service import DashboardService
from app.utils.response import success_response
from app.utils.decorators import roles_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1/dashboard')


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/admin — admin KPI overview (admin only)
# ---------------------------------------------------------------------------

@dashboard_bp.route('/admin', methods=['GET'], strict_slashes=False)
@roles_required('admin')
def admin_kpis():
    data = DashboardService.get_admin_kpis()
    return success_response(data=data, message='Admin dashboard retrieved')
