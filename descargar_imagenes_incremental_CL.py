# descargar_imagenes_incremental_CL.py - CÓDIGO COMPLETO v5.0 ULTRA MEJORADO
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
    """Simula comportamiento humano más realista - MEJORADO"""
    try:
        print("  👤 Simulando comportamiento humano avanzado...")
        
        # Scroll aleatorio más natural
        scrolls = random.randint(3, 6)  # AUMENTADO
        for _ in range(scrolls):
            scroll_amount = random.randint(200, 600)  # AUMENTADO
            direction = random.choice([1, -1])  # Arriba o abajo
            driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction});")
            time.sleep(random.uniform(1.2, 2.5))  # PAUSAS MÁS LARGAS
        
        # Simular movimiento de mouse más realista
        driver.execute_script("""
            const moves = 5 + Math.floor(Math.random() * 5);
            for(let i = 0; i < moves; i++) {
                setTimeout(() => {
                    const event = new MouseEvent('mousemove', {
                        clientX: Math.random() * window.innerWidth,
                        clientY: Math.random() * window.innerHeight,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                }, i * 300);
            }
        """)
        
        # Pausa aleatoria MÁS LARGA
        time.sleep(random.uniform(2, 4))  # AUMENTADO
        
        # NUEVO: Simular hover en elementos aleatorios
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, "a, button, img")[:15]
            if elementos:
                elemento_hover = random.choice(elementos)
                if elemento_hover.is_displayed():
                    driver.execute_script("""
                        arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
                        setTimeout(() => {
                            arguments[0].dispatchEvent(new MouseEvent('mouseout', {bubbles: true}));
                        }, 1000);
                    """, elemento_hover)
                    time.sleep(random.uniform(1, 2))
        except:
            pass
        
        # Ocasionalmente simular click en área vacía
        if random.random() < 0.4:  # AUMENTADO probabilidad
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                driver.execute_script("arguments[0].click();", body)
                time.sleep(random.uniform(0.8, 1.5))
            except:
                pass
                
    except Exception as e:
        print(f"  ⚠️ Error simulando humano: {e}")

def simular_actividad_humana_real(driver):
    """Simula actividad humana muy realista - MEJORADO"""
    try:
        print("  👤 Simulando actividad humana extendida...")
        
        # 1. Hacer búsquedas aleatorias MÁS REALISTAS
        try:
            search_selectors = ["input[type='search']", "input[placeholder*='buscar']", ".search-input", "#search"]
            
            for selector in search_selectors:
                try:
                    search_box = driver.find_element(By.CSS_SELECTOR, selector)
                    if search_box.is_displayed():
                        search_box.click()
                        time.sleep(random.uniform(2, 4))  # PAUSA MÁS LARGA
                        
                        # Escribir búsqueda falsa más lenta
                        fake_searches = ["casa lima", "departamento", "terreno", "oficina", "local comercial"]
                        fake_search = random.choice(fake_searches)
                        
                        for char in fake_search:
                            search_box.send_keys(char)
                            time.sleep(random.uniform(0.2, 0.5))  # MÁS LENTO
                        
                        time.sleep(random.uniform(3, 6))  # PAUSA MÁS LARGA
                        search_box.clear()
                        break
                except:
                    continue
        except:
            pass
        
        # 2. Scroll aleatorio por la página MÁS EXTENSO
        for _ in range(random.randint(5, 10)):  # AUMENTADO
            scroll_amount = random.randint(300, 1000)  # AUMENTADO
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(2, 4))  # PAUSAS MÁS LARGAS
        
        # 3. NUEVO: Simular lectura de elementos
        try:
            textos = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, p")[:8]
            for texto in textos:
                if texto.is_displayed():
                    # Simular scroll al elemento para "leerlo"
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", texto)
                    time.sleep(random.uniform(2, 4))  # Simular tiempo de lectura
        except:
            pass
        
        # 4. Hover en enlaces aleatorios MÁS TIEMPO
        try:
            links = driver.find_elements(By.TAG_NAME, "a")[:15]  # MÁS LINKS
            if links:
                for _ in range(random.randint(2, 4)):  # MÚLTIPLES HOVERS
                    random_link = random.choice(links)
                    if random_link.is_displayed():
                        # Hover MÁS TIEMPO
                        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover'));", random_link)
                        time.sleep(random.uniform(1.5, 3))  # HOVER MÁS LARGO
                        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseout'));", random_link)
        except:
            pass
        
        print("  ✅ Actividad humana extendida completada")
        
    except Exception as e:
        print(f"  ⚠️ Error simulando actividad: {e}")

