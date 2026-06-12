#!/usr/bin/env python3
from __future__ import annotations
"""
PDF Document Splitter
Splits combined scanned PDFs into separate classified documents.
Uses HuggingFace transformers + CUDA (Qwen2.5-VL-32B-Instruct).

Install:
    pip install transformers accelerate qwen-vl-utils pdf2image pypdf pillow
    apt install -y poppler-utils   # needed by pdf2image

Usage:
    python split.py /path/to/folder
    python split.py /path/to/folder --dpi 120
"""

import argparse
import json
import logging
import re
import sys

from dataclasses import dataclass
from pathlib import Path

from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter

from rotation import query_rotation as _query_rotation_impl, smooth_rotation_log


def _load_page(pdf_path: Path, page_num: int, dpi: int):
    """Load a single 1-indexed PDF page as a PIL image."""
    imgs = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_num, last_page=page_num)
    return imgs[0]

MODEL_PATH = "Qwen/Qwen2.5-VL-32B-Instruct"  # 4-bit NF4 → ~18 GB VRAM, ~64 GB disk download (needs 80 GB disk)
CONFIDENCE_THRESHOLD = 0.80  # below this → output file gets _REVIEW suffix

STRONG_SIGNOFF_SIGNALS = {"signature_block", "project_signoff"}

# Signals whose signal_page is the FIRST page of the NEW document (boundary = signal_page - 1)
START_ON_NEXT_SIGNALS = {
    "titled_id_header",
    "fresh_letterhead", "header_block_reset", "appendix_heading",
    "blank_form", "page_number_reset", "stamp_change",
}
# Signals whose signal_page is the LAST page of the CURRENT document (boundary = signal_page)
END_ON_PAGE_SIGNALS = {"signature_block", "project_signoff", "table_end"}

DEFAULT_DPI = 150

