from django.urls import path
from .views import (
    ProgramView,
    ProgramDetailView,
    ProgramShareView,
    ProgramItemView,
    ProgramItemDetailView,
    DashboardView,
    SharedProgramView
)

urlpatterns = [
    # Program endpoints
    path('programs/', ProgramView.as_view(), name='program-list-create'),
    path('programs/<int:pk>/', ProgramDetailView.as_view(), name='program-detail'),
    path('programs/<int:pk>/share/', ProgramShareView.as_view(), name='program-share'),
    
    # Program item endpoints
    path('programs/<int:program_pk>/items/', ProgramItemView.as_view(), name='program-item-list-create'),
    path('programs/<int:program_pk>/items/<int:item_pk>/', ProgramItemDetailView.as_view(), name='program-item-detail'),
    
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Public shared program
    path('programs/shared/<str:share_token>/', SharedProgramView.as_view(), name='shared-program'),
]