import schedule
import subprocess
import sys

from art import *
from cache import *
from utils import *
from config import *
from status import *
from uuid import uuid4
from constants import *
from classes.Tts import TTS
from termcolor import colored
from classes.YouTube import YouTube
from prettytable import PrettyTable
from llm_provider import list_models, select_model, get_active_model

LEGACY_CLI_NOTICE = (
    "Legacy CLI launcher: the Studio Web UI is the primary runtime now. "
    "Only Studio and YouTube Shorts paths are kept here. Use option 1 to open Studio."
)


def main():
    """Legacy menu launcher for non-Studio workflows.

    The Studio Web UI is the primary runtime path for this repository.
    This CLI remains available for older manual workflows and debugging.
    """

    # Get user input
    # user_input = int(question("Select an option: "))
    valid_input = False
    while not valid_input:
        try:
    # Show user options
            info("\n============ OPTIONS ============", False)

            for idx, option in enumerate(OPTIONS):
                print(colored(f" {idx + 1}. {option}", "cyan"))

            info("=================================\n", False)
            user_input = input("Select an option: ").strip()
            if user_input == '':
                print("\n" * 100)
                raise ValueError("Empty input is not allowed.")
            user_input = int(user_input)
            valid_input = True
        except ValueError as e:
            print("\n" * 100)
            print(f"Invalid input: {e}")


    # Start the selected option
    if user_input == 1:
        info("Opening Studio (primary runtime)...")
        from podcast_server import launch_podcast_server
        launch_podcast_server()
    elif user_input == 2:
        info("Starting YT Shorts Automater...")

        cached_accounts = get_accounts("youtube")

        if len(cached_accounts) == 0:
            warning("No accounts found in cache. Create one now?")
            user_input = question("Yes/No: ")

            if user_input.lower() == "yes":
                generated_uuid = str(uuid4())

                success(f" => Generated ID: {generated_uuid}")
                nickname = question(" => Enter a nickname for this account: ")
                fp_profile = question(" => Enter the path to the Firefox profile: ")
                niche = question(" => Enter the account niche: ")
                language = question(" => Enter the account language: ")

                account_data = {
                    "id": generated_uuid,
                    "nickname": nickname,
                    "firefox_profile": fp_profile,
                    "niche": niche,
                    "language": language,
                    "videos": [],
                }

                add_account("youtube", account_data)

                success("Account configured successfully!")
        else:
            table = PrettyTable()
            table.field_names = ["ID", "UUID", "Nickname", "Niche"]

            for account in cached_accounts:
                table.add_row([cached_accounts.index(account) + 1, colored(account["id"], "cyan"), colored(account["nickname"], "blue"), colored(account["niche"], "green")])

            print(table)
            info("Type 'd' to delete an account.", False)

            user_input = question("Select an account to start (or 'd' to delete): ").strip()

            if user_input.lower() == "d":
                delete_input = question("Enter account number to delete: ").strip()
                account_to_delete = None

                for account in cached_accounts:
                    if str(cached_accounts.index(account) + 1) == delete_input:
                        account_to_delete = account
                        break

                if account_to_delete is None:
                    error("Invalid account selected. Please try again.", "red")
                else:
                    confirm = question(f"Are you sure you want to delete '{account_to_delete['nickname']}'? (Yes/No): ").strip().lower()

                    if confirm == "yes":
                        remove_account("youtube", account_to_delete["id"])
                        success("Account removed successfully!")
                    else:
                        warning("Account deletion canceled.", False)

                return

            selected_account = None

            for account in cached_accounts:
                if str(cached_accounts.index(account) + 1) == user_input:
                    selected_account = account

            if selected_account is None:
                error("Invalid account selected. Please try again.", "red")
                main()
            else:
                from datetime import datetime
                _run_dir = os.path.join(ROOT_DIR, ".mp", datetime.now().strftime("%Y%m%d_%H%M%S"))
                os.makedirs(_run_dir, exist_ok=True)
                youtube = YouTube(
                    selected_account["id"],
                    selected_account["nickname"],
                    selected_account["niche"],
                    selected_account["language"],
                    run_dir=_run_dir,
                )

                while True:
                    rem_temp_files()
                    info("\n============ OPTIONS ============", False)

                    for idx, youtube_option in enumerate(YOUTUBE_OPTIONS):
                        print(colored(f" {idx + 1}. {youtube_option}", "cyan"))

                    info("=================================\n", False)

                    # Get user input
                    user_input = int(question("Select an option: "))
                    tts = TTS()

                    if user_input == 1:
                        youtube.generate_video(tts)
                        upload_to_yt = question("Do you want to upload this video to YouTube? (Yes/No): ")
                        if upload_to_yt.lower() == "yes":
                            youtube.upload_video()
                    elif user_input == 2:
                        videos = youtube.get_videos()

                        if len(videos) > 0:
                            videos_table = PrettyTable()
                            videos_table.field_names = ["ID", "Date", "Title"]

                            for video in videos:
                                videos_table.add_row([
                                    videos.index(video) + 1,
                                    colored(video["date"], "blue"),
                                    colored(video["title"][:60] + "...", "green")
                                ])

                            print(videos_table)
                        else:
                            warning(" No videos found.")
                    elif user_input == 3:
                        # Setup Upload CRON
                        info("How often do you want to upload?")

                        info("\n============ OPTIONS ============", False)
                        for idx, cron_option in enumerate(YOUTUBE_UPLOAD_CRON_OPTIONS):
                            print(colored(f" {idx + 1}. {cron_option}", "cyan"))
                        info("=================================\n", False)

                        user_input = int(question("Select an Option: "))

                        cron_script_path = os.path.join(ROOT_DIR, "src", "cron.py")
                        upload_cmd = ["python", cron_script_path, "youtube", selected_account['id'], get_active_model()]

                        def upload_job():
                            subprocess.run(upload_cmd)

                        if user_input == 1:
                            schedule.every(1).day.do(upload_job)
                            success("Set up Upload CRON (once a day).")
                        elif user_input == 2:
                            schedule.every().day.at("10:00").do(upload_job)
                            schedule.every().day.at("16:00").do(upload_job)
                            success("Set up Upload CRON (twice a day).")
                        else:
                            break

                    elif user_input == 4:
                        # Setup Discovery CRON
                        info("What time should discovery run daily?")

                        info("\n============ OPTIONS ============", False)
                        for idx, cron_option in enumerate(YOUTUBE_DISCOVERY_CRON_OPTIONS):
                            print(colored(f" {idx + 1}. {cron_option}", "cyan"))
                        info("=================================\n", False)

                        user_input = int(question("Select an Option: "))

                        cron_script_path = os.path.join(ROOT_DIR, "src", "cron.py")
                        discover_cmd = ["python", cron_script_path, "discover", selected_account['id'], get_active_model()]

                        def discover_job():
                            subprocess.run(discover_cmd)

                        time_map = {1: "06:00", 2: "07:00", 3: "08:00"}
                        if user_input in time_map:
                            run_time = time_map[user_input]
                        elif user_input == 4:
                            run_time = question("Enter time (HH:MM): ").strip()
                        else:
                            break

                        schedule.every().day.at(run_time).do(discover_job)
                        success(f"Set up Discovery CRON (daily at {run_time}).")

                    elif user_input == 5:
                        # Discover Trending Topics (run now)
                        from topic_discovery import run_discovery
                        info("Running topic discovery...")
                        result = run_discovery(selected_account.get("language", "English"))
                        if result and "winner" in result:
                            success(f"Best topic: {result['winner']['topic']}")
                            info(f"Angle: {result['winner']['angle']}")
                            info(f"Reasoning: {result.get('reasoning', '')}")
                            for r in result.get("runners_up", []):
                                info(f"  Runner-up: {r['topic']} (score: {r['score']})")
                        else:
                            warning("Topic discovery failed or returned no results.")
                    elif user_input == 6:
                        if get_verbose():
                            info(" => Climbing Options Ladder...", False)
                        break
    elif user_input == 3:
        if get_verbose():
            print(colored(" => Quitting...", "blue"))
        sys.exit(0)
    else:
        error("Invalid option selected. Please try again.", "red")
        main()
    

