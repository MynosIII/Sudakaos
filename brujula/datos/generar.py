"""Genera datos/ejes.json, datos/preguntas.json y datos/figuras.json (12 ejes + certeza).

    python brujula/datos/generar.py

Banco base: preguntas de 12axes (politicaltests, licencia MIT, (c) 2020 8values / SapplyValues), traducidas y
adaptadas a Latinoamérica: 14 por eje (4 originales de niveles 3 y 1, más 10 de base_ampliada.py con niveles 1 a 4),
más preguntas con condimento local por país.
Cada pregunta: e = {eje: peso}; peso negativo = estar de acuerdo empuja al polo 'a' (0), positivo al polo 'b' (100).
nivel = intensidad de la frase (1 moderada … 4 extrema): sirve para medir qué tan amplia es la posición (certeza).
Las posiciones de los dirigentes son codificación editorial A REVISAR (ver figuras_base.json).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_ampliada import AMPLIADA  # noqa: E402
from base_argentina import AR_EXTRA  # noqa: E402
from ejes_ampliados import EJES2, NUEVAS, SEC  # noqa: E402

D = Path(__file__).resolve().parent
PAISES = ["ar", "br", "py", "pe", "cl", "co", "uy"]
TODAS = ["general", *PAISES]

EJES = [
    ("fed", "Territorio", "Federal", "Unitario", "Provincias y municipios con poder propio.", "Un gobierno nacional fuerte que decide para todos.",
     ("Território", "Federal", "Unitário")),
    ("dem", "Gobierno", "Democracia", "Autoridad", "Las decisiones las toma la gente votando.", "Mejor que decidan líderes fuertes o expertos.",
     ("Governo", "Democracia", "Autoridade")),
    ("int", "Mundo", "Internacionalismo", "Nacionalismo", "Cooperación internacional y organismos globales.", "Soberanía primero y desconfianza del exterior.",
     ("Mundo", "Internacionalismo", "Nacionalismo")),
    ("mil", "Defensa", "Militarismo", "Pacifismo", "Fuerzas Armadas fuertes y opción militar sobre la mesa.", "Diplomacia ante todo y menos gasto militar.",
     ("Defesa", "Militarismo", "Pacifismo")),
    ("lib", "Seguridad", "Orden", "Libertades", "Más poder a la policía y al Estado para garantizar el orden.", "Libertades civiles por encima del control del Estado.",
     ("Segurança", "Ordem", "Liberdades")),
    ("col", "Propiedad", "Colectivismo", "Propiedad privada", "Redistribución y propiedad colectiva.", "Propiedad privada, herencia y capitalismo.",
     ("Propriedade", "Coletivismo", "Propriedade privada")),
    ("rel", "Religión", "Laicismo", "Religiosidad", "Religión fuera del Estado y de la política.", "La religión como guía de la vida social.",
     ("Religião", "Laicismo", "Religiosidade")),
    ("pro", "Valores", "Progresismo", "Tradición", "Ampliación de derechos y cambio cultural.", "Familia, costumbres y tradición.",
     ("Valores", "Progressismo", "Tradição")),
    ("mig", "Cultura", "Asimilación", "Multiculturalismo", "Una cultura común a la que se adapta quien llega.",
     "Diversidad cultural, la de quienes llegan y la de los pueblos originarios.",
     ("Cultura", "Assimilação", "Multiculturalismo")),
    ("pla", "Economía", "Planificación", "Mercado", "Estado que regula, planifica y cobra más a los ricos.", "Mercado libre, menos impuestos y menos regulación.",
     ("Economia", "Planejamento", "Mercado")),
    ("glo", "Comercio", "Proteccionismo", "Apertura", "Aranceles y producción nacional.", "Libre comercio y apertura al mundo.",
     ("Comércio", "Protecionismo", "Abertura")),
    ("tec", "Tecnología y ambiente", "Tecnología", "Bioconservadurismo", "Confianza en la ciencia, la tecnología y el progreso.", "Frenar la tecnología para cuidar el ambiente y la vida.",
     ("Tecnologia e ambiente", "Tecnologia", "Bioconservadorismo")),
]

EN_EJES = {"fed": {"nombre": "Territory", "a": "Federal", "b": "Unitary"}, "dem": {"nombre": "Government", "a": "Democracy", "b": "Authority"},
           "int": {"nombre": "World", "a": "Internationalism", "b": "Nationalism"}, "mil": {"nombre": "Defense", "a": "Militarism", "b": "Pacifism"},
           "lib": {"nombre": "Security", "a": "Order", "b": "Liberties"}, "col": {"nombre": "Property", "a": "Collectivism", "b": "Private property"},
           "rel": {"nombre": "Religion", "a": "Secularism", "b": "Religiosity"}, "pro": {"nombre": "Values", "a": "Progressivism", "b": "Tradition"},
           "mig": {"nombre": "Culture", "a": "Assimilation", "b": "Multiculturalism"}, "pla": {"nombre": "Economy", "a": "Planning", "b": "Markets"},
           "glo": {"nombre": "Trade", "a": "Protectionism", "b": "Openness"}, "tec": {"nombre": "Technology & environment", "a": "Technology", "b": "Bioconservatism"}}

# (id, eje, nivel firmado: + polo a / - polo b, texto es, texto pt)
BASE = [
    ("fed", 3, "Las leyes provinciales y municipales deberían estar por encima de las leyes nacionales.", "As leis estaduais e municipais deveriam estar acima das leis federais."),
    ("fed", 1, "Los gobiernos locales entienden mejor a sus vecinos que el gobierno nacional.", "Os governos locais entendem melhor seus cidadãos do que o governo federal."),
    ("fed", -1, "Hay muchos temas que no tiene sentido resolver a nivel provincial o local.", "Há muitos temas que não faz sentido resolver no nível estadual ou local."),
    ("fed", -3, "Un gobierno nacional fuerte es indispensable para proteger a todos los ciudadanos.", "Um governo federal forte é indispensável para proteger todos os cidadãos."),
    ("dem", 3, "Mientras más gente participe de una decisión, más chances hay de que sea la correcta.", "Quanto mais gente participa de uma decisão, maior a chance de ela ser a certa."),
    ("dem", 1, "El pueblo tiene que poder elegir a sus gobernantes, siempre.", "O povo tem que poder escolher seus governantes, sempre."),
    ("dem", -1, "La democracia es ineficiente y lenta.", "A democracia é ineficiente e lenta."),
    ("dem", -3, "La mayoría de la gente toma malas decisiones políticas.", "A maioria das pessoas toma más decisões políticas."),
    ("int", 3, "Las Naciones Unidas deberían tener más poder sobre los países.", "As Nações Unidas deveriam ter mais poder sobre os países."),
    ("int", 1, "Los países deberían cooperar siempre que eso beneficie a ambos.", "Os países deveriam cooperar sempre que isso beneficie os dois."),
    ("int", -1, "Mantener la soberanía nacional es más importante que cualquier acuerdo internacional.", "Manter a soberania nacional é mais importante do que qualquer acordo internacional."),
    ("int", -3, "En otros países nadie tiene en cuenta nuestros intereses.", "Em outros países ninguém leva em conta os nossos interesses."),
    ("mil", 3, "Debería haber servicio militar obligatorio.", "Deveria haver serviço militar obrigatório."),
    ("mil", 1, "Un país tiene que mantener Fuerzas Armadas fuertes para defenderse.", "Um país precisa manter Forças Armadas fortes para se defender."),
    ("mil", -1, "Siempre hay que agotar la vía diplomática antes de pensar en usar la fuerza.", "Sempre é preciso esgotar a via diplomática antes de pensar em usar a força."),
    ("mil", -3, "El gasto militar es un desperdicio de plata.", "O gasto militar é um desperdício de dinheiro."),
    ("lib", 3, "La policía necesita más poder y más protección legal.", "A polícia precisa de mais poder e mais proteção legal."),
    ("lib", 1, "Hay que resignar algo de libertad para que la gente esté más segura.", "É preciso abrir mão de alguma liberdade para que as pessoas estejam mais seguras."),
    ("lib", -1, "El Estado no tiene por qué meterse en la vida privada de la gente.", "O Estado não tem por que se meter na vida privada das pessoas."),
    ("lib", -3, "Los delitos sin víctimas, como consumir drogas, no deberían ser delito.", "Crimes sem vítimas, como usar drogas, não deveriam ser crime."),
    ("col", 3, "Las clases sociales no deberían existir.", "As classes sociais não deveriam existir."),
    ("col", 1, "Los ricos tienen mucho más de lo que necesitan.", "Os ricos têm muito mais do que precisam."),
    ("col", -1, "Las personas tienen derecho a dejarle toda su riqueza a sus hijos.", "As pessoas têm direito de deixar toda a sua riqueza para os filhos."),
    ("col", -3, "Mientras más libre es el mercado, más libre es la gente.", "Quanto mais livre o mercado, mais livres as pessoas."),
    ("rel", 3, "No existe ningún dios ni poder superior.", "Não existe nenhum deus nem poder superior."),
    ("rel", 1, "Las leyes no deberían basarse en la religión.", "As leis não deveriam se basear na religião."),
    ("rel", -1, "La religión le hace bien a la sociedad.", "A religião faz bem para a sociedade."),
    ("rel", -3, "Los valores de mi religión deberían difundirse lo más posible.", "Os valores da minha religião deveriam ser difundidos o máximo possível."),
    ("pro", 3, "El género es una construcción social.", "O gênero é uma construção social."),
    ("pro", 1, "El matrimonio entre personas del mismo sexo está bien.", "O casamento entre pessoas do mesmo sexo está certo."),
    ("pro", -1, "Las tradiciones son importantes y hay que cuidarlas.", "As tradições são importantes e precisam ser preservadas."),
    ("pro", -3, "La sociedad se volvió demasiado progresista.", "A sociedade ficou progressista demais."),
    ("mig", 3, "Solo deberían poder entrar al país inmigrantes muy calificados.", "Só deveriam poder entrar no país imigrantes muito qualificados."),
    ("mig", 1, "Controlar las fronteras es importante.", "Controlar as fronteiras é importante."),
    ("mig", -1, "Los inmigrantes le aportan al país más de lo que le cuestan.", "Os imigrantes trazem ao país mais do que custam."),
    ("mig", -3, "Nuestra cultura sería mejor si se mezclara más con otras.", "Nossa cultura seria melhor se se misturasse mais com outras."),
    ("pla", 3, "La planificación económica del Estado asegura más prosperidad.", "O planejamento econômico do Estado garante mais prosperidade."),
    ("pla", 1, "A los ricos habría que cobrarles más impuestos que ahora.", "Os ricos deveriam pagar mais impostos do que hoje."),
    ("pla", -1, "Demasiada intervención del Estado es una amenaza para la economía.", "Intervenção demais do Estado é uma ameaça para a economia."),
    ("pla", -3, "El Estado debería intervenir en el mercado lo mínimo posible.", "O Estado deveria intervir no mercado o mínimo possível."),
    ("glo", 3, "Sin aranceles, la economía de nuestro país se vendría abajo.", "Sem tarifas de importação, a economia do nosso país desabaria."),
    ("glo", 1, "El gobierno debería fomentar la producción y el consumo local.", "O governo deveria incentivar a produção e o consumo local."),
    ("glo", -1, "El comercio internacional suele beneficiar a las dos partes.", "O comércio internacional costuma beneficiar os dois lados."),
    ("glo", -3, "Los aranceles a las importaciones deberían eliminarse.", "As tarifas de importação deveriam ser eliminadas."),
    ("tec", 3, "El progreso tecnológico no se puede ni se debe frenar.", "O progresso tecnológico não pode nem deve ser freado."),
    ("tec", 1, "Un mundo mejor va a venir de la ciencia, la tecnología y la automatización.", "Um mundo melhor virá da ciência, da tecnologia e da automação."),
    ("tec", -1, "Hay que frenar algunas tecnologías para proteger el ambiente.", "É preciso frear algumas tecnologias para proteger o meio ambiente."),
    ("tec", -3, "La sociedad era mejor hace muchos años que ahora.", "A sociedade era melhor muitos anos atrás do que hoje."),
]

# Inglés: original de 12axes, ajustado donde la traducción se adaptó
EN = {
    ("fed", 3): "State and local laws should take precedence over national laws.", ("fed", 1): "Local governments understand their citizens better than the national government.",
    ("fed", -1): "There are many issues that make no sense to address at a local level.", ("fed", -3): "A strong national government is essential to protect all citizens.",
    ("dem", 3): "The more people take part in a decision, the better the chance it is right.", ("dem", 1): "People must always be able to choose their leaders.",
    ("dem", -1): "Democracy is inefficient and slow.", ("dem", -3): "Most people make poor political decisions.",
    ("int", 3): "The United Nations should have more power over countries.", ("int", 1): "Nations should cooperate whenever it benefits them both.",
    ("int", -1): "National sovereignty matters more than any international agreement.", ("int", -3): "Nobody in other countries has our best interests in mind.",
    ("mil", 3): "There should be compulsory military service.", ("mil", 1): "A country must maintain strong armed forces to defend itself.",
    ("mil", -1): "Diplomacy should always be exhausted before force is even considered.", ("mil", -3): "Military spending is a waste of money.",
    ("lib", 3): "Police need more power and legal protection.", ("lib", 1): "Some freedom must be given up to keep people safe.",
    ("lib", -1): "The government has no business in people's private lives.", ("lib", -3): "Victimless crimes, such as drug use, should not be crimes at all.",
    ("col", 3): "Social classes should not exist.", ("col", 1): "The wealthy have far more than they need.",
    ("col", -1): "People should have the right to leave all their wealth to their children.", ("col", -3): "The freer the market, the freer the people.",
    ("rel", 3): "There is no god or higher power.", ("rel", 1): "Laws should not be based on religion.",
    ("rel", -1): "Religion is beneficial for society.", ("rel", -3): "My religious values should be spread as much as possible.",
    ("pro", 3): "Gender is a social construct.", ("pro", 1): "Same-sex marriage is fine.",
    ("pro", -1): "Traditions are important and must be preserved.", ("pro", -3): "Society has become too progressive.",
    ("mig", 3): "Only highly skilled immigrants, if any, should be allowed into the country.", ("mig", 1): "Border control is important.",
    ("mig", -1): "Immigrants give the country more than they cost.", ("mig", -3): "Our culture would be better if mixed more with others.",
    ("pla", 3): "Government economic planning ensures greater prosperity.", ("pla", 1): "The rich should pay more taxes than they do now.",
    ("pla", -1): "Excessive government intervention is a threat to the economy.", ("pla", -3): "The government should intervene in the market as little as possible.",
    ("glo", 3): "Without tariffs, our country's economy would collapse.", ("glo", 1): "The government should encourage local production and consumption.",
    ("glo", -1): "International trade usually benefits both sides.", ("glo", -3): "Import tariffs should be eliminated.",
    ("tec", 3): "Technological progress cannot and should not be stopped.", ("tec", 1): "A better world will come from science, technology and automation.",
    ("tec", -1): "Some technologies must be slowed down to protect the environment.", ("tec", -3): "Society was better many years ago than it is now.",
}

# Condimento latinoamericano para la versión general (es, pt, en, efecto en 12 ejes)
GENERAL = [
    ("Cualquier persona debería poder comprar dólares sin restricciones.", "Qualquer pessoa deveria poder comprar dólares sem restrições.", "Anyone should be able to buy US dollars without restrictions.", {"glo": 1, "pla": 0.5}),
    ("El aborto debería ser legal, seguro y gratuito.", "O aborto deveria ser legal, seguro e gratuito.", "Abortion should be legal, safe and free.", {"pro": -2, "rel": -0.5}),
    ("Bajar la edad de imputabilidad ayudaría a reducir el delito.", "Reduzir a maioridade penal ajudaria a diminuir o crime.", "Lowering the age of criminal responsibility would help reduce crime.", {"lib": -1}),
    ("Las Fuerzas Armadas deberían participar en la lucha contra el narcotráfico.", "As Forças Armadas deveriam participar do combate ao narcotráfico.", "The armed forces should take part in fighting drug trafficking.", {"mil": -1, "lib": -0.5}),
    ("Fortalecer el Mercosur y la integración latinoamericana debería ser una prioridad.", "Fortalecer o Mercosul e a integração latino-americana deveria ser prioridade.", "Strengthening Mercosur and Latin American integration should be a priority.", {"int": -1}),
    ("China es un socio tan válido como Estados Unidos.", "A China é um parceiro tão válido quanto os Estados Unidos.", "China is as valid a partner as the United States.", {"int": -0.5, "glo": 0.5}),
    ("La minería a gran escala es una oportunidad que hay que aprovechar.", "A mineração em grande escala é uma oportunidade que precisa ser aproveitada.", "Large-scale mining is an opportunity we must seize.", {"tec": -1}),
    ("Un líder fuerte que no dependa de los partidos sería bueno para el país.", "Um líder forte que não dependa dos partidos seria bom para o país.", "A strong leader who doesn't depend on parties would be good for the country.", {"dem": 1}),
]

# Locales: en el formato de 8 ejes de la primera versión, convertidos con A12 (y retocados a mano donde hace falta)
def A12(e):
    out = {}
    def add(k, v):
        out[k] = round(out.get(k, 0) + v, 2)
    for k, w in e.items():
        if k == "eco":
            add("pla", w)
            add("col", 0.5 * w)
        elif k == "com":
            add("glo", w)
        elif k == "fed":
            add("fed", -w)
        elif k == "soc":
            add("pro", w)
        elif k == "seg":
            add("lib", -w)
        elif k == "ins":
            add("dem", w)
        elif k == "ext":
            add("int", -w)
        elif k == "amb":
            add("tec", -w)
        else:
            add(k, w)
    return {k: v for k, v in out.items() if v}


LOCAL = json.loads((D / "locales_base.json").read_text(encoding="utf8"))  # es, pt, en + efecto en 8 ejes (o e12)


def preguntas():
    qs = []
    for i, (k, nivel, t, tpt) in enumerate(BASE, 1):
        qs.append({"id": f"x{i:02d}", "t": t, "t_pt": tpt, "t_en": EN[(k, nivel)], "e": {k: -1 if nivel > 0 else 1}, "nivel": abs(nivel), "v": TODAS})
    for i, (k, nivel, t, tpt, ten) in enumerate(AMPLIADA, len(BASE) + 1):
        qs.append({"id": f"x{i:03d}" if i > 99 else f"x{i:02d}", "t": t, "t_pt": tpt, "t_en": ten, "e": {k: -1 if nivel > 0 else 1}, "nivel": abs(nivel), "v": TODAS, "extra": 1})
    for i, (t, tpt, ten, e) in enumerate(GENERAL, 1):
        qs.append({"id": f"g{i:02d}", "t": t, "t_pt": tpt, "t_en": ten, "e": e, "v": TODAS})
    for p in PAISES:
        for i, q in enumerate(LOCAL[p], 1):
            e = q.get("e12") or A12(q["e"])
            d = {"id": f"{p}{i:02d}", "t": q["t"], "e": e, "v": [p]}
            for lg in ("t_pt", "t_en"):
                if q.get(lg):
                    d[lg] = q[lg]
            qs.append(d)
    for i, (t, tpt, ten, e) in enumerate(AR_EXTRA, len(LOCAL["ar"]) + 1):
        e = dict(e)
        for pref, extra in SEC_AR.items():
            if t.startswith(pref):
                e.update(extra)
        qs.append({"id": f"ar{i:02d}", "t": t, "t_pt": tpt, "t_en": ten, "e": e, "v": ["ar"]})
    # ejes complementarios: pesos secundarios en frases existentes y frases nuevas
    for q in qs:
        if q["id"] in SEC:
            q["e"] = {**q["e"], **SEC[q["id"]]}
    for qid, t, tpt, ten, e, nivel, rap in NUEVAS:
        d = {"id": qid, "t": t, "t_pt": tpt, "t_en": ten, "e": e, "nivel": nivel, "v": TODAS, "nueva": 1}
        if rap:
            d["rap"] = 1
        qs.append(d)
    return qs


# Pesos secundarios para las frases argentinas (por comienzo del texto)
SEC_AR = {
    "El Banco Central no debería intervenir": {"mon": 1}, "Los controles de precios": {"mon": -0.5},
    "El transporte público tiene que seguir": {"bie": -0.5}, "Hay que reformar la ley de contrato": {"lab": 0.5},
    "Los repartidores de aplicaciones": {"lab": -0.5}, "La AUH y los planes sociales": {"bie": -1},
    "Quien cobra un plan social": {"bie": 0.5}, "Un impuesto a las grandes fortunas": {"dis": -1},
    "El litio tendría que": {"ind": -1}, "El acuerdo Mercosur": {"ind": 0.5},
    "Los decretos de necesidad": {"ipe": 1}, "A veces el Congreso": {"ipe": -0.5}, "Quien fue condenado": {"ipe": 0.5},
    "La TV Pública debería": {"inf": -1}, "Hay que bajar la edad": {"pen": 1}, "La prisión preventiva": {"pen": -1},
    "Las Fuerzas Armadas deberían ayudar": {"pen": 0.5}, "El país tiene que desarrollar": {"ind": -1, "tem": 0.5},
    "El Conicet": {"epi": -0.5, "tem": 0.5},
}


# ---------------------------------------------------------------- dirigentes: 8 ejes editoriales -> 12 ejes
def clip(x):
    return int(round(max(0, min(100, x))))


def a12(p):
    eco, com, fed, soc, seg, ins, ext, amb = (p[k] for k in ("eco", "com", "fed", "soc", "seg", "ins", "ext", "amb"))
    return {
        "fed": clip(100 - fed),
        "dem": clip(0.6 * ins + 0.25 * seg - 8),
        "int": clip(0.35 * soc + 0.25 * (100 - com) + 0.2 * ins + 0.2 * (100 - ext)),
        "mil": clip(100 - (0.7 * seg + 0.3 * ext)),
        "lib": clip(100 - seg),
        "col": clip(eco),
        "rel": clip(0.85 * soc + 8),
        "pro": clip(soc),
        "mig": clip(100 - (0.6 * soc + 0.4 * seg)),
        "pla": clip(0.75 * eco + 0.25 * com),
        "glo": clip(com),
        "tec": clip(0.3 * soc + 0.45 * (100 - amb) + 12),
    }


def a2(p, d12):
    """Posición estimada en los ejes complementarios que se pueden derivar de los 8 ejes editoriales.
    Quedan afuera los que no se infieren de ahí (epi, ges, eti, tem, fut) y 'cer' (es del usuario)."""
    eco, com, soc, seg, ins, amb = (p[k] for k in ("eco", "com", "soc", "seg", "ins", "amb"))
    radical = max(abs(eco - 50), abs(soc - 50), abs(ins - 50))
    return {
        "ecl": clip(amb),
        "dis": clip(0.8 * eco + 0.2 * soc),
        "bie": clip(0.85 * eco + 0.15 * soc),
        "tra": clip(1.6 * radical - 20),
        "idc": clip(0.6 * soc + 0.4 * (100 - eco)),
        "pen": clip(seg),
        "lab": clip(0.8 * eco + 0.2 * ins),
        "ind": clip(0.75 * com + 0.25 * eco),
        "mon": clip(0.6 * eco + 0.4 * (100 - ins)),
        "inf": clip(0.7 * ins + 0.3 * seg),
        "ipe": clip(100 - ins),
        "uni": clip(0.8 * d12["int"] + 0.2 * soc),
    }


def figuras():
    base = json.loads((D / "figuras_base.json").read_text(encoding="utf8"))
    out = {"_nota": "Codificación editorial inicial A REVISAR, a partir de programas, votaciones y declaraciones públicas. No es una medición de opinión. "
                    "0-100 por eje, mismos polos que ejes.json. Se arma con generar.py desde figuras_base.json (8 ejes + ajustes por persona).",
           "revision": "a revisar", "fecha": base.get("fecha", ""), "_nota_cargos": base.get("_nota_cargos", "")}
    for grupo in ("latam", "mundo", *PAISES):
        lst = []
        for f in base.get(grupo, []):
            pos = a12(f["pos"])
            pos.update({k: v for k, v in f.get("ajuste", {}).items() if k in pos})
            pos2 = a2(f["pos"], pos)
            pos2.update({k: v for k, v in f.get("ajuste", {}).items() if k not in pos})
            g = {k: v for k, v in f.items() if k not in ("pos", "ajuste")}
            g["pos"] = pos
            g["pos2"] = pos2
            lst.append(g)
        out[grupo] = lst
    return out


def ejes():
    nombres = {"general": "Latinoamérica (general)", "ar": "Argentina", "br": "Brasil", "py": "Paraguay", "pe": "Perú", "cl": "Chile",
               "co": "Colombia", "uy": "Uruguay"}
    ver = {v: {"nombre": n, "figuras": "latam" if v == "general" else v, "activa": True, **({"lang": "pt"} if v == "br" else {})}
           for v, n in nombres.items()}
    ver["mx"] = {"nombre": "México", "activa": False}
    return {
        "_nota": "30 ejes: 12 principales (mecánica de 12axes, politicaltests, MIT) + 17 complementarios + Certeza (ejes2; 'cer' tiene calc y es el promedio de certeza de los otros 29). Cada eje va de 0 (polo a) a 100 (polo b).",
        "ejes": [{"id": i, "nombre": n, "a": a, "b": b, "a_desc": ad, "b_desc": bd, "pt": {"nombre": pt[0], "a": pt[1], "b": pt[2]}, "en": EN_EJES[i]}
                 for i, n, a, b, ad, bd, pt in EJES],
        "respuestas": [{"v": 2, "t": "Muy de acuerdo"}, {"v": 1, "t": "De acuerdo"}, {"v": 0, "t": "Neutral / no sé"},
                       {"v": -1, "t": "En desacuerdo"}, {"v": -2, "t": "Muy en desacuerdo"}],
        "respuestas_pt": ["Concordo totalmente", "Concordo", "Neutro / não sei", "Discordo", "Discordo totalmente"],
        "respuestas_en": ["Strongly agree", "Agree", "Neutral / unsure", "Disagree", "Strongly disagree"],
        "ejes2": [{"id": i, "nombre": n, "a": a, "b": b, "a_desc": ad, "b_desc": bd, "pt": {"nombre": pt[0], "a": pt[1], "b": pt[2]},
                   "en": {"nombre": en[0], "a": en[1], "b": en[2]}, **({"calc": "certeza"} if i == "cer" else {})} for i, n, a, b, ad, bd, pt, en in EJES2],
        "versiones": ver,
        "creditos": "Preguntas base adaptadas de 12axes (politicaltests.github.io), licencia MIT, (c) 2020 8values (SapplyValues).",
    }


if __name__ == "__main__":
    qs = preguntas()
    (D / "preguntas.json").write_text(json.dumps({"_nota": "e = efecto de estar de acuerdo (peso negativo: polo a; positivo: polo b). nivel = intensidad (1 a 4) en las preguntas base; extra = ampliada (no entra en Express). v = versiones.",
                                                  "preguntas": qs}, ensure_ascii=False, indent=1), encoding="utf8")
    (D / "figuras.json").write_text(json.dumps(figuras(), ensure_ascii=False, indent=1), encoding="utf8")
    (D / "ejes.json").write_text(json.dumps(ejes(), ensure_ascii=False, indent=1), encoding="utf8")
    for v in TODAS:
        print(v, sum(1 for q in qs if v in q["v"]), "preguntas")