# ---------------------------------------------------------------------------
# Nomenclature — Bulgarian construction document classification (382 entries)
# ---------------------------------------------------------------------------
NOMENCLATURE = {
    1000: "Архитектура",
    1001: "Обяснителна записка", 1002: "Количествена сметка", 1003: "Ситуация",
    1004: "Разпределение", 1005: "Разрез", 1006: "Фасада", 1007: "План",
    1008: "Архитектурно заснемане", 1009: "План покрив", 1010: "Заглавна страница",
    1011: "Лиценз", 1012: "Становище", 1013: "Застраховка", 1014: "Изчисления",
    1015: "Детайли", 1999: "Друг вид документ",

    2000: "Конструкции",
    2001: "План изкоп", 2003: "План фундамент", 2004: "Кофражен план",
    2005: "Обяснителна записка", 2006: "Изчисления", 2007: "Оценка от техническия контрол",
    2008: "Светофарна уредба", 2009: "Тръбно-канална мрежа", 2010: "Отводняване",
    2011: "Конструктивно становище", 2012: "Протокол", 2013: "Разрез", 2014: "Армировка",
    2015: "Конструктивен чертеж", 2016: "Заглавна страница", 2017: "Лиценз",
    2018: "Становище", 2019: "Застраховка", 2020: "Извлечения", 2021: "Детайли",
    2022: "Разпределение", 2023: "Конструкция", 2999: "Друг вид документ",

    3000: "Водоснабдяване и канализация",
    3001: "Обяснителна записка", 3002: "Инсталация", 3003: "Аксонометрия",
    3004: "Детайли", 3005: "Ситуация / външни връзки", 3006: "Разпределения",
    3007: "Автоматично пожарогасене",
    3008: "Разрешително за проектиране на ВиК отклонение",
    3009: "Скица", 3010: "Разпределение водопровод", 3011: "Разпределение канализация",
    3012: "Разпределения ВиК", 3013: "Заглавна страница", 3014: "Лиценз",
    3015: "Становище", 3016: "Застраховка", 3017: "Изчисления", 3999: "Друг вид документ",

    4000: "Електричество",
    4001: "Обяснителна записка", 4002: "Схеми ел. табла", 4003: "Ел. инсталация",
    4004: "Мълниеотводна инсталация", 4006: "Външни ел. инсталации",
    4007: "Пожароизвестяване", 4008: "Асансьорни уредби", 4009: "Слаботокови инсталации",
    4010: "Ревизионна книга за асаньор",
    4011: "Предварителен договор за присъединяване",
    4012: "Заглавна страница", 4013: "Лиценз", 4014: "Становище", 4015: "Застраховка",
    4016: "Изчисления", 4017: "Детайли", 4018: "Осветителна ел. инсталация",
    4999: "Друг вид документ",

    5000: "Топлоснабдяване, отопление, вентилация и климатизация",
    5001: "Обяснителна записка", 5002: "Аксонометрия", 5003: "Разпределение",
    5004: "Схема", 5005: "Заглавна страница", 5006: "Лиценз", 5007: "Становище",
    5008: "Застраховка", 5009: "Изчисления", 5010: "Детайли", 5999: "Друг вид документ",

    6000: "Енергийна ефективност",
    6001: "Доклад", 6002: "Оценка от проектант за енергийна ефективност",
    6003: "Сертификат за енергийна ефективност", 6004: "Обяснителна записка",
    6005: "Заглавна страница", 6006: "Лиценз", 6007: "Становище", 6008: "Застраховка",
    6009: "Изчисления", 6010: "Детайли", 6999: "Друг вид документ",

    7000: "Газоснабдяване",
    7001: "Ревизионна книга за съоръжение с повишена опасност (СПО)",
    7002: "Заглавна страница", 7003: "Обяснителна записка", 7004: "Лиценз",
    7005: "Становище", 7006: "Застраховка", 7007: "Изчисления", 7008: "Детайли",
    7009: "Разпределение", 7010: "Чертеж", 7999: "Друг вид документ",

    8000: "Геодезия",
    8001: "Обяснителна записка", 8002: "Количествена сметка", 8003: "Трасировъчен план",
    8004: "Вертикална планировка", 8005: "Картограма на земните маси",
    8006: "Геодезическо заснемане", 8007: "КИИП", 8008: "Заглавна страница",
    8009: "Лиценз", 8010: "Становище", 8011: "Застраховка", 8012: "Изчисления",
    8013: "Детайли", 8014: "Координатен регистър", 8999: "Друг вид документ",

    9000: "Паркоустрояване и благоустрояване",
    9001: "Заповед за премахване на съществуваща дървесна растителност",
    9002: "Справка за картотекираната растителност, съгласно чл. 63, ал. 4 от ЗУТ",
    9003: "Заглавна страница", 9004: "Обяснителна записка", 9005: "Лиценз",
    9006: "Становище", 9007: "Застраховка", 9008: "Изчисления", 9009: "Детайли",
    9010: "Дендрологичен план", 9011: "Посадъчен план", 9012: "Чертеж",
    9999: "Друг вид документ",

    10000: "Технологична",
    10001: "Обяснителна записка", 10002: "Схема", 10003: "Заглавна страница",
    10004: "Лиценз", 10005: "Становище", 10006: "Застраховка", 10007: "Изчисления",
    10008: "Детайли", 10009: "Разпределение", 10999: "Друг вид документ",

    11000: "Пожарна безопасност",
    11001: "Становище", 11002: "Заглавна страница", 11003: "Обяснителна записка",
    11004: "Лиценз", 11005: "Застраховка", 11006: "Изчисления", 11007: "Детайли",
    11008: "Разпределение", 11999: "Друг вид документ",

    12000: "ПБЗ (безопасност и здраве)",
    12001: "Обяснителна записка", 12002: "Временна организация на движение",
    12003: "Работни схеми", 12004: "Организационен план", 12005: "Ситуация",
    12006: "Линеен план график",
    12007: "Становище Хигиенно епидемиологична инспекция",
    12008: "Заглавна страница", 12009: "Лиценз", 12010: "Становище",
    12011: "Застраховка", 12012: "Изчисления", 12013: "Детайли", 12014: "Разпределение",
    12015: "Съгласуване / Становище от МВР - КАТ",
    12999: "Друг вид документ",

    13000: "Организация и безопасност на движението",
    13001: "Заглавна страница", 13002: "Обяснителна записка", 13003: "Лиценз",
    13004: "Становище", 13005: "Застраховка", 13006: "Изчисления", 13007: "Детайли",
    13999: "Друг вид документ",

    14000: "Консервация, реставрация и експониране на недвижимите културни ценности",
    14001: "Заглавна страница", 14002: "Обяснителна записка", 14003: "Лиценз",
    14004: "Становище", 14005: "Застраховка", 14006: "Изчисления", 14007: "Детайли",
    14008: "Разпределение", 14999: "Друг вид документ",

    15000: "Инженерно-геоложко проучване",
    15001: "Доклад", 15002: "Ситуация", 15003: "Инженерногеоложки разрез",
    15004: "Инженерногеоложки профил", 15005: "Заглавна страница",
    15006: "Обяснителна записка", 15007: "Лиценз", 15008: "Становище",
    15009: "Застраховка", 15010: "Изчисления", 15011: "Детайли",
    15999: "Друг вид документ",

    16000: "Преработка по чл. 154",
    16001: "Документи по чл. 154 от ЗУТ",
    16002: "Заповед за допълване на Разрешение за строеж по чл. 154 от ЗУТ",
    16003: "Заглавна страница", 16004: "Обяснителна записка", 16005: "Лиценз",
    16006: "Становище", 16007: "Застраховка", 16008: "Изчисления", 16009: "Детайли",
    16999: "Друг вид документ",

    17000: "Генерален план",
    17001: "Заглавна страница", 17002: "Обяснителна записка", 17003: "Лиценз",
    17004: "Становище", 17005: "Застраховка", 17006: "Изчисления", 17007: "Детайли",
    17999: "Друг вид документ",

    18000: "Сметна документация",
    18001: "Заглавна страница", 18002: "Обяснителна записка", 18003: "Лиценз",
    18004: "Становище", 18005: "Застраховка", 18006: "Изчисления", 18007: "Детайли",
    18999: "Друг вид документ",

    19000: "Документи",
    19001: "Обходен лист", 19002: "Разписен лист", 19003: "Документ за собственост",
    19004: "Пълномощно", 19005: "Обратна разписка",
    19006: "Съгласуване / Становище от Министерство на културата / НИНКН",
    19007: "Съгласуване / Становище от ПБЗН",
    19008: "Съгласуване / Становище от МВР - КАТ",
    19009: "Съгласуване / Становище от РЗИ",
    19010: "Съгласуване / Становище от Басейнова дирекция",
    19011: "Съгласуване / Становище от Общинска собственост",
    19012: "Съгласуване / Становище от ИДТН",
    19013: "Съгласуване / Становище от БАБХ",
    19014: "Съгласуване / Становище от експлоатационни дружества и ведомства",
    19015: "Решения по реда на ЗООС",
    19016: "Решения по реда на ЗБР / Становище от РИОСВ",
    19017: "Изходни данни и условия за присъединяване",
    19018: "Решение на общото събрание за приемане на проекта",
    19019: "Разрешение за строеж (РС)", 19020: "Акт за узаконяване",
    19021: "Разрешително за водовземане / заустване",
    19030: "Нотариално заверена декларация по чл. 73, ал. 2 от ЗУТ",
    19031: "Нотариално заверена декларация по чл. 154, ал. 5 от ЗУТ",
    19032: "Нотариално заверена декларация за право на прокарване",
    19040: "Скица", 19041: "Протокол",
    19050: "Договор за изграждане на техническа инфраструктура",
    19051: "Договор за наем",
    19052: "Договор за поддръжка на асансьорна уредба",
    19053: "Договор по чл. 192 и/или чл. 193 от ЗУТ",
    19054: "Договор с експлоатационните дружества за присъединяване",
    19060: "Документ за собственост / право на строеж",
    19061: "Удостоверение за наследници",
    19062: "Разписна книга", 19063: "Документ от АГКК",
    19064: "Актуална скица с координати от СГКК",
    19070: "Предварителна оценка на идейните проекти по чл. 142, ал. 2 от ЗУТ",
    19071: "Доклад от лицензиран консултант", 19072: "Скица виза", 19073: "Писмо",
    19075: "Други документи / съгласувания по специални закони",
    19076: "Окончателен доклад от строителен надзор по чл. 177, ал. 3 от ЗУТ",
    19077: "Документи, свързани с уведомяване", 19078: "Копие от ПУП",
    19079: "Оценка за съответствие по чл. 142, ал. 6 от ЗУТ",
    19080: "Комплексен доклад",
    19081: "Писмо-Разрешение за промяна на предназначение / преустройство",
    19082: "Проект-заснемане и документи за отстранени отклонения",
    19083: "Протокол за спиране на строежа / Акт образец 10",
    19084: "Протокол на ЕСУТ / РЕСУТ",
    19085: "Протокол за откриване на строителна площадка (образец 2/2а)",
    19086: "Констативен акт за съответствие с строителните книжа (образец 3)",
    19087: "Заверена заповедна книга (образец 4)",
    19088: "Акт за уточняване на строителния терен (образец 5)",
    19089: "Акт за приемане на земната основа (образец 6)",
    19112: "Заповед за разрешаване изработването на ПУП",
    19113: "Заповед за разрешаване изменение на ПУП",
    19114: "Решение за одобряване на изменение на ОУП",
    19115: "Решение за одобряване на изменение на ПУП",
    19116: "Решение за одобряване на ОУП",
    19117: "Решение за одобряване на ПУП",
    19118: "Решение за разрешаване изработването на изменение на ОУП",
    19119: "Решение за разрешаване изработването на изменение на ПУП",
    19120: "Решение за разрешаване изработването на ОУП",
    19121: "Решение за разрешаване изработването на ПУП",
    19122: "Скица от действащия ПУП", 19123: "Извлечение от подземен кадастър",
    19124: "Изходни данни за присъединяване по чл. 144 от ЗУТ",
    19125: "Комбинирана скица",
    19126: "Копие от фактури за платени задължения към експлоатационните дружества",
    19127: "Декларация за съгласие на всички съсобственици",
    19128: "Декларации за съгласие от собственици на съседни УПИ",
    19129: "Одобрен проект за СПО по чл. 56 от ЗУТ",
    19130: "Одобрена схема за поставяне на СПО по чл. 56 от ЗУТ",
    19131: "Опорен план",
    19132: "Предварителен договор за прехвърляне на собственост",
    19133: "Презаверено Разрешение за строеж",
    19134: "Проект за план-извадка по чл. 133, ал. 1 ЗУТ",
    19135: "Проектна документация - Архитектурна част",
    19136: "Проектна документация - Дизайнерска част",
    19137: "Проектна документация - Инженерна част",
    19138: "Протокол от изпитване на пътните пластове",
    19139: "Протоколи от ел. измервания от лицензирана лаборатория",
    19140: "Разрешение за поставяне на преместваеми обекти",
    19141: "Разрешение за промяна на предназначението без СМР",
    19142: "Решение на Областния експертен съвет по чл. 133, ал. 2 ЗУТ",
    19146: "Ситуационен план",
    19147: "Скица-предложение за изменението по чл. 135, ал. 2 от ЗУТ",
    19148: "Служебни бележки от ВиК / НЕК за захранване на обекта",
    19149: "Становища по проекта",
    19150: "Съгласуване / Становище от Областна дирекция Земеделие",
    19151: "Строителни книжа и документи по време на строителството",
    19152: "Схема за рекламна локация",
    19153: "Схема по чл. 11, ал. 2 от НРППОУТДОДЕГОТОП",
    19154: "Съгласуване / Становище от Напоителни системи",
    19155: "Технически паспорт",
    19156: "Удостоверение за актуален административен адрес",
    19157: "Удостоверение за идентичност на наименование на улица",
    19158: "Удостоверение за нов административен адрес",
    19160: "Удостоверение за нанасяне в СКУТ",
    19161: "Удостоверения за нанасяне в СКППС",
    19162: "Удостоверение за търпимост", 19163: "Удостоверение по чл. 65 от ЗКИР",
    19165: "Удостоверение за въвеждане в експлоатация (УВЕ)",
    19166: "Оценка за съответствие по чл. 166, ал. 1, т. 1 от ЗУТ",
    19167: "Молба (Заявление, Искане)", 19168: "Застраховка",
    19169: "Заглавна страница", 19170: "Обяснителна записка", 19171: "Лиценз",
    19172: "Становище", 19173: "Изчисления", 19174: "Детайли", 19175: "Цифрови данни",
    19999: "Друг вид документ",
}


