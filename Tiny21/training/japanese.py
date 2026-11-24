"""Generate original A1/A2-style English to spaced romaji sentence pairs."""
import argparse
from collections import Counter
from hashlib import blake2s
from itertools import product
import json
from pathlib import Path

from training.codec import CONTEXT, answer_tokens, prompt_tokens
from training.japanese_lexicon import (
    ANIMALS, DRINK, FOOD, LANGUAGES, LISTEN, OBJECT, PEOPLE, PLACES, ROLES, THINGS,
    TIMES, TRANSPORT, VERBS, nouns,
)

NEAR = ('this', 'these', 'kore', 'kono', 'here', 'koko')
MIDDLE = ('that', 'those', 'sore', 'sono', 'there', 'soko')
FAR = ('that over there', 'those over there', 'are', 'ano', 'over there', 'asoko')
POINTS = (NEAR, MIDDLE, FAR)
GREETINGS = (
    ('good morning', 'ohayou gozaimasu'), ('good afternoon', 'konnichiwa'),
    ('good evening', 'konbanwa'), ('good night', 'oyasuminasai'),
    ('thank you', 'arigatou gozaimasu'), ('thank you very much', 'doumo arigatou gozaimasu'),
    ("you're welcome", 'dou itashimashite'), ('excuse me', 'sumimasen'),
    ("i'm sorry", 'gomennasai'), ('nice to meet you', 'hajimemashite'),
    ('see you tomorrow', 'mata ashita'), ('see you later', 'mata ne'),
    ("i don't understand", 'wakarimasen'), ('i understand', 'wakarimasu'),
    ('please say it again', 'mou ichido itte kudasai'),
    ('please speak slowly', 'yukkuri hanashite kudasai'),
    ('what is your name', 'onamae wa nan desu ka'),
    ('how are you', 'ogenki desu ka'), ('i am fine', 'genki desu'),
)
BE = {'first': ('am', 'was'), 'third': ('is', 'was'), 'plural': ('are', 'were')}
CONTRACTION = {
    'i': "i'm", 'you': "you're", 'he': "he's", 'she': "she's", 'we': "we're", 'they': "they're",
}


def key_number(*parts):
    return int.from_bytes(blake2s('|'.join(parts).encode(), digest_size=4).digest(), 'big')


def tagged(category, group, prompt, response):
    return {'category': category, 'fact': f'{category}.{group}', 'prompt': prompt, 'answer': response}


def complements(verb):
    """Return (semantic key, English surfaces, Japanese phrase, potential phrase)."""
    frame = verb.frame
    if frame in OBJECT:
        for noun in OBJECT[frame]:
            yield noun.name, noun.surfaces(), noun.japanese + ' o', noun.japanese + ' ga'
    elif frame == 'destination':
        for english, jp in PLACES:
            if english == 'home':
                surfaces = ('home',)
            else:
                surfaces = ('to ' + english,)
            yield english, surfaces, jp + ' ni', jp + ' ni'
        for _, _, _, _, english, jp in POINTS:
            yield english, (english,), jp + ' ni', jp + ' ni'
    elif frame == 'studying':
        for english, jp in LANGUAGES + (('math', 'suugaku'), ('history', 'rekishi'),
                                       ('kanji', 'kanji'), ('hiragana', 'hiragana')):
            yield english, (english,), jp + ' o', jp + ' ga'
    elif frame == 'language':
        for english, jp in LANGUAGES:
            yield english, (english,), jp + ' o', jp + ' ga'
    elif frame == 'listening':
        for english, jp in LISTEN:
            yield english, ('to ' + english,), jp + ' o', jp + ' ga'
    elif frame in ('meeting', 'help', 'waiting'):
        contacts = (('my friend', 'watashi no tomodachi'), ('my mother', 'haha'),
                    ('my father', 'chichi'), ('the teacher', 'sensei'),
                    ('taro', 'tarou'), ('hanako', 'hanako'))
        for english, jp in contacts:
            if frame == 'waiting':
                surfaces, particle = ('for ' + english,), ' o'
            elif verb.base == 'call':
                surfaces, particle = (english,), ' ni'
            elif frame == 'meeting':
                surfaces, particle = (english, 'with ' + english), ' ni'
            else:
                surfaces, particle = (english,), ' o'
            yield english, surfaces, jp + particle, jp + particle
    elif frame == 'transport':
        for english, jp in TRANSPORT:
            yield english, (english,), jp + ' ni', jp + ' ni'
    elif frame == 'putting':
        for thing, (place, jp) in product(THINGS[:6], (('on the desk', 'tsukue no ue'),
                                                     ('under the chair', 'isu no shita'),
                                                     ('in the box', 'hako no naka'))):
            surfaces = tuple(f'{name} {place}' for name in thing.surfaces())
            phrase = f'{thing.japanese} o {jp} ni'
            yield f'{thing.name} {place}', surfaces, phrase, phrase
    else:
        places = {
            'swim': (('in the pool', 'puuru de'), ('in the sea', 'umi de')),
            'work': (('at the hospital', 'byouin de'), ('at the bank', 'ginkou de'),
                     ('at the shop', 'mise de'), ('at home', 'ie de')),
            'walk': (('in the park', 'kouen de'), ('to the station', 'eki made')),
            'run': (('in the park', 'kouen de'), ('at school', 'gakkou de')),
            'sleep': (('at home', 'ie de'), ('in the car', 'kuruma no naka de')),
            'wake up': (('at six', 'roku ji ni'), ('at eight', 'hachi ji ni')),
            'rest': (('at home', 'ie de'), ('at the hotel', 'hoteru de')),
        }
        yield 'bare', ('',), '', ''
        for english, jp in places[verb.base]:
            yield english, (english,), jp, jp


