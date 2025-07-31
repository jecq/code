# descargar_imagenes_por_lotes_v2.py - PROCESAMIENTO INCREMENTAL INTELIGENTE
import json, os, time, requests, mysql.connector, random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys

# ⚠️ CAMBIA ESTOS VALORES POR LOS REALES DE TU MYSQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",                    # ← TU USUARIO REAL
    "password": "",  # ← TU CONTRASEÑA REAL  
    "database": "bd_propiedades_inmobiliarias"
}

IMAGENES_DIR = "images"

def conectar_mysql():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"❌ Error MySQL: {e}")
        return None

def obtener_propiedades_procesadas(cursor, minimo_imagenes=5):
    """Obtiene lista de propiedades que ya tienen suficientes imágenes"""
    try:
        cursor.execute("""
            SELECT p.id_interno, COUNT(ip.id) as num_imagenes
            FROM propiedades p 
            LEFT JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
            GROUP BY p.id, p.id_interno
            HAVING COUNT(ip.id) >= %s
        """, (minimo_imagenes,))
        
        procesadas = [str(row[0]) for row in cursor.fetchall()]
        cursor.fetchall()
        
        print(f"📋 Propiedades con {minimo_imagenes}+ imágenes: {len(procesadas)}")
        if procesadas:
            print(f"   IDs procesados: {', '.join(procesadas)}")
        
        return set(procesadas)
        
    except Exception as e:
        print(f"⚠️ Error obteniendo propiedades procesadas: {e}")
        return set()

def filtrar_links_pendientes(links, propiedades_procesadas, limite_lote=6):
    """Filtra links y retorna solo un lote pequeño de pendientes"""
    links_pendientes = []
    links_ya_procesados = []
    
    for url in links:
        id_interno = url.split("-")[-1].replace("/", "")
        
        if id_interno in propiedades_procesadas:
            links_ya_procesados.append(url)
        else:
            links_pendientes.append(url)
    
    # Tomar solo un lote pequeño para procesar
    lote_actual = links_pendientes[:limite_lote]
    
    print(f"📊 ANÁLISIS DE LOTE:")
    print(f"   🔄 Total pendientes: {len(links_pendientes)}")
    print(f"   ✅ Ya procesadas: {len(links_ya_procesados)}")
    print(f"   🎯 Lote actual: {len(lote_actual)} propiedades")
    
    if lote_actual:
        print(f"   📋 IDs del lote actual:")
        for i, url in enumerate(lote_actual, 1):
            id_interno = url.split("-")[-1].replace("/", "")
            print(f"      {i}. ID {id_interno}")
    
    return lote_actual, len(links_ya_procesados), len(links_pendientes)

def mostrar_estadisticas_bd(cursor):
    """Muestra estadísticas actuales de la BD"""
    print(f"\n📊 ESTADÍSTICAS ACTUALES DE LA BD:")
    print("=" * 50)
    
    try:
        # Total propiedades
        cursor.execute("SELECT COUNT(*) FROM propiedades")
        total_propiedades = cursor.fetchone()[0]
        cursor.fetchall()
        
        # Propiedades con imágenes
        cursor.execute("""
            SELECT COUNT(DISTINCT p.id) 
            FROM propiedades p 
            INNER JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
        """)
        con_imagenes = cursor.fetchone()[0]
        cursor.fetchall()
        
        # Propiedades sin imágenes
        sin_imagenes = total_propiedades - con_imagenes
        
        # Total imágenes
        cursor.execute("SELECT COUNT(*) FROM imagenes_propiedad")
        total_imagenes = cursor.fetchone()[0]
        cursor.fetchall()
        
        # Distribución de imágenes por propiedad
        cursor.execute("""
            SELECT p.id_interno, COUNT(ip.id) as num_imagenes
            FROM propiedades p 
            LEFT JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
            GROUP BY p.id, p.id_interno
            ORDER BY num_imagenes DESC
        """)
        distribucion = cursor.fetchall()
        cursor.fetchall()
        
        print(f"   🏠 Total propiedades: {total_propiedades}")
        print(f"   📸 Con imágenes: {con_imagenes}")
        print(f"   ❌ Sin imágenes: {sin_imagenes}")
        print(f"   📊 Total imágenes: {total_imagenes}")
        
        if con_imagenes > 0:
            promedio = total_imagenes / con_imagenes
            print(f"   📈 Promedio imágenes/propiedad: {promedio:.1f}")
        
        # Mostrar top propiedades con más imágenes
        if distribucion:
            print(f"\n   🏆 TOP PROPIEDADES CON MÁS IMÁGENES:")
            for i, (id_interno, num_imagenes) in enumerate(distribucion[:8], 1):
                estado = "✅" if num_imagenes >= 5 else "⚠️"
                print(f"      {i:2d}. ID {id_interno}: {num_imagenes} imágenes {estado}")
        
        # Progreso general
        if total_propiedades > 0:
            progreso = (con_imagenes / total_propiedades) * 100
            print(f"\n   📈 PROGRESO GENERAL: {progreso:.1f}% completado")
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")