def _build_nomenclature_text() -> str:
    categories: dict = {}
    for code, name in NOMENCLATURE.items():
        cat = (code // 1000) * 1000
        if code == cat:
            categories[cat] = {"name": name, "items": []}
        else:
            if cat not in categories:
                categories[cat] = {"name": f"Категория {cat}", "items": []}
            categories[cat]["items"].append((code, name))

    lines = ["НОМЕНКЛАТУРА (използвай точния код):"]
    for cat, info in sorted(categories.items()):
        items = " | ".join(f"{c} {n}" for c, n in info["items"])
        lines.append(f"{cat} {info['name']}: {items}")
    return "\n".join(lines)


NOMENCLATURE_TEXT = _build_nomenclature_text()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DocumentBoundary:
    page: int
    code: int
    name: str
    confidence: float
    flagged: bool = False
    style_signal: str = ""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pdf_splitter")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    fh = logging.FileHandler(log_dir / "split_log.txt", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def load_model(model_path: str, logger: logging.Logger):
    try:
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
    except ImportError:
        logger.error("transformers / bitsandbytes not installed. Run: pip install transformers accelerate bitsandbytes qwen-vl-utils")
        sys.exit(1)

    logger.info(f"Loading {model_path} (4-bit NF4, first run downloads weights)…")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_path,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model.eval()
    processor = AutoProcessor.from_pretrained(model_path)
    logger.info("Model ready")
    return model, processor, None  # config unused on HF path


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def resolve_code(code: int) -> tuple:
    if code in NOMENCLATURE:
        return code, NOMENCLATURE[code]
    fb = (code // 1000) * 1000 + 999
    if fb not in NOMENCLATURE:
        fb = 19999
    return fb, NOMENCLATURE[fb]


def clean_response(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)
    return text.strip()


def _infer(prompt_text: str, images: list, model, processor, config, logger: logging.Logger, max_tokens: int = 200) -> str | None:
    """Low-level: format prompt and run generate(). Returns raw output string."""
    import torch
    from qwen_vl_utils import process_vision_info
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    *[{"type": "image", "image": img} for img in images],
                    {"type": "text", "text": prompt_text},
                ],
            }
        ]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            padding=True,
            return_tensors="pt",
        ).to("cuda")

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)

        trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated_ids)]
        return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    except Exception as e:
        logger.error(f"  Inference failed: {e}")
        return None


def _extract_int(val, default: int = 19999) -> int:
    """Parse code that may be int 1005 or string '1005 Разрез'."""
    if isinstance(val, int):
        return val
    m = re.match(r"\d+", str(val).strip())
    return int(m.group()) if m else default


def _parse_json(text: str, logger: logging.Logger) -> dict:
    """Strip think/fence tags and parse the first JSON object."""
    text = clean_response(text)
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning(f"  No JSON: {text[:200]}")
        return {}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        logger.warning(f"  JSON parse error ({e}): {text[:200]}")
        return {}


# ---------------------------------------------------------------------------
# Phase 1 — document-end detection (prev + current + next)
# ---------------------------------------------------------------------------

def _query_document_end(images: list, page_nums: list, current_page: int, model, processor, config, logger: logging.Logger) -> tuple:
    """
    Given 2-3 consecutive pages, ask whether current_page ends a document.
    Returns (is_end: bool, confidence: float 0-1, signal: str, signal_on_page: int).
    """
    pages_label = ", ".join(str(p) for p in page_nums)
    prompt = (
        f"You are examining {len(images)} consecutive scanned pages ({pages_label}) "
        "from a Bulgarian construction/building permit archive.\n\n"
        f"Does page {current_page} END a document (i.e. does the next page start a new, "
        "separate document)?\n\n"
        "Check for these signals IN ORDER and report the first one you see:\n\n"
        "STRONG END signals (end=true):\n"
        "  signature_block — the labeled approval grid with 'Изготвил', 'Съгласувал', 'Одобрил' as "
        "printed text labels, AND at least one label has an actual handwritten signature or filled "
        "name/date next to it. CRITICAL: a round organizational stamp (печат / кръгъл печат) appearing "
        "alone at the bottom of a page of narrative text is NOT a signature_block — it must be "
        "accompanied by the labeled approval fields.\n"
        "  project_signoff — labeled fields 'Проектант', 'Изготвил', 'Проверил', 'Технически ръководител' "
        "with an actual handwritten signature or stamp next to each label. "
        "A label with a blank line or empty box is NOT a signoff.\n"
        "  table_end — totals/summary row at bottom of table, no continuation arrow\n\n"
        "STRONG START signals on the NEXT page (end=true):\n"
        "  titled_id_header — the NEXT page BEGINS a document: it opens with a document "
        "title or a letterhead/issuer block at the VERY TOP, AND right next to or just "
        "below that title there is a document-level identifier — a permit number (РС №), "
        "an outgoing/incoming number (изх. № / вх. №), a contract number, or an object/case "
        "number (a '№' followed by digits or a date). You do NOT need to read the identifier "
        "text correctly; it is enough that a number-bearing reference token sits next to the "
        "top title. Do NOT trigger this for: a section/article number inside body text "
        "(чл. 5, т. 3), a figure or drawing number, an appendix label (ПРИЛОЖЕНИЕ №), "
        "a technical drawing's title block — the framed corner/header block on a "
        "чертеж listing ОБЕКТ, ЧАСТ, ФАЗА, МАЩАБ, ЧЕРТЕЖ № or a sheet number: every "
        "sheet in a drawing set carries one of these, so it marks a new SHEET, not a "
        "new document, "
        "an explicit page-counter in the 'X of Y' form with X greater than 1 "
        "(стр. 2 от 2, 2/2, лист 2 от 3): that marks a CONTINUATION page of the "
        "previous document even when the agency letterhead banner repeats at the top "
        "(NOTE: a bare corner numeral alone — just '2' with no 'of Y' — does NOT count, "
        "since a real document start can carry one when its leading pages were not scanned), "
        "a page "
        "number in a corner, or a small running header/footer on a page whose body text "
        "continues the previous page. The identifier must belong to the new document's own "
        "top title block.\n"
        "  fresh_letterhead — different company logo or header block at top of next page\n"
        "  header_block_reset — next page repeats ОБЕКТ / МЕСТОПОЛОЖЕНИЕ / ВЪЗЛОЖИТЕЛ / ЧАСТ as self-contained header\n"
        "  appendix_heading — next page has 'ПРИЛОЖЕНИЕ № X към чл. Y' as standalone bold heading\n"
        "  blank_form — next page is a blank standardized form (all fields empty)\n"
        "  page_number_reset — page numbering resets on next page (e.g. 'стр. 1' or '1' in corner)\n"
        "  stamp_change — the official round stamp (печат) on the next page belongs to a visibly "
        "different organization or issuer than the stamp on the current page "
        "(do NOT use if stamps are absent or look the same)\n\n"
        "WEAK signals (end=true only if strong evidence):\n"
        "  appendix_mid_doc — 'ПРИЛОЖЕНИЕ № X' mid-document\n\n"
        "NOT an end (end=false):\n"
        "  same_letterhead — same letterhead continues\n"
        "  table_continuation — table clearly continues from previous page\n"
        "  stamp_and_date — a stamp or date appears on the current page but stamps appear on "
        "every page of this archive, so this alone means nothing\n"
        "  blank_signature_fields — signature/approval labels present but all fields are empty, "
        "unfilled, or contain only placeholder text like '(име, длъжност, дата, подпис)' — "
        "this is a form template, NOT a document end\n"
        "  none — no signal found\n\n"
        "IMPORTANT: 'signal_on_page' must be the exact page number from the list above "
        "where you actually see the signal. If the signature block is on page 12, write 12, "
        "not 11. Be precise — this is used to place the document boundary correctly.\n\n"
        "Confidence must reflect how clearly YOU see the signal on THIS page — "
        "how legible and unambiguous the evidence is — NOT the signal's category. "
        "A barely-legible stamp or corner page number deserves LOW confidence even "
        "if its signal type is listed as strong.\n\n"
        "Respond ONLY with JSON:\n"
        '{"end": true/false, "signal": "<signal_name>", "signal_on_page": <page_number>, '
        '"confidence": <0-100>, "reason": "<one sentence: exactly what you see that triggered this>"}'
    )
    raw = _infer(prompt, images, model, processor, config, logger, max_tokens=150)
    logger.debug(f"  End-of-doc response p{current_page}: {repr((raw or '')[:300])}")
    data = _parse_json(raw or "", logger)
    is_end = bool(data.get("end", False))
    signal = str(data.get("signal", "none")).lower().strip()
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    reason = str(data.get("reason", "")).strip()
    if reason:
        logger.info(f"  Reason: {reason}")
    force_false = {"table_continuation", "blank_signature_fields", "same_letterhead", "none"}
    if is_end and signal in force_false:
        logger.warning(f"  p{current_page}: end=true with signal={signal} — overriding to false")
        is_end = False
    try:
        signal_page = int(data.get("signal_on_page", current_page))
    except (TypeError, ValueError):
        signal_page = current_page
    # Tier1-#2: window-range validation. The model sometimes names a page OUTSIDE the
    # shown window (e.g. signal_on_page=4 from context [1,2,3]). The old code silently
    # substituted current_page and planted a misplaced boundary (FN3@165204533). Instead
    # re-query ONCE, mapping each image to its real page number and forcing a choice in
    # the window; only if that still fails do we clamp — and then LOUDLY, never silently.
    if is_end and signal_page not in page_nums:
        logger.warning(
            f"  p{current_page}: signal_on_page={signal_page} outside window {page_nums} "
            f"— re-querying with explicit page labels (no silent substitution)"
        )
        signal_page = _requery_signal_page(
            images, page_nums, current_page, signal, model, processor, config, logger
        )
        if signal_page not in page_nums:
            logger.error(
                f"  p{current_page}: re-query STILL returned out-of-window page {signal_page} "
                f"— clamping to {current_page}; boundary placement UNRELIABLE"
            )
            signal_page = current_page
    return is_end, conf, signal, signal_page


