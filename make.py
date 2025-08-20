import os
import time
import hashlib
import hmac
import urllib.request
import json
import ssl

# Binance API configuration
API_KEY = os.getenv('BINANCE_API_KEY', 'j4tVMFxHHfRRC2Oj0U9zTryy8hIoEe2wTWNUfmxSvs6kazhixAfgqibrfjn7fe5V')
API_SECRET = os.getenv('BINANCE_API_SECRET', 'f1qx6wYEF8tuIoeMbcaXyQNfPuZerfeEhZuAmkN9r3Zmk0yjtRlKvNlBWX5xaIGk')
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
        print(f"Error getting balances: {e}")
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
        print(f"Error getting withdrawable assets: {e}")
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
            print("Withdrawal response:", data)
            return None
    except Exception as e:
        print(f"Withdrawal error: {e}")
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
        print(f"Error getting network info: {e}")
        return None

def main():
    print("Fetching your account balances...")
    
    # Step 1: Get all balances and withdrawable assets
    balances = get_balances()
    withdrawable_assets = get_withdrawable_assets()
    
    if not balances:
        print("No assets found with positive balance")
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
        print("No withdrawable assets found")
        return
    
    # Step 3: Display available assets
    print("\nWithdrawable Assets:")
    for i, asset in enumerate(available_to_withdraw, 1):
        networks = ", ".join([net['network'] for net in asset['networks']])
        print(f"{i}. {asset['symbol']} - Available: {asset['free']:.8f} (Locked: {asset['locked']:.8f})")
        print(f"   Networks: {networks}")
    
    # Step 4: Select asset
    try:
        choice = int(input("\nSelect asset to withdraw (number): ")) - 1
        if choice < 0 or choice >= len(available_to_withdraw):
            print("Invalid selection")
            return
        selected_asset = available_to_withdraw[choice]
    except ValueError:
        print("Invalid input")
        return
    
    # Step 5: Select network
    print(f"\nAvailable networks for {selected_asset['symbol']}:")
    for i, net in enumerate(selected_asset['networks'], 1):
        print(f"{i}. {net['network']} - Fee: {net['withdrawFee']} {selected_asset['symbol']}")
    
    try:
        net_choice = int(input("Select network (number): ")) - 1
        if net_choice < 0 or net_choice >= len(selected_asset['networks']):
            print("Invalid selection")
            return
        selected_network = selected_asset['networks'][net_choice]['network']
    except ValueError:
        print("Invalid input")
        return
    
    # Step 6: Get address and memo
    print(f"\nPreparing to withdraw {selected_asset['symbol']} via {selected_network} network")
    address = input("Enter destination address: ")
    
    memo = ""
    if selected_asset['networks'][net_choice].get('addressRegex') or \
       selected_asset['networks'][net_choice].get('memoRegex'):
        memo = input("Enter memo/tag (if required, else leave blank): ")
    
    # Step 7: Get network fee info
    network_info = get_network_info(selected_asset['symbol'], selected_network)
    if not network_info:
        print("Failed to get network fee information")
        return
    
    # Step 8: Calculate withdrawable amount
    balance = selected_asset['free']
    fee = network_info['fee']
    min_amount = network_info['min']
    
    net_amount = balance - fee
    if net_amount < min_amount:
        print(f"Insufficient funds after fee. Need at least {min_amount + fee:.8f} {selected_asset['symbol']}")
        return
    
    # Step 9: Confirm withdrawal
    print(f"\nSummary:")
    print(f"Asset: {selected_asset['symbol']}")
    print(f"Network: {selected_network}")
    print(f"Available balance: {balance:.8f}")
    print(f"Withdrawal fee: {fee:.8f}")
    print(f"Net amount: {net_amount:.8f}")
    print(f"Destination: {address}")
    if memo:
        print(f"Memo: {memo}")
    
    confirm = input("\nConfirm withdrawal? (Type 'CONFIRM' to proceed): ")
    if confirm != 'CONFIRM':
        print("Withdrawal canceled")
        return
    
    # Step 10: Execute withdrawal
    print("\nInitiating withdrawal...")
    withdrawal_id = withdraw(
        selected_asset['symbol'],
        address,
        balance,
        selected_network,
        memo
    )
    
    if withdrawal_id:
        print(f"Withdrawal submitted! Transaction ID: {withdrawal_id}")
        print("Check your email for confirmation and your Binance withdrawal history")
    else:
        print("Withdrawal failed")

if __name__ == '__main__':
    main()
