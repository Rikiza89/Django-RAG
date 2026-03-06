"""
Management command: cache_models
================================
Downloads and caches the shared embedding model used by both
app_core (Knowledge Hub) and coding_ide (Coding IDE).

Usage:
    python manage.py cache_models
    python manage.py cache_models --check   # status only, no download
    python manage.py cache_models --force   # re-download even if cached
"""
import sys
import time

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Download and cache the shared embedding model for offline use'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', action='store_true',
            help='Show cache status without downloading'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Re-download even if already cached'
        )

    def handle(self, *args, **options):
        from app_core.cache_manager import embedding_cache

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  Embedding Model Cache Manager'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f"  Model : {settings.EMBEDDING_MODEL}")
        self.stdout.write(f"  Cache : {settings.MODELS_CACHE_DIR}")
        self.stdout.write(f"  Device: cpu (always)")
        self.stdout.write('')

        status = embedding_cache.check_cache_status()

        # ------------------------------------------------------------------
        # --check flag: just report and exit
        # ------------------------------------------------------------------
        if options['check']:
            if status['is_cached']:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Model is cached ({status['cache_size_mb']} MB)"
                ))
                self.stdout.write(f"  Path: {status['cache_path']}")
            else:
                self.stdout.write(self.style.WARNING(
                    '⚠  Model not yet downloaded.'
                ))
                self.stdout.write('  Run:  python manage.py cache_models')
            if status['model_loaded']:
                self.stdout.write(self.style.SUCCESS('✓ Model is loaded in memory'))
            self.stdout.write('')
            return

        # ------------------------------------------------------------------
        # Download / load
        # ------------------------------------------------------------------
        if status['is_cached'] and not options['force']:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Already cached ({status['cache_size_mb']} MB)  →  {status['cache_path']}"
            ))
            self.stdout.write('')
            self.stdout.write('  Loading into memory to verify…')
            try:
                t0 = time.time()
                embedding_cache.get_model()
                dim = embedding_cache.get_embedding_dimension()
                elapsed = time.time() - t0
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Loaded OK  |  dim={dim}  |  {elapsed:.1f}s"
                ))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ✗ Load failed: {exc}"))
                self.stdout.write('  Try:  python manage.py cache_models --force')
            self.stdout.write('')
            self._print_usage_tip()
            return

        if options['force']:
            self.stdout.write(self.style.WARNING('  --force: re-downloading model…'))
            embedding_cache.clear_memory()

        self.stdout.write(
            '  Downloading model (requires internet connection)…'
        )
        self.stdout.write(
            '  This runs only once; subsequent starts load from disk.\n'
        )

        try:
            t0 = time.time()

            # Monkey-patch tqdm so we can echo progress to the console
            self._patch_tqdm()
            embedding_cache.get_model(force_reload=options['force'])
            self._unpatch_tqdm()

            dim     = embedding_cache.get_embedding_dimension()
            elapsed = time.time() - t0
            size_mb = embedding_cache.check_cache_status()['cache_size_mb']

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('  ✓ Download complete'))
            self.stdout.write(f"    Size    : {size_mb} MB")
            self.stdout.write(f"    Dim     : {dim}")
            self.stdout.write(f"    Time    : {elapsed:.1f}s")
            self.stdout.write(f"    Saved to: {settings.MODELS_CACHE_DIR}")

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"\n  ✗ Download failed: {exc}"))
            self.stdout.write('')
            self.stdout.write('  Troubleshooting:')
            self.stdout.write('    • Check internet connection')
            self.stdout.write('    • Ensure sentence-transformers is installed')
            self.stdout.write('    • Try: pip install sentence-transformers')
            sys.exit(1)

        self.stdout.write('')
        self._print_usage_tip()

    # ------------------------------------------------------------------
    def _print_usage_tip(self):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('  Both apps share this cached model:')
        self.stdout.write('    • Knowledge Hub → document embedding')
        self.stdout.write('    • Coding IDE    → code chunk embedding')
        self.stdout.write('')
        self.stdout.write('  Next steps:')
        self.stdout.write('    1. ollama serve')
        self.stdout.write(f"    2. ollama pull {settings.OLLAMA_MODEL}")
        self.stdout.write(f"    3. ollama pull {settings.CODING_OLLAMA_MODEL}")
        self.stdout.write('    4. python manage.py runserver')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

    # ------------------------------------------------------------------
    # Very simple tqdm echo — avoids dependency on tqdm internals
    # ------------------------------------------------------------------
    def _patch_tqdm(self):
        try:
            import tqdm as _tqdm_mod

            stdout = self.stdout

            class _EchoBar(_tqdm_mod.tqdm):
                def update(self, n=1):
                    super().update(n)
                    pct = int(100 * self.n / self.total) if self.total else 0
                    desc = self.desc or ''
                    stdout.write(
                        f"\r    {desc} {pct:3d}%",
                        ending=''
                    )
                    stdout.flush()

            self._orig_tqdm = _tqdm_mod.tqdm
            _tqdm_mod.tqdm = _EchoBar
        except Exception:
            pass

    def _unpatch_tqdm(self):
        try:
            import tqdm as _tqdm_mod
            _tqdm_mod.tqdm = self._orig_tqdm
            self.stdout.write('')   # newline after progress bar
        except Exception:
            pass
