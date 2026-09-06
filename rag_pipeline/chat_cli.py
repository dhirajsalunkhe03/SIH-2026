#!/usr/bin/env python3
"""
CLI chat interface for Legal RAG system.
"""

import sys
import time
from typing import Optional
from rag_engine import LegalRAG, create_rag_engine, RAGAnswer
from config import get_config


class LegalRAGCLI:
    """Interactive CLI for Legal RAG."""
    
    LANGUAGE_OPTIONS = [
        ('auto', 'Auto-detect', 'Auto'),
        ('en', 'English', 'English'),
        ('hi', 'Hindi', 'हिंदी'),
        ('mr', 'Marathi', 'मराठी'),
        ('gu', 'Gujarati', 'ગુજરાતી'),
        ('bn', 'Bengali', 'বাংলা'),
        ('ta', 'Tamil', 'தமிழ்'),
        ('te', 'Telugu', 'తెలుగు'),
        ('kn', 'Kannada', 'ಕನ್ನಡ'),
        ('ml', 'Malayalam', 'മലയാളം'),
        ('pa', 'Punjabi', 'ਪੰਜਾਬੀ'),
    ]
    
    def __init__(self, engine: LegalRAG = None):
        self.engine = engine or create_rag_engine()
        self.config = get_config()
        self.current_language = 'auto'
        self.show_debug = False
    
    def print_banner(self):
        """Print welcome banner."""
        print("\n" + "=" * 60)
        print("  SIH 2026 — Legal Knowledge Assistant")
        print("  Traditional Knowledge, Biodiversity, ABS & IP")
        print("=" * 60)
        print()
        print("Select answer language:")
        for i, (code, en_name, native_name) in enumerate(self.LANGUAGE_OPTIONS, 1):
            marker = " ← current" if code == self.current_language else ""
            print(f"  {i:2d}. {en_name} ({native_name}){marker}")
        print()
        print("Commands:")
        print("  /lang <num>  - Change answer language")
        print("  /debug       - Toggle debug mode")
        print("  /help        - Show this help")
        print("  /quit        - Exit")
        print()
    
    def set_language(self, idx: int) -> bool:
        """Set answer language by menu index."""
        if 1 <= idx <= len(self.LANGUAGE_OPTIONS):
            self.current_language = self.LANGUAGE_OPTIONS[idx - 1][0]
            print(f"Language set to: {self.LANGUAGE_OPTIONS[idx - 1][1]} ({self.LANGUAGE_OPTIONS[idx - 1][2]})")
            return True
        return False
    
    def handle_command(self, cmd: str) -> bool:
        """Handle CLI commands. Returns True if command was handled."""
        cmd = cmd.strip().lower()
        
        if cmd in ('/quit', '/exit', '/q'):
            print("Goodbye!")
            return False  # Signal to exit
        
        elif cmd == '/help':
            self.print_banner()
            return True
        
        elif cmd == '/debug':
            self.show_debug = not self.show_debug
            print(f"Debug mode: {'ON' if self.show_debug else 'OFF'}")
            return True
        
        elif cmd.startswith('/lang '):
            try:
                idx = int(cmd.split()[1])
                self.set_language(idx)
            except (IndexError, ValueError):
                print("Usage: /lang <number>")
            return True
        
        return False
    
    def format_answer(self, result: RAGAnswer) -> str:
        """Format answer for display."""
        lines = []
        
        # Language info
        detected = result.detected_language.get('name', 'Unknown')
        detected_code = result.detected_language.get('code', 'unknown')
        answer_lang_name = next(
            (opt[1] for opt in self.LANGUAGE_OPTIONS if opt[0] == result.answer_language),
            result.answer_language
        )
        
        lines.append(f"\n{'─' * 60}")
        lines.append(f"Detected Query Language: {detected} ({detected_code})")
        lines.append(f"Answer Language: {answer_lang_name}")
        lines.append(f"Confidence: {result.confidence} ({result.confidence_reason})")
        lines.append(f"Retrieval Confidence: {result.retrieval_confidence}")
        lines.append(f"Latency: {result.retrieval_time_ms}ms retrieval + {result.generation_time_ms}ms generation = {result.total_time_ms}ms total")
        
        if result.error:
            lines.append(f"Error: {result.error}")
        
        lines.append(f"{'─' * 60}")
        lines.append(f"\n{result.answer}")
        
        if self.show_debug:
            lines.append(f"\n{'─' * 60}")
            lines.append("DEBUG INFO:")
            lines.append(f"  Retrieved chunks: {len(result.retrieved_chunks)}")
            lines.append(f"  Sources: {len(result.sources)}")
            for i, chunk in enumerate(result.retrieved_chunks[:3]):
                lines.append(f"  Chunk {i+1}: {chunk.get('chunk_id', '?')} score={chunk.get('score', 0):.4f}")
        
        return "\n".join(lines)
    
    def run(self):
        """Run the interactive CLI loop."""
        self.print_banner()
        
        while True:
            try:
                prompt = f"\n[{self.current_language}]> "
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    if not self.handle_command(user_input):
                        break  # Exit signal
                    continue
                
                # Process query
                print("Thinking...")
                start = time.time()
                
                try:
                    result = self.engine.answer(
                        query=user_input,
                        answer_language=self.current_language,
                        top_k=5
                    )
                    
                    elapsed = int((time.time() - start) * 1000)
                    result.total_time_ms = elapsed  # Update with actual total
                    
                    print(self.format_answer(result))
                    
                except Exception as e:
                    print(f"\nError: {e}")
                    if self.show_debug:
                        import traceback
                        traceback.print_exc()
            
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break


def main():
    """Main entry point."""
    print("Initializing Legal RAG Engine...")
    engine = create_rag_engine()
    
    cli = LegalRAGCLI(engine)
    cli.run()


if __name__ == '__main__':
    main()