from django import forms
from django.conf import settings
from .models import CodeKnowledgeBase, CodeLanguage


class CodeUploadForm(forms.ModelForm):
    class Meta:
        model = CodeKnowledgeBase
        fields = ['title', 'description', 'file', 'language', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. "Auth middleware — FastAPI"'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Brief description of what this code does (helps RAG retrieval)',
            }),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': ','.join(settings.CODE_ALLOWED_EXTENSIONS)}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. auth, middleware, fastapi'}),
        }
        help_texts = {
            'description': 'A clear description improves code retrieval accuracy.',
            'tags': 'Comma-separated tags for filtering (optional).',
            'file': f"Accepted: {', '.join(settings.CODE_ALLOWED_EXTENSIONS)}",
        }

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            import os
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in settings.CODE_ALLOWED_EXTENSIONS:
                raise forms.ValidationError(f"Unsupported file type: {ext}")
        return f


class CodeQueryForm(forms.Form):
    query = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 4,
            'placeholder': (
                'Describe what you need:\n'
                '  • "Write a Python function to parse JWT tokens"\n'
                '  • "Explain how the authentication middleware works"\n'
                '  • "Fix the bug in the user login handler"'
            ),
        }),
        label='Your Coding Request',
        help_text='Describe the code you want to write, understand, or debug.',
    )
    language_filter = forms.ChoiceField(
        choices=[('', 'All Languages')] + [(v, l) for v, l in CodeLanguage.choices],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Language Filter',
        help_text='Restrict retrieval to a specific language (optional).',
    )
    top_k = forms.IntegerField(
        min_value=1, max_value=10,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Code Snippets to Retrieve',
        help_text='How many code snippets to use as context.',
    )
    temperature = forms.FloatField(
        min_value=0.0, max_value=1.0,
        initial=0.2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05'}),
        label='Temperature',
        help_text='Lower = more deterministic code (0.2 recommended).',
    )
