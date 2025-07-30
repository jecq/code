# descargar_imagenes_antideteccion_mejorado1_cl.py
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
        
        # Verificar si la página está vacía o no cargó correctamente
        if len(driver.page_source) < 1000:
            print("  🚫 Página sospechosamente pequeña")
            return True
            
        return False
    except:
        return True  # Si hay error, asumir bloqueo

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
        # Scroll aleatorio más natural
        scrolls = random.randint(2, 4)
        for _ in range(scrolls):
            scroll_amount = random.randint(150, 400)
            direction = random.choice([1, -1])  # Arriba o abajo
            driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction});")
            time.sleep(random.uniform(0.8, 1.5))
        
        # Simular movimiento de mouse más realista
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
        
        # Pausa aleatoria
        time.sleep(random.uniform(1, 2.5))
        
        # Ocasionalmente simular click en área vacía
        if random.random() < 0.3:  # 30% de probabilidad
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                driver.execute_script("arguments[0].click();", body)
                time.sleep(random.uniform(0.5, 1))
            except:
                pass
                
    except Exception as e:
        print(f"  ⚠️ Error simulando humano: {e}")

def resetear_slider_mejorado(driver):
    """Intenta resetear el slider a la primera imagen con múltiples estrategias"""
    try:
        print("  🔄 Reseteando slider...")
        
        # Estrategia 1: Botones de navegación
        reset_selectors = [
            ".sp-previous-arrow",
            ".sp-first-arrow", 
            ".slider-prev",
            ".prev",
            "button[class*='prev']",
            "[data-action='prev']"
        ]
        
        # Hacer múltiples clicks hacia atrás
        for _ in range(8):  # Más intentos
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
        
        # Estrategia 2: Teclas de flecha
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(5):
                body.send_keys(Keys.HOME)  # Ir al inicio
                time.sleep(0.3)
                body.send_keys(Keys.ARROW_LEFT)
                time.sleep(0.3)
        except:
            pass
        
        # Estrategia 3: Click en primera miniatura si existe
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

def extraer_imagenes_con_reintentos(driver, url, max_intentos=3):
    """Extrae imágenes con sistema de reintentos mejorado"""
    for intento in range(1, max_intentos + 1):
        try:
            if intento > 1:
                print(f"  🔄 Reintento #{intento}/{max_intentos}")
                # Pausa progresiva más larga
                tiempo_espera = random.uniform(10, 20) * intento
                print(f"  ⏱️ Esperando {tiempo_espera:.1f}s antes del reintento...")
                time.sleep(tiempo_espera)
                
                # Limpiar cache antes del reintento
                limpiar_cache(driver)
            
            resultado = extraer_imagenes(driver, url, intento)
            
            # Si obtuvo al menos 1 imagen, considerarlo éxito
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

