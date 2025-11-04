"""
Django Forms for Knowledge Management System
"""
from django import forms
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.conf import settings
from .models import Document, UserProfile, AccessLevel, UserRole


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents"""
    
    class Meta:
        model = Document
        fields = ['title', 'file', 'access_level', 'department']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document Title'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': ','.join(settings.ALLOWED_EXTENSIONS)
            }),
            'access_level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Department (optional for department-level docs)'
            }),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size
            if file.size > settings.MAX_UPLOAD_SIZE:
                max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
                raise forms.ValidationError(f'File size exceeds maximum allowed size of {max_mb} MB')
            
            # Check file extension
            ext = '.' + file.name.split('.')[-1].lower()
            if ext not in settings.ALLOWED_EXTENSIONS:
                raise forms.ValidationError(f'File type not allowed. Allowed types: {", ".join(settings.ALLOWED_EXTENSIONS)}')
        
        return file
    
    def clean_department(self):
        department = self.cleaned_data.get('department', '').strip()
        access_level = self.cleaned_data.get('access_level')
        
        if access_level == AccessLevel.DEPARTMENT and not department:
            raise forms.ValidationError('Department is required for department-level access')
        
        return department


class QueryForm(forms.Form):
    """Form for submitting queries to the RAG system"""
    
    query = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ask a question about your documents...',
        }),
        max_length=1000,
        help_text='Ask questions about the content in your documents'
    )
    
    top_k = forms.IntegerField(
        initial=settings.FAISS_TOP_K,
        min_value=1,
        max_value=20,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
        }),
        help_text='Number of document chunks to retrieve'
    )
    
    temperature = forms.FloatField(
        initial=0.7,
        min_value=0.0,
        max_value=2.0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 0.1,
        }),
        help_text='Model creativity (0=focused, 2=creative)'
    )


class UserProfileForm(forms.ModelForm):
    """Form for editing user profiles"""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        disabled=True
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = UserProfile
        fields = ['role', 'department', 'preferred_chunk_size', 'max_query_results']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Engineering, Sales, HR'
            }),
            'preferred_chunk_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 200,
                'max': 2000
            }),
            'max_query_results': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user email if changed
        if 'email' in self.changed_data:
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
        
        if commit:
            profile.save()
        
        return profile


class UserCreationForm(forms.ModelForm):
    """Form for creating new users"""
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Minimum 8 characters'
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    role = forms.ChoiceField(
        choices=UserRole.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=UserRole.EMPLOYEE
    )
    
    department = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Department'
        }),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        
        if len(password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long")
        
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                department=self.cleaned_data.get('department', '')
            )
        
        return user


class DocumentFilterForm(forms.Form):
    """Form for filtering documents"""
    
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search documents...'
        })
    )
    
    access_level = forms.ChoiceField(
        choices=[('', 'All Access Levels')] + list(AccessLevel.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Department'
        })
    )
    
    file_type = forms.ChoiceField(
        choices=[
            ('', 'All Types'),
            ('pdf', 'PDF'),
            ('docx', 'Word'),
            ('txt', 'Text'),
            ('xlsx', 'Excel'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    processed = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('yes', 'Processed'),
            ('no', 'Not Processed'),
            ('error', 'Errors'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )