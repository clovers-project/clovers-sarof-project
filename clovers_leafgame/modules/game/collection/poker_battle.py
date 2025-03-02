import random
import asyncio
from clovers_leafgame.main import plugin
from clovers_leafgame.core.clovers import Event
from clovers_leafgame.output import text_to_image, BytesIO
from ..core import Session, Game
from ..tools import random_poker
from .action import place


class PokerGame:
    suit = {0: "结束", 1: "♠防御", 2: "♥恢复", 3: "♣技能", 4: "♦攻击"}
    point = {
        0: " 0",
        1: " A",
        2: " 2",
        3: " 3",
        4: " 4",
        5: " 5",
        6: " 6",
        7: " 7",
        8: " 8",
        9: " 9",
        10: "10",
        11: "11",
        12: "12",
        13: "13",
    }

    def __init__(self) -> None:
        deck = random_poker(2)
        hand = deck[:3]
        deck = deck[3:]
        self.deck = deck + [(0, 0), (0, 0), (0, 0), (0, 0)]
        self.P1 = Gamer(hand, 20)
        self.P2 = Gamer([], 25, SP=2)

    @classmethod
    def card(cls, suit: int, point: int):
        return f"{cls.suit[suit]}{cls.point[point]}"


class Gamer:
    def __init__(
        self,
        hand: list[tuple[int, int]],
        HP: int,
        ATK: int = 0,
        DEF: int = 0,
        SP: int = 0,
    ) -> None:
        self.hand = hand
        self.HP = HP
        self.ATK = ATK
        self.DEF = DEF
        self.SP = SP

    def status(self) -> str:
        return f"HP {self.HP} SP {self.SP} DEF {self.DEF}"

    def handcard(self) -> str:
        return "\n".join(f"【{PokerGame.card(*card)}】" for i, card in enumerate(self.hand, 1))

    def action_ACE(self, roll: int = 1) -> list[str]:
        msg = [f"技能牌：\n{self.handcard()}"]
        for suit, point in self.hand:
            point = roll if point == 1 else point
            match suit:
                case 1:
                    self.DEF += point
                    msg.append(f"♠防御力强化了{point}")
                case 2:
                    self.HP += point
                    msg.append(f"♥生命值增加了{point}")
                case 3:
                    self.SP += point * 2
                    msg.append(f"♣技能点增加了{point}")
                case 4:
                    self.ATK += point
                    msg.append(f"♦发动了攻击{point}")
            self.SP -= point
            self.SP = 0 if self.SP < 0 else self.SP
        return msg

    def action_active(self, index: int) -> list[str]:
        msg = []
        suit, point = self.hand[index]
        if point == 1:
            roll = random.randint(1, 6)
            msg.append(f"发动ACE技能！六面骰子判定为 {roll}")
            msg += self.action_ACE(roll)
        else:
            match suit:
                case 1:
                    self.ATK += point
                    msg.append(f"♠发动了攻击{point}")
                case 2:
                    self.HP += point
                    msg.append(f"♥生命值增加了{point}")
                case 3:
                    self.SP += point
                    msg.append(f"♣技能点增加了{point}")
                    roll = random.randint(1, 20)
                    msg.append(f"二十面骰判定为{roll}点，当前技能点{self.SP}")
                    if self.SP < roll:
                        msg.append("技能发动失败...")
                    else:
                        msg.append("技能发动成功！")
                        del self.hand[index]
                        msg += self.action_ACE()
                case 4:
                    self.ATK += point
                    msg.append(f"♦发动了攻击{point}")
        return msg

    def action_passive(self, card: tuple[int, int]) -> list[str]:
        msg = []
        suit, point = card
        msg.append(f"技能牌：{PokerGame.card(suit, point)}")
        match suit:
            case 1:
                self.DEF += point
                msg.append(f"♠发动了防御{point}")
            case 2:
                self.HP += point
                msg.append(f"♥生命值增加了{point}")
            case 3:
                self.SP += point * 2
                msg.append(f"♣技能点增加了{point}")
            case 4:
                self.ATK += point
                msg.append(f"♦发动了反击{point}")
        self.SP -= point
        self.SP = 0 if self.SP < 0 else self.SP
        return msg


poker_battle = Game("扑克对战", "出牌")


@plugin.handle(["扑克对战"], ["user_id", "group_id", "at"], priority=1)
@poker_battle.create(place)
async def _(session: Session, arg: str):
    poker_data = PokerGame()
    session.data["ACT"] = False
    session.data["poker"] = poker_data
    if session.bet:
        prop, n = session.bet
        tip = f"\n本场下注：{n}{prop.name}"
    else:
        tip = ""
    session.start_tips = f"P1初始手牌\n{poker_data.P1.handcard()}"
    return f"唰唰~，随机牌堆已生成{tip}\n{session.create_info()}"


@plugin.handle(["出牌"], ["user_id", "group_id"])
@poker_battle.action(place)
async def _(event: Event, session: Session):
    if session.data["ACT"]:
        return
    user_id = event.user_id
    if not 1 <= (index := event.args_to_int()) <= 3:
        return "请发送【出牌 1/2/3】打出你的手牌。"
    index -= 1
    session.data["ACT"] = True
    session.nextround()
    poker_data = session.data["poker"]
    assert isinstance(poker_data, PokerGame)
    if user_id == session.p1_uid:
        active = poker_data.P1
        passive = poker_data.P2
        passive_name = session.p2_nickname
    else:
        active = poker_data.P2
        passive = poker_data.P1
        passive_name = session.p1_nickname
    msg = active.action_active(index)
    if passive.SP > 1:
        roll = random.randint(1, 20)
        msg.append(f"{passive_name} 二十面骰判定为{roll}点，当前技能点{passive.SP}")
        if passive.SP < roll:
            msg.append("技能发动失败...")
        else:
            msg.append("技能发动成功！")
            msg += passive.action_passive(poker_data.deck[0])
            poker_data.deck = poker_data.deck[1:]
    # 回合结算
    if passive.ATK > active.DEF:
        active.HP += active.DEF - passive.ATK
    if active.ATK > passive.DEF:
        passive.HP += passive.DEF - active.ATK
    active.ATK = 0
    passive.ATK = 0
    passive.DEF = 0
    # 下回合准备
    passive.hand = hand = poker_data.deck[0:3]
    poker_data.deck = poker_data.deck[3:]
    output = BytesIO()
    text_to_image(
        f"玩家：{session.p1_nickname}\n"
        f"状态：{poker_data.P1.status()}\n"
        "----\n"
        f"玩家：{session.p2_nickname}\n"
        f"状态：{poker_data.P2.status()}\n"
        "----\n" + passive.handcard(),
        width=540,
        bg_color="white",
    ).save(output, format="png")
    msg = "\n".join(msg)

    async def result(tip: str):
        yield msg
        await asyncio.sleep(0.03 * len(msg))
        yield [tip, output]

    if active.HP < 1 or passive.HP < 1 or passive.HP > 40 or (0, 0) in hand:
        session.win = session.p1_uid if poker_data.P1.HP > poker_data.P2.HP else session.p2_uid
        return session.end(result("游戏结束"))
    session.data["ACT"] = False
    return result(f"请{passive_name}发送【出牌 1/2/3】打出你的手牌。")
