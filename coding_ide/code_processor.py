"""
Code-Aware Document Processor for the Coding IDE.
Handles extraction and chunking of source code files.
"""
import logging
import re

logger = logging.getLogger(__name__)


class CodeProcessor:
    """
    Extracts and chunks source code for RAG indexing.
    Splits code at logical boundaries (functions, classes, blocks).
    """

    # Patterns that mark the start of a logical unit (used for smart splitting)
    _BLOCK_PATTERNS = [
        re.compile(r'^(def |class |async def )', re.MULTILINE),          # Python
        re.compile(r'^(function |const |let |var |class |export )', re.MULTILINE),  # JS/TS
        re.compile(r'^(public |private |protected |static |void |int |class )', re.MULTILINE),  # Java/C#/C++
        re.compile(r'^(func )', re.MULTILINE),                           # Go/Swift
        re.compile(r'^(fn |pub fn |impl )', re.MULTILINE),               # Rust
    ]

    def extract_text(self, file_path: str) -> str:
        """Read source code from file with encoding fallback."""
        for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Read {len(content)} chars from {file_path} ({encoding})")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                raise
        raise ValueError(f"Cannot decode file: {file_path}")

    def get_preview(self, content: str, max_chars: int = 600) -> str:
        """Return a preview of the content."""
        return content[:max_chars].strip()

    def chunk_code(self, content: str, chunk_size: int = 400, overlap: int = 80) -> list[dict]:
        """
        Split source code into overlapping chunks while preserving logical boundaries.

        Returns a list of dicts: {'content': str, 'start_line': int, 'chunk_type': str}
        """
        if not content:
            return []

        lines = content.splitlines(keepends=True)
        chunks = []

        # Try to split at logical block boundaries first
        split_positions = self._find_block_starts(content)

        if len(split_positions) >= 2:
            chunks = self._chunk_by_blocks(lines, split_positions, chunk_size, overlap)
        else:
            # Fall back to sliding window over lines
            chunks = self._chunk_sliding_window(lines, chunk_size, overlap)

        logger.info(f"Created {len(chunks)} code chunks (chunk_size={chunk_size})")
        return chunks

    def _find_block_starts(self, content: str) -> list[int]:
        """Return character offsets where logical code blocks start."""
        positions = set()
        for pattern in self._BLOCK_PATTERNS:
            for m in pattern.finditer(content):
                positions.add(m.start())
        return sorted(positions)

    def _chunk_by_blocks(self, lines: list[str], split_positions: list[int], chunk_size: int, overlap: int) -> list[dict]:
        """Chunk code by grouping logical blocks that fit within chunk_size."""
        # Build (line_index, char_offset) map
        offsets = []
        pos = 0
        for line in lines:
            offsets.append(pos)
            pos += len(line)

        def line_of(char_pos):
            lo, hi = 0, len(offsets) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if offsets[mid] <= char_pos:
                    lo = mid
                else:
                    hi = mid - 1
            return lo

        block_line_starts = [line_of(p) for p in split_positions]
        block_line_starts = sorted(set(block_line_starts))

        chunks = []
        current_lines = []
        current_start = 0

        for i, start_line in enumerate(block_line_starts):
            end_line = block_line_starts[i + 1] if i + 1 < len(block_line_starts) else len(lines)
            block_text = ''.join(lines[start_line:end_line])

            if sum(len(l) for l in current_lines) + len(block_text) > chunk_size and current_lines:
                chunk_text = ''.join(current_lines)
                chunks.append({
                    'content': chunk_text.strip(),
                    'start_line': current_start,
                    'chunk_type': self._classify(chunk_text),
                })
                # Overlap: carry last `overlap` chars worth of lines
                carry = []
                carry_size = 0
                for line in reversed(current_lines):
                    if carry_size + len(line) > overlap:
                        break
                    carry.insert(0, line)
                    carry_size += len(line)
                current_lines = carry
                current_start = start_line - len(carry)

            if not current_lines:
                current_start = start_line
            current_lines.extend(lines[start_line:end_line])

        if current_lines:
            chunk_text = ''.join(current_lines)
            chunks.append({
                'content': chunk_text.strip(),
                'start_line': current_start,
                'chunk_type': self._classify(chunk_text),
            })

        return [c for c in chunks if c['content']]

    def _chunk_sliding_window(self, lines: list[str], chunk_size: int, overlap: int) -> list[dict]:
        """Fallback: fixed-size sliding window over lines."""
        chunks = []
        i = 0
        while i < len(lines):
            chunk_lines = []
            size = 0
            j = i
            while j < len(lines) and size + len(lines[j]) <= chunk_size:
                chunk_lines.append(lines[j])
                size += len(lines[j])
                j += 1
            if not chunk_lines:
                chunk_lines = [lines[i]]
                j = i + 1

            text = ''.join(chunk_lines).strip()
            if text:
                chunks.append({
                    'content': text,
                    'start_line': i,
                    'chunk_type': self._classify(text),
                })

            # Advance with overlap
            overlap_lines = 0
            overlap_size = 0
            for line in reversed(chunk_lines):
                if overlap_size + len(line) > overlap:
                    break
                overlap_lines += 1
                overlap_size += len(line)

            advance = max(1, len(chunk_lines) - overlap_lines)
            i += advance

        return chunks

    def _classify(self, text: str) -> str:
        """Classify chunk as code, comment, or mixed."""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return 'code'
        comment_lines = sum(
            1 for l in lines
            if l.startswith('#') or l.startswith('//') or l.startswith('*') or l.startswith('/*')
            or l.startswith('"""') or l.startswith("'''")
        )
        ratio = comment_lines / len(lines)
        if ratio > 0.8:
            return 'comment'
        if ratio > 0.3:
            return 'mixed'
        return 'code'