def resetear_slider_ultra_mejorado(driver):
    """Resetea el slider con estrategias ULTRA MEJORADAS - MÁS AGRESIVO"""
    try:
        print("  🔄 Reseteando slider con estrategias ultra mejoradas...")
        
        # Estrategia 1: BOTONES DE NAVEGACIÓN - SÚPER AGRESIVO
        reset_selectors = [
            ".sp-previous-arrow",
            ".sp-first-arrow", 
            ".slider-prev",
            ".prev",
            "button[class*='prev']",
            "[data-action='prev']",
            ".slick-prev",
            ".owl-prev",
            "button[aria-label*='previous' i]",  # NUEVO
            "button[title*='anterior' i]",       # NUEVO
            ".carousel-control-prev",            # NUEVO
            ".gallery-nav-prev"                  # NUEVO
        ]
        
        # HACER MUCHÍSIMOS MÁS CLICKS hacia atrás
        clicks_realizados = 0
        for intento in range(25):  # AUMENTADO SIGNIFICATIVAMENTE
            btn_encontrado = False
            for selector in reset_selectors:
                try:
                    prev_btns = driver.find_elements(By.CSS_SELECTOR, selector)
                    for prev_btn in prev_btns:
                        if prev_btn.is_displayed() and prev_btn.is_enabled():
                            # Verificar que no esté oculto
                            opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", prev_btn)
                            visibility = driver.execute_script("return window.getComputedStyle(arguments[0]).visibility;", prev_btn)
                            
                            if opacity != "0" and visibility != "hidden":
                                # TRIPLE INTENTO de click
                                try:
                                    driver.execute_script("arguments[0].click();", prev_btn)
                                    clicks_realizados += 1
                                    btn_encontrado = True
                                    time.sleep(random.uniform(0.8, 1.5))  # PAUSA MÁS LARGA
                                    break
                                except:
                                    try:
                                        prev_btn.click()
                                        clicks_realizados += 1
                                        btn_encontrado = True
                                        break
                                    except:
                                        continue
                    if btn_encontrado:
                        break
                except:
                    continue
            if not btn_encontrado:
                break
        
        print(f"    ✓ {clicks_realizados} clicks de retroceso realizados")
        
        # Estrategia 2: TECLAS DE FLECHA - MÁS INTENSIVA
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            slider = driver.find_element(By.ID, "sliderRemax")
            
            # Enfocar el slider y enviar teclas
            driver.execute_script("arguments[0].focus();", slider)
            time.sleep(1)
            
            for _ in range(15):  # AUMENTADO
                body.send_keys(Keys.HOME)  # Ir al inicio
                time.sleep(0.3)
                slider.send_keys(Keys.ARROW_LEFT)
                time.sleep(0.3)
                body.send_keys(Keys.ARROW_LEFT)
                time.sleep(0.3)
        except:
            pass
        
        # Estrategia 3: PRIMERA MINIATURA - MÁS OPCIONES
        try:
            miniaturas_selectors = [
                ".sp-thumbnail:first-child", 
                ".thumbnail:first-child", 
                ".thumb:first-child",
                ".slick-dots li:first-child",
                ".owl-dot:first-child",
                ".carousel-indicators li:first-child",  # NUEVO
                ".gallery-thumbs img:first-child",      # NUEVO
                "[data-slide-to='0']"                   # NUEVO
            ]
            
            for selector in miniaturas_selectors:
                try:
                    primera_miniatura = driver.find_element(By.CSS_SELECTOR, selector)
                    if primera_miniatura.is_displayed():
                        driver.execute_script("arguments[0].click();", primera_miniatura)
                        time.sleep(2)
                        print("    ✓ Click en primera miniatura realizado")
                        break
                except:
                    continue
        except:
            pass
        
        # Estrategia 4: JAVASCRIPT DIRECTO AL SLIDER - MÁS MÉTODOS
        try:
            driver.execute_script("""
                console.log('Intentando resetear slider...');
                
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
                    
                    // Intentar con owl carousel
                    if (jQuery && jQuery(slider).data('owl.carousel')) {
                        jQuery(slider).trigger('to.owl.carousel', [0, 500]);
                    }
                    
                    // Disparar evento personalizado de primera imagen
                    var firstEvent = new CustomEvent('showFirst', {bubbles: true});
                    slider.dispatchEvent(firstEvent);
                    
                    console.log('Reseteo de slider completado');
                }
                
                // Intentar con selectores adicionales
                var sliders = document.querySelectorAll('.slider, .gallery, .carousel');
                sliders.forEach(function(s) {
                    if (s.scrollLeft) s.scrollLeft = 0;
                    if (s.scrollTop) s.scrollTop = 0;
                });
            """)
            print("    ✓ JavaScript de reseteo ejecutado")
        except Exception as e:
            print(f"    ⚠️ Error en JavaScript: {e}")
        
        # Estrategia 5: NUEVA - SCROLL DEL CONTENEDOR
        try:
            contenedores = [
                ".sp-slides-container",
                ".slider-container", 
                ".gallery-container",
                ".carousel-inner"
            ]
            
            for selector in contenedores:
                try:
                    contenedor = driver.find_element(By.CSS_SELECTOR, selector)
                    driver.execute_script("arguments[0].scrollLeft = 0;", contenedor)
                    time.sleep(0.5)
                except:
                    continue
        except:
            pass
            
        print("  ✅ Slider ultra-reseteado con múltiples estrategias")
        time.sleep(random.uniform(4, 7))  # PAUSA EXTRA LARGA
        
    except Exception as e:
        print(f"  ⚠️ Error reseteando slider: {e}")

def detectar_imagen_valida_mejorada(img_elem):
    """Detecta si una imagen es válida con verificaciones MEJORADAS"""
    try:
        # Verificar que el elemento esté visible
        if not img_elem.is_displayed():
            return False, None
        
        # Verificar tamaño mínimo MÁS ESTRICTO
        size = img_elem.size
        if size['width'] < 100 or size['height'] < 100:  # AUMENTADO de 50
            return False, None
        
        # Obtener src con múltiples métodos
        src = img_elem.get_attribute("src")
        if not src:
            src = img_elem.get_attribute("data-src")  # Lazy loading
        if not src:
            src = img_elem.get_attribute("data-original")  # Otro tipo de lazy loading
        
        if not src or not src.startswith("http"):
            return False, None
        
        # Verificar que no sea una imagen de placeholder o inválida
        src_lower = src.lower()
        palabras_invalidas = [
            "placeholder", "loading", "spinner", "blank", "empty",
            "thumb", "thumbnail", "icon", "logo", "button", "arrow",
            "pixel", "spacer", "1x1", "transparent", "default",
            "no-image", "noimage", "404", "error"
        ]
        
        for palabra in palabras_invalidas:
            if palabra in src_lower:
                return False, None
        
        # Verificar longitud mínima de URL
        if len(src) < 30:  # URLs muy cortas probablemente sean inválidas
            return False, None
        
        # NUEVO: Verificar que la imagen tenga contenido real
        try:
            # Verificar atributos que indiquen imagen real
            alt = img_elem.get_attribute("alt") or ""
            title = img_elem.get_attribute("title") or ""
            
            # Si tiene alt o title descriptivo, es más probable que sea válida
            if any(palabra in (alt + title).lower() for palabra in ["propiedad", "casa", "departamento", "inmueble"]):
                return True, src
        except:
            pass
        
        return True, src
        
    except Exception as e:
        return False, None

def extraer_imagenes_ultra_mejorado(driver, url, intento=1):
    """Extrae imágenes con estrategias ULTRA MEJORADAS para obtener MUCHAS MÁS imágenes"""
    
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
    
    # Pausa inicial EXTRA LARGA
    pausa_inicial = random.uniform(18, 30)  # AUMENTADO SIGNIFICATIVAMENTE
    print(f"⏱️ Esperando carga inicial extendida: {pausa_inicial:.1f}s")
    time.sleep(pausa_inicial)
    
    # Verificar bloqueo después de cargar
    if verificar_si_bloqueado(driver):
        print("🚫 Página bloqueada detectada")
        raise Exception("Página bloqueada")
