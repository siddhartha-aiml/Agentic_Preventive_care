"""Language support for the voice layer.

- LANGUAGES: the languages the patient can pick (those Sarvam Bulbul can speak back).
- Hindi glossary + red flags: let the rule-based (demo-mode) agents and the hard safety net understand Hindi.
- t(): fixed patient-facing sentences. Hindi is hand-written; other languages are translated by the LLM when
  one is configured, otherwise they fall back to English.
- speech_text(): turns a chat message into plain text that sounds right when read aloud.
"""

import logging
import re
import unicodedata
from functools import lru_cache

log = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en-IN"

LANGUAGES: dict[str, dict[str, str]] = {
    "hi-IN": {"name": "Hindi", "native": "हिन्दी"},
    "en-IN": {"name": "English", "native": "English"},
    "bn-IN": {"name": "Bengali", "native": "বাংলা"},
    "mr-IN": {"name": "Marathi", "native": "मराठी"},
    "ta-IN": {"name": "Tamil", "native": "தமிழ்"},
    "te-IN": {"name": "Telugu", "native": "తెలుగు"},
    "gu-IN": {"name": "Gujarati", "native": "ગુજરાતી"},
    "kn-IN": {"name": "Kannada", "native": "ಕನ್ನಡ"},
    "ml-IN": {"name": "Malayalam", "native": "മലയാളം"},
    "pa-IN": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    "od-IN": {"name": "Odia", "native": "ଓଡ଼ିଆ"},
}


def normalize_language(code: str | None) -> str:
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def language_name(code: str | None) -> str:
    return LANGUAGES[normalize_language(code)]["name"]


# ───────────────────────── Hindi understanding (rule-based) ─────────────────────────

def _norm(text: str) -> str:
    """Lower-case and fold common Devanagari spelling variants (nukta, chandrabindu)."""
    return unicodedata.normalize("NFC", text).lower().replace("़", "").replace("ँ", "ं")


# Hindi / Hinglish phrase → English terms the keyword classifier and case matcher already understand.
_HI_GLOSSARY_RAW: dict[str, str] = {
    # general
    "बुखार": "fever", "ताप": "fever", "खांसी": "cough", "जुकाम": "cold", "सर्दी": "cold", "कमजोरी": "weakness",
    "थकान": "fatigue", "बदन दर्द": "body ache", "गला खराब": "sore throat", "ठंड लग": "chills", "वजन कम": "weight loss",
    # heart
    "सीने में दर्द": "chest pain", "छाती में दर्द": "chest pain", "सीने में जकड़न": "chest tight", "धड़कन": "palpitation",
    "बीपी": "blood pressure", "ब्लड प्रेशर": "blood pressure", "पैरों में सूजन": "swollen legs",
    # brain and nerves
    "सिर दर्द": "headache", "सिरदर्द": "headache", "सर दर्द": "headache", "सिर में दर्द": "headache", "सर में दर्द": "headache",
    "माइग्रेन": "migraine", "चक्कर": "dizzy", "झनझनाहट": "tingling", "सुन्न": "numb", "मिर्गी": "seizure",
    "दौरे पड़": "seizure", "याददाश्त": "memory", "हाथ कांप": "tremor",
    # skin
    "खुजली": "itch", "दाने": "rash", "चकत्ते": "rash", "त्वचा": "skin", "चमड़ी": "skin", "मुंहासे": "acne", "बाल झड़": "hair loss",
    # stomach
    "पेट": "stomach", "गैस": "bloating", "एसिडिटी": "acid reflux", "उल्टी": "vomit", "जी मिचला": "nausea",
    "दस्त लग": "diarrhea", "दस्त हो": "diarrhea", "पतले दस्त": "diarrhea", "लूज मोशन": "diarrhea", "कब्ज": "constipation",
    "अपच": "indigestion", "पीलिया": "jaundice", "सीने में जलन": "heartburn",
    # lungs
    "सांस फूल": "short of breath", "सांस लेने में": "breathing", "दमा": "asthma", "बलगम": "phlegm",
    "घरघराहट": "wheez", "खर्राटे": "snoring",
    # bones and joints
    "कमर दर्द": "back pain", "कमर में दर्द": "back pain", "पीठ दर्द": "back pain", "पीठ में दर्द": "back pain",
    "घुटने": "knee", "घुटना": "knee", "घुटनों": "knee", "जोड़ों": "joint", "कंधे": "shoulder", "कंधा": "shoulder",
    "हड्डी": "bone", "मोच": "sprain", "गर्दन में दर्द": "neck pain",
    # ear, nose, throat
    "कान में": "ear", "कान से": "ear", "कान दर्द": "ear", "कान का": "ear", "नाक": "nose", "गले": "throat", "गला": "throat",
    "सुनाई": "hearing", "साइनस": "sinus", "आवाज बैठ": "hoarse",
    # hormones
    "शुगर": "sugar diabetes", "मधुमेह": "diabetes", "थायराइड": "thyroid", "प्यास": "thirst", "वजन बढ़": "weight gain",
    # mind
    "घबराहट": "anxiety", "चिंता": "worry", "उदास": "sad", "नींद नहीं": "insomnia", "तनाव": "stress", "टेंशन": "stress",
    "मन नहीं लग": "depress",
    # eyes
    "आंख": "eye", "धुंधला": "blurry", "दिखाई नहीं": "vision", "नजर कमजोर": "vision",
    # urinary
    "पेशाब": "urine", "पथरी": "kidney stone",
    # women's health
    "माहवारी": "period", "पीरियड": "period", "मासिक": "menstru", "गर्भ": "pregnan", "प्रेग्नेंट": "pregnan",
    # severity / timing words used for urgency
    "बहुत तेज": "severe", "बहुत ज्यादा": "severe", "असहनीय": "unbearable", "बढ़ता जा": "getting worse", "अचानक": "sudden",
    # romanised Hindi (typed)
    "bukhar": "fever", "khansi": "cough", "kamzori": "weakness", "seene mein dard": "chest pain", "sir dard": "headache",
    "sar dard": "headache", "chakkar": "dizzy", "khujli": "itch", "pet dard": "stomach", "pet mein dard": "stomach",
    "ulti": "vomit", "kabz": "constipation", "saans phool": "short of breath", "kamar dard": "back pain",
    "ghutne": "knee", "ghabrahat": "anxiety", "neend nahi": "insomnia", "peshab": "urine", "pathri": "kidney stone",
}