# [Aquí van todas las funciones de tu programa original: descargar, propiedad_id, verificar_si_bloqueado, etc.]
# [Las copio idénticas de tu código para no repetir...]

def descargar(url, ruta):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://remax.pe/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9'
        }
        r = requests.get(url, stream=True, timeout=20, headers=headers)
        if r.status_code == 200:
            with open(ruta, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"⚠️ Error descarga: {str(e)[:50]}")
    return False

def propiedad_id(cursor, id_interno):
    cursor.execute("SELECT id FROM propiedades WHERE id_interno = %s", (id_interno,))
    res = cursor.fetchone()
    cursor.fetchall()
    return res[0] if res else None

def verificar_si_bloqueado(driver):
    """Detecta si el sitio nos está bloqueando"""
    try:
        indicadores_bloqueo = [
            "blocked", "captcha", "robot", "automated", 
            "suspicious", "rate limit", "demasiadas solicitudes",
            "access denied", "forbidden", "cloudflare"
        ]
        
        texto_pagina = driver.page_source.lower()
        titulo_pagina = driver.title.lower()
        
        for indicador in indicadores_bloqueo:
            if indicador in texto_pagina or indicador in titulo_pagina:
                print(f"  🚫 Posible bloqueo detectado: {indicador}")
                return True
        
        if len(driver.page_source) < 1000:
            print("  🚫 Página sospechosamente pequeña")
            return True
            
        return False
    except:
        return True

def limpiar_cache(driver):
    """Limpia cookies y cache para parecer más humano"""
    try:
        driver.delete_all_cookies()
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        print("  🧹 Cache y cookies limpiados")
        time.sleep(random.uniform(1, 2))
    except Exception as e:
        print(f"  ⚠️ Error limpiando cache: {e}")

def simular_humano_avanzado(driver):
    """Simula comportamiento humano más realista"""
    try:
        scrolls = random.randint(2, 4)
        for _ in range(scrolls):
            scroll_amount = random.randint(150, 400)
            direction = random.choice([1, -1])
            driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction});")
            time.sleep(random.uniform(0.8, 1.5))
        
        driver.execute_script("""
            const moves = 3 + Math.floor(Math.random() * 3);
            for(let i = 0; i < moves; i++) {
                setTimeout(() => {
                    const event = new MouseEvent('mousemove', {
                        clientX: Math.random() * window.innerWidth,
                        clientY: Math.random() * window.innerHeight,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                }, i * 200);
            }
        """)
        
        time.sleep(random.uniform(1, 2.5))
        
        if random.random() < 0.3:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                driver.execute_script("arguments[0].click();", body)
                time.sleep(random.uniform(0.5, 1))
            except:
                pass
                
    except Exception as e:
        print(f"  ⚠️ Error simulando humano: {e}")

