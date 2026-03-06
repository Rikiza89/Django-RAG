import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeKnowledgeBase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Descriptive name for this code file/snippet', max_length=255)),
                ('description', models.TextField(blank=True, help_text='What this code does (used as RAG context)')),
                ('file', models.FileField(blank=True, null=True, upload_to='code_files/%Y/%m/%d/')),
                ('file_hash', models.CharField(help_text='SHA-256 hash for deduplication', max_length=64, unique=True)),
                ('file_size', models.IntegerField(default=0, help_text='Size in bytes')),
                ('language', models.CharField(
                    choices=[
                        ('python', 'Python'), ('javascript', 'JavaScript'), ('typescript', 'TypeScript'),
                        ('java', 'Java'), ('cpp', 'C++'), ('c', 'C'), ('go', 'Go'), ('rust', 'Rust'),
                        ('php', 'PHP'), ('ruby', 'Ruby'), ('swift', 'Swift'), ('kotlin', 'Kotlin'),
                        ('csharp', 'C#'), ('html', 'HTML'), ('css', 'CSS'), ('sql', 'SQL'),
                        ('shell', 'Shell/Bash'), ('markdown', 'Markdown'), ('json', 'JSON'),
                        ('yaml', 'YAML'), ('other', 'Other'),
                    ],
                    default='other',
                    max_length=20,
                )),
                ('is_processed', models.BooleanField(default=False)),
                ('processing_error', models.TextField(blank=True, null=True)),
                ('chunk_count', models.IntegerField(default=0)),
                ('content_preview', models.TextField(blank=True, help_text='First 600 chars of source code')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('tags', models.CharField(blank=True, help_text='Comma-separated tags for filtering', max_length=255)),
                ('uploaded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='code_files',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='CodeChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_index', models.IntegerField()),
                ('content', models.TextField()),
                ('embedding_id', models.CharField(max_length=64, unique=True)),
                ('start_line', models.IntegerField(default=0, help_text='Approximate start line in source file')),
                ('chunk_type', models.CharField(
                    choices=[('code', 'Code'), ('comment', 'Comment/Docstring'), ('mixed', 'Mixed')],
                    default='code',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('code_file', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chunks',
                    to='coding_ide.codeknowledgebase',
                )),
            ],
            options={
                'ordering': ['code_file', 'chunk_index'],
                'unique_together': {('code_file', 'chunk_index')},
            },
        ),
        migrations.CreateModel(
            name='CodeQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_text', models.TextField()),
                ('response_text', models.TextField()),
                ('source_files', models.JSONField(default=list, help_text='List of CodeKnowledgeBase IDs used')),
                ('language_filter', models.CharField(blank=True, help_text='Language filter applied', max_length=20)),
                ('retrieval_time_ms', models.IntegerField(default=0)),
                ('inference_time_ms', models.IntegerField(default=0)),
                ('total_time_ms', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='code_queries',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='codeknowledgebase',
            index=models.Index(fields=['language', 'uploaded_at'], name='coding_ide__languag_idx'),
        ),
        migrations.AddIndex(
            model_name='codeknowledgebase',
            index=models.Index(fields=['uploaded_by', 'uploaded_at'], name='coding_ide__uploade_idx'),
        ),
        migrations.AddIndex(
            model_name='codeknowledgebase',
            index=models.Index(fields=['file_hash'], name='coding_ide__file_ha_idx'),
        ),
        migrations.AddIndex(
            model_name='codequerylog',
            index=models.Index(fields=['user', '-created_at'], name='coding_ide__user_id_idx'),
        ),
    ]
