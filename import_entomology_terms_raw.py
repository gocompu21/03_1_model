import os
import sys
import django
import re

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

RAW_TEXT = """
Abies aphid 
Acantholyda parki 
acaricide 
Aceria japonica 
acetylcholine (Ach) 
Acizzia jamatonica 
Acrididae 
Aculops chinonei 
Adelgidae 
Adoretus tenuimaculatus 
Agelastica coerulea 
aggregation pheromone 
agricultural chemicals 
Agromyzidae 
alarm pheromone 
Albizia psyllid 
Aleyrodidae 
allelochemical 
allelopathy 
allomone 
Alnus ambrosia beetle 
ametabolous 
Amphitetranychus viennensis 
Ancylis sativa 
Anomis privata 
Anomoneura mori 
Anoplophora chinensis 
antennae 
anti-aggregation pheromone 
antibiosis 
antixenosis 
Apareophora forsythiae 
Aphididae 
Aphis crinosa 
Aphis gossypії 
Aphis spiraecola 
apodeme 
apophyses 
aposematic coloration 
Apterygota 
Arachnida 
Archeognatha 
Arctiinae 
Arge pagana 
Arge similis 
Argidae 
Argopistes biplagiatus 
Armored scale 
Aromia bungii 
Arthropoda 
Asterolecaniidae 
Attelabidae 
attractant 
attractant gland 
attractant trap logs 
Aulacaspis rosae 
autoparasite 
Azaelea lace bug 
Azalea argid sawfly 
Bacillus thuringiensis 
bait trap 
Bamboo zygaenid 
banker plants 
basement membrane 
batesian mimicry 
beating 
Beauveria bassiana 
benzoylphenylurea insecticide 
biocenose 
biological concentration 
biological control 
Black locust midge 
Black pine bast scale 
Black-back prominent 
blastoderm 
Blattodea 
Box-tree pyralid 
brood parasite 
Brown chafer 
Brown winged green bug 
Buprestidae 
Cacopsylla tobirae 
Californian maple aphid 
Caligula japonica 
Caliroa carinata 
campaniform sensilla 
campodeiform 
carbamate insecticide 
carnivore 
Cecidomyiidae 
Celtis shivaphis 
Celtisaspis japonica 
central nervous system 
Cerambycidae 
Ceratovacuna nekoashi 
Cercopidae 
Ceroplastes ceriferus 
Ceroplastes japonicus 
Ceroplastes rubens 
Chaitophorus saliniger 
chemical control 
Chelicerata 
chemoreceptor 
chemosterilant 
Cherry spider mite 
Cherry tree borer 
Chestnut curculio 
Chestnut gall wasp 
Chiasmia cinerearia 
Chilli thrips 
Chinese hairy aphid 
chordotonal organ 
chorion 
Chrysomela vigintipunctata 
Chrysomelidae 
Chrysomphalus bifasciculatus 
Cicadellidae 
Cicadidae 
Cinara pinidensiflorae 
Cinara piniformosana 
circalunar rhythm 
circannual rhythm 
circulatory system 
Citrus whitefly 
classical conditioning 
clostera anachoreta 
Clostera anastomosis 
clypeus 
coarctate 
Coccidae 
Coccinelloid flea beetle 
Coleoptera 
Collembola 
complete metamorphosis 
compound eye 
Conogethes punctiferalis 
contact insecticide 
Coreidae 
corpora allata 
corpora cardiaca 
Corythucha ciliata 
Cotton aphid 
Cotton leaf roller 
Cottony cushion scale 
coxa 
Crape myrtle aphid 
crepuscular 
Crisicoccus pini 
cross-resistance 
Crustacea 
cryptic coloration 
Cryptotympana atrata 
Curculio sikkimensis 
Curculionidae 
cursorial 
Cyamophila willieti 
Cyllorhynchites ursulus quercuphillus 
Cymbidium scale 
Cynipidae 
darkening 
Dendrolimus spectabilis 
dermal light sense 
Dermaptera 
Dialeurodes citri 
diapause 
Diaspididae 
digestive organ 
Dinipponaphis autumna 
Diplura 
Diprionidae 
Diptera 
diurnal 
dorsal ocelli 
dorsal vessel 
Dotted white geometrid 
Dryocosmus kuriphilus 
Dryophthoridae 
ecdysial line 
ecdysis 
ecdysteroid 
ecological control 
economic injury level (EIL) 
economic threshold (ET) 
ectoderm 
Ectognathous 
ectoparasite 
egg 
elateriform 
Elcysma westwoodi 
elytra 
Embioptera 
embryogenesis 
emergence box 
Endoclyta excrescens 
endoderm 
endogenous entrainment 
endoparasite 
Endopterygota 
Entognathous 
entrainment 
Ephemeroptera 
epicranium 
epicuticle 
epidermis 
Epilachna quadricollis 
Ericerus pela 
Eriococciidae 
Eriococcus lagerstroemiae 
Eriophyes buxis 
Eriophyidae 
Eriophyoid mite 
eruciform 
Eulachnus thunbergi 
Eulecanium kunoense 
Eumeta japonica 
Euonymus gall midge 
Euonymus scale 
Euproctis pseudoconspersa 
Euproctis subflava 
Eurytomidae 
eusocial 
exarate 
excretory system 
exogenous entrainment 
Exopterygota 
exoskeleton 
Fall webworm 
False oleander scale 
fat body 
femur 
fertilization 
filter chamber 
flagellum 
Flatidae 
flushing method 
foregut 
fossorial 
frons 
Frosted moth-bug 
Fulgoridae 
fumigant 
Fuscartona funeralis 
gall 
gall-inducing pest 
Gastrolina depressa 
Geisha distinctissima 
Gelechiidae 
gena 
general equilibrium position (GEP) 
Geometridae 
Giant bagworm 
Giant silk moth 
Glyphodes perspectalis 
Glyphodes pyloalis 
granulosis virus (GV) 
Grape myrtile scale 
Green broad-winged plant-hopper 
Green peach aphid 
Grylloblattodea 
Gryllotalpidae 
gustatory receptor 
Gypsy moth 
habituation 
haemolymph 
halteres 
hardening 
Haritalodes derogata 
haustellate mouthparts 
head capsule 
hemelytra 
hemimetabolous 
Hemiptera 
Hemipteroids 
Henosepilachna vigintioctomaculata 
Hepialidae 
herbivore 
Heteroptera 
Hexapods 
Hibiscus leaf caterpillar 
hindgut 
holometabolous 
Homadaula anisocentra 
Homoptera 
Hyalopterus pruni 
Hymenoptera 
hyperparasite 
Hyphantria cunea 
hypognathous 
hypopharynx 
Icerya purchasi 
identification 
imprinting 
incomplete metamorphosis 
Indian wax scale 
infochemical 
inorganic insecticide 
Insecta 
insecticide 
Insecticide Resistance Action Committee (IRAC) 
instrumental learning 
integrated pest management (IPM) 
integument 
Ivela auripes 
Japanese alder leaf beetle 
Japanese pine sawyer 
Japanese red pine aphid 
Japanese walking-stick 
Japanese wax scale 
Johnston's organ 
Juniper bark borer 
juvenile hormone (JH) 
kairomone 
key pests 
kinesis 
Korean blackish cicada 
Korean pine webworm 
labium 
labrum 
lac gland 
Lantern fly 
Large reddish blant-tipped moth 
Larger potato lady beetle 
larvae 
Lasiocampidae 
latent learning 
lateral ocelli 
leaf eating pest 
legal control 
Lepidoptera 
Lepidosaphes pini 
Lepidosaphes pinnaeformis 
Leptoypha wuorentausi 
light trap 
Limacodidae 
Lycorma delicatula 
Lygaeidae 
Lymantria dispar 
Lymantrinae 
macrolide insecticide 
Macrophya timida 
Malaise trap 
Malpighian tubule 
mandibles 
Mantodea 
Mantophasmatodea 
Masakimyia pustulae 
Matsucoccus matsumurae 
Matsucoccus thunbergianae 
maxillae 
Mealy plum aphid 
mechanical control 
mechanoreceptor 
Mecoptera 
Membracidae 
Merostomata 
mesenteron 
mesoderm 
mesothorax 
metamorphosis 
Metarhizium anisopliae 
metathorax 
Metcalfa pruinosa 
midgut 
migration 
mimesis 
Mimosa webworm 
Mindarus japonicus 
Miridae 
molting 
molting hormone 
Monema flavescens 
Monochamus alternatus 
Monochamus saltuarius 
monophagous 
Monophlebidae 
morphogenesis 
mouthparts 
Mulberry sucker 
multiple-resistance 
mycetome 
Myriapoda 
Myzus persicae 
naiad 
Naratettix rubrovittatus 
natatorial 
Naxa seriaria 
negative correlated cross-resistance 
neonicotinoide insectide 
Neoptera 
nereistoxin insecticide 
nervous system 
Nesodiprion japonicus 
Neuroptera 
neurosecretory cell 
neurotransmitter 
Nipponaphis coreana 
Noctuidae 
nocturnal 
Notodontidae 
notum 
nuclear polyhedrosis virus (NPV) 
nymph 
Oak nut weevil 
Obolodiplosis robiniae 
obtect 
occiput 
ocelli 
Odonata 
oenocyte 
olfactory receptor 
Oligonychus ununguis 
oligophagous 
ommatidium 
omnivore 
oogenesis 
opisthognathous 
Orchestes sanguinipes 
organic insecticide 
organochloride insecticide 
organophosphorous insecticide 
Oriental moth 
Oriental tussock moth 
Oriental woolly aphid 
orientation behavior 
Orthaga olivacea 
Orthoperoids 
Orthoptera 
oviposition 
Pagoda tree looper 
Paleoptera 
Pamphiliidae 
Pancrustacea 
Papilionidae 
Paracolopha morrisoni 
parasitoid 
parthenogenesis 
Peach pyralid moth 
Pear lace bug 
pedicel 
Pellucid zygaenid 
Pentatomidae 
peripheral nervous system 
Periphyllus californiensis 
Periphyllus koelreuteriae 
Phalera assimilis 
Phasmatodea 
pheromone 
pheromone trap 
Phlaeothripidae 
photoreceptor 
Phthiraptera 
Phylloxeridae 
physical control 
phytophagy 
phytotoxicity 
Pieridae 
Pine bark beetle 
Pine caterpillar 
Pine green sawfly 
Pine mealybug 
Pine needle gall midge 
Pine oystershell scale 
Pineus orientalis 
pitfall trap 
Platypodinae 
Platypus koryoensis 
Plautia stali 
Plecoptera 
pleuron 
Plum globose scale 
Pochazia shantungensis 
poison gland 
polymorphism 
polyphagous 
potential pest 
presocial 
pressure receptor 
pressurized micro-injection method 
Prociphilus oriens 
proctodaeum 
procuticle 
prognathous 
protective coloration 
Protegira songi 
prothoracic gland 
prothoracicotropic hormone (PTTH) 
prothorax 
Protura 
Pryeria sinica 
Pseudaulacaspis cockerelli 
Pseudaulacaspis pentagona 
Pseudaulacaspis prunicola 
Pseudococcidae 
Psocoptera 
scavenger 
Psychidae 
Psyllidae 
scientific name 
Pterophoridae 
Pycnogonida 
Pyralidae 
Pyrrhalta humeralis 
Ramulus irregulariterdentatus 
raptorial 
Red wax scale 
Reddish-tipped prominent 
Red-necked longicorn 
reflex arc 
repellent 
repugnatorial gland 
resurgence 
Rhopalosiphum rufiabdominale 
Rhopobota naevana 
Rhus eriophyiid mite 
Ricaniidae 
Rice root aphid 
Rose argid sawfly 
Rose scale 
Sakhalin pine longicorn beetle 
Salix leaf beetle 
saltatorial 
saprophage 
Sarucallis kahawaluokalani 
Sasaki cherry aphid 
scape 
Scarabaeidae 
scarabaeiform 
Psocoptera 
scavenger 
Psychidae 
scientific name 
Pterophoridae 
Pycnogonida 
Pyrrhalta humeralis 
Scirtothrips dorsalis 
sclerotization 
Scolytinae 
Scolytus frontails 
seed & cone pest 
Semanotus bifasciatus 
semiochemical 
sensory organ 
Sesiidae 
seta 
sex pheromone 
Shivaphis celtis 
silk gland 
Singapora shinshana 
Siphonaptera 
Siricidae 
social parasite 
spermatheca 
Sphingidae 
spiracle 
Spiraea aphid 
spore forming bacteria 
Spruce spider mite 
spur 
staturniidae 
stemmata 
Stephanitis fasciicarina 
Stephanitis nashi 
Stephanitis pyrioides 
sternum 
sticky trap 
sting 
stomach poison 
stomodaeum 
Strepsiptera 
stretch receptor 
String cottony scale 
Styrax gall aphid 
subgenual organ 
sucking pest 
sulcus 
suture 
sweeping 
Swift moth 
Sycamore lace bug 
Synanthedon bicingulata 
synapse 
synomone 
synthetic pyrethroid insectocide 
systemic insecticide 
Takahashia japonica 
tanning 
tarsus 
taxis 
Tea red spider mite 
Tea tussock moth 
tegmina 
Tenthredinidae 
Tetranychidae 
Tetranychus kanzawai 
Tetranychus urticae 
Tettigoniidae 
Thecodiplosis japonensis 
Thripidae 
Thysanoptera 
Thysanura 
tibia 
Tingidae 
Tinocallis zelkowae 
Tobira sucker 
tolerance 
Tomicus piniperda 
Tortricidae 
Torymidae 
trachea 
suction trap 
tracheole 
trail pheromone 
tree boring pests 
trichoform sensilla 
Trichoptera 
trochanter 
trunk injection 
Tuberocephalus sasakii 
Two-spotted spider mite 
tympanal organ 
Ume leaf roller 
Unaspis euonymi 
venation 
vermiform 
vertex 
Viburnum leaf beetle 
visceral nervous system 
vitelline membrane 
vitellogenesis 
Walnut leaf beetle 
wax gland 
wax layer 
White peach scale 
White prunicola scale 
White spotted longicorn beetle 
White wax scale 
Willow lace bug 
Xylosandrus germanus 
Yellow-legged tussock moth 
yellow-pan trap 
Yellow-tipped prominent 
Yponomeutidae 
Zelkova aphid 
Zelkova jumping weevil 
zoophagy 
Zoraptera 
Zygaenidae
"""