# Simular comportamiento humano EXTENDIDO
    simular_humano_avanzado(driver)
    
    # NUEVO: Simular interacción con otros elementos de la página
    try:
        print("  🎭 Simulando interacción adicional con la página...")
        # Buscar y hacer hover en algunos elementos
        elementos_interactivos = driver.find_elements(By.CSS_SELECTOR, "button, a, .tab, .menu-item")[:5]
        for elem in elementos_interactivos:
            if elem.is_displayed():
                driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover'));", elem)
                time.sleep(random.uniform(0.5, 1.5))
                driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseout'));", elem)
    except:
        pass
    
    # Verificar que existe el slider con timeout MAYOR
    try:
        slider_element = WebDriverWait(driver, 35).until(  # AUMENTADO timeout
            EC.presence_of_element_located((By.ID, "sliderRemax"))
        )
        print("  ✅ Slider detectado")
    except TimeoutException:
        print("  ❌ No se encontró slider principal")
        # Intentar con otros selectores más tiempo
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".slider, .gallery, .images, .carousel"))
            )
            print("  ✅ Galería alternativa detectada")
        except:
            print("  ❌ No se encontró ninguna galería")
            return []
    
    # PAUSA ADICIONAL EXTRA LARGA después de detectar slider
    print("  ⏱️ Pausa extendida para carga completa del slider...")
    time.sleep(random.uniform(8, 15))  # AUMENTADO SIGNIFICATIVAMENTE
    
    # NUEVO: Scroll al slider para asegurar que esté en vista
    try:
        slider = driver.find_element(By.ID, "sliderRemax")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
        time.sleep(3)
        print("  ✅ Slider centrado en pantalla")
    except:
        pass
    
    # Resetear slider al inicio ULTRA AGRESIVO
    resetear_slider_ultra_mejorado(driver)
    
    # NUEVA PAUSA después del reseteo
    print("  ⏱️ Pausa post-reseteo...")
    time.sleep(random.uniform(5, 10))
    
    imgs_unicas = set()
    imagen_anterior = None
    clicks_realizados = 0
    max_clicks = 150  # AUMENTADO MUCHÍSIMO MÁS
    clicks_sin_cambio = 0
    max_sin_cambio = 15  # AUMENTADO para ser MÁS persistente
    intentos_sin_imagen = 0
    max_intentos_sin_imagen = 12  # AUMENTADO
    ciclos_completos = 0  # NUEVO: contador de ciclos completos
    max_ciclos = 3  # NUEVO: máximo de ciclos completos permitidos
    
    # Selectores mejorados para imágenes - MÁS COMPLETOS
    img_selectors = [
        "img[src*='digitaloceanspaces.com']",  # Mantener como prioridad
        "#sliderRemax img[src*='http']",
        ".sp-slide img[src*='http']",
        ".sp-slides-container img[src*='http']",
        ".sp-image img[src*='http']",           # NUEVO
        "img[src*='remax']",
        "img[src*='cdn']",
        "img[src*='amazonaws']",                # NUEVO
        ".slider img[src*='http']",
        ".gallery img[src*='http']",
        ".carousel img[src*='http']",           # NUEVO
        "img[data-src*='http']",               # Lazy loading
        "img[srcset*='http']",                 # Responsive images
        "img[data-original*='http']",          # NUEVO: otro tipo de lazy loading
        "picture img[src*='http']",            # NUEVO: elementos picture
        ".image-container img[src*='http']"    # NUEVO: contenedores de imagen
    ]
    
    # Selectores mejorados para botones - MÁS COMPLETOS
    btn_selectors = [
        ".sp-next-arrow",
        ".sp-arrow.sp-next-arrow", 
        ".slider-next", 
        ".next",
        "button[class*='next']",
        "[data-action='next']",
        ".gallery-next",
        ".arrow-right",
        "button[aria-label*='next' i]",
        "button[title*='siguiente' i]",
        ".slick-next",
        ".owl-next",
        ".carousel-control-next",              # NUEVO
        ".swiper-button-next",                 # NUEVO
        ".gallery-nav-next",                   # NUEVO
        "button[data-slide='next']",           # NUEVO
        ".right-arrow",                        # NUEVO
        ".nav-right"                           # NUEVO
    ]
    
    print(f"🎯 Iniciando extracción ULTRA MEJORADA de imágenes (máximo {max_clicks} clicks)...")
    
    for click_num in range(max_clicks):
        clicks_realizados += 1
        
        # Progreso cada 25 clicks
        if click_num > 0 and click_num % 25 == 0:
            print(f"  📊 Progreso: {click_num}/{max_clicks} clicks - {len(imgs_unicas)} imágenes encontradas")
        
        # Cada cierto número de clicks, simular comportamiento más humano
        if click_num % 12 == 0 and click_num > 0:  # REDUCIDO frecuencia
            simular_humano_avanzado(driver)
        
        # NUEVO: Scroll ocasional MÁS FRECUENTE para asegurar que el slider esté visible
        if click_num % 20 == 0:
            try:
                slider = driver.find_element(By.ID, "sliderRemax")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
                time.sleep(1.5)
            except:
                pass
        
        # NUEVO: Verificar si hemos completado un ciclo
        if click_num > 0 and clicks_sin_cambio > 20:  # Si llevamos muchos clicks sin cambio
            ciclos_completos += 1
            print(f"  🔄 Posible ciclo completo detectado #{ciclos_completos}")
            
            if ciclos_completos >= max_ciclos:
                print(f"  🛑 {max_ciclos} ciclos completos detectados, finalizando")
                break
            
            # Resetear contador y intentar con estrategia diferente
            clicks_sin_cambio = 0
            resetear_slider_ultra_mejorado(driver)
            time.sleep(random.uniform(3, 6))
        
        # Buscar imagen actual con verificación ULTRA MEJORADA
        img_actual = None
        for selector in img_selectors:
            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for img_elem in img_elements:
                    es_valida, src = detectar_imagen_valida_mejorada(img_elem)
                    if es_valida and src:
                        img_actual = src
                        break
                if img_actual:
                    break
            except (StaleElementReferenceException, NoSuchElementException):
                continue
        
        # Verificar si es una imagen nueva - LÓGICA ULTRA MEJORADA
        if img_actual:
            if img_actual not in imgs_unicas:
                imgs_unicas.add(img_actual)
                print(f"  📸 Imagen {len(imgs_unicas)}: ...{img_actual.split('/')[-1][:60]}")
                clicks_sin_cambio = 0
                intentos_sin_imagen = 0  # RESET contador
                imagen_anterior = img_actual
                ciclos_completos = 0  # RESET ciclos al encontrar nueva imagen
            elif img_actual == imagen_anterior:
                clicks_sin_cambio += 1
                if clicks_sin_cambio <= 5:  # Mostrar información inicial
                    print(f"  🔄 Misma imagen (sin cambio: {clicks_sin_cambio})")
            else:
                clicks_sin_cambio = 0
                intentos_sin_imagen = 0  # RESET contador
        else:
            clicks_sin_cambio += 1
            intentos_sin_imagen += 1
            if intentos_sin_imagen <= 8:
                print(f"  ❌ No se detectó imagen (intento {clicks_realizados}, sin imagen: {intentos_sin_imagen})")
        
        # LÓGICA DE SALIDA MEJORADA
        if clicks_sin_cambio >= max_sin_cambio:
            print(f"  🛑 Finalizando: {clicks_sin_cambio} clicks sin nuevas imágenes")
            break
        
        # MEJORADO: Si llevamos muchos intentos sin detectar imagen, estrategias de recuperación
        if intentos_sin_imagen >= 8:
            print(f"  🔄 {intentos_sin_imagen} intentos sin imagen, aplicando estrategias de recuperación...")
            
            # Estrategia 1: Resetear slider completamente
            resetear_slider_ultra_mejorado(driver)
            
            # Estrategia 2: Refresh de la página si es muy persistente
            if intentos_sin_imagen >= 15:
                print("  🔄 Refrescando página por problemas persistentes...")
                driver.refresh()
                time.sleep(random.uniform(10, 20))
                
                # Re-detectar slider después del refresh
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "sliderRemax"))
                    )
                    resetear_slider_ultra_mejorado(driver)
                except:
                    print("  ❌ No se pudo recuperar slider después del refresh")
                    break
            
            intentos_sin_imagen = 0
            time.sleep(random.uniform(4, 8))
        
        # Buscar y hacer click en botón siguiente con estrategias MÚLTIPLES MEJORADAS
        btn_clickeado = False
        
        # Estrategia 1: Botones CSS - SÚPER AGRESIVA
        for btn_selector in btn_selectors:
            try:
                next_btns = driver.find_elements(By.CSS_SELECTOR, btn_selector)
                for next_btn in next_btns:
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        # Verificaciones MÁS ESTRICTAS de visibilidad
                        opacity = driver.execute_script("return window.getComputedStyle(arguments[0]).opacity;", next_btn)
                        visibility = driver.execute_script("return window.getComputedStyle(arguments[0]).visibility;", next_btn)
                        display = driver.execute_script("return window.getComputedStyle(arguments[0]).display;", next_btn)
                        
                        if opacity != "0" and visibility != "hidden" and display != "none":
                            # Scroll al botón y esperar
                            driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                                next_btn
                            )
                            time.sleep(random.uniform(1, 2))
                            
                            # TRIPLE INTENTO de click MEJORADO
                            try:
                                # Método 1: JavaScript click
                                driver.execute_script("arguments[0].click();", next_btn)
                                btn_clickeado = True
                                break
                            except:
                                try:
                                    # Método 2: Click normal de Selenium
                                    next_btn.click()
                                    btn_clickeado = True
                                    break
                                except:
                                    try:
                                        # Método 3: Enviar evento de click personalizado
                                        driver.execute_script("""
                                            var event = new MouseEvent('click', {
                                                view: window,
                                                bubbles: true,
                                                cancelable: true
                                            });
                                            arguments[0].dispatchEvent(event);
                                        """, next_btn)
                                        btn_clickeado = True
                                        break
                                    except:
                                        continue
                if btn_clickeado:
                    break
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        
        # Estrategia 2: Teclas MÚLTIPLES MEJORADA
        if not btn_clickeado:
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                slider = driver.find_element(By.ID, "sliderRemax")
                
                # Enfocar elementos y probar múltiples teclas
                elementos_foco = [slider, body]
                teclas = [Keys.ARROW_RIGHT, Keys.SPACE, Keys.PAGE_DOWN]
                
                for elemento in elementos_foco:
                    driver.execute_script("arguments[0].focus();", elemento)
                    for tecla in teclas:
                        elemento.send_keys(tecla)
                        time.sleep(0.5)
                
                btn_clickeado = True
            except:
                pass
        
        # Estrategia 3: JavaScript directo al slider MEJORADO
        if not btn_clickeado:
            try:
                driver.execute_script("""
                    console.log('Intentando avanzar slider con JavaScript...');
                    
                    var slider = document.getElementById('sliderRemax');
                    if (slider) {
                        // Método 1: Eventos de swipe
                        var events = ['swipeleft', 'swiperight', 'next', 'forward'];
                        events.forEach(function(eventType) {
                            var event = new Event(eventType);
                            slider.dispatchEvent(event);
                        });
                        
                        // Método 2: APIs de sliders conocidos
                        if (slider.slick) {
                            slider.slick('slickNext');
                        }
                        if (slider.swiper) {
                            slider.swiper.slideNext();
                        }
                        if (window.jQuery && window.jQuery(slider).data('owl.carousel')) {
                            window.jQuery(slider).trigger('next.owl.carousel');
                        }
                        
                        // Método 3: Buscar y clickear botón next dentro del slider
                        var nextSelectors = ['.sp-next-arrow', '.next', '.slider-next', '.arrow-right'];
                        nextSelectors.forEach(function(sel) {
                            var nextBtn = slider.querySelector(sel);
                            if (nextBtn) {
                                nextBtn.click();
                            }
                        });
                        
                        // Método 4: Simular teclado
                        var keyEvent = new KeyboardEvent('keydown', {key: 'ArrowRight', keyCode: 39});
                        slider.dispatchEvent(keyEvent);
                        
                        console.log('JavaScript de avance completado');
                    }
                """)
                btn_clickeado = True
            except Exception as e:
                print(f"    ⚠️ Error en JavaScript de avance: {str(e)[:50]}")
        
        # Estrategia 4: NUEVA - Manipulación directa del DOM
        if not btn_clickeado:
            try:
                driver.execute_script("""
                    // Intentar manipular índices directamente
                    var slider = document.getElementById('sliderRemax');
                    if (slider) {
                        // Buscar elementos de slides
                        var slides = slider.querySelectorAll('.sp-slide, .slide, .carousel-item');
                        if (slides.length > 0) {
                            // Intentar hacer visible el siguiente slide
                            var activeIndex = -1;
                            slides.forEach(function(slide, index) {
                                if (slide.classList.contains('active') || slide.classList.contains('sp-selected')) {
                                    activeIndex = index;
                                }
                            });
                            
                            var nextIndex = (activeIndex + 1) % slides.length;
                            if (slides[nextIndex]) {
                                slides[nextIndex].scrollIntoView();
                                slides[nextIndex].click();
                            }
                        }
                    }
                """)
                btn_clickeado = True
            except:
                pass
        
        if not btn_clickeado:
            print(f"  ⚠️ No se pudo avanzar en click {clicks_realizados}")
            # Si no puede avanzar varias veces seguidas, aumentar contador
            if clicks_sin_cambio >= 8:  # MÁS TOLERANTE aún
                print(f"  ⚠️ Demasiados intentos fallidos de avance")
        
        # Pausa entre clicks - MÁS VARIABLE Y LARGA
        pausa_click = random.uniform(4, 8)  # AUMENTADO para dar más tiempo
        time.sleep(pausa_click)
    
    resultado = list(imgs_unicas)
    print(f"  ✅ Extracción ULTRA completada: {len(resultado)} imágenes únicas en {clicks_realizados} clicks")
    
    # ESTRATEGIA ALTERNATIVA MEJORADA: Si obtuvimos pocas imágenes
    if len(resultado) < 12 and clicks_realizados < 100:  # AUMENTADO umbral
        print(f"  ⚠️ Solo {len(resultado)} imágenes encontradas, ejecutando estrategia alternativa COMPLETA...")
        
        try:
            # Método 1: Scroll extensivo con búsqueda
            print("    🌀 Método 1: Scroll extensivo...")
            for scroll_round in range(15):  # AUMENTADO
                # Scroll down
                for _ in range(3):
                    driver.execute_script("window.scrollBy(0, 400);")
                    time.sleep(2)
                
                # Scroll up
                for _ in range(3):
                    driver.execute_script("window.scrollBy(0, -400);")
                    time.sleep(2)
                
                # Buscar imágenes después de cada ronda de scroll
                for selector in img_selectors[:5]:  # Los más importantes
                    try:
                        img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for img_elem in img_elements:
                            es_valida, src = detectar_imagen_valida_mejorada(img_elem)
                            if es_valida and src and src not in imgs_unicas:
                                imgs_unicas.add(src)
                                print(f"    📸 Imagen adicional por scroll {len(imgs_unicas)}: ...{src.split('/')[-1][:50]}")
                    except:
                        continue
            
            # Método 2: Intentar con diferentes resoluciones de ventana
            print("    📏 Método 2: Cambio de resolución...")
            resoluciones = [(1920, 1080), (1366, 768), (1280, 720)]
            for width, height in resoluciones:
                try:
                    driver.set_window_size(width, height)
                    time.sleep(3)
                    
                    # Resetear slider y buscar más imágenes
                    resetear_slider_ultra_mejorado(driver)
                    
                    # Hacer algunos clicks adicionales
                    for _ in range(10):
                        for btn_selector in btn_selectors[:3]:
                            try:
                                next_btn = driver.find_element(By.CSS_SELECTOR, btn_selector)
                                if next_btn.is_displayed():
                                    driver.execute_script("arguments[0].click();", next_btn)
                                    time.sleep(2)
                                    
                                    # Buscar nueva imagen
                                    for selector in img_selectors[:3]:
                                        try:
                                            img_elem = driver.find_element(By.CSS_SELECTOR, selector)
                                            es_valida, src = detectar_imagen_valida_mejorada(img_elem)
                                            if es_valida and src and src not in imgs_unicas:
                                                imgs_unicas.add(src)
                                                print(f"    📸 Imagen por resolución {len(imgs_unicas)}: ...{src.split('/')[-1][:50]}")
                                        except:
                                            continue
                                    break
                            except:
                                continue
                except:
                    continue
            
            # Restaurar resolución original
            try:
                driver.maximize_window()
            except:
                pass
            
            # Método 3: NUEVO - Intentar activar lazy loading
            print("    🔄 Método 3: Activación de lazy loading...")
            try:
                driver.execute_script("""
                    // Disparar eventos que podrían activar lazy loading
                    window.dispatchEvent(new Event('scroll'));
                    window.dispatchEvent(new Event('resize'));
                    window.dispatchEvent(new Event('load'));
                    
                    // Buscar imágenes con data-src y cargarlas
                    var lazyImages = document.querySelectorAll('img[data-src], img[data-original]');
                    lazyImages.forEach(function(img) {
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                        }
                        if (img.dataset.original) {
                            img.src = img.dataset.original;
                        }
                    });
                """)
                
                time.sleep(5)  # Esperar a que se carguen las imágenes lazy
                
                # Buscar las nuevas imágenes cargadas
                for selector in img_selectors:
                    try:
                        img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for img_elem in img_elements:
                            es_valida, src = detectar_imagen_valida_mejorada(img_elem)
                            if es_valida and src and src not in imgs_unicas:
                                imgs_unicas.add(src)
                                print(f"    📸 Imagen lazy {len(imgs_unicas)}: ...{src.split('/')[-1][:50]}")
                    except:
                        continue
            except:
                pass
            
        except Exception as e:
            print(f"    ⚠️ Error en estrategia alternativa: {str(e)[:50]}")
        
        resultado = list(imgs_unicas)
        print(f"  🔍 Estrategia alternativa COMPLETA: {len(resultado)} imágenes totales")
    
    return resultado

