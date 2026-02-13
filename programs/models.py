import secrets
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Max


class Program(models.Model):
    """
    Represents an event program (schedule/agenda).

    Programs can be shared publicly via a unique, non-guessable share token.
    Programs remain editable even after being shared.
    """
    #future optimization: add composite indexing on (owner, created_at) for faster user program listing
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateField()
    capacity = models.PositiveIntegerField(null=True, blank=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='programs',
        db_index=True,
    )

    share_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    shared_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def is_ready(self) -> bool:
        """
        Compute whether this program is ready to be shared.

        A program is ready if:
        1. It has at least one program item
        2. All items have valid time ranges (end > start)
        3. No items have overlapping time ranges
        """
        items = self.items.all()

        if not items.exists():
            return False

        items = list(items.order_by('start_time'))

        for i, item in enumerate(items):
            if item.end_time <= item.start_time:
                return False

            for other_item in items[i + 1:]:
                if self._items_conflict(item, other_item):
                    return False

        return True

    @property
    def shared_but_unready(self) -> bool:
        """
        Indicates a program that has been shared previously
        but is currently not in a ready state due to edits.
        """
        return self.shared_at is not None and not self.is_ready

    @staticmethod
    def _items_conflict(item_a, item_b) -> bool:
        """
        Two items conflict if their time ranges overlap.

        Back-to-back items (end == start) are allowed.
        """
        return (
            item_a.start_time < item_b.end_time
            and item_a.end_time > item_b.start_time
        )

    def generate_share_token(self):
        """
        Generate a cryptographically secure, unique share token.
        """
        if self.share_token:
            return

        while True:
            token = secrets.token_urlsafe(32)
            if not Program.objects.filter(share_token=token).exists():
                self.share_token = token
                break

class ProgramItem(models.Model):
    """
    Represents an individual session/item within a program.

    Items are ordered by position and validated by time range.
    """
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='items',
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    position = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']
        unique_together = ['program', 'position']

    def __str__(self):
        return f"{self.title} ({self.start_time} - {self.end_time})"

    def clean(self):
        """
        Basic model-level validation for time range correctness.
        """
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def save(self, *args, **kwargs):
        """
        Automatically assign position if not provided.

        Positions are sequential per program.
        """
        if self.position is None:
            max_position = (
                ProgramItem.objects
                .filter(program=self.program)
                .aggregate(max_pos=Max('position'))
                .get('max_pos')
            )
            self.position = (max_position or 0) + 1

        super().save(*args, **kwargs)
