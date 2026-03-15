from django.urls import path
from . import views

app_name = 'papers'

urlpatterns = [
    path('', views.UploadPaperView.as_view(), name='upload'),
    path('paper/<int:pk>/', views.PaperDetailView.as_view(), name='detail'),
    path('paper/<int:pk>/explain/', views.GenerateExplanationView.as_view(), name='explain_section'),
]
