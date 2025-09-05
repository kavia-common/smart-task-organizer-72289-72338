from flask_smorest import Blueprint
from flask.views import MethodView
from ..schemas import HealthResponseSchema

# Use a concise, correctly spelled tag and blueprint identifiers
blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")

@blp.route("/")
class HealthCheck(MethodView):
    @blp.response(200, HealthResponseSchema)
    @blp.doc(
        summary="Health check",
        description="Returns a static message to indicate the service is healthy.",
        operationId="health_check",
        tags=["Health"],
        responses={200: {"description": "Service is healthy"}},
    )
    def get(self):
        return {"message": "Healthy"}
