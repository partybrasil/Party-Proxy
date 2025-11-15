# 🎉 Party-Proxy

*Gestión automatizada y simple de proxys gratuitos con CLI y GitHub Actions*

**⏰ Última actualización:** 17:14:53 / 15-11-2025

---

## 🛠️ Descripción General

Party-Proxy es una aplicación CLI que scrappea proxys públicos y gratuitos (protocolos HTTP, HTTPS y SOCKS), los filtra y verifica con chequeo multicore/thread seguro. El workflow de GitHub Actions la ejecuta automáticamente **cada hora**, actualizando la lista de proxys verificados en una carpeta del repositorio y dejando disponible la descarga para cualquier usuario.

- **Fuentes:** Varios sitios públicos gratuitos.
- **Chequeo:** Alive/dead, seguridad, privacidad, latencia, país, ciudad, protocolo.
- **Limpieza:** Elimina duplicados antes y después del chequeo, borra los proxys muertos.

---

## 💻 Uso Local

1. **Clona el repositorio:**
   ```
   git clone https://github.com/partybrasil/Party-Proxy.git
   cd Party-Proxy
   ```

2. **Instala dependencias (requisitos):**
   ```
   pip install -r requirements.txt
   ```

3. **Ejecuta el scraper+checker:**
   ```
   python party_proxy.py
   ```

   - Lista final de proxys se guarda en: `output/active_proxies.txt` (o el formato elegido).
   - El script actualiza y limpia solo proxys funcionales y sin duplicados.

---

## 🚀 Automatización con GitHub Actions

El workflow se ejecuta **cada hora**, actualiza el dataset y sube el archivo a la carpeta `output/`.

### Archivo de workflow (`.github/workflows/proxy_update.yml`):

```
name: Party-Proxy Scrape & Check

on:
  schedule:
    - cron: '0 * * * *'  # Cada hora
  workflow_dispatch:

jobs:
  scrape_and_check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Party-Proxy
        run: python party_proxy.py
      - name: Commit and push live proxies
        run: |
          git config --global user.email "github-actions@github.com"
          git config --global user.name "github-actions"
          git add output/active_proxies.txt README.md
          git commit -m "Update proxies [skip ci]"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> Asegúrate de que:
> - El script CLI guarda el resultado en `output/active_proxies.txt`
> - El README.md es actualizado con la fecha/hora de última actualización (esto puede automatizarse al final del script)

---

## 📦 Carpeta de Descarga

- Carpeta: `output/`
  - ARCHIVO: `active_proxies.txt` (solo proxys verificados, listos para usar)
- El workflow de GitHub Actions deja el archivo activo y limpio tras cada ejecución.

---

## 📝 Estructura Mínima del Proyecto

```
party-proxy/
│
├── party_proxy.py            # Script principal de scraping + checking
├── requirements.txt          # Dependencias Python
├── output/
│     └── active_proxies.txt  # Proxys funcionales, actualizados siempre
│
├── .github/
│     └── workflows/
│           └── proxy_update.yml
├── README.md                 # Este documento
```

---

## 🩺 Troubleshooting rápido

- **Errores de workflow:** Revisa la pestaña "Actions" en el repo de GitHub.
- **Dependencias faltantes:** Verifica que todas las del `requirements.txt` estén instaladas.
- **Commit/push fallidos:** Confirma que `GITHUB_TOKEN` esté configurado en el repositorio.

---

## 🤝 Contribuir

- Pull requests y sugerencias bienvenidas para nuevas fuentes, optimizaciones y chequeos adicionales.
- Futuras mejoras: soporte más avanzado, GUI y métricas históricas.

---

## 📄 Licencia

MIT License