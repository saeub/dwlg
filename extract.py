import json
import hashlib
import html
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from glob import glob
from typing import Optional


def normalize(string: str, keep_linebreaks: bool = False) -> str:
    string = string.strip()
    string = string.replace(" ", " ")
    if not keep_linebreaks:
        string = string.replace("\n", " ")
    while "  " in string:
        string = string.replace("  ", " ")
    while " \n" in string:
        string = string.replace(" \n", "\n")
    while "\n " in string:
        string = string.replace("\n ", "\n")
    while "\n\n\n" in string:
        string = string.replace("\n\n\n", "\n\n")
    string = string.replace("…", "...")
    return string


def remove_html(string: str, keep_paragraphs: bool = False) -> str:
    string = re.sub(r"\s+", " ", string)
    if keep_paragraphs:
        string = re.sub(r"<br />", "\n", string)
        string = re.sub(r"</p>", "\n\n", string)
    string = re.sub(r"<[^>]+>", "", string)
    string = html.unescape(string)
    string = string.strip()
    return string


def remove_annotations(string: str) -> str:
    string = re.sub(r"\[Anmerkung:[^\]]+\]", "", string)
    return string


@dataclass
class Image:
    url: str
    name: str

    @classmethod
    def from_raw(cls, data) -> "Image":
        url = data["staticUrl"]
        name = data["name"]
        return cls(url, name)


@dataclass
class Audio:
    url: str
    name: str
    duration: timedelta

    @classmethod
    def from_raw(cls, data) -> "Audio":
        url = data["mp3Src"]
        name = normalize(data["name"])
        minutes, seconds = re.match(
            r"^(\d+):(\d+)$", data["formattedDuration"]
        ).groups()
        duration = timedelta(minutes=int(minutes), seconds=int(seconds))
        return cls(url, name, duration)


@dataclass
class Manuscript:
    teaser: Optional[str]
    text: Optional[str]

    @classmethod
    def from_raw(cls, data) -> "Manuscript":
        teaser = data["teaser"]
        text = normalize(remove_html(data["manuscript"], keep_paragraphs=True), keep_linebreaks=True) if data["manuscript"] else None
        return cls(teaser, text)


class Item:
    @staticmethod
    def from_raw(data) -> Optional["Item"]:
        item_type = data["inquiryType"]
        selection_type = data["selectionType"]

        if item_type == "ASSOCIATION" and selection_type in ["SINGLE", "MULTIPLE"]:
            question = normalize(data["inquiryText"])
            question = re.sub(r"\.{2,}", "___", question)
            assert len(data["subInquiries"]) == 1
            alternatives = [
                Answer.from_raw(alternative)
                for alternative in data["subInquiries"][0]["alternatives"]
            ]
            multiple = data["selectionType"] == "MULTIPLE"
            return AssociationItem(question, alternatives, multiple)

        # else:
        #     print(f"Unknown item type: {item_type} ({selection_type})", file=sys.stderr)

        return None


@dataclass
class Answer:
    text: str
    correct: bool

    @classmethod
    def from_raw(cls, data) -> "Answer":
        text = normalize(data["alternativeText"])
        text = re.sub(r"^\.+\s*", "", text)
        correct = data["isCorrect"]
        return cls(text, correct)


@dataclass
class AssociationItem(Item):
    question: str
    answers: list[Answer]
    multiple: bool


@dataclass
class Exercise:
    url: str
    name: str
    description: str
    items: list[Item]

    @classmethod
    def from_raw(cls, data) -> "Exercise":
        url = data["namedUrl"]
        if url.startswith("/"):
            url = "https://learngerman.dw.com" + url
        name = normalize(data["name"])
        description = remove_html(data["description"])
        items = list(
            filter(
                bool,
                (Item.from_raw(item) for item in data["inquiries"]),
            )
        )

        return Exercise(url, name, description, items)


@dataclass
class Lesson:
    id: int
    course: str
    name: str
    image: Optional[Image]
    audio: Optional[Audio]
    manuscript: Manuscript
    items: list[Item]
    original_url: Optional[str]

    @classmethod
    def from_raw(cls, data) -> "Lesson":
        id = data["lesson"]["id"]
        course = data["course"]
        name = data["lesson"]["name"]
        if data["lesson"]["mainContentImage"] is not None:
            image = Image.from_raw(data["lesson"]["mainContentImage"])
        else:
            image = None
        audios = [Audio.from_raw(audio) for audio in data["lesson"]["audios"]]
        assert len(audios) <= 1
        if len(audios) == 1:
            audio = audios[0]
        else:
            audio = None
        manuscript = Manuscript.from_raw(data["manuscript"])
        exercises = list(filter(lambda e: e.items, (Exercise.from_raw(exercise) for exercise in data["exercises"])))
        items = [item for exercise in exercises for item in exercise.items]
        # Usually, only the first 3 items are content-related
        items = items[:3]
        for link in data["extras"]["externalLinks"]:
            if "Originalartikel" in link["name"] and link["url"].startswith(
                "https://www.dw.com"
            ):
                original_url = link["url"]
                break
        else:
            original_url = None

        return cls(id, course, name, image, audio, manuscript, items, original_url)

    def to_json(self, split: str) -> str:
        data = {
            "text": self.manuscript.text,
            "items": [
                {
                    "question": item.question,
                    "answers": [
                        {"text": answer.text, "correct": answer.correct}
                        for answer in item.answers
                    ],
                    "multiple": item.multiple,
                }
                for item in self.items
            ],
            "metadata": {
                "dataset": "dwlg",
                "split": split,
                "extra": {
                    "id": self.id,
                    "course": self.course,
                    "name": self.name,
                }
            }
        }
        return json.dumps(data, ensure_ascii=False, cls=CustomEncoder)

    def hash(self) -> str:
        data = json.loads(self.to_json(""))
        del data["metadata"]  # Don't include metadata in hash
        data_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
        data_hash = hashlib.sha1(data_json.encode("utf-8"))
        return data_hash.hexdigest()


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


if __name__ == "__main__":
    hash_file = sys.argv[1]
    split = sys.argv[2]
    with open(hash_file) as f:
        hashes = json.load(f)

    if "*" in hashes:
        del hashes["*"]
        for filename in glob("data/raw/lesson-*.json"):
            lesson_id = re.match(r"data/raw/lesson-(\d+).json", filename).group(1)
            if lesson_id not in hashes:
                hashes[lesson_id] = None

    with open(f"data/splits/{split}.jsonl", "w") as outfile:
        for lesson_id in hashes:
            with open(f"data/raw/lesson-{lesson_id}.json") as infile:
                lesson = Lesson.from_raw(json.load(infile))

            # Check integrity
            if hashes[lesson_id] is not None and hashes[lesson_id] != lesson.hash():
                    print(f"WARNING: Hash mismatch for lesson {lesson_id}", file=sys.stderr)

            print(lesson.to_json(split), file=outfile)
