<!-- markdownlint-disable MD031 MD033 MD036 MD041 -->
<div align="center">

# Clovers-Sarof

_✨ 改自 [nonebot_plugin_russian](https://github.com/HibiKier/nonebot_plugin_russian) 和 [nonebot_plugin_horserace](https://github.com/shinianj/nonebot_plugin_horserace) 的小游戏合集 ✨_

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![pypi](https://img.shields.io/pypi/v/clovers_leafgame.svg)](https://pypi.python.org/pypi/clovers_leafgame)
[![pypi download](https://img.shields.io/pypi/dm/clovers_leafgame)](https://pypi.python.org/pypi/clovers_leafgame)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Github](https://img.shields.io/badge/GitHub-Clovers-00CC33?logo=github)](https://github.com/clovers-project/clovers)
[![license](https://img.shields.io/github/license/clovers-project/clovers-leafgame.svg)](./LICENSE)

</div>

# 安装

```bash
pip install clovers_leafgame
```

# 配置

<details>

<summary>在 clovers 配置文件内按需添加下面的配置项</summary>

```toml
[clovers_leafgame]
# 主路径
main_path = "D:\\linbot\\LiteGames"
# 默认显示字体
fontname = "simsun"
# 默认备用字体
fallback_fonts = [ "Arial", "Tahoma", "Microsoft YaHei", "Segoe UI", "Segoe UI Emoji", "Segoe UI Symbol", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Source Han Sans SC", "Noto Sans SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "Apple Color Emoji", "Noto Color Emoji",]

["clovers_leafgame.modules.account"]
# 每日签到的范围
sign_gold = [ 200, 500,]
# 标记字符串（不要动）
clovers_marking = "ＬＵＣＫＹ ＣＬＯＶＥＲ"
revolution_marking = " ＣＡＰＩＴＡＬＩＳＴ "
debug_marking = "  ＯＦＦＩＣＩＡＬ  "

["clovers_leafgame.modules.game"]
# 超时时间
timeout = 60
# 默认赌注
default_bet = 200

["clovers_leafgame.modules.game.horse_race"]
# 玩家人数范围
range_of_player_numbers = [ 2, 8,]
# 跑道长度
setting_track_length = 30
# 随机位置事件，能够随机到的跑道范围
random_move_range = [ 0, 0.8,]
# 每回合基础移动范围
base_move_range = [ 1, 3,]
# 事件概率
event_randvalue = 450

["clovers_leafgame.modules.market"]
# 重置冷却时间，设置为0禁用发起重置
revolt_cd = 28800
# 重置的基尼系数
revolt_gini = 0.68
# 重置签到的范围
revolt_gold = [ 1000, 2000,]
# 注册公司金币数
company_public_gold = 20000

["clovers_leafgame.modules.prop"]
# 抽卡所需金币
gacha_gold = 50
# 礼包金币范围
packet_gold = [ 200, 2000,]
# 幸运硬币赌注范围
luckey_coin = [ 2000, 100000,]
```

</details>

**默认资料卡背景**

首次运行本插件之后，会出现 `/data/LeafGames/BG_image/` (或者你指定的) 这个路径。

你需要往这个文件夹下添加一个 `default.png` 的图片，所有人的默认资料卡背景图片就是这张图了。

如果不配置的话，就是纯色 ~~高性能模式~~

改图片的时候不用关 bot 也会生效

# 使用

<details>
  
<summary>管理员指令</summary>

`获取 【道具名】 【数量】`

获取相应数量的道具

`冻结资产@someone`

查封 at 的群友的全部资产。

由于游戏市场机制过于简单导致运营时间长了以后会出现金币数量离谱的玩家

如果金币持有量过于离谱，可以使用`冻结资产`查封。

`继承群账户 【被继承群】 -> 【继承群】`

把群被继承群全部的资产转移到继承群

`数据验证`

修复存档数据

`保存数据`

在关 bot 前需要保存数据，不然会回档到上次自动保存的时间点

`刷新每日`

刷新每日签到，补贴，金币转移上限，所有人时效道具的剩余时间-1

`数据备份`

备份游戏数据文件

`刷新市场`

刷新一次市场波动模拟

</details>

<details>
  
<summary>个人账户</summary>

`设置背景 【图片】 【蒙版类型】`

两个参数都是可选参数。

蒙版类型：默认，高斯模糊，透明，html 颜色代码（支持透明度）

设置我的资料卡显示的背景图片和蒙版类型。

`删除背景`

将资料卡显示的背景图片设置为默认

`金币签到`

玩家每日可签到一次，每日 0 点刷新。

`发红包 【金额】 @someone`

给 at 的用户发金币

`送道具 【道具名】 【道具数量】 @someone`

给 at 的用户送指定数量的道具（可以不填道具数量，默认为 1）。可以送路灯挂件牌，道具名：路灯挂件标记。

`【道具名】查询`

查看自己的道具数量，如`金币查询`，`钻石查询`

`我的资料卡`

查看个人账户详细资料

`我的道具【详情】`

参数可选。

查看自己的道具列表

`股票查询`

查看自己的股票以及报价

`群金库查看`

查看本群公有道具和股票。

`群金库存 【道具名或股票名】 【数量】`

向群金库里面存入相应数量的道具或股票。

`群金库取 【道具名或股票名】 【数量】`

从群金库里面取出相应数量的道具或股票，需要管理员以上权限。

`群资料卡`

查看本群的详细信息

</details>

<details>

<summary>市场系统</summary>

`发起重置`

按比例清空前十名的金币，第一名进入路灯挂件榜。公司等级+1。

`重置签到`

每次重置后可领取一次，当群内的基尼系数大于设定值可发起重置，重置后可进行一次重置签到。

每日刷新有几率刷新重置签到。

`金币转移 【公司名】 【金额】`

跨群转移金币到目标账户，如果金额为负数则是从目标账户跨群转移金币到本群账户

`金币转入 【金额】`

从个人账户向本群转入金币，如果金额为负数则是从本群向个人账户转入金币

个人账户的金币为标准金币，汇率等于 1 级公司金币

`市场注册 【公司名】 @bot`

权限：[群主，管理员，超管]

当本群符合市场注册条件时，可以使用此指令把此群号注册到市场。

`公司重命名 【公司名】 @bot`

权限：[群主，管理员，超管]

修改本公司在市场上的注册名称

`市场信息 公司名`

查看指定公司的详细信息

`市场信息`

查看市场上所有公司的简略信息

`购买 【公司名】 【数量】 【最高单价】`

<details>

<summary>购买指定公司的股票</summary>

公司名和数量必须指定。

购买公司的股票时你的金币会同时补充为公司的资产。

所以大量`购买`某公司股票会使该公司股价明显上涨。同样，大量`结算`某公司股票会使该公司股价明显下跌。

`最高单价`为购买时限制的最高单价

例：

假如文文日报社 10 金币 1 股。

发送指令 `购买 文文日报社 2000` 购买 2000 股该公司股票。

假设购买之后，文文日报社上涨到 15 金币 1 股。

如果发送指令 `购买 文文日报社 2000 12`

那么购买的股票数可能会小于 2000 股，因为`最高单价`参数在 文文日报社 股价为 12 金币时停止继续购买。

</details>

`出售 【公司名】 【数量】 【报价】`

<details>

<summary>结算指定公司的股票</summary>

公司名和数量必须指定。

结算公司的股票时公司的金币会同时减少。

所以大量`结算`某公司股票会使该公司股价明显下跌。

当指定报价时，如果当前市场报价高于指定报价才会出售。

不指定报价时，下次市场刷新会按照自动价格全部出售

</details>

</details>

<details>
  
<summary>道具系统</summary>

`@bot【N】连抽卡` `@bot【N】连`

抽取指定数量的道具，在私聊抽卡不用 at。

`使用道具 【道具名】 【数量】 【其他参数】`

只有道具名是必选参数，数量默认为 1

部分道具可使用，可以用此指令使用道具。

如果在数量位置的参数不可格式化为数字，数量会被指定为 1，在数量位置的参数会进入其他参数。

道具有全局道具，群内道具，永久道具，时效道具。

[道具效果](https://github.com/KarisAya/clovers_leafgame/blob/master/clovers_leafgame/modules/prop/props_library.json)

**临时维护凭证**

_使用 exec 执行代码字符串_

**空气礼包**

_每种空气各获得一个_

**随机红包**

_打开后可以获得随机金币。_

**重开券**

_重置自己的本群账户_

**幸运硬币**

_需要数量参数，有 50%的概率获得金币，50%的概率失去金币。_

**超级幸运硬币**

_有 50%的概率金币翻倍，50%的概率金币清零。没有上限_

**道具兑换券**

_群内道具,永久道具_

_兑换任意一个非特殊道具，使用此道具不需要持有本道具。_

_使用道具时，优先扣除道具库存，超出库存的数量用金币补充，每个 50 次抽卡所需金币。_

_需要指定其它参数为道具名_

_使用方法：_

_`使用道具 道具兑换券 超级幸运硬币` 兑换一个超级幸运硬币_

_`使用道具 道具兑换券 10 超级幸运硬币` 兑换 10 个超级幸运硬币_

**绯红迷雾之书**

_把你的个人数据回溯到到任意时间节点。可回溯的时间节点有多少取决于服务器备份设置_

**恶魔轮盘**

_名下所有账户的金币与股票净值翻 10 倍，或清空。_

</details>

<details>
  
<summary>排行系统</summary>

`【道具名或排名标题】排行`

查看本群玩家在本群持有道具的数量（或排名数据）排行

如 `金币排行` 查看本群金币数排行

`【道具名或排名标题】总排行`

查看所有玩家的全部账户的道具总数量（或排名数据）排行

如果指定的道具名是群内道具，那么计算总数时会计算道具所在群汇率

**排名标题**

`胜场`,`连胜`,`败场`,`连败`,`路灯挂件`

</details>

<details>

<summary>开始游戏</summary>

游戏可以使用道具作为赌注！

注：同一时间群内只能有一场对决

所有游戏都可以通过下方的指令发起

`发起游戏指令 【下注道具】 【下注数量】 【其它参数】@someone`

发起游戏指令的所有参数都可忽略

`下注道具` 默认为金币

`下注数量` 默认为 0

`其它参数` 默认为空。如果想要给其它参数传入一个可以被格式化为数字的字符串，那么必须要有下注数量。

`at` 指定接受挑战对象

游戏对局可以使用如下指令处理

`接受挑战`

`拒绝挑战`

`认输`

`超时结算` （60 秒）

`游戏重置` （需要游戏对局超时）

**发起游戏指令**

<details>

<summary>俄罗斯轮盘</summary>

**发起**

`俄罗斯轮盘`

其它参数为装弹数

**进行**

`开枪 【N】`

**规则**

通过 装弹 来对其他人发起决斗，轮流开枪，直到运气不好的人先去世。

</details>

<details>

<summary>掷骰子</summary>

**发起**

`掷骰子`

**进行**

`开数`

**规则**

通过 掷骰子 来对其他人发起决斗，先手事先展示自己的组合。

后手可选择认输或继续开数，如后手开数则赌注翻倍。

先比组合，再比点数。

组合：满（5 个相同） > 串（4 个相同） > 条（3 个相同） > 两对（2 组 2 个相同） > 对（2 个相同） > 散（全不相同）

</details>

<details>

<summary>扑克对战</summary>

**发起**

`扑克对战`

**进行**

`出牌 1/2/3`

**规则**

通过 扑克对战 来对其他人对战，打出自己的手牌。当对方的血量小于 1 或者在自己回合出牌前血量>40 即可获胜。

牌库有两副共 104 张牌，当牌库没有牌了就以目前血量结算，结束游戏。

先手初始点数：HP 20 SP 0 DEF 0

后手初始点数：HP 25 SP 2 DEF 0

每回合抽三张牌，打出其中的一张作为行动牌，弃掉剩余手牌。**特别注意：防御牌作为行动牌是攻击**

之后对方摇一个 20 面骰子，如果点数小于对方 SP 则从牌库翻出一张牌作为技能牌打出，按照技能牌点数扣除对方 SP 点。

| 花色 | 描述 | 行动牌效果 | 技能牌效果 |
| ---- | ---- | ---------- | ---------- |
| 黑桃 | 防御 | 打出攻击   | 增加 DEF   |
| 红桃 | 生命 | 恢复 HP    | 恢复 HP    |
| 梅花 | 技能 | 主动技能   | 增加 SP    |
| 方片 | 攻击 | 打出攻击   | 打出反击   |

主动技能：摇一个 20 面骰子，如果点数小于自身 SP 则把剩余两张手牌作为技能牌全部打出，按照技能牌点数扣除自身 SP 点

ACE 技能：摇一个 6 面骰子，把打出的 ACE 牌点替换成摇出的点数，再把三张手牌全部作为技能牌打出，按照技能牌点数扣除自身 SP 点

</details>

<details>

<summary>同花顺</summary>

**发起**

`同花顺` `梭哈`

其它参数为等级 1-5，默认为 1，和手牌的大小相关。

**进行**

`看牌`

在开牌前可以确认自己的手牌。可私聊看牌（需要添加 bot 好友）

`开牌`

**规则**

通过 同花顺 来对其他人对战，先手看牌开牌，后手看牌开牌，直到一方认输或点数大的获胜。

组合：同花顺 > 四条 > 葫芦 > 同花 > 顺子 > 三条 > 两对 > 一对 > 散牌

花色：黑桃 > 红桃 > 梅花 > 方片

</details>

<details>

<summary>21点</summary>

**发起**

`21点`

对战双方需要添加 bot 好友

**进行**

`抽牌`

抽一张牌

`停牌`

停止抽牌

`双倍下注`

抽一张牌并停牌，赌注翻倍。

**规则**

通过 21 点 来对其他人对战，手牌点数大的获胜。

游戏中点数超过 21 会直接失败。

</details>

<details>

<summary>西部对战</summary>

**发起**

`西部对战 金额 at`

对战双方需要添加 bot 好友

**进行（私聊 bot）**

`装弹` `开枪` `闪避` `闪枪` `预判开枪`

**规则**

双方私聊 bot 本轮的行动

双方初始 1 发子弹，装弹上限为 6 发子弹（6 发可以继续装弹，但是子弹数不会再增加了）。

如果双方同时`开枪`，那么子弹会发生碰撞。本轮平局

`装弹` 在 **初始位置** 行动，剩余子弹数+1。会被 `开枪` `闪枪` 击杀

`闪避` 去 **闪避位置** ，不会消耗子弹。会被 `预判开枪` 击杀

`开枪` 在 **初始位置** 行动，打对方 **初始位置** ，剩余子弹数-1 击杀 `装弹` `预判开枪`

`闪枪` 去 **闪避位置** ，打对方 **初始位置** ，剩余子弹数-1 击杀 `装弹` `开枪`

`预判开枪` 在 **初始位置** 行动，打对方 **闪避位置** ，剩余子弹数-1 击杀 `闪避` `闪枪`

注：预判开枪不会与闪枪发生子弹碰撞，因为预判开枪速度比闪避开枪速度快。

</details>

<details>

<summary>恶魔轮盘</summary>

**发起**

`恶魔轮盘`

**进行**

`向对方开枪`,`向自己开枪`

如果向自己开枪是空弹，那么下一回合仍是自己行动。

`使用道具 道具名`

开枪前可以使用道具。

需要注意的是使用肾上腺素时需要同时指定对方道具

例如 `使用道具 肾上腺素 手铐` 这样就会使用对方的手铐

如果不指定道具或指定了对方没有的道具你会使用失败（肾上腺素仍会扣除）

**规则**

参考 [buckshot roulette](https://store.steampowered.com/app/2835570/_/) 规则

一些修改：

在子弹打光之后的下一回合会同时清空双方 buff 并切换玩家，而不是闲家回合

手铐可以永动

新增了道具 箱子 可以给两个人各刷一个道具

</details>

<details>

<summary>天国骰子</summary>

**发起**

`天国骰子 金额 at`

**进行**

`123456 继续`，`123456 结束`

**规则**

参考 [天国拯救 2](https://kingdomcomerpg.com/) 内无徽章骰子的规则

</details>

<details>

<summary>赛马小游戏</summary>

~~抄~~改自 [nonebot_plugin_horserace](https://github.com/shinianj/nonebot_plugin_horserace)

~~发言复刻~~ 请不要在使用此插件时出现报错去找原作者（冲我来，发 issue，我已经准备好赴死了）

`赛马创建`

第一位玩家发起活动

`赛马加入 你的马儿名称`

花费报名费，加入你的赛马

`赛马开始`

如果有足够的人加入了游戏，那么可以通过本指令开始游戏

`赛马暂停`

暂停本群的赛马，稍后可以用`赛马开始`继续游戏

**自定义事件包方式**

详细信息请参考：

[事件添加相关.txt](https://github.com/shinianj/nonebot_plugin_horserace/blob/main/%E4%BA%8B%E4%BB%B6%E6%B7%BB%E5%8A%A0%E7%9B%B8%E5%85%B3.txt)

[事件详细模板.txt](https://github.com/shinianj/nonebot_plugin_horserace/blob/main/%E4%BA%8B%E4%BB%B6%E8%AF%A6%E7%BB%86%E6%A8%A1%E6%9D%BF.txt)

写完的 json 文件放入 events/horserace 文件夹中就能跑了（除非你写错了，在加载事件时会失败，但不会影响其他事件加载也不会让你的 bot 崩了）

</details>

<details>

<summary>堡垒战</summary>

待补充

</details>

</details>

<details>

<summary>私聊关联群聊账户</summary>

可以在私聊签到、抽卡、使用道具、查看我的金币/道具/资料卡、查看排行，购买或结算股票，以及进行游戏等操作。

不过你直接去的话大概会提示关未联群聊账户（

连接账户的方法

1. 在群里发送`@bot关联账户`私聊账户就会关联到本群里
2. 私聊发送`关联账户`再根据提示输入群号私聊账户就会关联到群号所指的群
3. 进行游戏时账户会连接到游戏正在进行的群。

**如果你正在一场游戏中,然后把账户关联到别的群了，那么你会找不到对局。**

**请不要在游戏中修改关联的账户，如果不慎修改还想继续本场对局的话，那么请关联到对局所在的群。**

**请不要同时在多个群进行游戏，如果非要在多个群进行游戏，那么请注意发送游戏进行的指令之前账户是否关联到了对局所在的群。**

</details>

# 鸣谢

- [nonebot2](https://github.com/nonebot/nonebot2) 跨平台 Python 异步聊天机器人框架
- [nonebot_plugin_russian](https://github.com/HibiKier/nonebot_plugin_russian) 轮盘小游戏
- [nonebot_plugin_horserace](https://github.com/shinianj/nonebot_plugin_horserace) 赛马小游戏
- [nonebot_plugin_apscheduler](https://github.com/nonebot/plugin-apscheduler) APScheduler 定时任务插件
