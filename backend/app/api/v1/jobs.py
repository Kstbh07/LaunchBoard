"""V1 Jobs router forwarding to core jobs router."""
from app.api.jobs import CityCount, RoleCount, router

__all__ = ["CityCount", "RoleCount", "router"]
