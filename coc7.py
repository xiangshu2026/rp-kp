# -*- coding: utf-8 -*-
"""COC 7th 角色卡：属性、派生值、技能表、职业模板、随机生成。"""
import json, random, time
from pathlib import Path

ROOT = Path(__file__).parent
CARDS = ROOT / "cards"
NL = chr(10)

# ---------- 八项基础属性 ----------
ATTRS = [
    ("STR", "力量"), ("CON", "体质"), ("SIZ", "体型"), ("DEX", "敏捷"),
    ("APP", "外貌"), ("INT", "智力"), ("POW", "意志"), ("EDU", "教育"),
]

# 每项属性的投掷公式（COC 7th）
def roll_attr(key, age_group=1):
    if key in ("SIZ", "INT", "EDU"):
        v = (sum(random.randint(1, 6) for _ in range(2)) + 6) * 5
    else:
        v = sum(random.randint(1, 6) for _ in range(3)) * 5
    return v


# ---------- 技能表（COC 7th 核心规则书）----------
# (中文名, 英文键, 基础值, 分类)
SKILLS = [
    ("会计", "accounting", 5, "知识"),
    ("人类学", "anthropology", 1, "知识"),
    ("估价", "appraise", 5, "知识"),
    ("考古学", "archaeology", 1, "知识"),
    ("取悦", "charm", 15, "交际"),
    ("攀爬", "climb", 20, "行动"),
    ("信用评级", "credit_rating", 0, "交际"),
    ("克苏鲁神话", "cthulhu_mythos", 0, "特殊"),
    ("乔装", "disguise", 5, "行动"),
    ("闪避", "dodge", 0, "行动"),
    ("汽车驾驶", "drive_auto", 20, "行动"),
    ("电气维修", "elec_repair", 10, "技术"),
    ("电子学", "electronics", 1, "技术"),
    ("话术", "fast_talk", 5, "交际"),
    ("格斗(斗殴)", "fighting_brawl", 25, "战斗"),
    ("格斗(剑)", "fighting_sword", 20, "战斗"),
    ("格斗(斧)", "fighting_axe", 15, "战斗"),
    ("格斗(矛)", "fighting_spear", 20, "战斗"),
    ("格斗(鞭)", "fighting_whip", 5, "战斗"),
    ("射击(手枪)", "firearms_handgun", 20, "战斗"),
    ("射击(步枪/霰弹)", "firearms_rifle", 25, "战斗"),
    ("射击(弓)", "firearms_bow", 15, "战斗"),
    ("急救", "first_aid", 30, "技术"),
    ("历史", "history", 5, "知识"),
    ("恐吓", "intimidate", 15, "交际"),
    ("跳跃", "jump", 20, "行动"),
    ("母语", "language_own", 0, "语言"),
    ("外语", "language_other", 1, "语言"),
    ("法律", "law", 5, "知识"),
    ("图书馆使用", "library_use", 20, "知识"),
    ("聆听", "listen", 20, "感知"),
    ("锁匠", "locksmith", 1, "技术"),
    ("机械维修", "mech_repair", 10, "技术"),
    ("医学", "medicine", 1, "知识"),
    ("博物学", "natural_world", 10, "知识"),
    ("导航", "navigate", 10, "行动"),
    ("神秘学", "occult", 5, "知识"),
    ("操作重型机械", "op_hvy_mach", 1, "技术"),
    ("说服", "persuade", 10, "交际"),
    ("精神分析", "psychoanalysis", 1, "知识"),
    ("心理学", "psychology", 10, "知识"),
    ("骑术", "ride", 5, "行动"),
    ("科学", "science", 1, "知识"),
    ("妙手", "sleight_of_hand", 10, "行动"),
    ("侦查", "spot_hidden", 25, "感知"),
    ("潜行", "stealth", 20, "行动"),
    ("生存", "survival", 10, "行动"),
    ("游泳", "swim", 20, "行动"),
    ("投掷", "throw", 20, "战斗"),
    ("追踪", "track", 10, "感知"),
    ("潜水", "diving", 1, "行动"),
    ("爆破", "demolitions", 1, "技术"),
    ("读唇", "lipreading", 1, "感知"),
    ("催眠", "hypnosis", 1, "交际"),
    ("炮术", "artillery", 1, "战斗"),
    ("技艺(表演)", "art_perform", 5, "技艺"),
    ("技艺(摄影)", "art_photo", 5, "技艺"),
    ("技艺(烹饪)", "art_cook", 5, "技艺"),
    ("技艺(绘画)", "art_paint", 5, "技艺"),
    ("技艺(乐器)", "art_music", 5, "技艺"),
    ("技艺(技术制图)", "art_draft", 5, "技艺"),
    ("技艺(速记)", "art_short", 5, "技艺"),
    ("技艺(打字)", "art_type", 5, "技艺"),
    ("技艺(木工)", "art_wood", 5, "技艺"),
    ("技艺(管道)", "art_plumb", 5, "技艺"),
    ("技艺(耕作)", "art_farm", 5, "技艺"),
    ("技艺(采矿)", "art_mine", 5, "技艺"),
    ("技艺(泥瓦)", "art_mason", 5, "技艺"),
    ("技艺(雕塑)", "art_sculpt", 5, "技艺"),
    ("技艺(任一)", "art_any", 5, "技艺"),
    ("科学(生物学)", "sci_bio", 1, "科学"),
    ("科学(化学)", "sci_chem", 1, "科学"),
    ("科学(物理学)", "sci_phys", 1, "科学"),
    ("科学(数学)", "sci_math", 1, "科学"),
    ("科学(天文学)", "sci_astro", 1, "科学"),
    ("科学(地质学)", "sci_geo", 1, "科学"),
    ("科学(药学)", "sci_pharm", 1, "科学"),
    ("科学(动物学)", "sci_zoo", 1, "科学"),
    ("科学(工程学)", "sci_eng", 1, "科学"),
    ("科学(气象学)", "sci_meteo", 1, "科学"),
    ("计算机使用", "comp_use", 5, "技术"),
    ("驾驶(船)", "drive_boat", 1, "行动"),
    ("驾驶(飞机)", "drive_plane", 1, "行动"),
    ("驾驶(马车)", "drive_cart", 10, "行动"),
    ("动物驯养", "animal_handling", 5, "技术"),
    ("运动", "athletics", 20, "行动"),
    ("科学(任一)", "sci_any", 1, "科学"),
    ("杂技", "acrobatics", 5, "技艺"),
    ("摄影", "photography", 5, "技艺"),
]

