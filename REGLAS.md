<!-- Valor máximo de visitas al mes: es el calculo del mes escogido a programar las rutas inteligentes, de los días laborales de lunes a viernes, sin contar los domingos ni los festivos y se multiplica por 8 visitas por día y los sábados que se seleccionaron como laborales, que son 2 sábados al mes, esos sábados se multiplica por 4 visitas por sábado y se suman esos dos valores y da el resultado.

Valor de visitas al mes por usuario: es el calculo que se obtiene del panel del mes por usuario, sumando todas las cantidades de visitas.

Total días trabajados: la sumatoria de los días laborales de lunes a viernes sin contar los domingos y festivos mas la cantidad de sábados laborales, esto da el total de días trabajados

PDV: punto de venta (Droguerías)

REGLAS RUTAS INTELIGENTES

1.  
    Cantidad de visitas máximas diarias de lunes a viernes: Son máximo 8 visitas diarias de lunes a viernes, hay una excepción si el Valor de visitas al mes por usuario supera el Valor máximo de visitas al mes, puede aumentar la cantidad de visitas hasta un máximo de 10 visitas diarias

2.   
    Cantidad de visitas máximas los sábados: Son máximo 4 visitas los sábados, hay una excepción si el Valor de visitas al mes por usuario supera el Valor máximo de visitas al mes, puede aumentar la cantidad de visitas hasta un máximo de 5 visitas, primero se aumenta en las visitas de lunes a viernes, aun asi sino alcanza a llegar al Valor de visitas al mes por usuario, entonces si se aumenta por máximo a 5 visitas los sábados.

3.  
    Por lo menos se debe visitar todos los PDV una vez al mes, para garantizar la cobertura de todos los puntos

4.  
    si no alcanza a cumplir el Valor de visitas al mes por usuario entonces se comienza a disminuir la CANTIDAD VISITAS en este orden y de esta forma: 
    *   
        Si tiene en CANTIDAD VISITAS en 2 se reducen a 1, como mínimo, después se valida si reduciendo esta CANTIDAD VISITAS, se vuelve a calcular el Valor de visitas al mes por usuario y si no alcanza con esta distribución se continua reduciendo, se pasa al siguiente punto.
    *   
        Si tiene en CANTIDAD VISITAS en 3 se reducen a 2, después se valida si reduciendo esta CANTIDAD VISITAS, se vuelve a calcular el Valor de visitas al mes por usuario y si no alcanza con esta distribución se continua reduciendo, se pasa al siguiente punto.
    *   
        Si tiene en CANTIDAD VISITAS en 4 se reduce a 3, después se valida si reduciendo esta CANTIDAD VISITAS, se vuelve a calcular el Valor de visitas al mes por usuario y si no alcanza con esta distribución se continua reduciendo, se pasa al siguiente punto.
    *   
        Si después de hacer todas estas reducciones en CANTIDAD VISITAS y no se alcanza a cubrir el Valor de visitas al mes por usuario entonces se sigue reduciendo en -1, hasta llegar a un máximo de CANTIDAD VISITAS = 1 por PDV.

5.  
    Distribución de visitas por día: Si el Valor de visitas al mes por usuario es menor o igual al Valor máximo de visitas al mes, entonces distribuye equitativamente en el mes las visitas a los PDV teniendo en cuenta las reglas anteriores. La idea es distribuir y que se agrupen en puntos cercanos, si hay puntos que sean muy cercanos (350 metros de radio) se puede desbalancear un poco la distribución equitativa en el mes, se puede dejar visitas mayores hasta un máximo de 8 visitas o si tiene excepción como esta indicado en las reglas 1 y 2, entonces se puede programar hasta 10 visitas. Este desbalanceo se puede hacer en un máximo de 10 días. Si el Valor de visitas al mes por usuario es mayor al Valor máximo de visitas al mes, entonces distribúyelos también equitativamente, pero comienza a encontrar en donde puedes agregar PDV muy cercanos (350 metros de radio) a los grupos que se distribuyeron por día y a aumentar primero de lunes a viernes y por ultimo los sábados
6.  
    Si hay grupos de PDV muy cercanos y están muy alejados de los otros puntos y de acuerdo a la distribución es posible dejar únicamente estos puntos de venta agrupados en ese día, la distribución puede que no sea equitativa, puede que queden unos días menores visitas al promedio por día.