def resetear_slider_mejorado(driver):
    """Intenta resetear el slider a la primera imagen"""
    try:
        print("  🔄 Reseteando slider...")
        
        reset_selectors = [
            ".sp-previous-arrow",
            ".sp-first-arrow", 
            ".slider-prev",
            ".prev",
            "button[class*='prev']",
            "[data-action='prev']"
        ]
        
        for _ in range(8):
            btn_encontrado = False
            for selector in reset_selectors:
                try:
                    prev_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if prev_btn.is_displayed() and prev_btn.is_enabled():
                        driver.execute_script("arguments[0].click();", prev_btn)
                        btn_encontrado = True
                        time.sleep(random.uniform(0.8, 1.2))
                        break
                except:
                    continue
            if not btn_encontrado:
                break
        
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(5):
                body.send_keys(Keys.HOME)
                time.sleep(0.3)
                body.send_keys(Keys.ARROW_LEFT)
                time.sleep(0.3)
        except:
            pass
        
        try:
            miniaturas = driver.find_elements(By.CSS_SELECTOR, ".sp-thumbnail, .thumbnail, .thumb")
            if miniaturas:
                driver.execute_script("arguments[0].click();", miniaturas[0])
                time.sleep(1)
        except:
            pass
                
        print("  ✅ Slider reseteado")
        time.sleep(random.uniform(2, 3))
        
    except Exception as e:
        print(f"  ⚠️ Error reseteando slider: {e}")

def extraer_imagenes(driver, url, intento=1):
    """Extrae imágenes con estrategias mejoradas"""
    
    print(f"\n🔍 Accediendo a: {url}")
    id_prop = url.split("-")[-1].replace("/", "")
    print(f"📋 ID Propiedad: {id_prop}")
    
    try:
        driver.get(url)
    except Exception as e:
        print(f"❌ Error cargando página: {e}")
        raise e
    
    pausa_inicial = random.uniform(8, 15)
    print(f"⏱️ Esperando carga inicial: {pausa_inicial:.1f}s")
    time.sleep(pausa_inicial)
    
    if verificar_si_bloqueado(driver):
        print("🚫 Página bloqueada detectada")
        raise Exception("Página bloqueada")
    
    simular_humano_avanzado(driver)
    
    try:
        slider_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "sliderRemax"))
        )
        print("  ✅ Slider detectado")
    except TimeoutException:
        print("  ❌ No se encontró slider")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".slider, .gallery, .images"))
            )
            print("  ✅ Galería alternativa detectada")
        except:
            return []
    
    resetear_slider_mejorado(driver)
    
    imgs_unicas = set()
    imagen_anterior = None
    clicks_realizados = 0
    max_clicks = 60
    clicks_sin_cambio = 0
    max_sin_cambio = 6
    
    img_selectors = [
        "img[src*='digitaloceanspaces.com']",
        "#sliderRemax img[src*='http']",
        ".sp-slide img[src*='http']",
        "img[src*='remax']",
        ".sp-slides-container img",
        ".slider img[src*='http']",
        ".gallery img[src*='http']",
        "img[src*='cdn']"
    ]
    
    btn_selectors = [
        ".sp-next-arrow",
        ".slider-next", 
        ".next",
        "button[class*='next']",
        ".sp-arrow.sp-next-arrow",
        "[data-action='next']",
        ".gallery-next",
        ".arrow-right"
    ]
    
    print(f"🎯 Iniciando extracción de imágenes...")
    
    for click_num in range(max_clicks):
        clicks_realizados += 1
        
        if click_num % 5 == 0 and click_num > 0:
            simular_humano_avanzado(driver)
        
        img_actual = None
        for selector in img_selectors:
            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for img_elem in img_elements:
                    if img_elem.is_displayed():
                        src = img_elem.get_attribute("src")
                        if (src and src.startswith("http") and 
                            "placeholder" not in src.lower() and 
                            "loading" not in src.lower() and
                            "spinner" not in src.lower()):
                            img_actual = src
                            break
                if img_actual:
                    break
            except (StaleElementReferenceException, NoSuchElementException):
                continue
        
        if img_actual:
            if img_actual not in imgs_unicas:
                imgs_unicas.add(img_actual)
                print(f"  📸 Imagen {len(imgs_unicas)}: ...{img_actual.split('/')[-1][:40]}")
                clicks_sin_cambio = 0
                imagen_anterior = img_actual
            elif img_actual == imagen_anterior:
                clicks_sin_cambio += 1
                if clicks_sin_cambio <= 2:
                    print(f"  🔄 Misma imagen (sin cambio: {clicks_sin_cambio})")
            else:
                clicks_sin_cambio = 0
        else:
            clicks_sin_cambio += 1
            if clicks_sin_cambio <= 3:
                print(f"  ❌ No se detectó imagen (intento {clicks_realizados})")
        
        if clicks_sin_cambio >= max_sin_cambio:
            print(f"  🛑 Finalizando: {clicks_sin_cambio} clicks sin nuevas imágenes")
            break
        
        btn_clickeado = False
        
        for btn_selector in btn_selectors:
            try:
                next_btns = driver.find_elements(By.CSS_SELECTOR, btn_selector)
                for next_btn in next_btns:
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            next_btn
                        )
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        driver.execute_script("arguments[0].click();", next_btn)
                        btn_clickeado = True
                        break
                if btn_clickeado:
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        
        if not btn_clickeado:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ARROW_RIGHT)
                btn_clickeado = True
            except:
                pass
        
        if not btn_clickeado:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.SPACE)
                btn_clickeado = True
            except:
                pass
        
        if not btn_clickeado:
            print(f"  ⚠️ No se pudo avanzar en click {clicks_realizados}")
            if clicks_sin_cambio >= 3:
                break
        
        pausa_click = random.uniform(2, 4)
        time.sleep(pausa_click)
    
    resultado = list(imgs_unicas)
    print(f"  ✅ Extracción completada: {len(resultado)} imágenes únicas")
    
    return resultado