# Hindi / Hinglish emergency phrase → matching English red flag (see specialties.RED_FLAGS).
_HI_RED_FLAGS_RAW: dict[str, str] = {
    "सीने में तेज दर्द": "crushing chest pain", "सीने में बहुत दर्द": "crushing chest pain",
    "छाती में तेज दर्द": "crushing chest pain", "छाती में बहुत दर्द": "crushing chest pain",
    "सांस नहीं आ रही": "can't breathe", "सांस नहीं ले पा": "can't breathe", "दम घुट": "can't breathe",
    "चेहरा टेढ़ा": "face drooping", "मुंह टेढ़ा": "face drooping", "जुबान लड़खड़ा": "slurred speech",
    "आत्महत्या": "suicidal thoughts", "खुदकुशी": "suicidal thoughts", "मरना चाहत": "kill myself",
    "जान दे दू": "end my life", "जान देना चाहत": "end my life", "जीना नहीं चाहत": "end my life",
    "बेहोश": "unconscious", "खून की उल्टी": "vomiting blood", "खांसी में खून": "coughing up blood",
    "बहुत खून बह": "severe bleeding", "गला बंद हो": "throat closing",
    "seene mein tez dard": "crushing chest pain", "saans nahi aa rahi": "can't breathe", "behosh": "unconscious",
    "khoon ki ulti": "vomiting blood", "aatmahatya": "suicidal thoughts", "marna chahta": "kill myself",
}

HI_GLOSSARY = {_norm(k): v for k, v in _HI_GLOSSARY_RAW.items()}
HI_RED_FLAGS = {_norm(k): v for k, v in _HI_RED_FLAGS_RAW.items()}


def _contains(text: str, phrase: str) -> bool:
    if phrase.isascii():  # romanised: match whole words only ("pet dard" must not match "carpet dardanelles")
        return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
    return phrase in text


def detect_hindi_red_flag(text: str) -> str:
    """Return the Hindi phrase (as written in our list) that signals an emergency, or ''."""
    t = _norm(text)
    for phrase in HI_RED_FLAGS:
        if _contains(t, phrase):
            return phrase
    return ""


