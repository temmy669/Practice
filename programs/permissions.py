from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows access only to:
    - The owner of the object
    - Staff/superuser accounts (admins)
    """
    
    def has_object_permission(self, request, view, obj):
        # Admins have full access
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True
        
        # Owners have full access
        return obj.owner == request.user


class IsAuthenticatedOrReadOnlyShared(permissions.BasePermission):
    """
    Permission class that allows:
    - Authenticated users: full access
    - Unauthenticated users: read-only access to shared programs only
    """
    
    def has_permission(self, request, view):
        # Authenticated users always have permission at view level
        if request.user and request.user.is_authenticated:
            return True
        
        # Unauthenticated users can only access shared programs (read-only)
        # This is checked at the view level for the shared endpoint
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return False