def extraer_imagenes_con_reintentos(driver, url, max_intentos=2):
    """Extrae imágenes con sistema de reintentos"""
    for intento in range(1, max_intentos + 1):
        try:
            if intento > 1:
                print(f"  🔄 Reintento #{intento}/{max_intentos}")
                tiempo_espera = random.uniform(10, 20) * intento
                print(f"  ⏱️ Esperando {tiempo_espera:.1f}s antes del reintento...")
                time.sleep(tiempo_espera)
                
                limpiar_cache(driver)
            
            resultado = extraer_imagenes(driver, url, intento)
            
            if resultado:
                return resultado
            elif intento == max_intentos:
                print(f"  💥 Sin imágenes después de {max_intentos} intentos")
                return []
                
        except Exception as e:
            print(f"  ❌ Error en intento {intento}: {str(e)[:100]}")
            if intento == max_intentos:
                print(f"  💥 Falló después de {max_intentos} intentos")
                return []
    
    return []

def guardar(cursor, pid, urls):
    if not urls:
        return 0
    
    carpeta = os.path.join(IMAGENES_DIR, str(pid))
    os.makedirs(carpeta, exist_ok=True)
    print(f"  📁 Guardando en: images/{pid}/")
    
    cursor.execute("DELETE FROM imagenes_propiedad WHERE propiedad_id = %s", (pid,))
    cursor.fetchall()
    
    guardadas = 0
    for idx, url in enumerate(urls, start=1):
        nombre = f"imagen_{idx:02d}.jpg"
        ruta_local = os.path.join(carpeta, nombre)
        es_principal = 1 if idx == 1 else 0
        
        print(f"    💾 Descargando imagen {idx}/{len(urls)}...")
        if descargar(url, ruta_local):
            cursor.execute("""
                INSERT INTO imagenes_propiedad (propiedad_id, ruta_local, url_imagen, es_principal)
                VALUES (%s, %s, %s, %s)
            """, (pid, ruta_local, url, es_principal))
            cursor.fetchall()
            guardadas += 1
        
        time.sleep(random.uniform(0.3, 0.8))
    
    return guardadas

