from hashlib import md5
from time import sleep

import boto3
import requests
from bs4 import BeautifulSoup

r = requests.Session()
seen_messages = []
ssm = boto3.client("secretsmanager")


def get_webhook_url():
    global ssm

    return ssm.get_secret_value(
        SecretId="HazeronDiscordBot/WebhookURL"
    )['SecretString']


webhook_url = get_webhook_url()


class ChatMessage:
    def __init__(self, galaxy: str, player: str, message: str, time):
        self.galaxy = galaxy
        self.player = player
        self.message = message.replace(" @", " @\u200b")

        if self.message.startswith("@"):
            self.message = f"@\u200b{self.message[1:]}"

        self.time = time

    def __repr__(self) -> str:
        return f"[{self.galaxy}] {self.player}: {self.message}"

    @property
    def hash(self) -> str:
        return md5(f"[{self.time}] {str(self)}".encode("utf-8")).hexdigest()


def fetch_galactic_chat() -> str:
    returned_html = r.get("http://hazeron.com/galactic.html")

    return returned_html.content.decode("utf-8")


def parse_galactic_chat(input_html: str) -> [ChatMessage]:
    message_lines = [x for x in input_html.split("\n") if "font" in x]

    messages = []

    for line in message_lines:
        message_soup = BeautifulSoup(line, "html.parser")
        segments = message_soup.find_all(["div", "font"])

        time = next(segments[0].contents[0].strings).rstrip()
        galaxy = segments[1].string.lstrip()
        player = segments[2].string
        message = segments[3].string

        messages.append(ChatMessage(galaxy, player, message, time))

    return messages


def clean_seen_messages(current_messages: [ChatMessage]) -> None:
    global seen_messages

    current_message_hashes = [message.hash for message in current_messages]

    seen_messages = [x for x in seen_messages if x in current_message_hashes]


def is_message_seen(message: ChatMessage):
    return message.hash in seen_messages


while True:
    galactic_chat_html = fetch_galactic_chat()
    messages = parse_galactic_chat(galactic_chat_html)
    unsent_messages = [message for message in messages if not is_message_seen(message)]

    for unsent_message in unsent_messages:
        print(unsent_message)
        r_p = r.post(webhook_url, data={"username": f"[G] {unsent_message.player}", "content": unsent_message.message})

        while r_p.status_code == 429:
            rate_limit_data = r_p.json()
            sleep(rate_limit_data["retry_after"] / 1000)

            r_p = r.post(
                webhook_url,
                data={"username": f"[G] {unsent_message.player}", "content": unsent_message.message}
            )

        seen_messages.append(unsent_message.hash)

    clean_seen_messages(messages)

    sleep(15)
