from termcolor import colored

def _safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))

def error(message: str, show_emoji: bool = True) -> None:
    emoji = "❌" if show_emoji else ""
    _safe_print(colored(f"{emoji} {message}", "red"))

def success(message: str, show_emoji: bool = True) -> None:
    emoji = "✅" if show_emoji else ""
    _safe_print(colored(f"{emoji} {message}", "green"))

def info(message: str, show_emoji: bool = True) -> None:
    emoji = "ℹ️" if show_emoji else ""
    _safe_print(colored(f"{emoji} {message}", "magenta"))

def warning(message: str, show_emoji: bool = True) -> None:
    emoji = "⚠️" if show_emoji else ""
    _safe_print(colored(f"{emoji} {message}", "yellow"))

def question(message: str, show_emoji: bool = True) -> str:
    emoji = "❓" if show_emoji else ""
    try:
        return input(colored(f"{emoji} {message}", "magenta"))
    except UnicodeEncodeError:
        return input(colored(f"{message}", "magenta"))
