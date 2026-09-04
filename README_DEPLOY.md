# Desplegar en Streamlit Community Cloud

## 1. Preparar el proyecto

Esta carpeta contiene la aplicación en `app.py`. Los archivos necesarios para el despliegue son:

- `app.py`: aplicación Streamlit.
- `requirements.txt`: dependencias de Python.
- `runtime.txt`: versión de Python para Streamlit Cloud.
- `.streamlit/config.toml`: configuración de Streamlit y tamaño máximo de carga.
- `.streamlit/secrets.toml.example`: plantilla local para la clave de Google Maps.

No subas `.streamlit/secrets.toml`, archivos Excel reales ni la carpeta del entorno virtual.

## 2. Revocar la clave que estaba en el código

La clave de Google Maps que estaba escrita en `app.py` debe considerarse expuesta. En Google Cloud:

1. Abre **APIs y servicios > Credenciales**.
2. Revoca o elimina la clave anterior.
3. Crea una clave nueva.
4. Habilita **Geocoding API**.
5. Configura restricciones de API y límites de uso. La API puede requerir una cuenta de facturación.

## 3. Probar localmente

Desde PowerShell, situado en la carpeta del proyecto:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
notepad .streamlit\secrets.toml
```

Reemplaza el valor de `GOOGLE_MAPS_API_KEY` por la clave nueva y ejecuta:

```powershell
.\Scripts\python.exe -m streamlit run app.py
```

Abre la dirección local que muestre Streamlit, normalmente `http://localhost:8501`.

## 4. Crear el repositorio

1. Crea un repositorio nuevo en GitHub.
2. Copia allí `app.py`, `requirements.txt`, `runtime.txt`, `REGLAS.md`, `README_DEPLOY.md` y la carpeta `.streamlit` con `config.toml` y `secrets.toml.example`.
3. No copies `Lib`, `Scripts`, `Include`, `share`, `etc`, `__pycache__`, archivos Excel ni `.streamlit/secrets.toml`.
4. Confirma los cambios y publica el repositorio.

También puedes inicializar Git desde esta carpeta:

```powershell
git init
git add app.py requirements.txt runtime.txt REGLAS.md README_DEPLOY.md .streamlit .gitignore
git commit -m "Preparar despliegue de rutas inteligentes"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

## 5. Desplegar en Streamlit Community Cloud

1. Entra en <https://share.streamlit.io/> e inicia sesión con GitHub.
2. Selecciona **New app**.
3. Elige el repositorio, la rama `main` y el archivo principal `app.py`.
4. En **Advanced settings > Secrets**, pega:

```toml
GOOGLE_MAPS_API_KEY = "tu_clave_nueva"
```

5. Pulsa **Deploy**.
6. Espera a que instale `requirements.txt` y abre la URL pública.

## 6. Uso de la aplicación desplegada

En **Rutas Inteligentes**, carga el Panel del Mes y el Maestro de Coordenadas en formato `.xlsx`, selecciona el año, mes y sábados laborales, y genera el resumen.

En **Geocodificador**, prueba primero una dirección individual. Después carga el archivo de PDVs y procesa las coordenadas faltantes. La clave de Google Maps se consume desde los secretos y no se muestra en la interfaz.

## Solución rápida de problemas

- **ModuleNotFoundError**: verifica que el nombre del paquete esté en `requirements.txt` y reinicia la app.
- **NO_API_KEY**: revisa que el secreto se llame exactamente `GOOGLE_MAPS_API_KEY`.
- **REQUEST_DENIED**: comprueba Geocoding API, facturación y restricciones de la clave.
- **No carga el Excel**: confirma que sea `.xlsx`, que no supere 200 MB y que tenga las columnas esperadas por la aplicación.