def _requery_signal_page(images: list, page_nums: list, current_page: int, signal: str,
                         model, processor, config, logger: logging.Logger) -> int:
    """Tier1-#2: the end-detector named a signal_on_page outside the shown window.
    Re-ask ONCE, mapping each image to its real page number, forcing a choice within the
    window. Returns the page the model picks (caller validates it is in-window and handles
    a persistent miss explicitly — this never silently substitutes current_page)."""
    mapping = "; ".join(f"image {i + 1} = page {p}" for i, p in enumerate(page_nums))
    valid = ", ".join(str(p) for p in page_nums)
    prompt = (
        f"You are shown {len(images)} scanned pages, in this order: {mapping}.\n"
        f"A '{signal}' signal was reported among them. Looking ONLY at these pages, on which "
        f"one do you actually see it? Your answer MUST be one of: {valid}.\n"
        'Respond ONLY with JSON: {"signal_on_page": <page_number>}'
    )
    raw = _infer(prompt, images, model, processor, config, logger, max_tokens=40)
    data = _parse_json(raw or "", logger)
    try:
        picked = int(data.get("signal_on_page", current_page))
    except (TypeError, ValueError):
        picked = current_page
    logger.info(f"  [WINDOW-REQUERY] '{signal}' re-placed on page {picked} (window {page_nums})")
    return picked


def _query_transcribe_title(img, page_num: int, model, processor, config, logger: logging.Logger) -> tuple:
    """Tier2-#4: anti-hallucination gate for titled_id_header. Asks the model to READ
    (transcribe) rather than JUDGE — the 32B confabulates a РС№/title when concluding a
    boundary, far less when transcribing. The shared end-detection prompt is untouched
    (no detection bleed). Returns (title, identifier); each is 'none' when absent."""
    prompt = (
        f"This is page {page_num} of a scanned Bulgarian construction-archive document.\n"
        "Look ONLY at the TOP QUARTER of the page. Transcribe VERBATIM, exactly as printed "
        "(do NOT paraphrase, infer, translate, or complete a number you cannot fully read):\n"
        "  1. Any document TITLE shown as a heading at the very top (e.g. РАЗРЕШЕНИЕ ЗА СТРОЕЖ, "
        "СКИЦА, УДОСТОВЕРЕНИЕ, ПРОТОКОЛ, ЗАПОВЕД, СТАНОВИЩЕ).\n"
        "  2. Any document-level IDENTIFIER next to or just under that title — a permit number "
        "(РС №), an outgoing/incoming number (изх. № / вх. №), a contract or case number: a № "
        "followed by digits or a date.\n"
        "If a title heading is NOT present in the top quarter, answer title \"none\". "
        "If an identifier is NOT present, answer identifier \"none\". A section/article number "
        "(чл. 5), a figure/sheet number, or a bare page-corner numeral is NOT a document identifier.\n\n"
        'Respond ONLY with JSON: {"title": "<verbatim or none>", "identifier": "<verbatim or none>"}'
    )
    raw = _infer(prompt, [img], model, processor, config, logger, max_tokens=120)
    data = _parse_json(raw or "", logger)
    title = str(data.get("title", "none")).strip()
    ident = str(data.get("identifier", "none")).strip()
    return title, ident


# ---------------------------------------------------------------------------
# Phase 1b — appendix standalone check
# ---------------------------------------------------------------------------

def _query_is_standalone(images: list, page_nums: list, candidate_page: int, model, processor, config, logger: logging.Logger) -> tuple:
    """
    Called when an appendix heading triggered a boundary.
    Returns (standalone: bool, confidence: float 0-1).
    Standalone = the appendix has its own signature/approval block.
    Attached   = it shares one with the parent document → suppress the boundary.
    """
    pages_label = ", ".join(str(p) for p in page_nums)
    prompt = (
        f"You are examining pages {pages_label} from a Bulgarian construction archive. "
        f"Page {candidate_page} starts with 'ПРИЛОЖЕНИЕ № ...' (an appendix heading).\n\n"
        "Does this appendix have its OWN independent signature/approval block "
        "('Изготвил' / 'Съгласувал' / 'Одобрил' / round stamp) within its own pages?\n\n"
        "true  = standalone: the appendix has its own signature block → treat as separate document\n"
        "false = attached: it shares a signature block with the parent, or has none of its own "
        "→ keep in the same document\n\n"
        "Respond ONLY with JSON:\n"
        '{"standalone": true/false, "confidence": <0-100>}'
    )
    raw = _infer(prompt, images, model, processor, config, logger, max_tokens=60)
    logger.debug(f"  Standalone check p{candidate_page}: {repr((raw or '')[:200])}")
    data = _parse_json(raw or "", logger)
    standalone = bool(data.get("standalone", True))
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    return standalone, conf


# ---------------------------------------------------------------------------
# Phase 1c — one-page vs closing-page disambiguation + relational start-detection
# ---------------------------------------------------------------------------