SKILL_INDEX = {k: (cn, base, cat) for cn, k, base, cat in SKILLS}


# ---------- 职业模板 ----------
OCCUPATIONS = {
    "会计师": {"credit": [30, 70], "points": [("EDU",4)],
        "skills": ["会计", "法律", "图书馆使用", "聆听", "侦查", "说服", "心理学", "计算机使用"]},
    "杂技演员": {"credit": [5, 20], "points": [("EDU",2),("DEX",2)],
        "skills": ["攀爬", "闪避", "跳跃", "投掷", "游泳", "骑术", "妙手", "恐吓"]},
    "演员": {"credit": [10, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(表演)", "乔装", "话术", "心理学", "说服", "聆听", "侦查", "取悦"]},
    "建筑师": {"credit": [30, 70], "points": [("EDU",4)],
        "skills": ["技艺(技术制图)", "科学(数学)", "法律", "图书馆使用", "会计", "估价", "侦查", "操作重型机械"]},
    "图书管理员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["图书馆使用", "会计", "历史", "外语", "母语", "侦查", "聆听", "计算机使用"]},
    "拳击手": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["格斗(斗殴)", "闪避", "恐吓", "聆听", "心理学", "跳跃", "急救", "运动"]},
    "神职人员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["说服", "心理学", "图书馆使用", "历史", "神秘学", "外语", "聆听", "精神分析", "母语"]},
    "程序员": {"credit": [10, 70], "points": [("EDU",4)],
        "skills": ["计算机使用", "电气维修", "电子学", "图书馆使用", "科学(数学)", "侦查", "会计", "外语"]},
    "罪犯": {"credit": [5, 65], "points": [("EDU",2),("DEX",2)],
        "skills": ["潜行", "锁匠", "妙手", "侦查", "聆听", "话术", "闪避", "格斗(斗殴)"]},
    "医生": {"credit": [40, 80], "points": [("EDU",4)],
        "skills": ["医学", "急救", "精神分析", "心理学", "科学(生物学)", "科学(药学)", "外语", "说服", "侦查"]},
    "私人侦探": {"credit": [20, 45], "points": [("EDU",2),("DEX",2)],
        "skills": ["侦查", "聆听", "心理学", "话术", "法律", "图书馆使用", "射击(手枪)", "潜行", "闪避"]},
    "流浪汉": {"credit": [0, 5], "points": [("EDU",2),("DEX",2)],
        "skills": ["潜行", "聆听", "侦查", "闪避", "话术", "生存", "攀爬", "妙手", "格斗(斗殴)"]},
    "工程师": {"credit": [30, 60], "points": [("EDU",4)],
        "skills": ["机械维修", "电气维修", "电子学", "操作重型机械", "科学(工程学)", "爆破", "侦查", "攀爬", "汽车驾驶"]},
    "艺人": {"credit": [5, 30], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(表演)", "技艺(乐器)", "技艺(任一)", "乔装", "话术", "聆听", "心理学", "取悦"]},
    "农民": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(耕作)", "动物驯养", "机械维修", "博物学", "导航", "驾驶(马车)", "急救", "侦查"]},
    "消防员": {"credit": [10, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["急救", "攀爬", "闪避", "驾驶(马车)", "机械维修", "操作重型机械", "侦查", "游泳"]},
    "记者": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["话术", "说服", "心理学", "图书馆使用", "侦查", "聆听", "历史", "母语", "外语"]},
    "法官": {"credit": [50, 80], "points": [("EDU",4)],
        "skills": ["法律", "图书馆使用", "聆听", "心理学", "说服", "会计", "历史", "母语"]},
    "律师": {"credit": [30, 80], "points": [("EDU",4)],
        "skills": ["法律", "图书馆使用", "聆听", "心理学", "说服", "话术", "会计", "母语"]},
    "军官": {"credit": [20, 70], "points": [("EDU",2),("STR",2)],
        "skills": ["射击(步枪/霰弹)", "格斗(斗殴)", "闪避", "恐吓", "聆听", "导航", "急救", "汽车驾驶"]},
    "军人": {"credit": [20, 50], "points": [("EDU",2),("STR",2)],
        "skills": ["射击(步枪/霰弹)", "格斗(斗殴)", "闪避", "攀爬", "急救", "恐吓", "聆听", "潜行", "投掷"]},
    "博物馆馆长": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["考古学", "历史", "图书馆使用", "估价", "侦查", "神秘学", "会计", "外语"]},
    "音乐家": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(乐器)", "技艺(表演)", "聆听", "心理学", "话术", "历史", "外语"]},
    "护士": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["急救", "医学", "心理学", "聆听", "科学(生物学)", "科学(药学)", "侦查", "说服"]},
    "药剂师": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["科学(药学)", "科学(化学)", "医学", "急救", "会计", "图书馆使用", "侦查", "外语"]},
    "摄影师": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(摄影)", "侦查", "潜行", "心理学", "图书馆使用", "话术"]},
    "警察": {"credit": [20, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["射击(手枪)", "格斗(斗殴)", "法律", "侦查", "聆听", "心理学", "急救", "汽车驾驶", "说服"]},
    "教授": {"credit": [20, 70], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "心理学", "说服", "外语", "考古学", "科学(任一)", "母语", "侦查"]},
    "飞行员": {"credit": [20, 70], "points": [("EDU",2),("DEX",2)],
        "skills": ["驾驶(飞机)", "导航", "机械维修", "科学(气象学)", "聆听", "侦查", "急救"]},
    "心理医生": {"credit": [30, 80], "points": [("EDU",4)],
        "skills": ["精神分析", "心理学", "医学", "聆听", "说服", "图书馆使用", "外语"]},
    "研究员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["图书馆使用", "科学(任一)", "计算机使用", "外语", "侦查", "历史", "会计"]},
    "海员": {"credit": [10, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["游泳", "导航", "驾驶(船)", "机械维修", "攀爬", "急救", "侦查"]},
    "销售员": {"credit": [10, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["话术", "说服", "心理学", "会计", "聆听", "侦查", "取悦"]},
    "科学家": {"credit": [10, 70], "points": [("EDU",4)],
        "skills": ["科学(任一)", "图书馆使用", "计算机使用", "外语", "侦查", "会计"]},
    "秘书": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(速记)", "技艺(打字)", "会计", "图书馆使用", "聆听", "心理学", "计算机使用"]},
    "士兵": {"credit": [10, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["射击(步枪/霰弹)", "格斗(斗殴)", "闪避", "潜行", "急救", "攀爬", "聆听"]},
    "学生": {"credit": [5, 20], "points": [("EDU",4)],
        "skills": ["图书馆使用", "外语", "计算机使用", "侦查", "聆听", "历史", "科学(任一)"]},
    "技术员": {"credit": [10, 50], "points": [("EDU",4)],
        "skills": ["电气维修", "电子学", "机械维修", "计算机使用", "科学(工程学)", "侦查"]},
    "接线员": {"credit": [10, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["聆听", "话术", "电子学", "计算机使用", "侦查", "心理学"]},
    "殡葬师": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["医学", "会计", "心理学", "说服", "急救", "侦查", "历史"]},
    "传教士": {"credit": [0, 30], "points": [("EDU",4)],
        "skills": ["说服", "外语", "母语", "历史", "神秘学", "急救", "聆听", "心理学"]},
    "作家": {"credit": [5, 30], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "心理学", "母语", "神秘学", "说服", "侦查", "聆听", "话术"]},
    "探险家": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["攀爬", "游泳", "导航", "生存", "急救", "射击(步枪/霰弹)", "历史", "外语", "侦查"]},
    "古物学家": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["考古学", "历史", "图书馆使用", "估价", "侦查", "神秘学", "外语", "导航", "汽车驾驶"]},
    "黑客": {"credit": [10, 60], "points": [("EDU",4)],
        "skills": ["计算机使用", "电子学", "图书馆使用", "侦查", "潜行", "妙手", "话术"]},
    "赏金猎人": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["射击(手枪)", "格斗(斗殴)", "侦查", "潜行", "汽车驾驶", "法律", "聆听", "心理学"]},
    "工匠": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["技艺(木工)", "技艺(泥瓦)", "技艺(雕塑)", "机械维修", "会计", "侦查"]},
    "矿工": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(采矿)", "爆破", "攀爬", "机械维修", "急救", "聆听", "操作重型机械"]},
    "渔夫": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["游泳", "驾驶(船)", "导航", "博物学", "机械维修", "急救", "聆听"]},
    "赌徒": {"credit": [5, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["妙手", "心理学", "话术", "侦查", "聆听", "估价", "会计", "恐吓"]},
    "侦探(警务)": {"credit": [20, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["侦查", "聆听", "心理学", "法律", "射击(手枪)", "格斗(斗殴)", "图书馆使用", "说服"]},
    "保镖": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["格斗(斗殴)", "射击(手枪)", "闪避", "聆听", "侦查", "恐吓", "急救", "汽车驾驶"]},
    "司机": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["汽车驾驶", "机械维修", "导航", "侦查", "聆听", "闪避", "急救"]},
    "出租车司机": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["汽车驾驶", "导航", "聆听", "侦查", "话术", "机械维修", "心理学"]},
    "邮差": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["汽车驾驶", "导航", "聆听", "侦查", "攀爬", "闪避", "急救"]},
    "编辑": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "外语", "母语", "心理学", "说服", "侦查", "计算机使用"]},
    "政治家": {"credit": [20, 70], "points": [("EDU",2),("APP",2)],
        "skills": ["说服", "话术", "心理学", "法律", "历史", "聆听", "会计", "外语"]},
    "外交官": {"credit": [30, 80], "points": [("EDU",4)],
        "skills": ["外语", "母语", "历史", "法律", "说服", "心理学", "聆听", "会计"]},
    "社工": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["心理学", "说服", "聆听", "急救", "法律", "图书馆使用", "侦查"]},
    "翻译": {"credit": [10, 50], "points": [("EDU",4)],
        "skills": ["外语", "母语", "图书馆使用", "历史", "聆听", "心理学", "说服"]},
    "考古学家": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["考古学", "历史", "图书馆使用", "侦查", "估价", "外语", "导航", "攀爬"]},
    "地质学家": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["科学(地质学)", "科学(化学)", "图书馆使用", "导航", "攀爬", "侦查", "爆破"]},
    "生物学家": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["科学(生物学)", "科学(化学)", "图书馆使用", "医学", "侦查", "外语"]},
    "化学家": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["科学(化学)", "科学(药学)", "图书馆使用", "侦查", "外语", "急救"]},
    "物理学家": {"credit": [20, 70], "points": [("EDU",4)],
        "skills": ["科学(物理学)", "科学(数学)", "图书馆使用", "计算机使用", "侦查"]},
    "天文学家": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["科学(天文学)", "科学(数学)", "图书馆使用", "计算机使用", "导航"]},
    "数学家": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["科学(数学)", "会计", "计算机使用", "图书馆使用", "侦查"]},
    "气象学家": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["科学(气象学)", "科学(数学)", "计算机使用", "导航", "图书馆使用"]},
    "兽医": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["科学(动物学)", "医学", "急救", "动物驯养", "博物学", "侦查"]},
    "动物园管理员": {"credit": [10, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["动物驯养", "博物学", "急救", "攀爬", "侦查", "聆听"]},
    "农场主": {"credit": [20, 60], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(耕作)", "动物驯养", "会计", "机械维修", "驾驶(马车)", "博物学"]},
    "园艺师": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["技艺(耕作)", "博物学", "科学(生物学)", "会计", "侦查"]},
    "厨师": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(烹饪)", "估价", "会计", "聆听", "侦查", "心理学", "急救"]},
    "侍者": {"credit": [5, 20], "points": [("EDU",2),("APP",2)],
        "skills": ["聆听", "话术", "心理学", "侦查", "闪避", "技艺(烹饪)"]},
    "酒保": {"credit": [5, 30], "points": [("EDU",2),("APP",2)],
        "skills": ["聆听", "话术", "心理学", "侦查", "格斗(斗殴)", "技艺(烹饪)"]},
    "理发师": {"credit": [5, 25], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(任一)", "话术", "聆听", "侦查", "心理学", "妙手"]},
    "裁缝": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(任一)", "会计", "估价", "侦查", "聆听"]},
    "木匠": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(木工)", "机械维修", "会计", "估价", "侦查", "攀爬"]},
    "水管工": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(管道)", "机械维修", "会计", "估价", "侦查", "攀爬"]},
    "电工": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["电气维修", "电子学", "机械维修", "会计", "侦查", "攀爬"]},
    "机械师": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["机械维修", "电气维修", "操作重型机械", "汽车驾驶", "会计", "侦查"]},
    "焊工": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(木工)", "机械维修", "会计", "侦查", "攀爬", "急救"]},
    "印刷工": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(打字)", "机械维修", "会计", "侦查", "聆听"]},
    "摄影师(记者)": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(摄影)", "侦查", "潜行", "话术", "聆听", "心理学"]},
    "艺术评论家": {"credit": [10, 50], "points": [("EDU",4)],
        "skills": ["估价", "历史", "图书馆使用", "外语", "说服", "侦查"]},
    "拍卖师": {"credit": [20, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["估价", "话术", "说服", "心理学", "会计", "历史"]},
    "古董商": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["估价", "历史", "会计", "图书馆使用", "话术", "侦查", "神秘学"]},
    "珠宝商": {"credit": [20, 60], "points": [("EDU",2),("DEX",2)],
        "skills": ["估价", "会计", "妙手", "侦查", "聆听", "历史"]},
    "银行家": {"credit": [40, 80], "points": [("EDU",4)],
        "skills": ["会计", "法律", "说服", "心理学", "图书馆使用", "估价"]},
    "股票经纪人": {"credit": [30, 80], "points": [("EDU",4)],
        "skills": ["会计", "话术", "心理学", "说服", "聆听", "计算机使用"]},
    "保险调查员": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["会计", "法律", "侦查", "聆听", "心理学", "说服", "图书馆使用"]},
    "拍卖行职员": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["估价", "会计", "图书馆使用", "历史", "话术", "侦查"]},
    "海关职员": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["法律", "侦查", "聆听", "外语", "会计", "心理学"]},
    "监狱看守": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["格斗(斗殴)", "侦查", "聆听", "恐吓", "心理学", "急救", "法律"]},
    "保安": {"credit": [10, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["格斗(斗殴)", "侦查", "聆听", "射击(手枪)", "闪避", "急救", "汽车驾驶"]},
    "保镖(私人)": {"credit": [20, 60], "points": [("EDU",2),("STR",2)],
        "skills": ["格斗(斗殴)", "射击(手枪)", "闪避", "侦查", "聆听", "恐吓", "汽车驾驶"]},
    "佣兵": {"credit": [10, 60], "points": [("EDU",2),("STR",2)],
        "skills": ["射击(步枪/霰弹)", "格斗(斗殴)", "闪避", "潜行", "生存", "急救", "爆破", "导航"]},
    "狙击手": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["射击(步枪/霰弹)", "潜行", "侦查", "聆听", "生存", "导航", "急救"]},
    "特工": {"credit": [20, 60], "points": [("EDU",2),("DEX",2)],
        "skills": ["射击(手枪)", "潜行", "侦查", "聆听", "话术", "心理学", "乔装", "外语"]},
    "间谍": {"credit": [20, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["乔装", "话术", "心理学", "侦查", "聆听", "外语", "潜行", "妙手"]},
    "赏金猎人(西部)": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["射击(步枪/霰弹)", "骑术", "侦查", "生存", "导航", "急救", "聆听"]},
    "牛仔": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["骑术", "动物驯养", "射击(步枪/霰弹)", "生存", "导航", "急救", "聆听"]},
    "猎人": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["射击(步枪/霰弹)", "潜行", "生存", "导航", "聆听", "博物学", "急救"]},
    "捕兽者": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["生存", "潜行", "博物学", "导航", "聆听", "急救", "攀爬"]},
    "伐木工": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(木工)", "机械维修", "攀爬", "急救", "侦查", "聆听"]},
    "码头工人": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["运动", "攀爬", "操作重型机械", "格斗(斗殴)", "急救", "聆听"]},
    "铁路工人": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["机械维修", "操作重型机械", "攀爬", "急救", "侦查", "聆听"]},
    "矿场主": {"credit": [30, 70], "points": [("EDU",4)],
        "skills": ["会计", "估价", "法律", "操作重型机械", "侦查", "说服"]},
    "马戏团演员": {"credit": [5, 20], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(表演)", "杂技", "攀爬", "跳跃", "闪避", "动物驯养"]},
    "驯兽师": {"credit": [5, 30], "points": [("EDU",2),("APP",2)],
        "skills": ["动物驯养", "博物学", "技艺(表演)", "急救", "聆听", "心理学"]},
    "魔术师": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(表演)", "妙手", "乔装", "话术", "心理学", "侦查"]},
    "占卜师": {"credit": [5, 40], "points": [("EDU",2),("APP",2)],
        "skills": ["神秘学", "话术", "心理学", "聆听", "侦查", "技艺(表演)"]},
    "灵媒": {"credit": [5, 40], "points": [("EDU",4)],
        "skills": ["神秘学", "心理学", "聆听", "话术", "侦查", "技艺(表演)"]},
    "邪教徒": {"credit": [0, 20], "points": [("EDU",2),("POW",2)],
        "skills": ["神秘学", "克苏鲁神话", "外语", "潜行", "聆听", "心理学"]},
    "私家侦探(助手)": {"credit": [10, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["侦查", "聆听", "图书馆使用", "心理学", "汽车驾驶", "闪避"]},
    "警探": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["侦查", "聆听", "心理学", "法律", "射击(手枪)", "格斗(斗殴)", "说服", "图书馆使用"]},
    "法医": {"credit": [30, 60], "points": [("EDU",4)],
        "skills": ["医学", "科学(生物学)", "科学(化学)", "侦查", "急救", "图书馆使用"]},
    "验尸官": {"credit": [30, 60], "points": [("EDU",4)],
        "skills": ["医学", "科学(生物学)", "法律", "侦查", "急救", "心理学"]},
    "急救员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["急救", "医学", "汽车驾驶", "聆听", "侦查", "闪避", "攀爬"]},
    "护理员": {"credit": [10, 30], "points": [("EDU",4)],
        "skills": ["急救", "医学", "聆听", "心理学", "侦查", "说服"]},
    "助产士": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["医学", "急救", "心理学", "聆听", "说服", "科学(生物学)"]},
    "药剂师助理": {"credit": [10, 30], "points": [("EDU",4)],
        "skills": ["科学(药学)", "会计", "急救", "图书馆使用", "侦查"]},
    "牙医": {"credit": [30, 70], "points": [("EDU",4)],
        "skills": ["医学", "急救", "科学(生物学)", "会计", "侦查"]},
    "按摩师": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["医学", "急救", "聆听", "心理学", "说服", "技艺(任一)"]},
    "教练": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["运动", "急救", "心理学", "说服", "聆听", "侦查"]},
    "运动员": {"credit": [10, 50], "points": [("EDU",2),("STR",2)],
        "skills": ["运动", "闪避", "跳跃", "游泳", "攀爬", "急救", "聆听"]},
    "拳击教练": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["格斗(斗殴)", "运动", "闪避", "急救", "心理学", "聆听"]},
    "登山向导": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["攀爬", "导航", "生存", "急救", "博物学", "聆听"]},
    "潜水员": {"credit": [10, 40], "points": [("EDU",2),("CON",2)],
        "skills": ["潜水", "游泳", "机械维修", "急救", "侦查", "导航"]},
    "救生员": {"credit": [5, 30], "points": [("EDU",2),("CON",2)],
        "skills": ["游泳", "急救", "聆听", "侦查", "闪避", "运动"]},
    "消防队长": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["急救", "攀爬", "操作重型机械", "侦查", "说服", "心理学", "驾驶(马车)"]},
    "拆弹专家": {"credit": [20, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["爆破", "电气维修", "电子学", "侦查", "急救", "闪避"]},
    "军械师": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["机械维修", "射击(步枪/霰弹)", "爆破", "会计", "侦查"]},
    "试飞员": {"credit": [20, 60], "points": [("EDU",2),("DEX",2)],
        "skills": ["驾驶(飞机)", "导航", "机械维修", "科学(气象学)", "急救"]},
    "船长": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["导航", "驾驶(船)", "游泳", "机械维修", "说服", "聆听", "急救"]},
    "灯塔看守": {"credit": [5, 30], "points": [("EDU",2),("CON",2)],
        "skills": ["侦查", "聆听", "机械维修", "导航", "急救", "博物学"]},
    "捕鲸人": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["驾驶(船)", "游泳", "投掷", "格斗(斗殴)", "急救", "导航"]},
    "走私犯": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["潜行", "话术", "驾驶(船)", "妙手", "侦查", "聆听", "法律"]},
    "盗贼": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["锁匠", "潜行", "妙手", "闪避", "侦查", "聆听", "攀爬"]},
    "扒手": {"credit": [0, 20], "points": [("EDU",2),("DEX",2)],
        "skills": ["妙手", "潜行", "闪避", "侦查", "聆听", "话术"]},
    "诈骗犯": {"credit": [10, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["话术", "说服", "心理学", "乔装", "妙手", "会计", "法律"]},
    "伪造师": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(技术制图)", "技艺(打字)", "妙手", "估价", "会计", "侦查"]},
    "收赃人": {"credit": [10, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["估价", "话术", "聆听", "侦查", "心理学", "会计"]},
    "黑市商人": {"credit": [20, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["话术", "估价", "会计", "聆听", "侦查", "心理学"]},
    "毒贩": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["潜行", "话术", "侦查", "聆听", "妙手", "心理学"]},
    "赌场庄家": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["妙手", "心理学", "侦查", "聆听", "会计", "话术"]},
    "职业赌徒": {"credit": [5, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["妙手", "心理学", "话术", "侦查", "聆听", "估价"]},
    "私家赌局老板": {"credit": [20, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["话术", "心理学", "会计", "侦查", "聆听", "法律"]},
    "高利贷者": {"credit": [20, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["会计", "话术", "心理学", "恐吓", "侦查", "法律"]},
    "律师助理": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["法律", "图书馆使用", "会计", "聆听", "侦查", "说服"]},
    "法院书记员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["法律", "技艺(速记)", "技艺(打字)", "图书馆使用", "聆听"]},
    "公证人": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["法律", "会计", "图书馆使用", "聆听", "侦查", "说服"]},
    "税务员": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["会计", "法律", "侦查", "聆听", "心理学", "说服"]},
    "审计员": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["会计", "法律", "侦查", "图书馆使用", "心理学", "计算机使用"]},
    "银行柜员": {"credit": [10, 40], "points": [("EDU",2),("APP",2)],
        "skills": ["会计", "聆听", "话术", "侦查", "计算机使用"]},
    "出纳": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["会计", "聆听", "侦查", "计算机使用", "估价"]},
    "记账员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["会计", "图书馆使用", "侦查", "计算机使用", "聆听"]},
    "打字员": {"credit": [5, 25], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(打字)", "技艺(速记)", "聆听", "侦查", "会计"]},
    "速记员": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(速记)", "技艺(打字)", "聆听", "侦查", "心理学"]},
    "档案管理员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "会计", "侦查", "聆听", "计算机使用"]},
    "资料员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["图书馆使用", "计算机使用", "侦查", "会计", "外语"]},
    "新闻编辑": {"credit": [20, 60], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "心理学", "说服", "聆听", "侦查", "母语"]},
    "战地记者": {"credit": [10, 50], "points": [("EDU",2),("CON",2)],
        "skills": ["侦查", "聆听", "潜行", "急救", "摄影", "话术", "历史"]},
    "摄影记者": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(摄影)", "侦查", "潜行", "话术", "聆听", "急救"]},
    "专栏作家": {"credit": [10, 50], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "心理学", "母语", "说服", "侦查"]},
    "小说家": {"credit": [5, 40], "points": [("EDU",4)],
        "skills": ["图书馆使用", "历史", "心理学", "母语", "神秘学", "聆听"]},
    "诗人": {"credit": [0, 30], "points": [("EDU",4)],
        "skills": ["母语", "历史", "图书馆使用", "心理学", "说服", "技艺(任一)"]},
    "剧作家": {"credit": [5, 40], "points": [("EDU",4)],
        "skills": ["母语", "历史", "心理学", "技艺(表演)", "图书馆使用"]},
    "编剧": {"credit": [10, 50], "points": [("EDU",4)],
        "skills": ["母语", "历史", "心理学", "技艺(表演)", "说服"]},
    "导演": {"credit": [10, 60], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(表演)", "说服", "心理学", "聆听", "侦查", "历史"]},
    "制片人": {"credit": [20, 70], "points": [("EDU",2),("APP",2)],
        "skills": ["会计", "说服", "话术", "心理学", "法律", "侦查"]},
    "场记": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(速记)", "聆听", "侦查", "技艺(摄影)"]},
    "灯光师": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["电气维修", "机械维修", "攀爬", "侦查", "聆听"]},
    "化妆师": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["乔装", "技艺(任一)", "话术", "聆听", "心理学"]},
    "服装师": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(任一)", "乔装", "估价", "会计", "侦查"]},
    "布景师": {"credit": [10, 40], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(木工)", "技艺(绘画)", "机械维修", "估价", "侦查"]},
    "漫画家": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(绘画)", "母语", "历史", "心理学", "侦查"]},
    "插画家": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(绘画)", "估价", "侦查", "聆听", "技艺(任一)"]},
    "雕塑家": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(雕塑)", "估价", "侦查", "聆听", "技艺(任一)"]},
    "陶艺师": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(雕塑)", "估价", "会计", "侦查"]},
    "珠宝匠": {"credit": [10, 50], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(任一)", "估价", "会计", "侦查", "聆听"]},
    "钟表匠": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["机械维修", "技艺(任一)", "估价", "会计", "侦查"]},
    "乐师": {"credit": [5, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(乐器)", "聆听", "心理学", "技艺(表演)", "历史"]},
    "歌手": {"credit": [5, 40], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(表演)", "技艺(乐器)", "话术", "聆听", "心理学"]},
    "舞者": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(表演)", "运动", "闪避", "聆听", "心理学"]},
    "杂耍艺人": {"credit": [5, 20], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(表演)", "妙手", "杂技", "投掷", "闪避"]},
    "小丑": {"credit": [5, 25], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(表演)", "杂技", "话术", "心理学", "闪避"]},
    "街头艺人": {"credit": [0, 15], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(表演)", "技艺(乐器)", "话术", "聆听", "闪避"]},
    "乞丐": {"credit": [0, 5], "points": [("EDU",2),("DEX",2)],
        "skills": ["潜行", "聆听", "侦查", "话术", "闪避", "生存"]},
    "拾荒者": {"credit": [0, 10], "points": [("EDU",2),("CON",2)],
        "skills": ["侦查", "聆听", "生存", "机械维修", "潜行", "估价"]},
    "废品商": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["估价", "会计", "机械维修", "聆听", "侦查", "话术"]},
    "二手商": {"credit": [10, 40], "points": [("EDU",2),("APP",2)],
        "skills": ["估价", "会计", "话术", "聆听", "侦查", "心理学"]},
    "当铺老板": {"credit": [20, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["估价", "会计", "话术", "聆听", "侦查", "法律"]},
    "典当师": {"credit": [20, 50], "points": [("EDU",4)],
        "skills": ["估价", "会计", "法律", "聆听", "侦查", "历史"]},
    "书商": {"credit": [10, 50], "points": [("EDU",4)],
        "skills": ["估价", "会计", "图书馆使用", "历史", "外语", "侦查"]},
    "旧书商": {"credit": [5, 40], "points": [("EDU",4)],
        "skills": ["估价", "图书馆使用", "历史", "神秘学", "外语", "侦查"]},
    "报童": {"credit": [0, 10], "points": [("EDU",2),("DEX",2)],
        "skills": ["聆听", "侦查", "闪避", "话术", "攀爬"]},
    "信使": {"credit": [5, 25], "points": [("EDU",2),("DEX",2)],
        "skills": ["闪避", "潜行", "聆听", "侦查", "攀爬", "汽车驾驶"]},
    "快递员": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["汽车驾驶", "导航", "聆听", "侦查", "闪避"]},
    "搬运工": {"credit": [5, 25], "points": [("EDU",2),("STR",2)],
        "skills": ["运动", "攀爬", "操作重型机械", "急救", "聆听"]},
    "仓库管理员": {"credit": [10, 35], "points": [("EDU",2),("STR",2)],
        "skills": ["会计", "操作重型机械", "侦查", "聆听", "机械维修"]},
    "调度员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["聆听", "计算机使用", "侦查", "说服", "心理学"]},
    "话务员": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["聆听", "电子学", "话术", "侦查", "计算机使用"]},
    "电报员": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(打字)", "电子学", "聆听", "侦查", "技艺(速记)"]},
    "无线电操作员": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["电子学", "电气维修", "聆听", "侦查", "计算机使用"]},
    "工程师助理": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["机械维修", "电气维修", "技艺(技术制图)", "会计", "侦查"]},
    "制图员": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(技术制图)", "科学(数学)", "图书馆使用", "侦查"]},
    "测量员": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(技术制图)", "科学(数学)", "导航", "攀爬", "侦查"]},
    "建筑工": {"credit": [5, 30], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(泥瓦)", "攀爬", "操作重型机械", "急救", "聆听"]},
    "油漆工": {"credit": [5, 30], "points": [("EDU",2),("DEX",2)],
        "skills": ["技艺(绘画)", "攀爬", "估价", "侦查", "聆听"]},
    "清洁工": {"credit": [0, 15], "points": [("EDU",2),("CON",2)],
        "skills": ["潜行", "聆听", "侦查", "闪避", "估价"]},
    "门房": {"credit": [5, 25], "points": [("EDU",2),("STR",2)],
        "skills": ["聆听", "侦查", "心理学", "格斗(斗殴)", "急救"]},
    "管家": {"credit": [10, 40], "points": [("EDU",4)],
        "skills": ["聆听", "侦查", "心理学", "会计", "技艺(烹饪)", "说服"]},
    "女仆": {"credit": [5, 25], "points": [("EDU",2),("DEX",2)],
        "skills": ["聆听", "侦查", "技艺(烹饪)", "潜行", "心理学"]},
    "厨师长": {"credit": [20, 50], "points": [("EDU",2),("APP",2)],
        "skills": ["技艺(烹饪)", "会计", "说服", "聆听", "估价"]},
    "园丁": {"credit": [5, 25], "points": [("EDU",2),("STR",2)],
        "skills": ["技艺(耕作)", "博物学", "机械维修", "聆听", "侦查"]},
    "司机(私人)": {"credit": [10, 40], "points": [("EDU",2),("DEX",2)],
        "skills": ["汽车驾驶", "机械维修", "聆听", "侦查", "闪避"]},
    "保镖司机": {"credit": [15, 45], "points": [("EDU",2),("STR",2)],
        "skills": ["汽车驾驶", "格斗(斗殴)", "射击(手枪)", "侦查", "聆听", "闪避"]},
}

def derive(attrs, age=25, mythos=0):
    """按 COC 7th 计算派生属性，含年龄修正。"""
    a = {k: int(attrs.get(k, 50)) for k, _ in ATTRS}
    str_, con, siz, dex, app, int_, pow_, edu = [a[k] for k, _ in ATTRS]

    edu_pen = 0
    app_pen = 0
    str_pen = 0
    con_pen = 0
    dex_pen = 0
    move_pen = 0
    if 40 <= age < 50:
        edu_pen = 5; app_pen = 5; str_pen = 5; con_pen = 5; dex_pen = 5
    elif 50 <= age < 60:
        edu_pen = 10; app_pen = 10; str_pen = 10; con_pen = 10; dex_pen = 10; move_pen = 1
    elif 60 <= age < 70:
        edu_pen = 20; app_pen = 15; str_pen = 20; con_pen = 20; dex_pen = 20; move_pen = 2
    elif 70 <= age < 80:
        edu_pen = 40; app_pen = 20; str_pen = 40; con_pen = 30; dex_pen = 30; move_pen = 3
    elif age >= 80:
        edu_pen = 80; app_pen = 25; str_pen = 80; con_pen = 40; dex_pen = 40; move_pen = 4

    eff = dict(a)
    eff["EDU"] = max(1, edu - edu_pen)
    eff["APP"] = max(1, app - app_pen)
    eff["STR"] = max(1, str_ - str_pen)
    eff["CON"] = max(1, con - con_pen)
    eff["DEX"] = max(1, dex - dex_pen)

    hp_max = (eff["CON"] + eff["SIZ"]) // 10
    mp_max = eff["POW"] // 5
    san_start = eff["POW"]
    san_max = max(0, 99 - int(mythos or 0))
    san_now = min(san_start, san_max)

    move = 8
    if eff["DEX"] < eff["SIZ"] and eff["STR"] < eff["SIZ"]:
        move = 7
    elif eff["STR"] > eff["SIZ"] and eff["DEX"] > eff["SIZ"]:
        move = 9
    move = max(1, move - move_pen)

    db_build = eff["STR"] + eff["SIZ"]
    if db_build <= 64:
        dmg_bonus, build = "-2", -2
    elif db_build <= 84:
        dmg_bonus, build = "-1", -1
    elif db_build <= 124:
        dmg_bonus, build = "0", 0
    elif db_build <= 164:
        dmg_bonus, build = "+1d4", 1
    elif db_build <= 204:
        dmg_bonus, build = "+1d6", 2
    else:
        dmg_bonus, build = "+2d6", 3

    luck = random.randint(1, 100) if luck_unset(attrs) else int(attrs.get("LUCK", 50))

    return {
        "eff": eff,
        "HP": hp_max, "HP_max": hp_max,
        "MP": mp_max, "MP_max": mp_max,
        "SAN": san_now, "SAN_max": san_max, "SAN_start": san_start,
        "MOV": move, "DB": dmg_bonus, "BUILD": build,
        "LUCK": luck,
    }

def luck_unset(attrs):
    return "LUCK" not in attrs or not attrs.get("LUCK")


def blank_card(name="新角色"):
    attrs = {k: 50 for k, _ in ATTRS}
    skills = {}
    for cn, key, base, cat in SKILLS:
        skills[key] = {"name": cn, "base": base, "value": base, "cat": cat}
    d = derive(attrs, 25, 0)
    return {
        "id": "c" + str(int(time.time() * 1000)) + str(random.randint(100, 999)),
        "name": name,
        "player": "",
        "occupation": "",
        "age": 25,
        "gender": "",
        "residence": "",
        "birthplace": "",
        "portrait": "",
        "attrs": attrs,
        "skills": skills,
        "derived": d,
        "mythos": 0,
        "hp": d["HP"], "mp": d["MP"], "san": d["SAN"], "luck": d["LUCK"],
        "background": {
            "description": "", "ideology": "", "significant_people": "",
            "meaningful_locations": "", "treasured_possessions": "",
            "traits": "", "injuries": "", "phobias": "", "arcane_tomes": ""
        },
        "equipment": [],
        "notes": "",
        "relations": [],
        "created": time.time(),
        "updated": time.time(),
    }

# ---------- 随机生成 ----------
FIRST_NAMES = ["亚瑟", "玛戈", "朱利安", "艾德", "卡兰", "伊莎", "康拉德", "海伦", "奥古斯特", "薇拉",
               "亨利", "露西", "塞缪尔", "艾格尼丝", "埃德加", "多萝西"]
LAST_NAMES = ["布莱克伍德", "维尔", "科尔", "凯恩", "哈罗德", "温特斯", "格雷", "莫里斯",
              "阿什福德", "坎贝尔", "德拉蒙德", "费尔柴尔德"]

TRAITS = ["沉默寡言，但对承诺极为认真", "好奇心压过恐惧", "习惯用玩笑掩饰紧张",
          "对旧物有近乎偏执的收藏欲", "相信一切都有科学解释", "受过伤，但不肯说在哪里",
          "说话时总在观察对方的反应", "极度守时，讨厌任何形式的迟到"]

IDEOLOGY = ["真相必须被揭开，无论代价", "活着回来比什么都重要", "我有责任保护那些不知道真相的人",
             "知识是唯一的救赎", "我不欠任何人，包括神"]


def random_card(occupation=None):
    """随机角色卡。技能加点严格按职业点预算分配，不超池子。"""
    occ = occupation or random.choice(list(OCCUPATIONS.keys()))
    age = random.choice([22, 25, 28, 30, 32, 35, 38, 42, 45, 50, 55, 62])
    attrs = {}
    for k, _ in ATTRS:
        attrs[k] = roll_attr(k)
    attrs["LUCK"] = random.randint(3, 18) * 5

    card = blank_card(random.choice(FIRST_NAMES) + "·" + random.choice(LAST_NAMES))
    card["attrs"] = attrs
    card["age"] = age
    card["occupation"] = occ
    d = derive(attrs, age, 0)
    card["derived"] = d

    sk = card["skills"]
    # 母语与闪避：基础值本身就随属性走，直接改 base 与 value，不算加点
    sk["language_own"]["base"] = d["eff"]["EDU"]
    sk["language_own"]["value"] = d["eff"]["EDU"]
    sk["dodge"]["base"] = d["eff"]["DEX"] // 2
    sk["dodge"]["value"] = d["eff"]["DEX"] // 2

    occ_def = OCCUPATIONS[occ]
    pf = occ_def.get("points") or [("EDU", 4)]
    budget = sum(int(attrs.get(k, 0) or 0) * m for k, m in pf)

    # 信用评级先占职业点
    lo, hi = occ_def.get("credit") or [0, 0]
    cr = random.randint(lo, hi)
    sk["credit_rating"]["occ_add"] = cr
    sk["credit_rating"]["value"] = cr
    left = max(0, budget - cr)

    # 职业技能：预算内分配
    key_by_name = {}
    for key, rec in sk.items():
        key_by_name[rec.get("name")] = key
    for sname in occ_def["skills"]:
        if left <= 0:
            break
        key = key_by_name.get(sname)
        if not key:
            continue
        rec = sk[key]
        base_v = int(rec.get("base") or 0)
        room = max(0, 70 - base_v)
        if room <= 0:
            continue
        want = min(random.randint(40, 60), room, left)
        if want <= 0:
            continue
        rec["occ_add"] = int(rec.get("occ_add") or 0) + want
        rec["value"] = base_v + rec["occ_add"]
        left -= want

    # 剩下的一点点兴趣点也撒到非职业技能上
    int_left = int(attrs.get("INT", 0) or 0) * 2
    occ_names = set(occ_def["skills"])
    others = [k for k, r in sk.items()
              if r.get("name") not in occ_names and k != "credit_rating"]
    random.shuffle(others)
    for key in others:
        if int_left <= 0:
            break
        rec = sk[key]
        base_v = int(rec.get("base") or 0)
        room = max(0, 70 - base_v)
        if room <= 0:
            continue
        give = min(random.randint(10, 30), room, int_left)
        if give <= 0:
            continue
        rec["int_add"] = int(rec.get("int_add") or 0) + give
        rec["value"] = base_v + rec["int_add"]
        int_left -= give

    card["hp"] = d["HP"]
    card["mp"] = d["MP"]
    card["san"] = d["SAN"]
    card["luck"] = attrs["LUCK"]
    card["background"]["traits"] = random.choice(TRAITS)
    card["background"]["ideology"] = random.choice(IDEOLOGY)
    card["equipment"] = []
    card["updated"] = time.time()
    return card

def cards_dir():
    CARDS.mkdir(parents=True, exist_ok=True)
    return CARDS


def list_cards():
    out = []
    for p in sorted(cards_dir().glob("*.json")):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": c.get("id", p.stem), "name": c.get("name", "?"),
                        "occupation": c.get("occupation", ""), "age": c.get("age", 0),
                        "hp": c.get("hp"), "san": c.get("san"), "file": p.name})
        except Exception:
            continue
    return out


def save_card(card):
    card["updated"] = time.time()
    cid = str(card.get("id") or ("c" + str(int(time.time() * 1000))))
    card["id"] = cid
    p = cards_dir() / (cid + ".json")
    p.write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    return cid


def load_card(cid):
    p = cards_dir() / (str(cid) + ".json")
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def delete_card(cid):
    p = cards_dir() / (str(cid) + ".json")
    if p.exists():
        p.unlink()
        return True
    return False


def recalc(card):
    """改了属性/年龄后重算派生值，并把 HP/MP/SAN 夹到上限内。"""
    mythos = int(card.get("mythos") or 0)
    d = derive(card.get("attrs", {}), int(card.get("age") or 25), mythos)
    card["derived"] = d
    card["hp"] = min(int(card.get("hp") or d["HP"]), d["HP_max"])
    card["mp"] = min(int(card.get("mp") or d["MP"]), d["MP_max"])
    card["san"] = min(int(card.get("san") or d["SAN"]), d["SAN_max"])
    card["luck"] = int(card.get("luck") or d["LUCK"])
    return card


# ---------- 与跑团上下文对接 ----------
def card_to_context(card):
    """把角色卡压成一段喂给 KP 的文本，控制 token。"""
    if not card:
        return ""
    a = card.get("attrs", {})
    d = card.get("derived", {})
    eff = d.get("eff", {})
    L2 = ["## 玩家角色：" + str(card.get("name", ""))]
    if card.get("occupation"):
        L2.append("- 职业：" + str(card["occupation"]) + "　年龄：" + str(card.get("age", "")))
    L2.append("- 属性：" + " / ".join(k + " " + str(eff.get(k, a.get(k, 0))) for k, _ in ATTRS))
    L2.append("- HP " + str(card.get("hp")) + "/" + str(d.get("HP_max")) +
              "　MP " + str(card.get("mp")) + "/" + str(d.get("MP_max")) +
              "　SAN " + str(card.get("san")) + "/" + str(d.get("SAN_max")) +
              "　幸运 " + str(card.get("luck")))
    L2.append("- 伤害加成 " + str(d.get("DB")) + "　体格 " + str(d.get("BUILD")) +
              "　移动 " + str(d.get("MOV")))
    sk = card.get("skills", {})
    good = [(r["name"], r["value"]) for r in sk.values() if int(r.get("value", 0)) >= 50]
    good.sort(key=lambda x: -x[1])
    if good:
        L2.append("- 擅长：" + "、".join(n + " " + str(v) for n, v in good[:10]))
    bg = card.get("background", {})
    for k, label in (("traits", "性格"), ("ideology", "信条"), ("phobias", "恐惧"),
                     ("injuries", "旧伤")):
        if bg.get(k):
            L2.append("- " + label + "：" + str(bg[k]))
    if card.get("equipment"):
        L2.append("- 携带：" + "、".join(str(x) for x in card["equipment"][:12]))
    return NL.join(L2)