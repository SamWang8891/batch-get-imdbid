import itertools
import os
import random
import re
import shutil
import signal
import sys
import threading
import time
from enum import IntEnum
from typing import Optional

import requests
from bs4 import BeautifulSoup
from simple_term_menu import TerminalMenu

from lang import language_codes

stop_spinner = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.105 Mobile Safari/537.36",
]

HEADERS = {
    "User-Agent": random.choice(USER_AGENTS),
}


class NumberType(IntEnum):
    QUIT = -1,
    CONTINUE = -2,


def signal_handler(sig, frame):
    global stop_spinner
    stop_spinner = True
    print("\033[H\033[J", end="")  # Clear the screen
    print("The program left you behind and continue watching Shikanoko while it's antlers are growing back...\n")
    sys.exit(0)


def spinner(delay=0.1):
    spinner_symbols = itertools.cycle(["|", "/", "-", "\\"])  # ["◐", "◓", "◑", "◒"]
    while not stop_spinner:
        sys.stdout.write(f"\rLoading... {next(spinner_symbols)}")
        sys.stdout.flush()
        time.sleep(delay)


def select_language():
    menu = TerminalMenu(language_codes, title="Select the preferred language", show_search_hint=True,
                        show_search_hint_text="(Press \"/\" to search) (Better select the ones with country code.)")
    menu_entry_index = menu.show()
    selected: str = re.sub(r'\s+', ', ', language_codes[menu_entry_index], count=1)
    print(f"You selected \"{selected}\"!")
    time.sleep(1)

    if language_codes[menu_entry_index] != 'default':
        preferred_result_disp_language = language_codes[menu_entry_index].split(' ')[0]
        HEADERS['Accept-Language'] = f"{preferred_result_disp_language},en-US;q=0.9"


def fetch_page(url: str) -> BeautifulSoup:
    global stop_spinner
    for _ in range(3):  # Retry logic
        stop_spinner = False
        spinner_thread = threading.Thread(target=spinner)  # Start spinner
        spinner_thread.start()

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            stop_spinner = True  # Stop spinning
            spinner_thread.join()
            sys.stdout.write("\rLoading... Done!\n")  # Clear the spinner and display "done"
            sys.stdout.flush()

            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')

            print(f"Retrying... Status Code: {response.status_code}")
        except Exception as e:
            stop_spinner = True  # Ensure the spinner has stopped
            spinner_thread.join()
            print(f"\rError: {e}")

    raise Exception(f"Failed to fetch {url} after 3 attempts")


def get_episode_tt(url: str) -> dict[int, str]:
    start: int = 1

    soup = fetch_page(url)
    articles = soup.select('article.sc-663ab24a-1.fzyEyw.episode-item-wrapper')
    links = [link.get('href', '') for article in articles for link in
             article.find_all('a', class_='ipc-title-link-wrapper')]

    links = filter(lambda href: re.search(r'(tt\d+)\D', href), links)
    tt_list = [re.search(r'(tt\d+)\D', href).group(1) for href in links]

    if soup.find('div', class_='ipc-title__text', string=lambda text: text and 'E0' in text):
        start = 0

    return {idx: tt_id for idx, tt_id in enumerate(tt_list, start=start)},


def find_season_amount(url: str) -> int:
    for _ in range(3):
        soup = fetch_page(url)
        tablist = soup.select('ul[role="tablist"]')
        if len(tablist) == 2:

            links_without_unknown = [a for a in tablist[1].find_all('a') if a.text.isdigit()] if tablist[1] else []
            links_all = [a for a in tablist[1].find_all('a')] if tablist[1] else []
            time.sleep(2)
            if links_all != links_without_unknown:
                print("Unknown season ignored...")
            return len(links_without_unknown)

    raise Exception(f"Failed to season amount in find_season_amount() after 3 attempts")


def extract_id(str_contain_id: str) -> str:
    """
    Extracts the IMDb ID from the URL
    If not in the root page, extract the root tt id from the root webpage.
    :param str_contain_id: The IMDb URL
    :return: the IMDb ID
    """
    tt_id = re.search(r'tt\d+', str_contain_id).group(0)

    # Verify if the URL is the root page by searching for "Episodes" in the h3
    soup = fetch_page("https://imdb.com/title/" + tt_id)
    h3_tags = soup.find_all('h3')

    for tag in h3_tags:
        if 'Episodes' in tag.text:
            return re.search(r'tt\d+', tt_id).group(0)
        else:  # Get the root tt id if not in root page
            root_page_dir = soup.find('a', {'aria-label': 'View all episodes'}).get('href', '')
            return re.search(r'tt\d+', root_page_dir).group(0)

    match = re.search(r'tt\d+', str_contain_id)
    return match.group(0) if match else ''