def extraer_imagenes_con_reintentos_mejorado(driver, url, max_intentos=4):  # AUMENTADO intentos
    """Extrae imágenes con sistema de reintentos ULTRA mejorado"""
    mejor_resultado = []
    
    for intento in range(1, max_intentos + 1):
        try:
            if intento > 1:
                print(f"  🔄 Reintento MEJORADO #{intento}/{max_intentos}")
                # Pausa progresiva MÁS LARGA
                tiempo_espera = random.uniform(25, 40) * intento  # AUMENTADO SIGNIFICATIVAMENTE
                print(f"  ⏱️ Esperando {tiempo_espera:.1f}s antes del reintento...")
                time.sleep(tiempo_espera)
                
                # Limpiar cache y resetear estado
                limpiar_cache(driver)
                
                # NUEVO: Cambiar user agent ocasionalmente
                if intento == 3:
                    print("  🎭 Cambiando user agent...")
                    user_agents = [
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                    ]
                    new_ua = random.choice(user_agents)
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": new_ua})
            
            resultado = extraer_imagenes_ultra_mejorado(driver, url, intento)
            
            # Guardar el mejor resultado hasta ahora
            if len(resultado) > len(mejor_resultado):
                mejor_resultado = resultado
            
            # Si obtuvo un buen número de imágenes, considerarlo éxito
            if len(resultado) >= 8:  # REDUCIDO umbral para ser menos exigente
                print(f"  ✅ Intento {intento} EXITOSO: {len(resultado)} imágenes")
                return resultado
            elif len(resultado) > 0:
                print(f"  ⚠️ Intento {intento} parcial: {len(resultado)} imágenes (continuando...)")
            elif intento == max_intentos:
                print(f"  💥 Sin imágenes después de {max_intentos} intentos")
                return mejor_resultado  # Devolver el mejor resultado obtenido
                
        except Exception as e:
            print(f"  ❌ Error en intento {intento}: {str(e)[:100]}")
            if intento == max_intentos:
                print(f"  💥 Falló después de {max_intentos} intentos")
                return mejor_resultado  # Devolver el mejor resultado obtenido
    
    return mejor_resultado

