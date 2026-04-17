import requests
import re
import json
from concurrent.futures import ThreadPoolExecutor
import time
from urllib.parse import quote
import pandas as pd
from fake_useragent import UserAgent
import warnings
warnings.filterwarnings('ignore')

class SIMTracker:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.results = {}
    
    def headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def clean_phone(self, number):
        number = re.sub(r'[^\d+]', '', str(number))
        if not number.startswith('+91') and len(number) in [10, 11]:
            number = '+91' + number[-10:]
        return number
    
    def trace_bharat(self, number):
        try:
            url = f"https://www.tracebharat.com/mobile-number-tracker.php"
            data = {'number': number}
            resp = self.session.post(url, data=data, headers=self.headers(), timeout=12)
            
            owner = re.search(r'Owner[:\s]*Name[:\s]*<[^>]*>([^<]+)', resp.text, re.I)
            loc = re.search(r'Location[:\s]*<[^>]*>([^<]+)', resp.text, re.I)
            circle = re.search(r'Circle[:\s]*<[^>]*>([^<]+)', resp.text, re.I)
            
            return {
                'source': 'tracebharat',
                'owner': owner.group(1).strip() if owner else 'N/A',
                'location': loc.group(1).strip() if loc else 'N/A',
                'circle': circle.group(1).strip() if circle else 'N/A'
            }
        except:
            return {'source': 'tracebharat', 'status': 'error'}
    
    def findandtrace(self, number):
        try:
            url = "https://findandtrace.com/trace-mobile-number-location"
            data = {'mobilenumber': number}
            resp = self.session.post(url, data=data, headers=self.headers(), timeout=12)
            
            owner = re.search(r'Owner Name[:\s]*([^\n<]+)', resp.text)
            state = re.search(r'State[:\s]*([^\n<]+)', resp.text)
            
            return {
                'source': 'findandtrace',
                'owner': owner.group(1).strip() if owner else 'N/A',
                'state': state.group(1).strip() if state else 'N/A'
            }
        except:
            return {'source': 'findandtrace', 'status': 'error'}
    
    def bulkcheck(self, number):
        try:
            url = f"https://www.bulkcheck.in/mobile-number-tracker/{number}"
            resp = self.session.get(url, headers=self.headers(), timeout=10)
            
            op = re.search(r'Operator[:\s]*([A-Z\s]+)', resp.text)
            circle = re.search(r'Circle[:\s]*([A-Z\s]+)', resp.text)
            
            return {
                'source': 'bulkcheck',
                'operator': op.group(1).strip() if op else 'N/A',
                'circle': circle.group(1).strip() if circle else 'N/A'
            }
        except:
            return {'source': 'bulkcheck', 'status': 'error'}
    
    def mobilesms(self, number):
        try:
            url = "https://mobilesms.io/trace-location/"
            data = {'phone': number}
            resp = self.session.post(url, data=data, headers=self.headers(), timeout=12)
            
            info = re.findall(r'([A-Za-z\s]+):([^\n<]+)', resp.text)
            details = dict(info[:2]) if info else {}
            
            return {'source': 'mobilesms', **details}
        except:
            return {'source': 'mobilesms', 'status': 'error'}
    
    def check_all(self, number):
        number = self.clean_phone(number)
        print(f"🔍 Checking {number}...")
        
        tasks = [
            lambda: self.trace_bharat(number),
            lambda: self.findandtrace(number),
            lambda: self.bulkcheck(number),
            lambda: self.mobilesms(number)
        ]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda f: f(), tasks))
        
        combined = {'number': number, 'sources': results}
        self.results[number] = combined
        return combined
    
    def scan_multiple(self, numbers):
        for num in numbers:
            self.check_all(num)
            time.sleep(1.5)
        return self.results
    
    def export(self, format='csv'):
        data = []
        for num, info in self.results.items():
            for source in info['sources']:
                row = {'Number': num, 'Source': source['source']}
                row.update({k: v for k, v in source.items() if k != 'source' and k != 'status'})
                data.append(row)
        
        df = pd.DataFrame(data)
        filename = f"sim_results_{int(time.time())}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ {filename} তৈরি!")
        return df
