"""
Management command to setup the Knowledge Management System
Usage: python manage.py setup_system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app_core.models import UserProfile, UserRole
from app_core.cache_manager import embedding_cache
from app_core.ollama_client import ollama_client
import sys


class Command(BaseCommand):
    help = 'Setup the Knowledge Management System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-models',
            action='store_true',
            help='Skip downloading/checking models',
        )
        parser.add_argument(
            '--create-demo-users',
            action='store_true',
            help='Create demo users (admin, manager, employee)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Knowledge Management System Setup'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Check database
        self.stdout.write('Checking database...')
        try:
            User.objects.count()
            self.stdout.write(self.style.SUCCESS('✓ Database is ready'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database error: {str(e)}'))
            self.stdout.write(self.style.WARNING('Run: python manage.py migrate'))
            sys.exit(1)

        self.stdout.write('')

        # Check/download embedding model
        if not options['skip_models']:
            self.stdout.write('Checking embedding model...')
            try:
                cache_status = embedding_cache.check_cache_status()
                
                if cache_status['is_cached']:
                    self.stdout.write(self.style.SUCCESS('✓ Embedding model is cached'))
                    self.stdout.write(f"  Model: {cache_status['model_name']}")
                    self.stdout.write(f"  Size: {cache_status['cache_size_mb']} MB")
                else:
                    self.stdout.write(self.style.WARNING('⚠ Embedding model not cached'))
                    self.stdout.write('  Downloading model (requires internet)...')
                    
                    try:
                        model = embedding_cache.get_model()
                        self.stdout.write(self.style.SUCCESS('✓ Model downloaded and cached'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'✗ Failed to download model: {str(e)}'))
                        self.stdout.write(self.style.WARNING('  You can download it later with:'))
                        self.stdout.write('  python manage.py shell')
                        self.stdout.write('  >>> from app_core.cache_manager import embedding_cache')
                        self.stdout.write('  >>> embedding_cache.get_model()')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error checking model: {str(e)}'))

            self.stdout.write('')

            # Check Ollama
            self.stdout.write('Checking Ollama...')
            try:
                if ollama_client.check_connection():
                    self.stdout.write(self.style.SUCCESS('✓ Ollama is running'))
                    
                    if ollama_client.check_model_available():
                        self.stdout.write(self.style.SUCCESS(f'✓ Model {ollama_client.model} is available'))
                    else:
                        self.stdout.write(self.style.WARNING(f'⚠ Model {ollama_client.model} not found'))
                        self.stdout.write(f'  Run: ollama pull {ollama_client.model}')
                else:
                    self.stdout.write(self.style.WARNING('⚠ Ollama is not running'))
                    self.stdout.write('  Start Ollama with: ollama serve')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error checking Ollama: {str(e)}'))

            self.stdout.write('')

        # Create demo users if requested
        if options['create_demo_users']:
            self.stdout.write('Creating demo users...')
            
            demo_users = [
                {
                    'username': 'admin',
                    'password': 'admin123',
                    'email': 'admin@example.com',
                    'is_superuser': True,
                    'role': UserRole.ADMIN,
                    'department': 'Administration'
                },
                {
                    'username': 'manager',
                    'password': 'manager123',
                    'email': 'manager@example.com',
                    'is_superuser': False,
                    'role': UserRole.MANAGER,
                    'department': 'Engineering'
                },
                {
                    'username': 'employee',
                    'password': 'employee123',
                    'email': 'employee@example.com',
                    'is_superuser': False,
                    'role': UserRole.EMPLOYEE,
                    'department': 'Engineering'
                }
            ]
            
            for user_data in demo_users:
                username = user_data['username']
                
                if User.objects.filter(username=username).exists():
                    self.stdout.write(f'  - {username}: Already exists')
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=user_data['email'],
                        password=user_data['password'],
                        is_superuser=user_data['is_superuser'],
                        is_staff=user_data['is_superuser']
                    )
                    
                    UserProfile.objects.create(
                        user=user,
                        role=user_data['role'],
                        department=user_data['department']
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created {username} (password: {user_data["password"]})'))
            
            self.stdout.write('')

        # Summary
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Setup Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        users_count = User.objects.count()
        docs_count = 0
        try:
            from app_core.models import Document
            docs_count = Document.objects.count()
        except:
            pass
        
        self.stdout.write(f'Total Users: {users_count}')
        self.stdout.write(f'Total Documents: {docs_count}')
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('Next Steps:'))
        self.stdout.write('1. Start Ollama: ollama serve')
        self.stdout.write('2. Start Django: python manage.py runserver')
        self.stdout.write('3. Open browser: http://localhost:8000')
        self.stdout.write('')
        
        if options['create_demo_users']:
            self.stdout.write(self.style.WARNING('Demo Credentials:'))
            self.stdout.write('  Admin:    admin / admin123')
            self.stdout.write('  Manager:  manager / manager123')
            self.stdout.write('  Employee: employee / employee123')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('⚠ Change these passwords in production!'))
            self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('✓ Setup complete!'))