def _query_is_self_contained(img_n1, page_n1, model, processor, config, logger) -> tuple:
    """
    Called when signal_on_page == n+1. Asks whether page n+1 is a self-contained
    one-page document (has its own header at top + signature at bottom) or a
    continuation/closing page of the document that precedes it.
    Returns (self_contained: bool, confidence float 0-1).
    """
    prompt = (
        f"Look at page {page_n1}.\n\n"
        f"Is page {page_n1} a SELF-CONTAINED one-page document that starts AND ends here "
        "(e.g. a certificate, single-page permit, license, single-page letter, or insurance "
        "policy that has its own heading/title at the top AND a signature or stamp at the bottom)?\n\n"
        "OR is it a CONTINUATION or CLOSING PAGE of a longer document "
        "(i.e. the last page of a multi-page report showing only the signature section, "
        "with NO new document header at the top of this page)?\n\n"
        f"Key test: does page {page_n1} have its OWN document title, letterhead, or heading "
        "block at the VERY TOP (self-contained), or does it begin mid-content without a new "
        "header (continuation/closing)?\n\n"
        "A signatory/parties section label (e.g. 'СЪДЕЛИТЕЛИ', 'Проектанти'), an appendix "
        "label inside a list, or a numbered section heading is NOT a self-contained document "
        "header. A self-contained one-page document has its OWN document title or "
        "letterhead/issuer block at the very top AND its own signature/stamp at the bottom.\n\n"
        "Respond ONLY with JSON:\n"
        '{"self_contained": true/false, "confidence": <0-100>, '
        '"reason": "<one sentence: what you see at the very top of the page>"}'
    )
    raw = _infer(prompt, [img_n1], model, processor, config, logger, max_tokens=300)
    logger.debug(f"  Self-contained check p{page_n1}: {repr((raw or '')[:300])}")
    data = _parse_json(raw or "", logger)
    self_contained = bool(data.get("self_contained", False))
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    reason = str(data.get("reason", "")).strip()
    logger.info(f"  [ONE-PAGE-CHECK] p{page_n1} self_contained={self_contained} (conf={conf:.0%}): {reason}")
    return self_contained, conf


def _query_starts_new_document(img_prev, img_curr, page_prev, page_curr, model, processor, config, logger) -> tuple:
    """
    Relational two-page query: does page_curr begin a new, separate document
    relative to page_prev? Used by the independent start-detector.
    Returns (starts_new: bool, confidence float 0-1, reason str).
    """
    prompt = (
        f"You are examining two consecutive scanned pages (page {page_prev} and page {page_curr}) "
        "from a Bulgarian construction/building-permit archive. Many separate documents "
        "in this archive share the same scanner, paper, and municipal letterhead, so "
        "visual similarity does NOT by itself mean same document.\n\n"
        f"Decide: does page {page_curr} BEGIN a new, separate document distinct from page {page_prev}?\n\n"
        f"Answer starts_new=true ONLY if page {page_curr} shows a relational change that marks a "
        "new document:\n"
        f"  - a different company/institution letterhead, logo, or issuing authority than "
        f"page {page_prev}; or\n"
        "  - a self-contained document header block at the top (e.g. ОБЕКТ / ВЪЗЛОЖИТЕЛ / "
        "ЧАСТ, or a permit / certificate / contract / insurance title) that resets the "
        f"context rather than continuing page {page_prev}; or\n"
        "  - a clear change of document type or subject (e.g. a permit followed by an "
        "insurance policy, a contract followed by a certificate).\n\n"
        "Answer starts_new=false if:\n"
        f"  - page {page_curr} continues the same letterhead, issuer, and subject as page {page_prev}; or\n"
        f"  - the bold text at the top of page {page_curr} is a SECTION heading or a "
        f"parties/signatory label INSIDE the document already running on page {page_prev} "
        "(for example a numbered section, or labels naming parties, obligations, or "
        "terms of that same document) rather than a new document's title; or\n"
        f"  - page {page_curr} is only a continuation, a table continuation, or a "
        f"signature/stamp closing section of the document on page {page_prev}.\n\n"
        "A heading or bold text ALONE is NOT sufficient. The test is relational: has the "
        f"issuer/letterhead/subject changed from page {page_prev} to page {page_curr}? "
        "If you cannot read the text (scanning/OCR noise), judge from letterhead, logo, "
        "stamp, and layout-block cues.\n\n"
        "Respond ONLY with JSON:\n"
        '{"starts_new": true/false, "confidence": <0-100>, '
        '"reason": "<one sentence naming the relational cue you used>"}'
    )
    raw = _infer(prompt, [img_prev, img_curr], model, processor, config, logger, max_tokens=300)
    logger.debug(f"  Start-detect p{page_prev}→{page_curr}: {repr((raw or '')[:300])}")
    data = _parse_json(raw or "", logger)
    starts_new = bool(data.get("starts_new", False))
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    reason = str(data.get("reason", "")).strip()
    return starts_new, conf, reason


# ---------------------------------------------------------------------------
# Phase 1d — low-confidence boundary confirmation
# ---------------------------------------------------------------------------

def _query_confirm_boundary(img_n, img_n1, page_n, page_n1, model, processor, config, logger: logging.Logger) -> tuple:
    """
    Secondary check for low-confidence boundaries.
    Returns (different_documents: bool, confidence: float).
    """
    prompt = (
        f"Do page {page_n} and page {page_n1} belong to DIFFERENT documents that should be "
        "filed separately?\n\n"
        f"The question is whether page {page_n} COMPLETES one document and page {page_n1} "
        "BEGINS another — not whether they look similar or share the same document type or "
        "issuing organization.\n\n"
        "Two separate INSTANCES of the same document type (e.g. two different invoices, two "
        "different insurance policies, two different certificates — each with its own number "
        "and its own totals or conclusion) ARE different documents and should be filed "
        "separately even if they share the same issuer or visual format.\n\n"
        f"Answer false ONLY if page {page_n1} visibly continues the same table, narrative, or "
        f"document that page {page_n} belongs to (e.g. a table that flows across both pages, "
        f"or a numbered list continuing from page {page_n}).\n\n"
        "Respond ONLY with JSON:\n"
        '{"different_documents": true/false, "confidence": <0-100>}'
    )
    raw = _infer(prompt, [img_n, img_n1], model, processor, config, logger, max_tokens=80)
    logger.debug(f"  Confirm boundary p{page_n}→{page_n1}: {repr((raw or '')[:200])}")
    data = _parse_json(raw or "", logger)
    different = bool(data.get("different_documents", True))
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    return different, conf


# ---------------------------------------------------------------------------
# Phase 1e — style continuity detection
# ---------------------------------------------------------------------------

def _query_style_continuity(img_prev, img_curr, page_prev, page_curr, model, processor, config, logger: logging.Logger) -> dict:
    """
    Compare visual style of two consecutive pages.
    Returns a dict with style_match, letterhead_match, layout types, strongest_difference, confidence.
    """
    prompt = (
        "Compare these two scanned document pages visually.\n\n"
        "Examine specifically:\n"
        "1. Letterhead or company logo — same or different? Present on both, one, or neither?\n"
        "2. Font family and size of body text — consistent or noticeably different?\n"
        "3. Page layout type — narrative/prose, form/table, technical drawing, or mixed?\n"
        "4. Visual batch consistency — similar scan quality, paper tone, margin style?\n"
        f"5. Is there a new title block or document header starting on the second page (page {page_curr})?\n\n"
        "Respond ONLY with JSON:\n"
        '{"style_match": true/false, "letterhead_match": true/false/null, '
        '"layout_type_prev": "narrative" | "form" | "drawing" | "table" | "mixed", '
        '"layout_type_curr": "narrative" | "form" | "drawing" | "table" | "mixed", '
        '"strongest_difference": "<one sentence or null>", "confidence": <0-100>}'
    )
    raw = _infer(prompt, [img_prev, img_curr], model, processor, config, logger, max_tokens=120)
    logger.debug(f"  Style continuity p{page_prev}→{page_curr}: {repr((raw or '')[:300])}")
    data = _parse_json(raw or "", logger)
    if not data:
        return {"style_match": True, "letterhead_match": None, "layout_type_prev": "mixed",
                "layout_type_curr": "mixed", "strongest_difference": None, "confidence": 50}
    return data


def _query_rotation(img, page_num: int, model, processor, config, logger: logging.Logger) -> int:
    """OSD-first rotation (no model call). Legacy VLM path kept in rotation.py."""
    from rotation import query_rotation_osd_first
    return query_rotation_osd_first(img, page_num, logger)


# ---------------------------------------------------------------------------
# Phase 1f — next-page-start gate (replaces signature ownership)
# ---------------------------------------------------------------------------

