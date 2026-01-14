from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime
from programs.models import Program, ProgramItem

class ProgramItemTimeValidationTest(TestCase):
    """
    Test Suite 2: Program Item Time Validation
    Enforces the most important correctness rule: valid time ranges.
    """ 
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='alice', password='pass123')
        self.program = Program.objects.create(
            title='Test Event',
            date='2026-06-15',
            owner=self.user
        )
        self.client.force_authenticate(user=self.user)
    
    def test_creating_item_with_end_before_start_fails(self):
        """Creating an item with end_time <= start_time fails."""
        data = {
            'title': 'Invalid Session',
            'start_time': '2026-06-15T10:00:00Z',
            'end_time': '2026-06-15T09:00:00Z',  # End before start
            'position': 1
        }
        response = self.client.post(f'/api/programs/{self.program.id}/items/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_time', response.data)
    
    def test_updating_item_to_invalid_time_range_fails(self):
        """Updating an item to an invalid time range fails."""
        item = ProgramItem.objects.create(
            program=self.program,
            title='Valid Session',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 0),
            position=1
        )
        
        data = {
            'start_time': '2026-06-15T11:00:00Z',
            'end_time': '2026-06-15T10:00:00Z'  # End before start
        }
        response = self.client.patch(f'/api/programs/{self.program.id}/items/{item.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_time', response.data)


class ProgramItemConflictDetectionTest(TestCase):
    """
    Test Suite 3: Program Item Conflict Detection
    Core business logic - prevents overlapping schedule items.
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
    
    def test_creating_overlapping_item_fails(self):
        """Creating an item that overlaps an existing item fails."""
        # Create first item: 9:00 - 10:30
        ProgramItem.objects.create(
            program=self.program,
            title='Opening Keynote',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 30),
            position=1
        )
        
        # Try to create overlapping item: 10:00 - 11:00
        data = {
            'title': 'Conflicting Session',
            'start_time': '2026-06-15T10:00:00Z',
            'end_time': '2026-06-15T11:00:00Z',
            'position': 2
        }
        response = self.client.post(f'/api/programs/{self.program.id}/items/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_time', response.data)
    

class ProgramReadinessCalculationTest(TestCase):
    """
    Test Suite 4: Program Readiness Calculation
    Validates derived state - a key design decision.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass123')
        self.program = Program.objects.create(
            title='Tech Conference',
            date='2026-06-15',
            owner=self.user
        )
    
    def test_program_with_no_items_is_not_ready(self):
        """A program with no items is not ready."""
        self.assertFalse(self.program.is_ready)
    
    def test_program_with_valid_non_overlapping_items_is_ready(self):
        """A program with valid, non-overlapping items is ready."""
        ProgramItem.objects.create(
            program=self.program,
            title='Session 1',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 0),
            position=1
        )
        ProgramItem.objects.create(
            program=self.program,
            title='Session 2',
            start_time=datetime(2026, 6, 15, 10, 0),  # Adjacent, not overlapping
            end_time=datetime(2026, 6, 15, 11, 0),
            position=2
        )
        
        self.assertTrue(self.program.is_ready)
    
    def test_program_with_conflicting_items_is_not_ready(self):
        """A program with conflicting items is not ready."""
        ProgramItem.objects.create(
            program=self.program,
            title='Session 1',
            start_time=datetime(2026, 6, 15, 9, 0),
            end_time=datetime(2026, 6, 15, 10, 30),
            position=1
        )
        ProgramItem.objects.create(
            program=self.program,
            title='Session 2',
            start_time=datetime(2026, 6, 15, 10, 0),  # Overlaps
            end_time=datetime(2026, 6, 15, 11, 0),
            position=2
        )
        
        self.assertFalse(self.program.is_ready)


