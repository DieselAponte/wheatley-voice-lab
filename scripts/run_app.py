"""Convenience entry point for launching the Wheatley Voice Lab Gradio dashboard."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.voice_lab.presentation.gradio_app import launch


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wheatley Voice Lab — Aperture Science Interactive Audio Dashboard"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Server bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Server port (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Generate public shareable URL")
    parser.add_argument("--debug", action="store_true", help="Run with detailed Gradio debug traces")
    args = parser.parse_args()

    print("=" * 65)
    print("  WHEATLEY VOICE LAB — APERTURE SCIENCE EXPERIMENTAL AUDIO DIVISION")
    print("=" * 65)
    print(f"Iniciando interfaz web local en: http://{args.host}:{args.port}")
    print(f"Modo debug: {'ACTIVADO' if args.debug else 'DESACTIVADO'}")
    print(f"Enlace público (share): {'ACTIVADO' if args.share else 'DESACTIVADO'}")
    print("=" * 65)

    launch(host=args.host, port=args.port, share=args.share, debug=args.debug)


if __name__ == "__main__":
    main()