7.  
    Si hay coordenadas fuera de la ciudad principal, lo ideal es agruparlas lo mejor posible para que se puedan agrupar lo mas optimo posible, La idea es que si hay pocos puntos por ejemplo 6 PDV se pueda agrupar en solo un día para hacer esa ruta, o si tienen 8 PDV también hacerlos todos en un día, igualmente si hay 9 o 10 máximo (Así no sea una excepción), también agruparlos en solo un día, esto debido a que la persona que hace la ruta por lo general, sale de la ciudad principal y aprovecha un día para hacer la ruta que es fuera de la ciudad lo mayor posible. Puede que hayan puntos fuera de la ciudad pero son muy cercanos a la ciudad para estos puntos no aplica, solo para puntos que este fuera de la ciudad, y alejados mayor a 7km del centroide de la mayoría de los puntos mas cercanos.

8.  
    Las frecuencias (CANTIDAD VISITAS) deben separarse con un minimo de 7 dias, se pueden separar con mas dias, pero no con menos dias del minimo de 7 dias. -->

Valor máximo de visitas al mes: es el cálculo del mes escogido a programar las rutas inteligentes, sumando los días laborales (lunes a viernes, sin contar domingos ni festivos) multiplicados por 8 visitas diarias, más los sábados laborales seleccionados multiplicados por 4 visitas diarias.

Valor de visitas al mes por usuario: es la sumatoria de todas las cantidades de visitas asignadas a un usuario en el panel del mes.

Total días trabajados: la sumatoria de los días laborales de lunes a viernes más la cantidad de sábados laborales.

PDV: punto de venta (Droguerías).

REGLAS RUTAS INTELIGENTES

1.  Cantidad de visitas máximas diarias de lunes a viernes: Son máximo 8 visitas diarias. Solo se permite una excepción de sobrecarga (máximo 10 visitas) si el Valor de visitas al mes por usuario es mayor al Valor máximo de visitas al mes y los puntos adicionales están a menos de 350 metros del agrupamiento de coordenadas por dia.
2.  Cantidad de visitas máximas los sábados: Son máximo 4 visitas. Solo se permite una excepción de sobrecarga (máximo 5 visitas) si el Valor de visitas al mes por usuario es mayor al Valor máximo de visitas al mes y los puntos adicionales están a menos de 350 metros del agrupamiento de coordenadas por dia.
3.  Cobertura: Por lo menos se debe visitar todos los PDV una vez al mes para garantizar la cobertura.
4.  Reducción de frecuencias (Cascada): La reducción de frecuencias solo se ejecutará si el Valor de visitas al mes por usuario es mayor al Valor máximo de visitas al mes y tras intentar rutear aprovechando las excepciones de cercanía (<350m), el total de visitas sigue sin caber en el mes. La reducción se hará de forma escalonada:
    *   Primero, se buscan los PDV con CANTIDAD VISITAS en 2 y se reducen a 1. Se vuelve a intentar rutear.
    *   Si aún no alcanza el espacio, se buscan los PDV con CANTIDAD VISITAS en 3 y se reducen a 2. Se vuelve a intentar rutear.
    *   Si aún no alcanza el espacio, se buscan los PDV con CANTIDAD VISITAS en 4 y se reducen a 3, y así sucesivamente hasta que todas las visitas puedan ser programadas o se llegue a un máximo de 1 visita por PDV.
5.  Distribución y Sobrecarga por Cercanía: El sistema agrupará los PDV por zonas cercanas. Si el Valor de visitas al mes por usuario es mayor al Valor máximo de visitas al mes y si durante el armado de la ruta de un día se alcanza el tope normal (8 L-V o 4 Sab) y existe un punto a menos de 350 metros (0.35 km) de distancia del grupo de coordenadas diarias, se permite desbalancear la ruta agregándolo hasta el tope absoluto (10 L-V o 5 Sab). 
6.  Aislamiento: Si hay grupos de PDV muy cercanos entre sí pero muy alejados del resto, se pueden agrupar en un solo día, incluso si esto genera que la ruta de ese día tenga menos visitas del promedio diario.
7.  Rutas Remotas (Intermunicipales): Para puntos que estén fuera de la ciudad principal (a más de 12 km del centroide operativo), el límite estricto es de 8 visitas diarias. No aplican las excepciones de sobrecarga debido a los tiempos de desplazamiento.
8.  Separación de visitas (Regla de Oro): Las frecuencias (CANTIDAD VISITAS) deben separarse con un mínimo estricto de 7 días. Esta regla tiene prioridad absoluta sobre la regla 5 de cercanía.