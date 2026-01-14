from rest_framework import serializers
from django.utils import timezone
from .models import Program, ProgramItem


class ProgramItemSerializer(serializers.ModelSerializer):
    """Serializer for ProgramItem with time validation and conflict detection."""
    
    class Meta:
        model = ProgramItem
        fields = ['id', 'title', 'description', 'start_time', 'end_time', 'position', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Cross-field validation:
        1. end_time must be after start_time
        2. No time conflicts with sibling items
        """
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # Validate time range
        if end_time and start_time and end_time <= start_time:
            raise serializers.ValidationError({
                'end_time': 'End time must be after start time.'
            })
        
        # Get program from context (set in view)
        program = self.context.get('program')
        if not program:
            return data
        
        # Get all sibling items (exclude self if updating)
        sibling_items = program.items.all()
        if self.instance:
            sibling_items = sibling_items.exclude(pk=self.instance.pk)
        
        # Check for time conflicts
        for sibling in sibling_items:
            if self._check_conflict(start_time, end_time, sibling.start_time, sibling.end_time):
                raise serializers.ValidationError({
                    'start_time': f'Time conflict with "{sibling.title}" ({sibling.start_time} - {sibling.end_time})'
                })
        
        return data

    @staticmethod
    def _check_conflict(start_a, end_a, start_b, end_b):
        """Check if two time ranges overlap."""
        return (start_a < end_b) and (end_a > start_b)


class ProgramSerializer(serializers.ModelSerializer):
    """Serializer for Program with nested items and computed readiness."""
    
    items = ProgramItemSerializer(many=True, read_only=True)
    is_ready = serializers.ReadOnlyField()
    is_shared = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Program
        fields = [
            'id', 'title', 'description', 'date', 'capacity', 'owner',
            'share_token', 'shared_at', 'created_at', 'updated_at',
            'items', 'is_ready', 'is_shared', 'share_url', 'item_count'
        ]
        read_only_fields = ['id', 'owner', 'share_token', 'shared_at', 'created_at', 'updated_at']

    def get_is_shared(self, obj):
        """Return whether the program has been shared."""
        return obj.share_token is not None

    def get_share_url(self, obj):
        """Return the public share URL if the program is shared."""
        if obj.share_token:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/programs/shared/{obj.share_token}/')
        return None

    def get_item_count(self, obj):
        """Return the number of items in this program."""
        return obj.items.count()


class ProgramListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for program lists (e.g., dashboard)."""
    
    is_ready = serializers.ReadOnlyField()
    is_shared = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Program
        fields = [
            'id', 'title', 'date', 'capacity', 'created_at', 'updated_at',
            'is_ready', 'is_shared', 'share_url', 'item_count'
        ]

    def get_is_shared(self, obj):
        return obj.share_token is not None

    def get_share_url(self, obj):
        if obj.share_token:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/programs/shared/{obj.share_token}/')
        return None

    def get_item_count(self, obj):
        return obj.items.count()


class SharedProgramSerializer(serializers.ModelSerializer):
    """Read-only serializer for publicly shared programs."""
    
    items = ProgramItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Program
        fields = [
            'id', 'title', 'description', 'date', 'capacity',
            'shared_at', 'items', 'item_count'
        ]
        read_only_fields = fields

    def get_item_count(self, obj):
        return obj.items.count()