def _query_next_page_starts_new(img_curr, img_next, page_curr, page_next, model, processor, config, logger):
    """
    Called when page_curr has a signature/signoff. A signature only ends a
    document if page_next actually starts a new one. Returns (starts_new: bool,
    confidence float 0-1, reason str).
    """
    prompt = (
        f"Page {page_curr} ends with a signature or approval block. Look at the NEXT "
        f"page (page {page_next}) and decide whether it STARTS a new, separate document.\n\n"
        f"Page {page_next} starts a new document (starts_new=true) if ANY of:\n"
        "  - It has a new heading, title, or document header at the top\n"
        "  - It has a different letterhead, logo, or issuing organization\n"
        "  - It repeats a self-contained header block (ОБЕКТ / ВЪЗЛОЖИТЕЛ / ЧАСТ etc.)\n"
        "  - It has NO new heading, but is clearly a different document type or issuer "
        "(different subject, different form, different authority)\n\n"
        f"Page {page_next} does NOT start a new document (starts_new=false) if:\n"
        "  - It continues the same text, table, or narrative in the same style\n"
        "  - It is a continuation page of the document that page "
        f"{page_curr} belongs to\n\n"
        "Be strict: if the next page just continues in the same style with no new "
        "heading and no change of subject/issuer, answer false — the signature was "
        "mid-document.\n\n"
        "Respond ONLY with JSON:\n"
        '{"starts_new": true/false, "confidence": <0-100>, "reason": "<one sentence>", '
        '"next_page_heading": "<verbatim heading/title at the top of the next page, or empty string if none>"}'
    )
    raw = _infer(prompt, [img_curr, img_next], model, processor, config, logger, max_tokens=250)
    logger.debug(f"  Next-page-start p{page_next}: {repr((raw or '')[:300])}")
    data = _parse_json(raw or "", logger)
    starts_new = bool(data.get("starts_new", True))
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    reason = str(data.get("reason", "")).strip()
    next_page_heading = str(data.get("next_page_heading", "")).strip()
    if reason:
        logger.info(f"  Next-page-start reason: {reason}")
    return starts_new, conf, next_page_heading


# ---------------------------------------------------------------------------
# Phase 1g — identifier continuity (log-only, no decision impact)
# ---------------------------------------------------------------------------

def _query_doc_identifier(img, page_num, model, processor, config, logger):
    """
    Extract a stable document identifier for continuity comparison. Log-only for now.
    Returns a normalized string or "".
    """
    prompt = (
        f"Look at page {page_num}. Extract the single most prominent document "
        "identifier if present: a permit number (РС №), outgoing/incoming number "
        "(изх. №, вх. №), object/site string (ОБЕКТ: ...), or contract number. "
        "Return ONLY the short identifier token (number or brief label, max 60 characters). "
        "Do NOT copy full sentences. Return empty string if none.\n\n"
        'Respond ONLY with JSON:\n{"identifier": "<short token or empty>"}'
    )
    raw = _infer(prompt, [img], model, processor, config, logger, max_tokens=300)
    data = _parse_json(raw or "", logger)
    ident = str(data.get("identifier", "")).strip()
    norm = re.sub(r"[^0-9a-zа-я]", "", ident.lower())
    table = str.maketrans({"c": "с", "o": "о", "p": "р", "a": "а", "e": "е", "x": "х", "y": "у"})
    return norm.translate(table)


# ---------------------------------------------------------------------------
# Phase 2 — classify a single boundary page (full nomenclature)
# ---------------------------------------------------------------------------

def _classify_page(image, page_num: int, model, processor, config, logger: logging.Logger) -> tuple:
    """
    Send one page image with the full nomenclature and return (code, name, confidence).
    """
    prompt = (
        f"This is page {page_num} — the FIRST page of a document in a Bulgarian "
        "construction/building permit archive.\n\n"
        "Identify the document type using the nomenclature codes below. "
        "Pick the single most specific matching code.\n\n"
        f"{NOMENCLATURE_TEXT}\n\n"
        "Respond ONLY with JSON:\n"
        '{"code": <number>, "confidence": <0-100>}'
    )
    raw = _infer(prompt, [image], model, processor, config, logger, max_tokens=100)
    logger.debug(f"  Classify response p{page_num}: {repr((raw or '')[:200])}")
    data = _parse_json(raw or "", logger)
    code = resolve_code(_extract_int(data.get("code", 19999)))[0]
    conf = min(100.0, max(0.0, float(data.get("confidence", 50)))) / 100.0
    _, name = resolve_code(code)
    return code, name, conf


# ---------------------------------------------------------------------------
# Boundary detection — two-phase: detect ends then classify starts
# ---------------------------------------------------------------------------

