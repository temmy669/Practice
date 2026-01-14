from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime
from programs.models import Program, ProgramItem


class ProgramCreationAndOwnershipTest(TestCase):
    """
    Test Suite 1: Program Creation & Ownership
    Proves the core domain exists and ownership is enforced.
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='alice', password='pass123')
        self.other_user = User.objects.create_user(username='bob', password='pass456')
    
    def test_authenticated_user_can_create_program(self):
        """An authenticated user can create a program."""
        self.client.force_authenticate(user=self.user)  # type: ignore
        
        data = {
            'title': 'Tech Conference 2026',
            'description': 'Annual tech event',
            'date': '2026-06-15',
            'capacity': 200
        }
        response = self.client.post('/api/programs/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Tech Conference 2026')
        self.assertEqual(response.data['owner'], self.user.id)
    
    def test_creating_user_is_set_as_owner(self):
        """The creating user is automatically set as the program owner."""
        self.client.force_authenticate(user=self.user)  # type: ignore
        
        data = {'title': 'My Event', 'date': '2026-07-01'}
        response = self.client.post('/api/programs/', data)
        
        program = Program.objects.get(id=response.data['id'])
        self.assertEqual(program.owner, self.user)
    
    def test_user_cannot_access_another_users_program(self):
        """A user cannot access programs owned by other users."""
        program = Program.objects.create(
            title='Bob Program',
            date='2026-08-01',
            owner=self.other_user
        )
        
        self.client.force_authenticate(user=self.user)  # type: ignore
        response = self.client.get(f'/api/programs/{program.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_user_cannot_modify_another_users_program(self):
        """A user cannot modify programs owned by other users."""
        program = Program.objects.create(
            title='Bob Program',
            date='2026-08-01',
            owner=self.other_user
        )
        
        self.client.force_authenticate(user=self.user) # type: ignore
        data = {'title': 'Hacked Title'}
        response = self.client.patch(f'/api/programs/{program.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

