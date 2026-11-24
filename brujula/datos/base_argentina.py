"""Frases extra con condimento argentino (redacción propia, temas inspirados en el debate público argentino).

Cada tupla: (es, pt, en, e12). e12 usa la convención de preguntas.json: peso negativo = estar de acuerdo
empuja al polo 'a' del eje; positivo, al polo 'b'.
"""

AR_EXTRA = [
    # economía y Estado
    ("YPF tendría que seguir siendo mayormente del Estado.", "A YPF deveria continuar majoritariamente estatal.", "YPF should remain mostly state-owned.", {"pla": -1}),
    ("Aerolíneas Argentinas debería privatizarse aunque se pierdan rutas poco rentables.", "A Aerolíneas Argentinas deveria ser privatizada mesmo perdendo rotas pouco rentáveis.", "Aerolíneas Argentinas should be privatized even if unprofitable routes are lost.", {"pla": 1}),
    ("El Banco Central no debería intervenir en el precio del dólar.", "O Banco Central não deveria intervir no preço do dólar.", "The Central Bank should not intervene in the dollar exchange rate.", {"pla": 1}),
    ("Los controles de precios, como Precios Justos, sirven para frenar la inflación.", "Os controles de preços, como o Precios Justos, ajudam a frear a inflação.", "Price controls such as 'Precios Justos' help curb inflation.", {"pla": -1}),
    ("Sobran empleados públicos y hay que reducir la planta del Estado.", "Há funcionários públicos demais e é preciso reduzir o quadro do Estado.", "There are too many public employees and the state payroll should shrink.", {"pla": 1, "col": 0.5}),
    ("El transporte público tiene que seguir subsidiado aunque cueste plata al Estado.", "O transporte público deve continuar subsidiado mesmo custando caro ao Estado.", "Public transport should stay subsidized even if it costs the state money.", {"pla": -1}),
    # trabajo y distribución
    ("Hay que reformar la ley de contrato de trabajo para que contratar sea más fácil.", "É preciso reformar a lei trabalhista para que contratar seja mais fácil.", "Labor law should be reformed to make hiring easier.", {"col": 1}),
    ("Los repartidores de aplicaciones deberían ser empleados en blanco de esas empresas.", "Os entregadores de aplicativo deveriam ser empregados formais dessas empresas.", "App delivery riders should be formal employees of those companies.", {"col": -1}),
    ("Los paros de la CGT hacen más daño que bien.", "As greves gerais da CGT fazem mais mal do que bem.", "General strikes by the CGT do more harm than good.", {"col": 1}),
    ("La AUH y los planes sociales son necesarios para que nadie quede afuera.", "A AUH e os programas sociais são necessários para que ninguém fique de fora.", "Child allowances and social programs are needed so nobody is left behind.", {"col": -1}),
    ("Quien cobra un plan social debería dar algo a cambio con trabajo comunitario.", "Quem recebe um programa social deveria dar algo em troca com trabalho comunitário.", "People on welfare should give something back through community work.", {"col": 1}),
    ("Un impuesto a las grandes fortunas es justo.", "Um imposto sobre grandes fortunas é justo.", "A tax on large fortunes is fair.", {"col": -1}),
    # soberanía y comercio
    ("El litio tendría que industrializarse acá y no exportarse en bruto.", "O lítio deveria ser industrializado aqui e não exportado bruto.", "Lithium should be processed here rather than exported raw.", {"glo": -1}),
    ("El acuerdo Mercosur-Unión Europea es una oportunidad para el país.", "O acordo Mercosul-União Europeia é uma oportunidade para o país.", "The Mercosur-EU trade deal is an opportunity for the country.", {"glo": 1}),
    ("Comprar afuera por internet debería tener menos trabas y aranceles.", "Comprar do exterior pela internet deveria ter menos entraves e tarifas.", "Buying from abroad online should face fewer hurdles and tariffs.", {"glo": 1}),
    # instituciones y democracia
    ("Los decretos de necesidad y urgencia deberían usarse mucho menos.", "Os decretos de necessidade e urgência deveriam ser usados muito menos.", "Emergency decrees should be used much less.", {"dem": -1}),
    ("A veces el Congreso traba más de lo que ayuda a gobernar.", "Às vezes o Congresso atrapalha mais do que ajuda a governar.", "Congress sometimes gets in the way of governing more than it helps.", {"dem": 1}),
    ("Quien fue condenado por corrupción no debería poder ser candidato.", "Quem foi condenado por corrupção não deveria poder ser candidato.", "Anyone convicted of corruption should be barred from running for office.", {"dem": -0.5, "lib": -0.5}),
    ("La Boleta Única de Papel mejora la transparencia de las elecciones.", "A cédula única de papel melhora a transparência das eleições.", "The single paper ballot makes elections more transparent.", {"dem": -1}),
    ("La TV Pública debería ser independiente del gobierno de turno.", "A TV Pública deveria ser independente do governo da vez.", "Public TV should be independent from whoever is in government.", {"dem": -1, "lib": 0.5}),
    ("El gobierno debería poder disolver cortes de calle sin esperar a un juez.", "O governo deveria poder dissolver bloqueios de rua sem esperar um juiz.", "The government should be able to clear road blockades without waiting for a judge.", {"lib": -1, "dem": 0.5}),
    # seguridad
    ("Hay que bajar la edad de imputabilidad.", "É preciso reduzir a maioridade penal.", "The age of criminal responsibility should be lowered.", {"lib": -1}),
    ("Las Fuerzas Armadas deberían ayudar a combatir el narco en ciudades como Rosario.", "As Forças Armadas deveriam ajudar a combater o tráfico em cidades como Rosário.", "The armed forces should help fight drug trafficking in cities like Rosario.", {"lib": -1, "mil": -0.5}),
    ("La prisión preventiva se usa demasiado y debería ser la excepción.", "A prisão preventiva é usada demais e deveria ser a exceção.", "Pretrial detention is overused and should be the exception.", {"lib": 1}),
    ("Tener un arma para defenderse debería ser más fácil.", "Ter uma arma para se defender deveria ser mais fácil.", "It should be easier to own a gun for self-defense.", {"lib": 1, "col": 0.5}),
    # sociedad
    ("La ley de aborto legal fue un avance.", "A lei do aborto legal foi um avanço.", "The legal abortion law was a step forward.", {"pro": -1, "rel": -0.5}),
    ("El lenguaje inclusivo no debería usarse en escuelas ni en documentos oficiales.", "A linguagem neutra não deveria ser usada em escolas nem em documentos oficiais.", "Gender-neutral language should not be used in schools or official documents.", {"pro": 1}),
    ("La educación sexual integral tendría que darse en todas las escuelas.", "A educação sexual integral deveria ser dada em todas as escolas.", "Comprehensive sex education should be taught in every school.", {"pro": -1}),
    ("Regular el consumo personal de marihuana es el camino correcto.", "Regulamentar o consumo pessoal de maconha é o caminho certo.", "Regulating personal cannabis use is the right path.", {"pro": -0.5, "lib": 1}),
    # federalismo
    ("Buenos Aires concentra demasiado poder y el interior paga las consecuencias.", "Buenos Aires concentra poder demais e o interior paga as consequências.", "Buenos Aires concentrates too much power and the provinces pay the price.", {"fed": -1}),
    ("Las provincias con petróleo o litio deberían quedarse con más de lo que generan.", "As províncias com petróleo ou lítio deveriam ficar com mais do que geram.", "Provinces with oil or lithium should keep more of what those resources generate.", {"fed": -1}),
    ("Los fondos a las provincias tendrían que repartirse con reglas fijas y no a dedo.", "Os repasses às províncias deveriam seguir regras fixas e não favoritismo.", "Funds for the provinces should follow fixed rules, not discretion.", {"fed": -0.5, "dem": -0.5}),
    # mundo y defensa
    ("El reclamo por Malvinas tiene que ser una prioridad permanente.", "A reivindicação das Malvinas deve ser uma prioridade permanente.", "The Falklands/Malvinas claim must be a permanent priority.", {"int": 1}),
    ("Argentina debería alinearse con Estados Unidos en política exterior.", "A Argentina deveria se alinhar com os Estados Unidos na política externa.", "Argentina should align with the United States on foreign policy.", {"int": -0.5, "glo": 0.5}),
    ("El país tiene que desarrollar sus propios satélites y reactores, como INVAP y ARSAT, aunque cueste más.", "O país deve desenvolver seus próprios satélites e reatores, como INVAP e ARSAT, mesmo custando mais.", "The country should build its own satellites and reactors, like INVAP and ARSAT, even if it costs more.", {"tec": -1, "glo": -0.5}),
    ("El Conicet y la ciencia pública merecen más presupuesto.", "O Conicet e a ciência pública merecem mais orçamento.", "CONICET and public science deserve more funding.", {"tec": -1, "pla": -0.5}),
]