def search_imdb(url: str) -> dict[str, str]:
    soup = fetch_page(url)  # may cost lots of time
    links = soup.select('a.ipc-metadata-list-summary-item__t')
    return {link.text.strip(): link['href'] for link in links}


def user_search(search: str) -> Optional[str]:
    if search.startswith(('https://www.imdb.com/title/tt', 'https://imdb.com/title/tt')):
        if is_webpage_valid(search):
            return extract_id(search)
        else:
            print("Invalid IMDb URL. Please try again.")
            time.sleep(1)
            return None

    if search.startswith('https://'):
        print("Please enter a valid IMDb title URL.")
        time.sleep(1)
        return None

    if search.startswith('tt'):
        if is_webpage_valid('https://imdb.com/title/' + search):
            return search
        else:
            print("Invalid IMDb ID. Please try again.")
            time.sleep(1)
            return None

    results = search_imdb(f"https://imdb.com/find/?q={search}")
    print(results.items())
    if not results:
        print("No results. Try again.")
        time.sleep(1)
        return None

    while True:
        print("\033[H\033[J", end="")  # Clear the screen
        print("Searched for:", search)
        print("\nSearch Results:")  # TODO: implement the selection
        for idx, (key, value) in enumerate(results.items(), start=1):
            print(f"{idx}. {key} - https://imdb.com{value}")

        chosen = input("\nEnter the number of the title or 'a' to search again: ").strip()
        print("\n")
        if chosen.lower() == 'a':
            break

        if not (chosen.isdigit() and 1 <= int(chosen) <= len(results)):
            print("Invalid input. Try again.")
            time.sleep(1)
            continue

        try:
            return extract_id(list(results.values())[int(chosen) - 1])
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")
            time.sleep(1)


def is_webpage_valid(url: str) -> bool:
    global stop_spinner
    stop_spinner = False
    spinner_thread = threading.Thread(target=spinner)  # Start spinner
    spinner_thread.start()

    response = requests.get(url, headers=HEADERS)
    stop_spinner = True  # Stop spinning
    return response.status_code == 200


def create_dest_directory(root_id: str) -> str:
    dest_directory: str

    while True:
        dest_directory = clean_path(
            input("\nEnter or drag in the destination directory: ")
        )
        if not os.path.exists(dest_directory):
            print("\033[H\033[J", end="")  # Clear the screen
            print(f"You entered {dest_directory}")
            print("The path directory does not exist, do you want to create it?")
            inp_agree = input("Enter 'y' to create or 'n' to enter a new path: ").strip().lower() == 'y'

            if inp_agree:
                os.makedirs(dest_directory)
                break
        else:
            break

    # Separate the parent directory and the folder name
    folder_name = dest_directory.split(os.sep)[-1]
    parent_dir = dest_directory.replace(folder_name, '')

    new_dest: str

    # See if the folder name contains the IMDb ID
    if re.search(r'\[imdbid-tt\d+\]', folder_name):
        if not re.search(rf'\[imdbid-{root_id}\]',
                         folder_name):  # If the IMDb ID is different from the title's IMDb ID
            while True:
                print("\033[H\033[J", end="")  # Clear the screen
                print("The folder name does have an IMDb ID but it's not the same as the title's IMDb ID.")
                ans = input("\nDo you want to change (or create a new folder if the original folder has files in it) the folder name? (y/n): ").strip().lower()
                if ans == 'y':
                    folder_name: str = re.sub(r'\[imdbid-tt\d+\]', '', folder_name).strip()
                    new_dest = f"{parent_dir} {folder_name} [imdbid-{root_id}]"
                    os.rename(dest_directory, new_dest)
                    break
                elif ans == 'n':
                    print(
                        "Okay. But just to let you know, the IMDb ID is not the same as the title's IMDb ID. And it'll cause Jellyfin to recognize the wrong title.")
                    break
                else:
                    print("Invalid input.")
                    time.sleep(1)
    else:  # If the folder name does not contain any IMDb ID
        new_dest = f"{dest_directory} [imdbid-{root_id}]"
        os.rename(dest_directory, new_dest)

    for s in range(1, season_amount + 1):
        os.makedirs(os.path.join(dest_directory, f'Season {s}'), exist_ok=True)

    return dest_directory


