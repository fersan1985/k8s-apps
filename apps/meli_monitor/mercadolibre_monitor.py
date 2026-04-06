#!/usr/bin/env python3
"""
Monitor de precios de MercadoLibre Argentina
Notifica cuando hay bajadas de precio o cuotas sin interés
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Se requieren las librerías 'requests' y 'beautifulsoup4'")
    print("Instalar con: pip install requests beautifulsoup4")
    sys.exit(1)


DATA_FILE = Path(os.getenv("DATA_FILE", str(Path.home() / ".mercadolibre_monitor.json")))
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")


class Product:
    def __init__(self, url: str, name: str = "", price: float = 0,
                 installments: str = "", last_check: str = ""):
        self.url = url
        self.name = name
        self.price = price
        self.installments = installments
        self.last_check = last_check
        self.price_history: List[Dict] = []

    def to_dict(self):
        return {
            "url": self.url,
            "name": self.name,
            "price": self.price,
            "installments": self.installments,
            "last_check": self.last_check,
            "price_history": self.price_history
        }

    @classmethod
    def from_dict(cls, data: dict):
        product = cls(
            url=data["url"],
            name=data.get("name", ""),
            price=data.get("price", 0),
            installments=data.get("installments", ""),
            last_check=data.get("last_check", "")
        )
        product.price_history = data.get("price_history", [])
        return product


def load_products() -> Dict[str, Product]:
    """Carga los productos guardados"""
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return {url: Product.from_dict(p) for url, p in data.items()}


def save_products(products: Dict[str, Product]):
    """Guarda los productos"""
    data = {url: p.to_dict() for url, p in products.items()}
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def send_notification(message: str):
    """Envía notificación a Slack o Discord"""
    sent = False

    if SLACK_WEBHOOK:
        try:
            payload = {"text": message}
            response = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
            if response.status_code == 200:
                sent = True
                print("✓ Notificación enviada a Slack")
        except Exception as e:
            print(f"Error enviando a Slack: {e}")

    if DISCORD_WEBHOOK:
        try:
            payload = {"content": message}
            response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
            if response.status_code == 204:
                sent = True
                print("✓ Notificación enviada a Discord")
        except Exception as e:
            print(f"Error enviando a Discord: {e}")

    return sent


def scrape_product(url: str) -> Optional[Dict]:
    """Extrae información del producto de MercadoLibre"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraer título
        title_elem = soup.find('h1', class_='ui-pdp-title')
        if not title_elem:
            return None
        title = title_elem.text.strip()

        # Extraer precio
        price_elem = soup.find('span', class_='andes-money-amount__fraction')
        if not price_elem:
            return None

        price_text = price_elem.text.strip().replace('.', '').replace(',', '.')
        price = float(price_text)

        # Extraer información de cuotas
        installments = ""
        installments_elem = soup.find('span', class_='ui-pdp-color--GREEN')
        if installments_elem:
            installments = installments_elem.text.strip()

        # Buscar si hay cuotas sin interés
        has_interest_free = False
        if installments_elem:
            text = installments_elem.text.lower()
            has_interest_free = 'sin interés' in text or 'sin interes' in text

        return {
            'name': title,
            'price': price,
            'installments': installments,
            'has_interest_free': has_interest_free
        }

    except Exception as e:
        print(f"Error al obtener datos: {e}")
        return None


def add_product(url: str):
    """Agrega un producto para monitorear"""
    products = load_products()

    if url in products:
        print(f"❌ Este producto ya está siendo monitoreado")
        return

    print(f"🔍 Obteniendo información del producto...")
    data = scrape_product(url)

    if not data:
        print("❌ No se pudo obtener la información del producto")
        return

    product = Product(
        url=url,
        name=data['name'],
        price=data['price'],
        installments=data['installments'],
        last_check=datetime.now().isoformat()
    )

    product.price_history.append({
        'date': datetime.now().isoformat(),
        'price': data['price'],
        'installments': data['installments']
    })

    products[url] = product
    save_products(products)

    print(f"✅ Producto agregado:")
    print(f"   {data['name']}")
    print(f"   Precio: ${data['price']:,.2f}")
    if data['installments']:
        print(f"   {data['installments']}")


