import os
import time
import hashlib
import hmac
import urllib.request
import json
import ssl

# Color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def banner():
    font = f"""{RED}
 _    _                                   _                _ _   _       _                 
 | |__(_)_ _  __ _ _ _  __ ___   __ _ _  _| |_ ___  __ __ _(_) |_| |_  __| |_ _ __ ___ __ __
 | '_ \ | ' \/ _` | ' \/ _/ -_) / _` | || |  _/ _ \ \ V  V / |  _| ' \/ _` | '_/ _` \ V  V /
 |_.__/_|_||_\__,_|_||_\__\___| \__,_|\_,_|\__\___/  \_/\_/|_|\__|_||_\__,_|_| \__,_|\_/\_/ 
         {GREEN}by Bassem Mhamdi V1.0{RESET}"""
    print(font)

# Binance API configuration
API_KEY = os.getenv('BINANCE_API_KEY', 'add_API_KEY_here')
API_SECRET = os.getenv('BINANCE_API_SECRET', 'add_API_SECRET_here')
BASE_URL = 'https://api.binance.com'

def get_balances():
    """Get all non-zero balances"""
    timestamp = int(time.time() * 1000)
    query_string = f'timestamp={timestamp}'
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{BASE_URL}/api/v3/account?{query_string}&signature={signature}"
    request = urllib.request.Request(url)
    request.add_header('X-MBX-APIKEY', API_KEY)
    
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(request, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            return [asset for asset in data['balances'] 
                    if float(asset['free']) > 0 or float(asset['locked']) > 0]
    except Exception as e:
        print(f"{YELLOW}Error getting balances: {e}{RESET}")
        return []

def get_withdrawable_assets():
    """Get assets that support withdrawal and their networks"""
    timestamp = int(time.time() * 1000)
    query_string = f'timestamp={timestamp}'
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{BASE_URL}/sapi/v1/capital/config/getall?{query_string}&signature={signature}"
    request = urllib.request.Request(url)
    request.add_header('X-MBX-APIKEY', API_KEY)
    
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(request, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {coin['coin']: [
                net for net in coin['networkList'] 
                if net['withdrawEnable']
            ] for coin in data if any(net['withdrawEnable'] for net in coin['networkList'])}
    except Exception as e:
        print(f"{YELLOW}Error getting withdrawable assets: {e}{RESET}")
        return {}

def withdraw(asset, address, amount, network, memo=''):
    """Perform withdrawal to external address"""
    timestamp = int(time.time() * 1000)
    params = {
        'coin': asset,
        'address': address,
        'amount': amount,
        'network': network,
        'timestamp': timestamp
    }
    
    if memo:
        params['addressTag'] = memo
    
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{BASE_URL}/sapi/v1/capital/withdraw/apply?{query_string}&signature={signature}"
    request = urllib.request.Request(url, method='POST')
    request.add_header('X-MBX-APIKEY', API_KEY)
    request.add_header('Content-Type', 'application/x-www-form-urlencoded')
    
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(request, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            if 'id' in data:
                return data['id']
            print(f"{YELLOW}Withdrawal response: {data}{RESET}")
            return None
    except Exception as e:
        print(f"{YELLOW}Withdrawal error: {e}{RESET}")
        return None

def get_network_info(asset, network):
    """Get withdrawal fee and minimum amount for a network"""
    timestamp = int(time.time() * 1000)
    query_string = f'timestamp={timestamp}'
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{BASE_URL}/sapi/v1/capital/config/getall?{query_string}&signature={signature}"
    request = urllib.request.Request(url)
    request.add_header('X-MBX-APIKEY', API_KEY)
    
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(request, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            for coin in data:
                if coin['coin'] == asset:
                    for net in coin['networkList']:
                        if net['network'] == network:
                            return {
                                'fee': float(net['withdrawFee']),
                                'min': float(net['withdrawMin'])
                            }
        return None
    except Exception as e:
        print(f"{YELLOW}Error getting network info: {e}{RESET}")
        return None

def main():
    banner()
    print(f"{YELLOW}Fetching your account balances...{RESET}")
    
    # Step 1: Get all balances and withdrawable assets
    balances = get_balances()
    withdrawable_assets = get_withdrawable_assets()
    
    if not balances:
        print(f"{YELLOW}No assets found with positive balance{RESET}")
        return
    
    # Step 2: Create list of withdrawable assets with balance
    available_to_withdraw = []
    for asset in balances:
        symbol = asset['asset']
        free_balance = float(asset['free'])
        locked_balance = float(asset['locked'])
        
        if free_balance <= 0 and locked_balance <= 0:
            continue
        
        if symbol in withdrawable_assets:
            available_to_withdraw.append({
                'symbol': symbol,
                'free': free_balance,
                'locked': locked_balance,
                'networks': withdrawable_assets[symbol]
            })
    
    if not available_to_withdraw:
        print(f"{YELLOW}No withdrawable assets found{RESET}")
        return
    
    # Step 3: Display available assets
    print(f"{YELLOW}\nWithdrawable Assets:{RESET}")
    for i, asset in enumerate(available_to_withdraw, 1):
        networks = ", ".join([net['network'] for net in asset['networks']])
        print(f"{YELLOW}{i}. {asset['symbol']} - Available: {asset['free']:.8f} (Locked: {asset['locked']:.8f}){RESET}")
        print(f"{YELLOW}   Networks: {networks}{RESET}")
    
    # Step 4: Select asset
    try:
        choice = int(input(f"{YELLOW}\nSelect asset to withdraw (number): {RESET}")) - 1
        if choice < 0 or choice >= len(available_to_withdraw):
            print(f"{YELLOW}Invalid selection{RESET}")
            return
        selected_asset = available_to_withdraw[choice]
    except ValueError:
        print(f"{YELLOW}Invalid input{RESET}")
        return
    
    # Step 5: Select network
    print(f"{YELLOW}\nAvailable networks for {selected_asset['symbol']}:{RESET}")
    for i, net in enumerate(selected_asset['networks'], 1):
        print(f"{YELLOW}{i}. {net['network']} - Fee: {net['withdrawFee']} {selected_asset['symbol']}{RESET}")
    
    try:
        net_choice = int(input(f"{YELLOW}Select network (number): {RESET}")) - 1
        if net_choice < 0 or net_choice >= len(selected_asset['networks']):
            print(f"{YELLOW}Invalid selection{RESET}")
            return
        selected_network = selected_asset['networks'][net_choice]['network']
    except ValueError:
        print(f"{YELLOW}Invalid input{RESET}")
        return
    
    # Step 6: Get address and memo
    print(f"{YELLOW}\nPreparing to withdraw {selected_asset['symbol']} via {selected_network} network{RESET}")
    address = input(f"{YELLOW}Enter destination address: {RESET}")
    
    memo = ""
    if selected_asset['networks'][net_choice].get('addressRegex') or \
       selected_asset['networks'][net_choice].get('memoRegex'):
        memo = input(f"{YELLOW}Enter memo/tag (if required, else leave blank): {RESET}")
    
    # Step 7: Get network fee info
    network_info = get_network_info(selected_asset['symbol'], selected_network)
    if not network_info:
        print(f"{YELLOW}Failed to get network fee information{RESET}")
        return
    
    # Step 8: Calculate withdrawable amount
    balance = selected_asset['free']
    fee = network_info['fee']
    min_amount = network_info['min']
    
    net_amount = balance - fee
    if net_amount < min_amount:
        print(f"{YELLOW}Insufficient funds after fee. Need at least {min_amount + fee:.8f} {selected_asset['symbol']}{RESET}")
        return
    
    # Step 9: Confirm withdrawal
    print(f"{YELLOW}\nSummary:{RESET}")
    print(f"{YELLOW}Asset: {selected_asset['symbol']}{RESET}")
    print(f"{YELLOW}Network: {selected_network}{RESET}")
    print(f"{YELLOW}Available balance: {balance:.8f}{RESET}")
    print(f"{YELLOW}Withdrawal fee: {fee:.8f}{RESET}")
    print(f"{YELLOW}Net amount: {net_amount:.8f}{RESET}")
    print(f"{YELLOW}Destination: {address}{RESET}")
    if memo:
        print(f"{YELLOW}Memo: {memo}{RESET}")
    
    confirm = input(f"{YELLOW}\nConfirm withdrawal? (Type 'CONFIRM' to proceed): {RESET}")
    if confirm != 'CONFIRM':
        print(f"{YELLOW}Withdrawal canceled{RESET}")
        return
    
    # Step 10: Execute withdrawal
    print(f"{YELLOW}\nInitiating withdrawal...{RESET}")
    withdrawal_id = withdraw(
        selected_asset['symbol'],
        address,
        balance,
        selected_network,
        memo
    )
    
    if withdrawal_id:
        print(f"{YELLOW}Withdrawal submitted! Transaction ID: {withdrawal_id}{RESET}")
        print(f"{YELLOW}Check your email for confirmation and your Binance withdrawal history{RESET}")
    else:
        print(f"{YELLOW}Withdrawal failed{RESET}")

if __name__ == '__main__':
    main()
