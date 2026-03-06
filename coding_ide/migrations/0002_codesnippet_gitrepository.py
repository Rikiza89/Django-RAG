import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coding_ide', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeSnippet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Snippet name', max_length=255)),
                ('language', models.CharField(
                    choices=[
                        ('python', 'Python'), ('javascript', 'JavaScript'), ('typescript', 'TypeScript'),
                        ('java', 'Java'), ('cpp', 'C++'), ('c', 'C'), ('go', 'Go'), ('rust', 'Rust'),
                        ('php', 'PHP'), ('ruby', 'Ruby'), ('swift', 'Swift'), ('kotlin', 'Kotlin'),
                        ('csharp', 'C#'), ('html', 'HTML'), ('css', 'CSS'), ('sql', 'SQL'),
                        ('shell', 'Shell/Bash'), ('markdown', 'Markdown'), ('json', 'JSON'),
                        ('yaml', 'YAML'), ('other', 'Other'),
                    ],
                    default='python',
                    max_length=20,
                )),
                ('content', models.TextField(blank=True, help_text='Source code content')),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='code_snippets',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-modified_at'],
            },
        ),
        migrations.CreateModel(
            name='GitRepository',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Display name for this repo', max_length=255)),
                ('path', models.CharField(help_text='Absolute path on the server', max_length=1024, unique=True)),
                ('current_branch', models.CharField(blank=True, default='main', max_length=255)),
                ('is_initialized', models.BooleanField(default=False)),
                ('remote_url', models.CharField(blank=True, help_text='git remote origin URL', max_length=1024)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('added_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='git_repos',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Git Repository',
                'verbose_name_plural': 'Git Repositories',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='codesnippet',
            index=models.Index(fields=['created_by', '-modified_at'], name='coding_ide__snippet_idx'),
        ),
    ]