def list_products():
    """Lista todos los productos monitoreados"""
    products = load_products()

    if not products:
        print("No hay productos monitoreados aún.")
        print("Usa: mercadolibre_monitor.py add <URL>")
        return

    print(f"\n📋 Productos monitoreados ({len(products)}):\n")

    for i, (url, product) in enumerate(products.items(), 1):
        print(f"{i}. {product.name}")
        print(f"   Precio actual: ${product.price:,.2f}")
        if product.installments:
            print(f"   {product.installments}")
        print(f"   Última revisión: {product.last_check[:16]}")

        if len(product.price_history) > 1:
            first_price = product.price_history[0]['price']
            diff = product.price - first_price
            if diff < 0:
                print(f"   📉 Bajó ${abs(diff):,.2f} desde que se agregó")
            elif diff > 0:
                print(f"   📈 Subió ${diff:,.2f} desde que se agregó")
        print()


def check_products():
    """Verifica los precios de todos los productos"""
    products = load_products()

    if not products:
        print("No hay productos para verificar.")
        return

    print(f"🔍 Verificando {len(products)} productos...\n")

    notifications = []

    for url, product in products.items():
        print(f"⏳ {product.name[:50]}...")
        data = scrape_product(url)

        if not data:
            print("   ❌ Error al obtener datos\n")
            continue

        old_price = product.price
        new_price = data['price']

        # Actualizar producto
        product.price = new_price
        product.installments = data['installments']
        product.last_check = datetime.now().isoformat()

        product.price_history.append({
            'date': datetime.now().isoformat(),
            'price': new_price,
            'installments': data['installments']
        })

        # Verificar cambios
        if new_price < old_price:
            diff = old_price - new_price
            percent = (diff / old_price) * 100
            msg = f"💰 BAJÓ DE PRECIO: {product.name}\n"
            msg += f"   Antes: ${old_price:,.2f} → Ahora: ${new_price:,.2f}\n"
            msg += f"   Ahorro: ${diff:,.2f} ({percent:.1f}%)"
            notifications.append(msg)
            print(f"   ✅ {msg}\n")
        elif new_price > old_price:
            diff = new_price - old_price
            print(f"   📈 Subió ${diff:,.2f}\n")
        else:
            print(f"   ✓ Sin cambios (${new_price:,.2f})\n")

        # Verificar cuotas sin interés
        if data['has_interest_free'] and 'sin interés' not in product.installments.lower():
            msg = f"🎉 CUOTAS SIN INTERÉS: {product.name}\n"
            msg += f"   {data['installments']}"
            notifications.append(msg)
            print(f"   ✅ {msg}\n")

    save_products(products)

    if notifications:
        print("\n" + "="*60)
        print("🔔 NOTIFICACIONES")
        print("="*60 + "\n")
        for notif in notifications:
            print(notif)
            print()

        # Enviar notificaciones
        full_message = "\n\n".join(notifications)
        send_notification(full_message)


def remove_product(index: int):
    """Elimina un producto por índice"""
    products = load_products()

    if not products:
        print("No hay productos para eliminar.")
        return

    products_list = list(products.items())

    if index < 1 or index > len(products_list):
        print(f"❌ Índice inválido. Usa un número entre 1 y {len(products_list)}")
        return

    url, product = products_list[index - 1]
    del products[url]
    save_products(products)

    print(f"✅ Producto eliminado: {product.name}")


def main():
    parser = argparse.ArgumentParser(
        description='Monitor de precios de MercadoLibre Argentina',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s add https://www.mercadolibre.com.ar/...
  %(prog)s list
  %(prog)s check
  %(prog)s remove 1
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Add command
    add_parser = subparsers.add_parser('add', help='Agregar producto para monitorear')
    add_parser.add_argument('url', help='URL del producto en MercadoLibre')

    # List command
    subparsers.add_parser('list', help='Listar productos monitoreados')

    # Check command
    subparsers.add_parser('check', help='Verificar precios de todos los productos')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Eliminar producto')
    remove_parser.add_argument('index', type=int, help='Índice del producto (ver con list)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'add':
        add_product(args.url)
    elif args.command == 'list':
        list_products()
    elif args.command == 'check':
        check_products()
    elif args.command == 'remove':
        remove_product(args.index)


if __name__ == '__main__':
    main()