def extraer_imagenes(driver, url, intento=1):
    """Extrae imágenes con estrategias mejoradas"""
    
    print(f"\n🔍 Accediendo a: {url}")
    id_prop = url.split("-")[-1].replace("/", "")
    print(f"📋 ID Propiedad: {id_prop}")
    
    # Verificar si estamos bloqueados antes de proceder
    try:
        driver.get(url)
    except Exception as e:
        print(f"❌ Error cargando página: {e}")
        raise e
    
    # Pausa inicial más larga y aleatoria
    pausa_inicial = random.uniform(8, 15)
    print(f"⏱️ Esperando carga inicial: {pausa_inicial:.1f}s")
    time.sleep(pausa_inicial)
    
    # Verificar bloqueo después de cargar
    if verificar_si_bloqueado(driver):
        print("🚫 Página bloqueada detectada")
        raise Exception("Página bloqueada")
    
    # Simular comportamiento humano
    simular_humano_avanzado(driver)
    
    # Verificar que existe el slider con mayor timeout
    try:
        slider_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "sliderRemax"))
        )
        print("  ✅ Slider detectado")
    except TimeoutException:
        print("  ❌ No se encontró slider")
        # Intentar con otros selectores
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".slider, .gallery, .images"))
            )
            print("  ✅ Galería alternativa detectada")
        except:
            return []
    
    # Resetear slider al inicio
    resetear_slider_mejorado(driver)
    
    imgs_unicas = set()
    imagen_anterior = None
    clicks_realizados = 0
    max_clicks = 60  # Aumentado
    clicks_sin_cambio = 0
    max_sin_cambio = 6  # Aumentado
    
    # Selectores mejorados para imágenes
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
    
    # Selectores mejorados para botones
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
        
        # Cada cierto número de clicks, simular comportamiento más humano
        if click_num % 5 == 0 and click_num > 0:
            simular_humano_avanzado(driver)
        
        # Buscar imagen actual con verificación mejorada
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
        
        # Verificar si es una imagen nueva
        if img_actual:
            if img_actual not in imgs_unicas:
                imgs_unicas.add(img_actual)
                print(f"  📸 Imagen {len(imgs_unicas)}: ...{img_actual.split('/')[-1][:40]}")
                clicks_sin_cambio = 0
                imagen_anterior = img_actual
            elif img_actual == imagen_anterior:
                clicks_sin_cambio += 1
                if clicks_sin_cambio <= 2:  # Solo mostrar las primeras veces
                    print(f"  🔄 Misma imagen (sin cambio: {clicks_sin_cambio})")
            else:
                clicks_sin_cambio = 0
        else:
            clicks_sin_cambio += 1
            if clicks_sin_cambio <= 3:
                print(f"  ❌ No se detectó imagen (intento {clicks_realizados})")
        
        # Verificar si debemos continuar
        if clicks_sin_cambio >= max_sin_cambio:
            print(f"  🛑 Finalizando: {clicks_sin_cambio} clicks sin nuevas imágenes")
            break
        
        # Buscar y hacer click en botón siguiente con estrategias múltiples
        btn_clickeado = False
        
        # Estrategia 1: Botones CSS
        for btn_selector in btn_selectors:
            try:
                next_btns = driver.find_elements(By.CSS_SELECTOR, btn_selector)
                for next_btn in next_btns:
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        # Scroll al botón
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                            next_btn
                        )
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        # Click con JavaScript
                        driver.execute_script("arguments[0].click();", next_btn)
                        btn_clickeado = True
                        break
                if btn_clickeado:
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        
        # Estrategia 2: Tecla de flecha derecha
        if not btn_clickeado:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ARROW_RIGHT)
                btn_clickeado = True
            except:
                pass
        
        # Estrategia 3: Espaciador o Enter
        if not btn_clickeado:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.SPACE)
                btn_clickeado = True
            except:
                pass
        
        if not btn_clickeado:
            print(f"  ⚠️ No se pudo avanzar en click {clicks_realizados}")
            # Si no puede avanzar varias veces seguidas, salir
            if clicks_sin_cambio >= 3:
                break
        
        # Pausa entre clicks más realista
        pausa_click = random.uniform(2, 4)  # Más lenta
        time.sleep(pausa_click)
    
    resultado = list(imgs_unicas)
    print(f"  ✅ Extracción completada: {len(resultado)} imágenes únicas")
    
    return resultado

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
        
        # Pausa entre descargas
        time.sleep(random.uniform(0.3, 0.8))
    
    return guardadas