def crear_driver():
    """Crea un nuevo driver con configuración optimizada"""
    opts = uc.ChromeOptions()
    
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = uc.Chrome(options=opts, headless=False)
    
    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
        Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
        delete navigator.__webdriver_script_fn;
        delete window.chrome.runtime.onConnect;
        delete window.chrome.runtime.onMessage;
    """)
    
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    return driver

def main():
    print("🚀 DESCARGA POR LOTES INCREMENTAL v2.0")
    print("="*70)
    print("🎯 Procesa solo propiedades pendientes en lotes pequeños")
    print("📊 Evita re-procesar propiedades que ya tienen imágenes")
    print("="*70)
    
    conn = conectar_mysql()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Mostrar estadísticas actuales
    mostrar_estadisticas_bd(cur)
    
    try:
        with open("data/links.json", encoding="utf-8") as f:
            todos_los_links = json.load(f)
        print(f"\n📋 {len(todos_los_links)} links totales cargados")
    except FileNotFoundError:
        print("❌ No se encontró data/links.json")
        print("💡 Ejecuta primero: python extraer_links_agente.py (opción 2)")
        return
    
    # Obtener propiedades ya procesadas (con 5+ imágenes)
    MINIMO_IMAGENES = 5
    propiedades_procesadas = obtener_propiedades_procesadas(cur, MINIMO_IMAGENES)
    
    # Filtrar y obtener lote actual
    TAMAÑO_LOTE = 6  # Procesar máximo 6 por sesión
    lote_actual, ya_procesadas, total_pendientes = filtrar_links_pendientes(
        todos_los_links, propiedades_procesadas, TAMAÑO_LOTE
    )
    
    if not lote_actual:
        print("🎉 ¡TODAS LAS PROPIEDADES YA ESTÁN PROCESADAS!")
        print(f"   ✅ {ya_procesadas}/{len(todos_los_links)} propiedades con {MINIMO_IMAGENES}+ imágenes")
        conn.close()
        return
    
    # Mostrar plan de procesamiento
    print(f"\n🎯 PLAN DE PROCESAMIENTO:")
    print(f"   📊 Progreso actual: {ya_procesadas}/{len(todos_los_links)} ({(ya_procesadas/len(todos_los_links)*100):.1f}%)")
    print(f"   🔄 Pendientes totales: {total_pendientes}")
    print(f"   🎯 Lote actual: {len(lote_actual)} propiedades")
    print(f"   📈 Después del lote: {ya_procesadas + len(lote_actual)}/{len(todos_los_links)}")
    
    # Confirmación
    respuesta = input(f"\n🤔 ¿Procesar este lote de {len(lote_actual)} propiedades? (s/n): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Proceso cancelado")
        conn.close()
        return
    
    os.makedirs(IMAGENES_DIR, exist_ok=True)
    
    # Configuración para lotes pequeños
    REINICIAR_CADA = 3  # Cada 3 propiedades
    total_imagenes = 0
    propiedades_exitosas = 0
    propiedades_fallidas = 0
    driver = None
    
    inicio_tiempo = time.time()
    
    print(f"\n🎯 INICIANDO PROCESAMIENTO DEL LOTE")
    print("="*70)
    
    for i, url in enumerate(lote_actual, 1):
        tiempo_transcurrido = time.time() - inicio_tiempo
        print(f"\n{'='*80}")
        print(f"🏠 PROPIEDAD {i}/{len(lote_actual)} DEL LOTE ACTUAL")
        print(f"📊 Progreso total: {ya_procesadas + propiedades_exitosas}/{len(todos_los_links)}")
        print(f"⏱️ Tiempo: {tiempo_transcurrido/60:.1f} min | Exitosas: {propiedades_exitosas} | Fallidas: {propiedades_fallidas}")
        print(f"🔗 {url}")
        
        # Crear o reiniciar navegador
        if driver is None or (i - 1) % REINICIAR_CADA == 0:
            if driver:
                print(f"🔄 Reiniciando navegador (cada {REINICIAR_CADA} propiedades)")
                try:
                    driver.quit()
                except:
                    pass
                pausa_reinicio = random.uniform(25, 40)
                print(f"⏱️ Pausa de reinicio: {pausa_reinicio:.1f}s")
                time.sleep(pausa_reinicio)
            
            print("🌐 Creando nuevo navegador...")
            try:
                driver = crear_driver()
                print("✅ Navegador creado exitosamente")
            except Exception as e:
                print(f"❌ Error creando navegador: {e}")
                time.sleep(10)
                continue
        
        # Obtener ID de propiedad
        id_interno = url.split("-")[-1].replace("/", "")
        pid = propiedad_id(cur, id_interno)
        
        if not pid:
            print(f"❌ No existe propiedad en BD: {id_interno}")
            propiedades_fallidas += 1
            continue
        
        try:
            # Verificar estado del navegador
            try:
                driver.current_url
            except:
                print("🔄 Driver no responde, creando uno nuevo...")
                driver = crear_driver()
            
            # Verificar bloqueos
            if verificar_si_bloqueado(driver):
                print("🚫 Bloqueo detectado, forzando reinicio...")
                try:
                    driver.quit()