if __name__ == "__main__":
    # Print ASCII Banner
    print_banner()
    warning(LEGACY_CLI_NOTICE, False)

    first_time = get_first_time_running()

    if first_time:
        print(colored("Hey! It looks like you're running MoneyPrinter V2 for the first time. Let's get you setup first!", "yellow"))
        print(colored("Tip: the Studio Web UI is the main way to use this repo now.", "yellow"))

    # Setup file tree
    assert_folder_structure()

    # Remove temporary files
    rem_temp_files()

    # Fetch MP3 Files
    fetch_songs()

    # Select Ollama model — use config value if set, otherwise pick interactively
    configured_model = get_ollama_model()
    if configured_model:
        select_model(configured_model)
        success(f"Using configured model: {configured_model}")
    else:
        try:
            models = list_models()
        except Exception as e:
            error(f"Could not connect to Ollama: {e}")
            sys.exit(1)

        if not models:
            error("No models found on Ollama. Pull a model first (e.g. 'ollama pull llama3.2:3b').")
            sys.exit(1)

        info("\n========== OLLAMA MODELS =========", False)
        for idx, model_name in enumerate(models):
            print(colored(f" {idx + 1}. {model_name}", "cyan"))
        info("==================================\n", False)

        model_choice = None
        while model_choice is None:
            raw = input(colored("Select a model: ", "magenta")).strip()
            try:
                choice_idx = int(raw) - 1
                if 0 <= choice_idx < len(models):
                    model_choice = models[choice_idx]
                else:
                    warning("Invalid selection. Try again.")
            except ValueError:
                warning("Please enter a number.")

        select_model(model_choice)
        success(f"Using model: {model_choice}")

    while True:
        main()
