from pathlib import Path
import json
from .horse import Event


def load_dlcs(resource_path: Path = Path(__file__).parent / "event_library") -> list[Event]:
    events_list = []
    files = resource_path.iterdir()
    for x in files:
        log = f"加载事件文件：{x.name}"
        print(log, end="......")
        with open(x, "r", encoding="utf-8") as f:
            events_list += [deal(event) for event in json.load(f) if event]
        print("成功!")
    return events_list


def deal(raw_event: dict):
    raw_event["only_key"] = raw_event.get("race_only")
    buffs = set()
    buff_tags = ["locate_lock", "vertigo", "hiding"]
    for buff_tag in buff_tags:
        if raw_event.get(buff_tag) == 1:
            buffs.add(buff_tag)
    for buff_tag in raw_event.get("other_buff", []):
        buffs.add(buff_tag)
    raw_event["buffs"] = buffs
    return Event.model_validate(raw_event)
