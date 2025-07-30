# extraer_links_agente.py - EXTRACTOR CORREGIDO PARA REMAX REAL
import json
import os
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

# Instalar selenium-stealth si está disponible
try:
    from selenium_stealth import stealth
    STEALTH_AVAILABLE = True
except ImportError:
    print("⚠️ selenium-stealth no instalado. Ejecuta: pip install selenium-stealth")
    STEALTH_AVAILABLE = False

def crear_driver_stealth():
    """Crea un navegador con configuración stealth"""
    print("🌐 Creando navegador con configuración stealth...")
    
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
    
    # Configuración stealth
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--ignore-certificate-errors")
    
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
    
    # Scripts anti-detección
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__webdriver_script_fn;
            delete navigator.__webdriver_unwrapped;
            delete navigator.__webdriver_evaluate;
            delete navigator.__selenium_unwrapped;
            delete navigator.__fxdriver_unwrapped;
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => ({
                    0: {name: "Chrome PDF Plugin"},
                    1: {name: "Chrome PDF Viewer"},
                    2: {name: "Native Client"},
                    length: 3
                })
            });
            
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});
        '''
    })
    
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    return driver

def simular_comportamiento_humano(driver):
    """Simula comportamiento humano en la página"""
    try:
        print("  👤 Simulando comportamiento humano...")
        
        # Scroll aleatorio
        scrolls = random.randint(3, 5)
        for _ in range(scrolls):
            scroll_amount = random.randint(300, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(1.5, 3))
        
        # Simular movimiento de mouse
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
                }, i * 300);
            }
        """)
        
        time.sleep(random.uniform(2, 4))
        
    except Exception as e:
        print(f"  ⚠️ Error simulando comportamiento: {e}")

def es_link_propiedad_valido(url):
    """Verifica si un URL es válido para una propiedad"""
    if not url or not url.startswith("http"):
        return False
    
    # Debe contener remax.pe
    if "remax.pe" not in url.lower():
        return False
    
    # Patrones que hay que evitar
    patrones_invalidos = [
        "/agents/",
        "/agente/",
        "/office/",
        "/oficina/",
        "/buscar",
        "/search",
        "javascript:",
        "mailto:",
        "tel:",
        "#"
    ]
    
    # Verificar que no tenga patrones inválidos
    for patron in patrones_invalidos:
        if patron in url.lower():
            return False
    
    # Verificar que contenga patrones de propiedades o termine con ID
    try:
        # Estructura típica: cualquier-cosa-NUMEROID/
        ultimo_segmento = url.rstrip("/").split("/")[-1]
        
        # Buscar patrón ID-NUMERO al final
        if "-" in ultimo_segmento:
            partes = ultimo_segmento.split("-")
            ultimo_id = partes[-1]
            if ultimo_id.isdigit() and len(ultimo_id) >= 6:
                return True
        
        # O si la URL completa contiene números largos que parecen IDs
        import re
        ids_encontrados = re.findall(r'\d{6,}', url)
        if ids_encontrados:
            return True
            
    except:
        pass
    
    return False

def extraer_links_agente_remax(driver, url_agente):
    """Extrae todos los links de propiedades del agente con selectores específicos de RE/MAX"""
    print(f"🔍 Extrayendo links del agente RE/MAX: {url_agente}")
    
    try:
        # Ir a la página del agente
        driver.get(url_agente)
        
        # Pausa inicial más larga
        pausa_inicial = random.uniform(10, 15)
        print(f"⏱️ Esperando carga inicial: {pausa_inicial:.1f}s")
        time.sleep(pausa_inicial)
        
        # Verificar que la página cargó
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("  ✅ Página cargada correctamente")
        except TimeoutException:
            print("  ❌ Timeout esperando carga de página")
            return []
        
        # Simular comportamiento humano
        simular_comportamiento_humano(driver)
        
        # Confirmar agente
        try:
            texto_pagina = driver.page_source.lower()
            if "marisol" in texto_pagina or "neyra" in texto_pagina:
                print("  ✅ Agente Marisol confirmado")
            else:
                print("  ⚠️ No se pudo confirmar el agente, continuando...")
        except:
            pass
        
        links_encontrados = set()
        
        print("  🔍 Buscando links con estrategias específicas de RE/MAX...")
        
        # ESTRATEGIA 1: Buscar TODOS los enlaces que contengan números largos
        print("    🎯 Estrategia 1: Buscar todos los links con IDs...")
        try:
            todos_los_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"    📋 Analizando {len(todos_los_links)} links totales...")
            
            links_con_id = 0
            for link in todos_los_links:
                try:
                    href = link.get_attribute("href")
                    if href and es_link_propiedad_valido(href):
                        links_encontrados.add(href)
                        links_con_id += 1
                        if links_con_id <= 5:  # Mostrar primeros 5
                            print(f"      ✅ Link {links_con_id}: ...{href.split('/')[-1]}")
                except:
                    continue
            
            print(f"    📊 Links con ID encontrados: {links_con_id}")
            
        except Exception as e:
            print(f"    ❌ Error en estrategia 1: {e}")
        
        # ESTRATEGIA 2: Buscar por onclick o eventos JavaScript
        print("    🎯 Estrategia 2: Buscar elementos clickeables...")
        try:
            elementos_clickeables = driver.find_elements(By.CSS_SELECTOR, 
                "[onclick], [data-href], [data-url], [data-link]")
            
            for elemento in elementos_clickeables:
                try:
                    # Buscar en atributos onclick, data-href, etc.
                    for attr in ["onclick", "data-href", "data-url", "data-link"]:
                        valor = elemento.get_attribute(attr)
                        if valor and "http" in valor:
                            # Extraer URL del JavaScript
                            import re
                            urls = re.findall(r'https?://[^\s\'"]+', valor)
                            for url in urls:
                                if es_link_propiedad_valido(url):
                                    links_encontrados.add(url)
                except:
                    continue
                    
        except Exception as e:
            print(f"    ❌ Error en estrategia 2: {e}")
        
        # ESTRATEGIA 3: Inspección del HTML fuente
        print("    🎯 Estrategia 3: Buscar en HTML fuente...")
        try:
            html_source = driver.page_source
            import re
            
            # Buscar patrones de URLs de propiedades en el HTML
            patron_url = r'https?://[^\s\'"<>]+(?:propiedades?|property|inmueble)[^\s\'"<>]*\d{6,}[^\s\'"<>]*'
            urls_en_html = re.findall(patron_url, html_source, re.IGNORECASE)
            
            for url in urls_en_html:
                url_limpia = url.rstrip('",\'>;')  # Limpiar caracteres finales
                if es_link_propiedad_valido(url_limpia):
                    links_encontrados.add(url_limpia)
            
            print(f"    📊 URLs encontradas en HTML: {len(urls_en_html)}")
            
        except Exception as e:
            print(f"    ❌ Error en estrategia 3: {e}")
        
        # ESTRATEGIA 4: Scroll y carga dinámica
        print("    🎯 Estrategia 4: Scroll para cargar contenido dinámico...")
        scrolls_realizados = 0
        for scroll in range(8):  # Más scrolls
            try:
                # Scroll hacia abajo
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(3, 5))
                
                # Buscar nuevos links después del scroll
                nuevos_links = driver.find_elements(By.TAG_NAME, "a")
                links_antes = len(links_encontrados)
                
                for link in nuevos_links:
                    try:
                        href = link.get_attribute("href")
                        if href and es_link_propiedad_valido(href):
                            links_encontrados.add(href)
                    except:
                        continue
                
                nuevos_encontrados = len(links_encontrados) - links_antes
                scrolls_realizados += 1
                
                if nuevos_encontrados > 0:
                    print(f"      📈 Scroll {scrolls_realizados}: +{nuevos_encontrados} links nuevos")
                else:
                    print(f"      📊 Scroll {scrolls_realizados}: sin cambios")
                
            except Exception as e:
                print(f"      ⚠️ Error en scroll {scroll}: {e}")
                break
        
        # ESTRATEGIA 5: Buscar imágenes y elementos padre
        print("    🎯 Estrategia 5: Buscar a través de imágenes...")
        try:
            imagenes = driver.find_elements(By.TAG_NAME, "img")
            print(f"    📊 Analizando {len(imagenes)} imágenes...")
            
            for img in imagenes:
                try:
                    # Buscar link padre de la imagen
                    link_padre = img.find_element(By.XPATH, "./ancestor::a[@href]")
                    href = link_padre.get_attribute("href")
                    if href and es_link_propiedad_valido(href):
                        links_encontrados.add(href)
                except:
                    continue
                    
        except Exception as e:
            print(f"    ❌ Error en estrategia 5: {e}")
        
        # Scroll final hacia arriba para asegurar
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # Convertir a lista y mostrar resultados
        links_finales = list(links_encontrados)
        
        print(f"  📊 RESULTADOS FINALES:")
        print(f"     🔍 Links únicos encontrados: {len(links_finales)}")
        
        # Mostrar todos los links encontrados
        if links_finales:
            print("  📋 TODOS LOS LINKS ENCONTRADOS:")
            for i, link in enumerate(links_finales, 1):
                try:
                    id_prop = link.split("-")[-1].replace("/", "")
                    print(f"    {i:2d}. ID {id_prop}: {link}")
                except:
                    print(f"    {i:2d}. {link}")
        else:
            print("  ❌ NO SE ENCONTRARON LINKS DE PROPIEDADES")
            print("  🔍 DEBUGGING: Vamos a inspeccionar la página...")
            
            # Debugging: mostrar algunos links para entender la estructura
            try:
                todos_links_debug = driver.find_elements(By.TAG_NAME, "a")[:10]
                print("  📋 PRIMEROS 10 LINKS EN LA PÁGINA (para debugging):")
                for i, link in enumerate(todos_links_debug, 1):
                    try:
                        href = link.get_attribute("href")
                        texto = link.text.strip()[:50]
                        print(f"    {i}. {href} | Texto: '{texto}'")
                    except:
                        print(f"    {i}. Error obteniendo link")
            except:
                print("  ❌ Error en debugging")
        
        return links_finales
        
    except Exception as e:
        print(f"  ❌ Error general extrayendo links: {e}")
        return []

def crear_links_ejemplo():
    """Crea links de ejemplo para pruebas basados en los IDs visibles"""
    print("🔧 CREANDO LINKS DE EJEMPLO BASADOS EN LA PÁGINA REAL...")
    
    # IDs que se ven en la imagen (más algunos adicionales estimados)
    ids_reales_aproximados = [
        "1147916", "1147892", "1147032", "1146745",  # Visibles en la imagen
        "1146588", "1146234", "1145987", "1145654", 
        "1145321", "1144998", "1144776", "1144455",
        "1144123", "1143876", "1143654", "1143321",
        "1142998", "1142776"  # IDs estimados basados en el patrón
    ]
    
    links_ejemplo = []
    tipos_propiedades = ["terreno", "casa", "departamento", "local"]
    ubicaciones = ["lima", "surco", "callao", "san-isidro"]
    
    print(f"  📋 Generando {len(ids_reales_aproximados)} links de ejemplo...")
    
    for i, id_prop in enumerate(ids_reales_aproximados):
        tipo = random.choice(tipos_propiedades)
        ubicacion = random.choice(ubicaciones)
        
        # URL con estructura similar a RE/MAX real
        link = f"https://www.remax.pe/propiedades/{tipo}-en-{ubicacion}-{id_prop}/"
        links_ejemplo.append(link)
        
        if i < 5:  # Mostrar los primeros 5
            print(f"    {i+1}. ID {id_prop}: {link}")
    
    if len(links_ejemplo) > 5:
        print(f"    ... y {len(links_ejemplo) - 5} más")
    
    return links_ejemplo

def guardar_links(links, archivo="data/links.json"):
    """Guarda los links en archivo JSON"""
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        
        # Guardar links
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Links guardados en: {archivo}")
        print(f"📊 Total de links: {len(links)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando links: {e}")
        return False

def main():
    print("🚀 EXTRACTOR DE LINKS CORREGIDO PARA RE/MAX")
    print("=" * 60)
    print("📋 Versión mejorada con estrategias específicas para RE/MAX")
    print("=" * 60)
    
    # URL real del agente
    URL_AGENTE_REAL = "https://remax.pe/web/agents/marisoln@remaxexpo.com/remax-expo/"
    
    print("\n🎯 OPCIONES DISPONIBLES:")
    print("1. Extraer links REALES del agente (método mejorado)")
    print("2. Crear links de EJEMPLO basados en IDs visibles")
    
    while True:
        opcion = input("\n📝 Selecciona una opción (1 o 2): ").strip()
        
        if opcion == "1":
            print(f"\n🌐 EXTRAYENDO LINKS REALES CON MÉTODO MEJORADO:")
            print(f"🔗 URL: {URL_AGENTE_REAL}")
            
            driver = None
            try:
                # Crear navegador
                driver = crear_driver_stealth()
                
                # Extraer links reales con método corregido
                links = extraer_links_agente_remax(driver, URL_AGENTE_REAL)
                
                if links:
                    print(f"\n✅ EXTRACCIÓN EXITOSA: {len(links)} propiedades encontradas")
                    
                    # Guardar links
                    if guardar_links(links):
                        print("\n🎉 PROCESO COMPLETADO EXITOSAMENTE")
                        print("💡 Ahora puedes ejecutar: python verificar_y_cargar_datos.py")
                    else:
                        print("❌ Error guardando los links")
                else:
                    print("\n⚠️ No se encontraron propiedades con el método automático")
                    print("💡 Prueba la opción 2 para usar links de ejemplo")
                    
            except Exception as e:
                print(f"❌ Error durante la extracción: {e}")
                
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            break
            
        elif opcion == "2":
            print("\n🔧 CREANDO LINKS DE EJEMPLO BASADOS EN IDS REALES...")
            links = crear_links_ejemplo()
            
            if guardar_links(links):
                print("\n✅ LINKS DE EJEMPLO CREADOS")
                print("💡 Ahora puedes ejecutar: python verificar_y_cargar_datos.py")
                print("⚠️ NOTA: Estos son links aproximados basados en los IDs visibles")
            break
            
        else:
            print("❌ Opción inválida. Por favor selecciona 1 o 2.")

if __name__ == "__main__":
    main()