def phrase(*words):
    return ' '.join(word for word in words if word)


def action_forms(verb, subject, kind):
    plural = kind != 'third'
    do = 'do' if plural else 'does'
    dont = "don't" if plural else "doesn't"
    inflected = verb.base if plural else verb.third
    present, past = verb.stem + 'masu', verb.stem + 'mashita'
    negative, past_negative = verb.stem + 'masen', verb.stem + 'masen deshita'
    yield 'present', f'{subject} {inflected}', present, True
    yield 'past', f'{subject} {verb.past}', past, inflected != verb.past
    for neg in (dont, do + ' not'):
        yield 'negative', f'{subject} {neg} {verb.base}', negative, True
    for neg in ("didn't", 'did not'):
        yield 'past_negative', f'{subject} {neg} {verb.base}', past_negative, True
    yield 'future', f'{subject} will {verb.base}', present, True
    yield 'progressive', f'{subject} {BE[kind][0]} {verb.ing}', verb.te + ' imasu', True
    yield 'past_progressive', f'{subject} {BE[kind][1]} {verb.ing}', verb.te + ' imashita', True
    if subject in CONTRACTION:
        yield 'progressive', f'{CONTRACTION[subject]} {verb.ing}', verb.te + ' imasu', True
    yield 'potential', f'{subject} can {verb.base}', verb.potential + 'masu', True
    for neg in ("can't", 'cannot', 'can not'):
        yield 'potential_negative', f'{subject} {neg} {verb.base}', verb.potential + 'masen', True
    for aux, jp in ((do, present), ('did', past), ('can', verb.potential + 'masu')):
        label = {'did': 'past_question', 'can': 'potential_question'}.get(aux, 'question')
        yield label, f'{aux} {subject} {verb.base}', jp + ' ka', True
    if kind == 'first':
        for prefix in ('i want to', "i'd like to", 'i would like to'):
            yield 'desire', f'{prefix} {verb.base}', verb.stem + 'tai desu', True
        for prefix in ("i don't want to", 'i do not want to'):
            yield 'desire_negative', f'{prefix} {verb.base}', verb.stem + 'takunai desu', True
        yield 'desire_past', f'i wanted to {verb.base}', verb.stem + 'takatta desu', True
        for prefix in ("i didn't want to", 'i did not want to'):
            yield 'desire_past_negative', f'{prefix} {verb.base}', verb.stem + 'takunakatta desu', True
        for prefix in ('i have to', 'i need to'):
            yield 'obligation', f'{prefix} {verb.base}', verb.negative[:-3] + 'nakereba narimasen', True
        yield 'permission', f'may i {verb.base}', verb.te + ' mo ii desu ka', True
    if subject == 'you':
        yield 'desire_question', f'do you want to {verb.base}', verb.stem + 'tai desu ka', True


