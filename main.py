import requests
from collections import defaultdict
import os
import json
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_KEY = 'KEY'  # Замени на свой API ключ

def get_cities():
    """Получает список всех городов и населённых пунктов."""
    url = "https://api.novaposhta.ua/v2.0/json/"
    headers = {'Content-Type': 'application/json'}

    payload = {
        "apiKey": API_KEY,
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {}
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            return data['data']
        else:
            print(f"Ошибка: {data['errors']}")
    else:
        print(f"Ошибка HTTP: {response.status_code}")
    return []


def get_warehouses(city_ref):
    url = "https://api.novaposhta.ua/v2.0/json/"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "apiKey": API_KEY,
        "modelName": "AddressGeneral",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityRef": city_ref
        }
    }

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['data']
    except requests.exceptions.Timeout:
        print(f"Запрос для города {city_ref} превысил лимит времени.")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении отделений для города {city_ref}: {e}")
    return []


def save_cities_and_warehouses_by_region(cities):
    regions = defaultdict(list)
    
    # Группируем населённые пункты по областям и добавляем отделения
    for index, city in enumerate(cities):
        region_name = city.get('AreaDescription', 'Неизвестная область')
        city_name = city.get('Description', 'Неизвестный населённый пункт')
        settlement_type = city.get('SettlementTypeDescription', '')
        city_ref = city.get('Ref', '')

        print(f"[{index + 1}/{len(cities)}] Обрабатываем: {city_name} ({region_name})")

        # Получаем отделения для текущего населённого пункта
        warehouses = get_warehouses(city_ref)
        warehouse_list = [
            {
                'warehouse_number': wh.get('Number', ''),
                'description': wh.get('Description', ''),
                'type_of_warehouse': wh.get('TypeOfWarehouse', '')
            }
            for wh in warehouses
        ]

        city_data = {
            'name': city_name,
            'settlement_type': settlement_type,
            'region': region_name,
            'warehouses': warehouse_list
        }

        regions[region_name].append(city_data)

        
        sleep(0.3)
    
    
    os.makedirs('nova_poshta_regions', exist_ok=True)
    
   
    for region, cities_list in regions.items():
        file_name = f"nova_poshta_regions/{region}.json"
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(cities_list, file, ensure_ascii=False, indent=4)
        print(f"Сохранено: {file_name}")


if __name__ == "__main__":
    cities = get_cities()
    if cities:
        save_cities_and_warehouses_by_region(cities)
