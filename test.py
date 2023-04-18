import requests
from bs4 import BeautifulSoup
import re
import random, threading, queue, ctypes, time, sys
from email_validator import validate_email
from termcolor import colored
from colorama import init, Fore, Style

urls_attempted = 0
errors = 0

NUM_THREADS = 0
DEBUG = False

# Initialize colorama to enable colored output on Windows
init()

if len(sys.argv) != 3:
    print("Usage: python script_name.py [basic|advanced] [num_threads]")
    sys.exit(1)

try:
    NUM_THREADS = int(sys.argv[2])
    if NUM_THREADS <= 0 or NUM_THREADS > 150:
        print("Error: num_threads should be between 1 and 150")
        sys.exit(1)
except ValueError:
    print("Error: num_threads should be an integer")
    sys.exit(1)

if sys.argv[1] == "basic":
    contact_us_pages = [
        "/contact_us.html",
        "/contact",
        "/help-centre.list",
        "/contact-us",
        "/about-us/contact",
        "/support/contact",
        "/contact-us-2",
        "/contact-page",
        "/get-in-touch",
        "/contact-us/",
        "/",
    ]
elif sys.argv[1] == "advanced":
    contact_us_pages = [
        "/contact_us.html",
        "/contact",
        "/help-centre.list",
        "/contact-us",
        "/about-us/contact",
        "/support/contact",
        "/contact-us-2",
        "/contact-page",
        "/get-in-touch",
        "/contact-us/",
        "/about-us/",
        "/contact-us/contact-us/",
        "/contact-us/contact/",
        "/contact-us/support/",
        "/contact-us/get-in-touch/",
        "/about-us/contact-us/",
        "/about-us/contact/",
        "/about-us/support/",
        "/about-us/get-in-touch/",
        "/support/contact-us/",
        "/support/contact/",
        "/support/about-us/",
        "/support/get-in-touch/",
        "/get-in-touch/contact-us/",
        "/get-in-touch/contact/",
        "/get-in-touch/about-us/",
        "/get-in-touch/support/",
        "/contactus.html",
        "/contactus",
        "/contact_us",
        "/contactus.php",
        "/contactus.html",
        "/contactus.aspx",
        "/contactus.htm",
        "/aboutus.html",
        "/aboutus",
        "/about_us",
        "/aboutus.php",
        "/aboutus.html",
        "/aboutus.aspx",
        "/aboutus.htm",
        "/help.html",
        "/help",
        "/help.php",
        "/help.html",
        "/help.aspx",
        "/help.htm",
    ]
else:
    print(f"Error: unrecognized argument '{sys.argv[1]}'")
    sys.exit(1)


class Scraper:
    def __init__(self, urls, user_agents):
        self.urls = list(set(urls))  # Remove duplicates from the urls list
        self.user_agents = user_agents
        self.url_queue = queue.Queue()
        self.all_emails = set()
        self.lock = threading.Lock()
        self.setup_queue()

    def setup_queue(self):
        for url in self.urls:
            for path in contact_us_pages:
                full_url = url + path
                self.url_queue.put(full_url)

    def is_valid_email(self, email):
        try:
            v = validate_email(email)
            return True if v and v["domain"] else False
        except Exception:
            return False

    def scrape_emails(self, url):
        try:
            headers = {"User-Agent": random.choice(self.user_agents)}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            global errors
            errors += 1
            if DEBUG:
                print(colored(f"Error requesting {url}: {e}", "red"))
            return set()

        soup = BeautifulSoup(response.content, "html.parser")
        body = soup.find("body")
        if not body:
            if DEBUG:
                print(colored(f"No body found in {url}", "red"))
            return set()

        emails = set()
        for tag in body.find_all():
            if tag.name != "img":
                text = tag.get_text(strip=True)
                if text:
                    matches = re.findall(
                        r"(?<=[\s\W])[\w\.-]+@(?:[\w-]+\.)+[a-zA-Z]{2,}(?!.*\S)", text
                    )
                    for email in matches:
                        if self.is_valid_email(email):
                            emails.add(email)
        return emails

    def worker(self):
        global urls_attempted  # use the global keyword to access the global variable
        while True:
            url = self.url_queue.get()
            urls_attempted += 1  # increment the global count
            emails = self.scrape_emails(url)
            with self.lock:
                self.all_emails.update(emails)
            if emails:
                print(colored(f"{url}: {len(emails)} emails found", "green"))
            else:
                if DEBUG:
                    print(f"{url}: no emails found")
                else:
                    pass
            set_cmd_title(
                f"Hades Scraper :: Urls Attempted: {urls_attempted} :: Urls in Queue: {self.url_queue.qsize()} :: Emails Found: {len(self.all_emails)} :: Errors: {errors}"
            )
            self.url_queue.task_done()

    def start(self):
        for i in range(NUM_THREADS):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()

        while not self.url_queue.empty():
            time.sleep(1)

        # Remove duplicates from the all_emails set
        self.all_emails = set(email for email in self.all_emails if self.is_valid_email(email))

        with open("found.txt", "w") as f:
            for email in sorted(self.all_emails):
                f.write(email + "\n")

        print(
            Fore.GREEN + f"Total emails found: {len(self.all_emails)}" + Style.RESET_ALL
        )


def set_cmd_title(title):
    ctypes.windll.kernel32.SetConsoleTitleW(title)


def main():
    with open("urls.txt") as f:
        urls = [line.strip() for line in f]

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 Edg/81.0.416.77",
    ]

    scraper = Scraper(list(set(urls)), user_agents)
    set_cmd_title(
        f"Hades Scraper :: Urls: {len(urls)} :: Emails Found: {len(scraper.all_emails)}"
    )

    try:
        scraper.start()
    except KeyboardInterrupt:
        print(colored("Interrupted by user. Saving results...", "yellow"))

    deduplicated_emails = list(set(scraper.all_emails))
    with open("found.txt", "w") as f:
        for email in sorted(deduplicated_emails):
            f.write(email + "\n")

    print(colored(f"Total emails found: {len(deduplicated_emails)}", "green"))


if __name__ == "__main__":
    main()
