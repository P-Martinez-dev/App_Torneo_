"""
Los textos que se muestran en las pantallas de "Info".

Estos son los valores POR DEFECTO: si el admin nunca los editó, se muestran
estos. En cuanto edita uno, se guarda en la base y pasa a mostrarse el suyo.
Se dejan acá y no directamente en la plantilla para que el editable y el
por defecto sean exactamente el mismo texto, sin dos versiones que puedan
quedar desincronizadas.

Van en Markdown liviano: los ## son títulos y los ** negritas.
"""

INFO_TABLAS = """## Puntos por puesto

Cada torneo reparte puntos según el puesto:

- 🥇 **1° puesto** — 8 puntos
- 🥈 **2° puesto** — 7 puntos
- 🥉 **3° puesto** — 6 puntos
- 4️⃣ **4° puesto** — 4 puntos
- 8️⃣ **5° puesto** — 2 puntos
- 🎮 **6° en adelante** — 1 punto

Los puntos se acumulan a lo largo de todos los torneos: la tabla es
histórica, no de un torneo puntual. Con solo presentarte ya sumás, así que
venir siempre también cuenta.

## Desempates

Si dos jugadores tienen los mismos puntos, desempata primero los **puntos
por victoria** (3 por cada partido ganado, sumando todos los torneos) y
después el **win rate**. Si empatan en las tres cosas, comparten el mismo
puesto.

## Cómo leerla

Las **insignias** son un torneo cada una, en orden cronológico: de un
vistazo se ve el recorrido completo de cada jugador.

La **flecha** compara el puesto actual con el de antes del último torneo:
▲ subió, ▼ bajó, ● se mantuvo. Si es su primer torneo aparece como NUEVO,
en vez de un salto de puestos que no significaría nada.

También se pueden **filtrar torneos**: la tabla se recalcula al instante
sin ellos, para ver cómo estaría todo sin contar ciertas fechas.
"""

INFO_FORMATOS = """## Todos contra todos

Cada jugador se enfrenta una vez con cada uno de los demás. El orden final
sale de los puntos que va sumando cada uno por victoria, desempatando por
puntos de victoria y win rate si hace falta.

## Grupos + eliminación

Los jugadores se reparten en grupos, y dentro de cada grupo se juega todos
contra todos. Los mejores puestos de cada grupo clasifican a una fase de
eliminación directa.

Si hay empates en la clasificación al corte, se resuelven con un desempate
interno; si sobran o faltan clasificados para completar el bracket, entra
un repechaje cruzado entre grupos.

## Cinco vidas

Se juega en cola: el que gana se queda en cancha esperando al próximo
desafiante, y el que pierde una vida vuelve al final de la cola. Cuando se
queda sin vidas, queda eliminado. El último que queda en pie es el campeón.

**Cómo se arma la tabla final**

El campeón siempre es el 1° puesto. Para el resto, el orden **no** es
simplemente quién duró más: se combinan dos cosas.

**1. Puntos de racha (80% del criterio)**

Cada racha de victorias seguidas suma **su largo al cuadrado**:

- 1 victoria seguida = 1 punto
- 2 victorias seguidas = 4 puntos
- 3 victorias seguidas = 9 puntos
- 4 victorias seguidas = 16 puntos

Si en un mismo torneo hacés varias rachas, se suman todas. Por ejemplo,
dos rachas de 2 dan 4 + 4 = 8 puntos, mientras que una sola racha de 4 da
16: aguantar cuatro seguidas vale mucho más que ganar cuatro partidos
sueltos.

Es a propósito. El que está en cancha juega con personaje al azar y se va
desgastando, así que cada victoria extra sin bajarse es más difícil que la
anterior — y la tabla lo refleja.

**2. Qué tan lejos llegaste (20% del criterio)**

El orden en que fuiste eliminado. Pesa bastante menos que las rachas, pero
alcanza para desempatar entre dos que hicieron rachas parecidas.

Las dos cosas se llevan a una misma escala antes de combinarlas, así que
lo que importa es cómo te fue **respecto a los demás de ese torneo**, no
un número absoluto.
"""
