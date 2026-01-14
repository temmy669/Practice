from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime
from programs.models import Program, ProgramItem


class PublicAccessToSharedProgramsTest(TestCase):
    """
    Test Suite 6: Public Access to Shared Programs
    Proves external sharing works safely without authentication.
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='alice', password='pass123')
        self.program = Program.objects.create(
            title='Public Conference',
            date='2026-06-15',
            owner=self.user
        )
        # Make it ready and share it
        ProgramItem.objects.create(
            program=self.program,
            title='Opening Session',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 0),
            position=1
        )
        self.program.generate_share_token()
        self.program.save()
    
    def test_shared_program_accessible_without_authentication(self):
        """A shared program can be accessed without authentication."""
        # No authentication
        response = self.client.get(f'/api/programs/shared/{self.program.share_token}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Public Conference')
        self.assertEqual(len(response.data['items']), 1)
    
    def test_invalid_share_token_returns_404(self):
        """An invalid share token returns 404."""
        response = self.client.get('/api/programs/shared/invalid-token-xyz/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