def gloss(text: str) -> str:
    """English terms for the Hindi symptom/emergency phrases found in `text` ('' if none)."""
    t = _norm(text)
    terms: list[str] = []
    for table in (HI_RED_FLAGS, HI_GLOSSARY):
        for phrase, english in table.items():
            if english not in terms and _contains(t, phrase):
                terms.append(english)
    return ", ".join(terms)


# ───────────────────────── fixed sentences ─────────────────────────

SPECIALTY_HI = {
    "General Physician": "सामान्य डॉक्टर (जनरल फिजिशियन)",
    "Cardiology": "दिल के डॉक्टर (कार्डियोलॉजिस्ट)",
    "Neurology": "दिमाग और नसों के डॉक्टर (न्यूरोलॉजिस्ट)",
    "Dermatology": "त्वचा के डॉक्टर (डर्मेटोलॉजिस्ट)",
    "Gastroenterology": "पेट के डॉक्टर (गैस्ट्रोएंटरोलॉजिस्ट)",
    "Pulmonology": "फेफड़ों और सांस के डॉक्टर (पल्मोनोलॉजिस्ट)",
    "Orthopedics": "हड्डी और जोड़ों के डॉक्टर (ऑर्थोपेडिक)",
    "ENT": "कान, नाक और गले के डॉक्टर (ई एन टी)",
    "Endocrinology": "शुगर और थायराइड के डॉक्टर (एंडोक्राइनोलॉजिस्ट)",
    "Psychiatry": "मन के डॉक्टर (साइकियाट्रिस्ट)",
    "Ophthalmology": "आंखों के डॉक्टर",
    "Urology": "पेशाब और किडनी के डॉक्टर (यूरोलॉजिस्ट)",
    "Obstetrics & Gynecology": "महिलाओं की डॉक्टर (गायनेकोलॉजिस्ट)",
}


def specialty_label(specialty: str, lang: str) -> str:
    return SPECIALTY_HI.get(specialty, specialty) if lang == "hi-IN" else specialty