def import_raw_terms():
    # 수목해충학 과목 
    glossary_subject, _ = Subject.objects.get_or_create(name='수목해충학')
    
    # 텍스트 파싱
    raw_lines = RAW_TEXT.strip().split('\n')
    
    processed_terms = set()
    
    for line in raw_lines:
        line = line.strip()
        if not line or len(line) < 2:
            continue
            
        # 슬래시(/)나 괄호 처리: 분리하는 것이 좋을지?
        # 예: "매미과/아목" -> "매미과", "매미아목" (문맥상)
        # 하지만 단순히 분리하자.
        
        parts = re.split(r'[/,]', line)
        for part in parts:
            part = part.strip()
            # 괄호 제거 (선택적) 또는 괄호 포함? 
            # 예: "선녀벌레(과)" -> "선녀벌레", "선녀벌레과" 의미일 수 있음.
            # 일단 괄호 제거하고 저장
            part_cleaned = re.sub(r'\s*\(.*?\)', '', part)
            if part_cleaned and len(part_cleaned) >= 2:
                processed_terms.add(part_cleaned)
            
            # 괄호 내용이 중요하다면? 
            # 사용자가 리스트를 깔끔하게 줬으므로 최대한 그대로 쓰는 게 안전할 수도.
            # 하지만 "미국선녀벌레/흰불나방" 처럼 명확히 다른 것은 분리해야 함.
            
    print(f"추출된 용어 수: {len(processed_terms)}개")
    
    created_count = 0
    error_count = 0
    
    for word in processed_terms:
        try:
            # 이미 존재하는지 확인 (전체 용어 대상)
            # iexact로 대소문자 무시하고 중복 체크를 먼저 해볼 수도 있음
            if Term.objects.filter(word__iexact=word).exists():
                 term = Term.objects.filter(word__iexact=word).first()
                 created = False
            else:
                 term = Term.objects.create(word=word)
                 created = True
            
            # 해충학 과목 추가
            if glossary_subject not in term.subjects.all():
                term.subjects.add(glossary_subject)
                
            if created:
                created_count += 1
                
        except Exception as e:
            print(f"오류 ({word}): {e}")
            error_count += 1
                
    print(f"처리 완료. 신규 등록: {created_count}개, 오류: {error_count}개")

if __name__ == "__main__":
    import_raw_terms()
