from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Program, ProgramItem
from .serializers import (
    ProgramSerializer, ProgramListSerializer, ProgramItemSerializer,
    SharedProgramSerializer
)
from .permissions import IsOwnerOrAdmin, IsAuthenticatedOrReadOnlyShared


class ProgramView(APIView):
    """
    GET: List all programs for the authenticated user
    POST: Create a new program
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return programs owned by the current user (or all if admin)."""
        user = request.user
        if user.is_staff or user.is_superuser:
            programs = Program.objects.all()
        else:
            programs = Program.objects.filter(owner=user)
        
        serializer = ProgramListSerializer(programs, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new program owned by the current user."""
        serializer = ProgramSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProgramDetailView(APIView):
    """
    GET: Retrieve a specific program
    PUT/PATCH: Update a program
    DELETE: Delete a program
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_object(self, pk, user):
        """Get program and check permissions."""
        if user.is_staff or user.is_superuser:
            return get_object_or_404(Program, pk=pk)
        return get_object_or_404(Program, pk=pk, owner=user)
    
    def get(self, request, pk):
        """Retrieve program details."""
        program = self.get_object(pk, request.user)
        self.check_object_permissions(request, program)
        serializer = ProgramSerializer(program, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update entire program."""
        program = self.get_object(pk, request.user)
        self.check_object_permissions(request, program)
        serializer = ProgramSerializer(program, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partially update program."""
        program = self.get_object(pk, request.user)
        self.check_object_permissions(request, program)
        serializer = ProgramSerializer(program, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete a program."""
        program = self.get_object(pk, request.user)
        self.check_object_permissions(request, program)
        program.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProgramShareView(APIView):
    """
    POST: Share a program by generating a share token
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def post(self, request, pk):
        """Share a program publicly if it's ready."""
        user = request.user
        if user.is_staff or user.is_superuser:
            program = get_object_or_404(Program, pk=pk)
        else:
            program = get_object_or_404(Program, pk=pk, owner=user)
        
        self.check_object_permissions(request, program)
        
        # Check if already shared
        if program.share_token:
            serializer = ProgramSerializer(program, context={'request': request})
            return Response({
                'message': 'Program is already shared.',
                'program': serializer.data
            })
        
        # Check if program is ready
        if not program.is_ready:
            return Response({
                'error': 'Program is not ready to be shared. Ensure it has at least one item with valid times and no conflicts.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate share token and save
        program.generate_share_token()
        program.shared_at = timezone.now()
        program.save()
        
        serializer = ProgramSerializer(program, context={'request': request})
        return Response({
            'message': 'Program shared successfully.',
            'program': serializer.data
        }, status=status.HTTP_200_OK)


class ProgramItemView(APIView):
    """
    GET: List all items for a program
    POST: Create a new item for a program
    """
    permission_classes = [IsAuthenticated]
    
    def get_program(self, program_pk, user):
        """Get the parent program and check permissions."""
        if user.is_staff or user.is_superuser:
            return get_object_or_404(Program, pk=program_pk)
        return get_object_or_404(Program, pk=program_pk, owner=user)
    
    def get(self, request, program_pk):
        """List all items for a program."""
        program = self.get_program(program_pk, request.user)
        items = program.items.all()
        serializer = ProgramItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request, program_pk):
        """Create a new item for a program."""
        program = self.get_program(program_pk, request.user)
        serializer = ProgramItemSerializer(data=request.data, context={'program': program, 'request': request})
        if serializer.is_valid():
            serializer.save(program=program)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProgramItemDetailView(APIView):
    """
    GET: Retrieve a specific program item
    PUT/PATCH: Update a program item
    DELETE: Delete a program item
    """
    permission_classes = [IsAuthenticated]
    
    def get_program_and_item(self, program_pk, item_pk, user): #Here ownership is enforced via parent program lookup.
        """Get program and item, check permissions."""
        if user.is_staff or user.is_superuser:
            program = get_object_or_404(Program, pk=program_pk)
        else:
            program = get_object_or_404(Program, pk=program_pk, owner=user)
        
        item = get_object_or_404(ProgramItem, pk=item_pk, program=program)
        return program, item
    
    def get(self, request, program_pk, item_pk):
        """Retrieve item details."""
        program, item = self.get_program_and_item(program_pk, item_pk, request.user)
        serializer = ProgramItemSerializer(item, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, program_pk, item_pk):
        """Update entire item."""
        program, item = self.get_program_and_item(program_pk, item_pk, request.user)
        serializer = ProgramItemSerializer(item, data=request.data, context={'program': program, 'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, program_pk, item_pk):
        """Partially update item."""
        program, item = self.get_program_and_item(program_pk, item_pk, request.user)
        serializer = ProgramItemSerializer(item, data=request.data, partial=True, context={'program': program, 'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, program_pk, item_pk):
        """Delete an item."""
        program, item = self.get_program_and_item(program_pk, item_pk, request.user)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardView(APIView):
    """
    GET: Dashboard overview of all user's programs
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return overview of all user's programs with metadata."""
        user = request.user
        
        if user.is_staff or user.is_superuser:
            programs = Program.objects.all()
        else:
            programs = Program.objects.filter(owner=user)
        
        serializer = ProgramListSerializer(programs, many=True, context={'request': request})
        
        return Response({
            'programs': serializer.data,
            'total_count': programs.count()
        })


class SharedProgramView(APIView):
    """
    GET: View a shared program (public access)
    """
    permission_classes = [IsAuthenticatedOrReadOnlyShared]
    
    def get(self, request, share_token):
        """Return shared program details (accessible to anyone)."""
        program = get_object_or_404(Program, share_token=share_token)
        serializer = SharedProgramSerializer(program, context={'request': request})
        return Response(serializer.data)