STRINGS: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Hi {first} 👋 I'm your **Health Guide**.{history}\n\nTell me what's been bothering you — what symptoms are you "
              "experiencing, and when did they start? I'll ask a few follow-up questions, figure out which specialist fits best, "
              "and help you book an appointment.",
        "hi": "नमस्ते {first} जी 🙏 मैं आपका **हेल्थ गाइड** हूं।{history}\n\nबताइए, आपको क्या तकलीफ़ है और कब से है? "
              "मैं आपसे कुछ सवाल पूछूंगा, फिर सही डॉक्टर ढूंढकर अपॉइंटमेंट लेने में आपकी मदद करूंगा। नीचे माइक का बटन दबाकर बोलिए।",
    },
    "greeting_history": {
        "en": " I can see your health profile (including {known}) and I'll take it into account.",
        "hi": " मैंने आपकी पुरानी बीमारियों की जानकारी देख ली है और उसका ध्यान रखूंगा।",
    },
    "greeting_no_history": {
        "en": " If you have any existing conditions, you can add them in your Health Profile so I can take them into account.",
        "hi": "",
    },
    "handoff": {
        "en": "Thanks — let me find the right specialist for you.",
        "hi": "धन्यवाद। अब मैं आपके लिए सही डॉक्टर ढूंढता हूं।",
    },
    "rule_flag": {
        "en": "You mentioned “{flag}”, which can be a sign of a medical emergency.",
        "hi": "आपने “{flag}” बताया, यह किसी गंभीर इमरजेंसी का संकेत हो सकता है।",
    },
    "emergency": {
        "en": "⚠️ **This may be a medical emergency.** {reason} Please **call 112 (national emergency number) or 108 for an "
              "ambulance, or go to the nearest emergency room now**. If you are having thoughts of harming yourself, please call "
              "**Tele-MANAS at 14416** (or 1-800-891-4416), India's free 24/7 mental health helpline. \n\nIf you're safe and "
              "simply want follow-up care afterwards, I've listed suitable doctors below.",
        "hi": "⚠️ **यह इमरजेंसी हो सकती है।** {reason} कृपया **अभी 112 पर फोन करें, या एम्बुलेंस के लिए 108 पर फोन करें, या तुरंत "
              "सबसे पास के अस्पताल जाएं**। अगर मन में खुद को नुकसान पहुंचाने के ख्याल आ रहे हैं, तो **टेली-मानस 14416** पर फोन "
              "करें। यह मुफ़्त है और दिन-रात चालू रहता है।\n\nअगर आप अभी सुरक्षित हैं और बाद में डॉक्टर को दिखाना चाहते हैं, तो "
              "नीचे सही डॉक्टरों की सूची है।",
    },
    "classification": {
        "en": "Based on what you've shared, I recommend seeing a **{specialty}** specialist. {reasoning}",
        "hi": "आपकी बातों के हिसाब से आपको **{specialty}** को दिखाना चाहिए। {reasoning}",
    },
    "recs_intro": {
        "en": "Here are the top {n} doctors I matched for you, based on patients they've successfully treated with similar "
              "symptoms, their ratings and how soon they can see you. Select a doctor to view open slots and book.",
        "hi": "मैंने आपके लिए {n} डॉक्टर चुने हैं। इन डॉक्टरों ने पहले भी आपके जैसी तकलीफ़ वाले मरीज़ों का इलाज किया है। "
              "जिस डॉक्टर को दिखाना है, उनके कार्ड का हरा बटन दबाइए और समय चुनिए।",
    },
    "recs_none": {
        "en": "I couldn't find an available provider for this specialty right now. Please try again later or contact our clinic.",
        "hi": "अभी इस बीमारी के लिए कोई डॉक्टर खाली नहीं मिला। कृपया थोड़ी देर बाद फिर कोशिश करें।",
    },
    "reason_similar": {
        "en": "Has treated patients with similar symptoms (e.g. {case}) — {years} years of experience.",
        "hi": "इन्होंने आपके जैसी तकलीफ़ वाले मरीज़ों का इलाज किया है। {years} साल का अनुभव है।",
    },
    "reason_generic": {
        "en": "Highly rated {specialty} specialist with {years} years of experience.",
        "hi": "मरीज़ों की पसंद के अच्छे डॉक्टर हैं। {years} साल का अनुभव है।",
    },
    # rule-based (demo mode) intake
    "fb_red_flag": {"en": "I'm flagging this as potentially urgent.", "hi": "यह गंभीर हो सकता है।"},
    "fb_greeting": {
        "en": "Hello! 😊 What symptoms or health concerns brought you here today?",
        "hi": "नमस्ते! बताइए, आज आपको क्या तकलीफ़ है?",
    },
    "fb_q1": {
        "en": "Thanks for sharing that. How long have you had these symptoms, and did they start suddenly or gradually?",
        "hi": "बताने के लिए धन्यवाद। यह तकलीफ़ कितने दिनों से है? अचानक शुरू हुई या धीरे-धीरे?",
    },
    "fb_q2": {
        "en": "On a scale of 1 to 10, how severe is it right now — and is it constant, or does it come and go?",
        "hi": "तकलीफ़ कितनी है — थोड़ी, ज़्यादा, या बहुत ज़्यादा? और यह हर समय रहती है या आती-जाती है?",
    },
    "fb_q3": {
        "en": "Are there any other symptoms — such as fever, nausea, dizziness or shortness of breath — or anything that makes "
              "it better or worse?",
        "hi": "क्या इसके साथ और कोई तकलीफ़ है, जैसे बुखार, उल्टी, चक्कर या सांस फूलना? किस चीज़ से आराम मिलता है या तकलीफ़ बढ़ती है?",
    },
    "fb_q3_history": {
        "en": "Given your history ({conditions}), have you noticed any related changes recently? Also, are there other symptoms "
              "— such as fever, nausea, dizziness or shortness of breath — or anything that makes it better or worse?",
        "hi": "आपकी पुरानी बीमारी को देखते हुए, क्या हाल में कुछ बदलाव लगा? और क्या साथ में बुखार, उल्टी, चक्कर या सांस फूलने "
              "जैसी कोई तकलीफ़ है?",
    },
    "fb_complete": {
        "en": "Thank you — I have a clear picture now. Let me find the right specialist for you.",
        "hi": "धन्यवाद, मुझे आपकी तकलीफ़ समझ आ गई है। अब मैं आपके लिए सही डॉक्टर ढूंढता हूं।",
    },
    "fb_reasoning": {
        "en": "Your symptoms are commonly evaluated by a {specialty} specialist ({desc}).",
        "hi": "ऐसी तकलीफ़ में आमतौर पर इसी तरह के डॉक्टर को दिखाया जाता है।",
    },
    "fb_concierge_new": {
        "en": "Let's look at that new concern — I'll start a fresh assessment.",
        "hi": "ठीक है, इस नई तकलीफ़ के बारे में बात करते हैं।",
    },
    "fb_concierge": {
        "en": "Happy to help! Tap any doctor card above to see their open slots and book instantly. Bring a list of your current "
              "medications and note when your symptoms started — it helps your doctor a lot. If your symptoms suddenly worsen, "
              "please seek urgent care.",
        "hi": "ज़रूर। ऊपर किसी भी डॉक्टर के कार्ड का हरा बटन दबाकर समय चुनिए और अपॉइंटमेंट पक्का कीजिए। अपनी दवाइयां साथ लेकर "
              "जाइए। अगर तकलीफ़ अचानक बढ़ जाए तो तुरंत अस्पताल जाइए।",
    },
}


