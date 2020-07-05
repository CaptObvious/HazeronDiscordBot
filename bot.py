import json
import os
import re
from hashlib import md5
from time import sleep
from typing import List

import boto3
import requests

SEEN_MESSAGES_PATH = "/usr/share/hazeron-persistent/seen_messages.json"
SYSTEM_MESSAGE_REGEX = re.compile(r"(?P<time>\d\d:\d\d).*>Hazeron<.*\">(?P<message>[^<]*)")
USER_MESSAGE_REGEX = re.compile(
    r"(?P<time>\d\d:\d\d).*[^;]\">(?P<player>[^<]*).*\">(?P<message>[^<]*)"
)

r = requests.Session()
ssm = boto3.client("secretsmanager")


def get_webhook_url():
    global ssm

    ssm_response = json.loads(ssm.get_secret_value(SecretId="HazeronDiscordBot/WebhookURL")['SecretString'])

    return ssm_response["WebhookURL"]


webhook_url = get_webhook_url()


def load_seen_messages() -> List[str]:
    if not os.path.exists(SEEN_MESSAGES_PATH):
        return []

    with open(SEEN_MESSAGES_PATH) as f:
        return json.loads(f.read())


seen_messages = load_seen_messages()


class ChatMessage:
    def __init__(self, player: str, message: str, time: str):
        self.player = player
        self.message = message.replace(" @", " @\u200b")

        if self.message.startswith("@"):
            self.message = f"@\u200b{self.message[1:]}"

        self.time = time

    def __repr__(self) -> str:
        return f"{self.player}: {self.message}"

    @property
    def hash(self) -> str:
        return md5(f"[{self.time}] {str(self)}".encode("utf-8")).hexdigest()


def save_seen_messages() -> None:
    global seen_messages

    with open(SEEN_MESSAGES_PATH, "w") as f:
        f.write(json.dumps(seen_messages))
        f.flush()
        os.fsync(f.fileno())


def fetch_galactic_chat() -> str:
    returned_html = r.get("https://hazeron.com/galactic.html")

    return returned_html.content.decode("utf-8")


def parse_galactic_chat(input_html: str) -> [ChatMessage]:
    user_messages = [x.groupdict() for x in USER_MESSAGE_REGEX.finditer(input_html)]
    system_messages = [x.groupdict() for x in SYSTEM_MESSAGE_REGEX.finditer(input_html)]

    parsed_messages = [ChatMessage(x['player'], x['message'], x['time']) for x in user_messages]
    parsed_messages += [ChatMessage("SYSTEM", x["message"], x["time"]) for x in system_messages]

    return parsed_messages


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
    save_seen_messages()

    sleep(15)
