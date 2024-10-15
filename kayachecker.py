import subprocess
import os
import time
import socket
import datetime
from multiprocessing import Pool
import json
from collections import deque

# File paths
input_file = r'c:\\your_path\\bitcoin_addresses.txt'
positive_balance_file = r'c:\\your_path\\walletwithbalance.txt'
failure_file = r'c:\\your_path\\failure.txt'
potentially_not_checked_file = r'c:\\your_path\\Potentially_not_checked.txt'
electrum_path = r'c:\\your_path\\electrum-4.5.5-portable.exe'

class TimeEstimator:
    def __init__(self, max_samples=200):
        self.times = deque(maxlen=max_samples)
        self.start_time = time.time()

    def update(self, elapsed_time):
        self.times.append(elapsed_time)

    def estimate_remaining_time(self, remaining_tasks):
        if len(self.times) == 0:
            return None
        avg_time_per_task = sum(self.times) / len(self.times)
        remaining_time = avg_time_per_task * remaining_tasks
        return remaining_time

# Safeguard: check for internet and Electrum availability
def safeguard_check():
    def is_internet_available():
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def is_electrum_available():
        try:
            result = subprocess.run([electrum_path, '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    was_down = False

    while True:
        internet_ok = is_internet_available()
        electrum_ok = is_electrum_available()

        if internet_ok and electrum_ok:
            if was_down:
                print("Internet and Electrum are back online. Starting in 30 seconds...")
                for i in range(30, 0, -1):
                    print(f"Resuming in {i} seconds...", end="\r")
                    time.sleep(1)
                was_down = False
            break
        else:
            if not internet_ok:
                print("No internet connection. Waiting...")
            if not electrum_ok:
                print("Electrum is unavailable. Waiting...")
            was_down = True
            time.sleep(2)

def is_valid_bitcoin_address(address: str) -> bool:
    if address.startswith('1') and 26 <= len(address) <= 35:
        return True
    elif address.startswith('3') and 34 <= len(address) <= 35:
        return True
    elif address.startswith('bc1') and 42 <= len(address) <= 62:
        return True
    else:
        return False

def print_ignored_addresses(ignored_addresses: list):
    if ignored_addresses:
        print("\nThe following lines in the input file were ignored because they are not valid Bitcoin addresses:")
        for address in ignored_addresses:
            print(address)

        for i in range(10, 0, -1):
            print(f"Continuing in {i} seconds...", end="\r")
            time.sleep(1)
        print("\nProceeding with the valid addresses...")
    else:
        print("bitcoin_addresses.txt - wallets integrity checked and all good")

def check_balance(address: str) -> tuple[bool, str]:
    safeguard_check()
    try:
        result = subprocess.run([electrum_path, 'getaddressbalance', address], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def log_potentially_not_checked(last_wallet_address, addresses):
    if last_wallet_address not in addresses:
        print(f"Error: Last recorded wallet {last_wallet_address} not found in addresses list.")
        return
    
    # Find the index of the last recorded wallet
    last_index = addresses.index(last_wallet_address)

    # Get 3 wallets before and 3 after the last recorded wallet
    start_index = max(0, last_index - 3)
    end_index = min(len(addresses), last_index + 4)

    nearby_wallets = addresses[start_index:end_index]

    # Log to potentially_not_checked.txt with date and time
    with open(potentially_not_checked_file, 'a') as f:
        f.write(f"\n----------------------------------------\n")
        f.write(f"Date, Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for wallet in nearby_wallets:
            f.write(f"{wallet}\n")
    print("Logged potentially unchecked wallets to Potentially_not_checked.txt")

def log_result(result: tuple[bool, str, str], counter: list, processed_wallets: list, time_estimator: TimeEstimator, addresses: list):
    success, wallet_address, message = result
    processed_wallets[0] += 1
    with open(failure_file, 'w') as f:
        f.write(f"Last Recorded Wallet : {wallet_address}\n")
        f.write(f"Number of Processed Wallets : {processed_wallets[0]}\n")

    if success:
        try:
            balance_info = json.loads(message)
            confirmed = float(balance_info.get('confirmed', 0))
            log_message = f"Address: {wallet_address}, Balance: {confirmed} BTC"
            print(f"Checking Kaya AI: {wallet_address}")
            
            if confirmed > 0:
                with open(positive_balance_file, 'a') as positive_file:
                    positive_file.write(f"Address: {wallet_address}, Balance: {confirmed} BTC\n")

        except json.JSONDecodeError as e:
            log_message = f"Address: {wallet_address}, Error parsing balance: {str(e)}"
    else:
        log_message = f"Address: {wallet_address}, Error: {message}"
        log_potentially_not_checked(wallet_address, addresses)

    print(log_message)

    counter[0] -= 1
    elapsed_time = time.time() - time_estimator.start_time
    time_estimator.start_time = time.time()
    time_estimator.update(elapsed_time)

    remaining_time = time_estimator.estimate_remaining_time(counter[0])
    if remaining_time is not None:
        remaining_hours = int(remaining_time // 3600)
        remaining_minutes = int((remaining_time % 3600) // 60)
        print(f"Remaining wallets to process: {counter[0]} - Estimated remaining time {remaining_hours}H{remaining_minutes}MN")
    else:
        print(f"Remaining wallets to process: {counter[0]} - Remaining time under calculation")

def worker(address: str, counter: list, processed_wallets: list, time_estimator: TimeEstimator, addresses: list) -> tuple[bool, str, str]:
    success, message = check_balance(address)
    return success, address, message

def handle_failure_file():
    """
    Handle the presence of failure.txt, check if last_wallet_address is empty, 
    and prompt the user to process bitcoin_addresses.txt from the beginning or review their data.
    """
    last_wallet_address = None
    processed_wallets = 0

    # Read the failure.txt and check if it's correctly formatted
    try:
        with open(failure_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                last_wallet_line = lines[0].strip().split(': ')
                processed_wallets_line = lines[1].strip().split(': ')

                if len(last_wallet_line) == 2:
                    last_wallet_address = last_wallet_line[1]

                if len(processed_wallets_line) == 2 and processed_wallets_line[1].isdigit():
                    processed_wallets = int(processed_wallets_line[1])
    except Exception as e:
        print(f"Error reading failure.txt: {e}")
    
    if not last_wallet_address:
        print("Warning: last_wallet_address is empty or failure.txt is malformed.")
        return None, 0

    print(f"Last recorded wallet: {last_wallet_address}")
    print(f"Number of wallets processed: {processed_wallets}")

    # Prompt user to continue from the last wallet or start over
    choice = input("""
    Failure file detected:
    [Y] Start over and reset failure.txt?
    [N] Continue from the last recorded wallet?
    Please enter Y or N: """).strip().upper()

    if choice == 'Y':
        with open(failure_file, 'w') as f:
            f.write("Last Recorded Wallet : \n")
            f.write("Number of Processed Wallets : 0\n")
        print("Resetting progress. Starting from the beginning.")
        return None, 0  # Reset to start from the beginning

    elif choice == 'N':
        print("Continuing from the last recorded wallet.")
        return last_wallet_address, processed_wallets
    else:
        print("Invalid input. Please enter Y or N.")
        return handle_failure_file()  # Retry if input is invalid

if __name__ == '__main__':
    safeguard_check()

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        exit(1)

    with open(input_file, 'r') as f:
        addresses = f.read().splitlines()

    # Sanitize input file: filter out empty lines or lines that contain only whitespace
    addresses = [addr for addr in addresses if addr.strip()]

    last_wallet_address, processed_wallets = None, 0
    if os.path.exists(failure_file):
        last_wallet_address, processed_wallets = handle_failure_file()

    if last_wallet_address is None:
        valid_addresses = []
        ignored_addresses = []
        for address in addresses:
            if is_valid_bitcoin_address(address):
                valid_addresses.append(address)
            else:
                ignored_addresses.append(address)

        print_ignored_addresses(ignored_addresses)
        addresses = valid_addresses

    if last_wallet_address:
        last_index = addresses.index(last_wallet_address) if last_wallet_address in addresses else 0
    else:
        last_index = 0

    total_wallets = len(addresses)
    remaining_wallets = total_wallets - processed_wallets
    print(f"Total wallets to process: {total_wallets}")
    print(f"Remaining wallets to process: {remaining_wallets}")

    counter = [remaining_wallets]
    processed_wallets_list = [processed_wallets]

    time_estimator = TimeEstimator()

    pool = Pool(5)
    for i, address in enumerate(addresses[last_index:], start=last_index):
        safeguard_check()
        pool.apply_async(worker, args=(address, counter, processed_wallets_list, time_estimator, addresses), 
                         callback=lambda result: log_result(result, counter, processed_wallets_list, time_estimator, addresses))

    pool.close()
    pool.join()
