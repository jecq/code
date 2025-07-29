# descargar_imagenes_incremental_CL.py - CÓDIGO COMPLETO v4.2 MEJORADO
import json, os, time, requests, mysql.connector, random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys

# Instalar: pip install selenium-stealth
try:
    from selenium_stealth import stealth
    STEALTH_AVAILABLE = True
except ImportError:
    print("⚠️ selenium-stealth no instalado. Ejecuta: pip install selenium-stealth")
    STEALTH_AVAILABLE = False

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

def obtener_propiedades_procesadas(cursor, minimo_imagenes=10):
    """Obtiene lista de propiedades que ya tienen imágenes descargadas (mínimo especificado)"""
    try:
        cursor.execute("""
            SELECT p.id_interno, COUNT(ip.id) as num_imagenes
            FROM propiedades p 
            LEFT JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
            GROUP BY p.id, p.id_interno
            HAVING COUNT(ip.id) >= %s
        """, (minimo_imagenes,))
        
        procesadas = [str(row[0]) for row in cursor.fetchall()]
        cursor.fetchall()  # Limpiar buffer
        
        print(f"📋 Propiedades con {minimo_imagenes}+ imágenes: {len(procesadas)}")
        if procesadas:
            print(f"   IDs: {', '.join(procesadas[:10])}{'...' if len(procesadas) > 10 else ''}")
        
        return set(procesadas)
        
    except Exception as e:
        print(f"⚠️ Error obteniendo propiedades procesadas: {e}")
        return set()

def verificar_imagenes_existentes(cursor, id_interno, minimo_imagenes=10):
    """Verifica si una propiedad específica ya tiene suficientes imágenes"""
    try:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM imagenes_propiedad ip
            INNER JOIN propiedades p ON p.id = ip.propiedad_id
            WHERE p.id_interno = %s
        """, (id_interno,))
        
        count = cursor.fetchone()[0]
        cursor.fetchall()
        
        return count >= minimo_imagenes
        
    except Exception as e:
        print(f"⚠️ Error verificando imágenes: {e}")
        return False

def filtrar_links_pendientes(links, propiedades_procesadas):
    """Filtra los links para obtener solo los pendientes"""
    links_pendientes = []
    links_ya_procesados = []
    
    for url in links:
        id_interno = url.split("-")[-1].replace("/", "")
        
        if id_interno in propiedades_procesadas:
            links_ya_procesados.append(url)
        else:
            links_pendientes.append(url)
    
    print(f"📊 ANÁLISIS DE LINKS:")
    print(f"   🔄 Links pendientes: {len(links_pendientes)}")
    print(f"   ✅ Links ya procesados: {len(links_ya_procesados)}")
    print(f"   📋 Total links: {len(links)}")
    
    return links_pendientes, links_ya_procesados
def mostrar_resumen_procesadas_mejorado(cursor, links_ya_procesados, minimo_imagenes=10):
    """Muestra resumen de propiedades ya procesadas con el nuevo criterio"""
    if not links_ya_procesados:
        return
    
    print(f"\n📊 PROPIEDADES CON {minimo_imagenes}+ IMÁGENES ({len(links_ya_procesados)}):")
    print("=" * 60)
    
    for i, url in enumerate(links_ya_procesados[:10], 1):
        id_interno = url.split("-")[-1].replace("/", "")
        
        try:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM imagenes_propiedad ip
                INNER JOIN propiedades p ON p.id = ip.propiedad_id
                WHERE p.id_interno = %s
            """, (id_interno,))
            
            num_imagenes = cursor.fetchone()[0]
            cursor.fetchall()
            
            print(f"   {i:2d}. ID {id_interno} → {num_imagenes} imágenes ✅")
            
        except:
            print(f"   {i:2d}. ID {id_interno} → Error consultando")
    
    if len(links_ya_procesados) > 10:
        print(f"   ... y {len(links_ya_procesados) - 10} más")
    
    print()

