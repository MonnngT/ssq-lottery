"""Vocabulary data builder — generates JSON word list files from compact format.

Run once: python -m vocab.builder
"""

from vocab.build_from_compact import main as build_from_compact

if __name__ == "__main__":
    build_from_compact()
