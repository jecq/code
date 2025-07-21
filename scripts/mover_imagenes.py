"""
Mueve las imágenes de ./imágenes/  →  htdocs/inmo_imgs/{propiedad_id}/
y actualiza la DB con las URLs públicas.
"""
import os
import shutil
import mysql.connector
from pathlib import Path

# CONFIGURACIÓN
PROJECT_ROOT   = Path(__file__).resolve().parent.parent
IMAGES_SRC     = PROJECT_ROOT / "imágenes"
HTDOCS_IMGS    = Path("C:/xampp/htdocs/inmo_imgs")
BASE_URL       = "http://localhost/inmo_imgs"

DB_CONFIG = dict(
    host="localhost",
    user="root",
    password="",
    database="bd_propiedades_inmobiliarias"
)

def mover_y_actualizar():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur  = conn.cursor()

    for prop_id_dir in IMAGES_SRC.iterdir():
        if not prop_id_dir.is_dir():
            continue
        prop_id = prop_id_dir.name
        dst_dir = HTDOCS_IMGS / prop_id
        dst_dir.mkdir(parents=True, exist_ok=True)

        for img_file in prop_id_dir.glob("*.jpg"):
            dst_path = dst_dir / img_file.name
            shutil.move(str(img_file), dst_path)

            url_abs = f"{BASE_URL}/{prop_id}/{img_file.name}"
            cur.execute(
                "UPDATE imagenes_propiedad "
                "SET ruta_local=%s, url_imagen=%s "
                "WHERE propiedad_id=%s AND ruta_local=%s",
                (str(dst_path), url_abs, prop_id, str(img_file))
            )
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Imágenes movidas y URLs actualizadas.")

if __name__ == "__main__":
    mover_y_actualizar()