def crear_respaldo_progreso(propiedades_exitosas, propiedades_fallidas, total_imagenes):
    """Crea respaldo del progreso actual"""
    try:
        respaldo = {
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "propiedades_exitosas": propiedades_exitosas,
            "propiedades_fallidas": propiedades_fallidas,
            "total_imagenes": total_imagenes,
            "timestamp": time.time()
        }
        
        os.makedirs("backups", exist_ok=True)
        archivo_respaldo = f"backups/progreso_{int(time.time())}.json"
        
        with open(archivo_respaldo, 'w', encoding='utf-8') as f:
            json.dump(respaldo, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Respaldo creado: {archivo_respaldo}")
        
    except Exception as e:
        print(f"⚠️ Error creando respaldo: {e}")

def mostrar_estadisticas_detalladas_mejoradas(cursor, minimo_imagenes=10):
    """Muestra estadísticas detalladas con el nuevo criterio"""
    print(f"\n📊 ESTADÍSTICAS DETALLADAS (Mínimo {minimo_imagenes} imágenes):")
    print("=" * 60)
    
    try:
        # Total de propiedades en BD
        cursor.execute("SELECT COUNT(*) FROM propiedades")
        total_propiedades = cursor.fetchone()[0]
        cursor.fetchall()
        
        # Propiedades con suficientes imágenes (10+)
        cursor.execute("""
            SELECT COUNT(DISTINCT p.id) 
            FROM propiedades p 
            INNER JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
            GROUP BY p.id
            HAVING COUNT(ip.id) >= %s
        """, (minimo_imagenes,))
        propiedades_suficientes = len(cursor.fetchall())
        cursor.fetchall()
        
        # Propiedades con pocas imágenes (menos del mínimo)
        cursor.execute("""
            SELECT p.id_interno, COUNT(ip.id) as num_imagenes
            FROM propiedades p 
            LEFT JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
            GROUP BY p.id, p.id_interno
            HAVING COUNT(ip.id) > 0 AND COUNT(ip.id) < %s
            ORDER BY num_imagenes DESC
        """, (minimo_imagenes,))
        propiedades_insuficientes = cursor.fetchall()
        cursor.fetchall()
        
        # Propiedades sin imágenes
        cursor.execute("""
            SELECT COUNT(DISTINCT p.id) 
            FROM propiedades p 
            LEFT JOIN imagenes_propiedad ip ON p.id = ip.propiedad_id
            WHERE ip.id IS NULL
        """)
        propiedades_sin_imagenes = cursor.fetchone()[0]
        cursor.fetchall()
        
        # Total de imágenes
        cursor.execute("SELECT COUNT(*) FROM imagenes_propiedad")
        total_imagenes_bd = cursor.fetchone()[0]
        cursor.fetchall()
        
        # Mostrar estadísticas
        print(f"   🏠 Total propiedades en BD: {total_propiedades}")
        print(f"   ✅ Propiedades con {minimo_imagenes}+ imágenes: {propiedades_suficientes}")
        print(f"   ⚠️ Propiedades con pocas imágenes: {len(propiedades_insuficientes)}")
        print(f"   ❌ Propiedades sin imágenes: {propiedades_sin_imagenes}")
        print(f"   📸 Total imágenes en BD: {total_imagenes_bd}")
        
        # Mostrar propiedades con pocas imágenes
        if propiedades_insuficientes:
            print(f"\n🔍 PROPIEDADES QUE NECESITAN MÁS IMÁGENES:")
            for id_interno, num_imagenes in propiedades_insuficientes[:10]:
                print(f"   ID {id_interno} → {num_imagenes} imágenes (necesita {minimo_imagenes-num_imagenes} más)")
            if len(propiedades_insuficientes) > 10:
                print(f"   ... y {len(propiedades_insuficientes) - 10} más")
        
        # Progreso
        propiedades_pendientes = len(propiedades_insuficientes) + propiedades_sin_imagenes
        if total_propiedades > 0:
            print(f"   📈 Progreso: {(propiedades_suficientes/total_propiedades*100):.1f}%")
            print(f"   🔄 Pendientes de reprocesar: {propiedades_pendientes}")
        
        # Espacio en disco usado
        try:
            total_size = 0
            if os.path.exists(IMAGENES_DIR):
                for dirpath, dirnames, filenames in os.walk(IMAGENES_DIR):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)
                
                size_mb = total_size / (1024 * 1024)
                print(f"   💾 Espacio usado: {size_mb:.1f} MB")
        except:
            pass
            
    except Exception as e:
        print(f"⚠️ Error obteniendo estadísticas: {e}")
    
    print()

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

def simular_actividad_humana_real(driver):
    """Simula actividad humana muy realista"""
    try:
        print("  👤 Simulando actividad humana...")
        
        # 1. Hacer búsquedas aleatorias
        try:
            search_selectors = ["input[type='search']", "input[placeholder*='buscar']", ".search-input", "#search"]
            
            for selector in search_selectors:
                try:
                    search_box = driver.find_element(By.CSS_SELECTOR, selector)
                    if search_box.is_displayed():
                        search_box.click()
                        time.sleep(random.uniform(1, 2))
                        
                        # Escribir búsqueda falsa
                        fake_searches = ["casa lima", "departamento", "terreno", "oficina"]
                        fake_search = random.choice(fake_searches)
                        
                        for char in fake_search:
                            search_box.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.3))
                        
                        time.sleep(random.uniform(2, 4))
                        search_box.clear()
                        break
                except:
                    continue
        except:
            pass
        
        # 2. Scroll aleatorio por la página
        for _ in range(random.randint(3, 6)):
            scroll_amount = random.randint(200, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(1, 3))
        
        # 3. Hover en enlaces aleatorios
        try:
            links = driver.find_elements(By.TAG_NAME, "a")[:10]  # Primeros 10 links
            if links:
                random_link = random.choice(links)
                if random_link.is_displayed():
                    # Hover sin click
                    driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover'));", random_link)
                    time.sleep(random.uniform(0.5, 1.5))
        except:
            pass
        
        print("  ✅ Actividad humana simulada")
        
    except Exception as e:
        print(f"  ⚠️ Error simulando actividad: {e}")

