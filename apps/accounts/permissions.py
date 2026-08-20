from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and (request.user.is_staff or obj.id == request.user.id))

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or (request.user.role and request.user.role.name == 'admin')))

class HasRolePermission(permissions.BasePermission):
    def __init__(self, resource, action):
        self.resource = resource
        self.action = action

    def has_permission(self, request, view):
        return request.user and request.user.has_perm_for(self.resource, self.action)
