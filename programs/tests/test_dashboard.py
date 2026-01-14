from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime
from programs.models import Program, ProgramItem


class DashboardOverviewEndpointTest(TestCase):
    """
    Test Suite 7: Dashboard Overview Endpoint
    Satisfies the explicit requirement for a dashboard view.
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='alice', password='pass123')
        self.other_user = User.objects.create_user(username='bob', password='pass456')
    
    def test_dashboard_returns_only_users_programs(self):
        """Dashboard returns only programs owned by the user."""
        # Create programs for both users
        Program.objects.create(title='Alice Event 1', date='2026-06-15', owner=self.user)
        Program.objects.create(title='Alice Event 2', date='2026-07-20', owner=self.user)
        Program.objects.create(title='Bob Event', date='2026-08-10', owner=self.other_user)
        
        self.client.force_authenticate(user=self.user) # type: ignore
        response = self.client.get('/api/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['programs']), 2)
        self.assertEqual(response.data['total_count'], 2)
    
    def test_dashboard_includes_readiness_status(self):
        """Each program in dashboard includes readiness status."""
        program = Program.objects.create(title='Conference', date='2026-06-15', owner=self.user)
        
        self.client.force_authenticate(user=self.user) # type: ignore
        response = self.client.get('/api/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        program_data = response.data['programs'][0]
        self.assertIn('is_ready', program_data)
        self.assertFalse(program_data['is_ready'])  # No items yet
    
    def test_dashboard_includes_share_status(self):
        """Each program in dashboard includes share status."""
        program = Program.objects.create(title='Conference', date='2026-06-15', owner=self.user)
        ProgramItem.objects.create(
            program=program,
            title='Session',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 0),
            position=1
        )
        program.generate_share_token()
        program.save()
        
        self.client.force_authenticate(user=self.user) # type: ignore
        response = self.client.get('/api/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        program_data = response.data['programs'][0]
        self.assertIn('is_shared', program_data)
        self.assertTrue(program_data['is_shared'])
        self.assertIsNotNone(program_data['share_url'])
    