def resetear_slider_mejorado(driver):
    """Intenta resetear el slider a la primera imagen con múltiples estrategias MEJORADAS"""
    try:
        print("  🔄 Reseteando slider a primera imagen...")
        
        # Estrategia 1: Botones de navegación - MÁS AGRESIVO
        reset_selectors = [
            ".sp-previous-arrow",
            ".sp-first-arrow", 
            ".slider-prev",
            ".prev",
            "button[class*='prev']",
            "[data-action='prev']",
            ".slick-prev",
            ".owl-prev"
        ]
        
        # Hacer MUCHOS más clicks hacia atrás
        for _ in range(15):  # AUMENTADO significativamente
            btn_encontrado = False
            for selector in reset_selectors:
                try:
                    prev_btns = driver.find_elements(By.CSS_SELECTOR, selector)
                    for prev_btn in prev_btns:
                        if prev_btn.is_displayed() and prev_btn.is_enabled():
                            # Verificar que no esté oculto
                            opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", prev_btn)
                            if opacity != "0":
                                driver.execute_script("arguments[0].click();", prev_btn)
                                btn_encontrado = True
                                time.sleep(random.uniform(0.5, 1.0))
                                break
                    if btn_encontrado:
                        break
                except:
                    continue
            if not btn_encontrado:
                break
        
        # Estrategia 2: Teclas de flecha - MÁS INTENSIVA
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(10):  # AUMENTADO
                body.send_keys(Keys.HOME)  # Ir al inicio
                time.sleep(0.2)
                body.send_keys(Keys.ARROW_LEFT)
                time.sleep(0.2)
        except:
            pass
        
        # Estrategia 3: Click en primera miniatura si existe
        try:
            miniaturas_selectors = [
                ".sp-thumbnail:first-child", 
                ".thumbnail:first-child", 
                ".thumb:first-child",
                ".slick-dots li:first-child",
                ".owl-dot:first-child"
            ]
            
            for selector in miniaturas_selectors:
                try:
                    primera_miniatura = driver.find_element(By.CSS_SELECTOR, selector)
                    if primera_miniatura.is_displayed():
                        driver.execute_script("arguments[0].click();", primera_miniatura)
                        time.sleep(1)
                        break
                except:
                    continue
        except:
            pass
        
        # Estrategia 4: NUEVA - JavaScript directo al slider
        try:
            driver.execute_script("""
                var slider = document.getElementById('sliderRemax');
                if (slider) {
                    // Intentar resetear con eventos personalizados
                    var resetEvent = new Event('reset');
                    slider.dispatchEvent(resetEvent);
                    
                    // Intentar con métodos comunes de sliders
                    if (slider.slick) {
                        slider.slick('slickGoTo', 0);
                    }
                    if (slider.swiper) {
                        slider.swiper.slideTo(0);
                    }
                }
            """)
        except:
            pass
                
        print("  ✅ Slider reseteado (intentos múltiples)")
        time.sleep(random.uniform(3, 5))  # PAUSA MÁS LARGA
        
    except Exception as e:
        print(f"  ⚠️ Error reseteando slider: {e}")