@lru_cache(maxsize=512)
def _llm_translate(text: str, lang: str) -> str:
    """Translate a fixed English sentence for languages we have no hand-written copy for. Needs the LLM."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from .llm import chat_model

    out = chat_model().invoke(
        [
            SystemMessage(
                f"Translate the message into {language_name(lang)} in its native script, using simple everyday spoken words "
                "that a person with little schooling understands. Keep **bold** markers, numbers and doctor names unchanged. "
                "Return only the translation."
            ),
            HumanMessage(text),
        ]
    )
    return str(out.content).strip() or text


def t(key: str, lang: str | None, **kw) -> str:
    lang = normalize_language(lang)
    entry = STRINGS[key]
    if lang == "hi-IN":
        return entry["hi"].format(**kw)
    english = entry["en"].format(**kw)
    if lang == "en-IN":
        return english
    from ..config import get_settings

    if get_settings().demo_mode:
        return english
    try:
        return _llm_translate(english, lang)
    except Exception:
        log.exception("Translation to %s failed; using English", lang)
        return english


LANGUAGE_RULE = """Language rules (the patient is using voice and may not be able to read):
- The patient speaks {language}. Write every patient-facing field (question, reply, reasoning, red_flag_reason, reason) in {language}, in its native script.
- Use simple everyday spoken words that a person with little schooling understands. English words people commonly use (BP, sugar, X-ray, doctor) are fine.
- Short sentences, because the text is read aloud. No markdown, bullet lists or emojis. Do not ask for a "1 to 10" score; ask whether it is a little, a lot, or unbearable.
- symptom_summary and title must ALWAYS be written in English, because the doctor reads them."""


def language_rule(lang: str | None) -> str:
    lang = normalize_language(lang)
    return "" if lang == "en-IN" else "\n\n" + LANGUAGE_RULE.format(language=language_name(lang))


# ───────────────────────── text that is read aloud ─────────────────────────

_DIGIT_WORDS_HI = ["शून्य", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ"]
_PHONE_RE = re.compile(r"\b(112|108|14416|1-800-891-4416)\b")
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def _speak_digits(match: re.Match, lang: str) -> str:
    digits = [d for d in match.group(0) if d.isdigit()]
    return " ".join(_DIGIT_WORDS_HI[int(d)] if lang == "hi-IN" else d for d in digits)


def plain(text: str) -> str:
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"[*_#`>]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def speech_text(content: str, payload: dict | None, lang: str | None) -> str:
    """Plain text version of an assistant message, suitable for text-to-speech."""
    lang = normalize_language(lang)
    text = plain(content)
    if payload and payload.get("type") == "recommendations":
        for i, r in enumerate((payload.get("providers") or [])[:3], start=1):
            label = f"नंबर {i}" if lang == "hi-IN" else f"Number {i}" if lang == "en-IN" else f"{i}"
            text += f" {label}: {r['name']}. {plain(r.get('reason', ''))}"
    text = _PHONE_RE.sub(lambda m: _speak_digits(m, lang), text)
    if lang == "hi-IN":
        text = text.replace("Dr. ", "डॉक्टर ")
    return text