def detect_boundaries(
    pdf_path: Path,
    total_pages: int,
    model,
    processor,
    config,
    dpi: int,
    logger: logging.Logger,
    classify: bool = True,
) -> list:
    """
    Phase 1 — for each page n, load [n-1, n, n+1] and ask the model whether
               page n ends a document. If yes → n+1 is a new document start.
               At most 3 images are held in RAM at any time.
               Includes: style continuity pre-filter, table_end cap, appendix chain
               tracking, next-page-start gate for signatures, one-page disambiguation,
               start-detection fallback for heading-led docs, low-conf confirmation.

    Phase 2 — classify each document-start page with the full nomenclature.
    """
    page_buffer: dict = {}
    doc_starts: list = [1]
    end_confidences: dict = {}   # page n → (conf, signal)
    style_results: dict = {}     # page n → style result for n→n+1

    appendix_chain_active = False
    appendix_chain_start_page = None

    rotation_log: dict[int, int] = {}  # page_num → degrees rotated (0 = no rotation)
    def ensure(p: int) -> None:
        """Load page into buffer (original orientation — Phase 1 sees unrotated pages)."""
        if p not in page_buffer:
            page_buffer[p] = _load_page(pdf_path, p, dpi)

    def detect_rotation(p: int) -> None:
        """Detect rotation via OSD and APPLY it so Phase 1 queries see upright pages."""
        ensure(p)
        if p not in rotation_log:
            rotation = _query_rotation(page_buffer[p], p, model, processor, config, logger)
            rotation_log[p] = rotation
            if rotation != 0:
                page_buffer[p] = page_buffer[p].rotate(rotation, expand=True)
                logger.info(f"  Page {p} rotated {rotation} deg CCW for Phase 1 queries")

    logger.info(f"  Phase 1: end-of-document detection ({total_pages} pages)…")
    for n in range(1, total_pages):
        if n > 1:
            detect_rotation(n - 1)
        detect_rotation(n)
        detect_rotation(n + 1)
        ensure(n - 1 if n > 1 else n)
        ensure(n)
        ensure(n + 1)

        context_pages = ([n - 1] if n > 1 else []) + [n, n + 1]
        context_images = [page_buffer[p] for p in context_pages]

        # Style continuity — modifiers only, never a gate
        style_result = _query_style_continuity(
            page_buffer[n], page_buffer[n + 1], n, n + 1,
            model, processor, config, logger,
        )
        style_results[n] = style_result

        logger.info(f"  Checking page {n} (context: {context_pages})")
        is_end, conf, signal, signal_page = _query_document_end(context_images, context_pages, n, model, processor, config, logger)
        logger.info(f"  p{n}: end={is_end}, signal={signal}, signal_on_page={signal_page}, conf={conf:.0%}")

        # Place boundary at signal_page for end-on-page signals; at signal_page-1
        # for start-on-next signals (the new doc begins at signal_page, so the old
        # doc ends one page before it).
        if is_end:
            if signal in START_ON_NEXT_SIGNALS:
                effective_end = signal_page - 1
            else:
                effective_end = signal_page
        else:
            effective_end = n
        if is_end and signal_page != n:
            logger.info(
                f"  Signal '{signal}' is on p{signal_page}, not p{n} — "
                f"adjusting boundary: doc ends at p{effective_end}, next doc starts at p{effective_end + 1}"
            )

        # Tier2-#4: transcribe-then-judge gate for titled_id_header (anti-hallucination).
        # The shared end-detection prompt is left untouched (no bleed); we add ONE dedicated
        # READ on the signal page and keep the boundary only if BOTH a title AND a document-
        # level identifier are actually grounded there. Kills the invented-РС№ FP class
        # (FP11/19/27); a true titled start (e.g. p10 СКИЦА № 15-158202) transcribes both and
        # survives. Every gate decision is logged for both-directions auditing.
        if is_end and signal == "titled_id_header" and signal_page in page_buffer:
            t_title, t_ident = _query_transcribe_title(
                page_buffer[signal_page], signal_page, model, processor, config, logger
            )
            grounded = (t_title.lower() not in ("", "none")) and (t_ident.lower() not in ("", "none"))
            logger.info(
                f"  [TITLE-GATE] p{signal_page}: title={t_title!r} identifier={t_ident!r} "
                f"-> {'KEEP' if grounded else 'SUPPRESS'}"
            )
            if not grounded:
                is_end = False
                effective_end = n
                logger.info(
                    f"  [TITLE-GATE] titled_id_header at p{signal_page} SUPPRESSED "
                    f"— title/identifier not grounded on the page"
                )

        # One-page-check: when an END-on-page signal was projected forward to n+1,
        # disambiguate whether n+1 is self-contained (boundary at n) or a closing
        # page of the current doc (keep projection at n+1). Only fires for
        # signal in END_ON_PAGE_SIGNALS — START signals are correctly placed by -1
        # and must not also trigger this.
        if (is_end and signal in END_ON_PAGE_SIGNALS
                and signal_page == n + 1
                and n + 1 <= total_pages
                and n + 1 in page_buffer):
            sc, _ = _query_is_self_contained(
                page_buffer[n + 1], n + 1, model, processor, config, logger
            )
            if sc:
                effective_end = n
                logger.info(f"  [ONE-PAGE-CHECK] p{n+1} is self-contained — boundary corrected to p{n}")
            # else: keep effective_end = n+1 (continuation/closing, projection correct)

        # Style result — log-only this run (A/B to measure if confidence nudges are load-bearing).
        # Values still extracted so start-detector gate (style_break) still works.
        style_match = style_result.get("style_match", True)
        style_conf = style_result.get("confidence", 50) / 100.0
        letterhead_match = style_result.get("letterhead_match")
        layout_prev = style_result.get("layout_type_prev")
        layout_curr = style_result.get("layout_type_curr")

        # Cap table_end confidence so it must pass the low-conf confirmation pass
        # below — but don't veto it: some docs legitimately end on a totals row.
        # Cap unreliable signals so they must pass the confirmation pass below.
        # page_number_reset and stamp_change depend on small print / stamp text
        # that is marginal at this DPI.
        if signal in ("table_end", "page_number_reset", "stamp_change"):
            conf = min(conf, 0.60)

        # Appendix chain logic
        if is_end and "appendix" in signal:
            if not appendix_chain_active:
                standalone, sa_conf = _query_is_standalone(
                    context_images, context_pages, n + 1, model, processor, config, logger,
                )
                if not standalone:
                    is_end = False
                    appendix_chain_active = True
                    appendix_chain_start_page = n + 1
                    logger.info(f"  Appendix chain started at p{n + 1} — boundaries suppressed until closing signature or subject change")
                else:
                    logger.info(f"  Appendix on p{n + 1} is standalone — keeping boundary")
            else:
                # Inside an active chain: still check for a genuine issuer/subject change
                # before blanket-suppressing. A new spec sheet with a different issuer IS
                # a real boundary even inside a chain.
                if n > 1 and n in page_buffer and (n - 1) in page_buffer:
                    chain_sn, _, chain_reason = _query_starts_new_document(
                        page_buffer[n - 1], page_buffer[n], n - 1, n,
                        model, processor, config, logger,
                    )
                    if chain_sn:
                        logger.info(f"  Appendix chain: relational check found subject/issuer change at p{n} — boundary kept: {chain_reason}")
                        # is_end stays True; chain continues from this new start
                    else:
                        is_end = False
                        logger.info(f"  Inside appendix chain (started p{appendix_chain_start_page}) — boundary at p{n + 1} suppressed")
                else:
                    is_end = False
                    logger.info(f"  Inside appendix chain (started p{appendix_chain_start_page}) — boundary at p{n + 1} suppressed")

        elif is_end and signal in STRONG_SIGNOFF_SIGNALS and appendix_chain_active:
            appendix_chain_active = False
            appendix_chain_start_page = None
            logger.info(f"  Appendix chain closed by signature_block at p{n} — boundary confirmed")

        elif is_end and appendix_chain_active:
            appendix_chain_active = False
            appendix_chain_start_page = None
            logger.info(f"  Appendix chain reset by signal '{signal}' at p{n}")

        # Signature/signoff gate: a signature only ends a document if the NEXT
        # page actually starts a new one. Mid-document signatures are common here.
        if is_end and signal in {"signature_block", "project_signoff"} and effective_end == n:
            starts_new, sn_conf, next_heading = _query_next_page_starts_new(
                page_buffer[n], page_buffer[n + 1], n, n + 1,
                model, processor, config, logger,
            )
            if not starts_new:
                is_end = False
                logger.info(f"  Signature on p{n} but next page does not start a new doc — suppressed")
            else:
                conf = (conf + sn_conf) / 2
                logger.info(
                    f"  Signature on p{n} confirmed as end — next page starts new doc (conf={conf:.0%})"
                    + (f" [next_page_heading='{next_heading}']" if next_heading else "")
                )
                # ID-continuity disabled — was log-only, removed to save 2 model calls per signature boundary

        # Low-confidence confirmation pass — skip for strong visual signals that
        # don't need corroboration (fresh letterhead and header resets are visually unambiguous)
        if is_end and conf < 0.75 and signal not in ("fresh_letterhead", "header_block_reset", "titled_id_header"):
            confirmed, confirm_conf = _query_confirm_boundary(
                page_buffer[n], page_buffer[n + 1], n, n + 1,
                model, processor, config, logger,
            )
            if not confirmed:
                is_end = False
                logger.info(f"  Low-conf boundary at p{n} ({conf:.0%}) rejected by confirmation pass")
            else:
                conf = (conf + confirm_conf) / 2
                logger.info(f"  Low-conf boundary at p{n} confirmed — averaged conf={conf:.0%}")

        if is_end:
            new_start = effective_end + 1

            # Change 4: when the projection lands beyond the last page, re-evaluate
            # using the self-contained check rather than silently dropping.
            if new_start > total_pages and n + 1 in page_buffer:
                logger.info(
                    f"  [OOB-PROJECTION] new_start={new_start} > total_pages={total_pages} — re-evaluating"
                )
                sc, _ = _query_is_self_contained(
                    page_buffer[n + 1], n + 1, model, processor, config, logger
                )
                if sc:
                    effective_end = n
                    new_start = n + 1
                    logger.info(f"  [OOB-PROJECTION] p{n+1} self-contained — boundary corrected to p{n}")
                else:
                    is_end = False
                    effective_end = min(effective_end, total_pages)
                    logger.info(f"  [OOB-PROJECTION] p{n+1} is continuation — no boundary recorded, new doc beyond PDF")

            if new_start not in doc_starts and new_start <= total_pages:
                doc_starts.append(new_start)

            # Change 3: keep max confidence per effective_end (last-write-wins could
            # replace a higher-quality earlier confidence with a lower-quality later one).
            existing = end_confidences.get(effective_end)
            if existing is None or conf > existing[0]:
                end_confidences[effective_end] = (conf, signal)

            logger.info(f"  End at page {effective_end} → doc starts at page {new_start} (conf={conf:.0%}, signal={signal})")

        # Start-detection: independent of end-detection. Asks whether page n itself
        # begins a new document relative to n-1, producing a boundary AT n. Runs even
        # when is_end is True, because in single-page-doc runs a page both ends its own
        # doc AND is a fresh start. Uses the n-1→n style comparison (style_results[n-1]),
        # NOT n→n+1. page_buffer[n-1] and style_results[n-1] are both still available here.
        if n > 1 and n not in doc_starts:
            prev_style = style_results.get(n - 1, {})
            style_break = (
                prev_style.get("letterhead_match") is False
                or prev_style.get("layout_type_prev") != prev_style.get("layout_type_curr")
            )
            if is_end or style_break:
                starts_new, sd_conf, sd_reason = _query_starts_new_document(
                    page_buffer[n - 1], page_buffer[n], n - 1, n,
                    model, processor, config, logger,
                )
                if starts_new:
                    doc_starts.append(n)
                    existing = end_confidences.get(n - 1)
                    if existing is None or sd_conf > existing[0]:
                        end_confidences[n - 1] = (sd_conf, "start_only_heading")
                    logger.info(f"  [START-DETECT] p{n} starts a new doc (conf={sd_conf:.0%}): {sd_reason}")

        if (n - 1) in page_buffer:
            del page_buffer[n - 1]

    page_buffer.clear()

    # Smoothing exists to paper over a noisy detector; with the precision-first
    # OSD detector it must not override per-page decisions. Log-only diagnostic.
    _smoothed = smooth_rotation_log(rotation_log, logger)
    _diffs = {p: (rotation_log.get(p), d) for p, d in _smoothed.items() if rotation_log.get(p) != d}
    if _diffs:
        logger.info(f"  [ROT-SMOOTH] (log-only, not applied) would change: {_diffs}")

    doc_starts = sorted(set(doc_starts))
    logger.info(f"  Phase 1 done — document start pages: {doc_starts}")


    # --- Phase 2: classify the first page of each document ---
    boundaries = []
    if not classify:
        logger.info(f"  Skipping Phase 2 classification (classify=False)")
        for start_page in doc_starts:
            raw_conf, signal = end_confidences.get(start_page - 1, (1.0, "none"))
            conf = min(1.0, raw_conf + 0.10) if signal in STRONG_SIGNOFF_SIGNALS else raw_conf
            boundaries.append(DocumentBoundary(
                page=start_page, code=0, name="",
                confidence=conf, flagged=False, style_signal="",
            ))
    else:
        logger.info(f"  Phase 2: classifying {len(doc_starts)} document(s)…")
        for idx, start_page in enumerate(doc_starts):
            raw_conf, signal = end_confidences.get(start_page - 1, (1.0, "none"))

            if signal in STRONG_SIGNOFF_SIGNALS:
                conf = min(1.0, raw_conf + 0.10)
            else:
                conf = raw_conf

            logger.info(f"  Classifying page {start_page}…")
            img = _load_page(pdf_path, start_page, dpi)
            rot = rotation_log.get(start_page, 0)
            if rot != 0:
                img = img.rotate(rot, expand=True)
            code, name, cls_conf = _classify_page(img, start_page, model, processor, config, logger)
            del img

            next_start = doc_starts[idx + 1] if idx + 1 < len(doc_starts) else total_pages + 1
            if name == "Заглавна страница" and start_page + 1 < next_start:
                logger.info(f"  Title page at {start_page} — peeking at page {start_page + 1} for better classification…")
                img2 = _load_page(pdf_path, start_page + 1, dpi)
                rot2 = rotation_log.get(start_page + 1, 0)
                if rot2 != 0:
                    img2 = img2.rotate(rot2, expand=True)
                code2, name2, cls_conf2 = _classify_page(img2, start_page + 1, model, processor, config, logger)
                del img2
                if code2 != 19999:
                    logger.info(f"  Override: {code} {name} → {code2} {name2} (p2 conf={cls_conf2:.0%})")
                    code, name, cls_conf = code2, name2, min(cls_conf, cls_conf2)

            style_res = style_results.get(start_page - 1, {})
            style_signal = style_res.get("strongest_difference") or ""

            logger.info(f"  Page {start_page} → {code} {name} (end conf={conf:.0%}, class conf={cls_conf:.0%})")

            flagged = conf < CONFIDENCE_THRESHOLD and start_page != 1
            if flagged:
                logger.warning(f"  LOW CONFIDENCE split before page {start_page} ({conf:.0%}) — flagged for review")

            boundaries.append(DocumentBoundary(
                page=start_page, code=code, name=name,
                confidence=conf, flagged=flagged, style_signal=style_signal,
            ))

    logger.info(f"  Boundaries: {[(b.page, b.code, b.name) for b in boundaries]}")
    pages_rotated = {p: deg for p, deg in rotation_log.items() if deg != 0}
    return boundaries, pages_rotated