def actions():
    for verb in VERBS:
        for key, surfaces, obj, capable in complements(verb):
            for subject, jp, kind in PEOPLE:
                if subject == key and verb.frame in ('meeting', 'help', 'waiting'):
                    continue
                group = f'{subject}.{verb.base}.{key}'
                for form, english, answer, bare in action_forms(verb, subject, kind):
                    j_obj = capable if form.startswith('potential') else obj
                    if bare:
                        for surface in surfaces:
                            yield tagged('verb.' + form, group, phrase(english, surface),
                                         phrase(jp, 'wa', j_obj, answer))
                    if form in ('present', 'future', 'negative', 'past', 'past_negative',
                                'progressive', 'past_progressive', 'desire', 'desire_negative'):
                        past = form.startswith('past')
                        allowed = (2, 4, 5, 8) if past else (
                            (1, 6, 7, 9, 10) if form == 'future' else (0, 1, 3, 6, 7, 9, 10))
                        choice = key_number(subject, verb.base, key, form)
                        for step in range(2):
                            time, j_time = TIMES[allowed[(choice + step) % len(allowed)]]
                            surface = surfaces[(choice // len(allowed)) % len(surfaces)]
                            if surface.startswith('at ') and time.startswith('at '):
                                continue
                            core = phrase(english, surface)
                            prompt = phrase(core, time) if (choice + step) % 2 else f'{time}, {core}'
                            yield tagged('verb.time.' + form, group, prompt, phrase(jp, 'wa', j_time, j_obj, answer))
            group = f'{verb.base}.{key}'
            for i, surface in enumerate(surfaces):
                if i > 2:
                    break
                for label, en, ja in (
                    ('request', f'please {verb.base}', verb.te + ' kudasai'),
                    ('negative_request', f"please don't {verb.base}", verb.negative + 'de kudasai'),
                    ('negative_request', f'please do not {verb.base}', verb.negative + 'de kudasai'),
                    ('suggest', f"let's {verb.base}", verb.stem + 'mashou'),
                    ('suggest', f'let us {verb.base}', verb.stem + 'mashou'),
                    ('invite', f"won't you {verb.base}", verb.stem + 'masen ka'),
                ):
                    yield tagged('verb.' + label, group, phrase(en, surface), phrase(obj, ja))


def demonstratives():
    all_things = THINGS + FOOD[:8] + ROLES + ANIMALS
    for singular, plural, standalone, determiner, here, j_location in POINTS:
        for thing in all_things:
            group = f'{singular}.{thing.name}'
            for label, english, japanese in (
                ('identify', f'{singular} is {thing.indefinite}', f'{standalone} wa {thing.japanese} desu'),
                ('identify', f'{singular} is not {thing.indefinite}', f'{standalone} wa {thing.japanese} ja arimasen'),
                ('identify', f'is {singular} {thing.indefinite}', f'{standalone} wa {thing.japanese} desu ka'),
                ('identify', f'{singular} was {thing.indefinite}', f'{standalone} wa {thing.japanese} deshita'),
                ('identify', f'which one is the {thing.name}', f'dore ga {thing.japanese} desu ka'),
                ('identify', f'what is {singular}', f'{standalone} wa nan desu ka'),
                ('location', f'{singular} {thing.name} is {here}', f'{determiner} {thing.japanese} wa {j_location} ni arimasu'),
                ('possessive', f'{singular} is my {thing.name}', f'{standalone} wa watashi no {thing.japanese} desu'),
                ('possessive', f'{singular} is your {thing.name}', f'{standalone} wa anata no {thing.japanese} desu'),
                ('possessive', f'is {singular} your {thing.name}', f'{standalone} wa anata no {thing.japanese} desu ka'),
                ('possessive', f'whose {thing.name} is {singular}', f'{standalone} wa dare no {thing.japanese} desu ka'),
            ):
                if label == 'location' and thing in ROLES + ANIMALS:
                    japanese = japanese.replace('arimasu', 'imasu')
                yield tagged('demonstrative.' + label, group, english, japanese)
            if thing.plural:
                are = f'{standalone} wa {thing.japanese} desu'
                yield tagged('demonstrative.identify', group, f'{plural} are {thing.plural}', are)
                yield tagged('demonstrative.identify', group, f'are {plural} {thing.plural}', are + ' ka')
        for location, jp in PLACES:
            bare = location.removeprefix('the ')
            yield tagged('demonstrative.place', f'{here}.{location}', f'{here} is {location}', f'{j_location} wa {jp} desu')
            yield tagged('demonstrative.place', f'{here}.{location}', f'is the {bare} {here}', f'{jp} wa {j_location} ni arimasu')
            if location.startswith('the ') and here != 'there':
                yield tagged('demonstrative.place', f'{here}.{location}', f'is there a {bare} {here}',
                             f'{j_location} ni {jp} ga arimasu ka')


def copula():
    for subject, jp, kind in PEOPLE:
        now, before = BE[kind]
        for role in ROLES:
            plural = subject in ('we', 'they')
            english = role.plural if plural else role.indefinite
            topic = f'{jp} wa {role.japanese}'
            group = f'{subject}.{role.name}'
            for en, ja in (
                (f'{subject} {now} {english}', 'desu'),
                (f'{subject} {before} {english}', 'deshita'),
                (f'{subject} {now} not {english}', 'ja arimasen'),
                (f'{subject} {before} not {english}', 'ja arimasen deshita'),
                (f'{now} {subject} {english}', 'desu ka'),
                (f'{before} {subject} {english}', 'deshita ka'),
            ):
                yield tagged('copula', group, en, f'{topic} {ja}')
            if subject in CONTRACTION:
                yield tagged('copula', group, f'{CONTRACTION[subject]} {english}', f'{topic} desu')


def locations():
    locales = (('on the desk', 'tsukue no ue'), ('under the chair', 'isu no shita'),
               ('in the bag', 'kaban no naka'), ('in the room', 'heya'),
               ('next to the station', 'eki no tonari'), ('in front of the school', 'gakkou no mae'),
               ('behind the shop', 'mise no ushiro'), ('near the park', 'kouen no chikaku'),
               ('at home', 'ie'), ('at school', 'gakkou'), ('here', 'koko'),
               ('there', 'soko'), ('over there', 'asoko'))
    for noun, (location, place) in product(THINGS[:21] + ANIMALS + ROLES[:3], locales):
        if noun in ANIMALS + ROLES and location in ('in the bag', 'on the desk', 'under the chair'):
            continue
        stem = 'i' if noun in ANIMALS + ROLES else 'ari'
        topic = f'{noun.japanese} wa {place} ni'
        existence = f'{place} ni {noun.japanese} ga'
        group = f'{noun.name}.{place}'
        for label, english, japanese in (
            ('exist', f'there is {noun.indefinite} {location}', f'{existence} {stem}masu'),
            ('exist', f'there are {noun.plural} {location}', f'{existence} {stem}masu'),
            ('exist', f'there was {noun.indefinite} {location}', f'{existence} {stem}mashita'),
            ('exist', f'there is no {noun.name} {location}', f'{existence} {stem}masen'),
            ('exist', f'there are no {noun.plural} {location}', f'{existence} {stem}masen'),
            ('exist', f'is there {noun.indefinite} {location}', f'{existence} {stem}masu ka'),
            ('place', f'the {noun.name} is {location}', f'{topic} {stem}masu'),
            ('place', f'the {noun.name} was {location}', f'{topic} {stem}mashita'),
            ('place', f'the {noun.name} is not {location}', f'{topic} {stem}masen'),
            ('place', f'is the {noun.name} {location}', f'{topic} {stem}masu ka'),
        ):
            if '  ' not in english:
                yield tagged('location.' + label, group, english, japanese)
        # Common answers without a location qualifier use the same lexicon.
        yield tagged('location.where', noun.name, f'where is the {noun.name}',
                     f'{noun.japanese} wa doko ni {stem}masu ka')
    for english, jp in PLACES:
        yield tagged('location.where', english, f'where is {english}', f'{jp} wa doko desu ka')


def adjectives():
    groups = (
        (('big', 'ookii', 'i'), ('small', 'chiisai', 'i'), ('new', 'atarashii', 'i'),
         ('old', 'furui', 'i'), ('expensive', 'takai', 'i'), ('cheap', 'yasui', 'i')),
        (('delicious', 'oishii', 'i'), ('sweet', 'amai', 'i'), ('spicy', 'karai', 'i')),
        (('quiet', 'shizuka', 'na'), ('lively', 'nigiyaka', 'na'), ('clean', 'kirei', 'na'),
         ('famous', 'yuumei', 'na'), ('convenient', 'benri', 'na')),
    )
    for words, targets in zip(groups, (THINGS, FOOD, nouns(
        'town|towns|machi\npark|parks|kouen\nlibrary|libraries|toshokan\n'
        'school|schools|gakkou\nroom|rooms|heya\nrestaurant|restaurants|resutoran\nhotel|hotels|hoteru'))):
        for (word, ja, style), noun in product(words, targets):
            forms = (
                (('is', ja + ' desu'), ('was', ja[:-1] + 'katta desu'),
                 ('is not', ja[:-1] + 'kunai desu'), ('was not', ja[:-1] + 'kunakatta desu'))
                if style == 'i' else
                (('is', ja + ' desu'), ('was', ja + ' deshita'),
                 ('is not', ja + ' ja arimasen'), ('was not', ja + ' ja arimasen deshita'))
            )
            for english, jp in (('the ' + noun.name, noun.japanese), ('this ' + noun.name, 'kono ' + noun.japanese),
                                ('that ' + noun.name, 'sono ' + noun.japanese),
                                ('that ' + noun.name + ' over there', 'ano ' + noun.japanese)):
                group = f'{word}.{english}'
                for verb, ending in forms:
                    yield tagged('adjective.' + style, group, f'{english} {verb} {word}', f'{jp} wa {ending}')
                yield tagged('adjective.' + style, group, f'is {english} {word}', f'{jp} wa {ja} desu ka')
                yield tagged('adjective.' + style, group, f'{english} is very {word}', f'{jp} wa totemo {ja} desu')
            for singular, _, jp, _, _, _ in POINTS:
                if noun.plural:
                    article = 'an' if word[0] in 'aeiou' else 'a'
                    en = f'{singular} is {article} {word} {noun.name}'
                    attr = ja if style == 'i' else ja + ' na'
                    yield tagged('adjective.attributive', f'{noun.name}.{word}', en,
                                 f'{jp} wa {attr} {noun.japanese} desu')


def preferences():
    for (subject, jp, kind), noun in product(PEOPLE, FOOD + DRINK + ANIMALS):
        group = f'{subject}.{noun.name}'
        forms = (
            ('likes' if kind == 'third' else 'like', 'suki desu'),
            ('loves' if kind == 'third' else 'love', 'daisuki desu'),
            ("doesn't like" if kind == 'third' else "don't like", 'suki ja arimasen'),
            ('does not like' if kind == 'third' else 'do not like', 'suki ja arimasen'),
            ('dislikes' if kind == 'third' else 'dislike', 'kirai desu'),
            ('hates' if kind == 'third' else 'hate', 'daikirai desu'),
        )
        for en, ja in forms:
            for noun_surface in (noun.plural or noun.name, 'the ' + noun.name):
                yield tagged('preference', group, f'{subject} {en} {noun_surface}', f'{jp} wa {noun.japanese} ga {ja}')
        do = 'does' if kind == 'third' else 'do'
        yield tagged('preference', group, f'{do} {subject} like {noun.plural or noun.name}',
                     f'{jp} wa {noun.japanese} ga suki desu ka')
    for subject, jp, kind in PEOPLE:
        for word, ja in (('tired', 'tsukarete imasu'), ('busy', 'isogashii desu'),
                         ('hungry', 'onaka ga suite imasu'), ('thirsty', 'nodo ga kawaite imasu'),
                         ('happy', 'ureshii desu'), ('sad', 'kanashii desu')):
            for form in (f'{subject} {BE[kind][0]}', CONTRACTION.get(subject)):
                if form:
                    yield tagged('adjective.state', f'{subject}.{word}', f'{form} {word}', f'{jp} wa {ja}')


def counts():
    counters = (('one', 'hitotsu'), ('two', 'futatsu'), ('three', 'mittsu'),
                ('four', 'yottsu'), ('five', 'itsutsu'), ('six', 'muttsu'),
                ('seven', 'nanatsu'), ('eight', 'yattsu'), ('nine', 'kokonotsu'), ('ten', 'too'))
    for thing, (i, (name, ja)) in product(THINGS[:10] + FOOD[:7], enumerate(counters, 1)):
        for numeral in (name, str(i)):
            noun = thing.name if i == 1 else thing.plural
            for label, english, japanese in (
                ('request', f'{numeral} {noun}, please', f'{thing.japanese} o {ja} kudasai'),
                ('request', f'please give me {numeral} {noun}', f'{thing.japanese} o {ja} kudasai'),
                ('exist', f'there {"is" if i == 1 else "are"} {numeral} {noun}', f'{thing.japanese} ga {ja} arimasu'),
                ('buy', f'i bought {numeral} {noun}', f'watashi wa {thing.japanese} o {ja} kaimashita'),
            ):
                yield tagged('counter.' + label, f'{thing.name}.{name}', english, japanese)
    for i, name, ja in ((1,'one','hitori'), (2,'two','futari'), (3,'three','san nin'),
                        (4,'four','yo nin'), (5,'five','go nin'), (6,'six','roku nin')):
        for numeral in (name, str(i)):
            for noun in ROLES[:3] + nouns('person|people|hito\nfriend|friends|tomodachi'):
                english = noun.name if i == 1 else noun.plural
                yield tagged('counter.people', f'{noun.name}.{name}',
                             f'there {"is" if i == 1 else "are"} {numeral} {english}',
                             f'{noun.japanese} ga {ja} imasu')


def conversation():
    for english, jp in GREETINGS:
        yield tagged('conversation', english, english, jp)
    for english, jp in (('taro', 'tarou'), ('hanako', 'hanako'), ('yuki', 'yuki'),
                        ('ken', 'ken'), ('maria', 'maria'), ('john', 'jon'), ('anna', 'anna')):
        for frame in ('my name is {}', 'i am {}', "i'm {}"):
            yield tagged('conversation.introduction', english, frame.format(english), f'watashi wa {jp} desu')
    for thing in FOOD + DRINK + THINGS[:11]:
        for english in (f'how much is the {thing.name}', f'how much is this {thing.name}',
                        f'how much is that {thing.name}'):
            modifier = 'kono ' if 'this ' in english else 'sono ' if 'that ' in english else ''
            yield tagged('shopping.price', thing.name, english, f'{modifier}{thing.japanese} wa ikura desu ka')
    for singular, _, jp, _, _, _ in POINTS:
        yield tagged('shopping.demonstrative', singular, f'how much is {singular}', f'{jp} wa ikura desu ka')
        yield tagged('shopping.demonstrative', singular, f'{singular}, please', f'{jp} o kudasai')


def question_words():
    for subject, jp, kind in PEOPLE:
        be, past_be = BE[kind]
        for _, _, _, _, place, jp_place in POINTS:
            for auxiliary, japanese in ((be, 'imasu'), (past_be, 'imashita'),
                                        (be + ' not', 'imasen'), (past_be + ' not', 'imasen deshita')):
                yield tagged('location.person', f'{subject}.{place}', f'{subject} {auxiliary} {place}',
                             f'{jp} wa {jp_place} ni {japanese}')
        yield tagged('location.person', subject, f'where {be} {subject}', f'{jp} wa doko ni imasu ka')
    for verb in VERBS:
        for subject, jp, kind in PEOPLE:
            do = 'does' if kind == 'third' else 'do'
            if verb.frame in ('food', 'drink', 'reading', 'writing', 'shopping', 'making', 'media'):
                for aux, ending in ((do, 'masu'), ('did', 'mashita')):
                    yield tagged('question.what', f'{subject}.{verb.base}', f'what {aux} {subject} {verb.base}',
                                 f'{jp} wa nani o {verb.stem}{ending} ka')
                if subject == 'you':
                    yield tagged('question.what', f'{subject}.{verb.base}', f'what do you want to {verb.base}',
                                 f'anata wa nani o {verb.stem}tai desu ka')
            if verb.frame == 'destination':
                for aux, ending in ((do, 'masu'), ('did', 'mashita'), ('will', 'masu')):
                    yield tagged('question.where', f'{subject}.{verb.base}', f'where {aux} {subject} {verb.base}',
                                 f'{jp} wa doko ni {verb.stem}{ending} ka')
                yield tagged('question.where', f'{subject}.{verb.base}', f'where {BE[kind][0]} {subject} {verb.ing}',
                             f'{jp} wa doko ni {verb.stem}masu ka')
    for noun in THINGS + FOOD + DRINK:
        for pronoun, jp, group in (('i', 'watashi', 'first'), ('you', 'anata', 'second')):
            thing = noun.indefinite
            for en, suffix in (('want', 'hoshii desu'), ("don't want", 'hoshikunai desu'),
                               ('wanted', 'hoshikatta desu')):
                yield tagged('desire.noun', f'{pronoun}.{noun.name}', f'{pronoun} {en} {thing}',
                             f'{jp} wa {noun.japanese} ga {suffix}')
            yield tagged('possession.have', f'{pronoun}.{noun.name}', f'{pronoun} have {thing}',
                         f'{jp} wa {noun.japanese} o motte imasu')
            yield tagged('possession.have', f'{pronoun}.{noun.name}', f"{pronoun} don't have {thing}",
                         f'{jp} wa {noun.japanese} o motte imasen')
            if group == 'second':
                yield tagged('possession.have', f'{pronoun}.{noun.name}', f'do you have {thing}',
                             f'anata wa {noun.japanese} o motte imasu ka')
    for singular, _, jp, _, _, _ in POINTS:
        yield tagged('demonstrative.identify', singular, f"what's {singular}", f'{jp} wa nan desu ka')
    for place, jp in PLACES:
        yield tagged('location.where', place, f"where's {place}", f'{jp} wa doko desu ka')
    for noun in THINGS[:15] + FOOD[:7]:
        for word, ja in (('cheaper', 'yasui'), ('more expensive', 'takai'),
                         ('bigger', 'ookii'), ('smaller', 'chiisai')):
            yield tagged('adjective.comparative', f'{noun.name}.{word}',
                         f'this {noun.name} is {word} than that {noun.name}',
                         f'kono {noun.japanese} wa sono {noun.japanese} yori {ja} desu')
            yield tagged('adjective.comparative', f'{noun.name}.{word}',
                         f'which is {word}, this {noun.name} or that {noun.name}',
                         f'kono {noun.japanese} to sono {noun.japanese} to dochira ga {ja} desu ka')


def sequences():
    food = (('eat breakfast', 'asagohan o taberu', 'asagohan o tabeta'),
            ('eat lunch', 'hirugohan o taberu', 'hirugohan o tabeta'),
            ('eat dinner', 'bangohan o taberu', 'bangohan o tabeta'),
            ('drink coffee', 'koohii o nomu', 'koohii o nonda'),
            ('go to school', 'gakkou ni iku', 'gakkou ni itta'),
            ('go to bed', 'neru', 'neta'))
    actions = (('study japanese', 'nihongo o benkyou shimasu'),
               ('read a book', 'hon o yomimasu'), ('watch television', 'terebi o mimasu'),
               ('wash my hands', 'te o araimasu'), ('go home', 'ie ni kaerimasu'),
               ('take a walk', 'sanpo shimasu'))
    for (en, affirmative, past), (action, result) in product(food, actions):
        for when, jp in (('before', affirmative + ' mae ni'), ('after', past + ' ato de')):
            yield tagged('sequence', f'{en}.{action}', f'{when} i {en}, i {action}',
                         f'watashi wa {jp} {result}')
            yield tagged('sequence', f'{en}.{action}', f'i {action} {when} i {en}',
                         f'watashi wa {jp} {result}')


def everyday_life():
    countries = (('japan', 'nihon'), ('america', 'amerika'), ('canada', 'kanada'),
                 ('australia', 'oosutoraria'), ('england', 'igirisu'),
                 ('china', 'chuugoku'), ('korea', 'kankoku'), ('france', 'furansu'))
    cities = (('tokyo', 'toukyou'), ('kyoto', 'kyouto'), ('osaka', 'oosaka'),
              ('yokohama', 'yokohama'), ('new york', 'nyuu yooku'), ('london', 'rondon'))
    for subject, j_subject, kind in PEOPLE:
        be, _ = BE[kind]
        do = 'does' if kind == 'third' else 'do'
        for place, jp in cities + countries:
            group = f'{subject}.{place}'
            live = 'lives' if kind == 'third' else 'live'
            yield tagged('residence', group, f'{subject} {live} in {place}',
                         f'{j_subject} wa {jp} ni sunde imasu')
            yield tagged('residence', group, f'{subject} lived in {place}',
                         f'{j_subject} wa {jp} ni sunde imashita')
            yield tagged('residence', group, f'{subject} {do} not live in {place}',
                         f'{j_subject} wa {jp} ni sunde imasen')
            yield tagged('residence', group, f'{do} {subject} live in {place}',
                         f'{j_subject} wa {jp} ni sunde imasu ka')
            yield tagged('origin', group, f'{subject} {be} from {place}',
                         f'{j_subject} wa {jp} shusshin desu')
            yield tagged('origin', group, f'{subject} came from {place}',
                         f'{j_subject} wa {jp} kara kimashita')
            if subject in CONTRACTION:
                yield tagged('origin', group, f'{CONTRACTION[subject]} from {place}',
                             f'{j_subject} wa {jp} shusshin desu')
        yield tagged('residence', subject, f'where {do} {subject} live',
                     f'{j_subject} wa doko ni sunde imasu ka')
        yield tagged('origin', subject, f'where {be} {subject} from',
                     f'{j_subject} wa doko shusshin desu ka')

    for noun, (en, ja) in product(ANIMALS, (('cute', 'kawaii'), ('big', 'ookii'), ('small', 'chiisai'))):
        for determiner, jp in (('the', ''), ('this', 'kono '), ('that', 'sono ')):
            for cop, ending in (('is', 'i desu'), ('was', 'katta desu'),
                                ('is not', 'kunai desu'), ('was not', 'kunakatta desu')):
                yield tagged('adjective.i', f'{en}.{determiner} {noun.name}',
                             f'{determiner} {noun.name} {cop} {en}',
                             f'{jp}{noun.japanese} wa {ja[:-1]}{ending}')

    transportation = (('bus', 'basu'), ('train', 'densha'), ('car', 'kuruma'),
                      ('bicycle', 'jitensha'), ('taxi', 'takushii'), ('plane', 'hikouki'))
    for place, ja in PLACES:
        for vehicle, ride in transportation:
            yield tagged('travel.by', f'{place}.{vehicle}',
                         f'i go to {place} by {vehicle}' if place != 'home' else f'i go home by {vehicle}',
                         f'watashi wa {ride} de {ja} ni ikimasu')
            yield tagged('travel.by', f'{place}.{vehicle}',
                         f'i went to {place} by {vehicle}' if place != 'home' else f'i went home by {vehicle}',
                         f'watashi wa {ride} de {ja} ni ikimashita')
        yield tagged('travel.how', place,
                     f'how do you get to {place}' if place != 'home' else 'how do you get home',
                     f'{ja} ni dou yatte ikimasu ka')

    for i, hour in enumerate(('ichi ji', 'ni ji', 'san ji', 'yo ji', 'go ji', 'roku ji',
                              'shichi ji', 'hachi ji', 'ku ji', 'juu ji', 'juu ichi ji', 'juu ni ji'), 1):
        for english, minute in ((f"{i} o'clock", ''), (f'{i}:30', ' han'), (f'half past {i}', ' han')):
            yield tagged('time.clock', str(i), f"it's {english}", f'ima wa {hour}{minute} desu')
            yield tagged('time.clock', str(i), f'it is {english}', f'ima wa {hour}{minute} desu')
    yield tagged('time.clock', 'question', 'what time is it', 'ima nan ji desu ka')


def natural_variants(row):
    text, category = row['prompt'], row['category']
    for uncontracted, contracted in (('there is ', "there's "), ('what is ', "what's "),
                                     ('where is ', "where's ")):
        if text.startswith(uncontracted):
            yield {**row, 'prompt': contracted + text[len(uncontracted):]}
            break
    if category in ('verb.request', 'verb.negative_request'):
        if text.startswith('please '):
            action = text.removeprefix('please ')
            yield {**row, 'prompt': f'{action} please'}
            yield {**row, 'prompt': f'{action}, please'}
    elif category.startswith('verb.time.'):
        for english, _ in TIMES:
            if text.startswith(english + ', '):
                yield {**row, 'prompt': f'{text[len(english) + 2:]} {english}'}
                break
            if text.endswith(' ' + english):
                yield {**row, 'prompt': f'{english}, {text[:-(len(english) + 1)]}'}
                break


def group_is_fixed(category, fact):
    return ((category == 'time.clock' and fact.endswith('.question')) or
            (category == 'demonstrative.identify' and fact.endswith(('.this', '.that', '.that over there'))))


def holdout(fact, category, *, extended=False):
    # Keep all inflections and surface variants of one lexical pairing together.
    if category.startswith('conversation') or (extended and group_is_fixed(category, fact)):
        return False
    group = fact[len(category) + 1:]
    if category.startswith('verb.') and group == 'i.eat.apple':
        return True
    # The packed category distinguishes unrelated phenomena with the same lexemes.
    domain = category.split('.', 1)[0]
    return key_number(domain, group) % 17 == 0


def corpus(extended=False):
    rows = {}
    examples = (actions(), demonstratives(), copula(), locations(), adjectives(),
                preferences(), counts(), conversation(), question_words(), sequences())
    if extended:
        examples += (everyday_life(),)
    conflicts = Counter()
    for family in examples:
        for row in family:
            text = row['prompt']
            old = rows.get(text)
            if old is None:
                rows[text] = row
            elif old['answer'] != row['answer']:
                conflicts[row['category']] += 1
    if extended:
        for row in list(rows.values()):
            for variant in natural_variants(row):
                old = rows.setdefault(variant['prompt'], variant)
                if old['answer'] != variant['answer']:
                    conflicts[variant['category']] += 1
    return list(rows.values()), conflicts


def split_corpus(rows, *, extended=False):
    splits = {'train': [], 'validation': []}
    for row in rows:
        prompt, answer = row['prompt'], row['answer']
        question = answer.endswith(' ka') or prompt.startswith(('what ', 'where ', 'how ', 'whose ', 'which '))
        punct = '?' if question else '.'
        # Both the normal English punctuation and bare C64 prompts occur in each split.
        forms = (prompt, prompt + punct)
        destination = 'validation' if holdout(row['fact'], row['category'], extended=extended) else 'train'
        for form in forms:
            if (len(prompt_tokens(form)) + len(answer_tokens(answer)) <= CONTEXT and
                    len(form) <= 104):
                splits[destination].append({**row, 'prompt': form})
    return splits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--extended', action='store_true', help='add everyday scenes and alternative word orders')
    args = parser.parse_args()
    rows, conflicts = corpus(args.extended)
    splits = split_corpus(rows, extended=args.extended)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {'base_pairs': len(rows), 'alternate_targets': dict(conflicts), 'splits': {}}
    for name, data in splits.items():
        with (args.out / f'{name}.jsonl').open('w') as stream:
            for row in data:
                stream.write(json.dumps(row, ensure_ascii=True, separators=(',', ':')) + '\n')
        summary['splits'][name] = {'pairs': len(data), 'categories': dict(sorted(Counter(x['category'] for x in data).items()))}
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print({name: len(data) for name, data in splits.items()})


if __name__ == '__main__':
    main()
