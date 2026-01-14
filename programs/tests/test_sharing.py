from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime
from programs.models import Program, ProgramItem


class ProgramSharingRulesTest(TestCase):
    """
    Test Suite 5: Program Sharing Rules
    Proves the sharing concept is sound and guarded by readiness.
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='alice', password='pass123')
        self.program = Program.objects.create(
            title='Tech Conference',
            date='2026-06-15',
            owner=self.user
        )
        self.client.force_authenticate(user=self.user)
    
    def test_unready_program_cannot_be_shared(self):
        """An unready program cannot be shared."""
        response = self.client.post(f'/api/programs/{self.program.id}/share/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_sharing_ready_program_generates_share_token(self):
        """Sharing a ready program generates a share token."""
        # Make program ready
        ProgramItem.objects.create(
            program=self.program,
            title='Session',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 0),
            position=1
        )
        
        response = self.client.post(f'/api/programs/{self.program.id}/share/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['program']['share_token'])
        self.assertIsNotNone(response.data['program']['shared_at'])
    
    def test_sharing_already_shared_program_does_not_generate_new_token(self):
        """Sharing an already shared program does not generate a new token."""
        # Make program ready and share it
        ProgramItem.objects.create(
            program=self.program,
            title='Session',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 0),
            position=1
        )
        
        response1 = self.client.post(f'/api/programs/{self.program.id}/share/')
        first_token = response1.data['program']['share_token']
        
        response2 = self.client.post(f'/api/programs/{self.program.id}/share/')
        second_token = response2.data['program']['share_token']
        
        self.assertEqual(first_token, second_token)
        self.assertIn('already shared', response2.data['message'])