# ---------------------------------------------------------------------------
# PDF splitting
# ---------------------------------------------------------------------------

def safe_filename(name: str, max_len: int = 50) -> str:
    safe = re.sub(r'[/\\:*?"<>|]', "-", name).strip()
    safe = re.sub(r"\s+", "_", safe)
    return safe[:max_len]


def split_pdf(
    pdf_path: Path,
    boundaries: list,
    output_dir: Path,
    logger: logging.Logger,
) -> list:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem
    outputs = []

    for i, boundary in enumerate(boundaries):
        end_page = boundaries[i + 1].page - 1 if i + 1 < len(boundaries) else total

        writer = PdfWriter()
        for p in range(boundary.page - 1, end_page):
            writer.add_page(reader.pages[p])

        name_safe = safe_filename(boundary.name)
        flag = "_REVIEW" if boundary.flagged else ""
        out_path = output_dir / f"{stem}_{i + 1:03d}_{boundary.code:05d}_{name_safe}{flag}.pdf"

        with open(out_path, "wb") as f:
            writer.write(f)

        page_range = (
            f"page {boundary.page}"
            if boundary.page == end_page
            else f"pages {boundary.page}–{end_page}"
        )
        conf_str = f"{boundary.confidence:.0%}"
        style_str = f", style: \"{boundary.style_signal}\"" if boundary.style_signal else ""
        logger.info(f"  → {out_path.name}  ({page_range}, conf={conf_str}{style_str})")
        outputs.append(out_path)

    return outputs


# ---------------------------------------------------------------------------
# Per-file orchestration
# ---------------------------------------------------------------------------

def process_pdf(
    pdf_path: Path,
    output_dir: Path,
    model,
    processor,
    config,
    dpi: int,
    logger: logging.Logger,
) -> None:
    logger.info("─" * 60)
    logger.info(f"Processing: {pdf_path.name}")

    try:
        total_pages = len(PdfReader(str(pdf_path)).pages)
    except Exception as e:
        logger.error(f"  Failed to read PDF: {e}")
        return

    logger.info(f"  {total_pages} page(s) at {dpi} DPI (lazy loading)")

    logger.info("  Detecting boundaries…")
    boundaries, pages_rotated = detect_boundaries(pdf_path, total_pages, model, processor, config, dpi, logger)
    if pages_rotated:
        logger.info(f"  Rotated pages: {pages_rotated}")

    logger.info(f"  Splitting into {len(boundaries)} document(s)…")
    split_pdf(pdf_path, boundaries, output_dir, logger)

    logger.info(f"  Done: {pdf_path.name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split combined scanned PDFs using HuggingFace transformers + CUDA",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("folder", help="Folder containing PDFs to process")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Page render DPI")
    parser.add_argument("--model", default=MODEL_PATH, help="HuggingFace model path")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a directory", file=sys.stderr)
        sys.exit(1)

    output_dir = folder / "split"
    logger = setup_logging(output_dir)

    logger.info("PDF Document Splitter (HuggingFace / CUDA)")
    logger.info(f"Folder     : {folder}")
    logger.info(f"Model      : {args.model}")
    logger.info(f"DPI        : {args.dpi}")
    logger.info(f"Window     : prev+current+next (end-of-doc detection), confidence ≥ {CONFIDENCE_THRESHOLD:.0%}")
    logger.info(f"Output     : {output_dir}")

    model, processor, config = load_model(args.model, logger)

    # transformers/accelerate may call logging.disable() during model load — undo it
    logging.disable(logging.NOTSET)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        fh = logging.FileHandler(output_dir / "split_log.txt", encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)

    pdfs = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        logger.info("No PDFs found.")
        sys.exit(0)

    logger.info(f"Found {len(pdfs)} PDF(s)")

    for pdf_path in pdfs:
        try:
            process_pdf(pdf_path, output_dir, model, processor, config, args.dpi, logger)
        except Exception as e:
            logger.error(f"Error on {pdf_path.name}: {e}", exc_info=True)

    logger.info("─" * 60)
    logger.info("All done.")


if __name__ == "__main__":
    main()
