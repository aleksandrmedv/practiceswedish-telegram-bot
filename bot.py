import random

import os
from dotenv import load_dotenv

load_dotenv()

print("ENV TOKEN:", os.getenv("TELEGRAM_BOT_TOKEN"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from ui_texts import UI_TEXTS
from word_data import WORD_QUIZ_DATA
from noun_data import NOUN_FORMS_DATA, NOUN_FORM_LABELS, NOUN_FORM_SHORT
from verb_data import VERB_FORMS_DATA, VERB_FORM_LABELS

def get_ui_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")


def t(context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs) -> str:
    lang = get_ui_lang(context)
    text = UI_TEXTS[lang][key]
    return text.format(**kwargs) if kwargs else text


def build_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Swedish → English", callback_data="lang|en")],
        [InlineKeyboardButton("Swedish → Russian", callback_data="lang|ru")],
        [InlineKeyboardButton("Swedish → Ukrainian", callback_data="lang|uk")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_topic_menu(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    keyboard = []
    for topic_name in WORD_QUIZ_DATA.keys():
        keyboard.append([InlineKeyboardButton(topic_name, callback_data=f"topic|{topic_name}")])

    keyboard.append([InlineKeyboardButton(t(context, "main_menu"), callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def build_word_keyboard(
    context: ContextTypes.DEFAULT_TYPE,
    word_sv: str,
    options: list[str]
) -> InlineKeyboardMarkup:
    keyboard = []
    for option in options:
        keyboard.append(
            [InlineKeyboardButton(option, callback_data=f"answer|{word_sv}|{option}")]
        )

    return InlineKeyboardMarkup(keyboard)


def build_after_answer_menu(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(t(context, "next_word"), callback_data="next_word")],
    ]

    mistakes = context.user_data.get("mistakes", [])
    if mistakes:
        keyboard.append(
            [InlineKeyboardButton(t(context, "reinforce_words"), callback_data="reinforce_words")]
        )

    keyboard.append([InlineKeyboardButton(t(context, "main_menu"), callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_next_word(context: ContextTypes.DEFAULT_TYPE, topic_words: dict) -> str:
    remaining_words = context.user_data.get("remaining_words")

    if not remaining_words:
        remaining_words = list(topic_words.keys())
        random.shuffle(remaining_words)

    next_word = remaining_words.pop()
    context.user_data["remaining_words"] = remaining_words
    return next_word


def get_word_pool(context: ContextTypes.DEFAULT_TYPE, topic_words: dict) -> list[str]:
    reinforce_mode = context.user_data.get("reinforce_mode", False)
    mistakes = context.user_data.get("mistakes", [])

    if reinforce_mode and mistakes:
        return mistakes.copy()

    return list(topic_words.keys())


def prepare_word_pool(context: ContextTypes.DEFAULT_TYPE, topic_words: dict) -> None:
    word_pool = get_word_pool(context, topic_words)
    random.shuffle(word_pool)
    context.user_data["remaining_words"] = word_pool

async def start_verb_quiz(message, context):

    lang = context.user_data["lang"]
    context.user_data["mode"] = "verbs"
    group = context.user_data["verb_group"]

    reinforce_mode = context.user_data.get("reinforce_mode", False)
    mistakes = context.user_data.get("mistakes", [])

    if group == "all":
        verbs = {}
        for g in VERB_FORMS_DATA.values():
            verbs.update(g)
    else:
        verbs = VERB_FORMS_DATA[group]

    if reinforce_mode and mistakes:
        verb_pool = mistakes.copy()
    else:
        verb_pool = list(verbs.keys())

    verb = random.choice(verb_pool)
    verb_data = verbs[verb]

    translation = verb_data[lang]
    form_key = random.choice(["infinitive", "present", "preterite", "supinum"])
    form_label = VERB_FORM_LABELS[form_key][lang]

    forms = verb_data["forms"]

    correct_answer = forms[form_key]

    options = list(forms.values())
    random.shuffle(options)

    if correct_answer not in options:
        options[random.randint(0, 3)] = correct_answer

    random.shuffle(options)

    keyboard = []

    for option in options:
        keyboard.append([
            InlineKeyboardButton(
                option,
                callback_data=f"verb_answer|{verb}|{form_key}|{option}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f'{translation} / {verb} ({form_label})',
        reply_markup=reply_markup
    )


async def start_noun_quiz(message, context):
    lang = context.user_data.get("lang")
    context.user_data["mode"] = "nouns"

    reinforce_mode = context.user_data.get("reinforce_mode", False)
    mistakes = context.user_data.get("mistakes", [])

    if reinforce_mode and mistakes:
        noun_pool = mistakes.copy()
    else:
        noun_pool = list(NOUN_FORMS_DATA.keys())

    noun = random.choice(noun_pool)
    noun_data = NOUN_FORMS_DATA[noun]

    translation = noun_data[lang]
    article = noun_data["article"]
    forms = noun_data["forms"]

    form_key = random.choice([
        "singular_indef",
        "singular_def",
        "plural_indef",
        "plural_def"
    ])

    form_names = NOUN_FORM_LABELS[lang]


    options = list(forms.values())
    random.shuffle(options)

    keyboard = []
    for option in options:
        keyboard.append([
            InlineKeyboardButton(
                option,
                callback_data=f"noun_answer|{noun}|{form_key}|{option}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    question = t(
        context,
        "noun_question",
        translation=translation,
        word=f"{article} {noun}",
        form=form_names[form_key]
    )

    await message.reply_text(
        question,
        reply_markup=reply_markup
    )

async def send_verb_group_menu(message, context):

    keyboard = [
        [InlineKeyboardButton(t(context, "verb_group_1"), callback_data="verb_group|group1")],
        [InlineKeyboardButton(t(context, "verb_group_2"), callback_data="verb_group|group2")],
        [InlineKeyboardButton(t(context, "verb_group_3"), callback_data="verb_group|group3")],
        [InlineKeyboardButton(t(context, "verb_group_4"), callback_data="verb_group|group4")],
        [InlineKeyboardButton(t(context, "verb_group_all"), callback_data="verb_group|all")],
        [InlineKeyboardButton(t(context, "main_menu"), callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        t(context, "choose_verb_group"),
        reply_markup=reply_markup
    )


async def send_mode_menu(message, context):
    keyboard = [
        [InlineKeyboardButton(t(context, "mode_words"), callback_data="mode|words")],
        [InlineKeyboardButton(t(context, "mode_nouns"), callback_data="mode|nouns")],
        [InlineKeyboardButton(t(context, "mode_verbs"), callback_data="mode|verbs")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        t(context, "choose_mode"),
        reply_markup=reply_markup
    )


async def show_main_menu(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    await message.reply_text(
        t(context, "welcome"),
        reply_markup=build_main_menu()
    )


async def show_topic_menu(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    await message.reply_text(
        t(context, "choose_topic"),
        reply_markup=build_topic_menu(context)
    )

async def send_word_question(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang")
    topic = context.user_data.get("topic")

    if not lang or not topic:
        await message.reply_text(t(context, "settings_missing"))
        return

    topic_words = WORD_QUIZ_DATA[topic]

    remaining_words = context.user_data.get("remaining_words", [])

    # Если слова закончились — начинаем тему заново
    if not remaining_words:
        remaining_words = list(topic_words.keys())
        random.shuffle(remaining_words)
        context.user_data["remaining_words"] = remaining_words

    word_sv = context.user_data["remaining_words"].pop()
    correct_answer = topic_words[word_sv][lang]

    all_answers = [translations[lang] for translations in topic_words.values()]
    wrong_answers = [answer for answer in all_answers if answer != correct_answer]
    random.shuffle(wrong_answers)

    options = wrong_answers[:2]
    options.append(correct_answer)
    random.shuffle(options)

    context.user_data["current_word"] = word_sv
    context.user_data["current_correct_answer"] = correct_answer

    await message.reply_text(
        f'{t(context, "topic_label")}: {topic}\n{t(context, "question", word=word_sv)}',
        reply_markup=build_word_keyboard(context, word_sv, options)
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await show_main_menu(update.message, context)


async def word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang")
    topic = context.user_data.get("topic")

    if not lang:
        await update.message.reply_text(t(context, "choose_lang_first"))
        await show_main_menu(update.message, context)
        return

    if not topic:
        await update.message.reply_text(t(context, "choose_topic_first"))
        await show_topic_menu(update.message, context)
        return

    await send_word_question(update.message, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(t(context, "help"))


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action = data[0]

    if query.data == "main_menu":
        context.user_data.clear()
        await show_main_menu(query.message, context)
        return

    if query.data == "next_word":
        mode = context.user_data.get("mode")

        if mode == "words":
            await send_word_question(query.message, context)

        elif mode == "nouns":
            await start_noun_quiz(query.message, context)

        elif mode == "verbs":
            await start_verb_quiz(query.message, context)

        return

    if query.data == "reinforce_words":
        mode = context.user_data.get("mode")
        context.user_data["reinforce_mode"] = True
        context.user_data["remaining_words"] = []

        if mode == "words":
            await send_word_question(query.message, context)

        elif mode == "nouns":
            await start_noun_quiz(query.message, context)

        elif mode == "verbs":
            await start_verb_quiz(query.message, context)

        return

    if action == "lang":
        selected_lang = data[1]
        context.user_data.clear()
        context.user_data["lang"] = selected_lang
        context.user_data["correct_answers"] = 0
        context.user_data["total_questions"] = 0
        context.user_data["mistakes"] = []
        context.user_data["reinforce_mode"] = False

        await query.message.reply_text(t(context, "lang_selected"))
        await send_mode_menu(query.message, context)
        return

    if action == "mode":
        mode = data[1]
        context.user_data["mode"] = mode

        if mode == "words":
            await show_topic_menu(query.message, context)

        elif mode == "nouns":
            await start_noun_quiz(query.message, context)

        elif mode == "verbs":
            await send_verb_group_menu(query.message, context)

        return

    if action == "noun_answer":
        noun = data[1]
        form_key = data[2]
        selected_answer = data[3]

        lang = context.user_data.get("lang")
        reinforce_mode = context.user_data.get("reinforce_mode", False)

        noun_data = NOUN_FORMS_DATA[noun]

        article = noun_data["article"]
        translation = noun_data[lang]
        form_short = NOUN_FORM_SHORT[form_key]
        correct_answer = noun_data["forms"][form_key]

        context.user_data["total_questions"] = context.user_data.get("total_questions", 0) + 1
        mistakes = context.user_data.get("mistakes", [])

        if selected_answer == correct_answer:
            context.user_data["correct_answers"] = context.user_data.get("correct_answers", 0) + 1

            if reinforce_mode and noun in mistakes:
                mistakes.remove(noun)

            context.user_data["mistakes"] = mistakes
            noun_info = f"{translation} = {article} {noun} ({form_short})"
            result_text = t(context, "noun_correct", word=noun_info, answer=correct_answer)
        else:
            if noun not in mistakes:
                mistakes.append(noun)

            context.user_data["mistakes"] = mistakes
            noun_info = f"{translation} = {article} {noun} ({form_short})"
            result_text = t(context, "noun_wrong", word=noun_info, answer=correct_answer)

        if reinforce_mode and not context.user_data.get("mistakes"):
            context.user_data["reinforce_mode"] = False

        stats_text = t(
            context,
            "stats",
            correct=context.user_data.get("correct_answers", 0),
            total=context.user_data.get("total_questions", 0)
        )

        await query.edit_message_text(
            f"{result_text}\n\n{stats_text}",
            reply_markup=build_after_answer_menu(context)
        )
        return

    if action == "verb_answer":
        verb = data[1]
        form_key = data[2]
        selected_answer = data[3]

        lang = context.user_data.get("lang")
        reinforce_mode = context.user_data.get("reinforce_mode", False)
        group = context.user_data.get("verb_group")

        if group == "all":
            verbs = {}
            for g in VERB_FORMS_DATA.values():
                verbs.update(g)
        else:
            verbs = VERB_FORMS_DATA[group]

        verb_data = verbs[verb]

        translation = verb_data[lang]
        correct_answer = verb_data["forms"][form_key]
        form_label = VERB_FORM_LABELS[form_key][lang]

        context.user_data["total_questions"] = context.user_data.get("total_questions", 0) + 1
        mistakes = context.user_data.get("mistakes", [])

        if selected_answer == correct_answer:
            context.user_data["correct_answers"] = context.user_data.get("correct_answers", 0) + 1

            if reinforce_mode and verb in mistakes:
                mistakes.remove(verb)

            context.user_data["mistakes"] = mistakes

            verb_info = f"{translation} = {verb} ({form_label})"
            result_text = t(context, "verb_correct", word=verb_info, answer=correct_answer)
        else:
            if verb not in mistakes:
                mistakes.append(verb)

            context.user_data["mistakes"] = mistakes

            verb_info = f"{translation} = {verb} ({form_label})"
            result_text = t(context, "verb_wrong", word=verb_info, answer=correct_answer)

        if reinforce_mode and not context.user_data.get("mistakes"):
            context.user_data["reinforce_mode"] = False

        stats_text = t(
            context,
            "stats",
            correct=context.user_data.get("correct_answers", 0),
            total=context.user_data.get("total_questions", 0)
        )

        await query.edit_message_text(
            f"{result_text}\n\n{stats_text}",
            reply_markup=build_after_answer_menu(context)
        )
        return


    if action == "verb_group":
        group = data[1]

        context.user_data["mode"] = "verbs"
        context.user_data["verb_group"] = group

        await start_verb_quiz(query.message, context)

        return

    if action == "topic":
        selected_topic = data[1]
        context.user_data["topic"] = selected_topic
        context.user_data["remaining_words"] = []
        context.user_data["mistakes"] = []
        context.user_data["reinforce_mode"] = False
        context.user_data["correct_answers"] = 0
        context.user_data["total_questions"] = 0

        await query.message.reply_text(
            t(context, "topic_selected", theme=selected_topic)
        )
        await send_word_question(query.message, context)
        return

    if action == "answer":
        word_sv = data[1]
        selected_answer = data[2]

        lang = context.user_data.get("lang")
        topic = context.user_data.get("topic")
        reinforce_mode = context.user_data.get("reinforce_mode", False)

        if not lang or not topic:
            await query.message.reply_text(t(context, "settings_missing"))
            return

        correct_answer = WORD_QUIZ_DATA[topic][word_sv][lang]

        context.user_data["total_questions"] = context.user_data.get("total_questions", 0) + 1
        mistakes = context.user_data.get("mistakes", [])

        if selected_answer == correct_answer:
            context.user_data["correct_answers"] = context.user_data.get("correct_answers", 0) + 1

            if reinforce_mode and word_sv in mistakes:
                mistakes.remove(word_sv)

            context.user_data["mistakes"] = mistakes
            result_text = t(context, "correct", word=word_sv, answer=correct_answer)
        else:
            if word_sv not in mistakes:
                mistakes.append(word_sv)

            context.user_data["mistakes"] = mistakes
            result_text = t(context, "wrong", word=word_sv, answer=correct_answer)

        if reinforce_mode and not context.user_data.get("mistakes"):
            context.user_data["reinforce_mode"] = False

        stats_text = t(
            context,
            "stats",
            correct=context.user_data.get("correct_answers", 0),
            total=context.user_data.get("total_questions", 0)
        )

        await query.edit_message_text(
            f"{result_text}\n\n{stats_text}",
            reply_markup=build_after_answer_menu(context)
        )
        return



app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("word", word))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(button))

print("Bot started...")

app.run_polling()