def copy_and_rename_files(dest_directory: str, season_amount: int):
    while True:
        print("\033[H\033[J", end="")  # Clear the screen
        file_amount = input("Enter number of files per episode (default 1): ").strip() or "1"
        if file_amount.isdigit():
            file_amount = int(file_amount)
            break
        else:
            print("Invalid input.")
            time.sleep(1)


    start:int = 1 # Default start
    if season_amount > 1:
        while True:
            assign: int = ask_to_assign_number("season", season_amount)
            if assign == NumberType.QUIT:
                return

            if assign == NumberType.CONTINUE:
                break

            if assign > 0 and assign <= season_amount:
                start = assign
                break

            print("\nInvalid input.")
            print("assign:", assign)
            time.sleep(1)

    print()

    for i in range(start, season_amount + 1): # season loop

        id_dict: dict[int, str] = get_episode_tt(f"https://imdb.com/title/{root_id}/episodes?season={i}")

        is_reset: bool = False
        # TODO: Fixed the start in id_dict and now it goes wrong here
        for ep_index, ep_tt in id_dict.items(): # episode loop
            if is_reset:
                break

            for file_index in range(1, file_amount + 1): # file loop
                if is_reset:
                    break

                while True:
                    print("\033[H\033[J", end="")  # Clear the screen
                    print("Enter or drag in the directory of the file. \n('s' to skip, 'r' to reset naming process)")
                    print(
                        f"\nSeason {i}/{season_amount}, file {file_index}/{file_amount} for episode {ep_index}/{len(id_dict)}.")
                    file_path = clean_path(
                        input("Enter the file path: ").strip()
                    )

                    if file_path == "s":
                        break

                    if file_path == "r":
                        print("\033[H\033[J", end="")  # Clear the screen
                        print("Resetting naming process...")
                        time.sleep(1)
                        is_reset = True
                        break

                    if not os.path.exists(file_path):
                        print("\033[H\033[J", end="")  # Clear the screen
                        if file_path == '':
                            print("You entered nothing.")
                        else:
                            print(f"You entered {file_path}")
                        print("Invalid path. Try again.")
                        time.sleep(1)

                        continue

                    break

                file_ext = os.path.splitext(file_path)[1]
                new_file_path = os.path.join(
                    dest_directory,
                    f"Season {i}",
                    f"{str(ep_index).zfill(2)} [imdbid-{ep_tt}]{file_ext}"
                )
                shutil.copy(file_path, new_file_path)


def clean_path(path: str) -> str:
    no_esc = path.strip().replace('\\', '')
    if no_esc.startswith("'") and no_esc.endswith("'"):
        no_esc = no_esc[1:-1]
    return no_esc


def network_test():
    response_q8 = os.system("ping -c 1 8.8.8.8 > /dev/null 2>&1")
    response_imdb = os.system("ping -c 1 imdb.com > /dev/null 2>&1")

    if response_q8 == 0 and response_imdb == 0:
        return True
    elif response_q8 == 0 and response_imdb != 0:
        print("You seemed to have network connection but can't connect to IMDb.com.")
        raise Exception("No network connection.")


def ask_to_assign_number(info: str, total_amount:int) -> int:
    a = NumberType | int

    while True:
        print("\033[H\033[J", end="")  # Clear the screen
        print(f"There are {total_amount} {info}s.")
        print(f"Do you want to start from a particular {info}?")
        inp_number = input(
            f"\nEnter the {info} number to start with or press <Enter> to ignore, enter 'q' to quit the program: ").strip().lower()

        if inp_number == 'q':
            return NumberType.QUIT

        if not inp_number:
            return NumberType.CONTINUE

        if not inp_number.isdigit():
            print("Invalid input.")
            time.sleep(1)
            continue

        return int(inp_number)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    # TODO: Anime only warning

    select_language()

    while True:
        root_id: Optional[str] = None

        network_test()

        while True:
            print("\033[H\033[J", end="")  # Clear the screen
            print("Search for the title name or enter the IMDb title URL (e.g., https://www.imdb.com/title/tt...).\n")
            inp_search = input(
                "Search: "
            ).strip()
            print("\n")
            if not inp_search:
                continue

            if root_id := user_search(inp_search):
                break

        season_amount = find_season_amount(f"https://imdb.com/title/{root_id}/episodes/")

        print("\033[H\033[J", end="")  # Clear the screen

        if season_amount == 1:
            print(f"There is {season_amount} season.")
        else:
            print(f"There are {season_amount} seasons.")

        dest_directory = create_dest_directory(root_id)
        copy_and_rename_files(dest_directory, season_amount)

        print("\033[H\033[J", end="")  # Clear the screen
        inp_continue = input("Do you want to go on to the next title? (y/n): ").strip().lower()
        if inp_continue != 'y':
            break

    print("\033[H\033[J", end="")  # Clear the screen
    print("The program left you behind and continue watching Shikanoko while it's antlers are growing back...\n")