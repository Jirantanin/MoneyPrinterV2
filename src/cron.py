import sys

from status import *
from cache import get_accounts
from config import get_verbose, ROOT_DIR
from llm_provider import select_model

def main():
    """Main function to run scheduled Shorts automation.

    This function determines its operation based on command-line arguments:
    - If the purpose is "youtube", it initializes a YouTube account, generates a
      video with TTS, and uploads it.
    - If the purpose is "discover", it runs topic discovery for a YouTube account.

    Command-line arguments:
        sys.argv[1]: A string indicating the purpose, either "youtube" or "discover".
        sys.argv[2]: A string representing the account UUID.
    """
    purpose = str(sys.argv[1])
    account_id = str(sys.argv[2])
    model = str(sys.argv[3]) if len(sys.argv) > 3 else None

    if model:
        select_model(model)
    else:
        error("No Ollama model specified. Pass model name as third argument.")
        sys.exit(1)

    verbose = get_verbose()

    if purpose == "youtube":
        from classes.Tts import TTS
        from classes.YouTube import YouTube
        tts = TTS()

        accounts = get_accounts("youtube")

        if not account_id:
            error("Account UUID cannot be empty.")

        for acc in accounts:
            if acc["id"] == account_id:
                if verbose:
                    info("Initializing YouTube...")
                from datetime import datetime
                import os as _os
                _run_dir = _os.path.join(ROOT_DIR, ".mp", datetime.now().strftime("%Y%m%d_%H%M%S"))
                _os.makedirs(_run_dir, exist_ok=True)
                youtube = YouTube(
                    acc["id"],
                    acc["nickname"],
                    acc["niche"],
                    acc["language"],
                    run_dir=_run_dir,
                )
                youtube.generate_video(tts)
                # youtube.upload_video()
                if verbose:
                    success("create success Short.")
                break
    elif purpose == "discover":
        accounts = get_accounts("youtube")

        if not account_id:
            error("Account UUID cannot be empty.")
            sys.exit(1)

        for acc in accounts:
            if acc["id"] == account_id:
                if verbose:
                    info("Running topic discovery...")
                from topic_discovery import run_discovery
                result = run_discovery(acc.get("language", "English"))
                if result and verbose:
                    success(f"Discovered topic: {result['winner']['topic']}")
                break
    else:
        error("Invalid purpose. Expected 'youtube' or 'discover'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
