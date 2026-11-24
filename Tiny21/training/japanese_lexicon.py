"""Original beginner English to Japanese vocabulary and verb frames."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Noun:
    name: str
    plural: str
    japanese: str

    @property
    def indefinite(self):
        if not self.plural:
            return self.name
        article = 'an' if self.name[0] in 'aeiou' else 'a'
        return f'{article} {self.name}'

    def surfaces(self):
        forms = [self.indefinite, f'the {self.name}']
        if self.plural:
            forms.extend((self.plural, f'some {self.plural}', f'the {self.plural}'))
        else:
            forms.append(f'some {self.name}')
        return tuple(dict.fromkeys(forms))

    def object(self, number):
        return self.name if number == 0 else self.plural or self.name


def nouns(data):
    return tuple(Noun(*line.split('|')) for line in data.strip().splitlines())


FOOD = nouns('''
apple|apples|ringo
banana|bananas|banana
orange|oranges|orenji
pear|pears|nashi
egg|eggs|tamago
sandwich|sandwiches|sandoitchi
rice ball|rice balls|onigiri
rice||gohan
bread||pan
udon||udon
soba||soba
curry||karee
fish||sakana
meat||niku
vegetables||yasai
cake|cakes|keeki
cookie|cookies|kukkii
soup||suupu
salad|salads|sarada
''')
DRINK = nouns('''
water||mizu
green tea||ocha
tea||koucha
coffee||koohii
milk||gyuunyuu
juice||juusu
soda||saidaa
orange juice||orenji juusu
''')
THINGS = nouns('''
book|books|hon
notebook|notebooks|nooto
pencil|pencils|enpitsu
pen|pens|pen
umbrella|umbrellas|kasa
bag|bags|kaban
ticket|tickets|kippu
newspaper|newspapers|shinbun
magazine|magazines|zasshi
dictionary|dictionaries|jisho
letter|letters|tegami
photo|photos|shashin
picture|pictures|e
chair|chairs|isu
desk|desks|tsukue
bicycle|bicycles|jitensha
car|cars|kuruma
camera|cameras|kamera
watch|watches|udedokei
shoes||kutsu
hat|hats|boushi
shirt|shirts|shatsu
phone|phones|denwa
key|keys|kagi
map|maps|chizu
present|presents|purezento
''')
PLACES = (
    ('school', 'gakkou'), ('work', 'shigoto'), ('home', 'ie'),
    ('the park', 'kouen'), ('the station', 'eki'), ('the library', 'toshokan'),
    ('the shop', 'mise'), ('the hospital', 'byouin'), ('the bank', 'ginkou'),
    ('the airport', 'kuukou'), ('the supermarket', 'suupaa'),
    ('the museum', 'bijutsukan'), ('the restaurant', 'resutoran'),
    ('the hotel', 'hoteru'), ('the post office', 'yuubinkyoku'),
    ('the convenience store', 'konbini'), ('the beach', 'umi'),
    ('tokyo', 'toukyou'), ('kyoto', 'kyouto'), ('japan', 'nihon'),
)
PEOPLE = (
    ('i', 'watashi', 'first'), ('you', 'anata', 'plural'),
    ('he', 'kare', 'third'), ('she', 'kanojo', 'third'),
    ('we', 'watashitachi', 'plural'), ('they', 'karera', 'plural'),
    ('my mother', 'haha', 'third'), ('my father', 'chichi', 'third'),
    ('my older sister', 'ane', 'third'), ('my younger brother', 'otouto', 'third'),
    ('my friend', 'watashi no tomodachi', 'third'),
    ('taro', 'tarou', 'third'), ('hanako', 'hanako', 'third'),
)
ANIMALS = nouns('''
cat|cats|neko
dog|dogs|inu
bird|birds|tori
rabbit|rabbits|usagi
''')
ROLES = nouns('''
teacher|teachers|sensei
student|students|gakusei
doctor|doctors|isha
nurse|nurses|kangoshi
office worker|office workers|kaishain
beginner|beginners|shoshinsha
''')
LANGUAGES = (('japanese', 'nihongo'), ('english', 'eigo'), ('chinese', 'chuugokugo'),
             ('korean', 'kankokugo'), ('french', 'furansugo'), ('spanish', 'supeingo'))


@dataclass(frozen=True)
class Verb:
    base: str
    third: str
    past: str
    ing: str
    stem: str
    te: str
    negative: str
    potential: str
    frame: str


def verbs(data):
    return tuple(Verb(*line.split('|')) for line in data.strip().splitlines())


VERBS = verbs('''
eat|eats|ate|eating|tabe|tabete|tabenai|taberare|food
drink|drinks|drank|drinking|nomi|nonde|nomanai|nome|drink
read|reads|read|reading|yomi|yonde|yomanai|yome|reading
write|writes|wrote|writing|kaki|kaite|kakanai|kake|writing
buy|buys|bought|buying|kai|katte|kawanai|kae|shopping
sell|sells|sold|selling|uri|utte|uranai|ure|shopping
make|makes|made|making|tsukuri|tsukutte|tsukuranai|tsukure|making
watch|watches|watched|watching|mi|mite|minai|mirare|media
listen|listens|listened|listening|kiki|kiite|kikanai|kike|listening
speak|speaks|spoke|speaking|hanashi|hanashite|hanasanai|hanase|language
study|studies|studied|studying|benkyou shi|benkyou shite|benkyou shinai|benkyou deki|studying
go|goes|went|going|iki|itte|ikanai|ike|destination
come|comes|came|coming|ki|kite|konai|korare|destination
return|returns|returned|returning|kaeri|kaette|kaeranai|kaere|destination
walk|walks|walked|walking|aruki|aruite|arukanai|aruke|action
run|runs|ran|running|hashiri|hashitte|hashiranai|hashire|action
swim|swims|swam|swimming|oyogi|oyoide|oyoganai|oyoge|action
sleep|sleeps|slept|sleeping|ne|nete|nenai|nerare|action
wake up|wakes up|woke up|waking up|oki|okite|okinai|okirare|action
work|works|worked|working|hataraki|hataraite|hatarakanai|hatarake|action
rest|rests|rested|resting|yasumi|yasunde|yasumanai|yasume|action
wait|waits|waited|waiting|machi|matte|matanai|mate|waiting
meet|meets|met|meeting|ai|atte|awanai|ae|meeting
take|takes|took|taking|tori|totte|toranai|tore|photos
open|opens|opened|opening|ake|akete|akenai|akerare|doors
close|closes|closed|closing|shime|shimete|shimenai|shimerare|doors
use|uses|used|using|tsukai|tsukatte|tsukawanai|tsukae|objects
wash|washes|washed|washing|arai|aratte|arawanai|arae|washing
put|puts|put|putting|oki|oite|okanai|oke|putting
ride|rides|rode|riding|nori|notte|noranai|nore|transport
play|plays|played|playing|shi|shite|shinai|deki|sports
borrow|borrows|borrowed|borrowing|kari|karite|karinai|karirare|objects
lend|lends|lent|lending|kashi|kashite|kasanai|kase|objects
learn|learns|learned|learning|narai|naratte|narawanai|narae|studying
help|helps|helped|helping|tetsudai|tetsudatte|tetsudawanai|tetsudae|help
look for|looks for|looked for|looking for|sagashi|sagashite|sagasanai|sagase|objects
call|calls|called|calling|denwa shi|denwa shite|denwa shinai|denwa deki|meeting
''')

# Each action frame lists English complements and its Japanese particle.
# These combinations are restricted to useful beginner utterances.
OBJECT = {
    'food': FOOD, 'drink': DRINK, 'shopping': FOOD + DRINK + THINGS,
    'reading': (THINGS[0], THINGS[1], THINGS[7], THINGS[8], THINGS[9], THINGS[10]),
    'writing': nouns('letter|letters|tegami\nname|names|namae\nanswer|answers|kotae\nsentence|sentences|bun\nmessage|messages|messeeji'),
    'making': FOOD[:8] + nouns('lunch||hirugohan\nbreakfast||asagohan\ndinner||bangohan'),
    'media': nouns('movie|movies|eiga\nvideo|videos|douga\ntelevision||terebi\ngame|games|shiai'),
    'photos': nouns('photo|photos|shashin'),
    'doors': nouns('door|doors|doa\nwindow|windows|mado\nbox|boxes|hako'),
    'objects': (THINGS[1], THINGS[2], THINGS[3], THINGS[4], THINGS[5], THINGS[9], THINGS[19], THINGS[24], THINGS[25]),
    'washing': nouns('apple|apples|ringo\nshirt|shirts|shatsu\ncar|cars|kuruma\nplate|plates|sara\ncup|cups|koppu'),
    'sports': nouns('tennis||tenisu\nsoccer||sakkaa\nbaseball||yakyuu\nbasketball||basuketto booru'),
}
LISTEN = (('music', 'ongaku'), ('the radio', 'rajio'), ('japanese music', 'nihon no ongaku'),
          ('the song', 'uta'), ('the news', 'nyuusu'))
TRANSPORT = (('the bus', 'basu'), ('the train', 'densha'), ('a bicycle', 'jitensha'),
             ('the subway', 'chikatetsu'), ('a taxi', 'takushii'))
TIMES = (('today', 'kyou'), ('tomorrow', 'ashita'), ('yesterday', 'kinou'),
         ('every day', 'mainichi'), ('this morning', 'kesa'), ('last night', 'yuube'),
         ('tonight', 'konban'), ('next week', 'raishuu'), ('last week', 'senshuu'),
         ('on monday', 'getsuyoubi ni'), ('at seven', 'shichi ji ni'))