def crear_driver_ultra_stealth():
    """Crea driver con configuración stealth extrema"""
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    opts = uc.ChromeOptions()
    
    # Configuración básica
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    
    # Configuración stealth extrema
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--ignore-ssl-errors")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_argument("--disable-ipc-flooding-protection")
    
    # User agent aleatorio
    selected_ua = random.choice(user_agents)
    opts.add_argument(f"--user-agent={selected_ua}")
    
    # Crear driver
    driver = uc.Chrome(options=opts, headless=False)
    
    # Aplicar stealth si está disponible
    if STEALTH_AVAILABLE:
        stealth(driver,
            languages=["es-ES", "es"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
    
    # Scripts anti-detección ultra
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            // Eliminar todas las propiedades de webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__webdriver_script_fn;
            delete navigator.__webdriver_unwrapped;
            delete navigator.__webdriver_evaluate;
            delete navigator.__selenium_unwrapped;
            delete navigator.__fxdriver_unwrapped;
            
            // Falsificar plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => ({
                    0: {name: "Chrome PDF Plugin", description: "Portable Document Format", filename: "internal-pdf-viewer"},
                    1: {name: "Chrome PDF Viewer", description: "", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                    2: {name: "Native Client", description: "", filename: "internal-nacl-plugin"},
                    length: 3
                })
            });
            
            // Falsificar idiomas
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});
            
            // Falsificar permisos
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
            
            // Eliminar rastros de Chrome automation
            if (window.chrome && window.chrome.runtime && window.chrome.runtime.connect) {
                delete window.chrome.runtime.connect;
            }
        '''
    })
    
    # Configurar timeouts
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    return driver

def simular_navegacion_humana(driver, url_objetivo):
    """Simula navegación humana antes de ir al objetivo"""
    print("  👤 Simulando navegación humana...")
    
    try:
        # 1. Ir a la página principal
        driver.get("https://www.remax.pe/")
        time.sleep(random.uniform(5, 10))
        
        # 2. Simular actividad
        simular_actividad_humana_real(driver)
        
        # 3. Pausa larga antes del objetivo
        pausa_pre_objetivo = random.uniform(10, 20)
        print(f"  ⏱️ Pausa antes del objetivo: {pausa_pre_objetivo:.1f}s")
        time.sleep(pausa_pre_objetivo)
        
        # 4. Finalmente ir al objetivo
        driver.get(url_objetivo)
        
    except Exception as e:
        print(f"  ⚠️ Error en navegación humana: {e}")
        # Si falla, ir directo al objetivo
        driver.get(url_objetivo)
def extraer_imagenes(driver, url, intento=1):
    """Extrae imágenes con estrategias MEJORADAS para obtener MÁS imágenes"""
    
    print(f"\n🔍 Accediendo a: {url}")
    id_prop = url.split("-")[-1].replace("/", "")
    print(f"📋 ID Propiedad: {id_prop}")
    
    # Usar navegación humana en el primer intento
    if intento == 1:
        simular_navegacion_humana(driver, url)
    else:
        try:
            driver.get(url)
        except Exception as e:
            print(f"❌ Error cargando página: {e}")
            raise e
    
    # Pausa inicial MÁS LARGA
    pausa_inicial = random.uniform(12, 20)  # AUMENTADO
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
        slider_element = WebDriverWait(driver, 25).until(  # AUMENTADO timeout
            EC.presence_of_element_located((By.ID, "sliderRemax"))
        )
        print("  ✅ Slider detectado")
    except TimeoutException:
        print("  ❌ No se encontró slider")
        # Intentar con otros selectores
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".slider, .gallery, .images"))
            )
            print("  ✅ Galería alternativa detectada")
        except:
            return []
    
    # PAUSA ADICIONAL después de detectar slider
    print("  ⏱️ Pausa adicional para carga completa del slider...")
    time.sleep(random.uniform(5, 8))
    
    # Resetear slider al inicio MÁS AGRESIVO
    resetear_slider_mejorado(driver)
    
    imgs_unicas = set()
    imagen_anterior = None
    clicks_realizados = 0
    max_clicks = 100  # AUMENTADO significativamente
    clicks_sin_cambio = 0
    max_sin_cambio = 10  # AUMENTADO para ser más persistente
    intentos_sin_imagen = 0
    max_intentos_sin_imagen = 8  # NUEVO: límite de intentos sin detectar imagen
    
    # Selectores mejorados para imágenes - MÁS ESPECÍFICOS
    img_selectors = [
        "img[src*='digitaloceanspaces.com']",  # Mantener como prioridad
        "#sliderRemax img[src*='http']",
        ".sp-slide img[src*='http']",
        ".sp-slides-container img[src*='http']",
        "img[src*='remax']",
        "img[src*='cdn']",
        ".slider img[src*='http']",
        ".gallery img[src*='http']",
        "img[data-src*='http']",  # NUEVO: lazy loading
        "img[srcset*='http']"     # NUEVO: responsive images
    ]
    
    # Selectores mejorados para botones - MÁS OPCIONES
    btn_selectors = [
        ".sp-next-arrow",
        ".sp-arrow.sp-next-arrow", 
        ".slider-next", 
        ".next",
        "button[class*='next']",
        "[data-action='next']",
        ".gallery-next",
        ".arrow-right",
        "button[aria-label*='next' i]",  # NUEVO
        "button[title*='siguiente' i]",  # NUEVO
        ".slick-next",                   # NUEVO: para slick slider
        ".owl-next"                      # NUEVO: para owl carousel
    ]
    
    print(f"🎯 Iniciando extracción de imágenes...")
    
    for click_num in range(max_clicks):
        clicks_realizados += 1
        
        # Cada cierto número de clicks, simular comportamiento más humano
        if click_num % 8 == 0 and click_num > 0:  # REDUCIDO frecuencia
            simular_humano_avanzado(driver)
        
        # NUEVO: Scroll ocasional para asegurar que el slider esté visible
        if click_num % 15 == 0:
            try:
                slider = driver.find_element(By.ID, "sliderRemax")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
                time.sleep(1)
            except:
                pass
        
        # Buscar imagen actual con verificación MEJORADA
        img_actual = None
        for selector in img_selectors:
            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for img_elem in img_elements:
                    # VERIFICACIÓN MÁS ESTRICTA
                    if img_elem.is_displayed() and img_elem.size['width'] > 50 and img_elem.size['height'] > 50:
                        src = img_elem.get_attribute("src")
                        if not src:  # NUEVO: verificar data-src para lazy loading
                            src = img_elem.get_attribute("data-src")
                        
                        if (src and src.startswith("http") and 
                            "placeholder" not in src.lower() and 
                            "loading" not in src.lower() and
                            "spinner" not in src.lower() and
                            "thumb" not in src.lower() and  # NUEVO: evitar miniaturas
                            len(src) > 20):  # NUEVO: URLs muy cortas probablemente sean errores
                            img_actual = src
                            break
                if img_actual:
                    break
            except (StaleElementReferenceException, NoSuchElementException):
                continue
        
        # Verificar si es una imagen nueva - LÓGICA MEJORADA
        if img_actual:
            if img_actual not in imgs_unicas:
                imgs_unicas.add(img_actual)
                print(f"  📸 Imagen {len(imgs_unicas)}: ...{img_actual.split('/')[-1][:50]}")
                clicks_sin_cambio = 0
                intentos_sin_imagen = 0  # RESET contador
                imagen_anterior = img_actual
            elif img_actual == imagen_anterior:
                clicks_sin_cambio += 1
                if clicks_sin_cambio <= 3:  # Mostrar más información
                    print(f"  🔄 Misma imagen (sin cambio: {clicks_sin_cambio})")
            else:
                clicks_sin_cambio = 0
                intentos_sin_imagen = 0  # RESET contador
        else:
            clicks_sin_cambio += 1
            intentos_sin_imagen += 1  # NUEVO contador
            if intentos_sin_imagen <= 5:
                print(f"  ❌ No se detectó imagen (intento {clicks_realizados}, sin imagen: {intentos_sin_imagen})")
        
        # LÓGICA DE SALIDA MEJORADA
        if clicks_sin_cambio >= max_sin_cambio:
            print(f"  🛑 Finalizando: {clicks_sin_cambio} clicks sin nuevas imágenes")
            break
        
        # NUEVO: Si llevamos muchos intentos sin detectar imagen, intentar resetear
        if intentos_sin_imagen >= 5:
            print(f"  🔄 {intentos_sin_imagen} intentos sin imagen, reseteando slider...")
            resetear_slider_mejorado(driver)
            intentos_sin_imagen = 0
            time.sleep(random.uniform(3, 5))
        
        # Buscar y hacer click en botón siguiente con estrategias MÚLTIPLES
        btn_clickeado = False
        
        # Estrategia 1: Botones CSS - MÁS AGRESIVA
        for btn_selector in btn_selectors:
            try:
                next_btns = driver.find_elements(By.CSS_SELECTOR, btn_selector)
                for next_btn in next_btns:
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        # NUEVO: Verificar que no esté oculto por CSS
                        opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", next_btn)
                        visibility = driver.execute_script("return window.getComputedStyle(arguments[0]).visibility;", next_btn)
                        
                        if opacity != "0" and visibility != "hidden":
                            # Scroll al botón
                            driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                                next_btn
                            )
                            time.sleep(random.uniform(0.8, 1.5))
                            
                            # DOBLE INTENTO de click
                            try:
                                driver.execute_script("arguments[0].click();", next_btn)
                                btn_clickeado = True
                                break
                            except:
                                # Segundo intento con click normal
                                try:
                                    next_btn.click()
                                    btn_clickeado = True
                                    break
                                except:
                                    continue
                if btn_clickeado:
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        
        # Estrategia 2: Teclas MÚLTIPLES
        if not btn_clickeado:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                # Intentar varias teclas
                teclas = [Keys.ARROW_RIGHT, Keys.SPACE, Keys.PAGE_DOWN]
                for tecla in teclas:
                    body.send_keys(tecla)
                    time.sleep(0.5)
                btn_clickeado = True
            except:
                pass
        
        # Estrategia 3: JavaScript directo al slider
        if not btn_clickeado:
            try:
                # Intentar activar eventos del slider directamente
                driver.execute_script("""
                    var slider = document.getElementById('sliderRemax');
                    if (slider) {
                        var event = new Event('swipeleft');
                        slider.dispatchEvent(event);
                        
                        // Intentar otros eventos
                        var clickEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        
                        // Buscar botón next dentro del slider
                        var nextBtn = slider.querySelector('.sp-next-arrow, .next, .slider-next');
                        if (nextBtn) {
                            nextBtn.dispatchEvent(clickEvent);
                        }
                    }
                """)
                btn_clickeado = True
            except:
                pass
        
        if not btn_clickeado:
            print(f"  ⚠️ No se pudo avanzar en click {clicks_realizados}")
            # Si no puede avanzar varias veces seguidas, salir
            if clicks_sin_cambio >= 5:  # MÁS TOLERANTE
                break
        
        # Pausa entre clicks - MÁS VARIABLE
        pausa_click = random.uniform(3, 6)  # MÁS LENTA para dar tiempo
        time.sleep(pausa_click)
    
    resultado = list(imgs_unicas)
    print(f"  ✅ Extracción completada: {len(resultado)} imágenes únicas en {clicks_realizados} clicks")
    
    # NUEVO: Si obtuvimos muy pocas imágenes, intentar estrategia alternativa
    if len(resultado) < 8 and clicks_realizados < 50:
        print(f"  ⚠️ Solo {len(resultado)} imágenes encontradas, intentando estrategia alternativa...")
        try:
            # Intentar con scroll y espera adicional
            for _ in range(10):
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(2)
                driver.execute_script("window.scrollBy(0, -300);")
                time.sleep(2)
                
                # Buscar más imágenes después del scroll
                for selector in img_selectors[:3]:  # Solo los más importantes
                    try:
                        img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for img_elem in img_elements:
                            if img_elem.is_displayed():
                                src = img_elem.get_attribute("src")
                                if (src and src.startswith("http") and 
                                    src not in imgs_unicas and
                                    "placeholder" not in src.lower()):
                                    imgs_unicas.add(src)
                                    print(f"  📸 Imagen adicional {len(imgs_unicas)}: ...{src.split('/')[-1][:40]}")
                    except:
                        continue
        except:
            pass
        
        resultado = list(imgs_unicas)
        print(f"  🔍 Estrategia alternativa: {len(resultado)} imágenes totales")
    
    return resultado

def extraer_imagenes_con_reintentos(driver, url, max_intentos=3):
    """Extrae imágenes con sistema de reintentos mejorado"""
    for intento in range(1, max_intentos + 1):
        try:
            if intento > 1:
                print(f"  🔄 Reintento #{intento}/{max_intentos}")
                # Pausa progresiva más larga
                tiempo_espera = random.uniform(15, 25) * intento  # AUMENTADO
                print(f"  ⏱️ Esperando {tiempo_espera:.1f}s antes del reintento...")
                time.sleep(tiempo_espera)
                
                # Limpiar cache antes del reintento
                limpiar_cache(driver)
            
            resultado = extraer_imagenes(driver, url, intento)
            
            # Si obtuvo al menos 1 imagen, considerarlo éxito
            if resultado:
                print(f"  ✅ Intento {intento} exitoso: {len(resultado)} imágenes")
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
    
    # BORRAR imágenes existentes antes de guardar nuevas
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
    
    print(f"  ✅ {guardadas}/{len(urls)} imágenes guardadas exitosamente")
    return guardadas
def main():
    print("🚀 DESCARGA DE IMÁGENES - MODO INCREMENTAL v4.2 MEJORADO")
    print("="*70)
    print("🎯 CRITERIO: Solo propiedades con 10+ imágenes se consideran completas")
    print("🔧 MEJORAS: Extracción más agresiva, más reintentos, mejor detección")
    print("="*70)
    
    # Configurar mínimo de imágenes
    MINIMO_IMAGENES = 10
    
    # Conexión a base de datos
    conn = conectar_mysql()
    if not conn:
        return
    
    cur = conn.cursor()
    
    # Mostrar estadísticas actuales con el nuevo criterio
    mostrar_estadisticas_detalladas_mejoradas(cur, MINIMO_IMAGENES)
    
    # Cargar links
    try:
        with open("data/links.json", encoding="utf-8") as f:
            todos_los_links = json.load(f)
        print(f"📋 {len(todos_los_links)} links cargados desde archivo")
    except FileNotFoundError:
        print("❌ No se encontró data/links.json")
        return
    
    # Obtener propiedades ya procesadas (con 10+ imágenes)
    propiedades_procesadas = obtener_propiedades_procesadas(cur, MINIMO_IMAGENES)
    
    # Filtrar links pendientes
    links_pendientes, links_ya_procesados = filtrar_links_pendientes(
        todos_los_links, propiedades_procesadas
    )
    
    # Mostrar resumen de propiedades procesadas
    mostrar_resumen_procesadas_mejorado(cur, links_ya_procesados, MINIMO_IMAGENES)
    
    # Verificar si hay algo que procesar
    if not links_pendientes:
        print("🎉 ¡TODAS LAS PROPIEDADES YA TIENEN 10+ IMÁGENES!")
        print("   No hay nada nuevo que descargar.")
        conn.close()
        return
    
    # Mostrar qué se va a reprocesar
    print(f"\n🔄 PROPIEDADES QUE SERÁN REPROCESADAS:")
    print("=" * 50)
    
    propiedades_reprocessar = []
    for url in links_pendientes:
        id_interno = url.split("-")[-1].replace("/", "")
        try:
            cur.execute("""
                SELECT COUNT(*) 
                FROM imagenes_propiedad ip
                INNER JOIN propiedades p ON p.id = ip.propiedad_id
                WHERE p.id_interno = %s
            """, (id_interno,))
            
            num_imagenes_actual = cur.fetchone()[0]
            cur.fetchall()
            
            estado = "SIN IMÁGENES" if num_imagenes_actual == 0 else f"{num_imagenes_actual} imágenes"
            print(f"   ID {id_interno} → {estado} (NECESITA MÁS)")
            propiedades_reprocessar.append((id_interno, num_imagenes_actual))
            
        except:
            print(f"   ID {id_interno} → Error consultando")
    
    # Confirmación del usuario
    print(f"\n🤔 ¿Procesar/Reprocesar {len(links_pendientes)} propiedades con extracción mejorada? (s/n): ", end="")
    respuesta = input().lower().strip()
    
    if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Proceso cancelado por el usuario")
        conn.close()
        return
    
    # Crear directorio de imágenes
    os.makedirs(IMAGENES_DIR, exist_ok=True)
    
    # Configuración de procesamiento MEJORADA
    REINICIAR_CADA = 2  # REDUCIDO para reiniciar más frecuentemente
    total_imagenes = 0
    propiedades_exitosas = 0
    propiedades_fallidas = 0
    driver = None
    
    inicio_tiempo = time.time()
    
    print(f"\n🎯 INICIANDO PROCESAMIENTO MEJORADO DE {len(links_pendientes)} PROPIEDADES")
    print("="*80)
    
    for i, url in enumerate(links_pendientes, 1):
        tiempo_transcurrido = time.time() - inicio_tiempo
        
        print(f"\n{'='*90}")
        print(f"🏠 PROPIEDAD {i}/{len(links_pendientes)} | Total: {i + len(links_ya_procesados)}/{len(todos_los_links)}")
        print(f"⏱️ Tiempo: {tiempo_transcurrido/60:.1f} min | Exitosas: {propiedades_exitosas} | Fallidas: {propiedades_fallidas}")
        print(f"🔗 {url}")
        
        # Verificación doble por seguridad
        id_interno = url.split("-")[-1].replace("/", "")
        if verificar_imagenes_existentes(cur, id_interno, MINIMO_IMAGENES):
            print(f"⚠️ ADVERTENCIA: Propiedad {id_interno} ya tiene {MINIMO_IMAGENES}+ imágenes, saltando...")
            continue
        
        # Crear o reiniciar navegador MÁS FRECUENTEMENTE
        if driver is None or (i - 1) % REINICIAR_CADA == 0:
            if driver:
                print(f"🔄 Reiniciando navegador (cada {REINICIAR_CADA} propiedades para mejor rendimiento)")
                try:
                    driver.quit()
                except:
                    pass
                
                pausa_reinicio = random.uniform(30, 45)  # PAUSA MÁS LARGA
                print(f"⏱️ Pausa de reinicio: {pausa_reinicio:.1f}s")
                time.sleep(pausa_reinicio)
            
            print("🌐 Creando nuevo navegador con configuración stealth...")
            try:
                driver = crear_driver_ultra_stealth()
                print("✅ Navegador creado exitosamente")
            except Exception as e:
                print(f"❌ Error creando navegador: {e}")
                time.sleep(15)
                continue
        
        # Obtener ID de propiedad
        pid = propiedad_id(cur, id_interno)
        
        if not pid:
            print(f"❌ No existe propiedad en BD: {id_interno}")
            propiedades_fallidas += 1
            continue
        
        # Mostrar estado actual de la propiedad
        try:
            cur.execute("""
                SELECT COUNT(*) 
                FROM imagenes_propiedad ip
                INNER JOIN propiedades p ON p.id = ip.propiedad_id
                WHERE p.id_interno = %s
            """, (id_interno,))
            
            imagenes_actuales = cur.fetchone()[0]
            cur.fetchall()
            
            print(f"📊 Estado actual: {imagenes_actuales} imágenes → Objetivo: {MINIMO_IMAGENES}+ imágenes")
            
        except:
            print("📊 No se pudo consultar estado actual")
        
        try:
            # Verificar estado del navegador
            try:
                driver.current_url  # Test si el driver está vivo
            except:
                print("🔄 Driver no responde, creando uno nuevo...")
                driver = crear_driver_ultra_stealth()
            
            # Verificar si estamos bloqueados antes de proceder
            if verificar_si_bloqueado(driver):
                print("🚫 Bloqueo detectado, forzando reinicio...")
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                time.sleep(random.uniform(60, 90))  # PAUSA MUY LARGA
                continue
            
            # Intentar extraer imágenes con más reintentos
            print("🎯 Iniciando extracción MEJORADA...")
            imgs = extraer_imagenes_con_reintentos(driver, url, max_intentos=3)  # Mantener 3 intentos
            
            if imgs:
                print(f"💾 Guardando {len(imgs)} imágenes en base de datos...")
                guardadas = guardar(cur, pid, imgs)
                conn.commit()
                total_imagenes += guardadas
                propiedades_exitosas += 1
                
                # Mensaje de éxito detallado
                if guardadas >= MINIMO_IMAGENES:
                    print(f"🎉 ÉXITO COMPLETO: {guardadas} imágenes guardadas → ¡Objetivo de {MINIMO_IMAGENES}+ cumplido!")
                else:
                    print(f"⚠️ ÉXITO PARCIAL: {guardadas} imágenes guardadas → Aún necesita {MINIMO_IMAGENES - guardadas} más")
                
                print(f"📁 Ubicación: images/{pid}/")
                
                # Crear respaldo cada 3 propiedades exitosas (más frecuente)
                if propiedades_exitosas % 3 == 0:
                    crear_respaldo_progreso(propiedades_exitosas, propiedades_fallidas, total_imagenes)
                
            else:
                print("⚠️ Sin imágenes encontradas después de todos los intentos")
                propiedades_fallidas += 1
            
            # Limpiar cache más frecuentemente
            if i % 1 == 0:  # Cada propiedad
                limpiar_cache(driver)
                
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"❌ Error procesando propiedad: {error_msg}")
            propiedades_fallidas += 1
            
            # Reiniciar navegador en caso de error crítico
            if any(palabra in error_msg.lower() for palabra in 
                   ["timeout", "disconnected", "crashed", "blocked", "session", "chrome"]):
                print("🔄 Error crítico detectado, reiniciando navegador...")
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                time.sleep(random.uniform(45, 60))
        
        # Pausa entre propiedades MÁS LARGA
        if i < len(links_pendientes):
            pausa = random.uniform(20, 35)  # AUMENTADO
            print(f"⏱️ Pausa anti-detección: {pausa:.1f}s antes de siguiente propiedad...")
            time.sleep(pausa)
    
    # Limpieza final
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    # Crear respaldo final
    crear_respaldo_progreso(propiedades_exitosas, propiedades_fallidas, total_imagenes)
    
    # Estadísticas finales MEJORADAS
    tiempo_total = (time.time() - inicio_tiempo) / 60
    total_procesadas_ahora = propiedades_exitosas + propiedades_fallidas
    total_con_imagenes = len(links_ya_procesados) + propiedades_exitosas
    
    print(f"\n🎉 PROCESO COMPLETADO EN {tiempo_total:.1f} MINUTOS")
    print("="*80)
    print(f"📊 ESTADÍSTICAS DE ESTA SESIÓN:")
    print(f"   🔄 Propiedades procesadas ahora: {total_procesadas_ahora}")
    print(f"   ✅ Exitosas en esta sesión: {propiedades_exitosas}")
    print(f"   ❌ Fallidas en esta sesión: {propiedades_fallidas}")
    print(f"   📸 Imágenes descargadas ahora: {total_imagenes}")
    
    print(f"\n📊 ESTADÍSTICAS TOTALES:")
    print(f"   🏠 Total propiedades disponibles: {len(todos_los_links)}")
    print(f"   ✅ Total con {MINIMO_IMAGENES}+ imágenes: {total_con_imagenes}")
    print(f"   ❌ Aún pendientes: {len(todos_los_links) - total_con_imagenes}")
    print(f"   📈 Progreso total: {(total_con_imagenes/len(todos_los_links)*100):.1f}%")
    
    if total_imagenes > 0 and propiedades_exitosas > 0:
        print(f"   📊 Promedio imágenes/propiedad exitosa: {total_imagenes/propiedades_exitosas:.1f}")
    
    # Mostrar estadísticas finales de BD
    print(f"\n📊 VERIFICACIÓN FINAL:")
    mostrar_estadisticas_detalladas_mejoradas(cur, MINIMO_IMAGENES)
    
    try:
        conn.close()
    except:
        pass

if __name__ == "__main__":
    main()