def simular_navegacion_humana(driver, url_objetivo):
    """Simula navegación humana antes de ir al objetivo - MEJORADO"""
    print("  👤 Simulando navegación humana extendida...")
    
    try:
        # 1. Ir a la página principal
        driver.get("https://www.remax.pe/")
        time.sleep(random.uniform(8, 15))  # AUMENTADO
        
        # 2. Simular actividad extendida
        simular_actividad_humana_real(driver)
        
        # 3. NUEVO: Navegar por algunas secciones del sitio
        try:
            # Buscar enlaces de navegación
            nav_links = driver.find_elements(By.CSS_SELECTOR, "nav a, .menu a, header a")[:5]
            if nav_links:
                link_aleatorio = random.choice(nav_links)
                if link_aleatorio.is_displayed():
                    print("  🔗 Navegando por el sitio...")
                    driver.execute_script("arguments[0].click();", link_aleatorio)
                    time.sleep(random.uniform(5, 10))
                    
                    # Simular lectura
                    simular_humano_avanzado(driver)
        except:
            pass
        
        # 4. Pausa EXTRA larga antes del objetivo
        pausa_pre_objetivo = random.uniform(20, 35)  # AUMENTADO MUCHÍSIMO
        print(f"  ⏱️ Pausa extendida antes del objetivo: {pausa_pre_objetivo:.1f}s")
        time.sleep(pausa_pre_objetivo)
        
        # 5. Finalmente ir al objetivo
        print("  🎯 Navegando al objetivo final...")
        driver.get(url_objetivo)
        
    except Exception as e:
        print(f"  ⚠️ Error en navegación humana: {e}")
        # Si falla, ir directo al objetivo
        driver.get(url_objetivo)