def crear_driver():
    """Crea un nuevo driver con configuración optimizada"""
    opts = uc.ChromeOptions()
    
    # Opciones básicas
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    
    # Opciones anti-detección adicionales
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    
    # User agent más convincente
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = uc.Chrome(options=opts, headless=False)
    
    # Scripts anti-detección mejorados
    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
        Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
        delete navigator.__webdriver_script_fn;
        delete window.chrome.runtime.onConnect;
        delete window.chrome.runtime.onMessage;
    """)
    
    # Configurar timeouts
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    return driver

def main():
    print("🚀 DESCARGA DE IMÁGENES CON ANTI-DETECCIÓN MEJORADA v2.0")
    print("="*70)
    
    conn = conectar_mysql()
    if not conn:
        return
    
    cur = conn.cursor()
    
    try:
        with open("data/links.json", encoding="utf-8") as f:
            links = json.load(f)
        print(f"📋 {len(links)} propiedades cargadas desde links.json")
    except FileNotFoundError:
        print("❌ No se encontró data/links.json")
        return
    
    os.makedirs(IMAGENES_DIR, exist_ok=True)
    
    # Configuración para reiniciar navegador
    REINICIAR_CADA = 3  # Reiniciar cada 3 propiedades (más frecuente)
    total_imagenes = 0
    propiedades_exitosas = 0
    propiedades_fallidas = 0
    driver = None
    
    inicio_tiempo = time.time()
    
    for i, url in enumerate(links, 1):
        tiempo_transcurrido = time.time() - inicio_tiempo
        print(f"\n{'='*80}")
        print(f"🏠 PROPIEDAD {i}/{len(links)} | Tiempo: {tiempo_transcurrido/60:.1f} min")
        print(f"📊 Exitosas: {propiedades_exitosas} | Fallidas: {propiedades_fallidas}")
        print(f"🔗 {url}")
        
        # Crear o reiniciar navegador cuando sea necesario
        if driver is None or (i - 1) % REINICIAR_CADA == 0:
            if driver:
                print(f"🔄 Reiniciando navegador (cada {REINICIAR_CADA} propiedades)")
                try:
                    driver.quit()
                except:
                    pass
                # Pausa larga entre reinicios
                pausa_reinicio = random.uniform(25, 40)
                print(f"⏱️ Pausa de reinicio: {pausa_reinicio:.1f}s")
                time.sleep(pausa_reinicio)
            
            # Crear nuevo navegador
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
                driver.current_url  # Test si el driver está vivo
            except:
                print("🔄 Driver no responde, creando uno nuevo...")
                driver = crear_driver()
            
            # Verificar si estamos bloqueados antes de proceder
            if verificar_si_bloqueado(driver):
                print("🚫 Bloqueo detectado, forzando reinicio...")
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                time.sleep(random.uniform(45, 60))  # Pausa muy larga
                continue
            
            # Intentar extraer imágenes
            print("🎯 Iniciando extracción...")
            imgs = extraer_imagenes_con_reintentos(driver, url, max_intentos=2)
            
            if imgs:
                print(f"💾 Guardando {len(imgs)} imágenes en base de datos...")
                guardadas = guardar(cur, pid, imgs)
                conn.commit()
                total_imagenes += guardadas
                propiedades_exitosas += 1
                print(f"✅ ÉXITO: {guardadas}/{len(imgs)} imágenes guardadas → images/{pid}/")
            else:
                print("⚠️ Sin imágenes encontradas")
                propiedades_fallidas += 1
            
            # Limpiar cache cada 2 propiedades
            if i % 2 == 0:
                limpiar_cache(driver)
                
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"❌ Error procesando propiedad: {error_msg}")
            propiedades_fallidas += 1
            
            # Si hay error crítico, reiniciar navegador
            if any(palabra in error_msg.lower() for palabra in 
                   ["timeout", "disconnected", "crashed", "blocked", "session", "chrome"]):
                print("🔄 Error crítico detectado, reiniciando navegador...")
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                time.sleep(random.uniform(30, 45))
        
        # Pausa MUY larga entre propiedades para evitar detección
        if i < len(links):  # No pausar después de la última
            pausa = random.uniform(15, 30)  # 15-30 segundos
            print(f"⏱️ Pausa anti-detección: {pausa:.1f}s antes de siguiente propiedad...")
            time.sleep(pausa)
    
    # Limpieza final
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    try:
        conn.close()
    except:
        pass
    
    # Estadísticas finales
    tiempo_total = (time.time() - inicio_tiempo) / 60
    print(f"\n🎉 PROCESO COMPLETADO EN {tiempo_total:.1f} MINUTOS")
    print(f"="*70)
    print(f"📊 ESTADÍSTICAS FINALES:")
    print(f"   🏠 Total propiedades procesadas: {len(links)}")
    print(f"   ✅ Propiedades exitosas: {propiedades_exitosas}")
    print(f"   ❌ Propiedades fallidas: {propiedades_fallidas}")
    print(f"   📸 Total imágenes descargadas: {total_imagenes}")
    print(f"   📈 Tasa de éxito: {(propiedades_exitosas/len(links)*100):.1f}%")
    
    if total_imagenes > 0:
        print(f"   📊 Promedio imágenes por propiedad exitosa: {total_imagenes/propiedades_exitosas:.1f}")

if __name__ == "__main__":
    main()