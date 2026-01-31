import requests
import time
import logging
import os
from datetime import datetime

#Config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cloudflare_dns_updater.log"),
        logging.StreamHandler()
    ]
)

#Authorization Info
CLOUDFLARE_EMAIL = "You Cloudflare Email"
CLOUDFLARE_API_KEY = "API KEY"

#DNS
ZONE_NAME = "root domain"
RECORD_NAME = "subdomain"
FULL_RECORD_NAME = f"{RECORD_NAME}.{ZONE_NAME}"
TTL = 1  # 1 = Auto TTl
PROXIED = False  # DNS Only

def get_current_ip():
    """Get current IP"""
    try:
        response = requests.get("https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        return response.json()['ip']
    except Exception as e:
        logging.error(f"Failed to get IP: {str(e)}")
        return None

def get_zone_id():
    """Get Cloudflare Zone ID"""
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    params = {"name": ZONE_NAME}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result['success'] and result['result']:
            return result['result'][0]['id']
        else:
            logging.error(f"Failed to find this zone {ZONE_NAME}: {result['errors']}")
            return None
    except Exception as e:
        logging.error(f"Failed to get zone ID: {str(e)}")
        return None

def get_dns_record_info(zone_id):
    """Get DNS current record"""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    params = {
        "type": "A",
        "name": FULL_RECORD_NAME
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result['success'] and result['result']:
            record = result['result'][0]
            return record['id'], record['name'], record['content']
        else:
            logging.error(f"Failed to find this record {FULL_RECORD_NAME}: {result['errors']}")
            return None, None, None
    except Exception as e:
        logging.error(f"Failed to get this record: {str(e)}")
        return None, None, None

def update_dns_record(zone_id, record_id, new_ip):
    """Update DNS record"""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {
        "X-Auth-Email": CLOUDFLARE_EMAIL,
        "X-Auth-Key": CLOUDFLARE_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "type": "A",
        "name": RECORD_NAME,
        "content": new_ip,
        "ttl": TTL,
        "proxied": PROXIED
    }
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result['success']:
            logging.info(f"Update successfully {FULL_RECORD_NAME} -> {new_ip}")
            return True
        else:
            logging.error(f"Failed to update: {result['errors']}")
            return False
    except Exception as e:
        logging.error(f"Failed to update DNS record: {str(e)}")
        return False

def main_job():
    """Main Function"""
    logging.info("="*50)
    logging.info("Started to update DNS record")
    
    # 获取当前IP
    current_ip = get_current_ip()
    if not current_ip:
        logging.warning("This task was skipped.Error:We cannot get IP address")
        return
    
    logging.info(f"Current IP: {current_ip}")
    
    #Get Zone ID
    zone_id = get_zone_id()
    if not zone_id:
        logging.error("This task was stopped.Eroor:We cannot get zone ID.")
        return
    
    #Get Record Info
    record_id, record_name, record_ip = get_dns_record_info(zone_id)
    if not record_id:
        logging.error("This task was stopped.Eroor:We cannot get record ID.")
        return
    
    #Security
    if record_name != FULL_RECORD_NAME:
        logging.error(f"Warning:Security anomalous：Got anomalous record '{record_name}'，expected to be '{FULL_RECORD_NAME}'")
        return
    
    #Check whether should modify the record
    if record_ip == current_ip:
        logging.info(f"Record IP {record_ip} is the current IP.There's no need to update the record")
        return
    
    #Update DNS
    update_dns_record(zone_id, record_id, current_ip)

if __name__ == "__main__":
    #Verify environment value
    if not CLOUDFLARE_EMAIL or not CLOUDFLARE_API_KEY:
        logging.error("Please set value:CLOUDFLARE_EMAIL和CLOUDFLARE_API_KEY.")
        exit(1)
    
    logging.info("Cloudflare DNS Update Service was started.")
    logging.info(f"The domain that will be modified: {FULL_RECORD_NAME}")
    logging.info(f"How often: 15m | Proxy Mode: {'DNS Only' if not PROXIED else 'Proxied'}")
    
    #First Task
    main_job()
    
    #Do it per 15 minutes
    while True:
        time.sleep(900)  # 15m = 900s
        main_job()