def crear_driver_ultra_stealth():
    """Crea driver con configuración stealth ULTRA extrema"""
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    
    opts = uc.ChromeOptions()
    
    # Configuración básica MEJORADA
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    
    # Configuración stealth ULTRA extrema
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--ignore-ssl-errors")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_argument("--disable-ipc-flooding-protection")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-field-trial-config")
    opts.add_argument("--disable-back-forward-cache")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-breakpad")
    opts.add_argument("--disable-client-side-phishing-detection")
    opts.add_argument("--disable-component-update")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-domain-reliability")
    opts.add_argument("--disable-features=TranslateUI")
    
    # User agent aleatorio
    selected_ua = random.choice(user_agents)
    opts.add_argument(f"--user-agent={selected_ua}")
    
    # NUEVO: Configuraciones adicionales anti-detección
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    
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
    
    # Scripts anti-detección ULTRA mejorados
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            // Eliminar TODAS las propiedades de webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__webdriver_script_fn;
            delete navigator.__webdriver_unwrapped;
            delete navigator.__webdriver_evaluate;
            delete navigator.__selenium_unwrapped;
            delete navigator.__fxdriver_unwrapped;
            delete navigator.__driver_evaluate;
            delete navigator.__webdriver_evaluate__;
            delete navigator.__selenium_evaluate;
            delete navigator.__fxdriver_evaluate;
            delete navigator.__driver_unwrapped;
            delete navigator.__webdriver_unwrapped__;
            delete navigator.__selenium_unwrapped__;
            delete navigator.__fxdriver_unwrapped__;
            
            // Falsificar plugins más realista
            Object.defineProperty(navigator, 'plugins', {
                get: () => ({
                    0: {name: "Chrome PDF Plugin", description: "Portable Document Format", filename: "internal-pdf-viewer"},
                    1: {name: "Chrome PDF Viewer", description: "", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                    2: {name: "Native Client", description: "", filename: "internal-nacl-plugin"},
                    3: {name: "Widevine Content Decryption Module", description: "Enables Widevine licenses for playback of HTML audio/video content", filename: "widevinecdmadapter.dll"},
                    length: 4
                })
            });
            
            // Falsificar idiomas
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});
            
            // Falsificar hardware
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            
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
            
            // Falsificar WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
            
            // Falsificar timezone
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() {
                    return {timeZone: 'America/Lima'};
                }
            });
            
            // Eliminar detección por timing
            const originalSetInterval = window.setInterval;
            const originalSetTimeout = window.setTimeout;
            
            window.setInterval = function(callback, delay) {
                return originalSetInterval(callback, delay + Math.random() * 50);
            };
            
            window.setTimeout = function(callback, delay) {
                return originalSetTimeout(callback, delay + Math.random() * 50);
            };
        '''
    })
    
    # Configurar timeouts AUMENTADOS
    driver.set_page_load_timeout(45)  # AUMENTADO
    driver.implicitly_wait(15)        # AUMENTADO
    
    return driver

def guardar(cursor, pid, urls):
    """Función de guardado MEJORADA"""
    if not urls:
        return 0
    
    carpeta = os.path.join(IMAGENES_DIR, str(pid))
    os.makedirs(carpeta, exist_ok=True)
    print(f"  📁 Guardando en: images/{pid}/")
    
    # BORRAR imágenes existentes antes de guardar nuevas
    try:
        cursor.execute("DELETE FROM imagenes_propiedad WHERE propiedad_id = %s", (pid,))
        cursor.fetchall()
        print(f"  🗑️ Imágenes anteriores eliminadas de BD")
    except Exception as e:
        print(f"  ⚠️ Error eliminando imágenes anteriores: {e}")
    
    # NUEVO: También borrar archivos físicos anteriores
    try:
        if os.path.exists(carpeta):
            for archivo in os.listdir(carpeta):
                ruta_archivo = os.path.join(carpeta, archivo)
                if os.path.isfile(ruta_archivo):
                    os.remove(ruta_archivo)
            print(f"  🗑️ Archivos físicos anteriores eliminados")
    except Exception as e:
        print(f"  ⚠️ Error eliminando archivos físicos: {e}")
    
    guardadas = 0
    errores_descarga = 0
    
    for idx, url in enumerate(urls, start=1):
        nombre = f"imagen_{idx:02d}.jpg"
        ruta_local = os.path.join(carpeta, nombre)
        es_principal = 1 if idx == 1 else 0
        
        print(f"    💾 Descargando imagen {idx}/{len(urls)}...")
        
        # NUEVO: Múltiples intentos de descarga
        descarga_exitosa = False
        for intento_descarga in range(3):  # Hasta 3 intentos por imagen
            if descargar(url, ruta_local):
                descarga_exitosa = True
                break
            elif intento_descarga < 2:
                print(f"      🔄 Reintentando descarga {intento_descarga + 2}/3...")
                time.sleep(random.uniform(2, 4))
        
        if descarga_exitosa:
            # NUEVO: Verificar que el archivo se descargó correctamente
            try:
                if os.path.exists(ruta_local) and os.path.getsize(ruta_local) > 1000:  # Al menos 1KB
                    cursor.execute("""
                        INSERT INTO imagenes_propiedad (propiedad_id, ruta_local, url_imagen, es_principal)
                        VALUES (%s, %s, %s, %s)
                    """, (pid, ruta_local, url, es_principal))
                    cursor.fetchall()
                    guardadas += 1
                    print(f"      ✅ Imagen {idx} guardada exitosamente")
                else:
                    print(f"      ❌ Archivo corrupto o muy pequeño")
                    errores_descarga += 1
                    # Eliminar archivo corrupto
                    if os.path.exists(ruta_local):
                        os.remove(ruta_local)
            except Exception as e:
                print(f"      ❌ Error verificando archivo: {e}")
                errores_descarga += 1
        else:
            print(f"      ❌ Error en descarga después de 3 intentos")
            errores_descarga += 1
        
        # Pausa entre descargas MÁS VARIABLE
        time.sleep(random.uniform(0.5, 1.5))  # AUMENTADO
    
    print(f"  ✅ {guardadas}/{len(urls)} imágenes guardadas exitosamente")
    if errores_descarga > 0:
        print(f"  ⚠️ {errores_descarga} errores de descarga")
    
    return guardadas

def main():
    """Función principal ULTRA MEJORADA"""
    print("🚀 DESCARGA DE IMÁGENES - MODO INCREMENTAL v5.0 ULTRA MEJORADO")
    print("="*80)
    print("🎯 CRITERIO: Solo propiedades con 10+ imágenes se consideran completas")
    print("🔧 MEJORAS IMPLEMENTADAS:")
    print("   ✅ 1. Extracción MÁS agresiva: 150 clicks máximo, más persistente")
    print("   ✅ 2. Mejor detección de imágenes: Verifica tamaño, evita miniaturas, lazy loading")
    print("   ✅ 3. Múltiples estrategias de navegación: Botones, teclas, JavaScript directo")
    print("   ✅ 4. Reseteo mejorado del slider: Más intentos, múltiples métodos")
    print("   ✅ 5. Estrategia alternativa: Si obtiene pocas imágenes, intenta scroll adicional")
    print("   ✅ 6. Reinicio más frecuente: Cada 2 propiedades para mejor rendimiento")
    print("   ✅ 7. Pausas más largas: Entre propiedades y reintentos")
    print("   ✅ 8. Mejor logging: Más información sobre el proceso")
    print("="*80)
    
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
    
    # Mostrar qué se va a reprocesar con más detalle
    print(f"\n🔄 PROPIEDADES QUE SERÁN REPROCESADAS CON EXTRACCIÓN ULTRA MEJORADA:")
    print("=" * 70)
    
    propiedades_reprocessar = []
    for i, url in enumerate(links_pendientes[:15], 1):  # Mostrar solo las primeras 15
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
            necesita = MINIMO_IMAGENES - num_imagenes_actual if num_imagenes_actual < MINIMO_IMAGENES else 0
            print(f"   {i:2d}. ID {id_interno} → {estado} (necesita {necesita} más)")
            propiedades_reprocessar.append((id_interno, num_imagenes_actual))
            
        except:
            print(f"   {i:2d}. ID {id_interno} → Error consultando")
    
    if len(links_pendientes) > 15:
        print(f"   ... y {len(links_pendientes) - 15} más")
    
    # Confirmación del usuario con más información
    print(f"\n🤔 CONFIRMACIÓN:")
    print(f"   📊 Se procesarán/reprocesarán {len(links_pendientes)} propiedades")
    print(f"   🎯 Objetivo: Al menos {MINIMO_IMAGENES} imágenes por propiedad")
    print(f"   ⚡ Con extracción ULTRA mejorada (hasta 150 clicks por propiedad)")
    print(f"   ⏱️ Tiempo estimado: {len(links_pendientes) * 3:.0f}-{len(links_pendientes) * 5:.0f} minutos")
    print(f"\n¿Continuar con el procesamiento ULTRA mejorado? (s/n): ", end="")
    respuesta = input().lower().strip()
    
    if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Proceso cancelado por el usuario")
        conn.close()
        return
    
    # Crear directorio de imágenes
    os.makedirs(IMAGENES_DIR, exist_ok=True)
    
    # Configuración de procesamiento ULTRA MEJORADA
    REINICIAR_CADA = 2  # Reiniciar cada 2 propiedades para mejor rendimiento
    total_imagenes = 0
    propiedades_exitosas = 0
    propiedades_fallidas = 0
    driver = None
    
    inicio_tiempo = time.time()
    
    print(f"\n🎯 INICIANDO PROCESAMIENTO ULTRA MEJORADO DE {len(links_pendientes)} PROPIEDADES")
    print("="*90)
    print("🔧 CONFIGURACIÓN ACTIVA:")
    print(f"   📊 Máximo clicks por propiedad: 150")
    print(f"   🔄 Reinicio de navegador cada: {REINICIAR_CADA} propiedades")
    print(f"   🎯 Objetivo mínimo por propiedad: {MINIMO_IMAGENES} imágenes")
    print(f"   ⏱️ Pausas extendidas: 20-35s entre propiedades")
    print("="*90)
    
    for i, url in enumerate(links_pendientes, 1):
        tiempo_transcurrido = time.time() - inicio_tiempo
        velocidad = i / (tiempo_transcurrido / 60) if tiempo_transcurrido > 0 else 0
        tiempo_restante = (len(links_pendientes) - i) / velocidad if velocidad > 0 else 0
        
        print(f"\n{'='*100}")
        print(f"🏠 PROPIEDAD {i}/{len(links_pendientes)} | Total: {i + len(links_ya_procesados)}/{len(todos_los_links)}")
        print(f"⏱️ Tiempo: {tiempo_transcurrido/60:.1f}min | Velocidad: {velocidad:.1f} prop/min | ETA: {tiempo_restante:.0f}min")
        print(f"📊 Exitosas: {propiedades_exitosas} | Fallidas: {propiedades_fallidas} | Imágenes totales: {total_imagenes}")
        print(f"🔗 {url}")
        
        # Verificación doble por seguridad
        id_interno = url.split("-")[-1].replace("/", "")
        if verificar_imagenes_existentes(cur, id_interno, MINIMO_IMAGENES):
            print(f"⚠️ ADVERTENCIA: Propiedad {id_interno} ya tiene {MINIMO_IMAGENES}+ imágenes, saltando...")
            continue
        
        # Crear o reiniciar navegador MÁS FRECUENTEMENTE
        if driver is None or (i - 1) % REINICIAR_CADA == 0:
            if driver:
                print(f"🔄 Reiniciando navegador (cada {REINICIAR_CADA} propiedades para MÁXIMO rendimiento)")
                try:
                    driver.quit()
                except:
                    pass
                
                pausa_reinicio = random.uniform(40, 60)  # PAUSA MÁS LARGA para evitar detección
                print(f"⏱️ Pausa de reinicio EXTENDIDA: {pausa_reinicio:.1f}s")
                time.sleep(pausa_reinicio)
            
            print("🌐 Creando nuevo navegador con configuración ULTRA stealth...")
            try:
                driver = crear_driver_ultra_stealth()
                print("✅ Navegador ULTRA stealth creado exitosamente")
                
                # NUEVO: Simular actividad inicial en el navegador
                try:
                    driver.get("https://www.google.com")
                    time.sleep(random.uniform(3, 6))
                    print("✅ Navegador 'calentado' con actividad inicial")
                except:
                    pass
                    
            except Exception as e:
                print(f"❌ Error creando navegador: {e}")
                time.sleep(20)
                continue
        
        # Obtener ID de propiedad
        pid = propiedad_id(cur, id_interno)
        
        if not pid:
            print(f"❌ No existe propiedad en BD: {id_interno}")
            propiedades_fallidas += 1
            continue
        
        # Mostrar estado actual de la propiedad con más detalle
        try:
            cur.execute("""
                SELECT COUNT(*) 
                FROM imagenes_propiedad ip
                INNER JOIN propiedades p ON p.id = ip.propiedad_id
                WHERE p.id_interno = %s
            """, (id_interno,))
            
            imagenes_actuales = cur.fetchone()[0]
            cur.fetchall()
            
            necesita = max(0, MINIMO_IMAGENES - imagenes_actuales)
            print(f"📊 Estado actual: {imagenes_actuales} imágenes → Objetivo: {MINIMO_IMAGENES}+ (necesita {necesita} más)")
            
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
                time.sleep(random.uniform(90, 120))  # PAUSA EXTRA LARGA
                continue
            
            # Intentar extraer imágenes con sistema ULTRA mejorado
            print("🎯 Iniciando extracción ULTRA MEJORADA...")
            imgs = extraer_imagenes_con_reintentos_mejorado(driver, url, max_intentos=4)
            
            if imgs:
                print(f"💾 Guardando {len(imgs)} imágenes en base de datos...")
                guardadas = guardar(cur, pid, imgs)
                conn.commit()
                total_imagenes += guardadas
                propiedades_exitosas += 1
                
                # Mensaje de éxito MÁS detallado
                if guardadas >= MINIMO_IMAGENES:
                    print(f"🎉 ÉXITO COMPLETO: {guardadas} imágenes guardadas → ¡Objetivo de {MINIMO_IMAGENES}+ CUMPLIDO! ✅")
                else:
                    aun_necesita = MINIMO_IMAGENES - guardadas
                    print(f"⚠️ ÉXITO PARCIAL: {guardadas} imágenes guardadas → Aún necesita {aun_necesita} más para objetivo")
                
                print(f"📁 Ubicación: images/{pid}/")
                print(f"🏆 Promedio por propiedad exitosa: {total_imagenes/propiedades_exitosas:.1f} imágenes")
                
                # Crear respaldo cada 2 propiedades exitosas (más frecuente)
                if propiedades_exitosas % 2 == 0:
                    crear_respaldo_progreso(propiedades_exitosas, propiedades_fallidas, total_imagenes)
                
            else:
                print("⚠️ Sin imágenes encontradas después de TODOS los intentos ULTRA mejorados")
                propiedades_fallidas += 1
            
            # Limpiar cache después de cada propiedad
            limpiar_cache(driver)
                
        except Exception as e:
            error_msg = str(e)[:150]
            print(f"❌ Error procesando propiedad: {error_msg}")
            propiedades_fallidas += 1
            
            # Reiniciar navegador en caso de error crítico
            if any(palabra in error_msg.lower() for palabra in 
                   ["timeout", "disconnected", "crashed", "blocked", "session", "chrome", "unreachable"]):
                print("🔄 Error crítico detectado, reiniciando navegador...")
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                time.sleep(random.uniform(60, 90))  # PAUSA EXTRA LARGA
        
        # Pausa entre propiedades EXTRA LARGA para máximo stealth
        if i < len(links_pendientes):
            pausa = random.uniform(30, 50)  # AUMENTADO SIGNIFICATIVAMENTE
            print(f"⏱️ Pausa ULTRA anti-detección: {pausa:.1f}s antes de siguiente propiedad...")
            print(f"   💡 Esto asegura máximo stealth y evita bloqueos")
            time.sleep(pausa)
    
    # Limpieza final
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    # Crear respaldo final
    crear_respaldo_progreso(propiedades_exitosas, propiedades_fallidas, total_imagenes)
    
    # Estadísticas finales ULTRA MEJORADAS
    tiempo_total = (time.time() - inicio_tiempo) / 60
    total_procesadas_ahora = propiedades_exitosas + propiedades_fallidas
    total_con_imagenes = len(links_ya_procesados) + propiedades_exitosas
    
    print(f"\n🎉 PROCESO ULTRA MEJORADO COMPLETADO EN {tiempo_total:.1f} MINUTOS")
    print("="*90)
    print(f"📊 ESTADÍSTICAS DE ESTA SESIÓN ULTRA MEJORADA:")
    print(f"   🔄 Propiedades procesadas ahora: {total_procesadas_ahora}")
    print(f"   ✅ Exitosas en esta sesión: {propiedades_exitosas}")
    print(f"   ❌ Fallidas en esta sesión: {propiedades_fallidas}")
    print(f"   📸 Imágenes descargadas ahora: {total_imagenes}")
    print(f"   ⚡ Velocidad promedio: {total_procesadas_ahora/(tiempo_total) if tiempo_total > 0 else 0:.2f} propiedades/min")
    
    if propiedades_exitosas > 0:
        print(f"   🏆 Promedio imágenes/propiedad exitosa: {total_imagenes/propiedades_exitosas:.1f}")
        print(f"   🎯 Propiedades que alcanzaron objetivo (10+): {sum(1 for _ in range(propiedades_exitosas)) if total_imagenes >= propiedades_exitosas * 10 else 'Calculando...'}")
    
    print(f"\n📊 ESTADÍSTICAS TOTALES DEL PROYECTO:")
    print(f"   🏠 Total propiedades disponibles: {len(todos_los_links)}")
    print(f"   ✅ Total con {MINIMO_IMAGENES}+ imágenes: {total_con_imagenes}")
    print(f"   ❌ Aún pendientes: {len(todos_los_links) - total_con_imagenes}")
    print(f"   📈 Progreso total: {(total_con_imagenes/len(todos_los_links)*100):.1f}%")
    
    # Proyección de finalización
    if propiedades_exitosas > 0 and tiempo_total > 0:
        velocidad_actual = propiedades_exitosas / tiempo_total
        pendientes = len(todos_los_links) - total_con_imagenes
        tiempo_estimado_completar = pendientes / velocidad_actual if velocidad_actual > 0 else 0
        print(f"   ⏱️ Tiempo estimado para completar todo: {tiempo_estimado_completar:.0f} minutos")
    
    # Mostrar estadísticas finales de BD
    print(f"\n📊 VERIFICACIÓN FINAL EN BASE DE DATOS:")
    mostrar_estadisticas_detalladas_mejoradas(cur, MINIMO_IMAGENES)
    
    print(f"\n✅ MEJORAS IMPLEMENTADAS EN ESTA VERSIÓN:")
    print(f"   🎯 Extracción más agresiva: 150 clicks máximo (vs 100 anterior)")
    print(f"   🔍 Mejor detección: Validación estricta de tamaño e imágenes")
    print(f"   🚀 Múltiples estrategias: 8 métodos de navegación diferentes")
    print(f"   🔄 Reseteo mejorado: 25 intentos de reseteo (vs 15 anterior)")
    print(f"   🎭 Estrategia alternativa: Scroll, lazy loading, resoluciones")
    print(f"   ⏱️ Pausas más largas: 30-50s entre propiedades (vs 20-35s)")
    print(f"   📋 Mejor logging: Información detallada del progreso")
    print(f"   🛡️ Ultra stealth: Anti-detección mejorado")
    
    try:
        conn.close()
    except:
        pass

if __name__ == "__main__":
    main()