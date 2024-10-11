import subprocess
from multiprocessing import Pool
import json
import os
import time
from collections import deque

print("Github: @kayaaicom")

# This code includes a time estimation method inspired by the jk_timest project:
# https://github.com/jkpubsrc/python-module-jk-timest


# Define input and output file paths
input_file = r'c:\\Your _path\\bitcoin_addresses.txt'
positive_balance_file = r'c:\\Your _path\\walletwithbalance.txt'
failure_file = r'c:\\Your _path\\failure.txt'
# Electrum path
electrum_path = r'c:\\Your _path\\electrum-4.5.5-portable.exe'


class TimeEstimator:
#Edit as you wish - the time estimator track the processing times of the last 200 wallets
    def __init__(self, max_samples=200):
        self.times = deque(maxlen=max_samples)
        self.start_time = time.time()

    def update(self, elapsed_time):
        self.times.append(elapsed_time)

    def estimate_remaining_time(self, remaining_tasks):
        if len(self.times) == 0:
            return None  # Not enough data to estimate
        avg_time_per_task = sum(self.times) / len(self.times)
        remaining_time = avg_time_per_task * remaining_tasks
        return remaining_time

def is_valid_bitcoin_address(address: str) -> bool:
    """
    Validates a Bitcoin address based on starting characters and length.
    """
    if address.startswith('1') and 26 <= len(address) <= 35:
        return True
    elif address.startswith('3') and 34 <= len(address) <= 35:
        return True
    elif address.startswith('bc1') and 42 <= len(address) <= 62:
        return True
    else:
        return False

def print_ignored_addresses(ignored_addresses: list):
    """
    Prints the ignored addresses and displays a countdown before program execution continues.
    """
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
    """
    Check the balance of a Bitcoin address using Electrum.
    """
    try:
        result = subprocess.run(
            [electrum_path, 'getaddressbalance', address], 
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def log_result(result: tuple[bool, str, str], counter: list, processed_wallets: list, time_estimator: TimeEstimator):
    """
    Log the result of the balance check, estimate remaining time, and update failure.txt.
    """
    success, wallet_address, message = result

    # Increment the number of processed wallets and save progress in failure.txt
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

    print(log_message)

    # Decrement the counter for remaining wallets
    counter[0] -= 1

    # Calculate time elapsed for this wallet
    elapsed_time = time.time() - time_estimator.start_time
    time_estimator.start_time = time.time()
    time_estimator.update(elapsed_time)

    # Estimate remaining time
    remaining_time = time_estimator.estimate_remaining_time(counter[0])
    if remaining_time is not None:
        remaining_hours = int(remaining_time // 3600)
        remaining_minutes = int((remaining_time % 3600) // 60)
        print(f"Remaining wallets to process: {counter[0]} - Estimated remaining time {remaining_hours}H{remaining_minutes}MN")
    else:
        print(f"Remaining wallets to process: {counter[0]} - Remaining time under calculation")

def worker(address: str, counter: list, processed_wallets: list, time_estimator: TimeEstimator) -> tuple[bool, str, str]:
    """
    Worker function to check the balance of a single Bitcoin address.
    """
    success, message = check_balance(address)
    return success, address, message

def handle_failure_file():
    """
    Handle the presence of failure.txt, prompting the user to either ignore or continue from it.
    """
    print("""
    We found a progress file (failure.txt) from your last run.
    failure.txt tracks the Last Recorded Wallet processed and the Number of Processed Wallets.

    Would you like to:
    [Y] Ignore the file and start from the beginning? 
        (This will discard your previous progress, reset the processed wallet count, and start fresh)
    [N] Continue from where you left off? 
        (This will resume scanning from the last recorded address)
    """)

    choice = input("Please type Y for Yes or N for No: ").strip().upper()
    
    if choice == 'Y':
        # Reset failure.txt and start fresh
        with open(failure_file, 'w') as f:
            f.write("Last Recorded Wallet : \n")
            f.write("Number of Processed Wallets : 0\n")
        print("Starting fresh. Previous progress has been discarded.")
        return None, 0  # No wallet to resume, processed_wallets = 0

    elif choice == 'N':
        # Continue from where it left off
        with open(failure_file, 'r') as f:
            last_wallet_address = f.readline().strip().split(': ')[1]
            processed_wallets = int(f.readline().strip().split(': ')[1])
        print(f"Resuming from wallet {last_wallet_address}.")
        return last_wallet_address, processed_wallets
    
    else:
        print("Invalid input. Please type Y for Yes or N for No.")
        return handle_failure_file()  # Retry on invalid input

if __name__ == '__main__':
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        exit(1)

    # Read addresses from the input file
    with open(input_file, 'r') as f:
        addresses = f.read().splitlines()

    # If failure.txt exists, ask the user whether to reset or continue
    last_wallet_address, processed_wallets = None, 0
    if os.path.exists(failure_file):
        last_wallet_address, processed_wallets = handle_failure_file()

    # If failure.txt was ignored, validate the addresses
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

    # Start processing addresses
    if last_wallet_address:
        last_index = addresses.index(last_wallet_address) if last_wallet_address in addresses else 0
    else:
        last_index = 0

    total_wallets = len(addresses)
    remaining_wallets = total_wallets - processed_wallets
    print(f"Total wallets to process: {remaining_wallets}")
    print(f"Remaining wallets to process: {remaining_wallets}")

    counter = [remaining_wallets]
    processed_wallets_list = [processed_wallets]

    time_estimator = TimeEstimator()

    pool = Pool(5)
    for i, address in enumerate(addresses[last_index:], start=last_index):
        pool.apply_async(worker, args=(address, counter, processed_wallets_list, time_estimator), 
                         callback=lambda result: log_result(result, counter, processed_wallets_list, time_estimator))

    pool.close()
    pool.join()
