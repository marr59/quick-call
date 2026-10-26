"""Build the agent script: consent disclosure, one-question-at-a-time turn control, guard rails."""

TEMPLATES = {
    "en": dict(
        intro='"Hi, is this {name}? My name is {caller}. Before we start, I\'m an automated assistant '
              'calling on behalf of {behalf} about {topic}, and this call is being recorded. '
              'Is it alright if I ask you a few quick questions?"',
        refuse='If they say no or refuse: "Understood, thank you for your time. Have a good day." Then end_call.',
        agree='If they agree, ask these ONE AT A TIME. After each question stop talking and wait for a full '
              'answer; never interrupt; if the answer is unclear, ask once to repeat; acknowledge briefly '
              '("Got it", "Thank you") and move on:',
        close='Then: "Thank you, {name}, that is everything I needed. We will review and get back to you. '
              'Have a good day." Then end_call.',
        guard='If they ask who exactly the employer is, about pay, or anything outside the questions, say: '
              '"I am only collecting the initial details; a person will follow up with specifics." '
              'If they say goodbye at any point, say goodbye and end_call.',
    ),
    "ru": dict(
        intro='"Здравствуйте, это {name}? Меня зовут {caller}. Прежде чем начать: я автоматический помощник, '
              'звоню от имени {behalf} по поводу {topic}, разговор записывается. '
              'Можно задать вам несколько коротких вопросов?"',
        refuse='Если отказывается: "Понял, спасибо за ваше время, всего доброго." Затем end_call.',
        agree='Если соглашается, задавай вопросы ПО ОДНОМУ. После каждого вопроса замолчи и дождись полного '
              'ответа; никогда не перебивай; если ответ неясен, один раз попроси повторить; коротко подтверди '
              '("Понятно", "Спасибо") и переходи дальше:',
        close='Затем: "Спасибо, {name}, это всё, что мне нужно. Мы рассмотрим и свяжемся с вами. Всего доброго." '
              'Затем end_call.',
        guard='Если спрашивают, кто именно работодатель, про оплату или что-то вне вопросов, скажи: '
              '"Я только собираю первичные данные, по деталям с вами свяжется человек." '
              'Если прощаются, попрощайся и end_call. Говори по-русски.',
    ),
}


def build_script(lang, name, caller, behalf, topic, questions):
    """The whole agent behaviour is this text; the ElevenLabs agent prompt is just {{script}}."""
    t = TEMPLATES[lang]
    f = dict(name=name, caller=caller, behalf=behalf, topic=topic)
    lines = ["Wait for the person to answer first. Then follow this exactly:", "",
             t["intro"].format(**f), "", t["refuse"], "", t["agree"], ""]
    lines += ['%d. "%s"' % (i + 1, q.strip()) for i, q in enumerate(questions) if q.strip()]
    lines += ["", t["close"].format(**f), "", t["guard"]]
    return "\n".join(lines)
